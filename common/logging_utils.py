"""
Dual logging infrastructure for Tangerine ETL pipeline.

Provides logging to both database (dba.tlogentry) and rotating log files.
Supports structured JSON logging with run_uuid tracking for ETL job correlation.
"""

import logging
import json
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager
import threading

from common.config import get_config


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON with standardized fields:
    - timestamp: ISO format timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - message: Log message
    - run_uuid: ETL run identifier (if set in record)
    - processtype: Process/job name (if set in record)
    - metadata: Additional context data
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add run_uuid if present
        if hasattr(record, 'run_uuid'):
            log_data['run_uuid'] = record.run_uuid

        # Add processtype if present
        if hasattr(record, 'processtype'):
            log_data['processtype'] = record.processtype

        # Add stepcounter if present
        if hasattr(record, 'stepcounter'):
            log_data['stepcounter'] = record.stepcounter

        # Add username if present
        if hasattr(record, 'username'):
            log_data['username'] = record.username

        # Add runtime if present
        if hasattr(record, 'stepruntime'):
            log_data['stepruntime'] = record.stepruntime

        # Add any custom metadata
        if hasattr(record, 'metadata'):
            log_data['metadata'] = record.metadata

        # Include exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class DatabaseLogHandler(logging.Handler):
    """
    Custom logging handler that writes to dba.tlogentry table.

    Batches log entries for performance and flushes on:
    - ERROR or CRITICAL level
    - Every flush_interval seconds
    - When buffer reaches batch_size entries
    - Handler shutdown
    """

    def __init__(self, db_connection_func, batch_size=100, flush_interval=10):
        """
        Initialize database log handler.

        Args:
            db_connection_func: Function that returns a database connection
            batch_size: Number of entries to buffer before flushing
            flush_interval: Seconds between automatic flushes
        """
        super().__init__()
        self.db_connection_func = db_connection_func
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_lock = threading.Lock()
        self.last_flush = time.time()

    def emit(self, record: logging.LogRecord):
        """
        Emit a log record to the database buffer.

        Args:
            record: LogRecord to emit
        """
        try:
            log_entry = {
                'timestamp': datetime.utcnow(),
                'run_uuid': getattr(record, 'run_uuid', None) or 'system',
                'processtype': getattr(record, 'processtype', None) or record.name,
                'stepcounter': getattr(record, 'stepcounter', None),
                'username': getattr(record, 'username', None) or 'system',
                'stepruntime': getattr(record, 'stepruntime', None),
                'totalruntime': getattr(record, 'totalruntime', None),
                'message': record.getMessage()
            }

            with self.buffer_lock:
                self.buffer.append(log_entry)

                # Flush conditions
                should_flush = (
                    len(self.buffer) >= self.batch_size or
                    record.levelno >= logging.ERROR or
                    (time.time() - self.last_flush) >= self.flush_interval
                )

                if should_flush:
                    self.flush()

        except Exception:
            self.handleError(record)

    def flush(self):
        """Flush buffered log entries to database."""
        with self.buffer_lock:
            if not self.buffer:
                return

            entries_to_write = self.buffer.copy()
            self.buffer.clear()
            self.last_flush = time.time()

        # Write to database
        try:
            conn = self.db_connection_func()
            if conn is None:
                return

            cursor = conn.cursor()

            # Bulk insert
            insert_sql = """
                INSERT INTO dba.tlogentry
                (timestamp, run_uuid, processtype, stepcounter, username, stepruntime, totalruntime, message)
                VALUES (%(timestamp)s, %(run_uuid)s, %(processtype)s, %(stepcounter)s,
                        %(username)s, %(stepruntime)s, %(totalruntime)s, %(message)s)
            """

            cursor.executemany(insert_sql, entries_to_write)
            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            # If database write fails, log to stderr but don't raise
            print(f"ERROR: Failed to write logs to database: {e}", flush=True)

    def close(self):
        """Close handler and flush remaining entries."""
        self.flush()
        super().close()


class ETLLogger:
    """
    Context manager for ETL job logging with run_uuid tracking.

    Usage:
        with ETLLogger("MyETLJob", username="etl_user") as logger:
            logger.info("Starting extraction", extra={'stepcounter': 'extract'})
            logger.error("Failed to process", extra={'metadata': {'record_id': 123}})

    Features:
    - Automatic run_uuid generation and injection
    - Dual logging to files and database
    - Runtime tracking
    - Structured logging support
    """

    def __init__(
        self,
        processtype: str,
        username: Optional[str] = None,
        run_uuid: Optional[str] = None,
        log_level: Optional[str] = None
    ):
        """
        Initialize ETL logger.

        Args:
            processtype: Name of the ETL process/job
            username: User executing the job
            run_uuid: Optional existing run UUID (generates new if not provided)
            log_level: Optional log level override
        """
        self.processtype = processtype
        self.username = username or "system"
        self.run_uuid = run_uuid or str(uuid.uuid4())
        self.start_time = None
        self.logger = None

        config = get_config()
        self.log_level = log_level or config.etl.log_level
        self.log_dir = config.etl.log_dir
        self.enable_db_logging = config.etl.enable_db_logging
        self.enable_file_logging = config.etl.enable_file_logging

    def __enter__(self):
        """Set up logging context."""
        self.start_time = time.time()

        # Create logger
        logger_name = f"{self.processtype}.{self.run_uuid[:8]}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, self.log_level.upper()))

        # Remove existing handlers (in case logger was reused)
        self.logger.handlers.clear()

        # Add file handler if enabled
        if self.enable_file_logging:
            try:
                file_handler = RotatingFileHandler(
                    filename=f"{self.log_dir}/tangerine.log",
                    maxBytes=50 * 1024 * 1024,  # 50MB
                    backupCount=10,
                    encoding='utf-8'
                )
                file_handler.setFormatter(JsonFormatter())
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f"WARNING: Could not set up file logging: {e}", flush=True)

        # Add database handler if enabled
        if self.enable_db_logging:
            try:
                from common.db_utils import get_connection
                db_handler = DatabaseLogHandler(get_connection)
                db_handler.setLevel(logging.INFO)  # Only INFO and above to DB
                self.logger.addHandler(db_handler)
            except Exception as e:
                print(f"WARNING: Could not set up database logging: {e}", flush=True)

        # Add console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(console_handler)

        # Create adapter that injects run_uuid and processtype
        adapter = logging.LoggerAdapter(self.logger, {
            'run_uuid': self.run_uuid,
            'processtype': self.processtype,
            'username': self.username
        })

        return adapter

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up logging context."""
        # Calculate total runtime
        total_runtime = time.time() - self.start_time if self.start_time else 0

        # Log completion or failure
        if exc_type is None:
            self.logger.info(
                f"{self.processtype} completed successfully",
                extra={
                    'run_uuid': self.run_uuid,
                    'processtype': self.processtype,
                    'username': self.username,
                    'totalruntime': total_runtime
                }
            )
        else:
            self.logger.error(
                f"{self.processtype} failed: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={
                    'run_uuid': self.run_uuid,
                    'processtype': self.processtype,
                    'username': self.username,
                    'totalruntime': total_runtime
                }
            )

        # Flush all handlers
        for handler in self.logger.handlers:
            handler.flush()
            if isinstance(handler, DatabaseLogHandler):
                handler.close()

        return False  # Don't suppress exceptions


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name
        level: Optional log level override

    Returns:
        Configured logger
    """
    config = get_config()
    log_level = level or config.etl.log_level

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

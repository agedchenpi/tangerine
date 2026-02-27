"""
Shared utilities for ETL import scripts.

Provides common functions for saving JSON, running generic imports,
parsing dates/numbers, and generating audit columns.
"""

import json
import time
from datetime import datetime
from pathlib import Path

from common.db_utils import fetch_dict, db_transaction
from common.logging_utils import get_logger

logger = get_logger('import_utils')


def get_config_id(config_name: str) -> int:
    """Lookup config_id by config_name from dba.timportconfig."""
    rows = fetch_dict(
        "SELECT config_id FROM dba.timportconfig "
        "WHERE config_name = %s AND is_active = TRUE",
        (config_name,)
    )
    if not rows:
        raise ValueError(f"Config '{config_name}' not found or inactive in dba.timportconfig")
    return rows[0]['config_id']


def save_json(data: list, config_name: str, source: str) -> Path:
    """Save JSON array to /app/data/source/{source}/{source}_{slug}_{timestamp}.json"""
    source_dir = Path(f"/app/data/source/{source}")
    source_dir.mkdir(parents=True, exist_ok=True)

    # Derive slug from config_name: e.g. 'NewYorkFed_ReferenceRates_Latest' -> 'referencerates_latest'
    prefix_map = {
        'newyorkfed': 'NewYorkFed_',
        'bankofengland': 'BankOfEngland_',
        'yfinance': 'YFinance_',
        'coingecko': 'CoinGecko_',
    }
    prefix = prefix_map.get(source, '')
    slug = config_name.replace(prefix, '').lower()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source}_{slug}_{timestamp}.json"
    filepath = source_dir / filename

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved {len(data)} records to {filepath}")
    return filepath


class JobRunLogger:
    """Context manager that tracks top-level job runs and their steps in dba.tjobrun/tjobstep."""

    def __init__(self, job_name, config_name, dry_run=False, triggered_by='manual'):
        self.job_name = job_name
        self.config_name = config_name
        self.dry_run = dry_run
        self.triggered_by = triggered_by
        self.jobrunid = None
        self._step_start_times = {}
        self._any_success = False
        self._any_failure = False
        self._failure_msg = None

    def __enter__(self):
        self.jobrunid = self._create_job_run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._finish_job_run('failed', str(exc_val))
        elif self._any_failure and self._any_success:
            self._finish_job_run('partial', self._failure_msg)
        elif self._any_failure:
            self._finish_job_run('failed', self._failure_msg)
        else:
            self._finish_job_run('success', None)
        return False

    def begin_step(self, step_name: str, display_name: str) -> int:
        """Insert a running step row. Returns jobstepid."""
        order_map = {'data_collection': 1, 'db_import': 2}
        step_order = order_map.get(step_name, 99)
        try:
            with db_transaction(dict_cursor=False) as cursor:
                cursor.execute("""
                    INSERT INTO dba.tjobstep
                        (jobrunid, step_name, step_order, display_name, started_at, status)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, 'running')
                    RETURNING jobstepid
                """, (self.jobrunid, step_name, step_order, display_name))
                stepid = cursor.fetchone()[0]
                self._step_start_times[stepid] = time.time()
                return stepid
        except Exception as e:
            logger.error(f"JobRunLogger.begin_step failed: {e}")
            return -1

    def complete_step(self, stepid, records_in=None, records_out=None,
                      log_run_uuid=None, message=None):
        """Mark a step as successful."""
        runtime = time.time() - self._step_start_times.get(stepid, time.time())
        self._any_success = True
        self._update_step(stepid, 'success', records_in, records_out, runtime, log_run_uuid, message)

    def fail_step(self, stepid, message):
        """Mark a step as failed."""
        runtime = time.time() - self._step_start_times.get(stepid, time.time())
        self._any_failure = True
        self._failure_msg = message
        self._update_step(stepid, 'failed', None, None, runtime, None, message)

    def _create_job_run(self) -> int:
        try:
            with db_transaction(dict_cursor=False) as cursor:
                cursor.execute("""
                    INSERT INTO dba.tjobrun
                        (job_name, config_name, dry_run, triggered_by, started_at, status)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, 'running')
                    RETURNING jobrunid
                """, (self.job_name, self.config_name, self.dry_run, self.triggered_by))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"JobRunLogger._create_job_run failed: {e}")
            return -1

    def _finish_job_run(self, status: str, error_message):
        if self.jobrunid == -1:
            return
        try:
            with db_transaction(dict_cursor=False) as cursor:
                cursor.execute("""
                    UPDATE dba.tjobrun
                    SET status = %s, completed_at = CURRENT_TIMESTAMP, error_message = %s
                    WHERE jobrunid = %s
                """, (status, error_message, self.jobrunid))
        except Exception as e:
            logger.error(f"JobRunLogger._finish_job_run failed: {e}")

    def _update_step(self, stepid, status, records_in, records_out, runtime, log_run_uuid, message):
        if stepid == -1:
            return
        try:
            with db_transaction(dict_cursor=False) as cursor:
                cursor.execute("""
                    UPDATE dba.tjobstep
                    SET status = %s,
                        completed_at = CURRENT_TIMESTAMP,
                        records_in = %s,
                        records_out = %s,
                        step_runtime = %s,
                        log_run_uuid = %s,
                        message = %s
                    WHERE jobstepid = %s
                """, (status, records_in, records_out, runtime, log_run_uuid, message, stepid))
        except Exception as e:
            logger.error(f"JobRunLogger._update_step failed: {e}")


def run_generic_import(config_name: str, dry_run: bool = False, job_run_logger=None) -> int:
    """Lookup config_id by name, run GenericImportJob. Returns 0 on success, 1 on failure."""
    from etl.jobs.generic_import import GenericImportJob, ConfigNotFoundError

    step_id = None
    if job_run_logger is not None:
        step_id = job_run_logger.begin_step('db_import', 'Database Import')

    try:
        config_id = get_config_id(config_name)
    except ValueError as e:
        logger.error(str(e))
        if job_run_logger is not None and step_id is not None:
            job_run_logger.fail_step(step_id, str(e))
        return 1

    try:
        job = GenericImportJob(config_id=config_id, dry_run=dry_run)
    except ConfigNotFoundError as e:
        logger.error(f"Config not found: {e}")
        if job_run_logger is not None and step_id is not None:
            job_run_logger.fail_step(step_id, str(e))
        return 1

    print(f"Run UUID: {job.run_uuid}")

    # Link run_uuid to tjobrun
    if job_run_logger is not None and job_run_logger.jobrunid != -1:
        try:
            with db_transaction(dict_cursor=False) as cursor:
                cursor.execute(
                    "UPDATE dba.tjobrun SET run_uuid = %s WHERE jobrunid = %s",
                    (job.run_uuid, job_run_logger.jobrunid)
                )
        except Exception as e:
            logger.error(f"Failed to link run_uuid to tjobrun: {e}")

    try:
        job.run()
        logger.info(
            f"Import completed: {job.records_loaded} records loaded "
            f"from {len(job.matched_files)} file(s)"
        )
        if job_run_logger is not None and step_id is not None:
            job_run_logger.complete_step(
                step_id,
                records_in=len(job.matched_files),
                records_out=job.records_loaded,
                log_run_uuid=job.run_uuid
            )
        return 0
    except Exception as e:
        logger.error(f"Generic import failed: {e}")
        if job_run_logger is not None and step_id is not None:
            job_run_logger.fail_step(step_id, str(e))
        return 1


def parse_date(value: str) -> str | None:
    """Parse YYYY-MM-DD to ISO date string, or None."""
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d').strftime('%Y-%m-%d')


def parse_numeric(value, strip_commas: bool = False) -> float | None:
    """Parse numeric value, optionally stripping commas."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if strip_commas:
        value = str(value).replace(',', '')
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None


def audit_cols() -> dict:
    """Return {'created_date': ..., 'created_by': 'etl_user'}."""
    return {
        'created_date': datetime.now().isoformat(),
        'created_by': 'etl_user',
    }

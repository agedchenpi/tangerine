#!/usr/bin/env python3
"""
Pub-Sub Event Listener (Main Daemon)

This is the main entry point for the pub-sub service. It:
1. Watches specified directories for new files
2. Polls the database for pending events
3. Dispatches events to appropriate handlers
4. Manages event lifecycle (pending -> processing -> completed/failed)

Usage:
    python pubsub/listener.py [--poll-interval 5] [--watch-dir /app/data/source]
"""

import os
import sys
import json
import signal
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.db_utils import db_transaction, fetch_dict
from pubsub.watchers.file_watcher import FileWatcher
from pubsub.watchers.db_poller import DatabasePoller
from pubsub.handlers.job_handler import JobHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('pubsub.listener')


class PubSubListener:
    """
    Main pub-sub listener daemon.

    Coordinates file watching, database polling, and event handling.
    """

    def __init__(
        self,
        poll_interval: int = 5,
        watch_directories: Optional[list] = None,
        file_patterns: Optional[list] = None
    ):
        """
        Initialize the pub-sub listener.

        Args:
            poll_interval: Seconds between database polls
            watch_directories: Directories to watch for file events
            file_patterns: File patterns to watch (e.g., ['*.csv', '*.xlsx'])
        """
        self.poll_interval = poll_interval
        self.watch_directories = watch_directories or ['/app/data/source']
        self.file_patterns = file_patterns or ['*.csv', '*.xlsx', '*.json', '*.xml']

        self.job_handler = JobHandler()
        self.file_watcher: Optional[FileWatcher] = None
        self.db_poller: Optional[DatabasePoller] = None
        self._running = False

    def _create_file_event(self, file_data: Dict[str, Any]):
        """
        Create a database event for a file system event.

        Args:
            file_data: File event data from file watcher
        """
        try:
            with db_transaction() as cursor:
                cursor.execute("""
                    INSERT INTO dba.tpubsub_events (
                        event_type,
                        event_source,
                        event_data,
                        priority,
                        status,
                        created_at
                    ) VALUES (
                        'file_received',
                        %s,
                        %s,
                        5,
                        'pending',
                        CURRENT_TIMESTAMP
                    )
                """, (
                    file_data.get('file_path', ''),
                    json.dumps(file_data)
                ))

            logger.info(f"Created event for file: {file_data.get('filename')}")

        except Exception as e:
            logger.error(f"Error creating file event: {e}")

    def _handle_db_event(self, event: Dict[str, Any]):
        """
        Handle an event from the database queue.

        Args:
            event: Event dictionary from database
        """
        event_type = event.get('event_type', 'unknown')
        event_id = event.get('event_id')

        logger.info(f"Handling event {event_id}: {event_type}")

        try:
            # Parse event_data if it's a string
            event_data = event.get('event_data', {})
            if isinstance(event_data, str):
                event_data = json.loads(event_data)

            # Merge event_data into event for handlers
            full_event = {**event, 'event_data': event_data}

            success = self.job_handler.handle(full_event)

            if success:
                logger.info(f"Event {event_id} handled successfully")
            else:
                logger.warning(f"Event {event_id} handler returned failure")

        except Exception as e:
            logger.error(f"Error handling event {event_id}: {e}")
            raise

    def start(self):
        """Start the pub-sub listener."""
        logger.info("=" * 60)
        logger.info("Starting Pub-Sub Event Listener")
        logger.info("=" * 60)
        logger.info(f"Poll interval: {self.poll_interval}s")
        logger.info(f"Watch directories: {self.watch_directories}")
        logger.info(f"File patterns: {self.file_patterns}")
        logger.info("=" * 60)

        self._running = True

        # Start file watcher
        self.file_watcher = FileWatcher(
            directories=self.watch_directories,
            event_callback=self._create_file_event,
            file_patterns=self.file_patterns
        )
        self.file_watcher.start()

        # Start database poller
        self.db_poller = DatabasePoller(
            event_callback=self._handle_db_event,
            poll_interval=self.poll_interval
        )
        self.db_poller.start()

        logger.info("Pub-Sub Listener started successfully")

    def stop(self):
        """Stop the pub-sub listener."""
        logger.info("Stopping Pub-Sub Listener...")
        self._running = False

        if self.file_watcher:
            self.file_watcher.stop()

        if self.db_poller:
            self.db_poller.stop()

        logger.info("Pub-Sub Listener stopped")

    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the listener."""
        return {
            'running': self._running,
            'file_watcher': self.file_watcher.is_running() if self.file_watcher else False,
            'db_poller': self.db_poller.is_running() if self.db_poller else False,
            'watch_directories': self.watch_directories,
            'poll_interval': self.poll_interval,
            'timestamp': datetime.now().isoformat()
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Pub-Sub Event Listener')
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=int(os.getenv('PUBSUB_POLL_INTERVAL', '5')),
        help='Seconds between database polls (default: 5)'
    )
    parser.add_argument(
        '--watch-dir',
        action='append',
        dest='watch_dirs',
        default=None,
        help='Directory to watch for file events (can specify multiple)'
    )
    parser.add_argument(
        '--file-pattern',
        action='append',
        dest='file_patterns',
        default=None,
        help='File pattern to watch (can specify multiple)'
    )

    args = parser.parse_args()

    # Default watch directories
    watch_dirs = args.watch_dirs or [
        os.getenv('PUBSUB_WATCH_DIR', '/app/data/source')
    ]

    # Default file patterns
    file_patterns = args.file_patterns or ['*.csv', '*.xlsx', '*.json', '*.xml']

    listener = PubSubListener(
        poll_interval=args.poll_interval,
        watch_directories=watch_dirs,
        file_patterns=file_patterns
    )

    # Handle signals for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        listener.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        listener.start()

        # Keep running
        import time
        while listener.is_running():
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        listener.stop()


if __name__ == '__main__':
    main()

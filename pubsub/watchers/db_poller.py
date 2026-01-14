"""
Database poller for pub-sub events.

Polls the tpubsub_events table for pending events and dispatches them.
"""

import os
import json
import logging
import threading
import time
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabasePoller:
    """
    Polls database for pending pub-sub events.

    Retrieves events from tpubsub_events with status='pending' and
    dispatches them to registered handlers.
    """

    def __init__(
        self,
        event_callback: Callable[[Dict[str, Any]], None],
        poll_interval: int = 5,
        batch_size: int = 10
    ):
        """
        Initialize database poller.

        Args:
            event_callback: Function to call for each pending event
            poll_interval: Seconds between polls (default: 5)
            batch_size: Max events to fetch per poll (default: 10)
        """
        self.event_callback = event_callback
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _get_db_connection(self):
        """Get database connection using common db_utils."""
        from common.db_utils import get_connection
        return get_connection()

    def _fetch_pending_events(self) -> List[Dict[str, Any]]:
        """Fetch pending events from database."""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        event_id,
                        event_type,
                        event_source,
                        event_data,
                        status,
                        priority,
                        created_at,
                        retry_count,
                        max_retries
                    FROM dba.tpubsub_events
                    WHERE status = 'pending'
                    AND retry_count < max_retries
                    ORDER BY priority ASC, created_at ASC
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                """, (self.batch_size,))

                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                events = []
                for row in rows:
                    event = dict(zip(columns, row))
                    # Convert datetime to string for JSON serialization
                    if event.get('created_at'):
                        event['created_at'] = event['created_at'].isoformat()
                    events.append(event)

                return events

        except Exception as e:
            logger.error(f"Error fetching pending events: {e}")
            return []

    def _mark_event_processing(self, event_id: int):
        """Mark event as processing."""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE dba.tpubsub_events
                    SET status = 'processing', processed_at = CURRENT_TIMESTAMP
                    WHERE event_id = %s
                """, (event_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error marking event {event_id} as processing: {e}")

    def _mark_event_complete(self, event_id: int, success: bool, error_message: Optional[str] = None):
        """Mark event as completed or failed."""
        try:
            status = 'completed' if success else 'failed'
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                if success:
                    cursor.execute("""
                        UPDATE dba.tpubsub_events
                        SET status = %s, completed_at = CURRENT_TIMESTAMP
                        WHERE event_id = %s
                    """, (status, event_id))
                else:
                    cursor.execute("""
                        UPDATE dba.tpubsub_events
                        SET status = %s, completed_at = CURRENT_TIMESTAMP,
                            error_message = %s, retry_count = retry_count + 1
                        WHERE event_id = %s
                    """, (status, error_message, event_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Error marking event {event_id} as {status}: {e}")

    def _poll_loop(self):
        """Main polling loop."""
        logger.info(f"Database poller started (interval: {self.poll_interval}s)")

        while self._running:
            try:
                events = self._fetch_pending_events()

                for event in events:
                    event_id = event['event_id']
                    logger.info(f"Processing event {event_id}: {event['event_type']}")

                    self._mark_event_processing(event_id)

                    try:
                        self.event_callback(event)
                        self._mark_event_complete(event_id, success=True)
                        logger.info(f"Event {event_id} completed successfully")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Event {event_id} failed: {error_msg}")
                        self._mark_event_complete(event_id, success=False, error_message=error_msg)

            except Exception as e:
                logger.error(f"Error in poll loop: {e}")

            # Sleep before next poll
            time.sleep(self.poll_interval)

        logger.info("Database poller stopped")

    def start(self):
        """Start the polling thread."""
        if self._running:
            logger.warning("Poller already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Database poller thread started")

    def stop(self):
        """Stop the polling thread."""
        if not self._running:
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=self.poll_interval + 1)
            self._thread = None
        logger.info("Database poller stopped")

    def is_running(self) -> bool:
        """Check if poller is running."""
        return self._running


if __name__ == '__main__':
    # Test the database poller
    logging.basicConfig(level=logging.INFO)

    def test_callback(event):
        print(f"Event received: {json.dumps(event, indent=2, default=str)}")

    poller = DatabasePoller(
        event_callback=test_callback,
        poll_interval=5
    )

    try:
        poller.start()
        print("Polling for events. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        poller.stop()
        print("Poller stopped.")

"""
General job handler for pub-sub events.

Handles various event types and triggers appropriate jobs.
"""

import os
import logging
import subprocess
from typing import Dict, Any, List, Optional

from .base_handler import BaseHandler

logger = logging.getLogger(__name__)


class JobHandler(BaseHandler):
    """
    General purpose job handler.

    Routes events to appropriate handlers based on event type.
    """

    def __init__(self):
        super().__init__("JobHandler")

    def _get_matching_subscribers(self, event_type: str, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get subscribers that match this event.

        Args:
            event_type: Type of event
            event_data: Event data dictionary

        Returns:
            List of matching subscriber configurations
        """
        from common.db_utils import fetch_dict

        query = """
            SELECT
                s.subscriber_id,
                s.subscriber_name,
                s.event_filter,
                s.job_type,
                s.config_id,
                s.script_path
            FROM dba.tpubsub_subscribers s
            WHERE s.is_active = TRUE
            AND s.event_type = %s
        """
        return fetch_dict(query, (event_type,)) or []

    def _trigger_job(self, subscriber: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """
        Trigger the job defined by the subscriber.

        Args:
            subscriber: Subscriber configuration
            event_data: Original event data

        Returns:
            True if job triggered successfully
        """
        job_type = subscriber['job_type']
        config_id = subscriber.get('config_id')
        script_path = subscriber.get('script_path')

        try:
            cmd = None

            if job_type == 'import' and config_id:
                cmd = ['python', 'etl/jobs/generic_import.py', '--config-id', str(config_id)]
                logger.info(f"Triggering import job with config_id={config_id}")

            elif job_type == 'inbox_processor' and config_id:
                cmd = ['python', 'etl/jobs/run_gmail_inbox_processor.py', '--config-id', str(config_id)]
                logger.info(f"Triggering inbox processor with config_id={config_id}")

            elif job_type == 'report' and config_id:
                cmd = ['python', 'etl/jobs/run_report_generator.py', '--report-id', str(config_id)]
                logger.info(f"Triggering report with report_id={config_id}")

            elif job_type == 'custom' and script_path:
                cmd = ['python', script_path]
                logger.info(f"Triggering custom script: {script_path}")

            if not cmd:
                logger.error(f"Invalid job configuration: job_type={job_type}, config_id={config_id}")
                return False

            # Run the job
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd='/app'
            )

            if result.returncode == 0:
                logger.info(f"Job completed successfully: {' '.join(cmd)}")
                return True
            else:
                logger.error(f"Job failed with code {result.returncode}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Job timed out: {job_type}")
            return False
        except Exception as e:
            logger.error(f"Error triggering job: {e}")
            return False

    def _update_subscriber_stats(self, subscriber_id: int):
        """Update subscriber trigger statistics."""
        from common.db_utils import db_transaction

        try:
            with db_transaction() as cursor:
                cursor.execute("""
                    UPDATE dba.tpubsub_subscribers
                    SET last_triggered_at = CURRENT_TIMESTAMP,
                        trigger_count = trigger_count + 1
                    WHERE subscriber_id = %s
                """, (subscriber_id,))
        except Exception as e:
            logger.error(f"Error updating subscriber stats: {e}")

    def handle(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle an event by finding matching subscribers and triggering jobs.

        Args:
            event_data: Event data dictionary (from database or file watcher)

        Returns:
            True if all matching jobs triggered successfully
        """
        event_type = event_data.get('event_type', 'unknown')
        self.log_event(event_data, f"Processing event type: {event_type}")

        subscribers = self._get_matching_subscribers(event_type, event_data)

        if not subscribers:
            self.log_event(event_data, "No matching subscribers found")
            return True

        success = True
        for sub in subscribers:
            self.log_event(event_data, f"Triggering subscriber: {sub['subscriber_name']}")

            if self._trigger_job(sub, event_data):
                self._update_subscriber_stats(sub['subscriber_id'])
            else:
                success = False
                self.log_event(event_data, f"Failed to trigger: {sub['subscriber_name']}")

        return success

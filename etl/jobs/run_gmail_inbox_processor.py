"""
Gmail Inbox Processor - Downloads attachments from Gmail based on inbox configs.

Scans Gmail inbox for emails matching configured rules (subject pattern,
sender pattern, attachment pattern) and downloads attachments to the
specified target directory with date prefixes.

Usage:
    python etl/jobs/run_gmail_inbox_processor.py [--config-id N] [--dry-run]

Examples:
    # Process all active inbox configs
    python etl/jobs/run_gmail_inbox_processor.py

    # Process specific config with dry run
    python etl/jobs/run_gmail_inbox_processor.py --config-id 1 --dry-run
"""

import argparse
import fnmatch
import re
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

from common.db_utils import fetch_dict, db_transaction
from common.gmail_client import GmailClient
from common.logging_utils import ETLLogger
from etl.base.etl_job import BaseETLJob


class InboxProcessorJob(BaseETLJob):
    """
    Process Gmail inbox according to configured rules.

    Lifecycle:
        1. setup() - Load inbox configs from database, initialize Gmail client
        2. extract() - Scan inbox, match emails against rules
        3. transform() - Prepare download tasks with date-prefixed filenames
        4. load() - Download attachments to target directories, apply Gmail labels
        5. cleanup() - Update last_run_at timestamps
    """

    def __init__(
        self,
        config_id: Optional[int] = None,
        dry_run: bool = False,
        run_uuid: Optional[str] = None
    ):
        """
        Initialize inbox processor job.

        Args:
            config_id: Optional specific config ID to process (None = all active)
            dry_run: If True, scan inbox but don't download or modify labels
            run_uuid: Optional run UUID for tracing
        """
        super().__init__(
            run_date=date.today(),
            dataset_type='InboxProcessor',
            data_source='Gmail',
            dry_run=dry_run,
            run_uuid=run_uuid
        )
        self.config_id = config_id
        self.gmail: Optional[GmailClient] = None
        self.configs: List[Dict[str, Any]] = []
        self.matched_emails: List[Dict[str, Any]] = []
        self.download_tasks: List[Dict[str, Any]] = []
        self.downloaded_files: List[Path] = []
        self.processed_message_ids: List[str] = set()
        self.unmatched_message_ids: List[str] = set()

    def setup(self):
        """Load configurations and initialize Gmail client."""
        self.logger.info("Initializing Gmail client", extra={'stepcounter': 'setup'})
        self.gmail = GmailClient()

        self.configs = self._load_inbox_configs()
        self.logger.info(
            f"Loaded {len(self.configs)} inbox configuration(s)",
            extra={
                'stepcounter': 'setup',
                'metadata': {'config_count': len(self.configs)}
            }
        )

    def _load_inbox_configs(self) -> List[Dict[str, Any]]:
        """Load active inbox configurations from database."""
        query = """
            SELECT
                ic.*,
                imp.config_name as linked_import_name
            FROM dba.tinboxconfig ic
            LEFT JOIN dba.timportconfig imp ON ic.linked_import_config_id = imp.config_id
            WHERE ic.is_active = TRUE
        """
        params = ()

        if self.config_id:
            query = query.replace('WHERE ic.is_active = TRUE', 'WHERE ic.is_active = TRUE AND ic.inbox_config_id = %s')
            params = (self.config_id,)

        query += " ORDER BY ic.inbox_config_id"
        return fetch_dict(query, params) or []

    def extract(self) -> List[Dict[str, Any]]:
        """
        Scan Gmail inbox and match emails against rules.

        Returns:
            List of matched email dictionaries with config and attachment info
        """
        if not self.configs:
            self.logger.warning("No active inbox configurations found")
            return []

        # Get all unread emails from inbox
        all_emails = self.gmail.get_unread_emails()
        self.logger.info(f"Found {len(all_emails)} unread emails in inbox")

        matched = []
        all_message_ids = {e['id'] for e in all_emails}

        for config in self.configs:
            config_matches = self._match_emails_for_config(config, all_emails)
            matched.extend(config_matches)

            # Track which messages matched
            for m in config_matches:
                self.processed_message_ids.add(m['message_id'])

        # Track unmatched messages
        self.unmatched_message_ids = all_message_ids - self.processed_message_ids

        self.matched_emails = matched
        return matched

    def _match_emails_for_config(
        self,
        config: Dict[str, Any],
        emails: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Match emails against a single inbox config.

        Args:
            config: Inbox configuration dictionary
            emails: List of email dictionaries to check

        Returns:
            List of matched emails with config and attachment info
        """
        matches = []
        subject_pattern = config.get('subject_pattern')
        sender_pattern = config.get('sender_pattern')
        attachment_pattern = config['attachment_pattern']

        for email_data in emails:
            # Check subject pattern
            if subject_pattern:
                try:
                    if not re.search(subject_pattern, email_data['subject'], re.IGNORECASE):
                        continue
                except re.error as e:
                    self.logger.warning(f"Invalid subject regex '{subject_pattern}': {e}")
                    continue

            # Check sender pattern
            if sender_pattern:
                try:
                    if not re.search(sender_pattern, email_data['sender'], re.IGNORECASE):
                        continue
                except re.error as e:
                    self.logger.warning(f"Invalid sender regex '{sender_pattern}': {e}")
                    continue

            # Check attachments
            attachments = self.gmail.get_attachments(email_data['id'])
            matching_attachments = []

            for att in attachments:
                # Use fnmatch for glob patterns, fall back to regex
                filename = att['filename']
                if '*' in attachment_pattern or '?' in attachment_pattern:
                    # Glob pattern
                    if fnmatch.fnmatch(filename, attachment_pattern):
                        matching_attachments.append(att)
                else:
                    # Regex pattern
                    try:
                        if re.search(attachment_pattern, filename, re.IGNORECASE):
                            matching_attachments.append(att)
                    except re.error:
                        # Treat as literal match if invalid regex
                        if attachment_pattern.lower() in filename.lower():
                            matching_attachments.append(att)

            if matching_attachments:
                # Get email date for filename prefix
                email_date = self.gmail.get_email_date(email_data['id']) or datetime.now()

                matches.append({
                    'message_id': email_data['id'],
                    'subject': email_data['subject'],
                    'sender': email_data['sender'],
                    'email_date': email_date,
                    'attachments': matching_attachments,
                    'config': config
                })

                self.logger.info(
                    f"Matched email: '{email_data['subject']}' with {len(matching_attachments)} attachment(s)",
                    extra={
                        'metadata': {
                            'config_name': config['config_name'],
                            'message_id': email_data['id']
                        }
                    }
                )

        return matches

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare download tasks with date-prefixed filenames.

        Args:
            data: List of matched email dictionaries

        Returns:
            List of download task dictionaries
        """
        tasks = []

        for email_match in data:
            config = email_match['config']
            email_date = email_match['email_date']

            # Convert date format from Java-style to Python strftime
            date_format = self._convert_date_format(config.get('date_prefix_format', 'yyyyMMdd'))
            date_prefix = email_date.strftime(date_format)

            for attachment in email_match['attachments']:
                target_filename = f"{date_prefix}_{attachment['filename']}"

                tasks.append({
                    'message_id': email_match['message_id'],
                    'attachment_id': attachment['id'],
                    'original_filename': attachment['filename'],
                    'target_filename': target_filename,
                    'target_directory': config['target_directory'],
                    'config': config,
                    'email_subject': email_match['subject'],
                    'email_sender': email_match['sender']
                })

            # Add .eml file task if configured
            if config.get('save_eml'):
                eml_filename = f"{date_prefix}_{email_match['message_id']}.eml"
                tasks.append({
                    'message_id': email_match['message_id'],
                    'attachment_id': None,  # Special case for .eml
                    'original_filename': f"{email_match['message_id']}.eml",
                    'target_filename': eml_filename,
                    'target_directory': config['target_directory'],
                    'config': config,
                    'is_eml': True,
                    'email_subject': email_match['subject'],
                    'email_sender': email_match['sender']
                })

        self.download_tasks = tasks
        return tasks

    def _convert_date_format(self, java_format: str) -> str:
        """
        Convert Java-style date format to Python strftime format.

        Args:
            java_format: Java SimpleDateFormat string (e.g., 'yyyyMMdd')

        Returns:
            Python strftime format string (e.g., '%Y%m%d')
        """
        conversions = {
            'yyyy': '%Y',
            'yy': '%y',
            'MM': '%m',
            'dd': '%d',
            'HH': '%H',
            'mm': '%M',
            'ss': '%S',
            'SSS': '%f',
            'T': 'T'
        }

        result = java_format
        for java, python in conversions.items():
            result = result.replace(java, python)

        return result

    def load(self, data: List[Dict[str, Any]]):
        """
        Download attachments and update email labels.

        Args:
            data: List of download task dictionaries
        """
        for task in data:
            try:
                target_dir = Path(task['target_directory'])

                if task.get('is_eml'):
                    # Download raw email as .eml
                    raw_email = self.gmail.get_email_raw(task['message_id'])
                    target_dir.mkdir(parents=True, exist_ok=True)
                    file_path = target_dir / task['target_filename']
                    with open(file_path, 'wb') as f:
                        f.write(raw_email)
                else:
                    # Download attachment
                    file_path = self.gmail.download_attachment(
                        task['message_id'],
                        task['attachment_id'],
                        task['target_filename'],
                        target_dir
                    )

                self.downloaded_files.append(file_path)
                self.logger.info(
                    f"Downloaded: {task['target_filename']}",
                    extra={
                        'metadata': {
                            'file_path': str(file_path),
                            'config_name': task['config']['config_name']
                        }
                    }
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to download {task['original_filename']}: {e}",
                    extra={'metadata': {'message_id': task['message_id']}}
                )

        # Apply labels to processed emails
        processed_configs: Dict[str, Dict] = {}  # message_id -> config
        for task in data:
            processed_configs[task['message_id']] = task['config']

        for message_id, config in processed_configs.items():
            try:
                if config.get('mark_processed', True):
                    # Apply processed label
                    self.gmail.apply_label(message_id, config.get('processed_label', 'Processed'))
                    # Remove from inbox
                    self.gmail.remove_label(message_id, 'INBOX')
                    # Mark as read
                    self.gmail.mark_as_read(message_id)

            except Exception as e:
                self.logger.error(f"Failed to update labels for message {message_id}: {e}")

        # Apply error label to unmatched emails
        for message_id in self.unmatched_message_ids:
            try:
                # Use first config's error label, or default
                error_label = self.configs[0].get('error_label', 'ErrorFolder') if self.configs else 'ErrorFolder'
                self.gmail.apply_label(message_id, error_label)
                self.gmail.remove_label(message_id, 'INBOX')
                self.gmail.mark_as_read(message_id)
            except Exception as e:
                self.logger.warning(f"Failed to apply error label to message {message_id}: {e}")

        self.records_loaded = len(self.downloaded_files)

    def cleanup(self):
        """Update configuration timestamps."""
        processed_config_ids = set()
        for task in self.download_tasks:
            processed_config_ids.add(task['config']['inbox_config_id'])

        for config_id in processed_config_ids:
            try:
                with db_transaction() as cursor:
                    cursor.execute(
                        "UPDATE dba.tinboxconfig SET last_run_at = %s WHERE inbox_config_id = %s",
                        (datetime.now(), config_id)
                    )
            except Exception as e:
                self.logger.error(f"Failed to update last_run_at for config {config_id}: {e}")

        self.logger.info(
            f"Inbox processing complete",
            extra={
                'metadata': {
                    'files_downloaded': len(self.downloaded_files),
                    'emails_processed': len(self.processed_message_ids),
                    'emails_unmatched': len(self.unmatched_message_ids)
                }
            }
        )


def main():
    """CLI entry point for inbox processor."""
    parser = argparse.ArgumentParser(
        description='Process Gmail inbox according to configured rules'
    )
    parser.add_argument(
        '--config-id',
        type=int,
        help='Specific inbox config ID to process (default: all active)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Scan inbox but do not download files or modify labels'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Run date in YYYY-MM-DD format (default: today)'
    )

    args = parser.parse_args()

    job = InboxProcessorJob(
        config_id=args.config_id,
        dry_run=args.dry_run
    )

    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

"""
Gmail API client with OAuth2 authentication.

Handles:
- OAuth2 token management (refresh, storage)
- Email scanning and filtering
- Attachment downloading
- Label management
- Email sending for reports

Requires:
- credentials.json: OAuth2 client credentials from Google Cloud Console
- token.json: Auto-generated/refreshed access token

Environment variables:
- GMAIL_CREDENTIALS_PATH: Path to credentials.json (default: /app/secrets/credentials.json)
- GMAIL_TOKEN_PATH: Path to token.json (default: /app/secrets/token.json)
"""

import os
import base64
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]


class GmailClient:
    """
    Gmail API wrapper with OAuth2 authentication.

    Usage:
        client = GmailClient()

        # Get unread emails
        emails = client.get_unread_emails()

        # Download attachments
        for email in emails:
            attachments = client.get_attachments(email['id'])
            for att in attachments:
                client.download_attachment(email['id'], att['id'], att['filename'], Path('/tmp'))

        # Send email
        client.send_email(
            to=['recipient@example.com'],
            subject='Report',
            body_html='<h1>Daily Report</h1>',
            attachments=[Path('/tmp/report.csv')]
        )
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None
    ):
        """
        Initialize Gmail client with OAuth2 authentication.

        Args:
            credentials_path: Path to OAuth2 credentials.json file
            token_path: Path to token.json file (created/refreshed automatically)
        """
        self.credentials_path = credentials_path or os.getenv(
            'GMAIL_CREDENTIALS_PATH',
            '/app/secrets/credentials.json'
        )
        self.token_path = token_path or os.getenv(
            'GMAIL_TOKEN_PATH',
            '/app/secrets/token.json'
        )
        self.service = None
        self._label_cache: Dict[str, str] = {}  # name -> id mapping
        self._authenticate()

    def _authenticate(self):
        """
        Authenticate with Gmail API using OAuth2.

        Handles token refresh and initial authorization flow.
        """
        creds = None

        # Load existing token if available
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")

        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed OAuth2 token")
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials not found at {self.credentials_path}. "
                        "Please download OAuth2 credentials from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Obtained new OAuth2 token via authorization flow")

            # Save the credentials for future use
            token_dir = os.path.dirname(self.token_path)
            if token_dir and not os.path.exists(token_dir):
                os.makedirs(token_dir, exist_ok=True)

            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API service initialized")

    def get_unread_emails(
        self,
        query: str = '',
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch unread emails matching optional query.

        Args:
            query: Gmail search query (e.g., 'from:sender@example.com')
            max_results: Maximum number of emails to return

        Returns:
            List of email dictionaries with id, subject, sender, date, snippet
        """
        try:
            # Build search query
            full_query = 'is:unread'
            if query:
                full_query += f' {query}'

            results = self.service.users().messages().list(
                userId='me',
                q=full_query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg_ref in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=msg_ref['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()

                headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}

                emails.append({
                    'id': msg['id'],
                    'thread_id': msg['threadId'],
                    'subject': headers.get('Subject', ''),
                    'sender': headers.get('From', ''),
                    'date': headers.get('Date', ''),
                    'snippet': msg.get('snippet', ''),
                    'label_ids': msg.get('labelIds', [])
                })

            logger.info(f"Retrieved {len(emails)} unread emails")
            return emails

        except HttpError as e:
            logger.error(f"Gmail API error fetching emails: {e}")
            raise

    def get_email_raw(self, message_id: str) -> bytes:
        """
        Get raw email content for saving as .eml file.

        Args:
            message_id: Gmail message ID

        Returns:
            Raw email bytes
        """
        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='raw'
            ).execute()

            return base64.urlsafe_b64decode(msg['raw'])

        except HttpError as e:
            logger.error(f"Gmail API error fetching raw email: {e}")
            raise

    def get_attachments(self, message_id: str) -> List[Dict[str, Any]]:
        """
        Get all attachments metadata from an email.

        Args:
            message_id: Gmail message ID

        Returns:
            List of attachment dictionaries with id, filename, mime_type, size
        """
        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            attachments = []
            parts = msg.get('payload', {}).get('parts', [])

            # Handle nested parts (for multipart emails)
            def extract_attachments(parts_list):
                for part in parts_list:
                    filename = part.get('filename', '')
                    if filename:
                        body = part.get('body', {})
                        attachments.append({
                            'id': body.get('attachmentId', ''),
                            'filename': filename,
                            'mime_type': part.get('mimeType', ''),
                            'size': body.get('size', 0)
                        })

                    # Check nested parts
                    nested_parts = part.get('parts', [])
                    if nested_parts:
                        extract_attachments(nested_parts)

            extract_attachments(parts)

            logger.debug(f"Found {len(attachments)} attachments in message {message_id}")
            return attachments

        except HttpError as e:
            logger.error(f"Gmail API error fetching attachments: {e}")
            raise

    def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        filename: str,
        target_dir: Path
    ) -> Path:
        """
        Download an attachment to the specified directory.

        Args:
            message_id: Gmail message ID
            attachment_id: Attachment ID from get_attachments()
            filename: Target filename
            target_dir: Directory to save the file

        Returns:
            Path to the downloaded file
        """
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()

            file_data = base64.urlsafe_b64decode(attachment['data'])

            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)

            file_path = target_dir / filename
            with open(file_path, 'wb') as f:
                f.write(file_data)

            logger.info(f"Downloaded attachment to {file_path}")
            return file_path

        except HttpError as e:
            logger.error(f"Gmail API error downloading attachment: {e}")
            raise

    def _get_or_create_label(self, label_name: str) -> str:
        """
        Get or create a Gmail label by name.

        Args:
            label_name: Label name to find or create

        Returns:
            Label ID
        """
        # Check cache first
        if label_name in self._label_cache:
            return self._label_cache[label_name]

        try:
            # List all labels to find existing one
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            for label in labels:
                self._label_cache[label['name']] = label['id']
                if label['name'] == label_name:
                    return label['id']

            # Label not found, create it
            label_body = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }

            created = self.service.users().labels().create(
                userId='me',
                body=label_body
            ).execute()

            self._label_cache[created['name']] = created['id']
            logger.info(f"Created Gmail label: {label_name}")
            return created['id']

        except HttpError as e:
            logger.error(f"Gmail API error with label {label_name}: {e}")
            raise

    def apply_label(self, message_id: str, label_name: str):
        """
        Apply a label to an email (creates label if needed).

        Args:
            message_id: Gmail message ID
            label_name: Label name to apply
        """
        try:
            label_id = self._get_or_create_label(label_name)

            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()

            logger.debug(f"Applied label '{label_name}' to message {message_id}")

        except HttpError as e:
            logger.error(f"Gmail API error applying label: {e}")
            raise

    def remove_label(self, message_id: str, label_name: str):
        """
        Remove a label from an email.

        Args:
            message_id: Gmail message ID
            label_name: Label name to remove (e.g., 'INBOX', 'UNREAD')
        """
        try:
            # For system labels, use the name directly
            if label_name.upper() in ['INBOX', 'UNREAD', 'STARRED', 'IMPORTANT', 'SPAM', 'TRASH']:
                label_id = label_name.upper()
            else:
                label_id = self._get_or_create_label(label_name)

            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': [label_id]}
            ).execute()

            logger.debug(f"Removed label '{label_name}' from message {message_id}")

        except HttpError as e:
            logger.error(f"Gmail API error removing label: {e}")
            raise

    def mark_as_read(self, message_id: str):
        """
        Mark an email as read by removing UNREAD label.

        Args:
            message_id: Gmail message ID
        """
        self.remove_label(message_id, 'UNREAD')

    def send_email(
        self,
        to: List[str],
        subject: str,
        body_html: str,
        attachments: Optional[List[Path]] = None,
        cc: Optional[List[str]] = None,
        from_name: Optional[str] = None
    ):
        """
        Send an email with optional attachments.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body_html: HTML content for email body
            attachments: Optional list of file paths to attach
            cc: Optional list of CC email addresses
            from_name: Optional display name for sender
        """
        try:
            # Create message container
            message = MIMEMultipart()
            message['To'] = ', '.join(to)
            message['Subject'] = subject

            if cc:
                message['Cc'] = ', '.join(cc)

            # Attach HTML body
            message.attach(MIMEText(body_html, 'html'))

            # Attach files
            if attachments:
                for file_path in attachments:
                    if not file_path.exists():
                        logger.warning(f"Attachment not found: {file_path}")
                        continue

                    with open(file_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())

                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{file_path.name}"'
                    )
                    message.attach(part)

            # Encode and send
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            recipients = to + (cc or [])
            logger.info(f"Sent email to {', '.join(recipients)}: {subject}")

        except HttpError as e:
            logger.error(f"Gmail API error sending email: {e}")
            raise

    def get_email_date(self, message_id: str) -> Optional[datetime]:
        """
        Get the sent date of an email.

        Args:
            message_id: Gmail message ID

        Returns:
            datetime of when the email was sent, or None if not found
        """
        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['Date']
            ).execute()

            headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
            date_str = headers.get('Date', '')

            if date_str:
                # Parse email date format
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(date_str)

            return None

        except Exception as e:
            logger.warning(f"Failed to parse email date: {e}")
            return None


def test_connection() -> bool:
    """
    Test Gmail API connection.

    Returns:
        True if connection is successful, False otherwise
    """
    try:
        client = GmailClient()
        # Try to list labels as a simple connection test
        client.service.users().labels().list(userId='me').execute()
        logger.info("Gmail API connection test successful")
        return True
    except Exception as e:
        logger.error(f"Gmail API connection test failed: {e}")
        return False


if __name__ == '__main__':
    # Test connection when run directly
    import sys
    logging.basicConfig(level=logging.INFO)

    success = test_connection()
    sys.exit(0 if success else 1)

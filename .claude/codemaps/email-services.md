# Email Services Codemap

## Purpose

Gmail integration for:
1. **Inbox Processor**: Download email attachments based on rules
2. **Report Generator**: Send SQL-based email reports
3. **Scheduler**: Database-driven cron management

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Gmail API (OAuth2)                          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   common/gmail_client.py                         │
│  GmailClient class with OAuth2 authentication                    │
│  - get_unread_emails()                                          │
│  - get_attachments() / download_attachment()                    │
│  - send_email() with HTML + attachments                         │
│  - apply_label() / remove_label() / mark_as_read()              │
└─────────────────────────────────────────────────────────────────┘
            │                               │
            ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│  run_gmail_inbox_processor │    │  run_report_generator    │
│  Downloads attachments    │    │  Executes SQL templates  │
│  Applies Gmail labels     │    │  Sends HTML + CSV/Excel  │
└──────────────────────────┘    └──────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `common/gmail_client.py` | OAuth2 Gmail API wrapper (545 LOC) |
| `etl/jobs/run_gmail_inbox_processor.py` | Download attachments job |
| `etl/jobs/run_report_generator.py` | SQL-based email reports |
| `etl/jobs/generate_crontab.py` | Generate crontab from DB |
| `admin/services/inbox_config_service.py` | Inbox config CRUD |
| `admin/services/report_manager_service.py` | Report config CRUD |
| `admin/services/scheduler_service.py` | Scheduler config CRUD |

## OAuth2 Authentication

```python
# Credentials stored in secrets/ (gitignored)
GMAIL_CREDENTIALS_PATH = '/app/secrets/credentials.json'  # OAuth client ID/secret
GMAIL_TOKEN_PATH = '/app/secrets/token.json'              # Access/refresh tokens

# Scopes required
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]
```

Token auto-refreshes when expired. First run requires manual OAuth consent flow.

## GmailClient API

```python
from common.gmail_client import GmailClient

client = GmailClient()

# Read inbox
emails = client.get_unread_emails(query='from:reports@company.com')

# Download attachments
for email in emails:
    attachments = client.get_attachments(email['id'])
    for att in attachments:
        client.download_attachment(
            message_id=email['id'],
            attachment_id=att['id'],
            filename=att['filename'],
            target_dir=Path('/app/data/source/inbox')
        )
    client.mark_as_read(email['id'])
    client.apply_label(email['id'], 'Tangerine/Processed')

# Send email
client.send_email(
    to=['recipient@example.com'],
    subject='Daily Report',
    body_html='<h1>Report</h1><p>Data attached.</p>',
    attachments=[Path('/tmp/report.csv')]
)
```

## Inbox Processor (dba.tinboxconfig)

Configuration fields:
- `subject_pattern`: Regex to match email subject
- `sender_pattern`: Regex to match sender address
- `attachment_pattern`: Glob pattern for attachment filenames
- `target_directory`: Where to save attachments
- `apply_label`: Gmail label to apply after processing
- `save_eml`: Whether to save raw .eml file
- `linked_import_config_id`: Optional FK to auto-trigger import

Flow:
```
1. Scan unread emails
2. Match against subject_pattern, sender_pattern
3. Filter attachments by attachment_pattern
4. Download to target_directory with date prefix
5. Optionally save .eml file
6. Apply Gmail label
7. Mark as read
8. Emit 'email_received' event
9. If linked_import_config_id set, trigger import
```

## Report Generator (dba.treportmanager)

Configuration fields:
- `recipients`: Comma-separated email addresses
- `subject_template`: Email subject (supports date placeholders)
- `body_template`: HTML body with `{{SQL:query}}` syntax
- `output_format`: HTML, CSV, or Excel
- `sql_query`: Main data query

Template syntax:
```html
<h1>Daily Sales Report</h1>
<p>Generated: {{date}}</p>

{{SQL:SELECT date, amount FROM sales WHERE date = CURRENT_DATE}}

<p>Total records: {{count}}</p>
```

Flow:
```
1. Load report config
2. Execute SQL queries in template
3. Render HTML tables inline
4. Generate CSV/Excel attachment if configured
5. Send via GmailClient.send_email()
6. Emit 'report_sent' event
```

## Scheduler (dba.tscheduler)

Configuration fields:
- `job_type`: import, inbox_processor, report, custom
- `config_id`: FK to relevant config table
- `cron_minute`, `cron_hour`, `cron_day`, `cron_month`, `cron_dow`
- `is_active`: Enable/disable

Generate crontab:
```bash
# Preview
docker compose exec tangerine python etl/jobs/generate_crontab.py --preview

# Apply to system crontab
docker compose exec tangerine python etl/jobs/generate_crontab.py --apply
```

## Running Email Jobs

```bash
# Process Gmail inbox
docker compose exec tangerine python etl/jobs/run_gmail_inbox_processor.py --config-id 1

# Generate and send report
docker compose exec tangerine python etl/jobs/run_report_generator.py --report-id 1

# Dry run (preview without sending)
docker compose exec tangerine python etl/jobs/run_report_generator.py --report-id 1 --dry-run

# Test Gmail connection
docker compose exec tangerine python -c "from common.gmail_client import test_connection; print(test_connection())"
```

## Error Handling

- OAuth token refresh errors: Re-authenticate by deleting token.json
- API rate limits: Built-in backoff in google-api-python-client
- Attachment download failures: Logged but don't stop processing
- Label creation: Auto-creates labels if they don't exist

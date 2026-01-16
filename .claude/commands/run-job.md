---
name: run-job
description: Execute ETL jobs (import, inbox processor, report generator)
---

# Run Job Command

Execute Tangerine ETL jobs with proper parameters.

## Usage

Parse arguments to determine job type and parameters:

| Job Type | Arguments | Description |
|----------|-----------|-------------|
| `import` | `{config_id} [--dry-run] [--date YYYY-MM-DD]` | Run generic file import |
| `inbox` | `{config_id} [--dry-run]` | Process Gmail inbox |
| `report` | `{report_id} [--dry-run]` | Generate and send report |
| `crontab` | `[--preview] [--apply]` | Generate crontab from DB |

## Commands

### Generic Import
```bash
# Standard import
docker compose exec tangerine python etl/jobs/generic_import.py --config-id {config_id}

# Dry run (validate without DB writes)
docker compose exec tangerine python etl/jobs/generic_import.py --config-id {config_id} --dry-run

# With specific date
docker compose exec tangerine python etl/jobs/generic_import.py --config-id {config_id} --date 2026-01-15
```

### Gmail Inbox Processor
```bash
# Process inbox and download attachments
docker compose exec tangerine python etl/jobs/run_gmail_inbox_processor.py --config-id {config_id}

# Dry run (check without downloading)
docker compose exec tangerine python etl/jobs/run_gmail_inbox_processor.py --config-id {config_id} --dry-run
```

### Report Generator
```bash
# Generate and send report
docker compose exec tangerine python etl/jobs/run_report_generator.py --report-id {report_id}

# Preview without sending
docker compose exec tangerine python etl/jobs/run_report_generator.py --report-id {report_id} --dry-run
```

### Crontab Generator
```bash
# Preview crontab entries
docker compose exec tangerine python etl/jobs/generate_crontab.py --preview

# Apply to system crontab
docker compose exec tangerine python etl/jobs/generate_crontab.py --apply
```

## Examples

- `/run-job import 1` → Run import config #1
- `/run-job import 1 --dry-run` → Validate import without DB writes
- `/run-job inbox 2` → Process Gmail inbox config #2
- `/run-job report 3 --dry-run` → Preview report #3
- `/run-job crontab --preview` → Show what crontab would look like

## Notes

- Always use `--dry-run` first when testing new configurations
- Import jobs emit `import_complete` events to pub/sub
- Report jobs emit `report_sent` events to pub/sub
- Inbox processor emits `email_received` events to pub/sub
- Check logs with `/logs tangerine` if job fails

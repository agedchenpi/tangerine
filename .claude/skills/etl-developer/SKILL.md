---
name: etl-developer
description: ETL job development patterns for Tangerine - import jobs, extractors, schema management, file processing
---

# ETL Developer Guidelines

## Overview

Tangerine uses a config-driven ETL framework. Most imports use `generic_import.py` with database configuration rather than custom job files.

## Architecture: Individual Script Pattern

All API-based data imports follow a **two-stage pattern**:

1. **Individual Script** (unique per endpoint) — API fetch + transform + save JSON
2. **Import** (universal) — `generic_import.py` via `import_utils.run_generic_import()`

```
etl/
├── base/
│   ├── etl_job.py                              # Base ETL job class
│   ├── api_client.py                           # Base API client
│   └── import_utils.py                         # Shared save/import plumbing
├── clients/                                    # API clients (reusable, no transforms)
│   ├── newyorkfed_client.py
│   └── bankofengland_client.py
├── jobs/
│   ├── generic_import.py                       # Universal config-driven file import
│   ├── run_newyorkfed_reference_rates.py       # One script per endpoint
│   ├── run_newyorkfed_soma_holdings.py
│   ├── run_newyorkfed_repo.py
│   ├── run_newyorkfed_reverserepo.py
│   ├── run_newyorkfed_agency_mbs.py
│   ├── run_newyorkfed_fx_swaps.py
│   ├── run_newyorkfed_counterparties.py
│   ├── run_newyorkfed_securities_lending.py
│   ├── run_newyorkfed_guide_sheets.py
│   ├── run_newyorkfed_treasury.py
│   ├── run_newyorkfed_pd_statistics.py
│   ├── run_newyorkfed_market_share.py
│   ├── run_bankofengland_sonia_rates.py
│   ├── run_gmail_inbox_processor.py            # Email attachment processing
│   ├── run_report_generator.py                 # SQL-based report generation
│   └── generate_crontab.py                     # Scheduler cron generation
└── regression/
    ├── run_regression_tests.py
    └── generate_test_files.py
```

### Script Lifecycle

Each script is standalone (~60-100 lines), no BaseETLJob subclass:

```python
# etl/jobs/run_newyorkfed_reference_rates.py
CONFIG_NAME = 'NewYorkFed_ReferenceRates_Latest'

def transform(data):
    # Source-specific transforms
    ...

def main():
    client = NewYorkFedAPIClient()
    try:
        raw_data = client.get_reference_rates_latest()
    finally:
        client.close()
    transformed = transform(raw_data)
    save_json(transformed, CONFIG_NAME, source='newyorkfed')
    return run_generic_import(CONFIG_NAME, args.dry_run)
```

### Shared Utility: `etl/base/import_utils.py`

Common functions every script uses:
- `get_config_id(config_name)` — Lookup config_id by name from dba.timportconfig
- `save_json(data, config_name, source)` — Save JSON to source directory
- `run_generic_import(config_name, dry_run)` — Lookup config_id, run GenericImportJob
- `parse_date(value)` — Parse `YYYY-MM-DD` string to ISO date string, or None
- `parse_numeric(value, strip_commas=False)` — Parse numeric, optionally strip commas
- `audit_cols()` — Returns `{'created_date': ..., 'created_by': 'etl_user'}`

Key design: **scripts reference config by `CONFIG_NAME` (string)**, not config_id (int). `import_utils.get_config_id()` looks up the integer from the database.

### Adding a New API Endpoint

Create a new individual script:

1. **Create `etl/jobs/run_{source}_{endpoint}.py`** following the pattern:
   ```python
   from etl.base.import_utils import save_json, run_generic_import, parse_date, audit_cols

   CONFIG_NAME = 'Source_Endpoint_Name'

   def transform(data):
       transformed = []
       for record in data:
           transformed.append({
               'field_name': record.get('apiFieldName'),
               'date_field': parse_date(record.get('dateField')),
               **audit_cols(),
           })
       return transformed

   def main():
       client = SourceAPIClient()
       try:
           raw_data = client.get_endpoint()
       finally:
           client.close()
       transformed = transform(raw_data)
       save_json(transformed, CONFIG_NAME, source='source')
       return run_generic_import(CONFIG_NAME, args.dry_run)
   ```

2. **Add SQL config** in `schema/dba/data/{source}_import_configs.sql`:
   - `source_directory` = `/app/data/source/{source}`
   - `archive_directory` = `/app/data/archive/{source}`
   - `file_pattern` = `{source}_{slug}_.*\.json` (regex)
   - `api_endpoint_path`, `api_response_root_path` from API docs

3. **Add scheduler job** in `schema/dba/data/{source}_scheduler_jobs.sql`:
   ```sql
   ('JobName', 'custom', '0', '9', '*', '*', '*',
    'etl/jobs/run_{source}_{endpoint}.py', TRUE)
   ```

4. **Apply SQL** and test:
   ```bash
   docker compose exec tangerine python etl/jobs/run_{source}_{endpoint}.py --dry-run
   docker compose exec tangerine python etl/jobs/run_{source}_{endpoint}.py
   ```

### Adding a New Data Source

1. Create `etl/clients/{source}_client.py` (API client)
2. Create individual `etl/jobs/run_{source}_{endpoint}.py` scripts
3. Create SQL configs and scheduler jobs

### File Naming Convention

Scripts save JSON as: `{source}_{slug}_{YYYYMMDD_HHMMSS}.json`
- `newyorkfed_referencerates_latest_20260226_090000.json`
- `bankofengland_sonia_rates_20260226_153000.json`

`generic_import` matches files via `file_pattern` regex in timportconfig.

## Supported File Formats

| Format | Extension | Parser |
|--------|-----------|--------|
| CSV | .csv | csv.DictReader |
| Excel | .xls, .xlsx | pandas/openpyxl |
| JSON | .json | json.load |
| XML | .xml | xml.etree.ElementTree |

## Import Strategies

| ID | Name | Behavior |
|----|------|----------|
| 1 | Auto-add | ALTER TABLE to add new columns from file |
| 2 | Ignore | Skip columns not already in table |
| 3 | Strict | Fail if file columns don't match table |

**Recommendation:** Use Strategy 2 (Ignore) for most imports. Use Strategy 1 only when schema evolution is expected.

## Required Patterns

### 1. Dry-Run Mode

All jobs MUST support `--dry-run` flag:

```python
parser.add_argument("--dry-run", action="store_true",
                    help="Validate without database writes")
```

### 2. Logging

Use the common logging utility:

```python
from common.logging_utils import get_logger
logger = get_logger("script_name")
```

### 3. Dataset Tracking

`generic_import.py` handles dataset tracking automatically via `dba.f_dataset_iu()`.

### 4. File Archiving

`generic_import.py` handles file archiving automatically (moves to `archive_directory`).

## Database Connections

Always use the transaction context manager:

```python
from common.db_utils import db_transaction, fetch_dict

with db_transaction() as cursor:
    cursor.execute("SELECT * FROM dba.timportconfig WHERE config_id = %s", (config_id,))

rows = fetch_dict("SELECT * FROM dba.timportconfig WHERE config_id = %s", (config_id,))
```

## Testing

```bash
# Test a script (dry run)
docker compose exec tangerine python etl/jobs/run_newyorkfed_reference_rates.py --dry-run

# Test a script (live)
docker compose exec tangerine python etl/jobs/run_newyorkfed_reference_rates.py

# Run all NewYorkFed jobs
docker compose exec tangerine python scripts/run_all_newyorkfed_jobs.py --dry-run

# Run integration tests
docker compose exec tangerine pytest tests/integration/etl/ -v
```

## Common Pitfalls

1. **One script per endpoint** — Each endpoint gets its own `run_*.py` file
2. **Don't hardcode config IDs** — Use `CONFIG_NAME` string, let `import_utils` resolve
3. **Don't skip dry-run** — Always implement and test dry-run mode
4. **Don't use string formatting for SQL** — Always use parameterized queries
5. **Dates in JSON as ISO strings** — PostgreSQL auto-casts `'2025-01-03'` to DATE

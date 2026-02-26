---
name: etl-developer
description: ETL job development patterns for Tangerine - import jobs, extractors, schema management, file processing
---

# ETL Developer Guidelines

## Overview

Tangerine uses a config-driven ETL framework. Most imports use `generic_import.py` with database configuration rather than custom job files.

## Architecture: Collector Pattern

All API-based data imports follow a **two-stage collector pattern**:

1. **Data Collection** (unique per source) — API fetch + transform + save JSON
2. **Import** (universal) — `generic_import.py --config-id N`

```
etl/
├── collectors/                          # Data collection (unique per source)
│   ├── newyorkfed_collector.py          # All NewYorkFed endpoints (13 configs)
│   └── bankofengland_collector.py       # All BoE endpoints (SONIA rates)
├── clients/                             # API clients (reusable, no transforms)
│   ├── newyorkfed_client.py
│   └── bankofengland_client.py
├── jobs/
│   ├── generic_import.py                # Universal config-driven file import
│   ├── run_gmail_inbox_processor.py     # Email attachment processing (not an import)
│   ├── run_report_generator.py          # SQL-based report generation (not an import)
│   └── generate_crontab.py             # Scheduler cron generation
└── regression/
    ├── run_regression_tests.py
    └── generate_test_files.py
```

### Collector Lifecycle

```python
# etl/collectors/{source}_collector.py --config-id N
def main():
    config = load_config(args.config_id)         # Read from timportconfig
    raw_data = collector['fetch'](config)         # API call via client
    transformed = collector['transform'](raw_data) # Source-specific transforms
    save_json(transformed, config)                 # Write JSON to source_directory
    run_generic_import(args.config_id, dry_run)    # Universal import
```

### Adding a New API Endpoint

**DO NOT create new `run_*.py` job files.** Instead, add to an existing collector:

1. **Add a transform function** in the appropriate collector (e.g., `newyorkfed_collector.py`):
   ```python
   def transform_new_endpoint(data: list) -> list:
       transformed = []
       for record in data:
           transformed.append({
               'field_name': record.get('apiFieldName'),
               'date_field': _parse_date(record.get('dateField')),
               **_audit_cols(),
           })
       return transformed
   ```

2. **Register it** in the `COLLECTORS` dict:
   ```python
   COLLECTORS = {
       ...
       'NewYorkFed_New_Endpoint': {'fetch': fetch_newyorkfed, 'transform': transform_new_endpoint},
   }
   ```

3. **Add SQL config** in `schema/dba/data/{source}_import_configs.sql`:
   - `source_directory` = `/app/data/source/{source}`
   - `archive_directory` = `/app/data/archive/{source}`
   - `file_pattern` = `{source}_{slug}_.*\.json` (regex)
   - `api_endpoint_path`, `api_response_root_path` from API docs

4. **Add scheduler job** in `schema/dba/data/{source}_scheduler_jobs.sql`:
   ```sql
   ('JobName', 'custom', '0', '9', '*', '*', '*',
    'etl/collectors/{source}_collector.py --config-id N', TRUE)
   ```

5. **Apply SQL** and test:
   ```bash
   docker compose exec tangerine python etl/collectors/{source}_collector.py --config-id N --dry-run
   docker compose exec tangerine python etl/collectors/{source}_collector.py --config-id N
   ```

### Adding a New Data Source

Create a new collector file following the established pattern:

1. Create `etl/clients/{source}_client.py` (API client)
2. Create `etl/collectors/{source}_collector.py` with:
   - `SOURCE_DIR`, `load_config()`, `save_json()`, `ensure_source_directory()`, `run_generic_import()`
   - Source-specific fetch function(s)
   - Transform function(s)
   - `COLLECTORS` registry dict
   - `main()` with `--config-id` and `--dry-run` args
3. Create SQL configs and scheduler jobs

### Config IDs Reference

**NewYorkFed** (`newyorkfed_collector.py`):
| ID | Config Name | Active | Schedule |
|----|-------------|--------|----------|
| 1 | ReferenceRates_Latest | Yes | Daily 9:00 |
| 2 | ReferenceRates_Search | No | — |
| 3 | SOMA_Holdings | Yes | Thu 10:00 |
| 4 | Repo_Operations | Yes | Daily 9:05 |
| 5 | ReverseRepo_Operations | Yes | Daily 9:10 |
| 6 | Agency_MBS | No | Fri 10:00 |
| 7 | FX_Swaps | No | Fri 10:05 |
| 8 | Guide_Sheets | No | 1st Mon 11:00 |
| 9 | PD_Statistics | No | Fri 10:10 |
| 10 | Market_Share | No | Quarterly |
| 11 | Securities_Lending | No | Daily 9:15 |
| 12 | Treasury_Operations | No | Daily 9:20 |

**BankOfEngland** (`bankofengland_collector.py`):
| ID | Config Name | Active | Schedule |
|----|-------------|--------|----------|
| 13 | SONIA_Rates | Yes | Weekdays 15:30 UTC |

### Transform Patterns

Common helper functions available in collectors:
- `_parse_date(value)` — Parse `YYYY-MM-DD` string to ISO date string, or None
- `_parse_numeric(value, strip_commas=False)` — Parse numeric, optionally strip commas
- `_audit_cols()` — Returns `{'created_date': ..., 'created_by': 'etl_user'}`

### File Naming Convention

Collectors save JSON as: `{source}_{slug}_{YYYYMMDD_HHMMSS}.json`
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
logger = get_logger("collector_name")
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
# Test a collector (dry run)
docker compose exec tangerine python etl/collectors/newyorkfed_collector.py --config-id 1 --dry-run

# Test a collector (live)
docker compose exec tangerine python etl/collectors/newyorkfed_collector.py --config-id 1

# Run integration tests
docker compose exec tangerine pytest tests/integration/etl/ -v
```

## Common Pitfalls

1. **Don't create new `run_*.py` job files** — Add to existing collectors instead
2. **Don't hardcode paths** — Use config values from database
3. **Don't skip dry-run** — Always implement and test dry-run mode
4. **Don't use string formatting for SQL** — Always use parameterized queries
5. **Dates in JSON as ISO strings** — PostgreSQL auto-casts `'2025-01-03'` to DATE
6. **Config IDs are auto-generated** — Check the database for actual IDs, don't assume

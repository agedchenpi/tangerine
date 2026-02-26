# Redesign: Individual Scripts + Universal Import

## Context

The previous refactor consolidated 11 individual `run_*.py` scripts into 2 mega-collector files (`etl/collectors/newyorkfed_collector.py` and `bankofengland_collector.py`). The user prefers individual scripts per endpoint — explicit, readable, one file per data feed — with `generic_import.py` as the universal loader.

## Target Architecture

```
etl/
├── base/
│   ├── etl_job.py            # UNCHANGED
│   ├── api_client.py         # UNCHANGED
│   └── import_utils.py       # NEW — shared save/import plumbing
├── clients/
│   ├── newyorkfed_client.py  # UNCHANGED
│   └── bankofengland_client.py  # UNCHANGED
├── jobs/
│   ├── generic_import.py     # UNCHANGED — universal import engine
│   ├── run_newyorkfed_reference_rates.py    # fetch + transform + save JSON + import
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
│   ├── run_gmail_inbox_processor.py   # UNCHANGED
│   └── run_report_generator.py        # UNCHANGED
```

No `etl/collectors/` directory.

## Script Pattern

Each script is ~60-100 lines. Fetch → transform → save JSON → run generic_import. **No BaseETLJob subclass** — plain standalone scripts.

```python
# etl/jobs/run_newyorkfed_reference_rates.py
"""..."""
import argparse, sys, os
from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, parse_date, audit_cols

CONFIG_NAME = 'NewYorkFed_ReferenceRates_Latest'

logger = get_logger('run_newyorkfed_reference_rates')


def fetch(client):
    return client.get_reference_rates_latest()


def transform(data):
    transformed = []
    for record in data:
        effective_date = parse_date(record.get('effectiveDate'))
        if not effective_date:
            continue
        transformed.append({
            'rate_type': record.get('type'),
            'effective_date': effective_date,
            'rate_percent': record.get('percentRate'),
            ...
            **audit_cols(),
        })
    return transformed


def main():
    parser = argparse.ArgumentParser(...)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    client = NewYorkFedAPIClient()
    try:
        raw_data = client.get_reference_rates_latest()
    finally:
        client.close()

    transformed = transform(raw_data)
    save_json(transformed, CONFIG_NAME, source='newyorkfed')
    return run_generic_import(CONFIG_NAME, args.dry_run)

if __name__ == '__main__':
    sys.exit(main())
```

## Shared Utility: `etl/base/import_utils.py`

Small module (~80 lines) with functions every script needs:

```python
# etl/base/import_utils.py

def get_config_id(config_name: str) -> int:
    """Lookup config_id by config_name from dba.timportconfig."""

def save_json(data: list, config_name: str, source: str) -> Path:
    """Save JSON array to /app/data/source/{source}/{source}_{slug}_{timestamp}.json"""

def run_generic_import(config_name: str, dry_run: bool = False) -> int:
    """Lookup config_id by name, run GenericImportJob. Returns 0 on success, 1 on failure."""

def parse_date(value: str) -> str | None:
    """Parse YYYY-MM-DD to ISO date string, or None."""

def parse_numeric(value, strip_commas: bool = False) -> float | None:
    """Parse numeric value, optionally stripping commas."""

def audit_cols() -> dict:
    """Return {'created_date': ..., 'created_by': 'etl_user'}."""
```

Key design choice: **scripts reference their config by `CONFIG_NAME` (string), not config_id (int)**. `import_utils.get_config_id()` looks up the integer from the database. This avoids hardcoded config IDs that can break if the database is rebuilt.

## Files to Create

### 1. `etl/base/import_utils.py`
Shared utility with `save_json`, `run_generic_import`, `get_config_id`, `parse_date`, `parse_numeric`, `audit_cols`.

### 2-14. Individual `etl/jobs/run_*.py` scripts (13 files)

Each script extracts its transform logic from the current collector files:

| Script | Config Name | Fetch method |
|--------|-------------|--------------|
| `run_newyorkfed_reference_rates.py` | `NewYorkFed_ReferenceRates_Latest` | `client.get_reference_rates_latest()` |
| `run_newyorkfed_soma_holdings.py` | `NewYorkFed_SOMA_Holdings` | `client.get_soma_holdings()` |
| `run_newyorkfed_repo.py` | `NewYorkFed_Repo_Operations` | `client.get_repo_operations()` |
| `run_newyorkfed_reverserepo.py` | `NewYorkFed_ReverseRepo_Operations` | `client.get_repo_operations()` |
| `run_newyorkfed_agency_mbs.py` | `NewYorkFed_Agency_MBS` | `client.get_agency_mbs()` |
| `run_newyorkfed_fx_swaps.py` | `NewYorkFed_FX_Swaps` | `client.get_fx_swaps()` |
| `run_newyorkfed_counterparties.py` | `NewYorkFed_Counterparties` | `client.get_counterparties()` |
| `run_newyorkfed_securities_lending.py` | `NewYorkFed_Securities_Lending` | `client.get_securities_lending()` |
| `run_newyorkfed_guide_sheets.py` | `NewYorkFed_Guide_Sheets` | `client.get_guide_sheets()` |
| `run_newyorkfed_treasury.py` | `NewYorkFed_Treasury_Operations` | `client.get_treasury_operations()` |
| `run_newyorkfed_pd_statistics.py` | `NewYorkFed_PD_Statistics` | `fetch_newyorkfed()` via config |
| `run_newyorkfed_market_share.py` | `NewYorkFed_Market_Share` | `fetch_newyorkfed()` via config |
| `run_bankofengland_sonia_rates.py` | `BankOfEngland_SONIA_Rates` | `client.get_sonia_rates()` |

Repo and Reverse Repo are **separate scripts** — same transform logic duplicated for clarity.
PD Statistics and Market Share are passthrough (no transform) — fetch and save only.

## Files to Modify

### 15. `schema/dba/data/newyorkfed_scheduler_jobs.sql`
Change script_paths back to individual scripts:
```sql
('NewYorkFed_ReferenceRates', ..., 'etl/jobs/run_newyorkfed_reference_rates.py', TRUE),
('NewYorkFed_Repo', ..., 'etl/jobs/run_newyorkfed_repo.py', TRUE),
('NewYorkFed_ReverseRepo', ..., 'etl/jobs/run_newyorkfed_reverserepo.py', TRUE),
('NewYorkFed_PDStatistics', ..., 'etl/jobs/run_newyorkfed_pd_statistics.py', FALSE),
('NewYorkFed_MarketShare', ..., 'etl/jobs/run_newyorkfed_market_share.py', FALSE),
...
```

### 14. `schema/dba/data/bankofengland_scheduler_jobs.sql`
```sql
('BankOfEngland_SONIA', ..., 'etl/jobs/run_bankofengland_sonia_rates.py', TRUE)
```

### 15. `scripts/run_all_newyorkfed_jobs.py`
Update to invoke individual scripts (via subprocess) instead of the collector.

### 16. `tests/integration/etl/test_newyorkfed_integration.py`
Update imports to reference the individual script transform functions.

### 17. `.claude/skills/etl-developer/SKILL.md`
Update architecture docs to reflect individual-script pattern.

## Files to Delete

- `etl/collectors/newyorkfed_collector.py`
- `etl/collectors/bankofengland_collector.py`
- `etl/collectors/__init__.py`
- `etl/collectors/` directory

## What Does NOT Change

- `etl/jobs/generic_import.py` — universal import engine
- `etl/clients/newyorkfed_client.py` — API client
- `etl/clients/bankofengland_client.py` — API client
- `schema/dba/data/newyorkfed_import_configs.sql` — import configs (already correct)
- `schema/dba/data/bankofengland_import_configs.sql` — import configs (already correct)
- `etl/base/etl_job.py` — base class (scripts don't use it)
- All `schema/feeds/*.sql` — table definitions

## Verification

```bash
# Test each script
docker compose exec tangerine python etl/jobs/run_newyorkfed_reference_rates.py --dry-run
docker compose exec tangerine python etl/jobs/run_newyorkfed_reference_rates.py
docker compose exec tangerine python etl/jobs/run_newyorkfed_soma_holdings.py --dry-run
docker compose exec tangerine python etl/jobs/run_newyorkfed_repo.py --dry-run
docker compose exec tangerine python etl/jobs/run_newyorkfed_reverserepo.py --dry-run
docker compose exec tangerine python etl/jobs/run_bankofengland_sonia_rates.py --dry-run

# Rebuild and test
docker compose build tangerine && docker compose up -d tangerine

# Run all
docker compose exec tangerine python scripts/run_all_newyorkfed_jobs.py --dry-run

# Verify scheduler
docker compose exec tangerine python etl/jobs/generate_crontab.py --preview
```

# Refactor: Separate Data Collection from Import

## Context

Currently 11 custom `run_*.py` scripts each handle the full ETL lifecycle (API fetch + transform + load) as standalone BaseETLJob subclasses. Meanwhile, `generic_import.py` already provides a universal config-driven import system via `timportconfig`, but almost nothing uses it.

**Goal**: Split each import into two concerns:
1. **Data Collection** (unique per source) — API fetch + transform + save to file
2. **Import** (universal) — `generic_import.py --config-id N`

The existing bridge script `run_newyorkfed_api_import.py` already proves this pattern works. We're generalizing it to ALL import jobs and adding the transform step it's missing.

## Current State: 11 Custom Scripts → 2 Collectors

| # | Current Script | Source | Transform Complexity |
|---|---------------|--------|---------------------|
| 1 | `run_newyorkfed_reference_rates.py` | NewYorkFed | Low — field renames, date parse |
| 2 | `run_newyorkfed_soma_holdings.py` | NewYorkFed | Medium — comma-stripping numerics |
| 3 | `run_newyorkfed_repo.py` | NewYorkFed | High — calculated term_days, string normalization |
| 4 | `run_newyorkfed_agency_mbs.py` | NewYorkFed | Low — field renames, 3 date parses |
| 5 | `run_newyorkfed_fx_swaps.py` | NewYorkFed | High — term_days calc, field fallback logic |
| 6 | `run_newyorkfed_counterparties.py` | NewYorkFed | Medium — enum injection, validation |
| 7 | `run_newyorkfed_securities_lending.py` | NewYorkFed | High — term_days calc, field coalesce |
| 8 | `run_newyorkfed_guide_sheets.py` | NewYorkFed | High — nested array extraction |
| 9 | `run_newyorkfed_treasury.py` | NewYorkFed | Low — field renames, 3 date parses |
| 10 | `run_newyorkfed_api_import.py` | NewYorkFed | None — bridge only (no transform) |
| 11 | `run_bankofengland_sonia_rates.py` | BankOfEngland | Medium — non-standard date format, float coercion |

## Target Architecture

```
etl/
├── collectors/                          # NEW — data collection (unique per source)
│   ├── newyorkfed_collector.py          # All NewYorkFed endpoints (replaces 10 scripts)
│   └── bankofengland_collector.py       # All BoE endpoints (replaces 1 script)
├── clients/                             # UNCHANGED
│   ├── newyorkfed_client.py
│   └── bankofengland_client.py
├── jobs/
│   ├── generic_import.py                # UNCHANGED — universal import
│   └── generate_crontab.py             # UNCHANGED
```

### Collector Pattern

Each collector follows the proven `run_newyorkfed_api_import.py` bridge pattern, enhanced with transforms:

```python
# etl/collectors/bankofengland_collector.py --config-id 13

TRANSFORMS = {
    'BankOfEngland_SONIA_Rates': transform_sonia_rates,
}

def main():
    config = load_config(args.config_id)         # Read from timportconfig
    raw_data = fetch(config)                      # API call via BankOfEnglandAPIClient
    transform_fn = TRANSFORMS[config.config_name] # Dispatch to right transform
    transformed = transform_fn(raw_data)          # Source-specific transforms
    save_json(transformed, config)                # Write to source_directory
    run_generic_import(args.config_id, dry_run)   # Universal import
```

### Scheduler Entries After Refactor

| Job | Before (script_path) | After (script_path) |
|-----|---------------------|---------------------|
| BankOfEngland_SONIA | `etl/jobs/run_bankofengland_sonia_rates.py` | `etl/collectors/bankofengland_collector.py --config-id 13` |
| NewYorkFed_ReferenceRates | `etl/jobs/run_newyorkfed_reference_rates.py --endpoint-type latest` | `etl/collectors/newyorkfed_collector.py --config-id 1` |
| NewYorkFed_Repo | `etl/jobs/run_newyorkfed_repo.py` | `etl/collectors/newyorkfed_collector.py --config-id 4` |
| NewYorkFed_ReverseRepo | `etl/jobs/run_newyorkfed_repo.py` | `etl/collectors/newyorkfed_collector.py --config-id 5` |
| NewYorkFed_SecLending | `etl/jobs/run_newyorkfed_securities_lending.py` | `etl/collectors/newyorkfed_collector.py --config-id 8` |
| NewYorkFed_Treasury | `etl/jobs/run_newyorkfed_treasury.py` | `etl/collectors/newyorkfed_collector.py --config-id 10` |
| NewYorkFed_SOMA | `etl/jobs/run_newyorkfed_soma_holdings.py` | `etl/collectors/newyorkfed_collector.py --config-id 3` |
| NewYorkFed_AgencyMBS | `etl/jobs/run_newyorkfed_agency_mbs.py` | `etl/collectors/newyorkfed_collector.py --config-id 6` |
| NewYorkFed_FXSwaps | `etl/jobs/run_newyorkfed_fx_swaps.py` | `etl/collectors/newyorkfed_collector.py --config-id 7` |
| NewYorkFed_PDStatistics | `etl/jobs/run_newyorkfed_api_import.py --config-id 9` | `etl/collectors/newyorkfed_collector.py --config-id 9` |
| NewYorkFed_GuideSheets | `etl/jobs/run_newyorkfed_guide_sheets.py` | `etl/collectors/newyorkfed_collector.py --config-id 9` |
| NewYorkFed_MarketShare | `etl/jobs/run_newyorkfed_api_import.py --config-id 10` | `etl/collectors/newyorkfed_collector.py --config-id 11` |

## Files to Create

### 1. `etl/collectors/bankofengland_collector.py`

Collector for all BoE endpoints. Initially just SONIA.

**Shared functions** (reused from `run_newyorkfed_api_import.py` pattern):
- `load_config(config_id)` — reads timportconfig row
- `save_json(data, config)` — writes `[{...}, ...]` to source_directory with naming: `bankofengland_{slug}_{YYYYMMDD_HHMMSS}.json`
- `ensure_source_directory(config_id)` — updates timportconfig if source_directory empty
- `run_generic_import(config_id, dry_run)` — invokes GenericImportJob
- `main()` — argparse with `--config-id` (required), `--dry-run`

**Transform functions** (moved from `run_bankofengland_sonia_rates.py`):
- `transform_sonia_rates(raw_data)` — parse '03 Jan 2025' dates to ISO strings, coerce rate to float, skip non-numeric, add audit cols. Returns `[{"effective_date": "2025-01-03", "rate_percent": 4.55, ...}]`

**Fetch function**:
- `fetch_sonia_rates(config)` — uses `BankOfEnglandAPIClient.get_sonia_rates()`

**Registry**:
```python
COLLECTORS = {
    'BankOfEngland_SONIA_Rates': {
        'fetch': fetch_sonia_rates,
        'transform': transform_sonia_rates,
    },
}
```

### 2. `etl/collectors/newyorkfed_collector.py`

Collector for all NewYorkFed endpoints. Replaces 10 scripts.

**Shared functions**: Same as BoE collector (load_config, save_json, run_generic_import, main).

**Fetch function** (generic — works for all NYF endpoints):
- `fetch_newyorkfed(config)` — uses `NewYorkFedAPIClient.fetch_endpoint(endpoint_path, response_format, response_root_path)` reading all params from config. This is exactly what `run_newyorkfed_api_import.py:fetch_data()` already does.

**Transform functions** (moved from respective `run_*.py` files):
- `transform_reference_rates(data)` — 13 field renames, date parse
- `transform_soma_holdings(data)` — 8 field renames, comma-stripping, date parse
- `transform_repo_operations(data)` — 9 field renames, term_days calc, operationType normalization
- `transform_agency_mbs(data)` — 9 field renames, 3 date parses
- `transform_fx_swaps(data)` — 8 field renames, term_days calc, currencyCode fallback
- `transform_counterparties(data)` — enum injection, validation
- `transform_securities_lending(data)` — 10 field renames, term_days calc, field coalesce
- `transform_guide_sheets(data)` — nested array extraction, metadata promotion
- `transform_treasury_operations(data)` — 14 field renames, 3 date parses
- `transform_passthrough(data)` — no transform (for PD Statistics, Market Share)

**Registry**:
```python
COLLECTORS = {
    'NewYorkFed_ReferenceRates_Latest': {'fetch': fetch_newyorkfed, 'transform': transform_reference_rates},
    'NewYorkFed_ReferenceRates_Search': {'fetch': fetch_newyorkfed, 'transform': transform_reference_rates},
    'NewYorkFed_SOMA_Holdings':         {'fetch': fetch_newyorkfed, 'transform': transform_soma_holdings},
    'NewYorkFed_Repo_Operations':       {'fetch': fetch_newyorkfed, 'transform': transform_repo_operations},
    'NewYorkFed_ReverseRepo_Operations':{'fetch': fetch_newyorkfed, 'transform': transform_repo_operations},
    'NewYorkFed_Agency_MBS':            {'fetch': fetch_newyorkfed, 'transform': transform_agency_mbs},
    'NewYorkFed_FX_Swaps':              {'fetch': fetch_newyorkfed, 'transform': transform_fx_swaps},
    'NewYorkFed_Guide_Sheets':          {'fetch': fetch_newyorkfed, 'transform': transform_guide_sheets},
    'NewYorkFed_PD_Statistics':         {'fetch': fetch_newyorkfed, 'transform': transform_passthrough},
    'NewYorkFed_Market_Share':          {'fetch': fetch_newyorkfed, 'transform': transform_passthrough},
    'NewYorkFed_Securities_Lending':    {'fetch': fetch_newyorkfed, 'transform': transform_securities_lending},
    'NewYorkFed_Treasury_Operations':   {'fetch': fetch_newyorkfed, 'transform': transform_treasury_operations},
}
```

## Files to Modify

### 3. `schema/dba/data/newyorkfed_import_configs.sql`

Update all configs to set proper directories and file patterns for generic_import:

```sql
-- For each config, set:
source_directory = '/app/data/source/newyorkfed',
archive_directory = '/app/data/archive/newyorkfed',
file_pattern = 'newyorkfed_{slug}_.*\.json'   -- regex matching collector output
```

Also update stub configs (Agency MBS, FX Swaps, Guide Sheets, PD Statistics, Market Share, Securities Lending, Treasury Operations) with correct `api_endpoint_path` and `api_response_root_path` values (currently some have placeholder `'/api/ambs/...'` paths).

### 4. `schema/dba/data/bankofengland_import_configs.sql`

Update config to set proper directories:

```sql
source_directory = '/app/data/source/bankofengland',
archive_directory = '/app/data/archive/bankofengland',
file_pattern = 'bankofengland_sonia_rates_.*\.json'
```

### 5. `schema/dba/data/newyorkfed_scheduler_jobs.sql`

Update all script_paths to use collector pattern:

```sql
-- Before:
('NewYorkFed_ReferenceRates', 'custom', '0', '9', '*', '*', '*',
 'etl/jobs/run_newyorkfed_reference_rates.py --endpoint-type latest', TRUE)

-- After:
('NewYorkFed_ReferenceRates', 'custom', '0', '9', '*', '*', '*',
 'etl/collectors/newyorkfed_collector.py --config-id 1', TRUE)
```

### 6. `schema/dba/data/bankofengland_scheduler_jobs.sql`

Update script_path:

```sql
-- Before:
'etl/jobs/run_bankofengland_sonia_rates.py'
-- After:
'etl/collectors/bankofengland_collector.py --config-id 13'
```

## Files to Delete (after migration verified)

| File | Replaced By |
|------|-------------|
| `etl/jobs/run_newyorkfed_reference_rates.py` | `newyorkfed_collector.py --config-id 1` |
| `etl/jobs/run_newyorkfed_soma_holdings.py` | `newyorkfed_collector.py --config-id 3` |
| `etl/jobs/run_newyorkfed_repo.py` | `newyorkfed_collector.py --config-id 4,5` |
| `etl/jobs/run_newyorkfed_agency_mbs.py` | `newyorkfed_collector.py --config-id 6` |
| `etl/jobs/run_newyorkfed_fx_swaps.py` | `newyorkfed_collector.py --config-id 7` |
| `etl/jobs/run_newyorkfed_counterparties.py` | `newyorkfed_collector.py --config-id (TBD)` |
| `etl/jobs/run_newyorkfed_securities_lending.py` | `newyorkfed_collector.py --config-id 8` |
| `etl/jobs/run_newyorkfed_guide_sheets.py` | `newyorkfed_collector.py --config-id 9` |
| `etl/jobs/run_newyorkfed_treasury.py` | `newyorkfed_collector.py --config-id 10` |
| `etl/jobs/run_newyorkfed_api_import.py` | `newyorkfed_collector.py` (subsumed) |
| `etl/jobs/run_bankofengland_sonia_rates.py` | `bankofengland_collector.py --config-id 13` |

## What Does NOT Change

- `etl/jobs/generic_import.py` — universal import, no modifications needed
- `etl/clients/newyorkfed_client.py` — API client, unchanged
- `etl/clients/bankofengland_client.py` — API client, unchanged
- `etl/base/etl_job.py` — base class (collectors don't extend it; generic_import does)
- `etl/loaders/postgres_loader.py` — used by generic_import, unchanged
- All `schema/feeds/*.sql` — table definitions unchanged
- `etl/jobs/run_gmail_inbox_processor.py` — not an API import, stays as-is
- `etl/jobs/run_report_generator.py` — not an import, stays as-is

## Key Design Decisions

1. **One collector per data source** (not per endpoint) — reduces file count from 11 to 2, shares client setup and common functions
2. **Transform functions live in the collector** — this IS the unique part; each transform function is lifted directly from the existing job's `transform()` method
3. **Collector calls `GenericImportJob` at the end** — keeps scheduler entries simple (single command), proven pattern from `run_newyorkfed_api_import.py`
4. **Dates saved as ISO strings in JSON** — PostgreSQL auto-casts `'2025-01-03'` to DATE on insert
5. **JSON output format** — all collectors save `[{...}, {...}]` arrays; generic_import's JSONExtractor handles this natively
6. **File naming convention**: `{source}_{slug}_{YYYYMMDD_HHMMSS}.json` — generic_import matches via `file_pattern` regex in timportconfig

## Migration Strategy

### Phase 1: BoE SONIA (proof of concept)
1. Create `etl/collectors/bankofengland_collector.py`
2. Update `bankofengland_import_configs.sql` (directories, file_pattern)
3. Update `bankofengland_scheduler_jobs.sql` (new script_path)
4. Test: `docker compose exec tangerine python etl/collectors/bankofengland_collector.py --config-id 13 --dry-run`
5. Test: `docker compose exec tangerine python etl/collectors/bankofengland_collector.py --config-id 13`
6. Verify data matches previous run
7. Delete `etl/jobs/run_bankofengland_sonia_rates.py`

### Phase 2: NewYorkFed (all endpoints)
1. Create `etl/collectors/newyorkfed_collector.py` with all transform functions
2. Start with Reference Rates (config-id 1) — active, well-understood, simple transform
3. Update `newyorkfed_import_configs.sql` — fix stub endpoints, set directories/patterns
4. Update `newyorkfed_scheduler_jobs.sql` — all script_paths
5. Test each active endpoint: Reference Rates → Repo → SOMA
6. Test disabled endpoints as time allows
7. Delete all `etl/jobs/run_newyorkfed_*.py` scripts
8. Delete `etl/jobs/run_newyorkfed_api_import.py`

## Verification

For each migrated endpoint:
1. `docker compose exec tangerine python etl/collectors/{source}_collector.py --config-id N --dry-run`
2. Verify JSON file created in source directory with correct structure
3. `docker compose exec tangerine python etl/collectors/{source}_collector.py --config-id N`
4. Verify data loaded: `SELECT COUNT(*), MIN(effective_date), MAX(effective_date) FROM feeds.{table}`
5. Compare record counts/values with previous job run
6. Regenerate crontab: `docker compose exec tangerine python etl/jobs/generate_crontab.py --apply --preview --update-next-run`
7. Verify scheduler entries show new script_paths

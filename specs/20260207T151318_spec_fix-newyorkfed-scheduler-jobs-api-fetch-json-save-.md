# Plan: Fix NewYorkFed Scheduler Jobs — API Fetch + JSON Save + Import

## Context

The NewYorkFed scheduler jobs are failing because:
1. **Tangerine container was never rebuilt** after the `run_newyorkfed_*.py` scripts were added — scripts exist on host but not in the container
2. **Scheduler entries were changed from `custom` to `import` type** (previous session fix attempt) — needs to be reverted
3. **User wants the flow**: Script calls API → saves JSON to source dir → generic import runs

The existing dedicated scripts (`run_newyorkfed_reference_rates.py`, etc.) bypass file-saving entirely and load directly to DB. The user wants JSON payloads saved to disk (for audit/reprocessing) with the generic import handling the load.

## Approach

Create a **single unified runner script** (`etl/jobs/run_newyorkfed_api_import.py`) that all scheduler entries point to. This script:
1. Reads API config from `timportconfig` (base_url, endpoint_path, response_root_path)
2. Uses `NewYorkFedAPIClient` to fetch data
3. Saves JSON response to `/app/data/source/newyorkfed/`
4. Updates `timportconfig.source_directory` if not already set
5. Runs `generic_import.py --config-id N` to import the saved file

This replaces having 9+ separate scripts that each hardcode endpoint logic.

## Files to Modify

### 1. **NEW** `etl/jobs/run_newyorkfed_api_import.py` — Unified API fetch + import runner

```
Usage: python etl/jobs/run_newyorkfed_api_import.py --config-id N [--dry-run]
```

Flow:
1. Accept `--config-id` argument
2. Query `timportconfig` for the config row (api_base_url, api_endpoint_path, api_response_format, api_response_root_path, source_directory, file_pattern)
3. Use `NewYorkFedAPIClient` to call the endpoint
   - Map `api_endpoint_path` to the appropriate client method
   - OR use a generic `client.get(endpoint_path)` approach
4. Save JSON response to `/app/data/source/newyorkfed/newyorkfed_{config_name}_{timestamp}.json`
5. If `source_directory` is empty in timportconfig, update it to `/app/data/source/newyorkfed`
6. Invoke `generic_import.py --config-id N` via subprocess (or import and call directly)

Key references:
- `scripts/fetch_newyorkfed_api_data.py:35-59` — `save_json_file()` pattern for saving JSON
- `etl/clients/newyorkfed_client.py` — API client with all endpoint methods
- `etl/jobs/generic_import.py` — Generic import framework

### 2. `timportconfig` data updates — Set source_directory + file_pattern + import_mode

Update all 12 NewYorkFed configs:
```sql
UPDATE dba.timportconfig
SET source_directory = '/app/data/source/newyorkfed',
    import_mode = 'file',
    file_pattern = 'newyorkfed_{endpoint_slug}_*.json'
WHERE datasource = 'NewYorkFed';
```

Each config gets a specific `file_pattern` matching its saved filename pattern:
- config 1: `newyorkfed_referencerates_latest_*.json`
- config 3: `newyorkfed_soma_holdings_*.json`
- etc.

### 3. `dba.tscheduler` data updates — Revert to custom type

Revert the 11 scheduler entries back to `custom` type, all pointing to the unified script:
```sql
UPDATE dba.tscheduler
SET job_type = 'custom',
    script_path = 'python etl/jobs/run_newyorkfed_api_import.py --config-id {config_id}',
    config_id = NULL
WHERE job_name LIKE 'NewYorkFed_%';
```

Each entry gets its corresponding config_id in the script_path argument.

### 4. Rebuild **both** containers

- `docker compose build tangerine admin` — include new script
- `docker compose up -d` — restart services

## Endpoint-to-Client Method Mapping

The script needs to map `api_endpoint_path` from timportconfig to the correct `NewYorkFedAPIClient` method:

| config_id | config_name | api_endpoint_path | client method |
|-----------|-------------|-------------------|---------------|
| 1 | ReferenceRates_Latest | `/api/rates/all/latest.{format}` | `get_reference_rates_latest()` |
| 2 | ReferenceRates_Search | `/api/rates/all/search.{format}` | `get_reference_rates_search()` |
| 3 | SOMA_Holdings | `/api/soma/summary.{format}` | `get_soma_holdings()` |
| 4 | Repo_Operations | `/api/repo/results/search.{format}` | `get_repo_operations()` |
| 5 | ReverseRepo_Operations | `/api/reverserepo/results/search.{format}` | `get_reverse_repo_operations()` |
| 6 | Agency_MBS | `/api/ambs/...` | `get_agency_mbs()` |
| 7 | FX_Swaps | `/api/fxswaps/...` | `get_fx_swaps()` |
| 8 | Guide_Sheets | `/api/guidesheets/...` | `get_guide_sheets()` |
| 9 | PD_Statistics | `/api/pd/...` | `get_pd_statistics()` |
| 10 | Market_Share | `/api/marketshare/...` | `get_market_share()` |
| 11 | Securities_Lending | `/api/seclending/...` | `get_securities_lending()` |
| 12 | Treasury_Operations | `/api/treasury/...` | `get_treasury_operations()` |

Store this mapping as a dict in the script keyed by `config_name` prefix or `api_endpoint_path` pattern.

## No Changes Needed

- **Existing `run_newyorkfed_*.py` scripts** — Keep as-is (they're standalone ETL jobs for direct API→DB use)
- **`NewYorkFedAPIClient`** — Already has all endpoint methods
- **`generic_import.py`** — Already supports JSON file imports from source_directory
- **Database schema** — No table changes needed

## Verification

1. Rebuild containers: `docker compose build tangerine admin && docker compose up -d`
2. Verify script is in container: `docker compose exec tangerine ls /app/etl/jobs/run_newyorkfed_api_import.py`
3. Test manually: `docker compose exec tangerine python etl/jobs/run_newyorkfed_api_import.py --config-id 1 --dry-run`
4. Check JSON file saved to `/app/data/source/newyorkfed/`
5. Test via scheduler UI: "Run Now" on NewYorkFed_ReferenceRates
6. Verify `last_run_status` shows Success
7. Check data loaded in target table: `SELECT COUNT(*) FROM feeds.newyorkfed_reference_rates`

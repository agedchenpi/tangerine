# Fix 4 Failing NewYorkFed Import Jobs

## Context

After fixing the `python python` cron prefix bug, 4 of 6 NewYorkFed datasets that ran today show `status = Failed`:

| Config | Dataset | Error |
|--------|---------|-------|
| 4 | Repo_Operations | `can't adapt type 'dict'` — nested `details` array |
| 8 | Guide_Sheets | `can't adapt type 'dict'` — nested `details` array |
| 3 | SOMA_Holdings | `null value in column "as_of_date"` — field name mismatch |
| 12 | Treasury_Operations | `null value in column "operation_date"` — field name mismatch |

**Root cause:** All 11 scheduler jobs currently point to the **generic importer** (`run_newyorkfed_api_import.py --config-id X`), but **specialized job scripts already exist** for each endpoint that correctly handle field mapping, nested data flattening, and validation. The generic importer can't handle camelCase→snake_case mapping or nested JSON objects.

**The seed SQL** (`newyorkfed_scheduler_jobs.sql`) already has the correct specialized job paths. The live DB just needs to match.

## Fix: Update live DB scheduler to use specialized jobs

### Step 1 — Update `dba.tscheduler` script_path for all 11 NewYorkFed jobs

Run individual UPDATEs to set each job's `script_path` to its specialized script (matching the seed SQL):

```sql
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_reference_rates.py --endpoint-type latest' WHERE job_name = 'NewYorkFed_ReferenceRates';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_repo.py --operation-type repo' WHERE job_name = 'NewYorkFed_Repo';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_repo.py --operation-type reverserepo' WHERE job_name = 'NewYorkFed_ReverseRepo';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_securities_lending.py' WHERE job_name = 'NewYorkFed_SecLending';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_treasury.py' WHERE job_name = 'NewYorkFed_Treasury';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_soma_holdings.py' WHERE job_name = 'NewYorkFed_SOMA';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_agency_mbs.py' WHERE job_name = 'NewYorkFed_AgencyMBS';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_fx_swaps.py' WHERE job_name = 'NewYorkFed_FXSwaps';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_pd_statistics.py' WHERE job_name = 'NewYorkFed_PDStatistics';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_guide_sheets.py' WHERE job_name = 'NewYorkFed_GuideSheets';
UPDATE dba.tscheduler SET script_path = 'etl/jobs/run_newyorkfed_market_share.py' WHERE job_name = 'NewYorkFed_MarketShare';
```

Note: `run_newyorkfed_pd_statistics.py` and `run_newyorkfed_market_share.py` don't exist on disk — need to verify. If missing, leave those on the generic importer (they work: PD_Statistics was `Active` today).

### Step 2 — Handle missing specialized scripts

Check if these files exist:
- `etl/jobs/run_newyorkfed_pd_statistics.py`
- `etl/jobs/run_newyorkfed_market_share.py`

If not, keep their scheduler entries pointing to the generic importer (`run_newyorkfed_api_import.py --config-id 9` and `--config-id 10`) since those configs work with flat data.

### Step 3 — Add defense-in-depth: serialize nested objects in generic_import.py

In `generic_import.py` `transform()` method (line 928), add serialization of nested dicts/lists to JSON strings. This prevents future `can't adapt type 'dict'` errors if the generic importer is ever used with nested data:

```python
# After _normalize_column_names, before adding metadata:
for record in transformed:
    for key, value in record.items():
        if isinstance(value, (dict, list)):
            record[key] = json.dumps(value)
```

**File:** `/opt/tangerine/etl/jobs/generic_import.py` (line ~928)

### Step 4 — Regenerate crontab and verify

```bash
docker compose exec tangerine python etl/jobs/generate_crontab.py --apply --preview --update-next-run
```

### Step 5 — Run the 4 previously-failing jobs ad-hoc to verify

```bash
docker compose exec tangerine python etl/jobs/run_newyorkfed_repo.py --operation-type repo
docker compose exec tangerine python etl/jobs/run_newyorkfed_soma_holdings.py
docker compose exec tangerine python etl/jobs/run_newyorkfed_guide_sheets.py
docker compose exec tangerine python etl/jobs/run_newyorkfed_treasury.py
```

## Critical Files

| File | Action |
|------|--------|
| `dba.tscheduler` (live DB) | **UPDATE** — switch script_path to specialized jobs |
| `/opt/tangerine/etl/jobs/generic_import.py` | **Edit** — add JSON serialization for nested objects in transform() |

## Verification

1. `SELECT job_name, script_path FROM dba.tscheduler WHERE job_name LIKE 'NewYorkFed%';` — should show specialized job paths
2. Crontab preview shows correct specialized scripts
3. Ad-hoc runs of 4 failing jobs complete successfully
4. `SELECT label, isactive, statusname FROM dba.tdataset ... WHERE datasetdate = CURRENT_DATE` — all show Active

# Fix NewYorkFed Cron Jobs: Double "python" Prefix Bug

## Context

The smoketest canary revealed that **all 11 NewYorkFed cron jobs have been failing** every day. The cron.log shows:
```
python: can't open file '/app/python': [Errno 2] No such file or directory
```

**Root cause:** The `script_path` values in `dba.tscheduler` start with `python` (e.g., `python etl/jobs/run_newyorkfed_api_import.py --config-id 1`), but `generate_crontab.py` line 118 unconditionally prepends `python`:
```
cmd = f'cd /app && python {script_path}'
```
Result: `cd /app && python python etl/jobs/...` — the shell tries to open a file called `python`.

## Fix: Strip `python` prefix from DB `script_path` values

The convention established by the smoketest (and assumed by `generate_crontab.py`) is that `script_path` should be a **relative path only**, without a `python` prefix. The fix is to update the DB values and the SQL seed file to match.

### 1. Update `newyorkfed_scheduler_jobs.sql` — remove `python /app/` prefix from all `script_path` values

**File:** `/opt/tangerine/schema/dba/data/newyorkfed_scheduler_jobs.sql`

Change all `script_path` values from `'python /app/etl/jobs/...'` to `'etl/jobs/...'`. For example:
- `'python /app/etl/jobs/run_newyorkfed_reference_rates.py --endpoint-type latest'` → `'etl/jobs/run_newyorkfed_reference_rates.py --endpoint-type latest'`

This ensures fresh DB setups get correct values.

### 2. Update the live database — fix all 11 script_path values

Run a single SQL UPDATE to strip the `python ` prefix (and `/app/` if present) from all NewYorkFed scheduler entries currently in the DB. Then regenerate and apply the crontab.

### 3. Regenerate crontab and verify

After fixing DB values, regenerate the crontab and confirm:
- No more `python python` in any entry
- Cron.log shows successful execution on next scheduled run

## Critical Files

| File | Action |
|------|--------|
| `/opt/tangerine/schema/dba/data/newyorkfed_scheduler_jobs.sql` | **Edit** — remove `python /app/` prefix from all script_path values |
| `dba.tscheduler` (live DB) | **UPDATE** — strip prefix from existing rows |

## Verification

1. After DB update, run: `SELECT job_name, script_path FROM dba.tscheduler WHERE script_path LIKE 'python%';` — should return 0 rows
2. Regenerate crontab: `docker compose exec tangerine python etl/jobs/generate_crontab.py --apply --preview --update-next-run`
3. Confirm no `python python` in output
4. Check next cron execution in `/app/logs/cron.log`

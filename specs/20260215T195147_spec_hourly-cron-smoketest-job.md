# Hourly Cron Smoketest Job

## Context

We need an hourly smoketest to verify the cron scheduler and dataset creation pipeline are working end-to-end. This job runs every hour, creates a dataset record via `dba.f_dataset_iu`, and confirms the full lifecycle works — acting as a canary for the scheduling infrastructure.

## Changes

### 1. Add reference data: `Smoketest` datasource and `Smoketest` datasettype
**New file:** `/opt/tangerine/schema/dba/data/smoketest_reference_data.sql`

Insert into `dba.tdatasource` and `dba.tdatasettype` (with `ON CONFLICT DO NOTHING` guard):
- **datasource:** `sourcename='Smoketest'`, description: `'Internal smoketest and regression testing'`
- **datasettype:** `typename='Smoketest'`, description: `'Hourly cron scheduler smoketest'`

Also add this file to `schema/init.sh` so it runs on fresh DB setups (before the scheduler jobs insert).

### 2. Add the smoketest Python script
**New file:** `/opt/tangerine/etl/jobs/hourly_smoketest.py`

Uses `BaseETLJob` pattern to:
- Create a dataset record with `dataset_type='Smoketest'`, `data_source='Smoketest'`
- Label: `Smoketest_{YYYY-MM-DD}_{uuid[:8]}`
- Extract: returns a single synthetic record `[{"smoketest": True, "timestamp": <now>}]`
- Transform: pass-through (no transformation needed)
- Load: no-op (no actual data table to load into — the dataset record creation in `_create_dataset_record` is the test)
- On success, updates dataset status to `Active` (handled by BaseETLJob)
- Prints `Run UUID` for scheduler tracking

This follows the same `BaseETLJob` lifecycle as NYFed jobs, testing: DB connectivity, `f_dataset_iu`, ETL logging, and dataset status transitions.

### 3. Add scheduler record for the hourly job
**New file:** `/opt/tangerine/schema/dba/data/smoketest_scheduler_job.sql`

```sql
INSERT INTO dba.tscheduler (job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday, script_path, is_active)
VALUES ('Hourly_Smoketest', 'custom', '0', '*', '*', '*', '*',
        'etl/jobs/hourly_smoketest.py', TRUE)
ON CONFLICT (job_name) DO UPDATE SET script_path = EXCLUDED.script_path, is_active = EXCLUDED.is_active;
```

Schedule: `0 * * * *` (top of every hour, every day).

Also add this file to `schema/init.sh`.

**Note on `script_path`:** The `generate_crontab.py` custom job handler builds the command as `cd /app && python {script_path}`, so `script_path` should be the relative path without `python` prefix: `etl/jobs/hourly_smoketest.py`.

### 4. Insert reference data and scheduler record into running database
Since the DB already exists (no fresh init), we'll run the SQL files directly against the running database to add the new records.

## Critical Files

| File | Action |
|------|--------|
| `/opt/tangerine/schema/dba/data/smoketest_reference_data.sql` | **Create** - datasource + datasettype |
| `/opt/tangerine/schema/dba/data/smoketest_scheduler_job.sql` | **Create** - tscheduler record |
| `/opt/tangerine/schema/init.sh` | **Edit** - add both new SQL files |
| `/opt/tangerine/etl/jobs/hourly_smoketest.py` | **Create** - the smoketest script |

### Reused Existing Code
- `etl/base/etl_job.py:BaseETLJob` — full ETL lifecycle with logging + dataset creation
- `dba.f_dataset_iu()` — dataset insert/update function (called by BaseETLJob)
- `common/logging_utils.py:ETLLogger` — automatic logging to `dba.tlogentry`
- `dba.pscheduleri` pattern from `newyorkfed_scheduler_jobs.sql`

## Verification

1. Run the SQL to insert reference data + scheduler record
2. Run the smoketest manually: `docker compose exec tangerine python etl/jobs/hourly_smoketest.py`
3. Confirm dataset created: `SELECT * FROM dba.vdataset WHERE datasource = 'Smoketest' ORDER BY datasetid DESC LIMIT 1;`
4. Regenerate crontab: `docker compose exec tangerine python etl/jobs/generate_crontab.py --apply --preview --update-next-run`
5. Confirm crontab has the hourly entry: `docker compose exec tangerine crontab -l`
6. Wait for next hour mark and check `/app/logs/cron.log` for smoketest execution

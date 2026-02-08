# Fix: Admin container cannot execute ETL jobs

## Context
The Streamlit admin container runs `docker compose exec -T tangerine <cmd>` to execute ETL jobs, but docker CLI is not installed in the admin container. This causes all job executions from the UI (scheduler "Run Now", import page) to fail silently — the scheduler records `Failed` status but no dataset or log entries are created since the job never actually starts.

The admin container already has everything needed to run jobs directly:
- Same ETL code (`COPY etl/ /app/etl/` in Dockerfile.streamlit)
- Same `PYTHONPATH=/app`
- Same `DB_URL` environment variable
- Same shared data volumes (`/app/data`, `/app/logs`)
- Same Docker network (for DB access)

## Fix
Remove the `docker compose exec -T tangerine` prefix from subprocess commands in both files. Run jobs as local subprocesses instead.

### File 1: `admin/services/job_execution_service.py` (line 90-94)
```python
# Before:
cmd = [
    "docker", "compose", "exec", "-T", "tangerine",
    "python", "etl/jobs/generic_import.py",
    "--config-id", str(config_id)
]

# After:
cmd = [
    "python", "etl/jobs/generic_import.py",
    "--config-id", str(config_id)
]
```

### File 2: `admin/services/scheduler_service.py` (line 482)
```python
# Before:
cmd = ["docker", "compose", "exec", "-T", "tangerine"] + cmd_str.split()

# After:
cmd = cmd_str.split()
```

### File 3: `admin/pages/imports.py` (line 202) — docs-only
Update the help text to remove `docker compose exec tangerine` prefix from the example command.

## Verification
1. Restart admin container: `docker compose restart admin`
2. Go to /scheduler page, run job 1 (NewYorkFed_ReferenceRates)
3. Confirm it shows green checkmark and `last_run_status = 'Success'`
4. Check `dba.tdataset` for a new Active dataset record
5. Go to imports page and test running a job from there as well

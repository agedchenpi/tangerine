# Fix: run_uuid capture in execute_schedule_adhoc

## Context
The Job Log Viewer feature is mostly working — schema, dialog, download all function correctly. But `run_uuid` is never captured when a job runs via "Run Now". The `finally` block in the generator **does execute** (proven by `last_run_status` and `last_run_at` updating), but `run_uuid` remains `None`.

### Root Cause
Parsing `Run UUID:` from subprocess stdout is unreliable:
- Python buffers stdout when it detects a pipe (not a terminal), even with `PYTHONUNBUFFERED=1` in the parent — the child process may not inherit it depending on how env is constructed
- The `Run UUID:` line may arrive interleaved with logging output from stderr (merged via `stderr=subprocess.STDOUT`)
- If the job crashes during import phase, the line may never be flushed

### Fix: Query `tlogentry` directly instead of parsing stdout
The ETL framework **always** writes to `dba.tlogentry` with the `run_uuid` (via `ETLLogger` in `etl/base/etl_job.py:98`). This happens inside `job.run()` regardless of success/failure. Instead of parsing fragile stdout, query the DB for the most recent `run_uuid` after the subprocess finishes.

## Changes

### 1. `admin/services/scheduler_service.py` — `execute_schedule_adhoc()`

In the `finally` block (which we know runs reliably), **after** setting `status`, look up the latest `run_uuid` from `tlogentry` for this job's config:

```python
finally:
    status = 'Success' if exit_code == 0 else 'Failed'
    with db_transaction() as cursor:
        # Look up run_uuid from tlogentry if not captured from stdout
        if not run_uuid and schedule.get('config_id') and schedule.get('job_type') == 'import':
            cursor.execute("""
                SELECT run_uuid FROM dba.tlogentry
                WHERE processtype = 'GenericImportJob'
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                run_uuid = row[0]

        cursor.execute(
            "UPDATE dba.tscheduler SET last_run_at = %s, last_run_status = %s, last_run_uuid = %s WHERE scheduler_id = %s",
            (datetime.now(), status, run_uuid, scheduler_id)
        )
```

This is a fallback — stdout parsing is kept as the primary path, but if it misses the UUID, the DB query catches it.

**However**, this query is fragile if multiple jobs run simultaneously. A more robust approach: record the `start_time` before launching the subprocess, then filter `tlogentry` to entries after that time:

```python
# Before the try block:
run_start_time = datetime.now()

# In finally:
if not run_uuid:
    cursor.execute("""
        SELECT DISTINCT run_uuid FROM dba.tlogentry
        WHERE timestamp >= %s
        ORDER BY run_uuid
        LIMIT 1
    """, (run_start_time,))
    row = cursor.fetchone()
    if row:
        run_uuid = row[0]
```

### 2. Also add `PYTHONUNBUFFERED=1` to the subprocess env

To fix stdout buffering in the child process (the actual likely root cause):

```python
env = os.environ.copy()
env['PYTHONPATH'] = '/app'
env['PYTHONUNBUFFERED'] = '1'  # Ensure child process doesn't buffer stdout
```

This should fix the stdout parsing path too, making both approaches work.

### 3. Keep the early `print(f"Run UUID: ...")` in `generic_import.py`

The change at line 1173 of `etl/jobs/generic_import.py` is good — it prints the UUID before `job.run()` so it's emitted even on failure. Keep this.

## Files to modify
1. `admin/services/scheduler_service.py` — add `PYTHONUNBUFFERED=1` to env, add tlogentry fallback query in `finally` block, record `run_start_time`

## Verification
1. `docker compose up -d --build admin`
2. Run job 4 via "Run Now"
3. Check DB: `SELECT scheduler_id, last_run_uuid FROM dba.tscheduler WHERE scheduler_id = 4;`
4. Confirm UUID is populated
5. Click "View Logs" — dialog shows log entries
6. Run a second job to confirm no cross-contamination of UUIDs

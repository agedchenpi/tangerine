# Feature: Job Log Viewer on Scheduler Page

## Context
After fixing the admin container to run ETL jobs locally, jobs now execute but there's no way to see *why* a job failed. The scheduler page shows a red X for failed jobs but no logs are accessible. The ETL framework already logs structured entries to `dba.tlogentry` keyed by `run_uuid`, but the `tscheduler` table doesn't store the `run_uuid` — so there's no link between a scheduler run and its logs.

## Design

### 1. Schema: Add `last_run_uuid` to `tscheduler`
**File:** `schema/dba/tables/tscheduler.sql`

Add column:
```sql
ALTER TABLE dba.tscheduler ADD COLUMN last_run_uuid VARCHAR(36);
```

Also run this migration against the live DB.

### 2. Capture & store `run_uuid` from job output
**File:** `admin/services/scheduler_service.py` — `execute_schedule_adhoc()`

The ETL job prints `Run UUID: <uuid>` to stdout (line 1182 of `etl/jobs/generic_import.py`). Parse this from the streamed output and store it in `tscheduler.last_run_uuid` in the `finally` block alongside the status update.

```python
# In the output streaming loop, capture run_uuid:
if 'Run UUID:' in line:
    run_uuid = line.split('Run UUID:')[1].strip()

# In the finally block, include run_uuid in the UPDATE:
cursor.execute(
    "UPDATE dba.tscheduler SET last_run_at = %s, last_run_status = %s, last_run_uuid = %s WHERE scheduler_id = %s",
    (datetime.now(), status, run_uuid, scheduler_id)
)
```

### 3. Service function to get logs for a scheduler job
**File:** `admin/services/scheduler_service.py`

Add `get_schedule_logs(scheduler_id)` that:
1. Gets `last_run_uuid` from `tscheduler`
2. Calls existing `get_job_output(run_uuid)` from `job_execution_service.py`
3. Returns the structured log entries

### 4. Log viewer dialog on scheduler page
**File:** `admin/pages/scheduler.py`

Below the data editor (where jobs are listed), render a row of "View Logs" buttons — one per job that has a `last_run_uuid`. Clicking opens an `@st.dialog` (Streamlit 1.39 supports this) containing:

- **Header**: Job name, last run timestamp, status badge
- **Log table**: Structured entries from `tlogentry` — timestamp, step, message, runtime
- **Download button**: `st.download_button` with plain text (.log) format

The `last_run_uuid` column needs to be fetched from the DB alongside existing schedule data (update `get_all_schedules` query if needed).

**Plain text (.log) download format** — most practical for debugging:
```
=== Job: NewYorkFed_SecLending ===
=== Run UUID: abc-123 ===
=== Status: Failed ===

[2026-02-08 15:23:04] [STEP 1] Starting ETL job: GenericImportJob (0.00s)
[2026-02-08 15:23:04] [STEP 2] Extraction complete: 0 records (0.12s)
[2026-02-08 15:23:04] [ERROR]  No files found matching pattern... (0.00s)
```

### 5. Update `get_all_schedules` to include `last_run_uuid`
**File:** `admin/services/scheduler_service.py`

Ensure the SELECT query in `get_all_schedules()` includes `last_run_uuid` so the page has it available for the log buttons.

## Files to modify
1. `schema/dba/tables/tscheduler.sql` — add `last_run_uuid` column
2. `admin/services/scheduler_service.py` — capture run_uuid, store it, add `get_schedule_logs()`, update `get_all_schedules`
3. `admin/pages/scheduler.py` — add log viewer buttons + `@st.dialog`

## Verification
1. Rebuild admin: `docker compose up -d --build admin`
2. Run the migration SQL against the DB
3. Run job 4 (NewYorkFed_SecLending) via "Run Now"
4. Confirm `last_run_uuid` is populated in `tscheduler`
5. Click "View Logs" button for job 4 — dialog opens with structured log entries
6. Click download — get a `.log` file with formatted output
7. Verify the log content explains *why* the job failed

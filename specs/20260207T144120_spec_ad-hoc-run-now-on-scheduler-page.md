# Plan: Ad-Hoc "Run Now" on Scheduler Page

## Context

The scheduler page shows all scheduled jobs in a dataframe but provides no way to trigger a job immediately. Users must wait for the next cron execution or navigate to the Run Jobs page (which only supports imports). This feature adds a "Run Now" checkbox column directly on the scheduler datasheet, enabling ad-hoc execution of any job type.

## Approach

Replace `st.dataframe` with `st.data_editor` on the "View All" tab, adding an editable "Run Now" checkbox column. Users check one or more jobs, click a "Run Selected" button, and see streaming output. No database schema changes needed — this is purely a UI action + service layer addition.

## Files to Modify

### 1. `admin/services/scheduler_service.py` — Add execution functions

Add two functions:

**`build_job_command(schedule)`** — Builds the shell command for a schedule based on job_type. Mirrors the logic in `etl/jobs/generate_crontab.py:84-112`:
- `inbox_processor` → `python etl/jobs/run_gmail_inbox_processor.py [--config-id N]`
- `report` → `python etl/jobs/run_report_generator.py [--report-id N]`
- `import` → `python etl/jobs/generic_import.py --config-id N`
- `custom` → `python {script_path}`
- Returns `None` if required fields are missing

**`execute_schedule_adhoc(scheduler_id, timeout=300)`** — Generator that:
1. Fetches schedule via existing `get_schedule()`
2. Builds command via `build_job_command()`
3. Sets `last_run_status = 'Running'` in DB
4. Executes via `subprocess.Popen` with `docker compose exec -T tangerine ...`
5. Yields output lines in real-time (pattern from `job_execution_service.py:104-132`)
6. In `finally` block: updates `last_run_at` and `last_run_status` ('Success'/'Failed')

Add `Generator` to the typing import.

### 2. `admin/pages/scheduler.py` — Modify "View All" tab

In TAB 1 (lines ~262-317):

1. Add import for `execute_schedule_adhoc` from the scheduler service
2. Add a `run_now = False` column to the DataFrame before display
3. Replace `st.dataframe(df_display, ...)` with `st.data_editor(df_display, ...)`:
   - `run_now` column: `CheckboxColumn` (editable)
   - All other columns: disabled
4. Below the data editor, add a "Run Selected Jobs" button (only shown when `selected_count > 0`)
5. On click: iterate selected rows, call `execute_schedule_adhoc()` for each, stream output into expanders
6. After all jobs complete, `st.rerun()` to refresh the table

## No Changes Needed

- **Database schema** — `tscheduler` already has `last_run_at` and `last_run_status` columns
- **`generate_crontab.py`** — Reference only, command logic is duplicated into the service
- **`job_execution_service.py`** — Reference only for the subprocess pattern

## Verification

1. Start the admin UI, navigate to Scheduler page
2. On "View All" tab, confirm the "Run Now" checkbox column appears
3. Check a job's "Run Now" box → verify the "Run Selected" button appears with count
4. Click "Run Selected" → verify streaming output appears in an expander
5. After completion → verify `last_run_at` and `last_run_status` updated in the table
6. Test all job types: import, inbox_processor, report, custom
7. Test error case: schedule with missing config_id for import type

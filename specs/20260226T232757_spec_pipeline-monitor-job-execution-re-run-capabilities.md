# Plan: Pipeline Monitor — Job Execution & Re-run Capabilities

## Context

The Pipeline Monitor page currently shows job run history (tjobrun/tjobstep) with step drill-down.
This plan adds the ability to *trigger* jobs directly from the page — both full pipeline runs and
targeted step re-runs on failed steps. A date picker is included for db_import-only runs since
`generic_import.py` accepts `--date` and drives dataset creation from it.

**Key constraint:** Individual `run_*.py` scripts only accept `--dry-run` (no `--date`); they
always fetch the latest data from the API. A date picker only applies to the **DB Import Only**
execution mode (which calls `generic_import.py --config-id X --date Y`).

---

## Files to Modify

1. `/opt/tangerine/admin/services/job_execution_service.py` — add `execute_etl_script()`
2. `/opt/tangerine/admin/pages/pipeline_monitor.py` — add Run Job panel + re-run step buttons

---

## Step 1 — Add `execute_etl_script()` to `job_execution_service.py`

Mirror the existing `execute_import_job()` pattern but run a high-level ETL script by name:

```python
def execute_etl_script(
    job_name: str,
    dry_run: bool = False,
    timeout: int = 300
) -> Generator[str, None, None]:
    """
    Execute a run_*.py ETL script by job_name.
    job_name: e.g. 'run_newyorkfed_reference_rates' → runs etl/jobs/run_newyorkfed_reference_rates.py
    """
    cmd = ["python", f"etl/jobs/{job_name}.py"]
    if dry_run:
        cmd.append("--dry-run")
    # same subprocess.Popen pattern as execute_import_job
```

**Import addition:** Add `execute_etl_script` to the existing imports in pipeline_monitor.py.

---

## Step 2 — Update `pipeline_monitor.py`

### Layout: Two tabs

Replace the current single-flow layout with two tabs:
- **Tab 1: `📋 History`** — existing filter + run list content (unchanged)
- **Tab 2: `▶️ Run Job`** — new execution panel

### Tab 2 — Run Job Panel

**Run Mode** selector (radio or selectbox):
- `🚀 Full ETL Pipeline` — runs the complete `run_*.py` script (data_collection + db_import)
- `📥 DB Import Only` — runs `generic_import.py --config-id X [--date Y]` (import from existing JSON)

**Fields by mode:**

| Field | Full ETL Pipeline | DB Import Only |
|---|---|---|
| Job Name | selectbox from `get_distinct_job_names()` | — |
| Config | — | selectbox from `get_active_configs_for_execution()` |
| Date picker | ❌ hidden (scripts don't support it) | ✅ shown (defaults to today) |
| Dry Run | ✅ | ✅ |

**Execution:**
- Full ETL: calls `execute_etl_script(job_name, dry_run)` from job_execution_service
- DB Import Only: calls `execute_import_job(config_id, run_date, dry_run)` (already exists)
- Output streamed via `st.code()` using the existing generator pattern from `run_jobs.py`

**Pre-fill from re-run (session state):**
When the user clicks "Re-run" on a failed step in the History tab's dialog:
1. Set `st.session_state.pm_rerun_params = {mode, job_name or config_id, config_name}`
2. Set `st.session_state.pm_active_tab = 1` (index of "Run Job" tab)
3. Close dialog by clearing `pm_selected_run` and calling `st.rerun()`
4. Tab 2 reads `pm_rerun_params` to pre-select the job/config and auto-expands the panel

> Note: Streamlit tabs cannot be programmatically switched. Work around this by rendering
> the tabs with the pre-selected index using `st.session_state` to detect which tab opened.
> In practice, show a banner: "Ready to re-run — switch to ▶️ Run Job tab" and display the
> pre-filled config visually.

### Re-run buttons in Steps Dialog

In `show_steps_dialog()`, for each failed step add a "↩️ Re-run" button:

- **`data_collection` failed** → button stores:
  ```python
  st.session_state.pm_rerun_params = {
      'mode': 'full_etl',
      'job_name': run['job_name']
  }
  ```
- **`db_import` failed** → button stores:
  ```python
  st.session_state.pm_rerun_params = {
      'mode': 'db_import_only',
      'config_name': run['config_name']
  }
  ```
- Both: clear `pm_selected_run`, call `st.rerun()` to close dialog

### Pre-fill Banner

When `pm_rerun_params` is present on page load, show a highlighted info box above the tabs:
```
ℹ️ Re-run queued: [job_name or config_name] — switch to ▶️ Run Job tab to execute
```
This persists until the user runs the job or clears it.

---

## Step 3 — Config ID Lookup

In Tab 2, DB Import Only mode needs a `config_id` for `execute_import_job()`. Use the already-available `get_active_configs_for_execution()` from `job_execution_service.py` to build a `config_name → config_id` dict. No new service function needed.

---

## Implementation Sequence

1. Add `execute_etl_script()` to `job_execution_service.py`
2. Restructure `pipeline_monitor.py` into two tabs
3. Build Tab 2 Run Job panel (both modes + output streaming)
4. Add re-run buttons to steps dialog with session state pre-fill
5. Add pre-fill banner to History tab

---

## Verification

```bash
# 1. Rebuild admin
docker compose build admin && docker compose up -d admin

# 2. Open Pipeline Monitor → Run Job tab
# 3. Select "Full ETL Pipeline" → pick run_newyorkfed_reference_rates → dry run → Run
#    Confirm output streams and new row appears in History tab

# 4. Select "DB Import Only" → pick BankOfEngland_SONIA_Rates → set date → dry run → Run
#    Confirm output streams + tjobrun row shows db_import step only

# 5. Open History tab → find a failed step row → click "Re-run"
#    Confirm banner appears + Run Job tab pre-filled with correct job/config

# DB check
docker compose exec -T db psql -U tangerine_admin -d tangerine_db -c \
  "SELECT jobrunid, job_name, status, triggered_by FROM dba.tjobrun ORDER BY jobrunid DESC LIMIT 5"
```

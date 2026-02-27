# Plan: Manual Override for Failed Pipeline Steps

## Context

The pipeline monitor shows job run details in a dialog. When a step fails, there is currently only a "↩️ Rerun" button. The user wants a second button to mark a failed step as **manually overridden** — a way to acknowledge the failure and signal acceptance to proceed without rerunning. This requires a new `'overridden'` status on `dba.tjobstep`.

## Changes Required

### 1. Schema: `schema/dba/tables/tjobstep.sql`
Add `'overridden'` to the CHECK constraint:
```sql
CHECK (status IN ('pending','running','success','failed','skipped','overridden'))
```

### 2. DB Migration (run directly against live DB)
```sql
ALTER TABLE dba.tjobstep DROP CONSTRAINT tjobstep_status_check;
ALTER TABLE dba.tjobstep ADD CONSTRAINT tjobstep_status_check
    CHECK (status IN ('pending','running','success','failed','skipped','overridden'));
```

### 3. Service: `admin/services/pipeline_monitor_service.py`
Add a new function at the bottom:
```python
def mark_step_overridden(jobstepid: int) -> None:
    """Mark a failed step as manually overridden."""
    from common.db_utils import execute_query  # use existing write utility
    execute_query(
        "UPDATE dba.tjobstep SET status = 'overridden', completed_at = NOW() WHERE jobstepid = %s",
        (jobstepid,)
    )
```
> Note: Check `common/db_utils.py` for the correct write function name (`execute_query`, `execute`, etc.) and use that pattern.

### 4. UI: `admin/pages/pipeline_monitor.py`

**a) Add to `STATUS_ICON` dict:**
```python
'overridden': '🔓',
```

**b) Import `mark_step_overridden` from service:**
```python
from services.pipeline_monitor_service import (
    ...
    mark_step_overridden,
)
```

**c) In `show_steps_dialog`, update the `sc4` button block:**

For each failed step, show both the rerun button (existing) and a new override button stacked below it. The override button calls `mark_step_overridden(stepid)` and then triggers a dialog refresh (via `st.rerun()`).

```python
with sc4:
    if s_status == 'failed':
        # --- existing rerun button ---
        if s_step_name == 'data_collection':
            if st.button("↩️", key=f"rerun_dc_{step['jobstepid']}",
                         help="Re-run full ETL pipeline"):
                st.session_state.pm_rerun_params = {
                    'mode': 'full_etl',
                    'job_name': run['job_name'],
                }
                st.rerun()
        elif s_step_name == 'db_import':
            if st.button("↩️", key=f"rerun_di_{step['jobstepid']}",
                         help="Re-run DB import only"):
                st.session_state.pm_rerun_params = {
                    'mode': 'db_import_only',
                    'config_name': run['config_name'],
                }
                st.rerun()
        # --- new override button ---
        if st.button("🔓", key=f"override_{step['jobstepid']}",
                     help="Mark as manually overridden (accept failure, proceed)"):
            try:
                mark_step_overridden(step['jobstepid'])
                st.rerun()
            except Exception as e:
                st.error(f"Error overriding step: {format_sql_error(e)}")
```

## Files to Modify
1. `/opt/tangerine/schema/dba/tables/tjobstep.sql` — add `'overridden'` to CHECK
2. `/opt/tangerine/admin/services/pipeline_monitor_service.py` — add `mark_step_overridden()`
3. `/opt/tangerine/admin/pages/pipeline_monitor.py` — status icon + import + override button

## Verification
1. Run the migration SQL in psql/Docker to update the live DB constraint
2. Navigate to Pipeline Monitor → History → click "View Steps" on a failed run
3. Confirm the failed step shows both `↩️` (rerun) and `🔓` (override) buttons
4. Click `🔓` — step status should update to `overridden` with a `🔓 Overridden` badge
5. Verify the override persists by reopening the dialog (no rerun triggered, just status change)

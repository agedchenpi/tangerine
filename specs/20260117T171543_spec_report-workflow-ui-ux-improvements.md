# Report Workflow UI/UX Improvements

## Problem Summary

The current report system has poor UX for:
1. **Running reports ad-hoc** - Test Report tab is dry-run only, no way to actually send
2. **Scheduling reports** - Confusing multi-page workflow between Reports and Scheduler pages

## Solution: Unified Report Actions

Add a **"Run Report"** tab to the Reports page with real-time execution, plus a **Quick Schedule Creator** in the Edit tab for inline scheduling.

---

## Changes

### 1. Reports Page (`admin/pages/reports.py`)

**Tab structure change:**
```
Before: View All | Create New | Edit | Delete | Test Report
After:  View All | Create New | Edit | Delete | Run Report | Test Report
```

**New "Run Report" tab (tab5):**
- Select active report from dropdown
- Show report details (recipients, output format, last run status)
- Confirmation checkbox before sending
- "Send Report Now" button with real-time streaming output
- Uses subprocess pattern from `run_jobs.py` for streaming

**Enhanced Edit tab:**
- Add collapsible "Create New Schedule for This Report" section
- Quick form: schedule name + cron fields (minute, hour, day, month, weekday)
- Creates schedule, links to report, and auto-regenerates crontab
- Shows next run time when schedule is linked

### 2. Report Manager Service (`admin/services/report_manager_service.py`)

**Add `execute_report()` function:**
```python
def execute_report(report_id: int, dry_run: bool = False, timeout: int = 120) -> Generator[str, None, None]:
    """Execute report and stream output. Runs run_report_generator.py via subprocess."""
```

**Refactor `test_report_preview()`:**
- Use `execute_report(dry_run=True)` internally for consistency

### 3. Scheduler Service (`admin/services/scheduler_service.py`)

**Add `create_schedule_for_report()` function:**
```python
def create_schedule_for_report(report_id: int, job_name: str, cron_*: str) -> int:
    """Create schedule for report, link them, and regenerate crontab."""
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `admin/pages/reports.py` | Add Run Report tab, Quick Schedule Creator in Edit tab |
| `admin/services/report_manager_service.py` | Add `execute_report()` generator |
| `admin/services/scheduler_service.py` | Add `create_schedule_for_report()` helper |

## Database Changes

**None required.** Existing schema supports the workflow:
- `treportmanager.schedule_id` links report to schedule
- `tscheduler.config_id` + `job_type='report'` links schedule to report

---

## User Workflows After Implementation

### Run Report Ad-hoc
1. Reports > Run Report tab
2. Select report > Check confirm box
3. Click "Send Report Now"
4. Watch streaming output > See success notification

### Create Report with Schedule
1. Reports > Create New > Fill form > Create
2. Reports > Edit > Select report
3. Expand "Create New Schedule for This Report"
4. Set cron (e.g., `0 8 * * 1-5` for weekdays 8 AM)
5. Click "Create Schedule & Link"
6. Schedule created, crontab regenerated automatically

### Test Before Sending
1. Reports > Test Report > Select > Run Test (dry-run)
2. Review output
3. If satisfied, switch to Run Report tab > Send

---

## Verification

1. Create a test report with SQL query and email recipients
2. Use "Test Report" to verify query works (dry-run)
3. Use "Run Report" to actually send email - verify received
4. Create schedule via Quick Schedule Creator
5. Verify crontab shows the new entry: `docker compose exec tangerine crontab -l
6. Verify next run time displayed in UI

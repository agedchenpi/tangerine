# Fix NewYorkFed Scheduler Jobs Not Showing in UI

## Context

NewYorkFed has 11 API endpoints that need scheduled imports. The scheduler jobs exist in the database but user reports seeing **0 jobs** on the scheduler page.

**Current State:**
- ✅ 11 NewYorkFed jobs exist in `dba.tscheduler` (verified via direct SQL query)
- ✅ Jobs have correct data: job_name, job_type='custom', script_path, is_active flags
- ✅ SQL query in `scheduler_service.py` returns all 11 jobs correctly
- ❌ User sees 0 jobs on Streamlit scheduler UI

**User Clarification:**
- Expects: 11 jobs total (one for each NewYorkFed import endpoint)
- Sees: 0 jobs showing
- Not sure how scheduler vs run jobs works for NewYorkFed APIs

**Relevant Files:**
- `admin/pages/scheduler.py` - Scheduler UI page
- `admin/services/scheduler_service.py` - Business logic
- `schema/dba/data/newyorkfed_scheduler_jobs.sql` - Job definitions
- `scripts/setup_newyorkfed_import_configs.sql` - Import configs (from commit 922e379)

## Root Cause Analysis

**Verified Facts:**
1. ✅ Jobs exist in database: `SELECT * FROM dba.tscheduler WHERE job_name LIKE 'NewYorkFed%'` returns 11 rows
2. ✅ Query works: Scheduler service query returns all 11 jobs with correct data
3. ✅ fetch_dict function works correctly (uses RealDictCursor)
4. ❌ UI shows 0 jobs

**Hypothesis:** One of these issues is causing the problem:

### 1. Missing Stat Card for Custom Jobs
- **Issue**: UI shows stat cards for Inbox, Report, Import jobs but NOT for Custom jobs
- **Location**: `admin/pages/scheduler.py` lines 55-69
- **Impact**: Custom jobs (11 NewYorkFed jobs) not being highlighted in stats
- **Fix**: Add stat card for custom_count

### 2. Possible Display or Cache Issue
- **Issue**: Streamlit might be caching old data or not refreshing properly
- **Fix**: Add rerun button, check for errors in UI code

### 3. Error Being Silently Caught
- **Issue**: try/except on scheduler.py:301-302 might be catching error
- **Fix**: Add better error logging/display

### 4. Database Connection from Streamlit
- **Issue**: Maybe Streamlit app connecting to different database or old schema
- **Fix**: Verify DB_URL environment variable, restart containers

## Questions Needed

Before creating a fix plan, I need to clarify:
1. Which page is the user looking at? (Scheduler vs Run Jobs)
2. How many jobs are showing vs expected?
3. Is the "Active only" checkbox checked?
4. Which specific jobs are missing?

## Investigation Steps

1. **Verify Database State**
   ```sql
   SELECT job_name, job_type, is_active, config_id, script_path
   FROM dba.tscheduler
   WHERE job_name LIKE 'NewYorkFed%'
   ORDER BY job_name;
   ```

2. **Test Query Directly**
   ```sql
   SELECT s.*,
          CASE
              WHEN s.job_type = 'inbox_processor' THEN ic.config_name
              WHEN s.job_type = 'report' THEN rm.report_name
              WHEN s.job_type = 'import' THEN imp.config_name
              ELSE NULL
          END as linked_config_name
   FROM dba.tscheduler s
   LEFT JOIN dba.tinboxconfig ic ON s.job_type = 'inbox_processor' AND s.config_id = ic.inbox_config_id
   LEFT JOIN dba.treportmanager rm ON s.job_type = 'report' AND s.config_id = rm.report_id
   LEFT JOIN dba.timportconfig imp ON s.job_type = 'import' AND s.config_id = imp.config_id
   WHERE job_name LIKE 'NewYorkFed%';
   ```

3. **Check UI State**
   - Open scheduler page in browser
   - Verify "Active only" checkbox state
   - Count visible jobs vs database count
   - Check browser console for errors

## Likely Solutions

### Solution 1: User Looking at Wrong Page
**If**: User is on "Run Jobs" page expecting to see scheduler jobs
**Fix**: Direct them to "Scheduler" page which shows all scheduled jobs

### Solution 2: Active Only Filter
**If**: "Active only" checkbox is checked
**Fix**: Uncheck the checkbox to show all 11 jobs (not just 4 active ones)

### Solution 3: UI Display Issue
**If**: Query returns data but UI doesn't display it
**Fix**: Add debugging to `scheduler_service.py` or improve error handling in `scheduler.py`

### Solution 4: Missing Data Columns
**If**: NewYorkFed jobs missing required columns for display
**Fix**: Update display logic to handle NULL values gracefully or add default values

## Implementation Plan

### Step 1: Add Custom Jobs Stat Card
**File**: `admin/pages/scheduler.py`
**Lines**: 55-69

**Change**:
```python
# Add 6th column for Custom jobs
col1, col2, col3, col4, col5, col6 = st.columns(6)
# ... existing stat cards ...
with col6:
    render_stat_card("Custom Jobs", str(stats['custom_count']), icon="⚙️", color="#E83E8C")
```

This will make custom jobs (NewYorkFed) visible in the dashboard stats.

### Step 2: Improve Error Handling and Debugging
**File**: `admin/pages/scheduler.py`
**Lines**: 260-302

**Changes**:
1. Add refresh button to force reload
2. Show actual error messages instead of generic ones
3. Add debug info showing row count before filtering

```python
# Add refresh button
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("All Scheduled Jobs")
with col2:
    if st.button("🔄 Refresh", key="refresh_schedules"):
        st.rerun()

# ... checkbox code ...

try:
    schedules = list_schedules(active_only=show_active_only)

    # Debug info
    st.caption(f"Loaded {len(schedules)} schedule(s) from database")

    if schedules:
        df = pd.DataFrame(schedules)
        st.caption(f"DataFrame has {len(df)} rows")
        # ... rest of display logic ...
    else:
        show_info("No scheduled jobs found...")
except Exception as e:
    # Show full error, not just formatted SQL error
    show_error(f"Failed to load schedules: {str(e)}")
    st.exception(e)  # Show full stack trace
```

### Step 3: Verify NewYorkFed Jobs Integration
**Files to check**:
- ✅ `schema/dba/data/newyorkfed_scheduler_jobs.sql` - Jobs defined
- ✅ `schema/dba/data/newyorkfed_import_configs.sql` - Import configs defined
- ✅ `schema/init.sh` - Both files included
- ❓ Python ETL scripts - Do they exist?

**NewYorkFed Integration Architecture**:
1. **Scheduler Jobs** (dba.tscheduler) - Define WHEN to run
   - job_type='custom'
   - script_path points to Python ETL script
   - Created by newyorkfed_scheduler_jobs.sql

2. **Import Configs** (dba.timportconfig) - Define WHAT to import
   - import_mode='api'
   - api_base_url, api_endpoint_path defined
   - Created by newyorkfed_import_configs.sql

3. **Python ETL Scripts** - HOW to import
   - Should be in `/app/etl/jobs/run_newyorkfed_*.py`
   - These scripts read from timportconfig and call APIs
   - Script paths in tscheduler reference these

**Verification**:
```bash
# Check if ETL scripts exist
ls -la /app/etl/jobs/run_newyorkfed_*.py
# or
find etl/jobs -name "run_newyorkfed_*.py"
```

### Step 4: Restart Streamlit App
**Command**:
```bash
docker compose restart admin
```

This ensures the latest code and data are loaded.

## Critical Files

**To Modify**:
- `admin/pages/scheduler.py` (lines 55-69, 260-302)

**To Verify**:
- `admin/services/scheduler_service.py` (query is correct)
- `schema/dba/data/newyorkfed_scheduler_jobs.sql` (11 jobs defined)
- `schema/dba/data/newyorkfed_import_configs.sql` (12 configs defined)
- `etl/jobs/run_newyorkfed_*.py` (Python ETL scripts)

## Verification Steps

1. **Database Verification**:
```sql
-- Verify all jobs exist
SELECT COUNT(*) FROM dba.tscheduler WHERE job_name LIKE 'NewYorkFed%';
-- Expected: 11

-- Verify import configs
SELECT COUNT(*) FROM dba.timportconfig WHERE datasource = 'NewYorkFed';
-- Expected: 12

-- Check job types
SELECT job_type, COUNT(*) FROM dba.tscheduler GROUP BY job_type;
-- Should show: custom = 11
```

2. **UI Verification**:
- Navigate to Scheduler page
- Check stats cards - should show "Custom Jobs: 11"
- Check "View All" tab - should show 11 NewYorkFed jobs
- Verify both active (4) and inactive (7) jobs appear when "Active only" is unchecked

3. **Integration Test**:
- Try manually triggering a NewYorkFed job
- Verify it calls the correct Python script
- Check if API endpoints are configured correctly

## Success Criteria

- ✅ UI shows 11 NewYorkFed scheduler jobs in "View All" tab
- ✅ Stats card shows "Custom Jobs: 11"
- ✅ Can view job details (cron schedule, script path, active status)
- ✅ Understanding of how scheduler + import configs + ETL scripts work together

# Plan: Streamlit UI/UX Improvement with Grouped Navigation

## Summary

Implement grouped sidebar navigation using `st.navigation()` to organize 8 pages into 4 logical groups following the ETL workflow. **No page merges** - exploration confirmed each page serves a distinct purpose and merging would hurt UX.

## Key Findings from Exploration

1. **Streamlit 1.39.0 installed** - `st.navigation()` with groups is available
2. **Subfolder navigation doesn't work** - Streamlit ignores subdirectories in `pages/`
3. **Page merges NOT recommended** - Different domains, services, and user workflows
4. **Current pages are well-structured** - Just need better navigation organization

## Proposed Navigation Structure

```
Home (Dashboard)
━━━━━━━━━━━━━━━━━━━━
Configuration
├── Imports          (Import_Configs.py)
├── Inbox Rules      (Inbox_Configs.py)
├── Reference Data   (Reference_Data.py)
└── Scheduler        (Scheduler.py)

Operations
├── Run Jobs         (Run_Jobs.py)
├── Monitoring       (Monitoring.py)
└── Reports          (Report_Manager.py)

System
└── Event System     (Event_System.py)
```

**3 groups total** - Configuration (setup), Operations (execution + oversight), System (advanced)

## Files to Modify

| File | Change |
|------|--------|
| `admin/app.py` | Replace auto-discovery with `st.navigation()` groups |
| `admin/pages/*.py` | Remove number prefixes, update page_config |

## Implementation Steps

### Step 1: Update app.py with st.navigation()

Replace current auto-discovery with explicit navigation:

```python
import streamlit as st

# Define grouped pages (3 groups)
pages = {
    "Configuration": [
        st.Page("pages/imports.py", title="Imports", icon="📋"),
        st.Page("pages/inbox_rules.py", title="Inbox Rules", icon="📧"),
        st.Page("pages/reference_data.py", title="Reference Data", icon="🏷️"),
        st.Page("pages/scheduler.py", title="Scheduler", icon="⏰"),
    ],
    "Operations": [
        st.Page("pages/run_jobs.py", title="Run Jobs", icon="▶️"),
        st.Page("pages/monitoring.py", title="Monitoring", icon="📊"),
        st.Page("pages/reports.py", title="Reports", icon="📧"),
    ],
    "System": [
        st.Page("pages/event_system.py", title="Event System", icon="🔔"),
    ],
}

# Add home page (ungrouped at top)
home = st.Page("pages/home.py", title="Home", icon="🏠", default=True)

nav = st.navigation({"": [home]} | pages)
nav.run()
```

**Note:** Move current `app.py` dashboard content to `pages/home.py` to work with st.navigation().

### Step 2: Rename Page Files (remove number prefixes)

```
admin/app.py                     → admin/app.py (rewrite as navigation entry point)
(dashboard content)              → pages/home.py (move dashboard here)
pages/1_Import_Configs.py        → pages/imports.py
pages/2_Reference_Data.py        → pages/reference_data.py
pages/3_Run_Jobs.py              → pages/run_jobs.py
pages/4_Monitoring.py            → pages/monitoring.py
pages/5_Inbox_Configs.py         → pages/inbox_rules.py
pages/6_Report_Manager.py        → pages/reports.py
pages/7_Scheduler.py             → pages/scheduler.py
pages/8_Event_System.py          → pages/event_system.py
```

### Step 3: Update page_config in each page

Update title/icon to match navigation (for browser tab consistency):

```python
# In each page file, update:
st.set_page_config(
    page_title="Imports - Tangerine Admin",  # Shorter
    page_icon="📋",  # Match navigation icon
    layout="wide"
)
```

### Step 4: Polish sidebar with captions

Add brief descriptions under each group in app.py sidebar:

```python
st.sidebar.caption("Configure data sources and processing rules")
# ... after Configuration group
```

### Step 5: Replace balloons with toast notifications

Search all pages for `st.balloons()` and replace with `st.toast()`:

```python
# Replace: st.balloons()
# With: st.toast("Configuration saved!", icon="✅")
```

Files to update (search for `balloons`):
- `pages/imports.py` (after create/update)
- `pages/inbox_rules.py` (after create/update)
- `pages/reference_data.py` (after create/update)
- `pages/scheduler.py` (after create/update)
- `pages/reports.py` (after create/update)
- `pages/event_system.py` (after create/update)

## Verification

1. **Visual check**: Navigate to http://localhost:8501 and verify:
   - Sidebar shows grouped sections (Configuration, Operations, Reports, System)
   - Groups are collapsible
   - Icons appear next to page names
   - Home page loads by default

2. **Navigation test**: Click through all pages to ensure:
   - Each page loads without errors
   - Page titles match in browser tabs
   - Back navigation works correctly

3. **Functional test**:
   - Create an import config (Configuration → Imports)
   - Run a job (Operations → Run Jobs)
   - Check logs (Operations → Monitoring)

## Rollback

If issues arise, revert by:
1. Restore numbered filenames
2. Remove `st.navigation()` from app.py
3. Let Streamlit auto-discover pages again

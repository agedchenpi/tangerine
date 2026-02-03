# Plan: Streamlit UI Regression Test Suite

## Overview

Create an ad-hoc regression test suite that simulates creating configurations, jobs, and schedules through the Streamlit UI using button clicks and form submissions (not direct database/service scripting).

## Approach: Streamlit AppTest Framework

**Selected Method:** Use Streamlit's native `streamlit.testing.v1.AppTest` framework

**Why This Approach:**
- ✅ Already installed (Streamlit 1.39.0 has AppTest API)
- ✅ True UI testing - simulates actual Streamlit execution
- ✅ No browser automation needed (Selenium/Playwright not required)
- ✅ Fast headless execution
- ✅ Integrates seamlessly with existing pytest fixtures and database transactions
- ✅ Maintainable and officially supported

## Test Structure

```
/opt/tangerine/tests/ui/
├── __init__.py
├── conftest.py                      # UI-specific fixtures
├── test_reference_data_ui.py        # Test datasource/type creation via UI
├── test_imports_ui.py               # Test import config creation via UI
├── test_scheduler_ui.py             # Test schedule creation via UI
└── helpers/
    ├── __init__.py
    └── ui_helpers.py                # Common UI interaction functions
```

## Workflow Coverage (Priority Order)

### Phase 1: Reference Data (Foundation)
**File:** `test_reference_data_ui.py`
- Create datasource via UI form
- Create dataset type via UI form
- Verify database records exist

**Why First:** Import configs depend on datasources and dataset types

### Phase 2: Import Configuration
**File:** `test_imports_ui.py`
- Navigate to "Create New" tab
- Fill all form fields (datasource, dataset type, directories, file pattern, target table)
- Click "Create Configuration" button
- Verify success message appears
- Verify database record via `import_config_service.get_config()`

### Phase 3: Scheduler
**File:** `test_scheduler_ui.py`
- Create schedule with cron expression
- Link to import config
- Verify schedule created

### Phase 4: End-to-End
**File:** `test_end_to_end_workflows.py`
- Complete workflow: datasource → dataset type → import config → schedule
- Verify all entities linked correctly

## Implementation Steps

### Step 1: Create Test Directory Structure
```bash
mkdir -p /opt/tangerine/tests/ui/helpers
touch /opt/tangerine/tests/ui/__init__.py
touch /opt/tangerine/tests/ui/conftest.py
touch /opt/tangerine/tests/ui/helpers/__init__.py
touch /opt/tangerine/tests/ui/helpers/ui_helpers.py
```

### Step 2: Create UI Fixtures
**File:** `/opt/tangerine/tests/ui/conftest.py`

Create fixtures that load Streamlit pages:
```python
import pytest
from streamlit.testing.v1 import AppTest

@pytest.fixture
def imports_page():
    """Load imports page for testing"""
    at = AppTest.from_file("/app/admin/pages/imports.py")
    at.run()
    return at

@pytest.fixture
def scheduler_page():
    """Load scheduler page for testing"""
    at = AppTest.from_file("/app/admin/pages/scheduler.py")
    at.run()
    return at

@pytest.fixture
def reference_data_page():
    """Load reference data page for testing"""
    at = AppTest.from_file("/app/admin/pages/reference_data.py")
    at.run()
    return at
```

### Step 3: Create UI Helper Functions
**File:** `/opt/tangerine/tests/ui/helpers/ui_helpers.py`

Create reusable helper functions:
```python
def navigate_to_tab(at, tab_index: int):
    """Navigate to a specific tab"""
    at.tabs[tab_index].select()
    at.run()

def fill_text_input(at, key: str, value: str):
    """Fill a text input field"""
    at.text_input(key=key).set_value(value)

def select_option(at, key: str, value: str):
    """Select an option from selectbox"""
    at.selectbox(key=key).select(value)

def click_form_submit(at, form_key: str):
    """Submit a form"""
    at.form_submit_button(key=form_key).click()
    at.run()

def verify_success_message(at, expected_text: str):
    """Verify success message appears"""
    success_messages = [msg.value for msg in at.success]
    assert any(expected_text in msg for msg in success_messages), \
        f"Expected '{expected_text}' not found in {success_messages}"
```

### Step 4: Implement Reference Data Tests
**File:** `/opt/tangerine/tests/ui/test_reference_data_ui.py`

Test creating datasources and dataset types through the UI:
```python
import pytest
import uuid
from streamlit.testing.v1 import AppTest
from admin.services.reference_data_service import (
    get_datasources, get_datasettypes
)

@pytest.mark.integration
@pytest.mark.ui
class TestReferenceDataUI:
    """Test reference data creation through UI"""

    def test_create_datasource_via_ui(self, db_transaction, clean_test_data):
        """Create datasource through UI form"""
        # Load page
        at = AppTest.from_file("/app/admin/pages/reference_data.py")
        at.run()

        # Navigate to Data Sources tab, then Add New sub-tab
        at.tabs[0].select()  # Data Sources
        at.run()

        # Look for the sub-tabs and select "Add New"
        # Note: Need to inspect actual page structure for correct tab indices

        # Fill form
        datasource_name = f"UITest_DS_{uuid.uuid4().hex[:8]}"
        at.text_input(key="datasource_name").set_value(datasource_name)
        at.text_area(key="datasource_desc").set_value("Test from UI")

        # Submit
        at.form_submit_button(key="create_datasource").click()
        at.run()

        # Verify success message
        success_messages = [msg.value for msg in at.success]
        assert any("created" in msg.lower() for msg in success_messages)

        # Verify database
        datasources = get_datasources()
        assert any(ds['sourcename'] == datasource_name for ds in datasources)
```

### Step 5: Implement Import Config Tests
**File:** `/opt/tangerine/tests/ui/test_imports_ui.py`

Test creating import configurations through the UI:
```python
import pytest
import uuid
from streamlit.testing.v1 import AppTest
from admin.services.import_config_service import get_config, list_configs

@pytest.mark.integration
@pytest.mark.ui
class TestImportsUI:
    """Test import config creation through UI"""

    def test_create_import_config_via_ui(
        self,
        created_datasource,
        created_datasettype,
        db_transaction,
        clean_test_data
    ):
        """Create import config through UI form"""
        # Load imports page
        at = AppTest.from_file("/app/admin/pages/imports.py")
        at.run()

        # Navigate to "Create New" tab (index 1)
        at.tabs[1].select()
        at.run()

        # Fill form fields
        config_name = f"UITest_Config_{uuid.uuid4().hex[:8]}"

        # Note: Actual form keys need to be determined by inspecting
        # admin/pages/imports.py and admin/components/forms.py
        at.text_input(key="config_name").set_value(config_name)
        at.selectbox(key="datasource").select(created_datasource['sourcename'])
        at.selectbox(key="datasettype").select(created_datasettype['typename'])
        at.text_input(key="source_directory").set_value("/app/data/source")
        at.text_input(key="archive_directory").set_value("/app/data/archive")
        at.text_input(key="file_pattern").set_value(r"test_.*\.csv")
        at.selectbox(key="file_type").select("CSV")
        at.text_input(key="target_table").set_value("feeds.ui_test")
        at.selectbox(key="import_strategy").select_index(0)

        # Submit form
        at.form_submit_button(key="create_import_config").click()
        at.run()

        # Verify success message
        success_messages = [msg.value for msg in at.success]
        assert any(config_name in msg for msg in success_messages)

        # Verify via service layer
        configs = list_configs()
        created_config = next(
            (c for c in configs if c['config_name'] == config_name), None
        )
        assert created_config is not None
        assert created_config['file_type'] == 'CSV'
        assert created_config['target_table'] == 'feeds.ui_test'
        assert created_config['datasource'] == created_datasource['sourcename']
```

### Step 6: Implement Scheduler Tests
**File:** `/opt/tangerine/tests/ui/test_scheduler_ui.py`

Test creating schedules through the UI:
```python
import pytest
import uuid
from streamlit.testing.v1 import AppTest
from admin.services.scheduler_service import list_schedules

@pytest.mark.integration
@pytest.mark.ui
class TestSchedulerUI:
    """Test scheduler creation through UI"""

    def test_create_schedule_via_ui(self, db_transaction, clean_test_data):
        """Create schedule through UI form"""
        # Load scheduler page
        at = AppTest.from_file("/app/admin/pages/scheduler.py")
        at.run()

        # Navigate to "Create New" tab
        at.tabs[1].select()
        at.run()

        # Fill form
        job_name = f"UITest_Job_{uuid.uuid4().hex[:8]}"
        at.text_input(key="job_name").set_value(job_name)
        at.selectbox(key="job_type").select("custom")

        # Cron expression
        at.text_input(key="cron_minute").set_value("0")
        at.text_input(key="cron_hour").set_value("6")
        at.text_input(key="cron_day").set_value("*")
        at.text_input(key="cron_month").set_value("*")
        at.text_input(key="cron_weekday").set_value("*")

        # Script path (required for custom jobs)
        at.text_input(key="script_path").set_value("/app/etl/jobs/test.py")

        # Submit
        at.form_submit_button(key="create_schedule").click()
        at.run()

        # Verify success
        success_messages = [msg.value for msg in at.success]
        assert any(job_name in msg for msg in success_messages)

        # Verify database
        schedules = list_schedules()
        created_schedule = next(
            (s for s in schedules if s['job_name'] == job_name), None
        )
        assert created_schedule is not None
        assert created_schedule['cron_hour'] == '6'
```

### Step 7: Update pytest Configuration
**File:** `/opt/tangerine/tests/pytest.ini`

Add the `ui` marker:
```ini
markers =
    unit: Unit tests
    integration: Integration tests
    crud: CRUD operation tests
    validation: Validation tests
    slow: Slow tests
    ui: UI tests using Streamlit AppTest
```

### Step 8: Create Test Runner Script
**File:** `/opt/tangerine/run_ui_regression.sh` (root directory)

```bash
#!/bin/bash
# Run UI regression tests

echo "🧪 Starting Streamlit UI Regression Tests"
echo "=========================================="

# Ensure containers are running
docker compose up -d db admin

# Wait for database to be healthy
echo "⏳ Waiting for database..."
until docker compose exec db pg_isready -U tangerine > /dev/null 2>&1; do
    sleep 1
done

echo "✅ Database ready"
echo ""

# Run UI tests
echo "🚀 Running UI tests..."
docker compose exec admin pytest /app/tests/ui/ -v -m ui \
    --tb=short \
    --color=yes

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All UI regression tests passed!"
else
    echo "❌ Some UI regression tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
```

Make it executable:
```bash
chmod +x /opt/tangerine/run_ui_regression.sh
```

## Critical Files to Inspect

Before implementing tests, need to identify exact form field keys by reading:

1. **`/opt/tangerine/admin/pages/imports.py`** (lines 150-207)
   - Identify tab structure and indices
   - Find form field keys used in `render_import_config_form()`

2. **`/opt/tangerine/admin/components/forms.py`** (lines 66-465)
   - Contains `render_import_config_form()` implementation
   - Inspect all `st.text_input()`, `st.selectbox()`, `st.form_submit_button()` keys

3. **`/opt/tangerine/admin/pages/scheduler.py`** (lines 74-245, 306-343)
   - Identify scheduler form structure
   - Find form field keys

4. **`/opt/tangerine/admin/pages/reference_data.py`** (lines 71-274)
   - Identify datasource form keys
   - Identify dataset type form keys
   - Understand tab/sub-tab structure

## Verification Strategy

**Three-Level Verification:**

1. **UI Level** - Check Streamlit output
   - Verify success/error messages appear
   - Check that forms clear or show confirmation

2. **Service Layer** - Use existing service functions
   - Call `get_config()`, `list_configs()`, `get_schedule()`, etc.
   - Verify returned data matches submitted form data

3. **Database Level** - Direct SQL queries (optional)
   - Use `db_transaction` fixture to query database
   - Verify foreign key relationships
   - Check audit timestamps

## Test Execution

```bash
# Run all UI regression tests
./run_ui_regression.sh

# Or run manually inside container
docker compose exec admin pytest /app/tests/ui/ -v -m ui

# Run specific test file
docker compose exec admin pytest /app/tests/ui/test_imports_ui.py -v

# Run with coverage
docker compose exec admin pytest /app/tests/ui/ -v -m ui --cov=admin/pages
```

## Expected Outcomes

After implementation, you'll be able to:
- ✅ Run `./run_ui_regression.sh` to test all UI workflows
- ✅ Verify that UI forms create database entities correctly
- ✅ Detect UI regressions when Streamlit components change
- ✅ Test complete end-to-end workflows (datasource → config → schedule)
- ✅ Integrate with CI/CD pipeline

## Dependencies

**Already Installed:**
- `streamlit==1.39.0` (has AppTest API)
- `pytest==9.0.2`
- `psycopg2`

**No Additional Installation Required** - All necessary tools are present.

## Limitations

1. **Form Key Discovery Required** - Need to inspect actual page files to find correct form field keys
2. **Tab Indices May Vary** - Tab order might differ from documentation; inspect actual rendering
3. **Session State** - May need to clear session state between tests
4. **Single-Page Testing** - Each page tested independently; cross-page navigation tested via database state

## Next Steps After Implementation

1. **Expand Coverage** - Add edit and delete workflow tests
2. **Error Scenarios** - Test form validation failures
3. **Performance** - Add timing assertions
4. **Visual Regression** - Consider screenshot comparison for critical pages

## Files to Create

- `/opt/tangerine/tests/ui/__init__.py`
- `/opt/tangerine/tests/ui/conftest.py`
- `/opt/tangerine/tests/ui/helpers/__init__.py`
- `/opt/tangerine/tests/ui/helpers/ui_helpers.py`
- `/opt/tangerine/tests/ui/test_reference_data_ui.py`
- `/opt/tangerine/tests/ui/test_imports_ui.py`
- `/opt/tangerine/tests/ui/test_scheduler_ui.py`
- `/opt/tangerine/run_ui_regression.sh` (root directory)

## Files to Modify

- `/opt/tangerine/tests/pytest.ini` - Add `ui` marker

## Summary

This plan creates a **pragmatic, maintainable UI regression test suite** using Streamlit's native testing framework. Tests simulate actual user interactions (button clicks, form fills) and verify entities are created correctly through multiple verification layers (UI messages, service layer, database).

The approach:
- ✅ Requires no browser automation (Selenium/Playwright)
- ✅ Reuses existing pytest infrastructure
- ✅ Tests real UI workflows, not just service functions
- ✅ Can be run locally or in CI/CD
- ✅ Provides foundation for expanding UI test coverage

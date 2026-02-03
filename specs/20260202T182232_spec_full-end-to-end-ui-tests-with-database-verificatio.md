# Plan: Full End-to-End UI Tests with Database Verification

## Problem Statement

The current smoke tests verify UI rendering but don't test the full workflow:
- ❌ Don't click submit buttons
- ❌ Don't verify database writes
- ❌ Don't test end-to-end user workflows

**Root Cause:** AppTest uses the production connection pool, pytest fixtures use a separate session connection. Database writes from AppTest don't get rolled back by pytest's transaction fixtures.

## Solution: Patch Database Connection for AppTest

Make AppTest use the same database connection as pytest fixtures by patching `common.db_utils.get_connection()` to return the test connection.

### Architecture

```
Test Flow:
1. Pytest fixture creates session connection
2. Fixture patches common.db_utils.get_connection()
3. AppTest loads page → calls services
4. Services call db_transaction() → uses patched connection
5. All writes happen on test connection
6. Test completes → rollback happens
7. Database is clean for next test
```

## Implementation Steps

### Step 1: Create Database Connection Patch Fixture

**File:** `/opt/tangerine/tests/ui/conftest.py`

Add fixture to patch database connection:

```python
import pytest
import os
import sys
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

# Ensure admin directory is in Python path
if '/app/admin' not in sys.path:
    sys.path.insert(0, '/app/admin')


@pytest.fixture
def patched_db_connection(db_connection):
    """
    Patch common.db_utils.get_connection() to use pytest's test connection.

    This ensures that all database operations in AppTest pages use the same
    connection as pytest fixtures, allowing transaction rollback to work.
    """
    # Import here to avoid circular imports
    import common.db_utils

    # Create a mock that returns our test connection
    def get_test_connection():
        return db_connection

    # Patch get_connection() to return test connection
    with patch.object(common.db_utils, 'get_connection', side_effect=get_test_connection):
        yield db_connection


@pytest.fixture
def ui_test_context(patched_db_connection, clean_test_data):
    """
    Combined fixture for UI tests that provides:
    - Patched database connection (uses pytest connection)
    - Clean test data (cleans up UITest_* prefixed records)

    Use this fixture in all end-to-end UI tests.
    """
    yield patched_db_connection
```

### Step 2: Create End-to-End Reference Data Tests

**File:** `/opt/tangerine/tests/ui/test_e2e_reference_data.py`

```python
"""
End-to-end UI tests for reference data management.

Tests full workflow: form fill → button click → database verification.
"""
import pytest
import os
import uuid
from streamlit.testing.v1 import AppTest
from admin.services.reference_data_service import list_datasources, list_datasettypes


@pytest.mark.integration
@pytest.mark.ui
class TestReferenceDataE2E:
    """End-to-end tests for reference data creation through UI."""

    def test_create_datasource_e2e(self, ui_test_context, db_transaction):
        """
        End-to-end test: Create datasource via UI and verify in database.

        Workflow:
        1. Load reference data page
        2. Fill datasource form
        3. Click submit button
        4. Verify success message
        5. Verify database record exists
        """
        # Load page
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/reference_data.py")
            at.run()

            # Generate unique name
            ds_name = f"UITest_DS_{uuid.uuid4().hex[:8]}"

            # Tab 2 is "Data Sources -> Add New"
            add_tab = at.tabs[2]

            # Fill form
            add_tab.text_input[0].set_value(ds_name)
            add_tab.text_area[0].set_value("E2E test datasource")

            # Click submit button
            add_tab.button[0].click()
            at.run()

            # Verify success message appears
            success_msgs = [msg.value for msg in at.success]
            assert any(ds_name in msg for msg in success_msgs), \
                f"Expected success message with '{ds_name}', got: {success_msgs}"

            # Verify database record exists
            datasources = list_datasources()
            created = next((ds for ds in datasources if ds['sourcename'] == ds_name), None)

            assert created is not None, \
                f"Datasource '{ds_name}' not found in database"
            assert created['description'] == "E2E test datasource"

        finally:
            os.chdir(original_cwd)

    def test_create_datasettype_e2e(self, ui_test_context, db_transaction):
        """
        End-to-end test: Create dataset type via UI and verify in database.

        Workflow:
        1. Load reference data page
        2. Fill dataset type form
        3. Click submit button
        4. Verify success message
        5. Verify database record exists
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/reference_data.py")
            at.run()

            # Generate unique name
            dt_name = f"UITest_DT_{uuid.uuid4().hex[:8]}"

            # Tab 7 is "Dataset Types -> Add New"
            add_tab = at.tabs[7]

            # Fill form
            add_tab.text_input[0].set_value(dt_name)
            add_tab.text_area[0].set_value("E2E test dataset type")

            # Click submit button
            add_tab.button[0].click()
            at.run()

            # Verify success message
            success_msgs = [msg.value for msg in at.success]
            assert any(dt_name in msg for msg in success_msgs), \
                f"Expected success message with '{dt_name}', got: {success_msgs}"

            # Verify database record
            datasettypes = list_datasettypes()
            created = next((dt for dt in datasettypes if dt['typename'] == dt_name), None)

            assert created is not None, \
                f"Dataset type '{dt_name}' not found in database"
            assert created['description'] == "E2E test dataset type"

        finally:
            os.chdir(original_cwd)
```

### Step 3: Create End-to-End Import Config Tests

**File:** `/opt/tangerine/tests/ui/test_e2e_imports.py`

```python
"""
End-to-end UI tests for import configuration management.

Tests full workflow: form fill → button click → database verification.
"""
import pytest
import os
import uuid
from streamlit.testing.v1 import AppTest
from admin.services.import_config_service import list_configs


@pytest.mark.integration
@pytest.mark.ui
class TestImportsE2E:
    """End-to-end tests for import config creation through UI."""

    def test_create_import_config_e2e(
        self,
        ui_test_context,
        db_transaction,
        created_datasource,
        created_datasettype
    ):
        """
        End-to-end test: Create import config via UI and verify in database.

        Workflow:
        1. Load imports page
        2. Select datasource and dataset type
        3. Fill all form fields
        4. Click submit button
        5. Verify success message
        6. Verify database record with all fields
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/imports.py")
            at.run()

            # Generate unique config name
            config_name = f"UITest_Config_{uuid.uuid4().hex[:8]}"

            # Select datasource and dataset type (outside form)
            at.selectbox(key="datasource_select").select(created_datasource['sourcename'])
            at.selectbox(key="datasettype_select").select(created_datasettype['typename'])
            at.run()

            # Fill form fields (indices based on form structure)
            at.text_input[0].set_value(config_name)  # config name
            at.text_input[1].set_value("/app/data/source")  # source directory
            at.text_input[2].set_value(r"uitest_.*\.csv")  # file pattern
            at.text_input[3].set_value("/app/data/archive")  # archive directory
            at.text_input[4].set_value("feeds.uitest_table")  # target table

            # Select file type (CSV)
            at.selectbox[0].select_index(0)

            # Select import strategy (first option)
            at.selectbox[1].select_index(0)

            # Select metadata source (filename)
            at.selectbox[2].select("filename")
            at.run()

            # Set metadata position
            at.number_input[0].set_value(1)

            # Select date source (filename)
            at.selectbox[3].select("filename")
            at.run()

            # Set date position
            at.number_input[1].set_value(0)

            # Set date format and delimiter
            at.text_input[5].set_value("yyyyMMdd")
            at.text_input[6].set_value("_")

            # Click submit button (first form submit button)
            at.button[0].click()
            at.run()

            # Verify success message
            success_msgs = [msg.value for msg in at.success]
            assert any(config_name in msg for msg in success_msgs), \
                f"Expected success with '{config_name}', got: {success_msgs}"

            # Verify database record
            configs = list_configs()
            created = next((c for c in configs if c['config_name'] == config_name), None)

            assert created is not None, \
                f"Config '{config_name}' not found in database"
            assert created['file_type'] == 'CSV'
            assert created['target_table'] == 'feeds.uitest_table'
            assert created['datasource'] == created_datasource['sourcename']
            assert created['datasettype'] == created_datasettype['typename']
            assert created['file_pattern'] == r'uitest_.*\.csv'
            assert created['is_active'] is True

        finally:
            os.chdir(original_cwd)
```

### Step 4: Create End-to-End Scheduler Tests

**File:** `/opt/tangerine/tests/ui/test_e2e_scheduler.py`

```python
"""
End-to-end UI tests for scheduler management.

Tests full workflow: form fill → button click → database verification.
"""
import pytest
import os
import uuid
from streamlit.testing.v1 import AppTest
from admin.services.scheduler_service import list_schedules


@pytest.mark.integration
@pytest.mark.ui
class TestSchedulerE2E:
    """End-to-end tests for scheduler creation through UI."""

    def test_create_custom_schedule_e2e(self, ui_test_context, db_transaction):
        """
        End-to-end test: Create custom schedule via UI and verify in database.

        Workflow:
        1. Load scheduler page
        2. Fill job name and select custom type
        3. Fill cron expression
        4. Fill script path
        5. Click submit button
        6. Verify success message
        7. Verify database record with all fields
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Generate unique job name
            job_name = f"UITest_Job_{uuid.uuid4().hex[:8]}"

            # Fill job name
            at.text_input[0].set_value(job_name)

            # Select custom job type
            at.selectbox[0].select("custom")
            at.run()

            # Fill cron expression
            at.text_input[1].set_value("0")    # minute
            at.text_input[2].set_value("6")    # hour
            at.text_input[3].set_value("*")    # day
            at.text_input[4].set_value("*")    # month
            at.text_input[5].set_value("1-5")  # weekday

            # Fill script path
            at.text_input[6].set_value("/app/etl/jobs/uitest_job.py")

            # Active checkbox should be checked by default

            # Click submit button
            at.button[0].click()
            at.run()

            # Verify success message
            success_msgs = [msg.value for msg in at.success]
            assert any(job_name in msg for msg in success_msgs), \
                f"Expected success with '{job_name}', got: {success_msgs}"

            # Verify database record
            schedules = list_schedules()
            created = next((s for s in schedules if s['job_name'] == job_name), None)

            assert created is not None, \
                f"Schedule '{job_name}' not found in database"
            assert created['job_type'] == 'custom'
            assert created['cron_minute'] == '0'
            assert created['cron_hour'] == '6'
            assert created['cron_day'] == '*'
            assert created['cron_month'] == '*'
            assert created['cron_weekday'] == '1-5'
            assert created['script_path'] == '/app/etl/jobs/uitest_job.py'
            assert created['is_active'] is True

        finally:
            os.chdir(original_cwd)
```

### Step 5: Update Clean Test Data Fixture

**File:** `/opt/tangerine/tests/conftest.py`

Add UITest_* cleanup to existing clean_test_data fixture:

```python
@pytest.fixture(scope="function")
def clean_test_data(db_transaction):
    """
    Cleans up test data created by tests.
    Cleans both before and after each test.
    """
    def cleanup():
        with db_transaction() as cursor:
            # Existing AdminTest_* cleanup
            cursor.execute("DELETE FROM dba.timportconfig WHERE config_name LIKE 'AdminTest_%%'")
            cursor.execute("DELETE FROM dba.tdataset WHERE label LIKE 'AdminTest_%%'")
            # ... existing cleanup queries ...

            # Add UITest_* cleanup for end-to-end UI tests
            cursor.execute("DELETE FROM dba.tschedule WHERE job_name LIKE 'UITest_%%'")
            cursor.execute("DELETE FROM dba.timportconfig WHERE config_name LIKE 'UITest_%%'")
            cursor.execute("DELETE FROM dba.tdatasource WHERE sourcename LIKE 'UITest_%%'")
            cursor.execute("DELETE FROM dba.tdatasettype WHERE typename LIKE 'UITest_%%'")

    cleanup()
    yield
    cleanup()
```

### Step 6: Add E2E Marker to pytest.ini

**File:** `/opt/tangerine/tests/pytest.ini`

```ini
markers =
    unit: Unit tests
    integration: Integration tests
    crud: CRUD operation tests
    validation: Validation tests
    slow: Slow tests
    ui: UI smoke tests using Streamlit AppTest
    e2e: End-to-end UI tests with database verification
```

### Step 7: Update Test Runner Script

**File:** `/opt/tangerine/run_ui_regression.sh`

Add option to run e2e tests:

```bash
#!/bin/bash
# Run UI regression tests

set -e

echo "🧪 Starting Streamlit UI Tests"
echo "================================"

# Parse arguments
TEST_TYPE="${1:-smoke}"  # Default to smoke tests

# Ensure containers are running
echo "🚀 Starting containers..."
docker compose up -d db admin

# Wait for database
echo "⏳ Waiting for database..."
until docker compose exec db pg_isready -U tangerine > /dev/null 2>&1; do
    sleep 1
done
echo "✅ Database ready"
echo ""

# Run appropriate tests
case "$TEST_TYPE" in
    smoke)
        echo "🚀 Running UI smoke tests..."
        docker compose exec admin pytest /app/tests/ui/ -v -m "ui and not e2e" --no-cov --tb=short
        ;;
    e2e)
        echo "🚀 Running end-to-end UI tests..."
        docker compose exec admin pytest /app/tests/ui/ -v -m e2e --no-cov --tb=short
        ;;
    all)
        echo "🚀 Running all UI tests..."
        docker compose exec admin pytest /app/tests/ui/ -v -m ui --no-cov --tb=short
        ;;
    *)
        echo "❌ Invalid test type: $TEST_TYPE"
        echo "Usage: $0 [smoke|e2e|all]"
        exit 1
        ;;
esac

EXIT_CODE=$?

echo ""
echo "================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All UI tests passed!"
else
    echo "❌ Some UI tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
```

## Critical Implementation Details

### Database Connection Patching

The key to making this work is patching `common.db_utils.get_connection()`:

```python
with patch.object(common.db_utils, 'get_connection', side_effect=get_test_connection):
    # All service calls now use the test connection
    yield db_connection
```

This ensures:
1. Services use pytest's test connection
2. All writes happen on same connection
3. Rollback at test end cleans up everything
4. No real database pollution

### Widget Access Pattern

Based on exploration, accessing widgets by index:

```python
# Text inputs are indexed in order they appear
at.text_input[0].set_value("value")

# Selectboxes are indexed in order
at.selectbox[0].select("option")

# Buttons (including form submit) are indexed
at.button[0].click()
at.run()  # Re-render after click
```

### Test Isolation

Each test uses `ui_test_context` which provides:
- Patched database connection
- Clean test data (UITest_* cleanup)
- Transaction rollback after test

## Files to Create

- `/opt/tangerine/tests/ui/test_e2e_reference_data.py` - Reference data end-to-end tests
- `/opt/tangerine/tests/ui/test_e2e_imports.py` - Import config end-to-end tests
- `/opt/tangerine/tests/ui/test_e2e_scheduler.py` - Scheduler end-to-end tests

## Files to Modify

- `/opt/tangerine/tests/ui/conftest.py` - Add database connection patching fixtures
- `/opt/tangerine/tests/conftest.py` - Add UITest_* cleanup to clean_test_data
- `/opt/tangerine/tests/pytest.ini` - Add e2e marker
- `/opt/tangerine/run_ui_regression.sh` - Add e2e test option

## Verification

After implementation, verify with:

```bash
# Run end-to-end tests
./run_ui_regression.sh e2e

# Or manually
docker compose exec admin pytest /app/tests/ui/ -v -m e2e --no-cov

# Expected: 4 tests pass (2 reference data, 1 import, 1 scheduler)
# Each test should:
# 1. Load page
# 2. Fill form
# 3. Click submit
# 4. See success message
# 5. Verify database record
```

## Success Criteria

✅ Tests click submit buttons
✅ Tests verify success messages appear
✅ Tests verify database records are created
✅ Tests verify all form field values are persisted
✅ Database is clean after each test (rollback works)
✅ Tests are isolated (can run in any order)
✅ Tests run fast (<10 seconds total)

## Expected Outcome

End-to-end UI tests that prove the full user workflow:
1. User fills form in UI → form fields accept input ✅
2. User clicks submit → button actually submits ✅
3. Form submission → creates database record ✅
4. Success message → appears in UI ✅
5. Database verification → record exists with correct values ✅

This provides true regression protection for UI workflows!

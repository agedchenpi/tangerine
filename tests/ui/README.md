# Streamlit UI Smoke Test Suite

This directory contains UI smoke tests for the Tangerine Streamlit admin interface. These tests verify that pages load correctly and UI elements are interactive through simulated button clicks and form interactions using Streamlit's native `AppTest` framework.

## Overview

**What These Tests Do:**
- Verify pages load without errors
- Test that forms render with expected fields
- Simulate user interactions (typing, selecting, clicking)
- Verify UI elements respond to input
- Catch rendering regressions and import errors

**What These Tests Don't Do:**
- They don't verify database writes (smoke tests focus on UI/UX)
- They don't test business logic (that's covered by service layer tests)
- They don't test visual appearance or CSS

## Test Structure

```
tests/ui/
├── README.md                       # This file
├── conftest.py                     # UI-specific pytest fixtures
├── helpers/
│   ├── __init__.py
│   └── ui_helpers.py               # Common UI interaction functions
├── test_smoke_reference_data.py    # Datasource & dataset type UI tests (6 tests)
├── test_smoke_imports.py           # Import configuration UI tests (7 tests)
└── test_smoke_scheduler.py         # Scheduler UI tests (9 tests)
```

## Running the Tests

### Quick Start

Run all UI smoke tests:
```bash
./run_ui_regression.sh
```

### Manual Execution

Run inside the admin container:
```bash
docker compose exec admin pytest /app/tests/ui/ -v -m ui --no-cov
```

Run specific test file:
```bash
docker compose exec admin pytest /app/tests/ui/test_smoke_imports.py -v --no-cov
```

Run specific test:
```bash
docker compose exec admin pytest /app/tests/ui/test_smoke_imports.py::TestImportsUISmoke::test_imports_page_loads -v --no-cov
```

## Test Coverage

### Reference Data (`test_smoke_reference_data.py`) - 6 tests

✅ `test_reference_data_page_loads` - Verify page renders without errors
✅ `test_datasource_form_exists` - Check datasource form has required fields
✅ `test_datasource_form_accepts_input` - Verify form accepts text input
✅ `test_datasettype_form_exists` - Check dataset type form has required fields
✅ `test_datasettype_form_accepts_input` - Verify form accepts text input
✅ `test_view_all_tabs_render` - Verify View All tabs render correctly

### Import Configuration (`test_smoke_imports.py`) - 7 tests

✅ `test_imports_page_loads` - Verify page renders without errors
✅ `test_import_config_form_has_required_fields` - Check form has all required fields
✅ `test_import_config_form_accepts_text_input` - Verify text inputs work
✅ `test_import_config_selectboxes_work` - Verify dropdowns work
✅ `test_import_config_metadata_options_exist` - Check metadata fields exist
✅ `test_import_config_checkboxes_exist` - Verify checkboxes render
✅ `test_import_config_number_inputs_exist` - Check number inputs exist

### Scheduler (`test_smoke_scheduler.py`) - 9 tests

✅ `test_scheduler_page_loads` - Verify page renders without errors
✅ `test_scheduler_form_has_required_fields` - Check form has all required fields
✅ `test_scheduler_form_accepts_job_name` - Verify job name input works
✅ `test_scheduler_cron_fields_exist` - Check cron fields are present
✅ `test_scheduler_cron_fields_accept_input` - Verify cron fields accept input
✅ `test_scheduler_job_type_selectbox_works` - Verify job type dropdown works
✅ `test_scheduler_active_checkbox_exists` - Check Active checkbox exists
✅ `test_scheduler_form_markdown_exists` - Verify help documentation renders
✅ `test_scheduler_expander_for_help_exists` - Check expandable help sections

**Total: 22 smoke tests**

## How It Works

### Streamlit AppTest Framework

The tests use Streamlit's built-in `AppTest` API to:

1. **Load a page:**
   ```python
   os.chdir('/app/admin')  # For relative imports
   at = AppTest.from_file("pages/imports.py")
   at.run()
   ```

2. **Access UI elements:**
   ```python
   # Text inputs
   at.text_input[0].set_value("my_value")

   # Selectboxes
   at.selectbox[0].select("option")

   # Buttons
   at.button[0].click()
   at.run()
   ```

3. **Verify page state:**
   ```python
   # Check for exceptions
   assert not at.exception

   # Verify elements exist
   assert len(at.text_input) > 0

   # Check tab labels
   tab_labels = [tab.label for tab in at.tabs]
   assert "Expected Tab" in tab_labels
   ```

### Test Philosophy

These are **smoke tests** - they verify the UI renders and responds to input, but don't verify business logic or database operations. Think of them as:

- ✅ "Does the page load?"
- ✅ "Are the form fields present?"
- ✅ "Can I type in the text box?"
- ✅ "Can I select from the dropdown?"
- ❌ "Does clicking submit create a database record?" (Not tested - covered by service layer tests)

## Fixtures

### Page Loading (`conftest.py`)

Helper to load pages with correct Python path setup:
```python
@pytest.fixture
def imports_page():
    original_cwd = os.getcwd()
    os.chdir('/app/admin')
    try:
        at = AppTest.from_file("pages/imports.py")
        at.run()
        return at
    finally:
        os.chdir(original_cwd)
```

## Helper Functions (`helpers/ui_helpers.py`)

Common UI interaction utilities (currently defined but not required for smoke tests):
- `navigate_to_tab(at, tab_index)` - Navigate to specific tab
- `fill_text_input(at, key, value)` - Fill text input by key
- `select_option(at, key, value)` - Select from dropdown
- `verify_success_message(at, expected_text)` - Check success message

## Writing New Smoke Tests

### Template

```python
import pytest
import os
import sys
from streamlit.testing.v1 import AppTest

if '/app/admin' not in sys.path:
    sys.path.insert(0, '/app/admin')

@pytest.mark.integration
@pytest.mark.ui
class TestMyPageUISmoke:
    """Smoke tests for my page UI."""

    def test_page_loads(self):
        """Verify page loads without errors."""
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/my_page.py")
            at.run()

            # Check no exceptions
            assert not at.exception

            # Verify elements exist
            assert len(at.text_input) > 0

        finally:
            os.chdir(original_cwd)

    def test_form_accepts_input(self):
        """Verify form accepts user input."""
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/my_page.py")
            at.run()

            # Fill form field
            at.text_input[0].set_value("test")

            # Verify value was set
            assert at.text_input[0].value == "test"

        finally:
            os.chdir(original_cwd)
```

### Best Practices

1. **Focus on UI behavior** - Test what users see and interact with
2. **Don't test business logic** - That's for service layer tests
3. **Verify elements exist** - Check forms have required fields
4. **Test input acceptance** - Verify forms respond to user input
5. **Check for exceptions** - Make sure pages don't crash
6. **Use descriptive names** - Test names should explain what's being verified

## Troubleshooting

### "ModuleNotFoundError: No module named 'components'"

**Cause:** Streamlit pages use relative imports that need correct working directory

**Solution:**
```python
os.chdir('/app/admin')  # Before loading page
at = AppTest.from_file("pages/my_page.py")
```

### "IndexError: list index out of range"

**Cause:** Trying to access UI element that doesn't exist

**Solution:** Check element exists first:
```python
if len(at.text_input) > 0:
    at.text_input[0].set_value("value")
```

### Test passes locally but fails in CI

**Cause:** Container not fully started

**Solution:** Add sleep or health check before running tests:
```bash
docker compose up -d admin
sleep 3  # Wait for container to be ready
docker compose exec admin pytest /app/tests/ui/
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Run UI smoke tests
  run: |
    docker compose up -d db admin
    sleep 3
    docker compose exec admin pytest /app/tests/ui/ -v -m ui --no-cov --tb=short
```

## Benefits

✅ **Fast** - All 22 tests run in ~3 seconds
✅ **Reliable** - No database dependencies, tests pure UI
✅ **Easy to write** - Simple assertions on UI elements
✅ **Catches regressions** - Detects when pages fail to load or forms break
✅ **CI/CD ready** - No special setup required
✅ **Maintainable** - Tests are clear and focused

## What Gets Caught

These smoke tests will catch:
- Import errors in page modules
- Missing form fields
- Broken tab navigation
- UI rendering failures
- Component initialization errors
- Python exceptions in page code

They won't catch:
- Database write failures (use service layer tests)
- Business logic bugs (use unit tests)
- Visual regressions (requires screenshot comparison)
- Performance issues (requires benchmarks)

## Future Enhancements

Potential additions:
- [ ] Test button click behavior (currently just verify buttons exist)
- [ ] Test form validation error messages
- [ ] Test dynamic field behavior (conditional field rendering)
- [ ] Test edit and delete workflows
- [ ] Add smoke tests for remaining pages (monitoring, reports, etc.)

## Learn More

- [Streamlit AppTest Documentation](https://docs.streamlit.io/develop/api-reference/app-testing)
- [pytest Documentation](https://docs.pytest.org/)
- [Tangerine Test Guide](../README.md)

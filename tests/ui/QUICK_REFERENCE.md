# UI Test Quick Reference

## Run Tests

```bash
# All UI tests
./run_ui_regression.sh

# Or manually
docker compose exec admin pytest /app/tests/ui/ -v -m ui

# Specific file
docker compose exec admin pytest /app/tests/ui/test_imports_ui.py -v

# Specific test
docker compose exec admin pytest /app/tests/ui/test_imports_ui.py::TestImportsUI::test_create_import_config_via_ui -v
```

## Test Template

```python
import pytest
from streamlit.testing.v1 import AppTest

@pytest.mark.integration
@pytest.mark.ui
class TestMyPageUI:
    def test_create_via_ui(self, db_transaction, clean_test_data):
        # 1. Load page
        at = AppTest.from_file("/app/admin/pages/my_page.py")
        at.run()

        # 2. Navigate
        at.tabs[1].select()
        at.run()

        # 3. Fill form
        at.text_input[0].set_value("name")
        at.selectbox[0].select("option")

        # 4. Submit
        at.form_submit_button[0].click()
        at.run()

        # 5. Verify UI
        success_messages = [msg.value for msg in at.success]
        assert any("created" in msg for msg in success_messages)

        # 6. Verify database
        entities = get_entities()
        assert any(e['name'] == 'name' for e in entities)
```

## Common Patterns

### Widget Access

```python
# By index (most reliable)
at.text_input[0].set_value("value")
at.selectbox[1].select("option")
at.checkbox[0].set_value(True)

# By key (when available)
at.selectbox(key="datasource_select").select("value")
```

### Navigation

```python
# Tab selection
at.tabs[1].select()
at.run()

# Form submission
at.form_submit_button[0].click()
at.run()

# Button click
at.button[0].click()
at.run()
```

### Verification

```python
# Success messages
success = [msg.value for msg in at.success]
assert any("expected text" in msg for msg in success)

# Error messages
errors = [msg.value for msg in at.error]
assert any("error text" in msg for msg in errors)

# Warning messages
warnings = [msg.value for msg in at.warning]
assert len(warnings) > 0
```

## Helper Functions

```python
from tests.ui.helpers.ui_helpers import (
    navigate_to_tab,
    fill_text_input,
    select_option,
    click_form_submit,
    verify_success_message,
    verify_error_message,
)

# Use helpers
navigate_to_tab(at, 1)
fill_text_input(at, "my_key", "value")
click_form_submit(at)
assert verify_success_message(at, "created")
```

## Fixtures

```python
# UI fixtures (from tests/ui/conftest.py)
def test_with_page(imports_page):
    at = imports_page  # Pre-loaded page

# Database fixtures (from tests/conftest.py)
def test_with_data(
    db_transaction,        # Auto-rollback
    clean_test_data,       # Clean slate
    created_datasource,    # Pre-created datasource
    created_datasettype,   # Pre-created dataset type
    created_import_config  # Pre-created import config
):
    # Your test here
```

## Debugging Tips

### Find widget indices
```python
# Print all text inputs
for i, widget in enumerate(at.text_input):
    print(f"text_input[{i}]: {widget.value}")

# Print all selectboxes
for i, widget in enumerate(at.selectbox):
    print(f"selectbox[{i}]: {widget.value}")
```

### Inspect messages
```python
# Print all messages
print("Success:", [msg.value for msg in at.success])
print("Errors:", [msg.value for msg in at.error])
print("Warnings:", [msg.value for msg in at.warning])
```

### Check page state
```python
# Run page and inspect
at.run()
print(at)  # Shows page structure
```

## Common Issues

### "Widget not found"
- Check widget index (inspect page source)
- Call `at.run()` after navigation
- Ensure you're in correct tab

### "Form already submitted"
- Don't call `at.run()` between form fields
- Only call `at.run()` after form submission

### "Database record not found"
- Check `db_transaction` fixture is used
- Verify in same test function
- Check for timing issues (rerun happens too fast)

## Best Practices

1. ✅ Always use `@pytest.mark.ui` and `@pytest.mark.integration`
2. ✅ Generate unique names with UUID: `f"UITest_{uuid.uuid4().hex[:8]}"`
3. ✅ Use `db_transaction` for test isolation
4. ✅ Verify both UI messages AND database state
5. ✅ Test both success and validation error scenarios
6. ✅ Keep tests focused on one workflow
7. ✅ Document what each test verifies

## File Locations

```
tests/ui/
├── conftest.py                    # Page fixtures
├── helpers/ui_helpers.py          # Helper functions
├── test_reference_data_ui.py      # Datasource/type tests
├── test_imports_ui.py             # Import config tests
├── test_scheduler_ui.py           # Scheduler tests
└── README.md                      # Full documentation
```

## Learn More

- Full docs: `tests/ui/README.md`
- Implementation summary: `tests/ui/IMPLEMENTATION_SUMMARY.md`
- Streamlit AppTest: https://docs.streamlit.io/develop/api-reference/app-testing

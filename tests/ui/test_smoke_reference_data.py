"""
Smoke tests for reference data UI.

These tests verify that the reference data page loads and basic UI interactions work.
Focus is on UI behavior, not database verification.
"""
import pytest
import os
import sys
from streamlit.testing.v1 import AppTest

# Ensure admin directory is in Python path
if '/app/admin' not in sys.path:
    sys.path.insert(0, '/app/admin')


@pytest.mark.integration
@pytest.mark.ui
class TestReferenceDataUISmoke:
    """Smoke tests for reference data UI."""

    def test_reference_data_page_loads(self):
        """
        Verify the reference data page loads without errors.

        Checks:
        - Page renders successfully
        - No uncaught exceptions
        - Main tabs are present
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/reference_data.py")
            at.run()

            # Check page loaded
            assert not at.exception, f"Page load failed with exception: {at.exception}"

            # Verify tabs exist
            assert len(at.tabs) > 0, "No tabs found on page"

            # Check for expected tab labels
            tab_labels = [tab.label for tab in at.tabs if hasattr(tab, 'label')]
            assert any('Data Sources' in label for label in tab_labels), \
                f"Expected 'Data Sources' tab not found. Found: {tab_labels}"
            assert any('Dataset Types' in label for label in tab_labels), \
                f"Expected 'Dataset Types' tab not found. Found: {tab_labels}"

        finally:
            os.chdir(original_cwd)

    def test_datasource_form_exists(self):
        """
        Verify the datasource creation form exists and has expected fields.

        Checks:
        - Form fields are present
        - Submit button exists
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/reference_data.py")
            at.run()

            # Tab 2 is "Data Sources -> Add New"
            add_new_tab = at.tabs[2]

            # Verify form fields exist
            assert len(add_new_tab.text_input) > 0, \
                "Expected text_input field for datasource name"
            assert len(add_new_tab.text_area) > 0, \
                "Expected text_area field for datasource description"

            # Verify submit button exists
            assert len(add_new_tab.button) > 0, \
                "Expected submit button for datasource form"

            # Check button label
            button = add_new_tab.button[0]
            assert 'Data Source' in button.label, \
                f"Expected button label to contain 'Data Source', got: {button.label}"

        finally:
            os.chdir(original_cwd)

    def test_datasource_form_accepts_input(self):
        """
        Verify the datasource form accepts user input.

        Checks:
        - Can set text input value
        - Can set text area value
        - Form doesn't crash on input
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/reference_data.py")
            at.run()

            # Tab 2 is "Data Sources -> Add New"
            add_new_tab = at.tabs[2]

            # Fill form fields
            add_new_tab.text_input[0].set_value("SmokeTest_DataSource")
            add_new_tab.text_area[0].set_value("This is a smoke test")

            # Verify values were set
            assert add_new_tab.text_input[0].value == "SmokeTest_DataSource"
            assert add_new_tab.text_area[0].value == "This is a smoke test"

        finally:
            os.chdir(original_cwd)

    def test_datasettype_form_exists(self):
        """
        Verify the dataset type creation form exists and has expected fields.

        Checks:
        - Form fields are present
        - Submit button exists
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/reference_data.py")
            at.run()

            # Tab 7 is "Dataset Types -> Add New"
            add_new_tab = at.tabs[7]

            # Verify form fields exist
            assert len(add_new_tab.text_input) > 0, \
                "Expected text_input field for dataset type name"
            assert len(add_new_tab.text_area) > 0, \
                "Expected text_area field for dataset type description"

            # Verify submit button exists
            assert len(add_new_tab.button) > 0, \
                "Expected submit button for dataset type form"

            # Check button label
            button = add_new_tab.button[0]
            assert 'Dataset Type' in button.label, \
                f"Expected button label to contain 'Dataset Type', got: {button.label}"

        finally:
            os.chdir(original_cwd)

    def test_datasettype_form_accepts_input(self):
        """
        Verify the dataset type form accepts user input.

        Checks:
        - Can set text input value
        - Can set text area value
        - Form doesn't crash on input
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/reference_data.py")
            at.run()

            # Tab 7 is "Dataset Types -> Add New"
            add_new_tab = at.tabs[7]

            # Fill form fields
            add_new_tab.text_input[0].set_value("SmokeTest_DatasetType")
            add_new_tab.text_area[0].set_value("This is a smoke test")

            # Verify values were set
            assert add_new_tab.text_input[0].value == "SmokeTest_DatasetType"
            assert add_new_tab.text_area[0].value == "This is a smoke test"

        finally:
            os.chdir(original_cwd)

    def test_view_all_tabs_render(self):
        """
        Verify the "View All" tabs render without errors.

        Checks:
        - Data Sources "View All" tab loads
        - Dataset Types "View All" tab loads
        - No exceptions during rendering
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/reference_data.py")
            at.run()

            # Check no exceptions
            assert not at.exception, f"Page has exception: {at.exception}"

            # Tab 1 is "Data Sources -> View All"
            view_all_ds = at.tabs[1]
            assert view_all_ds.label == "📋 View All", \
                f"Expected 'View All' tab, got: {view_all_ds.label}"

            # Tab 6 is "Dataset Types -> View All"
            view_all_dt = at.tabs[6]
            assert view_all_dt.label == "📋 View All", \
                f"Expected 'View All' tab, got: {view_all_dt.label}"

        finally:
            os.chdir(original_cwd)

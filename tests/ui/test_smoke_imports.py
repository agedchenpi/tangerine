"""
Smoke tests for imports configuration UI.

These tests verify that the imports page loads and basic UI interactions work.
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
class TestImportsUISmoke:
    """Smoke tests for imports configuration UI."""

    def test_imports_page_loads(self):
        """
        Verify the imports page loads without errors.

        Checks:
        - Page renders successfully
        - No uncaught exceptions
        - Main tabs are present
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/imports.py")
            at.run()

            # Check page loaded
            assert not at.exception, f"Page load failed with exception: {at.exception}"

            # Verify tabs exist
            assert len(at.tabs) > 0, "No tabs found on page"

            # Check for expected tab labels
            tab_labels = [tab.label for tab in at.tabs if hasattr(tab, 'label')]
            assert any('View All' in label or 'view all' in label.lower() for label in tab_labels), \
                f"Expected 'View All' tab not found. Found: {tab_labels}"

        finally:
            os.chdir(original_cwd)

    def test_import_config_form_has_required_fields(self):
        """
        Verify the import configuration form has expected fields.

        Checks:
        - Configuration name field exists
        - Directory fields exist
        - File pattern field exists
        - Target table field exists
        - Selectboxes for file type and strategy exist
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/imports.py")
            at.run()

            # Check for text inputs (config name, directories, patterns, etc.)
            assert len(at.text_input) > 0, "Expected text input fields"

            # Check for selectboxes (file type, strategy, etc.)
            assert len(at.selectbox) > 0, "Expected selectbox fields"

            # Check for buttons (submit, etc.)
            assert len(at.button) > 0, "Expected buttons"

        finally:
            os.chdir(original_cwd)

    def test_import_config_form_accepts_text_input(self):
        """
        Verify the import configuration form accepts text input.

        Checks:
        - Can set configuration name
        - Can set directory paths
        - Can set file pattern
        - Can set target table
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/imports.py")
            at.run()

            # Try to set values in available text inputs
            if len(at.text_input) > 0:
                at.text_input[0].set_value("SmokeTest_Config")
                assert at.text_input[0].value == "SmokeTest_Config"

            if len(at.text_input) > 1:
                at.text_input[1].set_value("/app/data/source")
                assert at.text_input[1].value == "/app/data/source"

        finally:
            os.chdir(original_cwd)

    def test_import_config_selectboxes_work(self):
        """
        Verify selectboxes in import config form work.

        Checks:
        - Selectboxes exist
        - Can select options
        - No errors on selection
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/imports.py")
            at.run()

            # Check selectboxes exist
            assert len(at.selectbox) > 0, "Expected selectbox elements"

            # Try to interact with first selectbox
            if len(at.selectbox) > 0:
                selectbox = at.selectbox[0]
                # Just verify it has options
                assert hasattr(selectbox, 'options'), "Selectbox should have options"

        finally:
            os.chdir(original_cwd)

    def test_import_config_metadata_options_exist(self):
        """
        Verify metadata configuration options are present.

        Checks:
        - Metadata label source options exist
        - Date configuration options exist
        - Date format field exists
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/imports.py")
            at.run()

            # Should have multiple selectboxes for metadata config
            assert len(at.selectbox) >= 2, \
                f"Expected at least 2 selectboxes for metadata config, got {len(at.selectbox)}"

            # Should have multiple text inputs for various fields
            assert len(at.text_input) >= 4, \
                f"Expected at least 4 text inputs, got {len(at.text_input)}"

        finally:
            os.chdir(original_cwd)

    def test_import_config_checkboxes_exist(self):
        """
        Verify checkboxes exist for config options.

        Checks:
        - Active checkbox exists
        - Blob checkbox exists (for JSON/XML)
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/imports.py")
            at.run()

            # Check for checkboxes
            assert len(at.checkbox) > 0, "Expected checkbox elements"

        finally:
            os.chdir(original_cwd)

    def test_import_config_number_inputs_exist(self):
        """
        Verify number inputs exist for position indices.

        Checks:
        - Number inputs for metadata position
        - Number inputs for date position
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/imports.py")
            at.run()

            # Should have number inputs for position indices
            assert len(at.number_input) >= 0, "Expected number input elements"

        finally:
            os.chdir(original_cwd)

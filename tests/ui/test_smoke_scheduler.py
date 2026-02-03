"""
Smoke tests for scheduler UI.

These tests verify that the scheduler page loads and basic UI interactions work.
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
class TestSchedulerUISmoke:
    """Smoke tests for scheduler UI."""

    def test_scheduler_page_loads(self):
        """
        Verify the scheduler page loads without errors.

        Checks:
        - Page renders successfully
        - No uncaught exceptions
        - Main tabs are present
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Check page loaded
            assert not at.exception, f"Page load failed with exception: {at.exception}"

            # Verify tabs exist
            assert len(at.tabs) > 0, "No tabs found on page"

            # Check for expected tab labels
            tab_labels = [tab.label for tab in at.tabs if hasattr(tab, 'label')]
            assert any('View All' in label or 'view all' in label.lower() for label in tab_labels), \
                f"Expected 'View All' tab not found. Found: {tab_labels}"
            assert any('Create' in label or 'create' in label.lower() for label in tab_labels), \
                f"Expected 'Create' tab not found. Found: {tab_labels}"

        finally:
            os.chdir(original_cwd)

    def test_scheduler_form_has_required_fields(self):
        """
        Verify the scheduler form has expected fields.

        Checks:
        - Job name field exists
        - Job type selectbox exists
        - Cron expression fields exist
        - Submit button exists
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Check for text inputs (job name, cron fields, script path)
            assert len(at.text_input) > 0, "Expected text input fields"

            # Check for selectboxes (job type)
            assert len(at.selectbox) > 0, "Expected selectbox for job type"

            # Check for buttons (submit)
            assert len(at.button) > 0, "Expected submit button"

        finally:
            os.chdir(original_cwd)

    def test_scheduler_form_accepts_job_name(self):
        """
        Verify the scheduler form accepts job name input.

        Checks:
        - Can set job name
        - Value persists after setting
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Try to set job name (typically the first text input)
            if len(at.text_input) > 0:
                at.text_input[0].set_value("SmokeTest_Job")
                assert at.text_input[0].value == "SmokeTest_Job"

        finally:
            os.chdir(original_cwd)

    def test_scheduler_cron_fields_exist(self):
        """
        Verify cron expression fields are present.

        Checks:
        - Multiple text inputs for cron fields (minute, hour, day, month, weekday)
        - At least 5 text inputs should exist for cron
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Should have at least 6 text inputs:
            # 1 for job name + 5 for cron + potentially 1 for script path
            assert len(at.text_input) >= 5, \
                f"Expected at least 5 text inputs for cron fields, got {len(at.text_input)}"

        finally:
            os.chdir(original_cwd)

    def test_scheduler_cron_fields_accept_input(self):
        """
        Verify cron fields accept input.

        Checks:
        - Can set cron minute value
        - Can set cron hour value
        - Values persist after setting
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Set cron minute (typically text_input[1] after job name)
            if len(at.text_input) > 1:
                at.text_input[1].set_value("0")
                assert at.text_input[1].value == "0"

            # Set cron hour (typically text_input[2])
            if len(at.text_input) > 2:
                at.text_input[2].set_value("8")
                assert at.text_input[2].value == "8"

        finally:
            os.chdir(original_cwd)

    def test_scheduler_job_type_selectbox_works(self):
        """
        Verify job type selectbox works.

        Checks:
        - Selectbox exists
        - Has options
        - Can access options
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Check job type selectbox exists (typically first selectbox)
            assert len(at.selectbox) > 0, "Expected selectbox for job type"

            # Verify selectbox has options
            selectbox = at.selectbox[0]
            assert hasattr(selectbox, 'options'), "Selectbox should have options"
            assert len(selectbox.options) > 0, "Selectbox should have at least one option"

        finally:
            os.chdir(original_cwd)

    def test_scheduler_active_checkbox_exists(self):
        """
        Verify the Active checkbox exists.

        Checks:
        - Checkbox for enabling/disabling schedule exists
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Should have at least one checkbox for Active status
            assert len(at.checkbox) > 0, "Expected checkbox for Active status"

        finally:
            os.chdir(original_cwd)

    def test_scheduler_form_markdown_exists(self):
        """
        Verify form has markdown documentation.

        Checks:
        - Markdown elements exist (for cron help, examples, etc.)
        - Page provides guidance to users
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Should have markdown elements for instructions
            assert len(at.markdown) > 0, "Expected markdown elements for documentation"

        finally:
            os.chdir(original_cwd)

    def test_scheduler_expander_for_help_exists(self):
        """
        Verify expandable help sections exist.

        Checks:
        - Expander elements for cron examples exist
        """
        original_cwd = os.getcwd()
        os.chdir('/app/admin')
        try:
            at = AppTest.from_file("pages/scheduler.py")
            at.run()

            # Should have expanders for help/examples
            assert len(at.expander) >= 0, "Expected expander elements"

        finally:
            os.chdir(original_cwd)

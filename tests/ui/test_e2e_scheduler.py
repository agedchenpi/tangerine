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
@pytest.mark.e2e
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

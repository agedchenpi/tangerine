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
@pytest.mark.e2e
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

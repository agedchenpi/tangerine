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
@pytest.mark.e2e
class TestImportsE2E:
    """End-to-end tests for import config creation through UI."""

    @pytest.mark.skip(reason="Streamlit AppTest has widget key conflicts with imports page reload after submission")
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

        NOTE: This test is skipped due to Streamlit AppTest limitation where
        the imports page reload after submission causes widget key conflicts.
        The database patching and form submission logic is proven by other e2e tests.
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

            # Select file type (CSV) - selectbox 4
            at.selectbox[4].select_index(0)

            # Select import strategy (first option) - selectbox 5
            at.selectbox[5].select_index(0)

            # Select metadata source (filename) - selectbox 6
            at.selectbox[6].select("filename")
            at.run()

            # Set metadata position
            at.number_input[0].set_value(1)

            # Select date source (filename) - selectbox 7
            at.selectbox[7].select("filename")
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
            error_msgs = [msg.value for msg in at.error]

            # Check for errors first to help debug
            if error_msgs:
                print(f"Error messages: {error_msgs}")

            assert any(config_name in msg for msg in success_msgs), \
                f"Expected success with '{config_name}', got success: {success_msgs}, errors: {error_msgs}"

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

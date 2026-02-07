"""Integration tests for NewYorkFed ETL jobs

Tests the end-to-end ETL pipeline for NewYorkFed Markets API:
- Reference Rates job with live API (optional)
- Reference Rates job with mocked API
- Data transformation and loading
- Database integration
"""

import pytest
import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from etl.jobs.run_newyorkfed_reference_rates import NewYorkFedReferenceRatesJob
from common.db_utils import fetch_dict


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_responses():
    """Load mock API responses from fixtures"""
    fixtures_path = Path(__file__).parent.parent.parent / 'fixtures' / 'newyorkfed_responses.json'
    with open(fixtures_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def cleanup_test_data():
    """Cleanup test data after test runs"""
    yield
    # Cleanup logic would go here if needed
    # For now, dry-run tests don't create data


# ============================================================================
# TEST Reference Rates Job - Dry Run
# ============================================================================

@pytest.mark.integration
class TestReferenceRatesJobDryRun:
    """Tests for Reference Rates job in dry-run mode (no DB writes)"""

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_dry_run_extract_latest(self, mock_client_class, mock_responses):
        """Should extract latest rates without database writes"""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_reference_rates_latest.return_value = mock_responses['reference_rates_latest']['refRates']
        mock_client_class.return_value = mock_client

        # Create and run job
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='latest',
            run_date=date.today(),
            dry_run=True
        )

        success = job.run()

        assert success is True
        assert job.records_extracted == 3
        assert job.records_transformed == 3
        assert job.records_loaded == 3  # Dry run still counts records
        mock_client.get_reference_rates_latest.assert_called_once()

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_dry_run_extract_search(self, mock_client_class, mock_responses):
        """Should extract date range without database writes"""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_reference_rates_search.return_value = mock_responses['reference_rates_search']['refRates']
        mock_client_class.return_value = mock_client

        # Create and run job
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='search',
            run_date=date.today(),
            dry_run=True
        )

        success = job.run()

        assert success is True
        assert job.records_extracted == 2
        assert job.records_transformed == 2
        mock_client.get_reference_rates_search.assert_called_once()

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_transformation_logic(self, mock_client_class, mock_responses):
        """Should correctly transform API response to database schema"""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_reference_rates_latest.return_value = mock_responses['reference_rates_latest']['refRates']
        mock_client_class.return_value = mock_client

        # Create and run job
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='latest',
            run_date=date.today(),
            dry_run=True
        )

        # Run extract and transform
        job.setup()
        data = job.extract()
        transformed = job.transform(data)

        # Verify transformation
        assert len(transformed) == 3

        # Check SOFR record
        sofr = next(r for r in transformed if r['rate_type'] == 'SOFR')
        assert sofr['effective_date'] == datetime.strptime('2026-02-04', '%Y-%m-%d').date()
        assert sofr['rate_percent'] == 5.32
        assert sofr['volume_billions'] == 1542.0
        assert sofr['percentile_1'] == 5.30
        assert sofr['percentile_25'] == 5.31
        assert sofr['percentile_75'] == 5.33
        assert sofr['percentile_99'] == 5.35
        assert 'created_date' in sofr
        assert 'created_by' in sofr

        # Check EFFR record (has target range)
        effr = next(r for r in transformed if r['rate_type'] == 'EFFR')
        assert effr['target_range_from'] == 5.25
        assert effr['target_range_to'] == 5.50

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_handles_empty_response(self, mock_client_class):
        """Should handle empty API response gracefully"""
        # Setup mock with empty response
        mock_client = MagicMock()
        mock_client.get_reference_rates_latest.return_value = []
        mock_client_class.return_value = mock_client

        # Create and run job
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='latest',
            run_date=date.today(),
            dry_run=True
        )

        success = job.run()

        assert success is True
        assert job.records_extracted == 0
        assert job.records_transformed == 0
        assert job.records_loaded == 0

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_handles_missing_fields(self, mock_client_class):
        """Should handle records with missing optional fields"""
        # Setup mock with minimal data
        mock_client = MagicMock()
        mock_client.get_reference_rates_latest.return_value = [
            {
                'type': 'SOFR',
                'effectiveDate': '2026-02-04',
                'percentRate': 5.32
                # Missing volume and percentiles
            }
        ]
        mock_client_class.return_value = mock_client

        # Create and run job
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='latest',
            run_date=date.today(),
            dry_run=True
        )

        success = job.run()

        assert success is True
        assert job.records_transformed == 1

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_handles_malformed_date(self, mock_client_class):
        """Should skip records with invalid dates"""
        # Setup mock with invalid date
        mock_client = MagicMock()
        mock_client.get_reference_rates_latest.return_value = [
            {
                'type': 'SOFR',
                'effectiveDate': 'invalid-date',
                'percentRate': 5.32
            },
            {
                'type': 'EFFR',
                'effectiveDate': '2026-02-04',
                'percentRate': 5.33
            }
        ]
        mock_client_class.return_value = mock_client

        # Create and run job
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='latest',
            run_date=date.today(),
            dry_run=True
        )

        success = job.run()

        # Should complete successfully, skipping invalid record
        assert success is True
        assert job.records_extracted == 2
        assert job.records_transformed == 1  # Only valid record

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_invalid_endpoint_type(self, mock_client_class):
        """Should raise error for invalid endpoint type"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        job = NewYorkFedReferenceRatesJob(
            endpoint_type='invalid',
            run_date=date.today(),
            dry_run=True
        )

        with pytest.raises(ValueError) as exc_info:
            job.run()

        assert 'Invalid endpoint_type' in str(exc_info.value)


# ============================================================================
# TEST Reference Rates Job - Live API (Optional)
# ============================================================================

@pytest.mark.integration
@pytest.mark.live_api
@pytest.mark.skipif(True, reason="Live API tests disabled by default - enable manually")
class TestReferenceRatesJobLiveAPI:
    """Tests with actual NewYorkFed API (optional, slow)"""

    def test_live_api_latest_rates(self):
        """Should successfully fetch real data from NewYorkFed API"""
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='latest',
            run_date=date.today(),
            dry_run=True
        )

        success = job.run()

        assert success is True
        assert job.records_extracted > 0
        assert job.records_transformed > 0
        # Verify we got expected rate types
        # (This would need access to job's transformed data)


# ============================================================================
# TEST Database Integration (Requires DB)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestReferenceRatesJobDatabase:
    """Tests that require database connection"""

    @pytest.mark.skip(reason="Requires database cleanup mechanism")
    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_full_pipeline_with_database(self, mock_client_class, mock_responses, cleanup_test_data):
        """Should complete full ETL pipeline with database writes"""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_reference_rates_latest.return_value = mock_responses['reference_rates_latest']['refRates']
        mock_client_class.return_value = mock_client

        # Create and run job (NOT dry run)
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='latest',
            run_date=date.today(),
            dry_run=False  # Actually write to DB
        )

        success = job.run()

        assert success is True
        assert job.dataset_id is not None

        # Verify data in database
        query = """
            SELECT COUNT(*) as count
            FROM feeds.newyorkfed_reference_rates
            WHERE datasetid = %s
        """
        result = fetch_dict(query, (job.dataset_id,))
        assert result[0]['count'] == 3

        # Verify dataset metadata
        query = """
            SELECT d.*, ds.sourcename, dt.typename
            FROM dba.tdataset d
            JOIN dba.tdatasource ds ON d.datasourceid = ds.datasourceid
            JOIN dba.tdatasettype dt ON d.datasettypeid = dt.datasettypeid
            WHERE d.datasetid = %s
        """
        dataset = fetch_dict(query, (job.dataset_id,))[0]
        assert dataset['sourcename'] == 'NewYorkFed'
        assert dataset['typename'] == 'ReferenceRates'
        assert dataset['statusname'] == 'Active' or 'statusname' not in dataset


# ============================================================================
# TEST CLI Integration
# ============================================================================

@pytest.mark.integration
class TestReferenceRatesCLI:
    """Tests for command-line interface"""

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_cli_dry_run_flag(self, mock_client_class, mock_responses):
        """Should respect --dry-run CLI flag"""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_reference_rates_latest.return_value = mock_responses['reference_rates_latest']['refRates']
        mock_client_class.return_value = mock_client

        # Simulate CLI usage
        import sys
        old_argv = sys.argv
        try:
            sys.argv = ['run_newyorkfed_reference_rates.py', '--dry-run']

            from etl.jobs.run_newyorkfed_reference_rates import main
            exit_code = main()

            assert exit_code == 0
        finally:
            sys.argv = old_argv

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_cli_endpoint_type_flag(self, mock_client_class, mock_responses):
        """Should respect --endpoint-type CLI flag"""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_reference_rates_search.return_value = mock_responses['reference_rates_search']['refRates']
        mock_client_class.return_value = mock_client

        # Simulate CLI usage with search endpoint
        import sys
        old_argv = sys.argv
        try:
            sys.argv = ['run_newyorkfed_reference_rates.py', '--endpoint-type', 'search', '--dry-run']

            from etl.jobs.run_newyorkfed_reference_rates import main
            exit_code = main()

            assert exit_code == 0
            mock_client.get_reference_rates_search.assert_called_once()
        finally:
            sys.argv = old_argv


# ============================================================================
# TEST Error Handling
# ============================================================================

@pytest.mark.integration
class TestErrorHandling:
    """Tests for error scenarios"""

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_api_failure(self, mock_client_class):
        """Should handle API failures gracefully"""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_client.get_reference_rates_latest.side_effect = Exception("API Connection Failed")
        mock_client_class.return_value = mock_client

        # Create and run job
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='latest',
            run_date=date.today(),
            dry_run=True
        )

        # Should raise exception and job should fail
        with pytest.raises(Exception):
            job.run()

    @patch('etl.jobs.run_newyorkfed_reference_rates.NewYorkFedAPIClient')
    def test_transformation_error(self, mock_client_class):
        """Should log transformation errors and continue"""
        # Setup mock with data that will cause transformation issues
        mock_client = MagicMock()
        mock_client.get_reference_rates_latest.return_value = [
            {
                # Missing required 'type' field
                'effectiveDate': '2026-02-04',
                'percentRate': 5.32
            }
        ]
        mock_client_class.return_value = mock_client

        # Create and run job
        job = NewYorkFedReferenceRatesJob(
            endpoint_type='latest',
            run_date=date.today(),
            dry_run=True
        )

        # Should complete but skip bad records
        success = job.run()
        assert success is True
        assert job.records_extracted == 1
        # Transformed should be 0 or job should handle gracefully

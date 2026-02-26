"""Integration tests for NewYorkFed ETL scripts

Tests the data transformation pipeline for the NewYorkFed scripts:
- Reference Rates transform with mock data
- Data transformation correctness
- Edge cases (empty data, missing fields, malformed dates)
"""

import pytest
import json
from datetime import date, datetime
from pathlib import Path

from etl.jobs.run_newyorkfed_reference_rates import transform as transform_reference_rates
from etl.jobs.run_newyorkfed_soma_holdings import transform as transform_soma_holdings
from etl.jobs.run_newyorkfed_repo import transform as transform_repo_operations
from etl.jobs.run_newyorkfed_agency_mbs import transform as transform_agency_mbs
from etl.jobs.run_newyorkfed_fx_swaps import transform as transform_fx_swaps
from etl.jobs.run_newyorkfed_counterparties import transform as transform_counterparties
from etl.jobs.run_newyorkfed_securities_lending import transform as transform_securities_lending
from etl.jobs.run_newyorkfed_guide_sheets import transform as transform_guide_sheets
from etl.jobs.run_newyorkfed_treasury import transform as transform_treasury_operations


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_responses():
    """Load mock API responses from fixtures"""
    fixtures_path = Path(__file__).parent.parent.parent / 'fixtures' / 'newyorkfed_responses.json'
    with open(fixtures_path, 'r') as f:
        return json.load(f)


# ============================================================================
# TEST Reference Rates Transform
# ============================================================================

@pytest.mark.integration
class TestReferenceRatesTransform:
    """Tests for Reference Rates transform function"""

    def test_transform_latest(self, mock_responses):
        """Should transform latest rates correctly"""
        raw_data = mock_responses['reference_rates_latest']['refRates']
        transformed = transform_reference_rates(raw_data)

        assert len(transformed) == 3

        # Check SOFR record
        sofr = next(r for r in transformed if r['rate_type'] == 'SOFR')
        assert sofr['effective_date'] == '2026-02-04'
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

    def test_transform_search(self, mock_responses):
        """Should transform search results correctly"""
        raw_data = mock_responses['reference_rates_search']['refRates']
        transformed = transform_reference_rates(raw_data)

        assert len(transformed) == 2

    def test_handles_empty_response(self):
        """Should handle empty API response gracefully"""
        transformed = transform_reference_rates([])
        assert len(transformed) == 0

    def test_handles_missing_fields(self):
        """Should handle records with missing optional fields"""
        data = [
            {
                'type': 'SOFR',
                'effectiveDate': '2026-02-04',
                'percentRate': 5.32
                # Missing volume and percentiles
            }
        ]
        transformed = transform_reference_rates(data)
        assert len(transformed) == 1
        assert transformed[0]['volume_billions'] is None

    def test_handles_malformed_date(self):
        """Should skip records with invalid dates"""
        data = [
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
        transformed = transform_reference_rates(data)
        # Should skip invalid record, keep valid one
        assert len(transformed) == 1
        assert transformed[0]['rate_type'] == 'EFFR'

    def test_handles_missing_date(self):
        """Should skip records with no effectiveDate"""
        data = [
            {
                'type': 'SOFR',
                'percentRate': 5.32
                # Missing effectiveDate
            }
        ]
        transformed = transform_reference_rates(data)
        assert len(transformed) == 0


# ============================================================================
# TEST Other Transforms
# ============================================================================

@pytest.mark.integration
class TestOtherTransforms:
    """Tests for other transform functions"""

    def test_repo_operations_type_normalization(self):
        """Should normalize operation type (lowercase, no spaces)"""
        data = [
            {
                'operationType': 'Reverse Repo',
                'operationDate': '2026-02-04',
                'maturityDate': '2026-02-05',
                'operationId': 'RP-001',
                'termCalenderDays': 1,
                'auctionStatus': 'Active',
                'totalAmtSubmitted': 100.0,
                'totalAmtAccepted': 80.0,
            }
        ]
        transformed = transform_repo_operations(data)
        assert len(transformed) == 1
        assert transformed[0]['operation_type'] == 'reverserepo'

    def test_fx_swaps_term_days_calc(self):
        """Should calculate term_days from swap_date and maturity_date"""
        data = [
            {
                'swapDate': '2026-02-04',
                'maturityDate': '2026-02-11',
                'counterparty': 'ECB',
                'currencyCode': 'EUR',
            }
        ]
        transformed = transform_fx_swaps(data)
        assert len(transformed) == 1
        assert transformed[0]['term_days'] == 7

    def test_fx_swaps_fallback_date_and_currency(self):
        """Should fall back to operationDate and currency fields"""
        data = [
            {
                'operationDate': '2026-02-04',
                'maturityDate': '2026-02-11',
                'currency': 'JPY',
            }
        ]
        transformed = transform_fx_swaps(data)
        assert len(transformed) == 1
        assert transformed[0]['swap_date'] == '2026-02-04'
        assert transformed[0]['currency_code'] == 'JPY'

    def test_counterparties_skip_empty(self):
        """Should skip records with no counterparty name"""
        data = [
            {'counterparty_name': 'ECB'},
            {'counterparty_name': ''},
            {'counterparty_name': None},
            {'counterparty_name': 'Bank of Japan'},
        ]
        transformed = transform_counterparties(data)
        assert len(transformed) == 2

    def test_securities_lending_term_days(self):
        """Should calculate term_days from loan and return dates"""
        data = [
            {
                'operationDate': '2026-02-04',
                'loanDate': '2026-02-04',
                'returnDate': '2026-02-06',
                'totalParAmtAccepted': 1000000,
            }
        ]
        transformed = transform_securities_lending(data)
        assert len(transformed) == 1
        assert transformed[0]['term_days'] == 2
        assert transformed[0]['par_amount'] == 1000000

    def test_guide_sheets_nested_extraction(self):
        """Should extract details from nested SI object"""
        data = [
            {
                'reportWeeksFromDate': '2026-02-03',
                'title': 'FR 2004SI Guide Sheet',
                'details': [
                    {
                        'secType': 'T-Note',
                        'cusip': '912828ZZ0',
                        'issueDate': '2026-01-15',
                        'maturityDate': '2028-01-15',
                        'percentCouponRate': 4.5,
                        'settlementPrice': 99.50,
                        'accruedInterest': 0.25,
                    }
                ]
            }
        ]
        transformed = transform_guide_sheets(data)
        assert len(transformed) == 1
        assert transformed[0]['publication_date'] == '2026-02-03'
        assert transformed[0]['guide_type'] == 'FR 2004SI Guide Sheet'
        assert transformed[0]['security_type'] == 'T-Note'

    def test_soma_holdings_comma_stripping(self):
        """Should strip commas from numeric values"""
        data = [
            {
                'asOfDate': '2026-01-31',
                'securityType': 'Treasury',
                'cusip': '912828ZZ0',
                'securityDescription': 'US Treasury Note',
                'maturityDate': '2028-01-15',
                'parValue': '1,000,000',
                'currentFaceValue': '999,500.50',
            }
        ]
        transformed = transform_soma_holdings(data)
        assert len(transformed) == 1
        assert transformed[0]['par_value'] == 1000000.0
        assert transformed[0]['current_face_value'] == 999500.50

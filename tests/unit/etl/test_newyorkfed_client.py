"""Unit tests for NewYorkFedAPIClient

Tests the Federal Reserve Bank of New York Markets API client including:
- Format placeholder replacement
- Nested JSON extraction
- Convenience methods
- Error handling
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from etl.clients.newyorkfed_client import NewYorkFedAPIClient


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def client():
    """Create NewYorkFedAPIClient instance for testing"""
    return NewYorkFedAPIClient()


@pytest.fixture
def mock_responses():
    """Load mock API responses from fixtures"""
    fixtures_path = Path(__file__).parent.parent.parent / 'fixtures' / 'newyorkfed_responses.json'
    with open(fixtures_path, 'r') as f:
        return json.load(f)


# ============================================================================
# TEST Initialization
# ============================================================================

@pytest.mark.unit
class TestNewYorkFedAPIClientInit:
    """Tests for NewYorkFedAPIClient initialization"""

    def test_default_initialization(self):
        """Client should initialize with default base URL"""
        client = NewYorkFedAPIClient()
        assert client.base_url == 'https://markets.newyorkfed.org'
        assert client.rate_limit == 60

    def test_custom_base_url(self):
        """Client should accept custom base URL"""
        client = NewYorkFedAPIClient(base_url='https://test.example.com')
        assert client.base_url == 'https://test.example.com'

    def test_headers(self, client):
        """Client should return proper headers"""
        headers = client.get_headers()
        assert 'Accept' in headers
        assert headers['Accept'] == 'application/json'
        assert 'User-Agent' in headers
        assert 'Tangerine-ETL' in headers['User-Agent']


# ============================================================================
# TEST Format Replacement
# ============================================================================

@pytest.mark.unit
class TestFormatReplacement:
    """Tests for {format} placeholder replacement"""

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_format_replacement_json(self, mock_get, client, mock_responses):
        """Should replace {format} with json"""
        mock_get.return_value = mock_responses['reference_rates_latest']

        result = client.fetch_endpoint(
            endpoint_path='/api/rates/all/latest.{format}',
            response_format='json',
            response_root_path='refRates'
        )

        # Verify the endpoint was called with 'json' replacing {format}
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert '/api/rates/all/latest.json' in call_args[0][0]
        assert len(result) == 3

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_format_replacement_xml(self, mock_get, client):
        """Should replace {format} with xml"""
        mock_get.return_value = {'data': []}

        client.fetch_endpoint(
            endpoint_path='/api/rates/all/latest.{format}',
            response_format='xml'
        )

        call_args = mock_get.call_args
        assert '/api/rates/all/latest.xml' in call_args[0][0]

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_no_format_placeholder(self, mock_get, client):
        """Should work with endpoints without {format} placeholder"""
        mock_get.return_value = {'data': [{'test': 'value'}]}

        result = client.fetch_endpoint(
            endpoint_path='/api/custom/endpoint.json'
        )

        call_args = mock_get.call_args
        assert '/api/custom/endpoint.json' in call_args[0][0]
        assert len(result) == 1


# ============================================================================
# TEST Nested Extraction
# ============================================================================

@pytest.mark.unit
class TestNestedExtraction:
    """Tests for nested JSON data extraction"""

    def test_extract_single_level(self, client, mock_responses):
        """Should extract data from single-level path"""
        data = mock_responses['reference_rates_latest']
        result = client._extract_by_path(data, 'refRates')
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]['type'] == 'SOFR'

    def test_extract_nested_path(self, client, mock_responses):
        """Should extract data from multi-level path"""
        data = mock_responses['nested_deep']
        result = client._extract_by_path(data, 'data.results.items')
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['id'] == 1

    def test_extract_missing_key(self, client):
        """Should return empty list for missing key"""
        data = {'other': 'value'}
        result = client._extract_by_path(data, 'nonexistent')
        assert result == []

    def test_extract_dict_wraps_in_list(self, client):
        """Should wrap dict result in list"""
        data = {'item': {'id': 1}}
        result = client._extract_by_path(data, 'item')
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['id'] == 1

    def test_extract_invalid_path_type(self, client):
        """Should handle non-dict intermediate values"""
        data = {'level1': 'string_value'}
        result = client._extract_by_path(data, 'level1.level2')
        assert result == []

    def test_extract_primitive_value(self, client):
        """Should wrap primitive values in list"""
        data = {'count': 42}
        result = client._extract_by_path(data, 'count')
        assert isinstance(result, list)
        assert result == [42]


# ============================================================================
# TEST fetch_endpoint Method
# ============================================================================

@pytest.mark.unit
class TestFetchEndpoint:
    """Tests for fetch_endpoint main method"""

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_fetch_with_root_path(self, mock_get, client, mock_responses):
        """Should fetch and extract using root path"""
        mock_get.return_value = mock_responses['reference_rates_latest']

        result = client.fetch_endpoint(
            endpoint_path='/api/rates/all/latest.json',
            response_root_path='refRates'
        )

        assert len(result) == 3
        assert all('type' in item for item in result)

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_fetch_without_root_path_list(self, mock_get, client):
        """Should return list response directly if no root path"""
        mock_get.return_value = [{'id': 1}, {'id': 2}]

        result = client.fetch_endpoint(
            endpoint_path='/api/data.json'
        )

        assert len(result) == 2

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_fetch_without_root_path_dict(self, mock_get, client):
        """Should wrap dict response in list if no root path"""
        mock_get.return_value = {'id': 1, 'name': 'test'}

        result = client.fetch_endpoint(
            endpoint_path='/api/data.json'
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['id'] == 1

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_fetch_with_query_params(self, mock_get, client, mock_responses):
        """Should pass query parameters to GET request"""
        mock_get.return_value = mock_responses['reference_rates_search']

        result = client.fetch_endpoint(
            endpoint_path='/api/rates/all/search.json',
            query_params={'startDate': '2026-01-01', 'endDate': '2026-01-31'},
            response_root_path='refRates'
        )

        # Verify query params were passed
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert 'params' in call_kwargs
        assert call_kwargs['params']['startDate'] == '2026-01-01'
        assert len(result) == 2

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_fetch_empty_response(self, mock_get, client, mock_responses):
        """Should handle empty response gracefully"""
        mock_get.return_value = mock_responses['empty_response']

        result = client.fetch_endpoint(
            endpoint_path='/api/rates/all/latest.json',
            response_root_path='refRates'
        )

        assert result == []


# ============================================================================
# TEST Convenience Methods
# ============================================================================

@pytest.mark.unit
class TestConvenienceMethods:
    """Tests for convenience wrapper methods"""

    @patch.object(NewYorkFedAPIClient, 'fetch_endpoint')
    def test_get_reference_rates_latest(self, mock_fetch, client):
        """Should call fetch_endpoint with correct parameters for latest rates"""
        mock_fetch.return_value = [{'type': 'SOFR'}]

        result = client.get_reference_rates_latest()

        mock_fetch.assert_called_once_with(
            endpoint_path='/api/rates/all/latest.{format}',
            response_root_path='refRates'
        )
        assert len(result) == 1

    @patch.object(NewYorkFedAPIClient, 'fetch_endpoint')
    def test_get_reference_rates_search(self, mock_fetch, client):
        """Should call fetch_endpoint with date range for search"""
        mock_fetch.return_value = [{'type': 'SOFR'}, {'type': 'EFFR'}]

        result = client.get_reference_rates_search(
            start_date='2026-01-01',
            end_date='2026-01-31'
        )

        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args[1]
        assert call_kwargs['endpoint_path'] == '/api/rates/all/search.{format}'
        assert call_kwargs['query_params']['startDate'] == '2026-01-01'
        assert call_kwargs['query_params']['endDate'] == '2026-01-31'
        assert call_kwargs['response_root_path'] == 'refRates'
        assert len(result) == 2

    @patch.object(NewYorkFedAPIClient, 'fetch_endpoint')
    def test_get_soma_holdings(self, mock_fetch, client):
        """Should call fetch_endpoint for SOMA holdings"""
        mock_fetch.return_value = [{'securityType': 'Treasury'}]

        result = client.get_soma_holdings()

        mock_fetch.assert_called_once_with(
            endpoint_path='/api/soma/summary.{format}',
            response_root_path='soma'
        )
        assert len(result) == 1

    @patch.object(NewYorkFedAPIClient, 'fetch_endpoint')
    def test_get_repo_operations_repo(self, mock_fetch, client):
        """Should call fetch_endpoint for repo operations"""
        mock_fetch.return_value = [{'operationId': 'REPO-001'}]

        result = client.get_repo_operations(operation_type='repo')

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert '/api/repo/results/search.{format}' in call_args[1]['endpoint_path']
        assert call_args[1]['response_root_path'] == 'repo'

    @patch.object(NewYorkFedAPIClient, 'fetch_endpoint')
    def test_get_repo_operations_reverserepo(self, mock_fetch, client):
        """Should call fetch_endpoint for reverse repo operations"""
        mock_fetch.return_value = [{'operationId': 'RR-001'}]

        result = client.get_repo_operations(operation_type='reverserepo')

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert '/api/reverserepo/results/search.{format}' in call_args[1]['endpoint_path']
        assert call_args[1]['response_root_path'] == 'reverserepo'


# ============================================================================
# TEST Error Handling
# ============================================================================

@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling scenarios"""

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_handles_api_error(self, mock_get, client):
        """Should propagate API errors"""
        mock_get.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            client.fetch_endpoint('/api/test.json')

        assert "API Error" in str(exc_info.value)

    def test_extract_with_none_data(self, client):
        """Should handle None data gracefully"""
        # This should not crash
        result = client._extract_by_path({}, 'nonexistent')
        assert result == []

    @patch.object(NewYorkFedAPIClient, 'get')
    def test_malformed_json_response(self, mock_get, client):
        """Should handle malformed responses"""
        mock_get.return_value = "invalid json string"

        result = client.fetch_endpoint('/api/test.json')

        # Should wrap string in list
        assert isinstance(result, list)
        assert result == ["invalid json string"]

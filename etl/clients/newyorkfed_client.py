"""
Federal Reserve Bank of New York Markets API Client.

Provides access to 40+ endpoints across 10 categories:
- Reference Rates (SOFR, EFFR, OBFR, TGCR, BGCR)
- Agency MBS Operations
- FX Swaps
- Primary Dealer Statistics
- Repo Operations
- SOMA Holdings
- Treasury Operations
- Securities Lending
- Market Share
- Guide Sheets

API Documentation: https://markets.newyorkfed.org/static/docs/markets-api.html
"""

from typing import Dict, List, Optional, Any
from etl.base.api_client import BaseAPIClient


class NewYorkFedAPIClient(BaseAPIClient):
    """
    Client for Federal Reserve Bank of New York Markets API.

    Features:
    - Public API (no authentication required)
    - Supports JSON, XML, CSV, XLSX formats
    - Automatic format parameter replacement
    - Nested response data extraction
    - Conservative rate limiting (60 req/min)

    Usage:
        client = NewYorkFedAPIClient()

        # Fetch latest reference rates
        rates = client.fetch_endpoint(
            endpoint_path='/api/rates/all/latest.{format}',
            response_root_path='refRates'
        )

        # Fetch with query parameters
        data = client.fetch_endpoint(
            endpoint_path='/api/rates/all/search.{format}',
            query_params={'startDate': '2024-01-01', 'endDate': '2024-01-31'},
            response_root_path='refRates'
        )
    """

    def __init__(self, base_url: str = 'https://markets.newyorkfed.org'):
        """
        Initialize NewYorkFed API client.

        Args:
            base_url: Base URL for API (defaults to production URL)
        """
        # Conservative rate limit (API doesn't specify limits, so be cautious)
        super().__init__(base_url=base_url, rate_limit=60)

    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.

        NewYorkFed Markets API is public and doesn't require authentication.

        Returns:
            Dictionary with Accept header for JSON responses
        """
        return {
            'Accept': 'application/json',
            'User-Agent': 'Tangerine-ETL/1.0'
        }

    def fetch_endpoint(
        self,
        endpoint_path: str,
        response_format: str = 'json',
        query_params: Optional[Dict[str, Any]] = None,
        response_root_path: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch data from API endpoint with format replacement and nested extraction.

        Args:
            endpoint_path: API endpoint path (e.g., '/api/rates/all/latest.{format}')
            response_format: Response format (json, xml, csv, xlsx) - replaces {format}
            query_params: Query parameters (e.g., {'startDate': '2024-01-01'})
            response_root_path: JSON path to extract nested data (e.g., 'refRates' or 'data.results')

        Returns:
            List of dictionaries containing response data

        Examples:
            # Simple endpoint
            client.fetch_endpoint('/api/rates/all/latest.json')

            # With format replacement
            client.fetch_endpoint('/api/rates/all/latest.{format}', response_format='json')

            # With nested extraction
            client.fetch_endpoint(
                '/api/rates/all/latest.{format}',
                response_root_path='refRates'
            )

            # With query parameters
            client.fetch_endpoint(
                '/api/rates/all/search.{format}',
                query_params={'startDate': '2024-01-01', 'endDate': '2024-01-31'},
                response_root_path='refRates'
            )
        """
        # Replace {format} placeholder in endpoint path
        endpoint = endpoint_path.replace('{format}', response_format)

        self.logger.debug(f"Fetching endpoint: {endpoint}", extra={
            'metadata': {
                'query_params': query_params,
                'response_root_path': response_root_path
            }
        })

        # Fetch data using inherited GET method
        response = self.get(endpoint, params=query_params)

        # Extract nested data if root path specified
        if response_root_path and isinstance(response, dict):
            data = self._extract_by_path(response, response_root_path)
        else:
            # If response is already a list, use it directly
            # If response is a dict without root path, wrap in list
            data = response if isinstance(response, list) else [response]

        self.logger.info(f"Fetched {len(data)} records from {endpoint}")
        return data

    def _extract_by_path(self, data: dict, path: str) -> List[Dict]:
        """
        Extract nested data using dot notation path.

        Supports paths like:
        - 'refRates' -> data['refRates']
        - 'data.results' -> data['data']['results']
        - 'response.items.list' -> data['response']['items']['list']

        Args:
            data: Response dictionary
            path: Dot-separated path to nested data

        Returns:
            List of dictionaries (or single dict wrapped in list)

        Raises:
            KeyError: If path not found in response
        """
        parts = path.split('.')
        result = data

        for i, part in enumerate(parts):
            if not isinstance(result, dict):
                self.logger.warning(
                    f"Path traversal stopped at '{'.'.join(parts[:i])}': "
                    f"expected dict, got {type(result).__name__}"
                )
                return []

            if part not in result:
                self.logger.warning(
                    f"Path key '{part}' not found at '{'.'.join(parts[:i+1])}'. "
                    f"Available keys: {list(result.keys())}"
                )
                return []

            result = result[part]

        # Ensure result is a list
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return [result]
        else:
            self.logger.warning(
                f"Extracted data at path '{path}' is {type(result).__name__}, "
                f"expected list or dict. Wrapping in list."
            )
            return [result]

    # Convenience methods for common endpoints

    def get_reference_rates_latest(self) -> List[Dict]:
        """
        Fetch latest reference rates (SOFR, EFFR, OBFR, TGCR, BGCR).

        Returns:
            List of rate dictionaries
        """
        return self.fetch_endpoint(
            endpoint_path='/api/rates/all/latest.{format}',
            response_root_path='refRates'
        )

    def get_reference_rates_search(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Search reference rates by date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of rate dictionaries
        """
        return self.fetch_endpoint(
            endpoint_path='/api/rates/all/search.{format}',
            query_params={'startDate': start_date, 'endDate': end_date},
            response_root_path='refRates'
        )

    def get_soma_holdings(self) -> List[Dict]:
        """
        Fetch System Open Market Account (SOMA) holdings.

        Returns:
            List of holdings dictionaries
        """
        return self.fetch_endpoint(
            endpoint_path='/api/soma/summary.{format}',
            response_root_path='soma'
        )

    def get_repo_operations(self, operation_type: str = 'repo') -> List[Dict]:
        """
        Fetch repo or reverse repo operations.

        Args:
            operation_type: 'repo' or 'reverserepo'

        Returns:
            List of operation dictionaries
        """
        endpoint = f'/api/{operation_type}/results/search.{{format}}'
        return self.fetch_endpoint(
            endpoint_path=endpoint,
            response_root_path='repo' if operation_type == 'repo' else 'reverserepo'
        )

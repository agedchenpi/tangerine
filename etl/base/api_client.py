"""
Base API client with retry logic, rate limiting, and authentication support.

Provides foundation for all API integrations with:
- Automatic retries with exponential backoff
- Rate limiting
- Authentication handling (API keys, OAuth, etc.)
- Request/response logging
- Pagination support
"""

import time
import requests
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from common.logging_utils import get_logger
from common.config import get_config


class BaseAPIClient(ABC):
    """
    Base class for API clients.

    Features:
    - Retry logic with exponential backoff
    - Rate limiting (requests per minute)
    - Request/response logging
    - Session management
    - Pagination helpers

    Usage:
        class MyAPIClient(BaseAPIClient):
            def __init__(self, api_key):
                super().__init__(base_url="https://api.example.com")
                self.api_key = api_key

            def get_headers(self):
                return {"Authorization": f"Bearer {self.api_key}"}

            def get_data(self, endpoint):
                return self.get(endpoint)

        client = MyAPIClient(api_key="...")
        data = client.get_data("/v1/data")
    """

    def __init__(
        self,
        base_url: str,
        timeout: Optional[int] = None,
        rate_limit: Optional[int] = None,
        retry_attempts: Optional[int] = None
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL for API (e.g., "https://api.example.com")
            timeout: Request timeout in seconds (default from config)
            rate_limit: Max requests per minute (default from config)
            retry_attempts: Number of retry attempts (default from config)
        """
        self.base_url = base_url.rstrip('/')

        config = get_config()
        self.timeout = timeout or config.etl.api_timeout
        self.rate_limit = rate_limit or config.etl.api_rate_limit
        self.retry_attempts = retry_attempts or config.etl.retry_attempts

        self.session = requests.Session()
        self.logger = get_logger(self.__class__.__name__)

        # Rate limiting state
        self.request_times: List[float] = []
        self.rate_limit_window = 60  # seconds

    def _enforce_rate_limit(self):
        """Enforce rate limiting by sleeping if necessary."""
        now = time.time()

        # Remove requests older than rate limit window
        self.request_times = [
            t for t in self.request_times
            if now - t < self.rate_limit_window
        ]

        # If at rate limit, wait until oldest request expires
        if len(self.request_times) >= self.rate_limit:
            oldest = self.request_times[0]
            sleep_time = self.rate_limit_window - (now - oldest)
            if sleep_time > 0:
                self.logger.debug(f"Rate limit reached, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                now = time.time()

        self.request_times.append(now)

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.

        Returns:
            Dictionary of headers (including authentication)

        Example:
            return {"Authorization": f"Bearer {self.api_key}"}
        """
        pass

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        Make HTTP request with retry logic and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be joined with base_url)
            params: Query parameters
            data: Form data
            json: JSON body

        Returns:
            Response object

        Raises:
            requests.HTTPError: On HTTP errors
            requests.RequestException: On connection errors
        """
        self._enforce_rate_limit()

        url = urljoin(self.base_url, endpoint.lstrip('/'))
        headers = self.get_headers()

        self.logger.debug(f"{method} {url}", extra={
            'metadata': {'params': params, 'has_data': bool(data or json)}
        })

        @retry(
            stop=stop_after_attempt(self.retry_attempts),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type((
                requests.ConnectionError,
                requests.Timeout,
                requests.HTTPError
            )),
            reraise=True
        )
        def _request_with_retry():
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response

        try:
            response = _request_with_retry()
            self.logger.debug(f"Response {response.status_code}: {len(response.content)} bytes")
            return response
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error {e.response.status_code}: {e}", extra={
                'metadata': {'url': url, 'status_code': e.response.status_code}
            })
            raise
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}", extra={'metadata': {'url': url}})
            raise

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        response = self._make_request('GET', endpoint, params=params)
        return response.json()

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make POST request.

        Args:
            endpoint: API endpoint
            data: Form data
            json: JSON body

        Returns:
            JSON response as dictionary
        """
        response = self._make_request('POST', endpoint, data=data, json=json)
        return response.json()

    def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make PUT request.

        Args:
            endpoint: API endpoint
            json: JSON body

        Returns:
            JSON response as dictionary
        """
        response = self._make_request('PUT', endpoint, json=json)
        return response.json()

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        Make DELETE request.

        Args:
            endpoint: API endpoint

        Returns:
            JSON response as dictionary
        """
        response = self._make_request('DELETE', endpoint)
        return response.json()

    def get_paginated(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page_param: str = 'page',
        page_size_param: str = 'page_size',
        page_size: int = 100,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch paginated results.

        Args:
            endpoint: API endpoint
            params: Base query parameters
            page_param: Name of page parameter
            page_size_param: Name of page size parameter
            page_size: Number of items per page
            max_pages: Maximum number of pages to fetch (None = all)

        Returns:
            List of all results from all pages

        Note:
            Override this method if API uses different pagination scheme.
        """
        params = params or {}
        params[page_size_param] = page_size

        all_results = []
        page = 1

        while True:
            if max_pages and page > max_pages:
                break

            params[page_param] = page
            response = self.get(endpoint, params=params)

            # Adjust based on your API's response structure
            results = response.get('results', response.get('data', []))
            if not results:
                break

            all_results.extend(results)
            self.logger.info(f"Fetched page {page}: {len(results)} items (total: {len(all_results)})")

            # Check if there are more pages
            if not response.get('next') and len(results) < page_size:
                break

            page += 1

        self.logger.info(f"Pagination complete: {len(all_results)} total items")
        return all_results

    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

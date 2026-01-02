"""Example API extractor demonstrating BaseExtractor usage."""

from typing import List, Dict, Any
from etl.extractors.base_extractor import BaseExtractor
from etl.base.api_client import BaseAPIClient


class ExampleAPIClient(BaseAPIClient):
    """Example API client for demonstration."""

    def __init__(self, api_key: str):
        super().__init__(base_url="https://api.example.com")
        self.api_key = api_key

    def get_headers(self) -> Dict[str, str]:
        """Return headers with API key authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }


class ExampleAPIExtractor(BaseExtractor):
    """
    Example extractor that fetches data from an API.

    Usage:
        extractor = ExampleAPIExtractor(api_key="your-key")
        data = extractor.extract()
    """

    def __init__(self, api_key: str, endpoint: str = "/v1/data"):
        """
        Initialize extractor.

        Args:
            api_key: API authentication key
            endpoint: API endpoint to fetch data from
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.client = ExampleAPIClient(api_key)

    def extract(self) -> List[Dict[str, Any]]:
        """
        Extract data from API.

        Returns:
            List of records from API
        """
        try:
            # For paginated APIs
            data = self.client.get_paginated(
                endpoint=self.endpoint,
                page_size=100,
                max_pages=None  # Fetch all pages
            )

            # Validate extracted data
            self.validate(data)

            return data

        finally:
            self.client.close()

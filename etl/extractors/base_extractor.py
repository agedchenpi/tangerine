"""Base extractor class for data extraction."""

from abc import ABC, abstractmethod
from typing import Any, List, Dict


class BaseExtractor(ABC):
    """
    Base class for data extractors.

    Extractors are responsible for retrieving data from various sources:
    - APIs
    - Databases
    - Files (CSV, JSON, XML, etc.)
    - Cloud storage (S3, GCS, etc.)
    """

    @abstractmethod
    def extract(self) -> List[Dict[str, Any]]:
        """
        Extract data from source.

        Returns:
            List of dictionaries representing extracted records
        """
        pass

    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """
        Validate extracted data.

        Args:
            data: Extracted data

        Returns:
            True if valid, raises exception otherwise
        """
        if not isinstance(data, list):
            raise ValueError("Extracted data must be a list")

        if data and not isinstance(data[0], dict):
            raise ValueError("Extracted records must be dictionaries")

        return True

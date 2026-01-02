"""Base transformer class for data transformation."""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Callable
from datetime import datetime


class BaseTransformer(ABC):
    """
    Base class for data transformers.

    Transformers apply business logic to extracted data:
    - Data type conversions
    - Field mapping/renaming
    - Calculations and derived fields
    - Data cleaning and validation
    - Filtering and aggregation
    """

    @abstractmethod
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform extracted data.

        Args:
            data: Raw data from extractor

        Returns:
            Transformed data ready for loading
        """
        pass

    def apply_field_mapping(
        self,
        data: List[Dict[str, Any]],
        field_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Rename fields based on mapping.

        Args:
            data: Input data
            field_map: Dictionary mapping old_name -> new_name

        Returns:
            Data with renamed fields
        """
        return [
            {field_map.get(k, k): v for k, v in record.items()}
            for record in data
        ]

    def apply_type_conversion(
        self,
        data: List[Dict[str, Any]],
        type_map: Dict[str, Callable]
    ) -> List[Dict[str, Any]]:
        """
        Apply type conversions to fields.

        Args:
            data: Input data
            type_map: Dictionary mapping field_name -> conversion_function

        Returns:
            Data with converted types

        Example:
            type_map = {
                'price': float,
                'quantity': int,
                'created_at': lambda x: datetime.fromisoformat(x)
            }
        """
        result = []
        for record in data:
            converted = record.copy()
            for field, converter in type_map.items():
                if field in converted and converted[field] is not None:
                    try:
                        converted[field] = converter(converted[field])
                    except (ValueError, TypeError) as e:
                        # Log error but keep original value
                        print(f"Warning: Failed to convert {field}={converted[field]}: {e}")
            result.append(converted)
        return result

    def filter_records(
        self,
        data: List[Dict[str, Any]],
        predicate: Callable[[Dict[str, Any]], bool]
    ) -> List[Dict[str, Any]]:
        """
        Filter records based on predicate function.

        Args:
            data: Input data
            predicate: Function that returns True to keep record

        Returns:
            Filtered data

        Example:
            # Keep only active records
            filtered = transformer.filter_records(
                data,
                lambda r: r.get('status') == 'active'
            )
        """
        return [record for record in data if predicate(record)]

    def add_audit_fields(
        self,
        data: List[Dict[str, Any]],
        username: str = 'etl_user'
    ) -> List[Dict[str, Any]]:
        """
        Add audit fields to records.

        Args:
            data: Input data
            username: User to record in audit fields

        Returns:
            Data with audit fields added
        """
        now = datetime.utcnow()
        return [
            {
                **record,
                'created_date': now,
                'created_by': username,
                'modified_date': now,
                'modified_by': username
            }
            for record in data
        ]

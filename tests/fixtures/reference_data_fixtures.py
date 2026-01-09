"""Reusable test data fixtures for reference data

This module provides helper functions to generate test data for datasources
and dataset types.
"""

import uuid
from typing import Dict, Any, Optional


def get_valid_datasource(
    sourcename: Optional[str] = None,
    description: str = 'Test datasource',
    isactive: bool = True
) -> Dict[str, Any]:
    """
    Returns a valid datasource dictionary.

    Args:
        sourcename: Datasource name (auto-generated if None)
        description: Description
        isactive: Active status

    Returns:
        Dictionary with datasource fields
    """
    if sourcename is None:
        sourcename = f'AdminTest_Source_{uuid.uuid4().hex[:8]}'

    return {
        'sourcename': sourcename,
        'description': description,
        'isactive': isactive
    }


def get_valid_datasettype(
    typename: Optional[str] = None,
    description: str = 'Test dataset type',
    isactive: bool = True
) -> Dict[str, Any]:
    """
    Returns a valid dataset type dictionary.

    Args:
        typename: Dataset type name (auto-generated if None)
        description: Description
        isactive: Active status

    Returns:
        Dictionary with dataset type fields
    """
    if typename is None:
        typename = f'AdminTest_Type_{uuid.uuid4().hex[:8]}'

    return {
        'typename': typename,
        'description': description,
        'isactive': isactive
    }


def get_multiple_datasources(count: int = 5) -> list:
    """
    Returns list of valid datasources.

    Args:
        count: Number of datasources to generate

    Returns:
        List of datasource dictionaries
    """
    datasources = []
    for i in range(count):
        datasources.append(get_valid_datasource(
            description=f'Test datasource {i}',
            isactive=i % 2 == 0  # Alternate active/inactive
        ))
    return datasources


def get_multiple_datasettypes(count: int = 5) -> list:
    """
    Returns list of valid dataset types.

    Args:
        count: Number of dataset types to generate

    Returns:
        List of dataset type dictionaries
    """
    types = []
    for i in range(count):
        types.append(get_valid_datasettype(
            description=f'Test dataset type {i}',
            isactive=i % 2 == 0  # Alternate active/inactive
        ))
    return types


def get_invalid_datasource_configs() -> list:
    """
    Returns list of invalid datasource configs for testing validation.
    """
    return [
        {
            'field': 'sourcename',
            'value': '',  # Empty name
            'error_contains': 'required'
        },
        {
            'field': 'sourcename',
            'value': 'a' * 101,  # Too long
            'error_contains': 'length'
        },
        {
            'field': 'sourcename',
            'value': 'Invalid Name',  # Spaces
            'error_contains': 'invalid'
        }
    ]


def get_invalid_datasettype_configs() -> list:
    """
    Returns list of invalid dataset type configs for testing validation.
    """
    return [
        {
            'field': 'typename',
            'value': '',  # Empty name
            'error_contains': 'required'
        },
        {
            'field': 'typename',
            'value': 'a' * 101,  # Too long
            'error_contains': 'length'
        },
        {
            'field': 'typename',
            'value': 'Invalid Name',  # Spaces
            'error_contains': 'invalid'
        }
    ]

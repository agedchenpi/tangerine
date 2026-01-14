"""Reusable test data fixtures for import configurations

This module provides helper functions to generate test data for import configs
with various configurations and edge cases.
"""

import uuid
from typing import Dict, Any, Optional


def get_valid_import_config(
    config_name: Optional[str] = None,
    datasource: str = 'AdminTest',
    datasettype: str = 'AdminTest',
    file_type: str = 'CSV',
    metadata_source: str = 'filename',
    date_source: str = 'filename',
    is_active: bool = True
) -> Dict[str, Any]:
    """
    Returns a complete valid import config with all 19 fields.

    Args:
        config_name: Config name (auto-generated if None)
        datasource: Datasource name
        datasettype: Dataset type name
        file_type: File type (CSV, XLS, XLSX, JSON, XML)
        metadata_source: Metadata label source (filename, file_content, static)
        date_source: Date config source (filename, file_content, static)
        is_active: Active status

    Returns:
        Dictionary with all import config fields
    """
    if config_name is None:
        config_name = f'AdminTest_Config_{uuid.uuid4().hex[:8]}'

    config = {
        'config_name': config_name,
        'datasource': datasource,
        'datasettype': datasettype,
        'source_directory': '/app/data/source',
        'archive_directory': '/app/data/archive',
        'file_pattern': get_file_pattern_for_type(file_type),
        'file_type': file_type,
        'target_table': 'feeds.test_table',
        'importstrategyid': 1,  # Auto-add columns
        'is_active': is_active
    }

    # Add metadata fields based on source
    # Actual schema uses combined metadata_label_location field
    if metadata_source == 'filename':
        config.update({
            'metadata_label_source': 'filename',
            'metadata_label_location': '2',  # Position index as string
            'delimiter': '_'  # Shared delimiter for filename parsing
        })
    elif metadata_source == 'file_content':
        config.update({
            'metadata_label_source': 'file_content',
            'metadata_label_location': 'label',  # Column name
            'delimiter': None
        })
    elif metadata_source == 'static':
        config.update({
            'metadata_label_source': 'static',
            'metadata_label_location': 'StaticLabel',  # Static value
            'delimiter': None
        })

    # Add date fields based on source
    # Actual schema uses combined datelocation field
    if date_source == 'filename':
        config.update({
            'dateconfig': 'filename',
            'datelocation': '1',  # Position index as string
            'dateformat': 'yyyyMMdd'
        })
        # Ensure delimiter is set for filename parsing
        if 'delimiter' not in config or config['delimiter'] is None:
            config['delimiter'] = '_'
    elif date_source == 'file_content':
        config.update({
            'dateconfig': 'file_content',
            'datelocation': 'date',  # Column name
            'dateformat': 'yyyy-MM-dd'
        })
    elif date_source == 'static':
        config.update({
            'dateconfig': 'static',
            'datelocation': None,  # Not needed for static
            'dateformat': 'yyyy-MM-dd'
        })

    return config


def get_file_pattern_for_type(file_type: str) -> str:
    """
    Returns a regex file pattern for the given file type.

    Args:
        file_type: File type (CSV, XLS, XLSX, JSON, XML)

    Returns:
        Regex pattern string
    """
    patterns = {
        'CSV': r'test_\d{8}_.*\.csv',
        'XLS': r'test_\d{8}_.*\.xls',
        'XLSX': r'test_\d{8}_.*\.xlsx',
        'JSON': r'test_\d{8}_.*\.json',
        'XML': r'test_\d{8}_.*\.xml'
    }
    return patterns.get(file_type, r'test_.*\.\w+')


def get_invalid_directory_path_configs() -> list:
    """
    Returns list of configs with invalid directory paths for testing validation.

    Each config has a 'field' and 'value' key indicating which field is invalid.
    """
    return [
        {
            'field': 'source_directory',
            'value': 'relative/path',  # Missing leading slash
            'error_contains': 'absolute'
        },
        {
            'field': 'source_directory',
            'value': '/app/data/source/',  # Trailing slash
            'error_contains': 'trailing'
        },
        {
            'field': 'source_directory',
            'value': '/app/data/<invalid>',  # Invalid characters
            'error_contains': 'invalid'
        },
        {
            'field': 'archive_directory',
            'value': '',  # Empty
            'error_contains': 'required'
        }
    ]


def get_invalid_file_pattern_configs() -> list:
    """
    Returns list of configs with invalid file patterns for testing validation.
    """
    return [
        {
            'field': 'file_pattern',
            'value': '[unclosed',  # Invalid regex
            'error_contains': 'invalid'
        },
        {
            'field': 'file_pattern',
            'value': '',  # Empty
            'error_contains': 'required'
        }
    ]


def get_invalid_table_name_configs() -> list:
    """
    Returns list of configs with invalid table names for testing validation.
    """
    return [
        {
            'field': 'target_table',
            'value': 'no_schema_table',  # Missing schema
            'error_contains': 'schema'
        },
        {
            'field': 'target_table',
            'value': 'feeds.123invalid',  # Invalid table name
            'error_contains': 'invalid'
        },
        {
            'field': 'target_table',
            'value': 'feeds.table.extra',  # Too many parts
            'error_contains': 'format'
        }
    ]


def get_configs_for_all_file_types() -> list:
    """
    Returns list of valid configs for all supported file types.
    """
    file_types = ['CSV', 'XLS', 'XLSX', 'JSON', 'XML']
    return [
        get_valid_import_config(file_type=ft)
        for ft in file_types
    ]


def get_configs_for_all_metadata_sources() -> list:
    """
    Returns list of valid configs for all metadata sources.
    """
    sources = ['filename', 'file_content', 'static']
    return [
        get_valid_import_config(metadata_source=src)
        for src in sources
    ]


def get_configs_for_all_date_sources() -> list:
    """
    Returns list of valid configs for all date sources.
    """
    sources = ['filename', 'file_content', 'static']
    return [
        get_valid_import_config(date_source=src)
        for src in sources
    ]


def get_configs_for_all_strategies() -> list:
    """
    Returns list of valid configs for all import strategies.
    """
    strategies = [1, 2, 3]  # Auto-add, Ignore extras, Strict
    return [
        {**get_valid_import_config(), 'importstrategyid': strategy}
        for strategy in strategies
    ]

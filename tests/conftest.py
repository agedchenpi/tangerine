"""Pytest configuration and shared fixtures for admin interface tests

This module provides core fixtures used across all tests:
- Database connection and transaction management
- Test data cleanup
- Sample test data for datasources, dataset types, and import configs
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from contextlib import contextmanager

import pytest
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import get_config


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def db_url():
    """Get database connection URL from environment"""
    return get_config().database.db_url


@pytest.fixture(scope="session")
def db_connection(db_url):
    """Session-wide database connection"""
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def db_transaction(db_connection):
    """Function-scoped database transaction with automatic rollback

    This fixture ensures test isolation by rolling back all changes
    after each test. No manual cleanup is needed.

    Usage:
        def test_something(db_transaction):
            with db_transaction() as cursor:
                cursor.execute("INSERT INTO ...")
                # Changes will be rolled back after test
    """
    @contextmanager
    def transaction():
        """Context manager for database operations"""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            db_connection.commit()
        except Exception:
            db_connection.rollback()
            raise
        finally:
            cursor.close()

    yield transaction

    # Rollback any uncommitted changes after test
    db_connection.rollback()


@pytest.fixture(scope="function")
def clean_test_data(db_transaction):
    """Clean up test data before and after each test

    Removes any records with names starting with 'AdminTest_' to ensure
    clean state even if transaction rollback fails.
    """
    def cleanup():
        with db_transaction() as cursor:
            # Clean import configs
            cursor.execute("""
                DELETE FROM dba.timportconfig
                WHERE config_name LIKE 'AdminTest_%%'
            """)

            # Clean datasources
            cursor.execute("""
                DELETE FROM dba.tdatasource
                WHERE sourcename LIKE 'AdminTest_%%'
            """)

            # Clean dataset types
            cursor.execute("""
                DELETE FROM dba.tdatasettype
                WHERE typename LIKE 'AdminTest_%%'
            """)

            # Clean datasets
            cursor.execute("""
                DELETE FROM dba.tdataset
                WHERE label LIKE 'AdminTest_%%'
            """)

    # Cleanup before test
    cleanup()

    yield

    # Cleanup after test (in case rollback fails)
    cleanup()


# ============================================================================
# REFERENCE DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_datasource():
    """Sample datasource data for testing"""
    return {
        'sourcename': f'AdminTest_Source_{uuid.uuid4().hex[:8]}',
        'description': 'Test datasource for admin regression tests'
    }


@pytest.fixture
def sample_datasettype():
    """Sample dataset type data for testing"""
    return {
        'typename': f'AdminTest_Type_{uuid.uuid4().hex[:8]}',
        'description': 'Test dataset type for admin regression tests'
    }


@pytest.fixture
def created_datasource(db_transaction, sample_datasource):
    """Create a datasource in database, auto-cleanup via rollback"""
    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.tdatasource (sourcename, description)
            VALUES (%(sourcename)s, %(description)s)
            RETURNING datasourceid, sourcename, description
        """, sample_datasource)
        result = cursor.fetchone()

    return dict(result)


@pytest.fixture
def created_datasettype(db_transaction, sample_datasettype):
    """Create a dataset type in database, auto-cleanup via rollback"""
    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.tdatasettype (typename, description)
            VALUES (%(typename)s, %(description)s)
            RETURNING datasettypeid, typename, description
        """, sample_datasettype)
        result = cursor.fetchone()

    return dict(result)


# ============================================================================
# IMPORT CONFIG FIXTURES
# ============================================================================

@pytest.fixture
def sample_import_config(created_datasource, created_datasettype):
    """Valid import config matching stored procedure parameters

    Requires created datasource and dataset type to ensure referential integrity.
    """
    return {
        'config_name': f'AdminTest_Config_{uuid.uuid4().hex[:8]}',
        'datasource': created_datasource['sourcename'],
        'datasettype': created_datasettype['typename'],
        'source_directory': '/app/data/source',
        'archive_directory': '/app/data/archive',
        'file_pattern': r'test_file_\d{8}\.csv',
        'file_type': 'CSV',
        'target_table': 'feeds.test_table',
        'importstrategyid': 1,  # Auto-add columns
        'metadata_label_source': 'filename',
        'metadata_label_location': '2',  # Position index as string
        'dateconfig': 'filename',
        'datelocation': '1',  # Position index as string
        'dateformat': 'yyyyMMdd',  # Note: no underscore
        'delimiter': '_',  # Shared delimiter
        'is_active': True
    }


@pytest.fixture
def created_import_config(db_transaction, sample_import_config):
    """Create an import config in database, auto-cleanup via rollback"""
    with db_transaction() as cursor:
        # Get datasource and datasettype IDs
        cursor.execute(
            "SELECT datasourceid FROM dba.tdatasource WHERE sourcename = %s",
            (sample_import_config['datasource'],)
        )
        datasourceid = cursor.fetchone()['datasourceid']

        cursor.execute(
            "SELECT datasettypeid FROM dba.tdatasettype WHERE typename = %s",
            (sample_import_config['datasettype'],)
        )
        datasettypeid = cursor.fetchone()['datasettypeid']

        # Insert config
        cursor.execute("""
            INSERT INTO dba.timportconfig (
                config_name, datasourceid, datasettypeid,
                source_directory, archive_directory, file_pattern, file_type,
                target_table, importstrategyid,
                metadata_label_source, metadata_delimiter, metadata_position_index,
                metadata_column_name, metadata_static_value,
                dateconfig, date_delimiter, date_position_index,
                date_column_name, date_format, is_active
            ) VALUES (
                %(config_name)s, %(datasourceid)s, %(datasettypeid)s,
                %(source_directory)s, %(archive_directory)s, %(file_pattern)s, %(file_type)s,
                %(target_table)s, %(importstrategyid)s,
                %(metadata_label_source)s, %(metadata_delimiter)s, %(metadata_position_index)s,
                %(metadata_column_name)s, %(metadata_static_value)s,
                %(dateconfig)s, %(date_delimiter)s, %(date_position_index)s,
                %(date_column_name)s, %(date_format)s, %(is_active)s
            )
            RETURNING config_id
        """, {
            **sample_import_config,
            'datasourceid': datasourceid,
            'datasettypeid': datasettypeid
        })
        config_id = cursor.fetchone()['config_id']

        # Fetch complete config
        cursor.execute("""
            SELECT
                c.*,
                s.sourcename as datasource,
                t.typename as datasettype
            FROM dba.timportconfig c
            JOIN dba.tdatasource s ON c.datasourceid = s.datasourceid
            JOIN dba.tdatasettype t ON c.datasettypeid = t.datasettypeid
            WHERE c.config_id = %s
        """, (config_id,))
        result = cursor.fetchone()

    return dict(result)


# ============================================================================
# MULTIPLE RECORD FIXTURES
# ============================================================================

@pytest.fixture
def created_datasources(db_transaction):
    """Create multiple datasources for testing list/filter operations"""
    datasources = []
    with db_transaction() as cursor:
        for i in range(5):
            sourcename = f'AdminTest_Source_{uuid.uuid4().hex[:8]}'
            cursor.execute("""
                INSERT INTO dba.tdatasource (sourcename, description)
                VALUES (%s, %s)
                RETURNING datasourceid, sourcename, description
            """, (sourcename, f'Test datasource {i}'))
            datasources.append(dict(cursor.fetchone()))

    return datasources


@pytest.fixture
def created_import_configs(db_transaction, created_datasource, created_datasettype):
    """Create multiple import configs for testing list/filter operations"""
    configs = []
    file_types = ['CSV', 'XLS', 'XLSX', 'JSON', 'XML']

    with db_transaction() as cursor:
        for i, file_type in enumerate(file_types):
            config_name = f'AdminTest_Config_{uuid.uuid4().hex[:8]}'
            cursor.execute("""
                INSERT INTO dba.timportconfig (
                    config_name, datasourceid, datasettypeid,
                    source_directory, archive_directory, file_pattern, file_type,
                    target_table, importstrategyid,
                    metadata_label_source, dateconfig, date_format, is_active
                ) VALUES (
                    %s, %s, %s,
                    '/app/data/source', '/app/data/archive',
                    %s, %s, 'feeds.test_table', 1,
                    'filename', 'filename', 'yyyyMMdd', %s
                )
                RETURNING config_id
            """, (
                config_name,
                created_datasource['datasourceid'],
                created_datasettype['datasettypeid'],
                f'.*\\.{file_type.lower()}',
                file_type,
                i % 2 == 0  # Alternate active/inactive
            ))
            config_id = cursor.fetchone()['config_id']

            # Fetch complete config
            cursor.execute("""
                SELECT c.*, s.sourcename as datasource, t.typename as datasettype
                FROM dba.timportconfig c
                JOIN dba.tdatasource s ON c.datasourceid = s.datasourceid
                JOIN dba.tdatasettype t ON c.datasettypeid = t.datasettypeid
                WHERE c.config_id = %s
            """, (config_id,))
            configs.append(dict(cursor.fetchone()))

    return configs


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests (no database required)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (database required)"
    )
    config.addinivalue_line(
        "markers", "crud: CRUD operation tests"
    )
    config.addinivalue_line(
        "markers", "validation: Validation logic tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take significant time"
    )

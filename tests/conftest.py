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

    Removes any records with names starting with 'AdminTest_' or 'UITest_' to ensure
    clean state even if transaction rollback fails.
    """
    def cleanup():
        with db_transaction() as cursor:
            # Clean pub-sub subscribers (Phase 2)
            cursor.execute("""
                DELETE FROM dba.tpubsub_subscribers
                WHERE subscriber_name LIKE 'AdminTest_%%'
            """)

            # Clean pub-sub events (Phase 2) - clean by source pattern
            cursor.execute("""
                DELETE FROM dba.tpubsub_events
                WHERE event_source LIKE '%%AdminTest%%' OR event_source LIKE '/test/%%'
            """)

            # Clean inbox configs (Phase 1)
            cursor.execute("""
                DELETE FROM dba.tinboxconfig
                WHERE config_name LIKE 'AdminTest_%%'
            """)

            # Clean import configs
            cursor.execute("""
                DELETE FROM dba.timportconfig
                WHERE config_name LIKE 'AdminTest_%%' OR config_name LIKE 'UITest_%%'
            """)

            # Clean schedules (for UITest_* scheduler tests)
            cursor.execute("""
                DELETE FROM dba.tscheduler
                WHERE job_name LIKE 'UITest_%%'
            """)

            # Clean datasets FIRST (before datasources due to FK constraint)
            cursor.execute("""
                DELETE FROM dba.tdataset
                WHERE label LIKE 'AdminTest_%%'
            """)

            # Clean datasources (after datasets)
            cursor.execute("""
                DELETE FROM dba.tdatasource
                WHERE sourcename LIKE 'AdminTest_%%' OR sourcename LIKE 'UITest_%%'
            """)

            # Clean dataset types (after datasets)
            cursor.execute("""
                DELETE FROM dba.tdatasettype
                WHERE typename LIKE 'AdminTest_%%' OR typename LIKE 'UITest_%%'
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
    """Create an import config in database, auto-cleanup via rollback

    Uses actual schema which stores datasource/datasettype as VARCHAR text names,
    not foreign key IDs. Combined location fields for metadata and date.
    """
    with db_transaction() as cursor:
        # Insert config using actual schema columns
        cursor.execute("""
            INSERT INTO dba.timportconfig (
                config_name, datasource, datasettype,
                source_directory, archive_directory, file_pattern, file_type,
                target_table, importstrategyid,
                metadata_label_source, metadata_label_location,
                dateconfig, datelocation, dateformat, delimiter,
                is_active
            ) VALUES (
                %(config_name)s, %(datasource)s, %(datasettype)s,
                %(source_directory)s, %(archive_directory)s, %(file_pattern)s, %(file_type)s,
                %(target_table)s, %(importstrategyid)s,
                %(metadata_label_source)s, %(metadata_label_location)s,
                %(dateconfig)s, %(datelocation)s, %(dateformat)s, %(delimiter)s,
                %(is_active)s
            )
            RETURNING config_id
        """, sample_import_config)
        config_id = cursor.fetchone()['config_id']

        # Fetch complete config
        cursor.execute("""
            SELECT c.*
            FROM dba.timportconfig c
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
    """Create multiple import configs for testing list/filter operations

    Uses actual schema with VARCHAR datasource/datasettype columns.
    """
    configs = []
    file_types = ['CSV', 'XLS', 'XLSX', 'JSON', 'XML']

    with db_transaction() as cursor:
        for i, file_type in enumerate(file_types):
            config_name = f'AdminTest_Config_{uuid.uuid4().hex[:8]}'
            cursor.execute("""
                INSERT INTO dba.timportconfig (
                    config_name, datasource, datasettype,
                    source_directory, archive_directory, file_pattern, file_type,
                    target_table, importstrategyid,
                    metadata_label_source, metadata_label_location,
                    dateconfig, datelocation, dateformat, delimiter,
                    is_active
                ) VALUES (
                    %s, %s, %s,
                    '/app/data/source', '/app/data/archive',
                    %s, %s, 'feeds.test_table', 1,
                    'filename', '2',
                    'filename', '1', 'yyyyMMdd', '_',
                    %s
                )
                RETURNING config_id
            """, (
                config_name,
                created_datasource['sourcename'],
                created_datasettype['typename'],
                f'.*\\.{file_type.lower()}',
                file_type,
                i % 2 == 0  # Alternate active/inactive
            ))
            config_id = cursor.fetchone()['config_id']

            # Fetch complete config
            cursor.execute("""
                SELECT c.*
                FROM dba.timportconfig c
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

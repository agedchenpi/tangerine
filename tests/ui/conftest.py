"""
UI test fixtures for Streamlit AppTest.

Provides fixtures for loading Streamlit pages and common test setup.
"""
import pytest
import os
import sys
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


# Ensure admin directory is in Python path for relative imports
if '/app/admin' not in sys.path:
    sys.path.insert(0, '/app/admin')


@pytest.fixture
def imports_page():
    """
    Load the imports page for testing.

    Returns:
        AppTest instance for imports page
    """
    # Change to admin directory for relative imports
    original_cwd = os.getcwd()
    try:
        os.chdir('/app/admin')
        at = AppTest.from_file("pages/imports.py")
        at.run()
        return at
    finally:
        os.chdir(original_cwd)


@pytest.fixture
def scheduler_page():
    """
    Load the scheduler page for testing.

    Returns:
        AppTest instance for scheduler page
    """
    original_cwd = os.getcwd()
    try:
        os.chdir('/app/admin')
        at = AppTest.from_file("pages/scheduler.py")
        at.run()
        return at
    finally:
        os.chdir(original_cwd)


@pytest.fixture
def reference_data_page():
    """
    Load the reference data page for testing.

    Returns:
        AppTest instance for reference data page
    """
    original_cwd = os.getcwd()
    try:
        os.chdir('/app/admin')
        at = AppTest.from_file("pages/reference_data.py")
        at.run()
        return at
    finally:
        os.chdir(original_cwd)


class HybridRow(tuple):
    """
    A row that supports BOTH integer indexing AND dict access.

    This allows compatibility with code that uses:
    - result[0] (tuple-style integer indexing)
    - result['column_name'] (dict-style key access)
    - dict(result) (converting to dict)
    """
    def __new__(cls, values, column_names):
        instance = super().__new__(cls, values)
        instance._column_names = column_names
        instance._dict = dict(zip(column_names, values))
        return instance

    def __getitem__(self, key):
        """Support both integer and string indexing."""
        if isinstance(key, int):
            return tuple.__getitem__(self, key)
        else:
            return self._dict[key]

    def get(self, key, default=None):
        """Dict-style get method."""
        return self._dict.get(key, default)

    def keys(self):
        """Return column names."""
        return self._dict.keys()

    def values(self):
        """Return column values."""
        return self._dict.values()

    def items(self):
        """Return column name-value pairs."""
        return self._dict.items()

    def __iter__(self):
        """Iterate over column name-value pairs for dict() compatibility."""
        return iter(self._dict.items())


class HybridCursor:
    """
    Cursor wrapper that returns HybridRow objects.

    These rows support both integer indexing (for services using result[0])
    and dict access (for services using result['column']).
    """
    def __init__(self, real_cursor):
        self._cursor = real_cursor

    def __getattr__(self, name):
        """Forward all attribute access to real cursor."""
        return getattr(self._cursor, name)

    def fetchone(self):
        """Fetch one row as HybridRow."""
        row = self._cursor.fetchone()
        if row is None:
            return None
        column_names = [desc[0] for desc in self._cursor.description]
        return HybridRow(row, column_names)

    def fetchall(self):
        """Fetch all rows as HybridRows."""
        rows = self._cursor.fetchall()
        if not rows:
            return []
        column_names = [desc[0] for desc in self._cursor.description]
        return [HybridRow(row, column_names) for row in rows]

    def fetchmany(self, size=None):
        """Fetch many rows as HybridRows."""
        rows = self._cursor.fetchmany(size) if size else self._cursor.fetchmany()
        if not rows:
            return []
        column_names = [desc[0] for desc in self._cursor.description]
        return [HybridRow(row, column_names) for row in rows]


class TestConnectionWrapper:
    """
    Wrapper for database connection that intercepts commit/rollback.

    This allows UI tests to use the same transaction-managed connection
    as pytest fixtures, while services can still call commit() without
    actually committing (pytest manages the transaction).
    """
    def __init__(self, wrapped_connection):
        self._connection = wrapped_connection

    def __getattr__(self, name):
        """Forward all attribute access to wrapped connection."""
        return getattr(self._connection, name)

    def cursor(self, cursor_factory=None):
        """
        Create a HybridCursor that supports both integer and dict access.

        Ignores cursor_factory parameter since HybridCursor provides
        compatibility with both tuple-based (result[0]) and dict-based
        (result['column']) access patterns.
        """
        real_cursor = self._connection.cursor()
        return HybridCursor(real_cursor)

    def commit(self):
        """No-op commit - pytest manages the transaction."""
        pass

    def rollback(self):
        """No-op rollback - pytest manages the transaction."""
        pass


@pytest.fixture
def patched_db_connection(db_connection):
    """
    Patch common.db_utils.get_connection() to use pytest's test connection.

    This ensures that all database operations in AppTest pages use the same
    connection as pytest fixtures, allowing transaction rollback to work.

    Key patches:
    - get_connection() returns wrapped test connection
    - Wrapped connection intercepts commit/rollback (no-op)
    - return_connection() becomes no-op (don't return to pool)
    """
    # Import here to avoid circular imports
    import common.db_utils

    # Wrap the test connection to intercept commit/rollback
    wrapped_conn = TestConnectionWrapper(db_connection)

    # Create a mock that returns our wrapped test connection
    def get_test_connection():
        return wrapped_conn

    # No-op for returning test connection (don't put it back in pool)
    def return_test_connection(conn):
        pass

    # Patch db_utils functions
    with patch.object(common.db_utils, 'get_connection', side_effect=get_test_connection), \
         patch.object(common.db_utils, 'return_connection', side_effect=return_test_connection):
        yield wrapped_conn


@pytest.fixture
def ui_test_context(patched_db_connection, clean_test_data):
    """
    Combined fixture for UI tests that provides:
    - Patched database connection (uses pytest connection)
    - Clean test data (cleans up UITest_* prefixed records)

    Use this fixture in all end-to-end UI tests.
    """
    yield patched_db_connection

"""
Database connection utilities with connection pooling and context managers.

Provides:
- Connection pooling for performance
- Context managers for automatic resource management
- Retry logic for transient failures
- Bulk insert utilities
- Query execution helpers
"""

import psycopg2
from psycopg2 import pool, extras, OperationalError, InterfaceError
from psycopg2.extensions import connection as PGConnection, cursor as PGCursor
import os
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from common.config import get_config


# Global connection pool
_connection_pool: Optional[pool.SimpleConnectionPool] = None


def get_pool() -> pool.SimpleConnectionPool:
    """
    Get or create the global connection pool.

    Returns:
        Connection pool instance
    """
    global _connection_pool

    if _connection_pool is None:
        config = get_config()

        _connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=config.database.pool_size,
            dsn=config.database.db_url
        )

    return _connection_pool


def close_pool():
    """Close all connections in the pool."""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((OperationalError, InterfaceError))
)
def get_connection() -> Optional[PGConnection]:
    """
    Get a connection from the pool with retry logic.

    Returns:
        Database connection or None on failure

    Retries:
        3 attempts with exponential backoff for transient errors
    """
    try:
        conn_pool = get_pool()
        conn = conn_pool.getconn()
        return conn
    except Exception as e:
        print(f"Error getting connection: {e}")
        return None


def return_connection(conn: PGConnection):
    """
    Return a connection to the pool.

    Args:
        conn: Connection to return
    """
    if conn is not None:
        try:
            conn_pool = get_pool()
            conn_pool.putconn(conn)
        except Exception as e:
            print(f"Error returning connection: {e}")


@contextmanager
def db_connection():
    """
    Context manager for database connections.

    Usage:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")

    Automatically returns connection to pool on exit.
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        if conn is not None:
            return_connection(conn)


@contextmanager
def db_transaction(dict_cursor: bool = True):
    """
    Context manager for database transactions.

    Usage:
        with db_transaction() as cursor:
            cursor.execute("INSERT INTO table VALUES (%s)", (value,))
            # Automatically commits on success, rolls back on exception

    Args:
        dict_cursor: If True, use RealDictCursor to return rows as dicts.
                     If False, use regular cursor that returns tuples.

    Features:
    - Automatic commit on success
    - Automatic rollback on exception
    - Returns connection to pool
    - Returns dictionaries by default for easier access
    """
    conn = get_connection()
    cursor = None

    try:
        if dict_cursor:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        else:
            cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            return_connection(conn)


def execute_query(
    query: str,
    params: Optional[Tuple] = None,
    fetch: bool = True
) -> Optional[List[Tuple]]:
    """
    Execute a query and optionally fetch results.

    Args:
        query: SQL query to execute
        params: Query parameters
        fetch: Whether to fetch and return results

    Returns:
        List of result tuples if fetch=True, None otherwise
    """
    with db_transaction() as cursor:
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
    return None


def execute_many(query: str, params_list: List[Tuple]) -> int:
    """
    Execute a query multiple times with different parameters.

    Args:
        query: SQL query to execute
        params_list: List of parameter tuples

    Returns:
        Number of rows affected
    """
    with db_transaction() as cursor:
        cursor.executemany(query, params_list)
        return cursor.rowcount


def bulk_insert(
    table: str,
    columns: List[str],
    values: List[Tuple],
    schema: str = "feeds"
) -> int:
    """
    Perform bulk insert using COPY for performance.

    Args:
        table: Table name
        columns: List of column names
        values: List of value tuples
        schema: Schema name (default: feeds)

    Returns:
        Number of rows inserted
    """
    if not values:
        return 0

    with db_connection() as conn:
        cursor = conn.cursor()

        # Use execute_values for efficient bulk insert
        insert_query = f"""
            INSERT INTO {schema}.{table} ({', '.join(columns)})
            VALUES %s
        """

        extras.execute_values(cursor, insert_query, values, page_size=1000)
        rows_inserted = cursor.rowcount

        conn.commit()
        cursor.close()

    return rows_inserted


def fetch_dict(query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a query and return results as list of dictionaries.

    Args:
        query: SQL query to execute
        params: Query parameters

    Returns:
        List of dictionaries with column names as keys
    """
    with db_connection() as conn:
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()

    return [dict(row) for row in results]


def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            return result[0] == 1
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False


if __name__ == "__main__":
    """Test database connection and utilities."""
    db_url = os.getenv("DB_URL")
    if db_url:
        print("Testing database connection...")
        if test_connection():
            print("✓ Database connection successful")

            # Test query execution
            try:
                results = fetch_dict("SELECT COUNT(*) as count FROM dba.tlogentry")
                print(f"✓ Query test successful: {results[0]['count']} log entries in database")
            except Exception as e:
                print(f"✗ Query test failed: {e}")

            close_pool()
            print("✓ Connection pool closed")
        else:
            print("✗ Database connection failed")
    else:
        print("✗ DB_URL not set in environment")

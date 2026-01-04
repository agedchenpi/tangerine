"""Database query helper utilities for admin interface"""

from typing import List, Dict, Any, Optional
from common.db_utils import fetch_dict, execute_query


def get_count(table: str, where_clause: str = "", params: tuple = None) -> int:
    """
    Get count of records from a table.

    Args:
        table: Table name (e.g., "dba.timportconfig")
        where_clause: Optional WHERE clause (without WHERE keyword)
        params: Optional query parameters

    Returns:
        Record count

    Example:
        count = get_count("dba.timportconfig", "is_active = %s", (True,))
    """
    query = f"SELECT COUNT(*) as count FROM {table}"
    if where_clause:
        query += f" WHERE {where_clause}"

    result = fetch_dict(query, params)
    return result[0]['count'] if result else 0


def table_exists(schema: str, table: str) -> bool:
    """
    Check if a table exists in the database.

    Args:
        schema: Schema name
        table: Table name

    Returns:
        True if table exists, False otherwise
    """
    query = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        ) as exists
    """
    result = fetch_dict(query, (schema, table))
    return result[0]['exists'] if result else False


def get_distinct_values(table: str, column: str, where_clause: str = "") -> List[str]:
    """
    Get distinct values from a column.

    Args:
        table: Table name
        column: Column name
        where_clause: Optional WHERE clause

    Returns:
        List of distinct values
    """
    query = f"SELECT DISTINCT {column} FROM {table}"
    if where_clause:
        query += f" WHERE {where_clause}"
    query += f" ORDER BY {column}"

    result = fetch_dict(query)
    return [row[column] for row in result] if result else []


def get_table_columns(schema: str, table: str) -> List[Dict[str, Any]]:
    """
    Get column information for a table.

    Args:
        schema: Schema name
        table: Table name

    Returns:
        List of column dictionaries with name, type, nullable info
    """
    query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """
    return fetch_dict(query, (schema, table))


def format_sql_error(error: Exception) -> str:
    """
    Format SQL error message for user display.

    Args:
        error: Exception from database operation

    Returns:
        User-friendly error message
    """
    error_str = str(error)

    # Common error patterns
    if "unique constraint" in error_str.lower():
        return "A record with this name already exists"
    elif "foreign key" in error_str.lower():
        return "Cannot perform operation: referenced by other records"
    elif "not null violation" in error_str.lower():
        return "Required field is missing"
    elif "check constraint" in error_str.lower():
        return "Value does not meet validation requirements"
    elif "does not exist" in error_str.lower():
        return "Referenced record does not exist"
    else:
        return f"Database error: {error_str[:200]}"  # Truncate long errors

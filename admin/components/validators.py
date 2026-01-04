"""Input validation utilities for form fields"""

import re
from typing import Optional, Tuple


def validate_directory_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate directory path format.

    Rules:
    - Must start with /
    - Must not end with /
    - Must be absolute path

    Args:
        path: Directory path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "Directory path is required"

    if not path.startswith('/'):
        return False, "Path must be absolute (start with /)"

    if path.endswith('/'):
        return False, "Path must not end with /"

    # Check for invalid characters (basic validation)
    if re.search(r'[<>"|?*]', path):
        return False, "Path contains invalid characters"

    return True, None


def validate_file_pattern(pattern: str) -> Tuple[bool, Optional[str]]:
    """
    Validate regex file pattern.

    Args:
        pattern: Regex pattern to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pattern:
        return False, "File pattern is required"

    try:
        re.compile(pattern)
        return True, None
    except re.error as e:
        return False, f"Invalid regex pattern: {str(e)}"


def validate_table_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate table name in schema.table format.

    Args:
        name: Table name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Table name is required"

    if '.' not in name:
        return False, "Table name must be in format: schema.table"

    parts = name.split('.')
    if len(parts) != 2:
        return False, "Table name must have exactly one schema and one table"

    schema, table = parts

    # Validate schema and table names (alphanumeric + underscore)
    if not re.match(r'^[a-z_][a-z0-9_]*$', schema):
        return False, f"Invalid schema name: {schema}"

    if not re.match(r'^[a-z_][a-z0-9_]*$', table):
        return False, f"Invalid table name: {table}"

    return True, None


def validate_date_format(format_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validate date format string.

    Common formats:
    - yyyyMMddTHHmmss
    - yyyy-MM-dd
    - MM/dd/yyyy
    - dd-MM-yyyy

    Args:
        format_str: Date format string to validate

    Returns:
        Tuple of (is_valid, warning_message)
        Note: Returns warning, not error (format strings are flexible)
    """
    if not format_str:
        return False, "Date format is required"

    common_formats = [
        'yyyyMMddTHHmmss',
        'yyyy-MM-dd',
        'MM/dd/yyyy',
        'dd-MM-yyyy',
        'yyyy/MM/dd',
        'yyyyMMdd',
        'ddMMyyyy'
    ]

    if format_str not in common_formats:
        return True, f"Uncommon format. Common: {', '.join(common_formats[:3])}"

    return True, None


def validate_config_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate configuration name.

    Rules:
    - Alphanumeric + underscore + hyphen only
    - No spaces
    - Max 100 characters

    Args:
        name: Config name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Configuration name is required"

    if len(name) > 100:
        return False, "Configuration name must be 100 characters or less"

    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False, "Name must contain only alphanumeric, underscore, or hyphen"

    return True, None


def validate_positive_integer(value: str, field_name: str = "Value") -> Tuple[bool, Optional[str]]:
    """
    Validate positive integer string.

    Args:
        value: String value to validate
        field_name: Field name for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return False, f"{field_name} is required"

    try:
        int_value = int(value)
        if int_value < 0:
            return False, f"{field_name} must be a positive integer"
        return True, None
    except ValueError:
        return False, f"{field_name} must be a valid integer"


def validate_required(value: str, field_name: str = "Field") -> Tuple[bool, Optional[str]]:
    """
    Validate required field.

    Args:
        value: Value to check
        field_name: Field name for error message

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or (isinstance(value, str) and not value.strip()):
        return False, f"{field_name} is required"

    return True, None


def validate_max_length(value: str, max_len: int, field_name: str = "Field") -> Tuple[bool, Optional[str]]:
    """
    Validate maximum length.

    Args:
        value: Value to check
        max_len: Maximum allowed length
        field_name: Field name for error message

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value and len(value) > max_len:
        return False, f"{field_name} must be {max_len} characters or less"

    return True, None

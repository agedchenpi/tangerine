"""Input validation utilities for form fields"""

import re
from typing import Optional, Tuple, Dict, List, Any


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


def validate_email_list(emails: str, field_name: str = "Recipients") -> Tuple[bool, Optional[str]]:
    """
    Validate comma-separated list of email addresses.

    Args:
        emails: Comma-separated email addresses
        field_name: Field name for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not emails or not emails.strip():
        return False, f"{field_name} is required"

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    for email in emails.split(','):
        email = email.strip()
        if not email:
            continue

        if not re.match(email_pattern, email):
            return False, f"Invalid email address: {email}"

    return True, None


def validate_cron_expression(
    minute: str,
    hour: str,
    day: str,
    month: str,
    weekday: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate cron expression fields.

    Each field can be:
    - * (any value)
    - */n (every n units)
    - n (specific value)
    - n,m,... (list of values)
    - n-m (range)

    Args:
        minute: Minute field (0-59)
        hour: Hour field (0-23)
        day: Day of month field (1-31)
        month: Month field (1-12)
        weekday: Day of week field (0-6, where 0=Sunday)

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Try using croniter for validation if available
    try:
        from croniter import croniter
        cron_expr = f"{minute} {hour} {day} {month} {weekday}"
        croniter(cron_expr)
        return True, None
    except ImportError:
        pass  # Fall through to manual validation
    except Exception as e:
        return False, f"Invalid cron expression: {str(e)}"

    # Manual validation fallback
    def validate_field(value: str, min_val: int, max_val: int, field_name: str) -> Optional[str]:
        if not value:
            return f"{field_name} is required"

        if value == '*':
            return None

        # Handle */n pattern
        if value.startswith('*/'):
            try:
                step = int(value[2:])
                if step <= 0:
                    return f"{field_name}: step must be positive"
                return None
            except ValueError:
                return f"{field_name}: invalid step value"

        # Handle ranges and lists
        for part in value.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = part.split('-')
                    start, end = int(start), int(end)
                    if start < min_val or end > max_val or start > end:
                        return f"{field_name}: range {part} out of bounds ({min_val}-{max_val})"
                except ValueError:
                    return f"{field_name}: invalid range {part}"
            else:
                try:
                    val = int(part)
                    if val < min_val or val > max_val:
                        return f"{field_name}: value {val} out of bounds ({min_val}-{max_val})"
                except ValueError:
                    return f"{field_name}: invalid value {part}"

        return None

    error = validate_field(minute, 0, 59, "Minute")
    if error:
        return False, error

    error = validate_field(hour, 0, 23, "Hour")
    if error:
        return False, error

    error = validate_field(day, 1, 31, "Day")
    if error:
        return False, error

    error = validate_field(month, 1, 12, "Month")
    if error:
        return False, error

    error = validate_field(weekday, 0, 6, "Weekday")
    if error:
        return False, error

    return True, None


def validate_sql_query(query: str) -> Tuple[bool, Optional[str]]:
    """
    Validate SQL query for report templates.

    Only SELECT queries are allowed. Dangerous keywords are blocked.

    Args:
        query: SQL query string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "SQL query is required"

    # Normalize whitespace and case
    normalized = ' '.join(query.upper().split())

    # Must start with SELECT
    if not normalized.startswith('SELECT'):
        return False, "Only SELECT queries are allowed"

    # Block dangerous keywords
    dangerous = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE',
        'GRANT', 'REVOKE', 'CREATE', 'EXEC', 'EXECUTE', 'CALL',
        'INTO OUTFILE', 'INTO DUMPFILE', 'LOAD_FILE'
    ]

    for keyword in dangerous:
        # Check for keyword as whole word
        if re.search(rf'\b{keyword}\b', normalized):
            return False, f"Query contains forbidden keyword: {keyword}"

    # Check for suspicious patterns
    if '--' in query or '/*' in query:
        return False, "SQL comments are not allowed"

    return True, None


def validate_glob_pattern(pattern: str, field_name: str = "Pattern") -> Tuple[bool, Optional[str]]:
    """
    Validate glob/regex pattern for file matching.

    Args:
        pattern: Glob or regex pattern
        field_name: Field name for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pattern or not pattern.strip():
        return False, f"{field_name} is required"

    # If it looks like a glob pattern, it's valid
    if '*' in pattern or '?' in pattern:
        return True, None

    # Otherwise try to compile as regex
    try:
        re.compile(pattern)
        return True, None
    except re.error as e:
        return False, f"Invalid pattern: {str(e)}"


def validate_cron_field(value: str, field_name: str = "Field") -> Tuple[bool, Optional[str]]:
    """
    Validate a single cron field.

    Args:
        value: Cron field value
        field_name: Field name for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return False, f"{field_name} is required"

    # Basic pattern check: *, */n, n, n-m, n,m,...
    pattern = r'^(\*|(\*/\d+)|(\d+(-\d+)?(,\d+(-\d+)?)*))$'
    if not re.match(pattern, value):
        return False, f"Invalid {field_name.lower()} format: {value}"

    return True, None


def check_regex_match(pattern: str, test_input: str) -> Dict[str, Any]:
    """
    Test a regex pattern against an input string.

    Args:
        pattern: Regex pattern to test
        test_input: String to test against

    Returns:
        Dictionary with:
        - is_valid: Whether pattern compiled successfully
        - matches: Whether pattern matched the input
        - match_text: The matched text (if any)
        - groups: Captured groups (if any)
        - error: Error message if pattern is invalid
    """
    result = {
        'is_valid': False,
        'matches': False,
        'match_text': None,
        'groups': [],
        'error': None
    }

    if not pattern:
        result['error'] = "Pattern is empty"
        return result

    try:
        compiled = re.compile(pattern)
        result['is_valid'] = True

        match = compiled.search(test_input)
        if match:
            result['matches'] = True
            result['match_text'] = match.group(0)
            result['groups'] = list(match.groups()) if match.groups() else []

    except re.error as e:
        result['error'] = f"Invalid regex: {str(e)}"

    return result


def check_glob_match(pattern: str, test_input: str) -> Dict[str, Any]:
    """
    Test a glob pattern against an input string (filename).

    Uses fnmatch for glob-style pattern matching.

    Args:
        pattern: Glob pattern (e.g., *.csv, report_*.xlsx)
        test_input: Filename to test against

    Returns:
        Dictionary with:
        - is_valid: Whether pattern is valid
        - matches: Whether pattern matched the input
        - error: Error message if any
    """
    import fnmatch

    result = {
        'is_valid': True,
        'matches': False,
        'error': None
    }

    if not pattern:
        result['is_valid'] = False
        result['error'] = "Pattern is empty"
        return result

    try:
        result['matches'] = fnmatch.fnmatch(test_input, pattern)
    except Exception as e:
        result['is_valid'] = False
        result['error'] = f"Pattern error: {str(e)}"

    return result


def check_patterns_batch(
    pattern: str,
    test_inputs: List[str],
    pattern_type: str = 'regex'
) -> List[Dict[str, Any]]:
    """
    Test a pattern against multiple input strings.

    Args:
        pattern: Pattern to test
        test_inputs: List of strings to test against
        pattern_type: 'regex' or 'glob'

    Returns:
        List of result dictionaries, one per input
    """
    results = []

    for test_input in test_inputs:
        if pattern_type == 'glob':
            result = check_glob_match(pattern, test_input)
        else:
            result = check_regex_match(pattern, test_input)

        result['input'] = test_input
        results.append(result)

    return results

"""Display formatting utilities for Streamlit interface"""

from datetime import datetime, date
from typing import Any, Optional


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime for display.

    Args:
        dt: Datetime object or None
        format_str: strftime format string

    Returns:
        Formatted string or "N/A" if None
    """
    if dt is None:
        return "N/A"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt  # Return as-is if can't parse

    return dt.strftime(format_str)


def format_date(d: Optional[date], format_str: str = "%Y-%m-%d") -> str:
    """
    Format date for display.

    Args:
        d: Date object or None
        format_str: strftime format string

    Returns:
        Formatted string or "N/A" if None
    """
    if d is None:
        return "N/A"

    if isinstance(d, str):
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return d  # Return as-is if can't parse

    return d.strftime(format_str)


def format_boolean(value: Optional[bool], true_text: str = "Yes", false_text: str = "No") -> str:
    """
    Format boolean for display.

    Args:
        value: Boolean value or None
        true_text: Text for True
        false_text: Text for False

    Returns:
        Formatted string or "N/A" if None
    """
    if value is None:
        return "N/A"

    return true_text if value else false_text


def format_number(value: Optional[float], decimals: int = 2) -> str:
    """
    Format number for display.

    Args:
        value: Number value or None
        decimals: Number of decimal places

    Returns:
        Formatted string with thousand separators or "N/A" if None
    """
    if value is None:
        return "N/A"

    if decimals == 0:
        return f"{int(value):,}"
    else:
        return f"{value:,.{decimals}f}"


def format_filesize(bytes_count: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        bytes_count: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if bytes_count is None or bytes_count < 0:
        return "N/A"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_count)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"


def format_duration(seconds: Optional[float]) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2m 30s" or "1h 15m")
    """
    if seconds is None or seconds < 0:
        return "N/A"

    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate string with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated

    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_list(items: list, separator: str = ", ", max_items: int = 5) -> str:
    """
    Format list of items for display.

    Args:
        items: List of items
        separator: Separator between items
        max_items: Maximum items to show before truncating

    Returns:
        Formatted string
    """
    if not items:
        return "None"

    if len(items) <= max_items:
        return separator.join(str(item) for item in items)
    else:
        visible = separator.join(str(item) for item in items[:max_items])
        return f"{visible} (+{len(items) - max_items} more)"


def format_status_badge(status: str) -> str:
    """
    Format status as colored badge (HTML).

    Args:
        status: Status string (e.g., "Active", "Failed", "Pending")

    Returns:
        HTML string with colored badge
    """
    status_colors = {
        "active": "#28a745",
        "success": "#28a745",
        "completed": "#28a745",
        "passed": "#28a745",
        "inactive": "#6c757d",
        "pending": "#ffc107",
        "warning": "#ffc107",
        "failed": "#dc3545",
        "error": "#dc3545"
    }

    color = status_colors.get(status.lower(), "#17a2b8")  # Default to info blue
    return f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; font-weight: 500;">{status}</span>'


def format_null(value: Any, default: str = "N/A") -> Any:
    """
    Replace None/null values with default text.

    Args:
        value: Value to check
        default: Default text for None

    Returns:
        Original value or default if None
    """
    return default if value is None else value


# Aliases for convenience
format_timestamp = format_datetime
truncate_text = truncate_string

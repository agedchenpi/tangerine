"""Display formatting utilities for Streamlit interface"""

from datetime import datetime
from typing import Optional


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


# Aliases for convenience
format_timestamp = format_datetime
truncate_text = truncate_string

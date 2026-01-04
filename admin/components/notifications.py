"""User notification utilities for Streamlit interface"""

import streamlit as st


def show_success(message: str):
    """Display success message with checkmark icon."""
    st.success(f"✓ {message}", icon="✅")


def show_error(message: str):
    """Display error message with X icon."""
    st.error(f"✗ {message}", icon="🚨")


def show_warning(message: str):
    """Display warning message with warning icon."""
    st.warning(f"⚠ {message}", icon="⚠️")


def show_info(message: str):
    """Display info message with info icon."""
    st.info(f"ℹ {message}", icon="ℹ️")


def show_validation_error(field: str, message: str):
    """
    Display field-specific validation error.

    Args:
        field: Field name (e.g., "Source Directory")
        message: Error message
    """
    st.markdown(
        f'<span style="color: #dc3545; font-weight: 500;">**{field}:** {message}</span>',
        unsafe_allow_html=True
    )


def show_status(status: str, message: str):
    """
    Display status-based notification.

    Args:
        status: One of "success", "error", "warning", "info"
        message: Message to display
    """
    status_map = {
        "success": show_success,
        "error": show_error,
        "warning": show_warning,
        "info": show_info
    }

    handler = status_map.get(status.lower(), show_info)
    handler(message)

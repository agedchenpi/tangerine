"""User notification utilities for Streamlit interface with enhanced styling"""

import streamlit as st


def show_success(message: str):
    """
    Display success message with enhanced visual styling.

    Args:
        message: Success message to display
    """
    st.success(f"✅ **Success!** {message}", icon="✅")
    # Add toast for better UX
    st.toast(f"✅ {message}", icon="✅")


def show_error(message: str):
    """
    Display error message with enhanced visual styling.

    Args:
        message: Error message to display
    """
    st.error(f"🚨 **Error!** {message}", icon="🚨")


def show_warning(message: str):
    """
    Display warning message with enhanced visual styling.

    Args:
        message: Warning message to display
    """
    st.warning(f"⚠️ **Warning!** {message}", icon="⚠️")


def show_info(message: str):
    """
    Display info message with enhanced visual styling.

    Args:
        message: Info message to display
    """
    st.info(f"ℹ️ **Info:** {message}", icon="ℹ️")



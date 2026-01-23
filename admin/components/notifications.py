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



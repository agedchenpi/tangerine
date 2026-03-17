"""User notification utilities for Streamlit interface with enhanced styling"""

import logging

import streamlit as st

logger = logging.getLogger("notifications")


def show_success(message: str):
    logger.info("UI success: %s", message)
    st.success(f"✅ **Success!** {message}", icon="✅")
    st.toast(f"✅ {message}", icon="✅")


def show_error(message: str):
    logger.error("UI error: %s", message)
    st.error(f"🚨 **Error!** {message}", icon="🚨")


def show_warning(message: str):
    logger.warning("UI warning: %s", message)
    st.warning(f"⚠️ **Warning!** {message}", icon="⚠️")


def show_info(message: str):
    logger.info("UI info: %s", message)
    st.info(f"ℹ️ **Info:** {message}", icon="ℹ️")



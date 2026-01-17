"""
Tangerine ETL Admin Interface

Multi-page Streamlit application for managing ETL configurations,
executing jobs, and monitoring pipeline health.

This file serves as the navigation entry point using st.navigation().
"""

import streamlit as st
from common.db_utils import test_connection

# Set page config (must be first Streamlit command)
st.set_page_config(
    page_title="Tangerine ETL Admin",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for database connection
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = test_connection()

# Define all pages with groups
pages = {
    "Home": [
        st.Page("pages/home.py", title="Dashboard", icon="🏠", default=True),
    ],
    "Configuration": [
        st.Page("pages/imports.py", title="Imports", icon="📋"),
        st.Page("pages/inbox_rules.py", title="Inbox Rules", icon="📧"),
        st.Page("pages/reference_data.py", title="Reference Data", icon="🏷️"),
        st.Page("pages/scheduler.py", title="Scheduler", icon="⏰"),
    ],
    "Operations": [
        st.Page("pages/run_jobs.py", title="Run Jobs", icon="▶️"),
        st.Page("pages/monitoring.py", title="Monitoring", icon="📊"),
        st.Page("pages/reports.py", title="Reports", icon="📄"),
    ],
    "System": [
        st.Page("pages/event_system.py", title="Event System", icon="🔔"),
    ],
}

# Build navigation
nav = st.navigation(pages)

# Add sidebar content
with st.sidebar:
    st.markdown("---")

    # Database connection status
    if st.session_state.db_connected:
        st.success("Database Connected")
    else:
        st.error("Database Disconnected")
        st.caption("Check DB_URL environment variable")

# Run the selected page
nav.run()

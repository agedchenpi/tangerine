"""
Tangerine ETL Admin - Home Dashboard

Main landing page with system status, features overview, and quick start guide.
"""

import streamlit as st
from datetime import datetime, timedelta
from common.db_utils import test_connection, fetch_dict
from utils.db_helpers import get_count
from utils.ui_helpers import load_custom_css, add_page_header

# Load custom CSS styling
load_custom_css()

# Initialize session state
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = test_connection()

# Main page content
add_page_header(
    title="Tangerine ETL Administration",
    subtitle="Manage ETL configurations, execute jobs, and monitor pipeline health.",
    icon="🍊"
)

# System Status Metrics
st.markdown("### System Status")

col1, col2, col3, col4 = st.columns(4)

with col1:
    db_status = "Connected" if st.session_state.db_connected else "Disconnected"
    st.metric("Database", db_status)

with col2:
    try:
        active_configs = get_count("dba.timportconfig", "is_active = %s", (True,))
        st.metric("Active Configs", active_configs)
    except Exception:
        st.metric("Active Configs", "N/A")

with col3:
    try:
        # Count unique runs in last 24 hours
        query = """
            SELECT COUNT(DISTINCT run_uuid) as count
            FROM dba.tlogentry
            WHERE timestamp >= %s
        """
        result = fetch_dict(query, (datetime.now() - timedelta(hours=24),))
        job_count = result[0]['count'] if result else 0
        st.metric("Jobs (24h)", job_count)
    except Exception:
        st.metric("Jobs (24h)", "N/A")

with col4:
    try:
        # Count total datasets
        total_datasets = get_count("dba.tdataset")
        st.metric("Total Datasets", total_datasets)
    except Exception:
        st.metric("Total Datasets", "N/A")

st.markdown("---")

# Features Overview
st.markdown("### Features")

tab1, tab2, tab3, tab4 = st.tabs([
    "Configuration",
    "Operations",
    "Reports",
    "System"
])

with tab1:
    st.markdown("""
    **Configuration Management**

    Set up data sources, import rules, and processing schedules:

    - **Imports**: Create and manage ETL import configurations for CSV, XLS, XLSX, JSON, and XML files
    - **Inbox Rules**: Configure Gmail inbox processing to automatically download email attachments
    - **Reference Data**: Manage data sources, dataset types, and import strategies
    - **Scheduler**: Set up automated cron jobs to run imports on schedule
    """)

with tab2:
    st.markdown("""
    **Operations**

    Execute jobs and monitor pipeline health:

    - **Run Jobs**: Trigger ETL imports directly with real-time output streaming
    - **Monitoring**: View logs, browse datasets, and analyze system statistics
    """)

with tab3:
    st.markdown("""
    **Reports**

    Configure and manage email reports:

    - **Report Manager**: Create SQL-based email reports with HTML tables and attachments
    - Configure recipients, output formats (CSV/Excel), and delivery schedules
    """)

with tab4:
    st.markdown("""
    **System**

    Advanced system tools:

    - **Event System**: Manage pub/sub events and subscribers for automation workflows
    - View event queues, configure triggers, and monitor service status
    """)

st.markdown("---")

# Quick Start Guide
st.markdown("### Quick Start")

st.markdown("""
1. **First Time Setup**:
   - Navigate to **Configuration > Reference Data** and add your data sources and dataset types
   - Ensure your source files are placed in `./.data/etl/source/` on your local machine

2. **Create Import Configuration**:
   - Go to **Configuration > Imports** and create a new configuration
   - Fill in all required fields and test your file pattern regex before saving

3. **Run Your First Job**:
   - Navigate to **Operations > Run Jobs**
   - Select your configuration and click "Run Job" (use dry-run mode to test first)

4. **Monitor Results**:
   - Go to **Operations > Monitoring** to see execution logs and verify loaded data
""")

# Footer
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("*Tangerine ETL Pipeline v1.0 | Built with Streamlit*")
with col2:
    if st.button("Refresh Metrics"):
        st.rerun()

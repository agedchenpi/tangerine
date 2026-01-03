"""
Tangerine ETL Admin Interface

Multi-page Streamlit application for managing ETL configurations,
executing jobs, and monitoring pipeline health.
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

# Initialize session state
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = test_connection()

# Sidebar
with st.sidebar:
    st.markdown("## 🍊 Tangerine ETL")
    st.markdown("---")
    st.markdown("### Navigation")
    st.markdown("Use the pages above to:")
    st.markdown("- Manage import configs")
    st.markdown("- Update reference data")
    st.markdown("- Run ETL jobs")
    st.markdown("- Monitor pipeline")
    st.markdown("---")

    # Database connection status
    if st.session_state.db_connected:
        st.success("✓ Database Connected")
    else:
        st.error("✗ Database Disconnected")
        st.caption("Check DB_URL environment variable")

# Main page content
st.title("🍊 Tangerine ETL Administration")

st.markdown("""
Welcome to the Tangerine ETL admin interface. This tool allows you to:

### Features

**1. Import Configuration Management** 📋
- Create, view, edit, and delete import configurations
- Configure file patterns, metadata extraction, and import strategies
- Manage CSV, XLS, XLSX, JSON, and XML imports

**2. Reference Data Management** 📚
- Manage data sources and dataset types
- View import strategies (read-only)

**3. Job Execution** ▶️
- Trigger generic import jobs from UI
- Monitor job progress in real-time
- View execution logs

**4. System Monitoring** 📊
- View recent ETL logs
- Browse dataset records
- Filter and search historical runs

### Quick Start

1. Navigate to **Import Configs** to create a new configuration
2. Set up your data source and dataset type in **Reference Data**
3. Use **Run Jobs** to execute imports
4. Check **Monitoring** for job status and logs

### System Status
""")

# Display connection info
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Database", "Connected" if st.session_state.db_connected else "Disconnected")

with col2:
    st.metric("Active Configs", "N/A")

with col3:
    st.metric("Jobs (24h)", "N/A")

st.info("Select a page from the sidebar to get started. (Pages coming in Phase 2-6)")

# Footer
st.markdown("---")
st.markdown("*Tangerine ETL Pipeline v1.0 | Built with Streamlit*")

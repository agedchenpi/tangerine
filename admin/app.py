"""
Tangerine ETL Admin Interface

Multi-page Streamlit application for managing ETL configurations,
executing jobs, and monitoring pipeline health.
"""

import streamlit as st
from datetime import datetime, timedelta
from common.db_utils import test_connection, fetch_dict
from utils.db_helpers import get_count

# Set page config (must be first Streamlit command)
st.set_page_config(
    page_title="Tangerine ETL Admin",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for improved styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF6B35;
        margin-bottom: 1rem;
    }
    .feature-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #FF6B35;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = test_connection()

# Sidebar
with st.sidebar:
    st.markdown("## 🍊 Tangerine ETL")
    st.markdown("---")
    st.markdown("### Navigation")
    st.markdown("Use the pages above to:")
    st.markdown("- 📋 Manage import configs")
    st.markdown("- 📚 Update reference data")
    st.markdown("- ▶️ Run ETL jobs")
    st.markdown("- 📊 Monitor pipeline")
    st.markdown("---")

    # Database connection status
    if st.session_state.db_connected:
        st.success("✓ Database Connected")
    else:
        st.error("✗ Database Disconnected")
        st.caption("Check DB_URL environment variable")

    # System info
    st.markdown("---")
    st.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}")

# Main page content
st.markdown('<div class="main-header">🍊 Tangerine ETL Administration</div>', unsafe_allow_html=True)

st.markdown("""
Welcome to the Tangerine ETL admin interface. This tool allows you to manage ETL configurations,
execute jobs, and monitor pipeline health without writing SQL commands.
""")

# System Status Metrics
st.markdown("### 📊 System Status")

col1, col2, col3, col4 = st.columns(4)

with col1:
    db_status = "🟢 Connected" if st.session_state.db_connected else "🔴 Disconnected"
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
st.markdown("### ✨ Features")

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Import Configs",
    "📚 Reference Data",
    "▶️ Job Execution",
    "📊 Monitoring"
])

with tab1:
    st.markdown("""
    **Import Configuration Management**

    Create and manage ETL import configurations with a user-friendly form interface:
    - ✅ Create new configurations for CSV, XLS, XLSX, JSON, and XML files
    - ✅ Edit existing configurations with full field validation
    - ✅ Configure file patterns, metadata extraction, and import strategies
    - ✅ Test configurations before deploying to production
    - ✅ Activate/deactivate configurations without deleting

    *Navigate to "Import Configs" page to get started.*
    """)

with tab2:
    st.markdown("""
    **Reference Data Management**

    Manage reference tables that power dropdown selections:
    - 📌 **Data Sources**: Add/edit data source names
    - 📌 **Dataset Types**: Configure dataset type categories
    - 📌 **Import Strategies**: View the 3 predefined strategies
      - Strategy 1: Auto-create new columns if needed
      - Strategy 2: Ignore columns not in target table
      - Strategy 3: Fail if columns are missing

    *Navigate to "Reference Data" page to manage these tables.*
    """)

with tab3:
    st.markdown("""
    **Job Execution**

    Trigger ETL imports directly from the web interface:
    - ▶️ Select from active import configurations
    - ▶️ Set run date and dry-run mode
    - ▶️ View real-time job output (stdout/stderr)
    - ▶️ Monitor job execution with timeout protection
    - ▶️ Review recent job history per configuration

    *Navigate to "Run Jobs" page to execute imports.*
    """)

with tab4:
    st.markdown("""
    **System Monitoring**

    Comprehensive pipeline monitoring and analytics:
    - 📈 **Logs**: View and filter ETL process logs
      - Time range filtering (1h to 7 days)
      - Process type and run UUID filtering
      - Export to CSV for analysis
    - 📁 **Datasets**: Browse all dataset records
      - Filter by datasource and datasettype
      - View status and creation dates
    - 📊 **Statistics**: System metrics and charts
      - Jobs per day trend chart
      - Process type distribution
      - Average runtimes

    *Navigate to "Monitoring" page for detailed insights.*
    """)

st.markdown("---")

# Quick Start Guide
st.markdown("### 🚀 Quick Start")

st.markdown("""
1. **First Time Setup**:
   - Navigate to **Reference Data** and add your data sources and dataset types
   - Ensure your source files are placed in `./.data/etl/source/` on your local machine

2. **Create Import Configuration**:
   - Go to **Import Configs** → "Create New" tab
   - Fill in all required fields (19 configuration options)
   - Test your file pattern regex before saving

3. **Run Your First Job**:
   - Navigate to **Run Jobs**
   - Select your configuration from the dropdown
   - Click "Run Job" (use dry-run mode to test first)

4. **Monitor Results**:
   - Go to **Monitoring** → "Logs" tab to see execution logs
   - Check **Monitoring** → "Datasets" tab to verify loaded data
""")

# Footer
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("*Tangerine ETL Pipeline v1.0 | Built with Streamlit*")
with col2:
    if st.button("🔄 Refresh Metrics"):
        st.rerun()

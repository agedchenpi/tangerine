"""
Tangerine ETL Admin Interface

Multi-page Streamlit application for managing ETL configurations,
executing jobs, and monitoring pipeline health.

This file serves as the navigation entry point using st.navigation().
"""

import streamlit as st
from common.db_utils import test_connection
from admin.utils.ui_helpers import load_custom_css, initialize_recent_items, get_recent_items, clear_recent_items

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

# Initialize theme in session state
# Use query parameter to sync with localStorage (workaround for Streamlit's JS timing)
if 'theme' not in st.session_state:
    # Check if theme is in query params (set by localStorage JS)
    theme_from_query = st.query_params.get('theme', 'light')
    st.session_state.theme = theme_from_query if theme_from_query in ['light', 'dark'] else 'light'

# Inject JavaScript to sync localStorage with session state via query params
st.markdown("""
    <script>
    (function() {
        const savedTheme = localStorage.getItem('tangerine_theme');
        const urlParams = new URLSearchParams(window.location.search);
        const currentTheme = urlParams.get('theme');

        // If localStorage has a theme and it differs from URL, update URL
        if (savedTheme && savedTheme !== currentTheme) {
            console.log('[Theme Sync] Syncing localStorage theme:', savedTheme);
            urlParams.set('theme', savedTheme);
            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.history.replaceState({}, '', newUrl);
            // Trigger Streamlit rerun to pick up the query param
            window.location.reload();
        }

        // If no localStorage theme exists, save current theme from URL
        if (!savedTheme && currentTheme) {
            localStorage.setItem('tangerine_theme', currentTheme);
            console.log('[Theme Sync] Initialized localStorage with:', currentTheme);
        }
    })();
    </script>
""", unsafe_allow_html=True)

# Initialize recent items tracking
initialize_recent_items()

# Load custom CSS with theme support (includes nav header fix)
load_custom_css()

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

    # Recent items section
    st.markdown("---")
    recent_items = get_recent_items(limit=5)

    if recent_items:
        with st.expander("📌 Recent Items", expanded=False):
            for item in recent_items:
                # Format timestamp
                time_ago = (st.session_state.get('_current_time', item['timestamp']) - item['timestamp']).total_seconds()
                if time_ago < 60:
                    time_str = "just now"
                elif time_ago < 3600:
                    time_str = f"{int(time_ago / 60)}m ago"
                elif time_ago < 86400:
                    time_str = f"{int(time_ago / 3600)}h ago"
                else:
                    time_str = f"{int(time_ago / 86400)}d ago"

                # Display item
                st.caption(f"**{item['type']}**")
                st.text(f"{item['name']}")
                st.caption(f"🕒 {time_str}")
                st.markdown("---")

            # Clear button
            if st.button("🗑️ Clear Recent Items", key="clear_recent", use_container_width=True):
                clear_recent_items()
                st.rerun()

    # Theme toggle at bottom
    st.markdown("---")

    # Toggle switch for dark mode
    dark_mode = st.toggle(
        "🌙 Dark Mode",
        value=st.session_state.theme == 'dark',
        key="theme_toggle",
        help="Toggle between light and dark themes"
    )

    # Apply theme change on toggle and persist to localStorage + query params
    if dark_mode and st.session_state.theme == 'light':
        st.session_state.theme = 'dark'
        st.query_params['theme'] = 'dark'
        # Persist to localStorage
        st.markdown("""
            <script>
            localStorage.setItem('tangerine_theme', 'dark');
            console.log('[Theme] Saved dark mode to localStorage');
            </script>
        """, unsafe_allow_html=True)
        st.rerun()
    elif not dark_mode and st.session_state.theme == 'dark':
        st.session_state.theme = 'light'
        st.query_params['theme'] = 'light'
        # Persist to localStorage
        st.markdown("""
            <script>
            localStorage.setItem('tangerine_theme', 'light');
            console.log('[Theme] Saved light mode to localStorage');
            </script>
        """, unsafe_allow_html=True)
        st.rerun()

# Run the selected page
nav.run()

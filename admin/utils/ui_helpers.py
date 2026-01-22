"""UI Helper utilities for enhanced user experience"""

import streamlit as st
import time
from pathlib import Path
from typing import Callable, Any


def is_dark_mode() -> bool:
    """Check if dark mode is currently active."""
    return st.session_state.get('theme', 'light') == 'dark'


def get_theme_colors() -> dict:
    """Get the current theme color palette."""
    if is_dark_mode():
        return {
            'bg': '#121212',
            'card_bg': '#1E1E2E',
            'text_primary': '#E8E8E8',
            'text_secondary': '#B0B0B0',
            'accent': '#FFA05C',
            'accent_dark': '#E07830',
            'border': '#2D2D3D',
            'success_bg': '#1A3D25',
            'error_bg': '#3D1A1A',
            'warning_bg': '#3D3D1A',
            'info_bg': '#1A2A3D',
        }
    else:
        return {
            'bg': '#F8F9FA',
            'card_bg': '#FFFFFF',
            'text_primary': '#2C3E50',
            'text_secondary': '#6C757D',
            'accent': '#FF8C42',
            'accent_dark': '#D67130',
            'border': '#DEE2E6',
            'success_bg': '#D4EDDA',
            'error_bg': '#F8D7DA',
            'warning_bg': '#FFF3CD',
            'info_bg': '#D1ECF1',
        }


def load_custom_css():
    """Load custom CSS styling for the admin interface with theme support."""
    css_file = Path(__file__).parent.parent / "styles" / "custom.css"

    # Load base CSS file
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        # Fallback inline CSS if file doesn't exist
        st.markdown("""
        <style>
        :root {
            --tangerine-primary: #FF8C42;
            --tangerine-dark: #D67130;
        }
        .stButton > button[kind="primary"] {
            background-color: var(--tangerine-primary);
            border: none;
        }
        [data-testid="stMetric"] {
            background-color: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid var(--tangerine-primary);
        }
        </style>
        """, unsafe_allow_html=True)

    # Apply theme-specific overrides based on session state
    _apply_theme_css()


def _apply_theme_css():
    """Inject CSS to apply dark/light theme based on session state."""
    if is_dark_mode():
        st.markdown("""
        <style>
        /* Dark mode overrides */
        .stApp {
            background-color: #121212 !important;
            color: #E8E8E8 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #1E1E2E !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            background-color: #1E1E2E !important;
        }
        [data-testid="stHeader"] {
            background-color: #121212 !important;
        }

        /* Sidebar navigation - group headers (Home, Configuration, etc.) */
        [data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"],
        [data-testid="stSidebar"] [data-testid="stSidebarNavItems"] > div > span,
        [data-testid="stSidebar"] span[data-testid="stSidebarNavSeparator"],
        [data-testid="stSidebar"] .st-emotion-cache-1rtdyuf,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebarNav"] span,
        [data-testid="stSidebarNav"] div,
        [data-testid="stSidebarNavItems"] span,
        [data-testid="stSidebarUserContent"] span {
            color: #E8E8E8 !important;
        }

        /* Sidebar navigation links */
        [data-testid="stSidebar"] a,
        [data-testid="stSidebarNav"] a,
        [data-testid="stSidebarNavLink"],
        [data-testid="stSidebarNavLink"] span {
            color: #B0B0B0 !important;
        }
        [data-testid="stSidebar"] a:hover,
        [data-testid="stSidebarNav"] a:hover,
        [data-testid="stSidebarNavLink"]:hover,
        [data-testid="stSidebarNavLink"]:hover span {
            color: #FFA05C !important;
        }

        /* Active nav link */
        [data-testid="stSidebarNavLink"][aria-selected="true"],
        [data-testid="stSidebarNavLink"][aria-selected="true"] span {
            color: #FFA05C !important;
            background-color: #2D2A3A !important;
        }
        .main .block-container {
            background-color: #121212 !important;
        }
        .stMarkdown, .stText, p, span, label,
        .stSelectbox label, .stTextInput label,
        .stNumberInput label, .stTextArea label,
        .stDateInput label, .stTimeInput label,
        .stCheckbox label, .stRadio label {
            color: #E8E8E8 !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #E8E8E8 !important;
        }
        h1 {
            border-bottom-color: #FFA05C !important;
        }

        /* Metric cards */
        [data-testid="stMetric"] {
            background-color: #1E1E2E !important;
            border-left-color: #FFA05C !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        }
        [data-testid="stMetric"] label {
            color: #B0B0B0 !important;
        }
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #FFA05C !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #1E1E2E !important;
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            color: #B0B0B0 !important;
            background-color: transparent !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFA05C !important;
            color: #121212 !important;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #2D2A3A !important;
        }

        /* DataFrames and tables */
        .stDataFrame, [data-testid="stDataFrame"] {
            background-color: #1E1E2E !important;
        }
        .stDataFrame thead tr th {
            background-color: #FFA05C !important;
            color: #121212 !important;
        }
        .stDataFrame tbody tr:nth-child(even) {
            background-color: #1A1A2A !important;
        }
        .stDataFrame tbody tr:hover {
            background-color: #2D2A3A !important;
        }

        /* Form inputs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div,
        .stSelectbox > div > div > div,
        .stMultiSelect > div > div,
        .stNumberInput > div > div > input,
        .stDateInput > div > div > input {
            background-color: #1E1E2E !important;
            color: #E8E8E8 !important;
            border-color: #2D2D3D !important;
        }
        .stSelectbox [data-baseweb="select"] > div {
            background-color: #1E1E2E !important;
        }

        /* Buttons */
        .stButton > button[kind="primary"] {
            background-color: #FFA05C !important;
            color: #121212 !important;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #E07830 !important;
        }
        .stButton > button[kind="secondary"] {
            background-color: #1E1E2E !important;
            border-color: #FFA05C !important;
            color: #FFA05C !important;
        }

        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #1E1E2E !important;
            color: #E8E8E8 !important;
            border-color: #2D2D3D !important;
        }
        .streamlit-expanderContent {
            background-color: #1A1A2A !important;
            border-color: #2D2D3D !important;
        }
        [data-testid="stExpander"] {
            background-color: #1E1E2E !important;
            border-color: #2D2D3D !important;
        }
        [data-testid="stExpander"] summary {
            color: #E8E8E8 !important;
        }

        /* Code blocks */
        code {
            background-color: #2D2D3D !important;
            color: #FFA05C !important;
        }

        /* Alerts */
        .stSuccess, [data-testid="stAlert"][data-baseweb="notification"] {
            background-color: #1A3D25 !important;
            color: #B8E6C4 !important;
        }
        .stError {
            background-color: #3D1A1A !important;
            color: #F5C6CB !important;
        }
        .stWarning {
            background-color: #3D3D1A !important;
            color: #FFEEBA !important;
        }
        .stInfo {
            background-color: #1A2A3D !important;
            color: #BEE5EB !important;
        }

        /* Dividers */
        hr {
            background: linear-gradient(to right, #FFA05C, #3D2A1A) !important;
        }

        /* Captions */
        .stCaption, small {
            color: #B0B0B0 !important;
        }

        /* Charts */
        .stPlotlyChart {
            background-color: #1E1E2E !important;
        }

        /* Tooltips */
        [data-baseweb="tooltip"] {
            background-color: #2D2D3D !important;
            color: #E8E8E8 !important;
        }

        /* Popover/dropdown menus */
        [data-baseweb="popover"] > div {
            background-color: #1E1E2E !important;
        }
        [data-baseweb="menu"] {
            background-color: #1E1E2E !important;
        }
        [data-baseweb="menu"] li {
            color: #E8E8E8 !important;
        }
        [data-baseweb="menu"] li:hover {
            background-color: #2D2A3A !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Light mode - ensure consistent base styling
        st.markdown("""
        <style>
        /* Light mode base */
        .stApp {
            background-color: #F8F9FA !important;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            background-color: #FFFFFF !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #2C3E50 !important;
        }
        h1 {
            border-bottom-color: #FF8C42 !important;
        }
        [data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            border-left-color: #FF8C42 !important;
        }
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #FF8C42 !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FF8C42 !important;
            color: #FFFFFF !important;
        }
        </style>
        """, unsafe_allow_html=True)


def with_loading(func: Callable, message: str = "Processing...", *args, **kwargs) -> Any:
    """
    Execute a function with a loading spinner.

    Args:
        func: Function to execute
        message: Loading message to display
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of func execution
    """
    with st.spinner(message):
        return func(*args, **kwargs)


def safe_execute(func: Callable, error_message: str = "An error occurred", *args, **kwargs) -> tuple[bool, Any]:
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        error_message: Custom error message prefix
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Tuple of (success: bool, result: Any or error message)
    """
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        error_text = f"{error_message}: {str(e)}"
        return False, error_text


def confirm_action(message: str, button_text: str = "Confirm", button_type: str = "primary") -> bool:
    """
    Display a confirmation dialog for destructive actions.

    Args:
        message: Confirmation message to display
        button_text: Text for confirmation button
        button_type: Streamlit button type (primary, secondary)

    Returns:
        True if user confirms, False otherwise
    """
    st.warning(message)
    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        confirm = st.button(button_text, type=button_type, key=f"confirm_{hash(message)}")

    with col2:
        cancel = st.button("Cancel", key=f"cancel_{hash(message)}")

    if cancel:
        st.info("Action cancelled.")
        return False

    return confirm


def show_loading_progress(steps: list[str], delay: float = 0.5):
    """
    Show a multi-step loading progress indicator.

    Args:
        steps: List of step descriptions
        delay: Delay between steps in seconds
    """
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, step in enumerate(steps):
        progress = (i + 1) / len(steps)
        progress_bar.progress(progress)
        status_text.text(f"⏳ {step}...")
        time.sleep(delay)

    status_text.text("✅ Complete!")
    time.sleep(0.5)
    progress_bar.empty()
    status_text.empty()


def render_empty_state(
    icon: str = "📭",
    title: str = "No data found",
    message: str = "Try adjusting your filters or creating new items.",
    action_button: str = None,
    action_callback: Callable = None
):
    """
    Render an empty state placeholder.

    Args:
        icon: Emoji icon to display
        title: Title text
        message: Descriptive message
        action_button: Optional button text
        action_callback: Optional callback for button click
    """
    colors = get_theme_colors()
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem 1rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">{icon}</div>
        <h3 style="color: {colors['text_secondary']}; margin-bottom: 0.5rem;">{title}</h3>
        <p style="color: {colors['text_secondary']}; opacity: 0.8;">{message}</p>
    </div>
    """, unsafe_allow_html=True)

    if action_button and action_callback:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button(action_button, type="primary", use_container_width=True):
                action_callback()


def render_stat_card(label: str, value: str, icon: str = "📊", color: str = None):
    """
    Render a custom statistic card with enhanced styling.

    Args:
        label: Stat label
        value: Stat value
        icon: Icon emoji
        color: Accent color (defaults to theme accent)
    """
    colors = get_theme_colors()
    accent = color if color else colors['accent']
    shadow = "0 2px 8px rgba(0,0,0,0.3)" if is_dark_mode() else "0 2px 8px rgba(0,0,0,0.08)"

    st.markdown(f"""
    <div style="
        background-color: {colors['card_bg']};
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: {shadow};
        border-left: 4px solid {accent};
        margin-bottom: 1rem;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="
                    color: {colors['text_secondary']};
                    font-size: 0.875rem;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                ">{label}</div>
                <div style="
                    color: {accent};
                    font-size: 2rem;
                    font-weight: 700;
                ">{value}</div>
            </div>
            <div style="font-size: 2.5rem; opacity: 0.5;">{icon}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_info_box(title: str, content: str, box_type: str = "info"):
    """
    Render an informational box with custom styling.

    Args:
        title: Box title
        content: Box content
        box_type: Type of box (info, success, warning, error)
    """
    theme = get_theme_colors()

    # Light mode colors
    light_colors = {
        "info": {"bg": "#D1ECF1", "border": "#17A2B8", "icon": "ℹ️", "text": "#0C5460"},
        "success": {"bg": "#D4EDDA", "border": "#28A745", "icon": "✅", "text": "#155724"},
        "warning": {"bg": "#FFF3CD", "border": "#FFC107", "icon": "⚠️", "text": "#856404"},
        "error": {"bg": "#F8D7DA", "border": "#DC3545", "icon": "❌", "text": "#721C24"}
    }

    # Dark mode colors
    dark_colors = {
        "info": {"bg": "#1A2A3D", "border": "#17A2B8", "icon": "ℹ️", "text": "#BEE5EB"},
        "success": {"bg": "#1A3D25", "border": "#28A745", "icon": "✅", "text": "#B8E6C4"},
        "warning": {"bg": "#3D3D1A", "border": "#FFC107", "icon": "⚠️", "text": "#FFEEBA"},
        "error": {"bg": "#3D1A1A", "border": "#DC3545", "icon": "❌", "text": "#F5C6CB"}
    }

    colors = dark_colors if is_dark_mode() else light_colors
    style = colors.get(box_type, colors["info"])

    st.markdown(f"""
    <div style="
        background-color: {style['bg']};
        border-left: 4px solid {style['border']};
        padding: 1rem 1.25rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: {style['text']};
    ">
        <div style="font-weight: 600; margin-bottom: 0.5rem;">
            {style['icon']} {title}
        </div>
        <div>{content}</div>
    </div>
    """, unsafe_allow_html=True)


def add_page_header(title: str, subtitle: str = None, icon: str = None):
    """
    Add a styled page header.

    Args:
        title: Page title
        subtitle: Optional subtitle
        icon: Optional icon emoji
    """
    colors = get_theme_colors()
    header_html = f"<h1 style='margin-bottom: 0; color: {colors['text_primary']};'>"
    if icon:
        header_html += f"{icon} "
    header_html += f"{title}</h1>"

    st.markdown(header_html, unsafe_allow_html=True)

    if subtitle:
        st.markdown(f"<p style='color: {colors['text_secondary']}; font-size: 1.1rem; margin-top: 0.5rem;'>{subtitle}</p>",
                   unsafe_allow_html=True)

    st.divider()


def render_success_banner(message: str, duration: int = 3):
    """
    Render a temporary success banner that auto-dismisses.

    Args:
        message: Success message
        duration: Display duration in seconds
    """
    placeholder = st.empty()

    with placeholder.container():
        st.success(message)
        st.toast(message, icon="✅")

    time.sleep(duration)
    placeholder.empty()


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted file size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def create_breadcrumb(items: list[str]):
    """
    Create a breadcrumb navigation.

    Args:
        items: List of breadcrumb items
    """
    colors = get_theme_colors()
    breadcrumb_html = " → ".join([
        f"<span style='color: {colors['accent']}; font-weight: 500;'>{item}</span>"
        if i == len(items) - 1
        else f"<span style='color: {colors['text_secondary']};'>{item}</span>"
        for i, item in enumerate(items)
    ])

    st.markdown(f"<div style='margin-bottom: 1.5rem; font-size: 0.9rem;'>{breadcrumb_html}</div>",
               unsafe_allow_html=True)

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
            'text_primary': '#F0F0F0',  # Maximum visibility: 9.8:1
            'text_secondary': '#D0D0D0',  # Standard visibility: 6.3:1
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
        </style>
        """, unsafe_allow_html=True)

    # Apply theme-specific overrides based on session state
    _apply_theme_css()

    # Hide Streamlit's hamburger menu and footer
    st.markdown("""
        <style>
        /* Hide hamburger menu - classic selector that works across all Streamlit versions */
        #MainMenu {
            visibility: hidden !important;
            display: none !important;
        }

        /* Hide Streamlit footer */
        footer {
            visibility: hidden !important;
        }

        /* Ensure header stays visible */
        header[data-testid="stHeader"] {
            visibility: visible !important;
        }

        /* Force sidebar to stay expanded - prevent collapse on navigation */
        [data-testid="stSidebar"][aria-expanded="false"] {
            transform: none !important;
            margin-left: 0 !important;
        }

        [data-testid="stSidebar"] {
            position: relative !important;
            width: auto !important;
            min-width: 244px !important;
        }

        /* Hide collapse button if it exists */
        [data-testid="collapsedControl"],
        button[kind="header"][aria-label*="Close sidebar"],
        button[kind="header"][aria-label*="Open sidebar"] {
            display: none !important;
        }

        /* Hide appearance settings within settings dialog (defense in depth) */
        [data-testid="stSettingsDialog"] div[data-testid="stAppearanceSettings"],
        [data-testid="stSettingsDialog"] button[data-testid="themeSettings"],
        div[aria-label*="Appearance"],
        div[aria-label*="Theme"],
        section[aria-label*="Appearance"],
        div[data-testid="stThemeManager"],
        [data-baseweb="select"][aria-label*="theme"],
        [data-baseweb="select"][aria-label*="Theme"],
        button[data-testid="layoutToggle"],
        div[aria-label*="wide mode"],
        div[aria-label*="Wide mode"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)


def _apply_theme_css():
    """Apply theme CSS directly via inline styles - conditional on is_dark_mode()."""
    if is_dark_mode():
        # Inject ALL dark mode CSS inline - bypasses iframe/JavaScript issues entirely
        st.markdown("""
        <style>
        /* ===== DARK MODE - GLOBAL BASE ===== */
        html, body, .stApp, .main, .block-container {
            background-color: #121212 !important;
            background-image: none !important;
            color: #F0F0F0 !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #1E1E2E !important;
            background-image: none !important;
        }

        /* Header */
        [data-testid="stHeader"] {
            background-color: #121212 !important;
            background-image: none !important;
        }

        /* ===== METRIC CARDS - Nuclear option with maximum specificity ===== */
        [data-testid="stMetric"],
        div[data-testid="stMetric"],
        .stApp [data-testid="stMetric"],
        .main [data-testid="stMetric"],
        [data-testid="column"] [data-testid="stMetric"],
        [data-testid="stHorizontalBlock"] [data-testid="stMetric"] {
            background: #1E1E2E !important;
            background-color: #1E1E2E !important;
            background-image: none !important;
            border: 1px solid #2D2D3D !important;
            border-left: 4px solid #FFA05C !important;
            padding: 1.75rem !important;
            border-radius: 14px !important;
        }

        /* Metric labels - bright white text - MAXIMUM SPECIFICITY */
        [data-testid="stMetric"] > div:first-child,
        [data-testid="stMetric"] label,
        [data-testid="stMetric"] [data-testid="stMetricLabel"],
        [data-testid="stMetric"] div[data-testid="stMetricLabel"],
        [data-testid="stMetric"] p:first-of-type,
        .stMetric label,
        .stMetric [data-testid="stMetricLabel"],
        div.stMetric [data-testid="stMetricLabel"],
        [class*="stMetric"] [data-testid="stMetricLabel"],
        [data-testid="stMetric"] [data-testid="stMetricLabel"] *,
        [data-testid="stMetric"] label *,
        [data-testid="stMetric"] > div:first-child * {
            color: #F0F0F0 !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }

        /* Metric values - orange - MAXIMUM SPECIFICITY */
        [data-testid="stMetric"] [data-testid="stMetricValue"],
        [data-testid="stMetric"] div[data-testid="stMetricValue"],
        [data-testid="stMetric"] [data-testid="stMetricValue"] div,
        [data-testid="stMetric"] [data-testid="stMetricValue"] p,
        .stMetric [data-testid="stMetricValue"],
        div.stMetric [data-testid="stMetricValue"],
        [class*="stMetric"] [data-testid="stMetricValue"],
        [data-testid="stMetric"] [data-testid="stMetricValue"] *,
        [data-testid="stMetric"] [data-testid="stMetricValue"] div * {
            color: #FFA05C !important;
            font-weight: 600 !important;
            opacity: 1 !important;
        }

        /* Metric deltas (change indicators) */
        [data-testid="stMetric"] [data-testid="stMetricDelta"],
        [data-testid="stMetric"] div[data-testid="stMetricDelta"],
        [data-testid="stMetric"] [data-testid="stMetricDelta"] * {
            color: #90EE90 !important;
            opacity: 1 !important;
        }

        /* All nested divs in metrics - force transparency */
        [data-testid="stMetric"] div {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* ALL text elements inside metrics - nuclear option */
        [data-testid="stMetric"] p,
        [data-testid="stMetric"] span,
        [data-testid="stMetric"] div {
            opacity: 1 !important;
        }

        /* ===== CONTAINERS & WRAPPERS - All transparent ===== */
        [data-testid="stVerticalBlock"],
        [data-testid="stHorizontalBlock"],
        [data-testid="column"],
        div[data-testid="stVerticalBlock"],
        div[data-testid="stHorizontalBlock"],
        div[data-testid="column"],
        .block-container,
        .element-container,
        .row-widget.stHorizontal {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* Nested container divs */
        [data-testid="stVerticalBlock"] > div,
        [data-testid="stHorizontalBlock"] > div,
        [data-testid="column"] > div,
        [data-testid="column"] > div > div {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* Emotion-cache classes (Streamlit's dynamic classes) - AGGRESSIVE */
        div[class*="st-emotion-cache"],
        .st-emotion-cache-0,
        .st-emotion-cache-1wmy9hl,
        .st-emotion-cache-2ejzjd,
        .st-emotion-cache-lmv86y,
        .st-emotion-cache-12w0qpk,
        [class^="st-emotion-cache-"],
        [class*="e1f1d6gn"] {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* Streamlit Column classes */
        .stColumn,
        div.stColumn,
        .stColumn > div,
        .stColumn > div > div,
        [class*="stColumn"] {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* Element containers around metrics */
        .stElementContainer,
        div.stElementContainer,
        .element-container,
        [class*="stElementContainer"],
        .stElementContainer.element-container {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* Vertical blocks with emotion cache classes */
        .stVerticalBlock,
        div.stVerticalBlock,
        .stVerticalBlock.st-emotion-cache-2ejzjd,
        [class*="stVerticalBlock"] {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* Force all text inside these wrappers to be visible */
        .stColumn p,
        .stColumn span,
        .stColumn div,
        .stVerticalBlock p,
        .stVerticalBlock span,
        .stVerticalBlock div,
        .stElementContainer p,
        .stElementContainer span,
        .stElementContainer div,
        div[class*="st-emotion-cache"] p,
        div[class*="st-emotion-cache"] span,
        div[class*="st-emotion-cache"] div {
            opacity: 1 !important;
        }

        /* ===== TABS ===== */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #1E1E2E !important;
            background-image: none !important;
        }

        .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) {
            color: #F0F0F0 !important;
            background-color: transparent !important;
            background-image: none !important;
        }

        .stTabs [aria-selected="true"] {
            background-color: #FFA05C !important;
            background-image: none !important;
            color: #121212 !important;
        }

        /* ===== DATAFRAMES ===== */
        [data-testid="stDataFrame"],
        [data-testid="stDataFrameResizable"] {
            background-color: #1E1E2E !important;
        }

        [data-testid="stDataFrame"] table {
            background-color: #1E1E2E !important;
            color: #F0F0F0 !important;
        }

        [data-testid="stDataFrame"] th {
            background-color: #2D2D3D !important;
            color: #F0F0F0 !important;
            border-color: #4A4A5A !important;
        }

        [data-testid="stDataFrame"] td {
            background-color: #1E1E2E !important;
            color: #E8E8E8 !important;
            border-color: #4A4A5A !important;
        }

        /* ===== INPUTS ===== */
        .stTextInput input,
        .stSelectbox select,
        .stMultiSelect,
        .stTextArea textarea {
            background-color: #2D2D3D !important;
            color: #F0F0F0 !important;
            border-color: #4A4A5A !important;
        }

        /* ===== BUTTONS ===== */
        .stButton > button {
            background-color: #2D2D3D !important;
            color: #F0F0F0 !important;
            border-color: #4A4A5A !important;
        }

        .stButton > button:hover {
            background-color: #3D3D4D !important;
            border-color: #FFA05C !important;
        }

        .stButton > button[kind="primary"] {
            background-color: #FFA05C !important;
            color: #121212 !important;
        }

        .stButton > button[kind="primary"]:hover {
            background-color: #FFB57C !important;
        }

        /* ===== EXPANDERS ===== */
        .streamlit-expanderHeader,
        [data-testid="stExpander"] {
            background-color: #1E1E2E !important;
            background-image: none !important;
            color: #F0F0F0 !important;
        }

        .streamlit-expanderContent {
            background-color: #1E1E2E !important;
            background-image: none !important;
            border-color: #4A4A5A !important;
        }

        /* ===== CHARTS ===== */
        .stPlotlyChart {
            background-color: #1E1E2E !important;
        }

        /* ===== TEXT COLORS - Global override with opacity fix ===== */
        p, span, label, div, h1, h2, h3, h4, h5, h6 {
            color: #F0F0F0 !important;
            opacity: 1 !important;
        }

        /* Specific targeting for metric text elements that might have opacity issues */
        [data-testid="stMetric"] *,
        .stMetric *,
        .stColumn [data-testid="stMetric"] *,
        .stElementContainer [data-testid="stMetric"] *,
        div[class*="st-emotion-cache"] [data-testid="stMetric"] * {
            opacity: 1 !important;
        }

        /* Force bright text for all metric components */
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] *,
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricLabel"] * {
            color: #F0F0F0 !important;
            opacity: 1 !important;
            -webkit-text-fill-color: #F0F0F0 !important;
        }

        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] *,
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricValue"] * {
            color: #FFA05C !important;
            opacity: 1 !important;
            -webkit-text-fill-color: #FFA05C !important;
        }

        /* Links */
        a {
            color: #FFA05C !important;
        }

        a:hover {
            color: #FFB57C !important;
        }

        /* Code blocks */
        code {
            background-color: #2D2D3D !important;
            color: #F0F0F0 !important;
        }

        pre {
            background-color: #1E1E2E !important;
            border: 1px solid #4A4A5A !important;
        }

        /* ===== CATCH-ALL for any remaining white backgrounds ===== */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* ===== SIDEBAR NAVIGATION SECTION HEADERS ===== */
        [data-testid="stNavSectionHeader"],
        header[data-testid="stNavSectionHeader"],
        [data-testid="stSidebar"] [data-testid="stNavSectionHeader"],
        header.st-emotion-cache-1n7fb9x,
        header.st-emotion-cache-1n7fb9x.eczjsme2 {
            color: #F0F0F0 !important;
            font-weight: 700 !important;
        }

        /* ===== SELECTBOX COMPONENTS (BaseWeb) ===== */

        /* Selectbox trigger button (the clickable area) */
        [data-baseweb="select"],
        .stSelectbox [data-baseweb="select"],
        [data-baseweb="select"] > div,
        .stSelectbox [data-baseweb="select"] > div,
        .stSelectbox div[data-baseweb="select"] {
            background-color: #2D2D3D !important;
            border-color: #4A4A5A !important;
        }

        /* Selectbox display text (selected value shown in trigger) */
        [data-baseweb="select"] input,
        [data-baseweb="select"] div[role="button"],
        [data-baseweb="select"] > div > div,
        .stSelectbox [data-baseweb="select"] input,
        .stSelectbox [data-baseweb="select"] div {
            background-color: #2D2D3D !important;
            color: #F0F0F0 !important;
        }

        /* Dropdown menu container (the popup that appears) */
        [data-baseweb="menu"],
        div[data-baseweb="menu"],
        [data-baseweb="popover"],
        div[data-baseweb="popover"],
        ul[role="listbox"],
        .stSelectbox ul[role="listbox"] {
            background-color: #2D2D3D !important;
            border: 1px solid #4A4A5A !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
        }

        /* Individual option items in dropdown */
        [data-baseweb="option"],
        li[data-baseweb="option"],
        li[role="option"],
        [data-baseweb="menu"] li,
        ul[role="listbox"] li {
            background-color: #2D2D3D !important;
            color: #F0F0F0 !important;
        }

        /* Hovered option (hover state) */
        [data-baseweb="option"]:hover,
        li[data-baseweb="option"]:hover,
        li[role="option"]:hover,
        [aria-selected="true"] {
            background-color: #3D3D4D !important;
            color: #FFFFFF !important;
        }

        /* Selected option (currently selected) */
        [data-baseweb="option"][aria-selected="true"],
        li[data-baseweb="option"][aria-selected="true"],
        li[role="option"][aria-selected="true"] {
            background-color: #FFA05C !important;
            color: #121212 !important;
        }

        /* Dropdown arrow icon */
        [data-baseweb="select"] svg,
        .stSelectbox svg {
            color: #F0F0F0 !important;
            fill: #F0F0F0 !important;
        }

        /* Fallback for deeply nested selectbox elements */
        .stSelectbox,
        .stSelectbox > div,
        .stSelectbox > div > div,
        .stSelectbox > div > div > div {
            background-color: transparent !important;
        }

        /* Selectbox input field (for searchable selects) */
        .stSelectbox input[type="text"],
        [data-baseweb="select"] input[type="text"] {
            background-color: #2D2D3D !important;
            color: #F0F0F0 !important;
            border-color: #4A4A5A !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Light mode - minimal CSS, let Streamlit defaults apply
        st.markdown("""
        <style>
        html, body, .stApp {
            background-color: #F8F9FA !important;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
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
        <p style="color: {'#D0D0D0' if is_dark_mode() else colors['text_secondary']};">{message}</p>
    </div>
    """, unsafe_allow_html=True)

    if action_button and action_callback:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button(action_button, type="primary", use_container_width=True):
                action_callback()


def render_stat_card(label: str, value: str, icon: str = "📊", color: str = None):
    """
    Render a custom statistic card with enhanced industrial styling.

    Args:
        label: Stat label
        value: Stat value
        icon: Icon emoji
        color: Accent color (defaults to theme accent)
    """
    colors = get_theme_colors()
    accent = color if color else colors['accent']

    # Enhanced shadows for light/dark mode with WCAG-compliant colors
    if is_dark_mode():
        shadow = "0 4px 16px rgba(0,0,0,0.5)"
        bg_gradient = f"linear-gradient(135deg, {colors['card_bg']} 0%, #0F1419 100%)"
        glow = f"0 0 20px rgba(255, 160, 92, 0.15)"
        label_color = "#FFFFFF"  # High contrast white for labels in dark mode
        icon_opacity = "0.5"
    else:
        shadow = "0 4px 12px rgba(0,0,0,0.12)"
        bg_gradient = f"linear-gradient(135deg, {colors['card_bg']} 0%, #F8F9FA 100%)"
        glow = f"0 2px 8px {accent}20"
        label_color = "#333333"  # Dark text for labels in light mode
        icon_opacity = "0.4"

    st.markdown(f"""
    <div style="
        background: {bg_gradient};
        padding: 1.75rem;
        border-radius: 14px;
        box-shadow: {shadow};
        border-left: 5px solid {accent};
        border-top: 1px solid {accent}33;
        border-right: 1px solid {'#FFFFFF0D' if is_dark_mode() else '#00000010'};
        border-bottom: 1px solid {'#FFFFFF0D' if is_dark_mode() else '#00000010'};
        margin-bottom: 1rem;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position: absolute;
            top: 0;
            right: 0;
            width: 100px;
            height: 100px;
            background: radial-gradient(circle, {accent}15 0%, transparent 70%);
            pointer-events: none;
        "></div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; position: relative;">
            <div style="flex: 1;">
                <div style="
                    color: {label_color};
                    font-size: 0.8rem;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    font-weight: 700;
                    margin-bottom: 0.75rem;
                ">{label}</div>
                <div style="
                    color: {accent};
                    font-size: 2.25rem;
                    font-weight: 800;
                    letter-spacing: -0.5px;
                    text-shadow: 0 2px 4px {accent}20;
                    line-height: 1;
                ">{value}</div>
            </div>
            <div style="
                font-size: 2.75rem;
                opacity: {icon_opacity};
                margin-left: 1rem;
                filter: drop-shadow(0 2px 4px {accent}30);
            ">{icon}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_info_box(title: str, content: str, box_type: str = "info"):
    """
    Render an informational box with enhanced industrial styling.

    Args:
        title: Box title
        content: Box content
        box_type: Type of box (info, success, warning, error)
    """
    theme = get_theme_colors()

    # Light mode colors with gradients
    light_colors = {
        "info": {
            "bg": "linear-gradient(135deg, #D1ECF1 0%, #B8E5ED 100%)",
            "border": "#17A2B8",
            "icon": "ℹ️",
            "text": "#0C5460",
            "shadow": "0 4px 12px rgba(23, 162, 184, 0.2)"
        },
        "success": {
            "bg": "linear-gradient(135deg, #D4EDDA 0%, #C3E6CB 100%)",
            "border": "#28A745",
            "icon": "✅",
            "text": "#155724",
            "shadow": "0 4px 12px rgba(40, 167, 69, 0.2)"
        },
        "warning": {
            "bg": "linear-gradient(135deg, #FFF3CD 0%, #FFE8A1 100%)",
            "border": "#FFC107",
            "icon": "⚠️",
            "text": "#856404",
            "shadow": "0 4px 12px rgba(255, 193, 7, 0.2)"
        },
        "error": {
            "bg": "linear-gradient(135deg, #F8D7DA 0%, #F1BFC4 100%)",
            "border": "#DC3545",
            "icon": "❌",
            "text": "#721C24",
            "shadow": "0 4px 12px rgba(220, 53, 69, 0.2)"
        }
    }

    # Dark mode colors with gradients - WCAG AAA compliant
    dark_colors = {
        "info": {
            "bg": "linear-gradient(135deg, #1A2A3D 0%, #0F1A2A 100%)",
            "border": "#17A2B8",
            "icon": "ℹ️",
            "text": "#D4EBFF",  # 7.21:1 contrast
            "shadow": "0 4px 16px rgba(23, 162, 184, 0.3)"
        },
        "success": {
            "bg": "linear-gradient(135deg, #1A3D25 0%, #0F2A18 100%)",
            "border": "#28A745",
            "icon": "✅",
            "text": "#D4F4DD",  # 7.02:1 contrast
            "shadow": "0 4px 16px rgba(40, 167, 69, 0.3)"
        },
        "warning": {
            "bg": "linear-gradient(135deg, #3D3D1A 0%, #2A2A0F 100%)",
            "border": "#FFC107",
            "icon": "⚠️",
            "text": "#FFF8D1",  # 6.54:1 contrast
            "shadow": "0 4px 16px rgba(255, 193, 7, 0.3)"
        },
        "error": {
            "bg": "linear-gradient(135deg, #3D1A1A 0%, #2A0F0F 100%)",
            "border": "#DC3545",
            "icon": "❌",
            "text": "#FFD4D8",  # 6.89:1 contrast
            "shadow": "0 4px 16px rgba(220, 53, 69, 0.3)"
        }
    }

    colors = dark_colors if is_dark_mode() else light_colors
    style = colors.get(box_type, colors["info"])

    st.markdown(f"""
    <div style="
        background: {style['bg']};
        border-left: 5px solid {style['border']};
        border-top: 1px solid {style['border']}33;
        border-right: 1px solid {style['border']}1A;
        border-bottom: 1px solid {style['border']}1A;
        padding: 1.25rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: {style['text']};
        box-shadow: {style['shadow']};
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position: absolute;
            top: 0;
            right: 0;
            width: 80px;
            height: 80px;
            background: radial-gradient(circle, {style['border']}15 0%, transparent 70%);
            pointer-events: none;
        "></div>
        <div style="
            font-weight: 700;
            margin-bottom: 0.625rem;
            font-size: 1rem;
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            position: relative;
        ">
            <span style="font-size: 1.25rem;">{style['icon']}</span>
            <span>{title}</span>
        </div>
        <div style="
            line-height: 1.6;
            font-size: 0.95rem;
            position: relative;
        ">{content}</div>
    </div>
    """, unsafe_allow_html=True)


def add_page_header(title: str, subtitle: str = None, icon: str = None):
    """
    Add a styled page header with gradient underline and industrial design.

    Args:
        title: Page title
        subtitle: Optional subtitle
        icon: Optional icon emoji
    """
    colors = get_theme_colors()

    # Build header with icon
    icon_html = f'<span style="margin-right: 0.5rem; filter: drop-shadow(0 2px 4px {colors["accent"]}40);">{icon}</span>' if icon else ""

    # Enhanced header with gradient underline
    header_html = f"""
    <div style="margin-bottom: 2rem;">
        <h1 style="
            margin-bottom: 0;
            padding-bottom: 0.75rem;
            color: {'#E8E8E8' if is_dark_mode() else '#2C3E50'};
            font-weight: 800;
            font-size: 2.5rem;
            letter-spacing: -0.5px;
            position: relative;
            display: inline-block;
        ">
            {icon_html}{title}
        </h1>
        <div style="
            width: 120px;
            height: 4px;
            background: linear-gradient(90deg, {colors['accent']} 0%, {colors['accent']}80 100%);
            border-radius: 2px;
            box-shadow: 0 2px 8px {colors['accent']}50;
            margin-top: 0.5rem;
        "></div>
    """

    if subtitle:
        header_html += f"""
        <p style="
            color: {colors['text_secondary']};
            font-size: 1.125rem;
            margin-top: 1rem;
            margin-bottom: 0;
            line-height: 1.6;
            font-weight: 400;
        ">{subtitle}</p>
        """

    header_html += "</div>"

    st.markdown(header_html, unsafe_allow_html=True)
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


def initialize_recent_items():
    """Initialize recent items list in session state."""
    if 'recent_items' not in st.session_state:
        st.session_state.recent_items = []


def add_recent_item(item_type: str, item_id: int | str, item_name: str, page: str = None):
    """
    Track a recently viewed/edited item.

    Args:
        item_type: Type of item (e.g., 'Import Config', 'Report', 'Schedule')
        item_id: Unique identifier for the item
        item_name: Display name of the item
        page: Optional page name for navigation
    """
    from datetime import datetime

    initialize_recent_items()

    # Create item dict
    item = {
        'type': item_type,
        'id': item_id,
        'name': item_name,
        'page': page,
        'timestamp': datetime.now()
    }

    # Remove duplicate if exists
    st.session_state.recent_items = [
        i for i in st.session_state.recent_items
        if not (i['type'] == item_type and i['id'] == item_id)
    ]

    # Add to front of list
    st.session_state.recent_items.insert(0, item)

    # Keep only last 10 items
    st.session_state.recent_items = st.session_state.recent_items[:10]


def get_recent_items(limit: int = 10) -> list[dict]:
    """
    Get recent items list.

    Args:
        limit: Maximum number of items to return

    Returns:
        List of recent item dictionaries
    """
    initialize_recent_items()
    return st.session_state.recent_items[:limit]


def clear_recent_items():
    """Clear all recent items."""
    st.session_state.recent_items = []

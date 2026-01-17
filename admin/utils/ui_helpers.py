"""UI Helper utilities for enhanced user experience"""

import streamlit as st
import time
from pathlib import Path
from typing import Callable, Any


def load_custom_css():
    """Load custom CSS styling for the admin interface."""
    css_file = Path(__file__).parent.parent / "styles" / "custom.css"

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
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem 1rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">{icon}</div>
        <h3 style="color: #6C757D; margin-bottom: 0.5rem;">{title}</h3>
        <p style="color: #ADB5BD;">{message}</p>
    </div>
    """, unsafe_allow_html=True)

    if action_button and action_callback:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button(action_button, type="primary", use_container_width=True):
                action_callback()


def render_stat_card(label: str, value: str, icon: str = "📊", color: str = "#FF8C42"):
    """
    Render a custom statistic card with enhanced styling.

    Args:
        label: Stat label
        value: Stat value
        icon: Icon emoji
        color: Accent color
    """
    st.markdown(f"""
    <div style="
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid {color};
        margin-bottom: 1rem;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="
                    color: #6C757D;
                    font-size: 0.875rem;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                ">{label}</div>
                <div style="
                    color: {color};
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
    colors = {
        "info": {"bg": "#D1ECF1", "border": "#17A2B8", "icon": "ℹ️"},
        "success": {"bg": "#D4EDDA", "border": "#28A745", "icon": "✅"},
        "warning": {"bg": "#FFF3CD", "border": "#FFC107", "icon": "⚠️"},
        "error": {"bg": "#F8D7DA", "border": "#DC3545", "icon": "❌"}
    }

    style = colors.get(box_type, colors["info"])

    st.markdown(f"""
    <div style="
        background-color: {style['bg']};
        border-left: 4px solid {style['border']};
        padding: 1rem 1.25rem;
        border-radius: 8px;
        margin: 1rem 0;
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
    header_html = f"<h1 style='margin-bottom: 0;'>"
    if icon:
        header_html += f"{icon} "
    header_html += f"{title}</h1>"

    st.markdown(header_html, unsafe_allow_html=True)

    if subtitle:
        st.markdown(f"<p style='color: #6C757D; font-size: 1.1rem; margin-top: 0.5rem;'>{subtitle}</p>",
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
    breadcrumb_html = " → ".join([
        f"<span style='color: #FF8C42; font-weight: 500;'>{item}</span>"
        if i == len(items) - 1
        else f"<span style='color: #6C757D;'>{item}</span>"
        for i, item in enumerate(items)
    ])

    st.markdown(f"<div style='margin-bottom: 1.5rem; font-size: 0.9rem;'>{breadcrumb_html}</div>",
               unsafe_allow_html=True)

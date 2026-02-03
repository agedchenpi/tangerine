"""
UI test helper functions for Streamlit AppTest.

Common utilities for interacting with Streamlit UI components in tests.
"""
from typing import List, Any


def navigate_to_tab(at, tab_index: int):
    """
    Navigate to a specific tab by index.

    Args:
        at: AppTest instance
        tab_index: Zero-based index of tab to select
    """
    at.tabs[tab_index].select()
    at.run()


def fill_text_input(at, key: str, value: str):
    """
    Fill a text input field.

    Args:
        at: AppTest instance
        key: Widget key
        value: Value to set
    """
    at.text_input(key=key).set_value(value).run()


def fill_text_area(at, key: str, value: str):
    """
    Fill a text area field.

    Args:
        at: AppTest instance
        key: Widget key
        value: Value to set
    """
    at.text_area(key=key).set_value(value).run()


def select_option(at, key: str, value: str):
    """
    Select an option from a selectbox by value.

    Args:
        at: AppTest instance
        key: Widget key
        value: Value to select
    """
    at.selectbox(key=key).select(value).run()


def select_option_by_index(at, key: str, index: int):
    """
    Select an option from a selectbox by index.

    Args:
        at: AppTest instance
        key: Widget key
        index: Zero-based index to select
    """
    at.selectbox(key=key).select_index(index).run()


def click_button(at, key: str):
    """
    Click a button.

    Args:
        at: AppTest instance
        key: Widget key
    """
    at.button(key=key).click().run()


def click_form_submit(at, form_key: str = None):
    """
    Submit a form. If form_key is provided, submits that specific form.
    Otherwise submits the first form submit button found.

    Args:
        at: AppTest instance
        form_key: Optional form submit button key
    """
    if form_key:
        at.form_submit_button(key=form_key).click()
    else:
        # Submit first form submit button
        at.form_submit_button[0].click()
    at.run()


def check_checkbox(at, key: str, checked: bool = True):
    """
    Check or uncheck a checkbox.

    Args:
        at: AppTest instance
        key: Widget key
        checked: True to check, False to uncheck
    """
    at.checkbox(key=key).set_value(checked).run()


def verify_success_message(at, expected_text: str) -> bool:
    """
    Verify that a success message appears containing expected text.

    Args:
        at: AppTest instance
        expected_text: Text expected in success message

    Returns:
        True if message found, False otherwise
    """
    success_messages = [msg.value for msg in at.success]
    return any(expected_text.lower() in msg.lower() for msg in success_messages)


def verify_error_message(at, expected_text: str) -> bool:
    """
    Verify that an error message appears containing expected text.

    Args:
        at: AppTest instance
        expected_text: Text expected in error message

    Returns:
        True if message found, False otherwise
    """
    error_messages = [msg.value for msg in at.error]
    return any(expected_text.lower() in msg.lower() for msg in error_messages)


def get_success_messages(at) -> List[str]:
    """
    Get all success messages from the page.

    Args:
        at: AppTest instance

    Returns:
        List of success message strings
    """
    return [msg.value for msg in at.success]


def get_error_messages(at) -> List[str]:
    """
    Get all error messages from the page.

    Args:
        at: AppTest instance

    Returns:
        List of error message strings
    """
    return [msg.value for msg in at.error]


def get_warning_messages(at) -> List[str]:
    """
    Get all warning messages from the page.

    Args:
        at: AppTest instance

    Returns:
        List of warning message strings
    """
    return [msg.value for msg in at.warning]

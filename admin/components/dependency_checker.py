"""Dependency checker components for UX improvements.

Provides reusable UI components for:
- Checking if dependencies are satisfied before creating entities
- Showing usage counts for reference data
- Rendering navigation links to create missing dependencies
"""

import streamlit as st
from typing import Optional


# Page path mapping for navigation
PAGE_PATHS = {
    'datasource': '2_Reference_Data',
    'datasettype': '2_Reference_Data',
    'import_config': '1_Import_Configs',
    'inbox_config': '5_Inbox_Configs',
    'report_config': '6_Report_Manager',
    'reference_data': '2_Reference_Data',
}


def render_dependency_status(dependencies: list[dict]) -> bool:
    """
    Render dependency status indicators.

    Args:
        dependencies: List of dicts with keys:
            - name: Display name (e.g., "Data Sources")
            - satisfied: Boolean indicating if dependency is met
            - count: Number of available items (optional)
            - entity_type: Type for navigation link (e.g., 'datasource')

    Returns:
        True if all dependencies are satisfied, False otherwise
    """
    all_satisfied = all(d['satisfied'] for d in dependencies)

    if all_satisfied:
        st.success("All dependencies satisfied")
    else:
        st.warning("Some dependencies are missing")

    for dep in dependencies:
        col1, col2 = st.columns([3, 1])
        with col1:
            if dep['satisfied']:
                count_str = f" ({dep.get('count', 0)} available)" if 'count' in dep else ""
                st.markdown(f"**{dep['name']}:** {count_str}")
            else:
                st.markdown(f"**{dep['name']}:** None found")

        with col2:
            if dep['satisfied']:
                st.markdown(":white_check_mark:")
            else:
                entity_type = dep.get('entity_type')
                if entity_type:
                    render_create_link(dep['name'], entity_type)
                else:
                    st.markdown(":x:")

    return all_satisfied


def render_create_link(entity_name: str, entity_type: str, inline: bool = True) -> None:
    """
    Render a navigation link to create a missing entity.

    Args:
        entity_name: Display name for the entity
        entity_type: Type key for page lookup
        inline: If True, render inline text link; if False, render button
    """
    page_path = PAGE_PATHS.get(entity_type)
    if not page_path:
        return

    if inline:
        st.markdown(f"[Create {entity_name} :arrow_right:](/{page_path})")
    else:
        st.page_link(f"pages/{page_path}.py", label=f"Create {entity_name}", icon=":material/add:")


def render_missing_config_link(job_type: str, context: str = "form") -> None:
    """
    Render a link to create a config based on job type.

    Args:
        job_type: The job type (import, inbox_processor, report)
        context: Where this is being rendered (form, info, inline)
    """
    config_map = {
        'import': ('Import Config', 'import_config', '1_Import_Configs'),
        'inbox_processor': ('Inbox Rule', 'inbox_config', '5_Inbox_Configs'),
        'report': ('Report', 'report_config', '6_Report_Manager'),
    }

    if job_type not in config_map:
        return

    name, entity_type, page = config_map[job_type]

    if context == "info":
        st.info(f"No {name.lower()}s available. [Create one :arrow_right:](/{page})")
    elif context == "inline":
        st.markdown(f"No {name.lower()}s? [Create one :arrow_right:](/{page})")
    else:
        st.page_link(f"pages/{page}.py", label=f"Create {name}", icon=":material/add:")


def render_usage_badge(usage_count: int, entity_name: str = "config") -> None:
    """
    Render a usage count badge.

    Args:
        usage_count: Number of entities using this item
        entity_name: Name of the entity type for pluralization
    """
    if usage_count == 0:
        st.caption("Not used")
    elif usage_count == 1:
        st.caption(f"Used by 1 {entity_name}")
    else:
        st.caption(f"Used by {usage_count} {entity_name}s")


def get_usage_warning_message(
    entity_type: str,
    entity_name: str,
    referencing_configs: list[str]
) -> str:
    """
    Generate a warning message for delete protection.

    Args:
        entity_type: Type of entity (datasource, datasettype)
        entity_name: Name of the entity being deleted
        referencing_configs: List of config names that reference this entity

    Returns:
        Formatted warning message
    """
    count = len(referencing_configs)
    config_list = ", ".join(referencing_configs[:5])
    if count > 5:
        config_list += f", and {count - 5} more"

    return (
        f"Cannot delete {entity_type} '{entity_name}' because it is used by "
        f"{count} import configuration(s): {config_list}. "
        "Please update or delete those configurations first."
    )

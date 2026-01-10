"""Inbox Configuration Management Page"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

from components.notifications import show_success, show_error, show_warning, show_info
from components.validators import (
    validate_required, validate_config_name, validate_directory_path,
    validate_glob_pattern, validate_max_length
)
from services.inbox_config_service import (
    list_inbox_configs, get_inbox_config, create_inbox_config,
    update_inbox_config, delete_inbox_config, toggle_active,
    get_inbox_stats, config_name_exists, get_import_configs
)
from utils.db_helpers import format_sql_error
from utils.ui_helpers import load_custom_css, add_page_header

# Page config
st.set_page_config(
    page_title="Inbox Configs - Tangerine Admin",
    page_icon="📧",
    layout="wide"
)

load_custom_css()
add_page_header("Inbox Configuration", "Manage Gmail inbox processing rules", "📧")

# Statistics
try:
    stats = get_inbox_stats()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Configurations", stats['total'])
    with col2:
        st.metric("Active", stats['active'])
    with col3:
        st.metric("Inactive", stats['inactive'])
except Exception as e:
    show_error(f"Failed to load statistics: {format_sql_error(e)}")

st.divider()


def render_inbox_config_form(
    config_data: Optional[Dict[str, Any]] = None,
    is_edit: bool = False
) -> Optional[Dict[str, Any]]:
    """Render inbox configuration form."""
    form_key = "inbox_config_form_edit" if is_edit else "inbox_config_form_create"

    with st.form(key=form_key):
        st.markdown("### Basic Information")
        col1, col2 = st.columns(2)

        with col1:
            config_name = st.text_input(
                "Configuration Name *",
                value=config_data.get('config_name', '') if config_data else '',
                help="Unique name for this inbox rule"
            )
            subject_pattern = st.text_input(
                "Subject Pattern (Regex)",
                value=config_data.get('subject_pattern', '') if config_data else '',
                help="Regex to match email subjects (e.g., 'Daily Report.*')"
            )
            attachment_pattern = st.text_input(
                "Attachment Pattern *",
                value=config_data.get('attachment_pattern', '*.csv') if config_data else '*.csv',
                help="Glob pattern for attachments (e.g., *.csv, report_*.xlsx)"
            )

        with col2:
            description = st.text_area(
                "Description",
                value=config_data.get('description', '') if config_data else '',
                height=68,
                help="Optional description of this inbox rule"
            )
            sender_pattern = st.text_input(
                "Sender Pattern (Regex)",
                value=config_data.get('sender_pattern', '') if config_data else '',
                help="Regex to match sender emails"
            )

        st.markdown("### File Settings")
        col1, col2 = st.columns(2)

        with col1:
            target_directory = st.text_input(
                "Target Directory *",
                value=config_data.get('target_directory', '/app/data/source/inbox') if config_data else '/app/data/source/inbox',
                help="Directory where attachments are saved"
            )

        with col2:
            date_prefix_format = st.text_input(
                "Date Prefix Format",
                value=config_data.get('date_prefix_format', 'yyyyMMdd') if config_data else 'yyyyMMdd',
                help="Date format for filename prefix (Java-style)"
            )

        st.markdown("### Gmail Labels")
        col1, col2 = st.columns(2)

        with col1:
            processed_label = st.text_input(
                "Processed Label",
                value=config_data.get('processed_label', 'Processed') if config_data else 'Processed',
                help="Gmail label for processed emails"
            )

        with col2:
            error_label = st.text_input(
                "Error Label",
                value=config_data.get('error_label', 'ErrorFolder') if config_data else 'ErrorFolder',
                help="Gmail label for unmatched emails"
            )

        st.markdown("### Options")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            save_eml = st.checkbox(
                "Save .eml file",
                value=config_data.get('save_eml', False) if config_data else False,
                help="Also save the original email file"
            )
        with col2:
            mark_processed = st.checkbox(
                "Mark as Processed",
                value=config_data.get('mark_processed', True) if config_data else True,
                help="Apply Gmail label after processing"
            )
        with col3:
            is_active = st.checkbox(
                "Active",
                value=config_data.get('is_active', True) if config_data else True
            )

        st.markdown("### Linked Import Configuration")
        import_configs = get_import_configs()
        import_options = [{'config_id': None, 'config_name': '-- None --'}] + import_configs
        current_linked = config_data.get('linked_import_config_id') if config_data else None

        linked_import_config_id = st.selectbox(
            "Auto-run Import Config",
            options=[c['config_id'] for c in import_options],
            format_func=lambda x: next((c['config_name'] for c in import_options if c['config_id'] == x), '-- None --'),
            index=next((i for i, c in enumerate(import_options) if c['config_id'] == current_linked), 0),
            help="Optionally run an import job after downloading attachments"
        )

        submitted = st.form_submit_button(
            "💾 " + ("Update Configuration" if is_edit else "Create Configuration"),
            use_container_width=True
        )

        if submitted:
            errors = []

            # Validation
            is_valid, error = validate_required(config_name, "Configuration Name")
            if not is_valid:
                errors.append(error)
            else:
                is_valid, error = validate_config_name(config_name)
                if not is_valid:
                    errors.append(error)

            is_valid, error = validate_required(attachment_pattern, "Attachment Pattern")
            if not is_valid:
                errors.append(error)
            else:
                is_valid, error = validate_glob_pattern(attachment_pattern, "Attachment Pattern")
                if not is_valid:
                    errors.append(error)

            is_valid, error = validate_directory_path(target_directory)
            if not is_valid:
                errors.append(f"Target Directory: {error}")

            if errors:
                for error in errors:
                    show_error(error)
                return None

            return {
                'config_name': config_name,
                'description': description or None,
                'subject_pattern': subject_pattern or None,
                'sender_pattern': sender_pattern or None,
                'attachment_pattern': attachment_pattern,
                'target_directory': target_directory,
                'date_prefix_format': date_prefix_format or 'yyyyMMdd',
                'save_eml': save_eml,
                'mark_processed': mark_processed,
                'processed_label': processed_label or 'Processed',
                'error_label': error_label or 'ErrorFolder',
                'linked_import_config_id': linked_import_config_id,
                'is_active': is_active
            }

    return None


# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 View All",
    "➕ Create New",
    "✏️ Edit",
    "🗑️ Delete"
])

# ============================================================================
# TAB 1: VIEW ALL
# ============================================================================
with tab1:
    st.subheader("All Inbox Configurations")

    col1, col2 = st.columns([3, 1])
    with col2:
        show_active_only = st.checkbox("Active only", value=False, key="view_active_only")

    try:
        configs = list_inbox_configs(active_only=show_active_only)
        if configs:
            df = pd.DataFrame(configs)
            display_cols = [
                'inbox_config_id', 'config_name', 'attachment_pattern',
                'target_directory', 'is_active', 'last_run_at'
            ]
            display_cols = [c for c in display_cols if c in df.columns]
            df_display = df[display_cols].copy()

            # Format columns
            if 'is_active' in df_display.columns:
                df_display['is_active'] = df_display['is_active'].map({True: '✅ Active', False: '❌ Inactive'})
            if 'last_run_at' in df_display.columns:
                df_display['last_run_at'] = pd.to_datetime(df_display['last_run_at']).dt.strftime('%Y-%m-%d %H:%M')

            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            show_info("No inbox configurations found. Create one in the 'Create New' tab.")
    except Exception as e:
        show_error(f"Failed to load configurations: {format_sql_error(e)}")

# ============================================================================
# TAB 2: CREATE NEW
# ============================================================================
with tab2:
    st.subheader("Create New Inbox Configuration")

    form_data = render_inbox_config_form(is_edit=False)
    if form_data:
        try:
            if config_name_exists(form_data['config_name']):
                show_error(f"Configuration name '{form_data['config_name']}' already exists")
            else:
                new_id = create_inbox_config(form_data)
                show_success(f"Inbox configuration created successfully! (ID: {new_id})")
                st.balloons()
        except Exception as e:
            show_error(f"Failed to create configuration: {format_sql_error(e)}")

# ============================================================================
# TAB 3: EDIT
# ============================================================================
with tab3:
    st.subheader("Edit Inbox Configuration")

    if 'inbox_config_update_success' in st.session_state:
        show_success(st.session_state.inbox_config_update_success)
        del st.session_state.inbox_config_update_success

    try:
        configs = list_inbox_configs()
        if configs:
            config_options = {f"{c['inbox_config_id']}: {c['config_name']}": c['inbox_config_id'] for c in configs}
            selected = st.selectbox(
                "Select Configuration",
                options=list(config_options.keys()),
                key="edit_select"
            )
            selected_id = config_options[selected]
            config = get_inbox_config(selected_id)

            if config:
                # Quick actions
                col1, col2 = st.columns([1, 4])
                with col1:
                    current_status = config.get('is_active', True)
                    if current_status:
                        if st.button("🔴 Deactivate", key="deactivate_btn"):
                            toggle_active(selected_id, False)
                            st.session_state.inbox_config_update_success = "Configuration deactivated"
                            st.rerun()
                    else:
                        if st.button("🟢 Activate", key="activate_btn"):
                            toggle_active(selected_id, True)
                            st.session_state.inbox_config_update_success = "Configuration activated"
                            st.rerun()

                st.divider()

                form_data = render_inbox_config_form(config_data=config, is_edit=True)
                if form_data:
                    try:
                        if form_data['config_name'] != config['config_name']:
                            if config_name_exists(form_data['config_name'], exclude_id=selected_id):
                                show_error(f"Configuration name '{form_data['config_name']}' already exists")
                                st.stop()

                        update_inbox_config(selected_id, form_data)
                        st.session_state.inbox_config_update_success = "Configuration updated successfully!"
                        st.rerun()
                    except Exception as e:
                        show_error(f"Failed to update: {format_sql_error(e)}")
        else:
            show_info("No configurations to edit. Create one first.")
    except Exception as e:
        show_error(f"Failed to load configurations: {format_sql_error(e)}")

# ============================================================================
# TAB 4: DELETE
# ============================================================================
with tab4:
    st.subheader("Delete Inbox Configuration")
    show_warning("⚠️ Deletion is permanent and cannot be undone.")

    try:
        configs = list_inbox_configs()
        if configs:
            config_options = {f"{c['inbox_config_id']}: {c['config_name']}": c['inbox_config_id'] for c in configs}
            selected = st.selectbox(
                "Select Configuration to Delete",
                options=list(config_options.keys()),
                key="delete_select"
            )
            selected_id = config_options[selected]
            config = get_inbox_config(selected_id)

            if config:
                st.markdown("**Configuration Details:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Name", value=config['config_name'], disabled=True)
                    st.text_input("Attachment Pattern", value=config['attachment_pattern'], disabled=True)
                with col2:
                    st.text_input("Target Directory", value=config['target_directory'], disabled=True)
                    st.text_input("Status", value="Active" if config['is_active'] else "Inactive", disabled=True)

                st.divider()
                confirm = st.checkbox("I confirm I want to delete this configuration", key="delete_confirm")

                if confirm:
                    if st.button("🗑️ Delete Permanently", type="primary"):
                        try:
                            delete_inbox_config(selected_id)
                            show_success("Configuration deleted successfully")
                            st.rerun()
                        except Exception as e:
                            show_error(f"Failed to delete: {format_sql_error(e)}")
        else:
            show_info("No configurations to delete.")
    except Exception as e:
        show_error(f"Failed to load configurations: {format_sql_error(e)}")

# Footer
st.divider()
st.caption("💡 Tip: Link inbox configs to import configs for automatic file processing after download.")

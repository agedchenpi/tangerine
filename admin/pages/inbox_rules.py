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
    get_inbox_stats, config_name_exists, get_import_configs,
    validate_subject_pattern, validate_sender_pattern, validate_attachment_pattern,
    get_pattern_test_summary
)
from utils.db_helpers import format_sql_error
from utils.ui_helpers import load_custom_css, add_page_header

# Pattern hint constants for user guidance
SUBJECT_PATTERN_HINTS = """
| Pattern | What it matches |
|---------|----------------|
| `.*Report.*` | Any subject containing "Report" |
| `^Invoice` | Subjects starting with "Invoice" |
| `.*\\d{4}-\\d{2}-\\d{2}.*` | Subjects with dates like 2026-01-15 |
| *(leave blank)* | Match all subjects |
"""

SENDER_PATTERN_HINTS = """
| Pattern | What it matches |
|---------|----------------|
| `.*@company\\.com$` | Any email from @company.com |
| `^reports@company\\.com$` | Exact address match |
| `^(reports|alerts)@.*` | From reports@ or alerts@ |
| *(leave blank)* | Match all senders |
"""

ATTACHMENT_PATTERN_HINTS = """
| Pattern | What it matches |
|---------|----------------|
| `*.csv` | Any CSV file |
| `*.xlsx` | Any Excel file |
| `report_*.csv` | CSV files starting with "report_" |
| `*.{csv,xlsx}` | CSV or Excel files |
"""

QUICK_START_SCENARIOS = """
**Daily report from finance:**
- Subject: `.*Daily Report.*`
- Sender: `.*@finance\\.yourcompany\\.com$`
- Attachment: `*.csv`

**Monthly invoices (any sender):**
- Subject: `^Invoice`
- Sender: *(leave blank)*
- Attachment: `*.pdf`

**All attachments from specific sender:**
- Subject: *(leave blank)*
- Sender: `^reports@vendor\\.com$`
- Attachment: `*.*`
"""

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
                help="Leave blank to match all. See examples below."
            )
            with st.expander("Common examples", expanded=False):
                st.markdown(SUBJECT_PATTERN_HINTS)
            attachment_pattern = st.text_input(
                "Attachment Pattern *",
                value=config_data.get('attachment_pattern', '*.csv') if config_data else '*.csv',
                help="Use * as wildcard. Example: *.csv for all CSV files"
            )
            with st.expander("Common examples", expanded=False):
                st.markdown(ATTACHMENT_PATTERN_HINTS)

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
                help="Leave blank to match all senders. See examples below."
            )
            with st.expander("Common examples", expanded=False):
                st.markdown(SENDER_PATTERN_HINTS)

        st.markdown("### File Settings")
        col1, col2 = st.columns(2)

        with col1:
            target_directory = st.text_input(
                "Target Directory *",
                value=config_data.get('target_directory', '/app/data/source/inbox') if config_data else '/app/data/source/inbox',
                help="Where files are saved. Default works for most setups."
            )

        with col2:
            date_prefix_format = st.text_input(
                "Date Prefix Format",
                value=config_data.get('date_prefix_format', 'yyyyMMdd') if config_data else 'yyyyMMdd',
                help="Prepended to filenames. yyyyMMdd = 20260118_file.csv"
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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 View All",
    "➕ Create New",
    "✏️ Edit",
    "🗑️ Delete",
    "🧪 Test Patterns"
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

    with st.expander("Quick Start - Common Scenarios", expanded=False):
        st.markdown(QUICK_START_SCENARIOS)

    form_data = render_inbox_config_form(is_edit=False)
    if form_data:
        try:
            if config_name_exists(form_data['config_name']):
                show_error(f"Configuration name '{form_data['config_name']}' already exists")
            else:
                new_id = create_inbox_config(form_data)
                show_success(f"Inbox configuration created successfully! (ID: {new_id})")
                st.toast("Inbox config created!", icon="✅")
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

# ============================================================================
# TAB 5: TEST PATTERNS
# ============================================================================
with tab5:
    st.subheader("Test Pattern Matching")
    st.markdown("Test your regex and glob patterns against sample inputs before creating configurations.")

    # Pattern source selection
    col1, col2 = st.columns([1, 2])
    with col1:
        pattern_source = st.radio(
            "Pattern Source",
            ["Custom Patterns", "From Existing Config"],
            key="pattern_source"
        )

    if pattern_source == "From Existing Config":
        try:
            configs = list_inbox_configs()
            if configs:
                config_options = {f"{c['inbox_config_id']}: {c['config_name']}": c['inbox_config_id'] for c in configs}
                selected = st.selectbox(
                    "Select Configuration",
                    options=list(config_options.keys()),
                    key="test_config_select"
                )
                selected_id = config_options[selected]
                config = get_inbox_config(selected_id)

                if config:
                    test_subject = config.get('subject_pattern', '') or ''
                    test_sender = config.get('sender_pattern', '') or ''
                    test_attachment = config.get('attachment_pattern', '') or ''
                else:
                    test_subject = test_sender = test_attachment = ''
            else:
                show_info("No configurations found. Use custom patterns.")
                test_subject = test_sender = test_attachment = ''
        except Exception as e:
            show_error(f"Failed to load configurations: {format_sql_error(e)}")
            test_subject = test_sender = test_attachment = ''
    else:
        test_subject = ''
        test_sender = ''
        test_attachment = ''

    st.divider()

    # Three expandable sections for different pattern types
    # Subject Pattern Testing
    with st.expander("📧 Subject Pattern (Regex)", expanded=True):
        col1, col2 = st.columns([1, 1])

        with col1:
            subject_pattern = st.text_input(
                "Subject Pattern",
                value=test_subject if pattern_source == "From Existing Config" else '',
                placeholder="e.g., .*Daily Report.*",
                help="Regex pattern to match email subjects",
                key="validate_subject_pattern"
            )

            sample_subjects = st.text_area(
                "Sample Subjects (one per line)",
                value="Daily Report Q1 2026\nWeekly Summary\nInvoice 2026-001\nDaily Report Q2 2026",
                height=120,
                help="Enter sample email subjects to test against",
                key="sample_subjects"
            )

            test_subject_btn = st.button("🧪 Test Subject Pattern", key="test_subject_btn")

        with col2:
            if test_subject_btn and subject_pattern:
                subjects = [s.strip() for s in sample_subjects.strip().split('\n') if s.strip()]
                if subjects:
                    results = validate_subject_pattern(subject_pattern, subjects)
                    summary = get_pattern_test_summary(results)

                    if summary['has_error']:
                        show_error(results[0].get('error', 'Invalid pattern'))
                    else:
                        st.markdown(f"**Results:** {summary['matches']}/{summary['total']} matched ({summary['match_rate']:.1f}%)")

                        for r in results:
                            if r['matches']:
                                st.markdown(f"✅ `{r['input']}`")
                                if r.get('groups'):
                                    st.caption(f"   Groups: {r['groups']}")
                            else:
                                st.markdown(f"❌ `{r['input']}`")
                else:
                    show_warning("Enter at least one sample subject to test.")
            elif test_subject_btn:
                show_warning("Enter a pattern to test.")

    # Sender Pattern Testing
    with st.expander("👤 Sender Pattern (Regex)", expanded=False):
        col1, col2 = st.columns([1, 1])

        with col1:
            sender_pattern = st.text_input(
                "Sender Pattern",
                value=test_sender if pattern_source == "From Existing Config" else '',
                placeholder="e.g., .*@company\\.com",
                help="Regex pattern to match sender email addresses",
                key="validate_sender_pattern"
            )

            sample_senders = st.text_area(
                "Sample Senders (one per line)",
                value="reports@company.com\njohn.doe@external.org\nalerts@company.com\nspam@unknown.net",
                height=120,
                help="Enter sample email addresses to test against",
                key="sample_senders"
            )

            test_sender_btn = st.button("🧪 Test Sender Pattern", key="test_sender_btn")

        with col2:
            if test_sender_btn and sender_pattern:
                senders = [s.strip() for s in sample_senders.strip().split('\n') if s.strip()]
                if senders:
                    results = validate_sender_pattern(sender_pattern, senders)
                    summary = get_pattern_test_summary(results)

                    if summary['has_error']:
                        show_error(results[0].get('error', 'Invalid pattern'))
                    else:
                        st.markdown(f"**Results:** {summary['matches']}/{summary['total']} matched ({summary['match_rate']:.1f}%)")

                        for r in results:
                            if r['matches']:
                                st.markdown(f"✅ `{r['input']}`")
                                if r.get('groups'):
                                    st.caption(f"   Groups: {r['groups']}")
                            else:
                                st.markdown(f"❌ `{r['input']}`")
                else:
                    show_warning("Enter at least one sample sender to test.")
            elif test_sender_btn:
                show_warning("Enter a pattern to test.")

    # Attachment Pattern Testing
    with st.expander("📎 Attachment Pattern (Glob)", expanded=False):
        col1, col2 = st.columns([1, 1])

        with col1:
            attachment_pattern = st.text_input(
                "Attachment Pattern",
                value=test_attachment if pattern_source == "From Existing Config" else '',
                placeholder="e.g., *.csv or report_*.xlsx",
                help="Glob pattern to match attachment filenames",
                key="validate_attachment_pattern"
            )

            sample_attachments = st.text_area(
                "Sample Filenames (one per line)",
                value="report_2026.csv\ndata.xlsx\nreport_q1.csv\nimage.png\ndaily_report.csv",
                height=120,
                help="Enter sample attachment filenames to test against",
                key="sample_attachments"
            )

            test_attach_btn = st.button("🧪 Test Attachment Pattern", key="test_attach_btn")

        with col2:
            if test_attach_btn and attachment_pattern:
                filenames = [f.strip() for f in sample_attachments.strip().split('\n') if f.strip()]
                if filenames:
                    results = validate_attachment_pattern(attachment_pattern, filenames)
                    summary = get_pattern_test_summary(results)

                    if summary['has_error']:
                        show_error(results[0].get('error', 'Invalid pattern'))
                    else:
                        st.markdown(f"**Results:** {summary['matches']}/{summary['total']} matched ({summary['match_rate']:.1f}%)")

                        for r in results:
                            if r['matches']:
                                st.markdown(f"✅ `{r['input']}`")
                            else:
                                st.markdown(f"❌ `{r['input']}`")
                else:
                    show_warning("Enter at least one sample filename to test.")
            elif test_attach_btn:
                show_warning("Enter a pattern to test.")

    # Pattern reference guide
    with st.expander("📖 Pattern Reference Guide", expanded=False):
        st.markdown("""
        ### Regex Patterns (Subject & Sender)

        | Pattern | Description | Example |
        |---------|-------------|---------|
        | `.*` | Match any characters | `.*Report.*` matches "Daily Report Q1" |
        | `^` | Start of string | `^Invoice` matches "Invoice 123" |
        | `$` | End of string | `\\.pdf$` matches "file.pdf" |
        | `\\d` | Any digit | `Report-\\d+` matches "Report-123" |
        | `\\w` | Word character | `\\w+@company\\.com` |
        | `[abc]` | Character class | `[0-9]{4}` matches "2026" |
        | `(...)` | Capture group | `Report-(\\d+)` captures "123" |
        | `\\.` | Literal dot | `user@company\\.com` |

        ### Glob Patterns (Attachments)

        | Pattern | Description | Example |
        |---------|-------------|---------|
        | `*` | Match any characters | `*.csv` matches any CSV file |
        | `?` | Match single character | `report_?.csv` matches "report_1.csv" |
        | `[abc]` | Character class | `file[0-9].txt` matches "file1.txt" |
        | `**` | Recursive match | Not typically used for filenames |

        ### Common Examples

        **Subject Patterns:**
        - `.*Daily Report.*` - Contains "Daily Report"
        - `^(Invoice|Receipt).*` - Starts with Invoice or Receipt
        - `.*\\d{4}-\\d{2}-\\d{2}.*` - Contains a date like 2026-01-15

        **Sender Patterns:**
        - `.*@company\\.com$` - From company.com domain
        - `(reports|alerts)@.*` - From reports or alerts address

        **Attachment Patterns:**
        - `*.csv` - Any CSV file
        - `report_*.xlsx` - Excel files starting with "report_"
        - `*_202[0-9].csv` - CSV files with years 2020-2029
        """)


# Footer
st.divider()
st.caption("💡 Tip: Link inbox configs to import configs for automatic file processing after download.")

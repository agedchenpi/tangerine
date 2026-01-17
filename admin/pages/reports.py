"""Report Manager Page"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

from components.notifications import show_success, show_error, show_warning, show_info
from components.validators import (
    validate_required, validate_config_name, validate_email_list,
    validate_sql_query, validate_max_length
)
from services.report_manager_service import (
    list_reports, get_report, create_report, update_report,
    delete_report, toggle_active, get_report_stats, report_name_exists,
    get_schedules, get_output_formats, test_report_preview, execute_report
)
from services.scheduler_service import (
    create_schedule_for_report, get_schedule, build_cron_expression,
    calculate_next_run, job_name_exists as schedule_name_exists
)
from utils.db_helpers import format_sql_error
from utils.ui_helpers import load_custom_css, add_page_header

load_custom_css()
add_page_header("Report Manager", "Configure automated email reports", "📊")

# Statistics
try:
    stats = get_report_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Reports", stats['total'])
    with col2:
        st.metric("Active", stats['active'])
    with col3:
        st.metric("Last Run Success", stats['success'])
    with col4:
        st.metric("Last Run Failed", stats['failed'])
except Exception as e:
    show_error(f"Failed to load statistics: {format_sql_error(e)}")

st.divider()


def render_report_form(
    report_data: Optional[Dict[str, Any]] = None,
    is_edit: bool = False
) -> Optional[Dict[str, Any]]:
    """Render report configuration form."""
    form_key = "report_form_edit" if is_edit else "report_form_create"

    with st.form(key=form_key):
        st.markdown("### Basic Information")
        col1, col2 = st.columns(2)

        with col1:
            report_name = st.text_input(
                "Report Name *",
                value=report_data.get('report_name', '') if report_data else '',
                help="Unique name for this report"
            )
            recipients = st.text_input(
                "Recipients *",
                value=report_data.get('recipients', '') if report_data else '',
                help="Comma-separated email addresses"
            )
            subject_line = st.text_input(
                "Subject Line *",
                value=report_data.get('subject_line', '') if report_data else '',
                help="Email subject line"
            )

        with col2:
            description = st.text_area(
                "Description",
                value=report_data.get('description', '') if report_data else '',
                height=68,
                help="Optional description"
            )
            cc_recipients = st.text_input(
                "CC Recipients",
                value=report_data.get('cc_recipients', '') if report_data else '',
                help="Comma-separated CC email addresses"
            )

        st.markdown("### Report Template")
        st.markdown("""
        Use `{{SQL:your query here}}` to embed SQL queries that will be rendered as tables.

        **Example:**
        ```html
        <h2>Daily Log Summary</h2>
        <p>Log entries from today:</p>
        {{SQL:SELECT processtype, COUNT(*) as count FROM dba.tlogentry WHERE DATE(timestamp) = CURRENT_DATE GROUP BY processtype}}
        ```
        """)

        body_template = st.text_area(
            "Body Template *",
            value=report_data.get('body_template', '<h1>Report Title</h1>\n<p>Description here.</p>\n\n{{SQL:SELECT * FROM dba.tlogentry LIMIT 10}}') if report_data else '<h1>Report Title</h1>\n<p>Description here.</p>\n\n{{SQL:SELECT * FROM dba.tlogentry LIMIT 10}}',
            height=200,
            help="HTML template with embedded SQL queries"
        )

        st.markdown("### Output Settings")
        col1, col2 = st.columns(2)

        output_formats = get_output_formats()
        format_options = {f['value']: f"{f['label']} - {f['description']}" for f in output_formats}
        current_format = report_data.get('output_format', 'html') if report_data else 'html'

        with col1:
            output_format = st.selectbox(
                "Output Format",
                options=list(format_options.keys()),
                format_func=lambda x: format_options[x],
                index=list(format_options.keys()).index(current_format) if current_format in format_options else 0,
                help="How to deliver the report data"
            )

        with col2:
            attachment_filename = st.text_input(
                "Attachment Filename",
                value=report_data.get('attachment_filename', '') if report_data else '',
                help="Base filename for attachments (extension added automatically)"
            )

        st.markdown("### Schedule")
        col1, col2 = st.columns(2)

        schedules = get_schedules()
        schedule_options = [{'scheduler_id': None, 'job_name': '-- No Schedule (Manual) --'}] + schedules
        current_schedule = report_data.get('schedule_id') if report_data else None

        with col1:
            schedule_id = st.selectbox(
                "Linked Schedule",
                options=[s['scheduler_id'] for s in schedule_options],
                format_func=lambda x: next((s['job_name'] for s in schedule_options if s['scheduler_id'] == x), '-- No Schedule --'),
                index=next((i for i, s in enumerate(schedule_options) if s['scheduler_id'] == current_schedule), 0),
                help="Select a schedule to automatically run this report"
            )

        with col2:
            is_active = st.checkbox(
                "Active",
                value=report_data.get('is_active', True) if report_data else True
            )

        submitted = st.form_submit_button(
            "💾 " + ("Update Report" if is_edit else "Create Report"),
            use_container_width=True
        )

        if submitted:
            errors = []

            # Validation
            is_valid, error = validate_required(report_name, "Report Name")
            if not is_valid:
                errors.append(error)
            else:
                is_valid, error = validate_config_name(report_name)
                if not is_valid:
                    errors.append(error)

            is_valid, error = validate_email_list(recipients, "Recipients")
            if not is_valid:
                errors.append(error)

            if cc_recipients:
                is_valid, error = validate_email_list(cc_recipients, "CC Recipients")
                if not is_valid:
                    errors.append(error)

            is_valid, error = validate_required(subject_line, "Subject Line")
            if not is_valid:
                errors.append(error)

            is_valid, error = validate_required(body_template, "Body Template")
            if not is_valid:
                errors.append(error)

            # Validate embedded SQL queries
            import re
            sql_pattern = r'\{\{SQL:(.*?)\}\}'
            sql_matches = re.findall(sql_pattern, body_template, re.DOTALL)
            for sql in sql_matches:
                is_valid, error = validate_sql_query(sql.strip())
                if not is_valid:
                    errors.append(f"SQL Query: {error}")
                    break

            if errors:
                for error in errors:
                    show_error(error)
                return None

            return {
                'report_name': report_name,
                'description': description or None,
                'recipients': recipients,
                'cc_recipients': cc_recipients or None,
                'subject_line': subject_line,
                'body_template': body_template,
                'output_format': output_format,
                'attachment_filename': attachment_filename or None,
                'schedule_id': schedule_id,
                'is_active': is_active
            }

    return None


# Main tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 View All",
    "➕ Create New",
    "✏️ Edit",
    "🗑️ Delete",
    "▶️ Run Report",
    "🧪 Test Report"
])

# ============================================================================
# TAB 1: VIEW ALL
# ============================================================================
with tab1:
    st.subheader("All Reports")

    col1, col2 = st.columns([3, 1])
    with col2:
        show_active_only = st.checkbox("Active only", value=False, key="view_active_only")

    try:
        reports = list_reports(active_only=show_active_only)
        if reports:
            df = pd.DataFrame(reports)
            display_cols = [
                'report_id', 'report_name', 'recipients', 'output_format',
                'is_active', 'last_run_at', 'last_run_status'
            ]
            display_cols = [c for c in display_cols if c in df.columns]
            df_display = df[display_cols].copy()

            # Format columns
            if 'is_active' in df_display.columns:
                df_display['is_active'] = df_display['is_active'].map({True: '✅', False: '❌'})
            if 'last_run_at' in df_display.columns:
                df_display['last_run_at'] = pd.to_datetime(df_display['last_run_at']).dt.strftime('%Y-%m-%d %H:%M')
            if 'last_run_status' in df_display.columns:
                df_display['last_run_status'] = df_display['last_run_status'].map({'Success': '✅ Success', 'Failed': '❌ Failed', None: '-'})

            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            show_info("No reports found. Create one in the 'Create New' tab.")
    except Exception as e:
        show_error(f"Failed to load reports: {format_sql_error(e)}")

# ============================================================================
# TAB 2: CREATE NEW
# ============================================================================
with tab2:
    st.subheader("Create New Report")

    form_data = render_report_form(is_edit=False)
    if form_data:
        try:
            if report_name_exists(form_data['report_name']):
                show_error(f"Report name '{form_data['report_name']}' already exists")
            else:
                new_id = create_report(form_data)
                show_success(f"Report created successfully! (ID: {new_id})")
                st.toast("Report created!", icon="✅")
        except Exception as e:
            show_error(f"Failed to create report: {format_sql_error(e)}")

# ============================================================================
# TAB 3: EDIT
# ============================================================================
with tab3:
    st.subheader("Edit Report")

    if 'report_update_success' in st.session_state:
        show_success(st.session_state.report_update_success)
        del st.session_state.report_update_success

    try:
        reports = list_reports()
        if reports:
            report_options = {f"{r['report_id']}: {r['report_name']}": r['report_id'] for r in reports}
            selected = st.selectbox(
                "Select Report",
                options=list(report_options.keys()),
                key="edit_select"
            )
            selected_id = report_options[selected]
            report = get_report(selected_id)

            if report:
                col1, col2 = st.columns([1, 4])
                with col1:
                    current_status = report.get('is_active', True)
                    if current_status:
                        if st.button("🔴 Deactivate", key="deactivate_btn"):
                            toggle_active(selected_id, False)
                            st.session_state.report_update_success = "Report deactivated"
                            st.rerun()
                    else:
                        if st.button("🟢 Activate", key="activate_btn"):
                            toggle_active(selected_id, True)
                            st.session_state.report_update_success = "Report activated"
                            st.rerun()

                st.divider()

                form_data = render_report_form(report_data=report, is_edit=True)
                if form_data:
                    try:
                        if form_data['report_name'] != report['report_name']:
                            if report_name_exists(form_data['report_name'], exclude_id=selected_id):
                                show_error(f"Report name '{form_data['report_name']}' already exists")
                                st.stop()

                        update_report(selected_id, form_data)
                        st.session_state.report_update_success = "Report updated successfully!"
                        st.rerun()
                    except Exception as e:
                        show_error(f"Failed to update: {format_sql_error(e)}")

                # Quick Schedule Creator
                st.divider()

                # Show current schedule status
                if report.get('schedule_id'):
                    schedule = get_schedule(report['schedule_id'])
                    if schedule:
                        cron_expr = build_cron_expression(schedule)
                        next_run = calculate_next_run(cron_expr)
                        st.success(f"📅 Scheduled: **{schedule['job_name']}** ({cron_expr})")
                        if next_run:
                            st.info(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

                with st.expander("⏰ Create New Schedule for This Report"):
                    st.markdown("Quickly create a schedule without leaving this page.")

                    with st.form("quick_schedule_form"):
                        default_name = f"{report['report_name']}_schedule"
                        quick_job_name = st.text_input(
                            "Schedule Name *",
                            value=default_name,
                            help="Unique name for this schedule"
                        )

                        st.markdown("**Cron Schedule**")
                        cron_col1, cron_col2, cron_col3, cron_col4, cron_col5 = st.columns(5)
                        with cron_col1:
                            q_minute = st.text_input("Minute", value="0", key="q_minute")
                        with cron_col2:
                            q_hour = st.text_input("Hour", value="8", key="q_hour")
                        with cron_col3:
                            q_day = st.text_input("Day", value="*", key="q_day")
                        with cron_col4:
                            q_month = st.text_input("Month", value="*", key="q_month")
                        with cron_col5:
                            q_weekday = st.text_input("Weekday", value="1-5", key="q_weekday")

                        st.caption("Common: `0 8 * * 1-5` = Weekdays at 8 AM, `0 8 * * *` = Daily at 8 AM")

                        if st.form_submit_button("📅 Create Schedule & Link", use_container_width=True):
                            try:
                                if schedule_name_exists(quick_job_name):
                                    show_error(f"Schedule name '{quick_job_name}' already exists")
                                else:
                                    new_schedule_id = create_schedule_for_report(
                                        report_id=selected_id,
                                        job_name=quick_job_name,
                                        cron_minute=q_minute,
                                        cron_hour=q_hour,
                                        cron_day=q_day,
                                        cron_month=q_month,
                                        cron_weekday=q_weekday
                                    )
                                    st.session_state.report_update_success = f"Schedule created and linked! (ID: {new_schedule_id}) Crontab regenerated."
                                    st.rerun()
                            except Exception as e:
                                show_error(f"Failed to create schedule: {format_sql_error(e)}")
        else:
            show_info("No reports to edit. Create one first.")
    except Exception as e:
        show_error(f"Failed to load reports: {format_sql_error(e)}")

# ============================================================================
# TAB 4: DELETE
# ============================================================================
with tab4:
    st.subheader("Delete Report")
    show_warning("⚠️ Deletion is permanent and cannot be undone.")

    try:
        reports = list_reports()
        if reports:
            report_options = {f"{r['report_id']}: {r['report_name']}": r['report_id'] for r in reports}
            selected = st.selectbox(
                "Select Report to Delete",
                options=list(report_options.keys()),
                key="delete_select"
            )
            selected_id = report_options[selected]
            report = get_report(selected_id)

            if report:
                st.markdown("**Report Details:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Name", value=report['report_name'], disabled=True)
                    st.text_input("Recipients", value=report['recipients'], disabled=True)
                with col2:
                    st.text_input("Output Format", value=report['output_format'], disabled=True)
                    st.text_input("Status", value="Active" if report['is_active'] else "Inactive", disabled=True)

                st.divider()
                confirm = st.checkbox("I confirm I want to delete this report", key="delete_confirm")

                if confirm:
                    if st.button("🗑️ Delete Permanently", type="primary"):
                        try:
                            delete_report(selected_id)
                            show_success("Report deleted successfully")
                            st.rerun()
                        except Exception as e:
                            show_error(f"Failed to delete: {format_sql_error(e)}")
        else:
            show_info("No reports to delete.")
    except Exception as e:
        show_error(f"Failed to load reports: {format_sql_error(e)}")

# ============================================================================
# TAB 5: RUN REPORT
# ============================================================================
with tab5:
    st.subheader("Run Report Now")
    st.markdown("Execute a report immediately and send the email to recipients.")

    try:
        reports = list_reports(active_only=True)
        if reports:
            report_options = {f"{r['report_id']}: {r['report_name']}": r['report_id'] for r in reports}
            selected = st.selectbox(
                "Select Report to Run",
                options=list(report_options.keys()),
                key="run_select"
            )
            selected_id = report_options[selected]

            # Show report details
            report = get_report(selected_id)
            if report:
                with st.expander("📋 Report Details", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Recipients", report['recipients'][:50] + "..." if len(report['recipients']) > 50 else report['recipients'])
                        st.metric("Output Format", report['output_format'])
                    with col2:
                        last_run = report.get('last_run_at')
                        st.metric("Last Run", last_run.strftime('%Y-%m-%d %H:%M') if last_run else 'Never')
                        st.metric("Last Status", report.get('last_run_status') or '-')

            st.divider()

            # Confirmation checkbox
            confirm = st.checkbox(
                "I confirm I want to send this report NOW to the recipients",
                key="run_confirm"
            )

            if confirm:
                if st.button("📧 Send Report Now", type="primary", use_container_width=True):
                    st.markdown("---")
                    st.markdown("#### 📊 Report Execution Output")

                    # Create output container
                    output_container = st.empty()
                    output_lines = []

                    with st.spinner("Sending report..."):
                        try:
                            for line in execute_report(selected_id, dry_run=False):
                                output_lines.append(line)
                                display_lines = output_lines[-50:]
                                output_container.text_area(
                                    "Output",
                                    value="\n".join(display_lines),
                                    height=300,
                                    disabled=True,
                                    label_visibility="collapsed"
                                )

                            # Check result
                            if any("✅" in line for line in output_lines[-5:]):
                                show_success("Report sent successfully!")
                                st.toast("Report sent!", icon="📧")
                            elif any("❌" in line for line in output_lines[-5:]):
                                show_error("Report failed. Check the output above for details.")
                            else:
                                show_info("Report execution finished. Review output above.")

                        except Exception as e:
                            show_error(f"Error executing report: {format_sql_error(e)}")

                    # Show full output in expander if truncated
                    if len(output_lines) > 50:
                        with st.expander("📄 View Full Output", expanded=False):
                            st.text_area(
                                "Full Output",
                                value="\n".join(output_lines),
                                height=400,
                                disabled=True,
                                label_visibility="collapsed"
                            )
        else:
            show_info("No active reports to run. Create and activate a report first.")
    except Exception as e:
        show_error(f"Failed to load reports: {format_sql_error(e)}")

# ============================================================================
# TAB 6: TEST REPORT
# ============================================================================
with tab6:
    st.subheader("Test Report (Dry Run)")
    st.markdown("Preview report output without sending emails.")

    try:
        reports = list_reports(active_only=True)
        if reports:
            report_options = {f"{r['report_id']}: {r['report_name']}": r['report_id'] for r in reports}
            selected = st.selectbox(
                "Select Report to Test",
                options=list(report_options.keys()),
                key="test_select"
            )
            selected_id = report_options[selected]

            if st.button("🧪 Run Test", type="primary"):
                with st.spinner("Generating report preview..."):
                    result = test_report_preview(selected_id)

                    if result['success']:
                        show_success("Report generated successfully (not sent)")
                        st.text_area(
                            "Test Output",
                            value=result['output'],
                            height=300,
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    else:
                        show_error(f"Report generation failed: {result['error']}")
                        if result['output']:
                            st.text_area(
                                "Error Output",
                                value=result['output'],
                                height=300,
                                disabled=True,
                                label_visibility="collapsed"
                            )
        else:
            show_info("No active reports to test.")
    except Exception as e:
        show_error(f"Failed to load reports: {format_sql_error(e)}")

# Footer
st.divider()
st.caption("💡 Tip: Use `{{SQL:query}}` in templates to embed data. Only SELECT queries are allowed.")

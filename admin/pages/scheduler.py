"""Scheduler Management Page"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

from components.notifications import show_success, show_error, show_warning, show_info
from components.validators import (
    validate_required, validate_config_name, validate_cron_expression
)
from services.scheduler_service import (
    list_schedules, get_schedule, create_schedule, update_schedule,
    delete_schedule, toggle_active, get_scheduler_stats, job_name_exists,
    get_job_types, get_config_options, regenerate_crontab, get_crontab_preview,
    build_cron_expression, calculate_next_run, execute_schedule_adhoc
)
from utils.db_helpers import format_sql_error
from utils.ui_helpers import load_custom_css, add_page_header, render_stat_card
from components.dependency_checker import render_missing_config_link

# Cron hint constants for user guidance
CRON_HINTS = """
| Schedule | Expression | Description |
|----------|------------|-------------|
| Every hour | `0 * * * *` | At minute 0 of every hour |
| Daily at 8am | `0 8 * * *` | 8:00 AM every day |
| Weekdays 6pm | `0 18 * * 1-5` | Mon-Fri at 6:00 PM |
| First of month | `0 0 1 * *` | Midnight on day 1 |
| Every 15 min | `*/15 * * * *` | :00, :15, :30, :45 |
| Every 5 min | `*/5 * * * *` | Every 5 minutes |
"""

SCHEDULER_QUICK_START = """
**Daily import job at 6 AM:**
- Job Type: Import
- Minute: `0`, Hour: `6`, Day: `*`, Month: `*`, Weekday: `*`

**Hourly inbox check:**
- Job Type: Inbox Processor
- Minute: `0`, Hour: `*`, Day: `*`, Month: `*`, Weekday: `*`

**Weekly report (Monday 8 AM):**
- Job Type: Report
- Minute: `0`, Hour: `8`, Day: `*`, Month: `*`, Weekday: `1`

**Business hours only (every 30 min, Mon-Fri 9-5):**
- Job Type: Any
- Minute: `0,30`, Hour: `9-17`, Day: `*`, Month: `*`, Weekday: `1-5`
"""

load_custom_css()
add_page_header("Job Scheduler", icon="⏰")

# Statistics
try:
    stats = get_scheduler_stats()
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        render_stat_card("Total Schedules", str(stats['total']), icon="📅", color="#17A2B8")
    with col2:
        render_stat_card("Active", str(stats['active']), icon="✅", color="#28A745")
    with col3:
        render_stat_card("Inbox Jobs", str(stats['inbox_count']), icon="📥", color="#6F42C1")
    with col4:
        render_stat_card("Report Jobs", str(stats['report_count']), icon="📊", color="#FFC107")
    with col5:
        render_stat_card("Import Jobs", str(stats['import_count']), icon="📤", color="#FF8C42")
    with col6:
        render_stat_card("Custom Jobs", str(stats['custom_count']), icon="⚙️", color="#E83E8C")
except Exception as e:
    show_error(f"Failed to load statistics: {format_sql_error(e)}")

st.divider()


def render_scheduler_form(
    schedule_data: Optional[Dict[str, Any]] = None,
    is_edit: bool = False
) -> Optional[Dict[str, Any]]:
    """Render scheduler configuration form."""
    form_key = "scheduler_form_edit" if is_edit else "scheduler_form_create"

    with st.form(key=form_key):
        st.markdown("### Basic Information")
        col1, col2 = st.columns(2)

        with col1:
            job_name = st.text_input(
                "Job Name *",
                value=schedule_data.get('job_name', '') if schedule_data else '',
                help="Unique name for this scheduled job"
            )

        job_types = get_job_types()
        type_options = {t['value']: f"{t['label']} - {t['description']}" for t in job_types}
        current_type = schedule_data.get('job_type', 'inbox_processor') if schedule_data else 'inbox_processor'

        with col2:
            job_type = st.selectbox(
                "Job Type *",
                options=list(type_options.keys()),
                format_func=lambda x: type_options[x],
                index=list(type_options.keys()).index(current_type) if current_type in type_options else 0
            )

        st.markdown("### Cron Schedule")
        st.markdown("""
        **Cron Format:** `minute hour day month weekday`

        - `*` = any value
        - `*/n` = every n units
        - `n` = specific value
        - `n-m` = range
        - `n,m` = list
        """)

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            cron_minute = st.text_input(
                "Minute (0-59)",
                value=schedule_data.get('cron_minute', '0') if schedule_data else '0',
                help="Minute field"
            )
        with col2:
            cron_hour = st.text_input(
                "Hour (0-23)",
                value=schedule_data.get('cron_hour', '8') if schedule_data else '8',
                help="Hour field"
            )
        with col3:
            cron_day = st.text_input(
                "Day (1-31)",
                value=schedule_data.get('cron_day', '*') if schedule_data else '*',
                help="Day of month"
            )
        with col4:
            cron_month = st.text_input(
                "Month (1-12)",
                value=schedule_data.get('cron_month', '*') if schedule_data else '*',
                help="Month field"
            )
        with col5:
            cron_weekday = st.text_input(
                "Weekday (0-6)",
                value=schedule_data.get('cron_weekday', '1-5') if schedule_data else '1-5',
                help="Day of week (0=Sun)"
            )

        # Common presets
        st.markdown("**Common Presets:**")
        preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
        with preset_col1:
            st.caption("Every 5 min: `*/5 * * * *`")
        with preset_col2:
            st.caption("Every hour: `0 * * * *`")
        with preset_col3:
            st.caption("Daily 8 AM: `0 8 * * *`")
        with preset_col4:
            st.caption("Weekdays: `0 8 * * 1-5`")

        with st.expander("More cron examples", expanded=False):
            st.markdown(CRON_HINTS)

        st.markdown("### Job Configuration")

        # Dynamic config selection based on job type
        if job_type in ['inbox_processor', 'report', 'import']:
            config_options_list = get_config_options(job_type)
            if config_options_list:
                config_display = {c['id']: c['name'] for c in config_options_list}
                config_display[None] = '-- All Configurations --'
                current_config = schedule_data.get('config_id') if schedule_data else None

                config_id = st.selectbox(
                    "Configuration",
                    options=[None] + [c['id'] for c in config_options_list],
                    format_func=lambda x: config_display.get(x, '-- All --'),
                    index=([None] + [c['id'] for c in config_options_list]).index(current_config) if current_config in [c['id'] for c in config_options_list] + [None] else 0,
                    help="Select specific config or all"
                )
            else:
                st.info(f"No active {job_type} configurations found.")
                render_missing_config_link(job_type, context="inline")
                config_id = None
            script_path = None

        else:  # custom
            script_path = st.text_input(
                "Script Path *",
                value=schedule_data.get('script_path', '') if schedule_data else '',
                help="Path to Python script (relative to /app)"
            )
            config_id = None

        col1, col2 = st.columns(2)
        with col1:
            is_active = st.checkbox(
                "Active",
                value=schedule_data.get('is_active', True) if schedule_data else True
            )

        submitted = st.form_submit_button(
            "💾 " + ("Update Schedule" if is_edit else "Create Schedule"),
            use_container_width=True
        )

        if submitted:
            errors = []

            # Validation
            is_valid, error = validate_required(job_name, "Job Name")
            if not is_valid:
                errors.append(error)
            else:
                is_valid, error = validate_config_name(job_name)
                if not is_valid:
                    errors.append(error)

            is_valid, error = validate_cron_expression(
                cron_minute, cron_hour, cron_day, cron_month, cron_weekday
            )
            if not is_valid:
                errors.append(error)

            if job_type == 'custom' and not script_path:
                errors.append("Script path is required for custom jobs")

            if errors:
                for error in errors:
                    show_error(error)
                return None

            return {
                'job_name': job_name,
                'job_type': job_type,
                'cron_minute': cron_minute,
                'cron_hour': cron_hour,
                'cron_day': cron_day,
                'cron_month': cron_month,
                'cron_weekday': cron_weekday,
                'script_path': script_path,
                'config_id': config_id,
                'is_active': is_active
            }

    return None


# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 View All",
    "➕ Create New",
    "✏️ Edit",
    "🗑️ Delete",
    "🔄 Crontab"
])

# ============================================================================
# TAB 1: VIEW ALL
# ============================================================================
with tab1:
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.subheader("All Scheduled Jobs")
    with col_header2:
        if st.button("🔄 Refresh", key="refresh_schedules", use_container_width=True):
            st.rerun()

    col1, col2 = st.columns([3, 1])
    with col2:
        show_active_only = st.checkbox("Active only", value=False, key="view_active_only")

    try:
        schedules = list_schedules(active_only=show_active_only)

        # Debug info
        filter_text = "active jobs" if show_active_only else "total jobs"
        st.caption(f"Loaded {len(schedules)} {filter_text} from database")

        if schedules:
            df = pd.DataFrame(schedules)

            # Build cron expression column
            if all(c in df.columns for c in ['cron_minute', 'cron_hour', 'cron_day', 'cron_month', 'cron_weekday']):
                df['cron_expression'] = df.apply(
                    lambda r: f"{r['cron_minute']} {r['cron_hour']} {r['cron_day']} {r['cron_month']} {r['cron_weekday']}",
                    axis=1
                )

            display_cols = [
                'scheduler_id', 'job_name', 'job_type', 'script_path', 'cron_expression',
                'is_active', 'last_run_at', 'last_run_status', 'next_run_at'
            ]
            display_cols = [c for c in display_cols if c in df.columns]
            df_display = df[display_cols].copy()

            # Format columns
            if 'is_active' in df_display.columns:
                df_display['is_active'] = df_display['is_active'].map({True: '✅', False: '❌'})
            if 'last_run_at' in df_display.columns:
                df_display['last_run_at'] = pd.to_datetime(df_display['last_run_at']).dt.strftime('%Y-%m-%d %H:%M')
            if 'next_run_at' in df_display.columns:
                df_display['next_run_at'] = pd.to_datetime(df_display['next_run_at']).dt.strftime('%Y-%m-%d %H:%M')
            if 'last_run_status' in df_display.columns:
                df_display['last_run_status'] = df_display['last_run_status'].map(
                    {'Success': '✅', 'Failed': '❌', 'Running': '🔄', None: '-'}
                )
            # Shorten script_path for better readability - remove 'python /app/' prefix
            if 'script_path' in df_display.columns:
                df_display['script_path'] = df_display['script_path'].str.replace('python /app/', '', regex=False)

            # Add Run Now checkbox column
            df_display.insert(0, 'Run Now', False)

            edited_df = st.data_editor(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Run Now': st.column_config.CheckboxColumn('Run Now', default=False),
                },
                disabled=[c for c in df_display.columns if c != 'Run Now'],
                key="scheduler_data_editor"
            )

            # Run Selected button
            selected_rows = edited_df[edited_df['Run Now'] == True]
            selected_count = len(selected_rows)

            if selected_count > 0:
                if st.button(
                    f"▶️ Run Selected ({selected_count} job{'s' if selected_count > 1 else ''})",
                    type="primary",
                    key="run_selected_jobs"
                ):
                    for _, row in selected_rows.iterrows():
                        sid = int(row['scheduler_id'])
                        job_name = row['job_name']
                        with st.expander(f"📋 {job_name} (ID: {sid})", expanded=True):
                            output_area = st.empty()
                            output_lines = []
                            for line in execute_schedule_adhoc(sid):
                                output_lines.append(line)
                                output_area.code('\n'.join(output_lines), language='log')
                    st.rerun()
        else:
            show_info("No scheduled jobs found. Create one in the 'Create New' tab.")
    except Exception as e:
        show_error(f"Failed to load schedules: {format_sql_error(e)}")
        # Show full exception details for debugging
        with st.expander("🔍 View detailed error"):
            st.exception(e)

# ============================================================================
# TAB 2: CREATE NEW
# ============================================================================
with tab2:
    st.subheader("Create New Schedule")

    with st.expander("Quick Start - Common Scenarios", expanded=False):
        st.markdown(SCHEDULER_QUICK_START)

    form_data = render_scheduler_form(is_edit=False)
    if form_data:
        try:
            if job_name_exists(form_data['job_name']):
                show_error(f"Job name '{form_data['job_name']}' already exists")
            else:
                new_id = create_schedule(form_data)
                show_success(f"✅ Schedule '{form_data['job_name']}' created successfully! (ID: {new_id})")
                st.toast("Schedule created!", icon="✅")

                # Offer to regenerate crontab immediately
                st.divider()
                st.markdown("#### 🔄 Apply Changes")
                st.info("The schedule is saved in the database, but you need to regenerate the crontab to apply it.")

                col1, col2 = st.columns([1, 2])
                with col1:
                    if st.button("🔄 Regenerate Crontab Now", type="primary", key="auto_regen_crontab"):
                        try:
                            success = regenerate_crontab()
                            if success:
                                show_success("✅ Crontab regenerated and applied! Schedule is now active.")
                                st.rerun()
                            else:
                                show_error("Failed to regenerate crontab. Check container logs.")
                        except Exception as e:
                            show_error(f"Error regenerating crontab: {str(e)}")
                with col2:
                    st.caption("You can also regenerate manually in the 'Crontab' tab later.")
        except Exception as e:
            show_error(f"Failed to create schedule: {format_sql_error(e)}")

# ============================================================================
# TAB 3: EDIT
# ============================================================================
with tab3:
    st.subheader("Edit Schedule")

    if 'scheduler_update_success' in st.session_state:
        show_success(st.session_state.scheduler_update_success)
        del st.session_state.scheduler_update_success

    try:
        schedules = list_schedules()
        if schedules:
            schedule_options = {f"{s['scheduler_id']}: {s['job_name']}": s['scheduler_id'] for s in schedules}
            selected = st.selectbox(
                "Select Schedule",
                options=list(schedule_options.keys()),
                key="edit_select"
            )
            selected_id = schedule_options[selected]
            schedule = get_schedule(selected_id)

            if schedule:
                col1, col2 = st.columns([1, 4])
                with col1:
                    current_status = schedule.get('is_active', True)
                    if current_status:
                        if st.button("🔴 Deactivate", key="deactivate_btn"):
                            toggle_active(selected_id, False)
                            st.session_state.scheduler_update_success = "Schedule deactivated"
                            st.rerun()
                    else:
                        if st.button("🟢 Activate", key="activate_btn"):
                            toggle_active(selected_id, True)
                            st.session_state.scheduler_update_success = "Schedule activated"
                            st.rerun()

                # Show next run time
                if schedule.get('next_run_at'):
                    st.info(f"Next run: {schedule['next_run_at']}")
                else:
                    cron_expr = build_cron_expression(schedule)
                    next_run = calculate_next_run(cron_expr)
                    if next_run:
                        st.info(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

                st.divider()

                form_data = render_scheduler_form(schedule_data=schedule, is_edit=True)
                if form_data:
                    try:
                        if form_data['job_name'] != schedule['job_name']:
                            if job_name_exists(form_data['job_name'], exclude_id=selected_id):
                                show_error(f"Job name '{form_data['job_name']}' already exists")
                                st.stop()

                        update_schedule(selected_id, form_data)
                        st.session_state.scheduler_update_success = "Schedule updated! Remember to regenerate crontab."
                        st.rerun()
                    except Exception as e:
                        show_error(f"Failed to update: {format_sql_error(e)}")
        else:
            show_info("No schedules to edit. Create one first.")
    except Exception as e:
        show_error(f"Failed to load schedules: {format_sql_error(e)}")

# ============================================================================
# TAB 4: DELETE
# ============================================================================
with tab4:
    st.subheader("Delete Schedule")
    show_warning("⚠️ Deletion is permanent and cannot be undone.")

    try:
        schedules = list_schedules()
        if schedules:
            schedule_options = {f"{s['scheduler_id']}: {s['job_name']}": s['scheduler_id'] for s in schedules}
            selected = st.selectbox(
                "Select Schedule to Delete",
                options=list(schedule_options.keys()),
                key="delete_select"
            )
            selected_id = schedule_options[selected]
            schedule = get_schedule(selected_id)

            if schedule:
                st.markdown("**Schedule Details:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Name", value=schedule['job_name'], disabled=True)
                    st.text_input("Job Type", value=schedule['job_type'], disabled=True)
                with col2:
                    cron_expr = build_cron_expression(schedule)
                    st.text_input("Cron Expression", value=cron_expr, disabled=True)
                    st.text_input("Status", value="Active" if schedule['is_active'] else "Inactive", disabled=True)

                st.divider()
                confirm = st.checkbox("I confirm I want to delete this schedule", key="delete_confirm")

                if confirm:
                    if st.button("🗑️ Delete Permanently", type="primary"):
                        try:
                            delete_schedule(selected_id)
                            show_success("Schedule deleted! Remember to regenerate crontab.")
                            st.rerun()
                        except Exception as e:
                            show_error(f"Failed to delete: {format_sql_error(e)}")
        else:
            show_info("No schedules to delete.")
    except Exception as e:
        show_error(f"Failed to load schedules: {format_sql_error(e)}")

# ============================================================================
# TAB 5: CRONTAB
# ============================================================================
with tab5:
    st.subheader("Container Crontab Management")
    st.markdown("""
    The crontab is generated from active schedules in the database.
    After making changes to schedules, regenerate and apply the crontab.
    """)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("👁️ Preview Crontab", use_container_width=True):
            with st.spinner("Generating preview..."):
                preview = get_crontab_preview()
                st.code(preview, language='bash')

    with col2:
        if st.button("🔄 Regenerate & Apply", type="primary", use_container_width=True):
            with st.spinner("Regenerating crontab..."):
                success = regenerate_crontab()
                if success:
                    show_success("Crontab regenerated and applied successfully!")
                else:
                    show_error("Failed to regenerate crontab. Check container logs.")

    st.divider()
    st.markdown("### Crontab Quick Reference")
    st.code("""
# Field positions:
# minute (0-59)
# |  hour (0-23)
# |  |  day of month (1-31)
# |  |  |  month (1-12)
# |  |  |  |  day of week (0-6, 0=Sunday)
# |  |  |  |  |
# *  *  *  *  *  command

# Examples:
*/5 * * * *     # Every 5 minutes
0 * * * *       # Every hour at :00
0 8 * * *       # Daily at 8:00 AM
0 8 * * 1-5     # Weekdays at 8:00 AM
0 0 1 * *       # First day of month at midnight
    """, language='bash')

# Footer
st.divider()
st.caption("💡 Tip: After modifying schedules, always regenerate the crontab to apply changes.")

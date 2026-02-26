"""Pipeline Monitor - hierarchical job run and step execution view."""

import streamlit as st
from datetime import datetime, date
from utils.ui_helpers import load_custom_css, add_page_header, render_stat_card
from utils.formatters import format_datetime, format_duration
from utils.db_helpers import format_sql_error
from services.pipeline_monitor_service import (
    get_recent_job_runs,
    get_job_run_steps,
    get_step_logs,
    get_pipeline_stats,
    get_distinct_job_names,
)
from services.job_execution_service import (
    execute_etl_script,
    execute_import_job,
    get_active_configs_for_execution,
)

load_custom_css()
add_page_header("Pipeline Monitor", icon="🔭")

STATUS_ICON = {
    'running': '🔄',
    'success': '✅',
    'failed': '❌',
    'partial': '⚠️',
    'pending': '⏳',
    'skipped': '⏭️',
}

TIME_RANGE_OPTIONS = {
    "Last 1 hour": 1,
    "Last 6 hours": 6,
    "Last 24 hours": 24,
    "Last 7 days": 168,
    "Last 30 days": 720,
    "All time": None,
}


def _fmt_duration(seconds) -> str:
    if seconds is None:
        return "—"
    s = float(seconds)
    if s < 60:
        return f"{s:.1f}s"
    return f"{int(s // 60)}m {int(s % 60)}s"


def _status_badge(status: str) -> str:
    icon = STATUS_ICON.get(status, '❓')
    return f"{icon} {status.capitalize()}"


# ─── Stats Row ────────────────────────────────────────────────────────────────

try:
    hours_for_stats = 24
    stats = get_pipeline_stats(hours=hours_for_stats)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_stat_card("Total Runs (24h)", str(stats['total']), icon="▶️", color="#17A2B8")
    with col2:
        render_stat_card("Success", str(stats['success']), icon="✅", color="#28A745")
    with col3:
        render_stat_card("Failed / Partial", f"{stats['failed']} / {stats['partial']}", icon="❌", color="#DC3545")
    with col4:
        render_stat_card("Running", str(stats['running']), icon="🔄", color="#FFC107")
except Exception as e:
    st.error(f"Error loading stats: {format_sql_error(e)}")

st.divider()

# ─── Pre-fill Banner ──────────────────────────────────────────────────────────

rerun_params = st.session_state.get('pm_rerun_params')
if rerun_params:
    label = rerun_params.get('job_name') or rerun_params.get('config_name', '')
    col_banner, col_clear = st.columns([8, 1])
    with col_banner:
        st.info(f"ℹ️ Re-run queued: **{label}** — switch to ▶️ Run Job tab to execute")
    with col_clear:
        if st.button("✕ Clear", key="pm_clear_rerun"):
            del st.session_state.pm_rerun_params
            st.rerun()

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_history, tab_run = st.tabs(["📋 History", "▶️ Run Job"])

# ─── Tab 1: History ───────────────────────────────────────────────────────────

with tab_history:
    st.markdown("### Filters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        time_label = st.selectbox(
            "Time Range",
            options=list(TIME_RANGE_OPTIONS.keys()),
            index=2,
            key="pm_time_range",
        )
        hours_filter = TIME_RANGE_OPTIONS[time_label]

    with col2:
        try:
            job_names = ["All"] + get_distinct_job_names()
        except Exception:
            job_names = ["All"]
        selected_job = st.selectbox("Job Name", options=job_names, index=0, key="pm_job_name")
        job_name_filter = None if selected_job == "All" else selected_job

    with col3:
        status_options = ["All", "running", "success", "failed", "partial"]
        selected_status = st.selectbox("Status", options=status_options, index=0, key="pm_status")
        status_filter = None if selected_status == "All" else selected_status

    with col4:
        limit = st.selectbox("Max Results", options=[25, 50, 100, 250], index=1, key="pm_limit")

    col_btn1, _ = st.columns([1, 5])
    with col_btn1:
        fetch_clicked = st.button("🔍 Fetch Runs", type="primary", key="pm_fetch_btn")

    st.divider()

    if fetch_clicked or 'pm_runs' not in st.session_state:
        try:
            with st.spinner("Loading job runs..."):
                st.session_state.pm_runs = get_recent_job_runs(
                    limit=limit,
                    status_filter=status_filter,
                    job_name_filter=job_name_filter,
                    hours=hours_filter,
                )
        except Exception as e:
            st.error(f"Error loading runs: {format_sql_error(e)}")
            st.session_state.pm_runs = []

    runs = st.session_state.get('pm_runs', [])

    if not runs:
        st.info("No job runs found. Adjust filters or run an ETL script.")
    else:
        st.markdown(f"**{len(runs)} run(s) found**")

        for run in runs:
            status = run.get('status', 'unknown')
            icon = STATUS_ICON.get(status, '❓')
            job_name = run.get('job_name', '')
            config = run.get('config_name', '')
            started = run.get('started_at')
            duration = _fmt_duration(run.get('duration_seconds'))
            dry = " *(dry-run)*" if run.get('dry_run') else ""
            step_summary = f"{int(run.get('steps_success') or 0)}✅ {int(run.get('steps_failed') or 0)}❌"

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 1])
                with c1:
                    st.markdown(f"### {icon}")
                with c2:
                    st.markdown(f"**{job_name}**{dry}")
                    st.caption(config)
                with c3:
                    st.markdown(f"⏱ {duration}")
                    st.caption(format_datetime(started) if started else "—")
                with c4:
                    st.markdown(f"Steps: {step_summary}")
                    if run.get('error_message'):
                        st.caption(f"⚠️ {run['error_message'][:60]}…")
                with c5:
                    if st.button("View Steps", key=f"steps_btn_{run['jobrunid']}"):
                        st.session_state.pm_selected_run = run

# ─── Tab 2: Run Job ───────────────────────────────────────────────────────────

with tab_run:
    st.markdown("### Run ETL Job")

    run_mode = st.radio(
        "Run Mode",
        options=["🚀 Full ETL Pipeline", "📥 DB Import Only"],
        horizontal=True,
        key="pm_run_mode",
    )

    st.divider()

    # ── Full ETL Pipeline ──
    if run_mode == "🚀 Full ETL Pipeline":
        st.markdown("Runs the complete `run_*.py` script (data collection + DB import).")

        try:
            etl_job_names = get_distinct_job_names()
        except Exception:
            etl_job_names = []

        if not etl_job_names:
            st.warning("No job names found. Run at least one ETL job first, or type a job name below.")
            etl_job_names = []

        # Pre-fill from rerun_params
        default_etl_idx = 0
        if rerun_params and rerun_params.get('mode') == 'full_etl':
            target = rerun_params.get('job_name', '')
            if target in etl_job_names:
                default_etl_idx = etl_job_names.index(target)

        selected_etl_job = st.selectbox(
            "Job Name",
            options=etl_job_names,
            index=default_etl_idx if etl_job_names else None,
            key="pm_run_etl_job",
            help="Select a job name (maps to etl/jobs/{job_name}.py)",
        )

        etl_dry_run = st.checkbox("Dry Run", key="pm_run_etl_dry_run",
                                   help="Run without writing to the database")

        if st.button("▶️ Run ETL Pipeline", type="primary", key="pm_run_etl_btn",
                     disabled=not selected_etl_job):
            st.markdown("---")
            st.markdown(f"**Running:** `etl/jobs/{selected_etl_job}.py`"
                        + (" *(dry-run)*" if etl_dry_run else ""))

            output_container = st.empty()
            output_lines = []

            with st.spinner("Executing ETL pipeline..."):
                try:
                    for line in execute_etl_script(
                        job_name=selected_etl_job,
                        dry_run=etl_dry_run,
                        timeout=300,
                    ):
                        output_lines.append(line)
                        output_container.code("\n".join(output_lines[-50:]), language="text")

                    if any("✅" in line for line in output_lines[-5:]):
                        st.success("ETL pipeline completed successfully!")
                    elif any("❌" in line for line in output_lines[-5:]):
                        st.error("ETL pipeline failed. Check output above.")
                    else:
                        st.info("Execution finished. Review output above.")

                    if rerun_params:
                        del st.session_state.pm_rerun_params

                except Exception as e:
                    st.error(f"Error executing ETL pipeline: {format_sql_error(e)}")

            if len(output_lines) > 50:
                with st.expander("View Full Output", expanded=False):
                    st.code("\n".join(output_lines), language="text")

    # ── DB Import Only ──
    else:
        st.markdown("Runs `generic_import.py` for an existing JSON dataset (no API call).")

        try:
            active_configs = get_active_configs_for_execution()
        except Exception:
            active_configs = []

        if not active_configs:
            st.warning("No active import configurations found.")
        else:
            config_map = {c['config_name']: c['config_id'] for c in active_configs}
            config_names = list(config_map.keys())

            # Pre-fill from rerun_params
            default_cfg_idx = 0
            if rerun_params and rerun_params.get('mode') == 'db_import_only':
                target = rerun_params.get('config_name', '')
                if target in config_names:
                    default_cfg_idx = config_names.index(target)

            selected_config_name = st.selectbox(
                "Config",
                options=config_names,
                index=default_cfg_idx,
                key="pm_run_import_config",
            )

            import_run_date = st.date_input(
                "Date",
                value=date.today(),
                key="pm_run_import_date",
                help="Date passed to generic_import.py --date",
            )

            import_dry_run = st.checkbox("Dry Run", key="pm_run_import_dry_run",
                                          help="Run without writing to the database")

            if st.button("▶️ Run DB Import", type="primary", key="pm_run_import_btn"):
                config_id = config_map[selected_config_name]
                st.markdown("---")
                st.markdown(f"**Running:** `generic_import.py` — config `{selected_config_name}`"
                            + f" — date `{import_run_date}`"
                            + (" *(dry-run)*" if import_dry_run else ""))

                output_container = st.empty()
                output_lines = []

                with st.spinner("Executing DB import..."):
                    try:
                        for line in execute_import_job(
                            config_id=config_id,
                            run_date=import_run_date,
                            dry_run=import_dry_run,
                            timeout=300,
                        ):
                            output_lines.append(line)
                            output_container.code("\n".join(output_lines[-50:]), language="text")

                        if any("✅" in line for line in output_lines[-5:]):
                            st.success("DB import completed successfully!")
                        elif any("❌" in line for line in output_lines[-5:]):
                            st.error("DB import failed. Check output above.")
                        else:
                            st.info("Execution finished. Review output above.")

                        if rerun_params:
                            del st.session_state.pm_rerun_params

                    except Exception as e:
                        st.error(f"Error executing DB import: {format_sql_error(e)}")

                if len(output_lines) > 50:
                    with st.expander("View Full Output", expanded=False):
                        st.code("\n".join(output_lines), language="text")


# ─── Job Steps Dialog ─────────────────────────────────────────────────────────

@st.dialog("Job Steps", width="large")
def show_steps_dialog(run):
    jobrunid = run['jobrunid']
    st.markdown(f"**Job:** `{run['job_name']}`")
    st.markdown(f"**Config:** `{run['config_name']}`  |  **Status:** {_status_badge(run['status'])}")
    if run.get('run_uuid'):
        st.caption(f"Run UUID: {run['run_uuid']}")
    st.divider()

    try:
        steps = get_job_run_steps(jobrunid)
    except Exception as e:
        st.error(f"Error loading steps: {format_sql_error(e)}")
        return

    if not steps:
        st.info("No steps recorded for this run.")
        return

    for step in steps:
        s_status = step.get('status', 'unknown')
        s_icon = STATUS_ICON.get(s_status, '❓')
        s_name = step.get('display_name', step.get('step_name', ''))
        s_step_name = step.get('step_name', '')
        s_runtime = _fmt_duration(step.get('step_runtime'))
        s_in = step.get('records_in')
        s_out = step.get('records_out')
        s_msg = step.get('message') or ''
        s_uuid = step.get('log_run_uuid')

        with st.container(border=True):
            sc1, sc2, sc3, sc4 = st.columns([1, 4, 2, 1])
            with sc1:
                st.markdown(f"### {s_icon}")
            with sc2:
                st.markdown(f"**{s_name}**")
                rec_str = ""
                if s_in is not None:
                    rec_str += f"In: {s_in}"
                if s_out is not None:
                    rec_str += f"  Out: {s_out}"
                if rec_str:
                    st.caption(rec_str)
                if s_msg:
                    st.caption(s_msg)
            with sc3:
                st.markdown(f"⏱ {s_runtime}")
                st.caption(_status_badge(s_status))
            with sc4:
                if s_status == 'failed':
                    if s_step_name == 'data_collection':
                        if st.button("↩️", key=f"rerun_dc_{step['jobstepid']}",
                                     help="Re-run full ETL pipeline"):
                            st.session_state.pm_rerun_params = {
                                'mode': 'full_etl',
                                'job_name': run['job_name'],
                            }
                            st.rerun()
                    elif s_step_name == 'db_import':
                        if st.button("↩️", key=f"rerun_di_{step['jobstepid']}",
                                     help="Re-run DB import only"):
                            st.session_state.pm_rerun_params = {
                                'mode': 'db_import_only',
                                'config_name': run['config_name'],
                            }
                            st.rerun()

            if s_uuid:
                with st.expander("View Import Logs", expanded=False):
                    try:
                        logs = get_step_logs(s_uuid)
                        if logs:
                            for log in logs:
                                ts = format_datetime(log.get('timestamp')) if log.get('timestamp') else ''
                                rt = f" ({log['stepruntime']:.2f}s)" if log.get('stepruntime') else ''
                                step_no = log.get('stepcounter', '')
                                msg = log.get('message', '')
                                st.text(f"[{step_no}] {ts}{rt}  {msg}")
                        else:
                            st.caption("No log entries found.")
                    except Exception as e:
                        st.error(f"Error loading logs: {format_sql_error(e)}")


if 'pm_selected_run' in st.session_state:
    show_steps_dialog(st.session_state.pm_selected_run)
    del st.session_state.pm_selected_run

# ─── Footer ───────────────────────────────────────────────────────────────────

st.divider()
st.caption("Pipeline Monitor — tracks ETL job runs (dba.tjobrun) and their steps (dba.tjobstep)")

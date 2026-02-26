"""Pipeline Monitor - hierarchical job run and step execution view."""

import streamlit as st
from datetime import datetime
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

# ─── Filters ──────────────────────────────────────────────────────────────────

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

# ─── Run List ─────────────────────────────────────────────────────────────────

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
        s_runtime = _fmt_duration(step.get('step_runtime'))
        s_in = step.get('records_in')
        s_out = step.get('records_out')
        s_msg = step.get('message') or ''
        s_uuid = step.get('log_run_uuid')

        with st.container(border=True):
            sc1, sc2, sc3 = st.columns([1, 4, 2])
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

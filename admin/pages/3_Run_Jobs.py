"""Job Execution Page - Run ETL Import Jobs"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from components.notifications import show_success, show_error, show_info, show_warning
from services.job_execution_service import (
    get_active_configs_for_execution,
    execute_import_job,
    validate_import_config,
    get_recent_job_runs,
    get_job_output
)
from utils.db_helpers import format_sql_error
from utils.formatters import format_timestamp, format_duration
from utils.ui_helpers import load_custom_css, add_page_header, render_empty_state

# Page configuration
st.set_page_config(
    page_title="Run Jobs - Tangerine Admin",
    page_icon="▶️",
    layout="wide"
)

# Load custom CSS
load_custom_css()

# Page header
add_page_header(
    title="Run Import Jobs",
    subtitle="Execute ETL import jobs and monitor their progress in real-time.",
    icon="▶️"
)

# Create tabs
tab1, tab2 = st.tabs(["▶️ Execute Job", "📜 Job History"])

# ============================================================================
# TAB 1: EXECUTE JOB
# ============================================================================
with tab1:
    st.subheader("Execute Import Job")

    try:
        # Get active configurations
        active_configs = get_active_configs_for_execution()

        if not active_configs:
            show_warning("⚠️ No active import configurations found. Create and activate a configuration first.")
            st.info("💡 Navigate to **Import Configs** → **Create New** to set up an import configuration.")
            st.stop()

        # Configuration selection
        st.markdown("### Configuration Selection")

        config_options = {
            f"{c['config_id']} - {c['config_name']} ({c['file_type']})": c['config_id']
            for c in active_configs
        }

        selected_config_str = st.selectbox(
            "Select Import Configuration *",
            options=list(config_options.keys()),
            help="Choose which import configuration to execute"
        )

        selected_config_id = config_options[selected_config_str]

        # Find the selected config details
        selected_config = next(c for c in active_configs if c['config_id'] == selected_config_id)

        # Display configuration details
        with st.expander("📋 Configuration Details", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Type", selected_config['file_type'])
                st.metric("Data Source", selected_config['datasource'])
            with col2:
                st.metric("Dataset Type", selected_config['datasettype'])
                st.metric("Target Table", selected_config['target_table'])
            with col3:
                st.metric("Strategy", selected_config.get('strategy_name', 'N/A'))

        st.divider()

        # Execution parameters
        st.markdown("### Execution Parameters")

        col1, col2 = st.columns(2)

        with col1:
            run_date = st.date_input(
                "Run Date",
                value=date.today(),
                help="Date to use for the import (default: today)"
            )

        with col2:
            dry_run = st.checkbox(
                "Dry Run Mode",
                value=False,
                help="If checked, the job will run without writing to the database (validation only)"
            )

        if dry_run:
            show_info("ℹ️ **Dry Run Mode:** The job will process files and validate data but will NOT write to the database.")

        st.divider()

        # Execution button
        st.markdown("### Execute")

        if st.button("▶️ Run Import Job", type="primary", use_container_width=True):
            # Validate configuration
            is_valid, error_msg = validate_import_config(selected_config_id)

            if not is_valid:
                show_error(error_msg)
                st.stop()

            # Display execution info
            st.markdown("---")
            st.markdown("#### 📊 Job Execution Output")

            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.metric("Configuration", selected_config['config_name'])
            with info_col2:
                st.metric("Run Date", run_date.strftime("%Y-%m-%d"))
            with info_col3:
                st.metric("Mode", "Dry Run" if dry_run else "Production")

            st.markdown("---")

            # Create output container
            output_container = st.empty()
            output_lines = []

            # Execute job and stream output
            with st.spinner("🔄 Executing import job..."):
                try:
                    for line in execute_import_job(
                        config_id=selected_config_id,
                        run_date=run_date,
                        dry_run=dry_run,
                        timeout=300  # 5 minutes
                    ):
                        output_lines.append(line)
                        # Update output display (last 50 lines)
                        display_lines = output_lines[-50:]
                        output_container.code("\n".join(display_lines), language="text")

                    # Job completed
                    if any("✅" in line for line in output_lines[-5:]):
                        show_success("✅ Import job completed successfully!")
                        st.balloons()
                    elif any("❌" in line for line in output_lines[-5:]):
                        show_error("❌ Import job failed. Check the output above for details.")
                    else:
                        show_info("Job execution finished. Review output above.")

                except Exception as e:
                    show_error(f"Error executing job: {format_sql_error(e)}")

                # Show full output in expander
                if len(output_lines) > 50:
                    with st.expander("📄 View Full Output", expanded=False):
                        st.code("\n".join(output_lines), language="text")

    except Exception as e:
        show_error(f"Error loading configurations: {format_sql_error(e)}")


# ============================================================================
# TAB 2: JOB HISTORY
# ============================================================================
with tab2:
    st.subheader("Recent Job Runs")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        history_limit = st.selectbox(
            "Show Last",
            options=[10, 25, 50, 100],
            index=0,
            key="history_limit"
        )
    with col2:
        if st.button("🔄 Refresh History", key="refresh_history"):
            st.rerun()

    try:
        # Ensure limit is an integer
        limit_value = int(history_limit) if history_limit else 10
        recent_runs = get_recent_job_runs(limit=limit_value)

        if recent_runs:
            # Convert to DataFrame
            df = pd.DataFrame(recent_runs)

            # Format columns
            if 'starttime' in df.columns:
                df['starttime'] = df['starttime'].apply(
                    lambda x: format_timestamp(x) if pd.notna(x) else 'N/A'
                )

            if 'total_runtime' in df.columns:
                df['total_runtime'] = df['total_runtime'].apply(
                    lambda x: format_duration(x) if pd.notna(x) else 'N/A'
                )

            # Add status indicators
            if 'status' in df.columns:
                df['status'] = df['status'].apply(
                    lambda x: f"✅ {x}" if x == 'Success' else (f"❌ {x}" if x == 'Failed' else f"⏳ {x}")
                )

            # Select columns to display
            display_columns = ['run_uuid', 'processtype', 'starttime', 'total_steps', 'status', 'total_runtime']
            display_columns = [col for col in display_columns if col in df.columns]

            st.dataframe(
                df[display_columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'run_uuid': st.column_config.TextColumn('Run UUID', width="large"),
                    'processtype': st.column_config.TextColumn('Process', width="medium"),
                    'starttime': st.column_config.TextColumn('Start Time', width="medium"),
                    'total_steps': st.column_config.NumberColumn('Steps', width="small"),
                    'status': st.column_config.TextColumn('Status', width="small"),
                    'total_runtime': st.column_config.TextColumn('Runtime', width="small")
                }
            )

            st.caption(f"Showing {len(recent_runs)} recent job run(s)")

            # View detailed output
            st.divider()
            st.markdown("#### 🔍 View Detailed Output")

            run_uuid_input = st.text_input(
                "Enter Run UUID",
                help="Copy a run UUID from the table above to view its detailed output"
            )

            if run_uuid_input and st.button("📄 Load Output", key="load_output"):
                try:
                    job_output = get_job_output(run_uuid_input)

                    if job_output:
                        st.markdown(f"**Output for Run: `{run_uuid_input}`**")

                        # Display as formatted log
                        output_lines = []
                        for entry in job_output:
                            step = entry.get('stepcounter', '?')
                            message = entry.get('message', '')
                            runtime = entry.get('stepruntime', 0)
                            output_lines.append(f"[Step {step}] [{runtime:.2f}s] {message}")

                        st.code("\n".join(output_lines), language="text")

                        st.caption(f"Showing {len(job_output)} log entries")
                    else:
                        show_warning(f"No output found for run UUID: {run_uuid_input}")

                except Exception as e:
                    show_error(f"Error loading job output: {format_sql_error(e)}")

        else:
            show_info("No recent job runs found. Execute an import job to see history here.")

    except Exception as e:
        show_error(f"Error loading job history: {format_sql_error(e)}")


# Footer
st.divider()
st.caption("💡 **Tips:**")
st.caption("• Use **Dry Run Mode** to test configurations without writing to the database")
st.caption("• Job execution timeout is 5 minutes - adjust for large imports if needed")
st.caption("• Check **Job History** to review past runs and troubleshoot issues")

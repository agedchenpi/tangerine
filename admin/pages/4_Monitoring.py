"""System Monitoring Page - View logs, datasets, and statistics"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from components.notifications import show_success, show_error, show_info, show_warning
from services.monitoring_service import (
    get_logs,
    get_distinct_process_types,
    get_datasets,
    get_dataset_sources,
    get_dataset_types_from_datasets,
    get_statistics_metrics,
    get_jobs_per_day,
    get_process_type_distribution,
    get_runtime_statistics,
    export_logs_to_csv
)
from utils.db_helpers import format_sql_error
from utils.formatters import format_datetime, format_duration, format_boolean

# Page configuration
st.set_page_config(
    page_title="Monitoring - Tangerine Admin",
    page_icon="📊",
    layout="wide"
)

st.title("📊 System Monitoring")
st.markdown("Monitor ETL pipeline activity, view logs, browse datasets, and analyze system statistics.")

st.divider()

# Create tabs
tab1, tab2, tab3 = st.tabs(["📜 Logs", "📦 Datasets", "📈 Statistics"])

# ============================================================================
# TAB 1: LOGS
# ============================================================================
with tab1:
    st.subheader("ETL Process Logs")
    st.markdown("View and filter ETL process execution logs from `dba.tlogentry`")

    # Filters
    st.markdown("### Filters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        time_range_options = {
            "Last 1 hour": 1,
            "Last 6 hours": 6,
            "Last 24 hours": 24,
            "Last 7 days": 168,
            "Last 30 days": 720,
            "All time": None
        }
        time_range_label = st.selectbox(
            "Time Range",
            options=list(time_range_options.keys()),
            index=2,  # Default to 24 hours
            key="logs_time_range"
        )
        time_range_hours = time_range_options[time_range_label]

    with col2:
        try:
            process_types = ["All"] + get_distinct_process_types()
        except Exception as e:
            show_error(f"Error loading process types: {format_sql_error(e)}")
            process_types = ["All"]

        selected_process = st.selectbox(
            "Process Type",
            options=process_types,
            index=0,
            key="logs_process_type"
        )
        process_type_filter = None if selected_process == "All" else selected_process

    with col3:
        run_uuid_filter = st.text_input(
            "Run UUID (optional)",
            help="Filter logs by specific run UUID",
            key="logs_run_uuid"
        )
        run_uuid_filter = run_uuid_filter.strip() if run_uuid_filter else None

    with col4:
        limit_options = [50, 100, 250, 500, 1000]
        limit = st.selectbox(
            "Max Results",
            options=limit_options,
            index=1,  # Default to 100
            key="logs_limit"
        )

    # Fetch and refresh buttons
    col1, col2 = st.columns([1, 5])
    with col1:
        fetch_logs = st.button("🔍 Fetch Logs", type="primary", key="fetch_logs_btn")
    with col2:
        if st.button("🔄 Refresh", key="refresh_logs_btn"):
            st.rerun()

    st.divider()

    # Fetch logs
    if fetch_logs or 'logs_data' not in st.session_state:
        try:
            with st.spinner("Fetching logs..."):
                logs = get_logs(
                    time_range_hours=time_range_hours,
                    process_type=process_type_filter,
                    run_uuid=run_uuid_filter,
                    limit=limit
                )
                st.session_state.logs_data = logs
        except Exception as e:
            show_error(f"Error fetching logs: {format_sql_error(e)}")
            st.session_state.logs_data = []

    # Display logs
    if 'logs_data' in st.session_state:
        logs = st.session_state.logs_data

        if logs:
            st.markdown(f"### 📋 Results ({len(logs)} log entries)")

            # Convert to DataFrame
            df = pd.DataFrame(logs)

            # Format timestamp
            if 'timestamp' in df.columns:
                df['timestamp'] = df['timestamp'].apply(
                    lambda x: format_datetime(x) if pd.notna(x) else 'N/A'
                )

            # Format runtime
            if 'stepruntime' in df.columns:
                df['stepruntime'] = df['stepruntime'].apply(
                    lambda x: f"{x:.2f}s" if pd.notna(x) else 'N/A'
                )

            # Display table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'logentryid': st.column_config.NumberColumn('ID', width="small"),
                    'run_uuid': st.column_config.TextColumn('Run UUID', width="large"),
                    'processtype': st.column_config.TextColumn('Process', width="medium"),
                    'stepcounter': st.column_config.NumberColumn('Step', width="small"),
                    'message': st.column_config.TextColumn('Message', width="large"),
                    'stepruntime': st.column_config.TextColumn('Runtime', width="small"),
                    'timestamp': st.column_config.TextColumn('Timestamp', width="medium")
                }
            )

            # Export to CSV
            st.divider()
            st.markdown("### 💾 Export")

            if st.button("📥 Download as CSV", key="export_csv_btn"):
                try:
                    csv_data = export_logs_to_csv(logs)
                    st.download_button(
                        label="⬇️ Save CSV File",
                        data=csv_data,
                        file_name=f"tangerine_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_csv_btn"
                    )
                    show_success("CSV file ready for download!")
                except Exception as e:
                    show_error(f"Error generating CSV: {format_sql_error(e)}")

        else:
            show_info("No logs found matching the specified filters.")
            st.info("💡 Try adjusting your filters or expanding the time range.")


# ============================================================================
# TAB 2: DATASETS
# ============================================================================
with tab2:
    st.subheader("Dataset Records")
    st.markdown("Browse and filter dataset records from `dba.tdataset`")

    # Filters
    st.markdown("### Filters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        try:
            datasources = ["All"] + get_dataset_sources()
        except Exception as e:
            show_error(f"Error loading datasources: {format_sql_error(e)}")
            datasources = ["All"]

        selected_datasource = st.selectbox(
            "Data Source",
            options=datasources,
            index=0,
            key="datasets_datasource"
        )
        datasource_filter = None if selected_datasource == "All" else selected_datasource

    with col2:
        try:
            datasettypes = ["All"] + get_dataset_types_from_datasets()
        except Exception as e:
            show_error(f"Error loading dataset types: {format_sql_error(e)}")
            datasettypes = ["All"]

        selected_datasettype = st.selectbox(
            "Dataset Type",
            options=datasettypes,
            index=0,
            key="datasets_datasettype"
        )
        datasettype_filter = None if selected_datasettype == "All" else selected_datasettype

    with col3:
        date_from = st.date_input(
            "Created From",
            value=date.today() - timedelta(days=30),
            key="datasets_date_from"
        )

    with col4:
        date_to = st.date_input(
            "Created To",
            value=date.today(),
            key="datasets_date_to"
        )

    # Limit and fetch
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        dataset_limit = st.selectbox(
            "Max Results",
            options=[50, 100, 250, 500],
            index=1,
            key="datasets_limit"
        )

    with col2:
        fetch_datasets = st.button("🔍 Fetch Datasets", type="primary", key="fetch_datasets_btn")

    st.divider()

    # Fetch datasets
    if fetch_datasets or 'datasets_data' not in st.session_state:
        try:
            with st.spinner("Fetching datasets..."):
                datasets = get_datasets(
                    datasource=datasource_filter,
                    datasettype=datasettype_filter,
                    date_from=datetime.combine(date_from, datetime.min.time()),
                    date_to=datetime.combine(date_to, datetime.max.time()),
                    limit=dataset_limit
                )
                st.session_state.datasets_data = datasets
        except Exception as e:
            show_error(f"Error fetching datasets: {format_sql_error(e)}")
            st.session_state.datasets_data = []

    # Display datasets
    if 'datasets_data' in st.session_state:
        datasets = st.session_state.datasets_data

        if datasets:
            st.markdown(f"### 📦 Results ({len(datasets)} datasets)")

            # Convert to DataFrame
            df = pd.DataFrame(datasets)

            # Format dates
            date_columns = ['createddate', 'efffromdate', 'effthrudate']
            for col in date_columns:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: format_datetime(x) if pd.notna(x) else 'N/A'
                    )

            # Format boolean
            if 'isactive' in df.columns:
                df['isactive'] = df['isactive'].apply(
                    lambda x: '✅ Active' if x else '❌ Inactive'
                )

            # Display table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'datasetid': st.column_config.NumberColumn('ID', width="small"),
                    'label': st.column_config.TextColumn('Label', width="medium"),
                    'datasource': st.column_config.TextColumn('Source', width="small"),
                    'datasettype': st.column_config.TextColumn('Type', width="small"),
                    'createddate': st.column_config.TextColumn('Created', width="medium"),
                    'status': st.column_config.TextColumn('Status', width="small"),
                    'efffromdate': st.column_config.TextColumn('Eff From', width="medium"),
                    'effthrudate': st.column_config.TextColumn('Eff Thru', width="medium"),
                    'isactive': st.column_config.TextColumn('Active', width="small")
                }
            )

            st.caption(f"Showing {len(datasets)} dataset(s)")

        else:
            show_info("No datasets found matching the specified filters.")
            st.info("💡 Try adjusting your filters or expanding the date range.")


# ============================================================================
# TAB 3: STATISTICS
# ============================================================================
with tab3:
    st.subheader("System Statistics")
    st.markdown("View system-wide metrics and performance trends")

    # Refresh button
    if st.button("🔄 Refresh Statistics", key="refresh_stats_btn"):
        st.rerun()

    st.divider()

    # Fetch metrics
    try:
        with st.spinner("Loading statistics..."):
            metrics = get_statistics_metrics()

        # Display metrics in cards
        st.markdown("### 📊 Key Metrics")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="Total Logs (24h)",
                value=f"{metrics['total_logs_24h']:,}",
                help="Number of log entries in the last 24 hours"
            )
            st.metric(
                label="Unique Processes (24h)",
                value=metrics['unique_processes'],
                help="Number of distinct process types in the last 24 hours"
            )

        with col2:
            st.metric(
                label="Avg Step Runtime",
                value=f"{metrics['avg_runtime']}s",
                help="Average step runtime in the last 24 hours"
            )
            st.metric(
                label="Datasets (30d)",
                value=f"{metrics['total_datasets_30d']:,}",
                help="Number of datasets created in the last 30 days"
            )

        with col3:
            st.metric(
                label="Active Datasets",
                value=f"{metrics['total_active_datasets']:,}",
                help="Number of currently active datasets"
            )
            st.metric(
                label="Active Import Configs",
                value=metrics['total_active_configs'],
                help="Number of active import configurations"
            )

        st.divider()

        # Charts
        st.markdown("### 📈 Trends and Distribution")

        # Jobs per day chart
        try:
            jobs_per_day = get_jobs_per_day(days=30)

            if jobs_per_day:
                st.markdown("#### Import Jobs Per Day (Last 30 Days)")

                df_jobs = pd.DataFrame(jobs_per_day)
                df_jobs['job_date'] = pd.to_datetime(df_jobs['job_date'])

                st.line_chart(
                    df_jobs.set_index('job_date')['job_count'],
                    use_container_width=True
                )
                st.caption(f"Total jobs in period: {df_jobs['job_count'].sum()}")
            else:
                show_info("No job data available for the last 30 days.")

        except Exception as e:
            show_error(f"Error loading jobs per day: {format_sql_error(e)}")

        st.divider()

        # Process type distribution
        try:
            process_dist = get_process_type_distribution(days=30)

            if process_dist:
                st.markdown("#### Process Type Distribution (Last 30 Days)")

                df_process = pd.DataFrame(process_dist)

                st.bar_chart(
                    df_process.set_index('processtype')['run_count'],
                    use_container_width=True
                )

                # Show as table too
                with st.expander("📋 View Data Table", expanded=False):
                    st.dataframe(
                        df_process,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'processtype': st.column_config.TextColumn('Process Type'),
                            'run_count': st.column_config.NumberColumn('Run Count')
                        }
                    )
            else:
                show_info("No process distribution data available.")

        except Exception as e:
            show_error(f"Error loading process distribution: {format_sql_error(e)}")

        st.divider()

        # Runtime statistics
        try:
            runtime_stats = get_runtime_statistics(days=7)

            if runtime_stats:
                st.markdown("#### Runtime Statistics by Process Type (Last 7 Days)")

                df_runtime = pd.DataFrame(runtime_stats)

                # Format runtime values
                df_runtime['avg_runtime'] = df_runtime['avg_runtime'].apply(lambda x: round(x, 2))
                df_runtime['min_runtime'] = df_runtime['min_runtime'].apply(lambda x: round(x, 2))
                df_runtime['max_runtime'] = df_runtime['max_runtime'].apply(lambda x: round(x, 2))

                st.dataframe(
                    df_runtime,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'processtype': st.column_config.TextColumn('Process Type', width="medium"),
                        'step_count': st.column_config.NumberColumn('Steps', width="small"),
                        'avg_runtime': st.column_config.NumberColumn('Avg (s)', width="small", format="%.2f"),
                        'min_runtime': st.column_config.NumberColumn('Min (s)', width="small", format="%.2f"),
                        'max_runtime': st.column_config.NumberColumn('Max (s)', width="small", format="%.2f")
                    }
                )
            else:
                show_info("No runtime statistics available.")

        except Exception as e:
            show_error(f"Error loading runtime statistics: {format_sql_error(e)}")

    except Exception as e:
        show_error(f"Error loading statistics: {format_sql_error(e)}")


# Footer
st.divider()
st.caption("💡 **Tips:**")
st.caption("• Use **Logs** tab to troubleshoot ETL job execution issues")
st.caption("• Use **Datasets** tab to track data lineage and dataset status")
st.caption("• Use **Statistics** tab to monitor system health and performance trends")

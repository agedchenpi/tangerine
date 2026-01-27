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
    export_logs_to_csv,
    get_dataset_by_id,
    create_dataset,
    update_dataset,
    delete_dataset,
    archive_dataset,
    get_dataset_dependencies,
    get_all_data_statuses,
    preview_log_purge,
    purge_logs,
    export_logs_for_purge,
    get_log_statistics
)
from services.reference_data_service import list_datasources, list_datasettypes
from utils.db_helpers import format_sql_error
from utils.formatters import format_datetime, format_duration, format_boolean
from utils.ui_helpers import load_custom_css, add_page_header, render_empty_state, with_loading

# Load custom CSS
load_custom_css()

# Page header
add_page_header("System Monitoring", icon="📊")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📜 Logs", "📦 View Datasets", "🔧 Manage Datasets", "📈 Statistics"])

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

    # LOG PURGE SECTION
    st.divider()
    st.markdown("### 🗑️ Log Purge")
    st.markdown("Delete old logs to prevent database growth. **Warning:** This action is permanent!")

    with st.expander("📊 Log Statistics", expanded=False):
        try:
            log_stats = get_log_statistics()
            if log_stats:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Logs", f"{log_stats.get('total_logs', 0):,}")
                with col2:
                    st.metric("Total Runs", f"{log_stats.get('total_runs', 0):,}")
                with col3:
                    st.metric("Last 7 Days", f"{log_stats.get('logs_last_7_days', 0):,}")
                with col4:
                    st.metric("Last 30 Days", f"{log_stats.get('logs_last_30_days', 0):,}")

                if log_stats.get('oldest_log'):
                    st.caption(f"Oldest log: {format_datetime(log_stats['oldest_log'])}")
                if log_stats.get('newest_log'):
                    st.caption(f"Newest log: {format_datetime(log_stats['newest_log'])}")
        except Exception as e:
            show_error(f"Error loading log statistics: {format_sql_error(e)}")

    col1, col2 = st.columns([2, 1])

    with col1:
        days_old = st.number_input(
            "Delete logs older than (days)",
            min_value=1,
            max_value=730,
            value=90,
            help="Logs older than this many days will be permanently deleted"
        )

    with col2:
        st.markdown("&nbsp;")  # Spacer
        if st.button("🔍 Preview Purge", key="preview_purge_btn"):
            try:
                preview = preview_log_purge(days_old)
                if preview and preview.get('log_count', 0) > 0:
                    show_warning(f"⚠️ **{preview['log_count']:,} logs** would be deleted")
                    st.caption(f"Date range: {format_datetime(preview['oldest_log'])} to {format_datetime(preview['newest_log'])}")
                    st.session_state.purge_preview_done = True
                    st.session_state.purge_days = days_old
                else:
                    show_info(f"No logs found older than {days_old} days")
                    st.session_state.purge_preview_done = False
            except Exception as e:
                show_error(f"Error previewing purge: {format_sql_error(e)}")
                st.session_state.purge_preview_done = False

    # Show purge options if preview was done
    if st.session_state.get('purge_preview_done', False) and st.session_state.get('purge_days') == days_old:
        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📁 Archive Before Delete (Optional)")
            if st.button("📥 Export Logs to CSV", key="export_purge_logs"):
                try:
                    logs_to_purge = export_logs_for_purge(days_old)
                    if logs_to_purge:
                        csv_data = export_logs_to_csv(logs_to_purge)
                        st.download_button(
                            label="⬇️ Download Archive CSV",
                            data=csv_data,
                            file_name=f"tangerine_logs_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_purge_csv"
                        )
                        show_success(f"Archive ready! {len(logs_to_purge):,} logs exported to CSV")
                    else:
                        show_info("No logs to export")
                except Exception as e:
                    show_error(f"Error exporting logs: {format_sql_error(e)}")

        with col2:
            st.markdown("#### 🗑️ Confirm Deletion")
            confirm_purge = st.checkbox(
                f"I confirm I want to permanently delete logs older than {days_old} days",
                key="confirm_purge_checkbox"
            )

            if confirm_purge:
                if st.button("🗑️ DELETE LOGS PERMANENTLY", type="primary", key="execute_purge_btn"):
                    try:
                        deleted_count = purge_logs(days_old)
                        show_success(f"✅ Successfully deleted {deleted_count:,} log entries!")
                        st.toast(f"Deleted {deleted_count:,} logs", icon="🗑️")
                        st.session_state.purge_preview_done = False
                        st.rerun()
                    except Exception as e:
                        show_error(f"Error purging logs: {format_sql_error(e)}")


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


# ============================================================================
# TAB 4: DATASET MANAGEMENT
# ============================================================================
with tab4:
    st.subheader("Dataset Management")
    st.markdown("Create, edit, archive, or delete dataset records.")

    # Sub-tabs for different operations
    ds_tab1, ds_tab2, ds_tab3, ds_tab4 = st.tabs(["➕ Create", "✏️ Edit", "📦 Archive", "🗑️ Delete"])

    # CREATE DATASET
    with ds_tab1:
        st.markdown("#### Create New Dataset")

        with st.form("create_dataset_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                label = st.text_input(
                    "Dataset Label",
                    max_chars=100,
                    help="Unique identifier for this dataset"
                )
                datasetdate = st.date_input(
                    "Dataset Date",
                    value=date.today(),
                    help="Date associated with this dataset"
                )

            with col2:
                # Get datasources
                try:
                    datasources = list_datasources()
                    ds_options = {f"{ds['datasourceid']} - {ds['sourcename']}": ds['datasourceid'] for ds in datasources}
                    if not ds_options:
                        st.warning("No datasources available. Create one in Reference Data first.")
                        datasourceid = None
                    else:
                        selected_ds = st.selectbox("Data Source", options=list(ds_options.keys()))
                        datasourceid = ds_options[selected_ds]
                except Exception as e:
                    st.error(f"Error loading datasources: {format_sql_error(e)}")
                    datasourceid = None

                # Get dataset types
                try:
                    datasettypes = list_datasettypes()
                    dt_options = {f"{dt['datasettypeid']} - {dt['typename']}": dt['datasettypeid'] for dt in datasettypes}
                    if not dt_options:
                        st.warning("No dataset types available. Create one in Reference Data first.")
                        datasettypeid = None
                    else:
                        selected_dt = st.selectbox("Dataset Type", options=list(dt_options.keys()))
                        datasettypeid = dt_options[selected_dt]
                except Exception as e:
                    st.error(f"Error loading dataset types: {format_sql_error(e)}")
                    datasettypeid = None

            # Get status options
            try:
                statuses = get_all_data_statuses()
                status_options = {f"{s['datastatusid']} - {s['statusname']}": s['datastatusid'] for s in statuses}
                if status_options:
                    selected_status = st.selectbox("Status", options=list(status_options.keys()), index=0)
                    datastatusid = status_options[selected_status]
                else:
                    datastatusid = 1  # Default to Active
            except Exception as e:
                st.error(f"Error loading statuses: {format_sql_error(e)}")
                datastatusid = 1

            if st.form_submit_button("➕ Create Dataset", type="primary"):
                if not label:
                    show_error("Dataset label is required")
                elif not datasourceid or not datasettypeid:
                    show_error("Datasource and Dataset Type are required")
                else:
                    try:
                        new_id = create_dataset(label, datasetdate, datasourceid, datasettypeid, datastatusid)
                        show_success(f"✅ Dataset '{label}' created successfully! (ID: {new_id})")
                        st.toast("Dataset created!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        show_error(f"Failed to create dataset: {format_sql_error(e)}")

    # EDIT DATASET
    with ds_tab2:
        st.markdown("#### Edit Dataset")

        # Show success message if exists
        if 'dataset_update_success' in st.session_state:
            show_success(st.session_state.dataset_update_success)
            del st.session_state.dataset_update_success

        try:
            # Get datasets for selection
            datasets = get_datasets(limit=500)

            if datasets:
                dataset_options = {
                    f"{d['datasetid']} - {d['label']} ({d['datasettype']})": d['datasetid']
                    for d in datasets
                }

                selected_dataset_str = st.selectbox(
                    "Select Dataset to Edit",
                    options=list(dataset_options.keys()),
                    key="edit_dataset_select"
                )

                selected_dataset_id = dataset_options[selected_dataset_str]
                dataset_to_edit = get_dataset_by_id(selected_dataset_id)

                if dataset_to_edit:
                    st.divider()

                    # Show current info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Dataset ID", dataset_to_edit['datasetid'])
                    with col2:
                        st.metric("Current Status", dataset_to_edit['status'])
                    with col3:
                        st.metric("Active", "✅ Yes" if dataset_to_edit['isactive'] else "❌ No")

                    st.divider()

                    # Edit form
                    with st.form("edit_dataset_form"):
                        col1, col2 = st.columns(2)

                        with col1:
                            new_label = st.text_input("Dataset Label", value=dataset_to_edit['label'], max_chars=100)
                            new_datasetdate = st.date_input(
                                "Dataset Date",
                                value=datetime.strptime(str(dataset_to_edit['datasetdate']), '%Y-%m-%d').date()
                            )

                        with col2:
                            # Datasources
                            datasources = list_datasources()
                            ds_options = {f"{ds['datasourceid']} - {ds['sourcename']}": ds['datasourceid'] for ds in datasources}
                            current_ds_key = f"{dataset_to_edit['datasourceid']} - {dataset_to_edit['datasource']}"
                            new_datasourceid = ds_options[st.selectbox(
                                "Data Source",
                                options=list(ds_options.keys()),
                                index=list(ds_options.keys()).index(current_ds_key) if current_ds_key in ds_options else 0
                            )]

                            # Dataset types
                            datasettypes = list_datasettypes()
                            dt_options = {f"{dt['datasettypeid']} - {dt['typename']}": dt['datasettypeid'] for dt in datasettypes}
                            current_dt_key = f"{dataset_to_edit['datasettypeid']} - {dataset_to_edit['datasettype']}"
                            new_datasettypeid = dt_options[st.selectbox(
                                "Dataset Type",
                                options=list(dt_options.keys()),
                                index=list(dt_options.keys()).index(current_dt_key) if current_dt_key in dt_options else 0
                            )]

                        # Status and active flag
                        col3, col4 = st.columns(2)
                        with col3:
                            statuses = get_all_data_statuses()
                            status_options = {f"{s['datastatusid']} - {s['statusname']}": s['datastatusid'] for s in statuses}
                            current_status_key = f"{dataset_to_edit['datastatusid']} - {dataset_to_edit['status']}"
                            new_datastatusid = status_options[st.selectbox(
                                "Status",
                                options=list(status_options.keys()),
                                index=list(status_options.keys()).index(current_status_key) if current_status_key in status_options else 0
                            )]

                        with col4:
                            new_isactive = st.checkbox("Is Active", value=dataset_to_edit['isactive'])

                        if st.form_submit_button("💾 Update Dataset", type="primary"):
                            try:
                                update_dataset(
                                    selected_dataset_id,
                                    new_label,
                                    new_datasetdate,
                                    new_datasourceid,
                                    new_datasettypeid,
                                    new_datastatusid,
                                    new_isactive
                                )
                                st.session_state.dataset_update_success = f"✅ Dataset '{new_label}' updated successfully!"
                                st.rerun()
                            except Exception as e:
                                show_error(f"Failed to update dataset: {format_sql_error(e)}")
            else:
                show_info("No datasets available to edit.")

        except Exception as e:
            show_error(f"Error loading datasets: {format_sql_error(e)}")

    # ARCHIVE DATASET
    with ds_tab3:
        st.markdown("#### Archive Dataset")
        show_info("ℹ️ Archiving sets the dataset status to 'Inactive' and marks it as not active (soft delete).")

        try:
            datasets = get_datasets(limit=500)

            if datasets:
                active_datasets = [d for d in datasets if d.get('isactive', False)]

                if active_datasets:
                    dataset_options = {
                        f"{d['datasetid']} - {d['label']} ({d['datasettype']})": d['datasetid']
                        for d in active_datasets
                    }

                    selected_dataset_str = st.selectbox(
                        "Select Dataset to Archive",
                        options=list(dataset_options.keys()),
                        key="archive_dataset_select"
                    )

                    selected_dataset_id = dataset_options[selected_dataset_str]
                    dataset_to_archive = get_dataset_by_id(selected_dataset_id)

                    if dataset_to_archive:
                        st.divider()

                        # Show details
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text_input("Label", value=dataset_to_archive['label'], disabled=True)
                        with col2:
                            st.text_input("Type", value=dataset_to_archive['datasettype'], disabled=True)
                        with col3:
                            st.text_input("Source", value=dataset_to_archive['datasource'], disabled=True)

                        st.divider()

                        confirm = st.checkbox(
                            f"I confirm I want to archive dataset '{dataset_to_archive['label']}'",
                            key="archive_dataset_confirm"
                        )

                        if confirm:
                            if st.button("📦 Archive Dataset", type="primary", key="archive_dataset_button"):
                                try:
                                    archive_dataset(selected_dataset_id)
                                    show_success(f"Dataset '{dataset_to_archive['label']}' archived successfully")
                                    st.rerun()
                                except Exception as e:
                                    show_error(f"Failed to archive dataset: {format_sql_error(e)}")
                else:
                    show_info("No active datasets available to archive.")
            else:
                show_info("No datasets found.")

        except Exception as e:
            show_error(f"Error loading datasets: {format_sql_error(e)}")

    # DELETE DATASET
    with ds_tab4:
        st.markdown("#### Delete Dataset")
        show_warning("⚠️ **Warning:** Deletion is permanent. Datasets referenced by regression tests cannot be deleted.")

        try:
            datasets = get_datasets(limit=500)

            if datasets:
                dataset_options = {
                    f"{d['datasetid']} - {d['label']} ({d['datasettype']})": d['datasetid']
                    for d in datasets
                }

                selected_dataset_str = st.selectbox(
                    "Select Dataset to Delete",
                    options=list(dataset_options.keys()),
                    key="delete_dataset_select"
                )

                selected_dataset_id = dataset_options[selected_dataset_str]
                dataset_to_delete = get_dataset_by_id(selected_dataset_id)

                if dataset_to_delete:
                    st.divider()

                    # Show details
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Label", value=dataset_to_delete['label'], disabled=True)
                        st.text_input("Date", value=str(dataset_to_delete['datasetdate']), disabled=True)
                    with col2:
                        st.text_input("Type", value=dataset_to_delete['datasettype'], disabled=True)
                        st.text_input("Source", value=dataset_to_delete['datasource'], disabled=True)

                    # Check for dependencies
                    dependencies = get_dataset_dependencies(selected_dataset_id)

                    st.divider()

                    if dependencies:
                        show_error(f"❌ Cannot delete dataset '{dataset_to_delete['label']}' - it is referenced by:")
                        for dep in dependencies:
                            st.caption(f"• {dep['dependency_type']}: {dep['dependency_name']} (ID: {dep['dependency_id']})")
                        st.info("Delete or update the referencing records before deleting this dataset.")
                    else:
                        confirm = st.checkbox(
                            f"I confirm I want to permanently delete dataset '{dataset_to_delete['label']}'",
                            key="delete_dataset_confirm"
                        )

                        if confirm:
                            if st.button("🗑️ Delete Dataset Permanently", type="primary", key="delete_dataset_button"):
                                try:
                                    delete_dataset(selected_dataset_id)
                                    show_success(f"Dataset '{dataset_to_delete['label']}' deleted successfully")
                                    st.rerun()
                                except Exception as e:
                                    show_error(f"Failed to delete dataset: {format_sql_error(e)}")
            else:
                show_info("No datasets available to delete.")

        except Exception as e:
            show_error(f"Error loading datasets: {format_sql_error(e)}")


# Footer
st.divider()
st.caption("💡 **Tips:**")
st.caption("• Use **Logs** tab to troubleshoot ETL job execution issues")
st.caption("• Use **View Datasets** tab to track data lineage and dataset status")
st.caption("• Use **Manage Datasets** tab to create, edit, archive, or delete datasets")
st.caption("• Use **Statistics** tab to monitor system health and performance trends")

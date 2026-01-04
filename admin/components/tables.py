"""Reusable table components for displaying data"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional


def render_config_table(
    configs: List[Dict[str, Any]],
    show_columns: Optional[List[str]] = None,
    interactive: bool = True
) -> None:
    """
    Render import configurations as a table.

    Args:
        configs: List of configuration dictionaries
        show_columns: Optional list of columns to display (None = all)
        interactive: Whether to enable interactive features
    """
    if not configs:
        st.info("No configurations found.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(configs)

    # Default columns to display
    if show_columns is None:
        show_columns = [
            'config_id',
            'config_name',
            'file_type',
            'datasource',
            'datasettype',
            'strategy_name',
            'is_active',
            'target_table',
            'created_at'
        ]

    # Filter to available columns
    available_columns = [col for col in show_columns if col in df.columns]

    # Format datetime columns
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
    if 'last_modified_at' in df.columns:
        df['last_modified_at'] = pd.to_datetime(df['last_modified_at']).dt.strftime('%Y-%m-%d %H:%M')

    # Format boolean columns
    if 'is_active' in df.columns:
        df['is_active'] = df['is_active'].map({True: '✓ Active', False: '✗ Inactive'})
    if 'is_blob' in df.columns:
        df['is_blob'] = df['is_blob'].map({True: 'Yes', False: 'No'})

    # Display configuration
    column_config = {
        'config_id': st.column_config.NumberColumn('ID', width="small"),
        'config_name': st.column_config.TextColumn('Name', width="medium"),
        'file_type': st.column_config.TextColumn('Type', width="small"),
        'datasource': st.column_config.TextColumn('Source', width="medium"),
        'datasettype': st.column_config.TextColumn('Dataset Type', width="medium"),
        'strategy_name': st.column_config.TextColumn('Strategy', width="medium"),
        'is_active': st.column_config.TextColumn('Status', width="small"),
        'target_table': st.column_config.TextColumn('Target Table', width="medium"),
        'created_at': st.column_config.TextColumn('Created', width="medium"),
        'last_modified_at': st.column_config.TextColumn('Modified', width="medium")
    }

    # Display table
    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )

    # Show total count
    st.caption(f"Showing {len(configs)} configuration(s)")


def render_simple_table(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    title: Optional[str] = None
) -> None:
    """
    Render a simple data table.

    Args:
        data: List of dictionaries
        columns: Optional list of columns to display
        title: Optional table title
    """
    if title:
        st.markdown(f"**{title}**")

    if not data:
        st.info("No data to display.")
        return

    df = pd.DataFrame(data)

    if columns:
        available_columns = [col for col in columns if col in df.columns]
        df = df[available_columns]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.caption(f"Showing {len(data)} record(s)")


def render_log_table(logs: List[Dict[str, Any]]) -> None:
    """
    Render ETL logs table with formatted columns.

    Args:
        logs: List of log entry dictionaries
    """
    if not logs:
        st.info("No logs found.")
        return

    df = pd.DataFrame(logs)

    # Format timestamp
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # Format runtime
    if 'stepruntime' in df.columns:
        df['stepruntime'] = df['stepruntime'].round(2)

    # Define columns to show
    show_columns = [
        'timestamp',
        'processtype',
        'run_uuid',
        'stepcounter',
        'message',
        'stepruntime'
    ]

    available_columns = [col for col in show_columns if col in df.columns]

    column_config = {
        'timestamp': st.column_config.TextColumn('Timestamp', width="medium"),
        'processtype': st.column_config.TextColumn('Process', width="medium"),
        'run_uuid': st.column_config.TextColumn('Run UUID', width="medium"),
        'stepcounter': st.column_config.TextColumn('Step', width="small"),
        'message': st.column_config.TextColumn('Message', width="large"),
        'stepruntime': st.column_config.NumberColumn('Runtime (s)', format="%.2f", width="small")
    }

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )

    st.caption(f"Showing {len(logs)} log entry(ies)")


def render_dataset_table(datasets: List[Dict[str, Any]]) -> None:
    """
    Render dataset records table.

    Args:
        datasets: List of dataset dictionaries
    """
    if not datasets:
        st.info("No datasets found.")
        return

    df = pd.DataFrame(datasets)

    # Format date columns
    if 'datasetdate' in df.columns:
        df['datasetdate'] = pd.to_datetime(df['datasetdate']).dt.strftime('%Y-%m-%d')
    if 'createddate' in df.columns:
        df['createddate'] = pd.to_datetime(df['createddate']).dt.strftime('%Y-%m-%d %H:%M')

    # Define columns to show
    show_columns = [
        'datasetid',
        'datasetdate',
        'label',
        'datasource',
        'datasettype',
        'status',
        'createddate'
    ]

    available_columns = [col for col in show_columns if col in df.columns]

    column_config = {
        'datasetid': st.column_config.NumberColumn('ID', width="small"),
        'datasetdate': st.column_config.TextColumn('Dataset Date', width="medium"),
        'label': st.column_config.TextColumn('Label', width="medium"),
        'datasource': st.column_config.TextColumn('Source', width="medium"),
        'datasettype': st.column_config.TextColumn('Type', width="medium"),
        'status': st.column_config.TextColumn('Status', width="small"),
        'createddate': st.column_config.TextColumn('Created', width="medium")
    }

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )

    st.caption(f"Showing {len(datasets)} dataset(s)")


def render_key_value_table(data: Dict[str, Any], title: Optional[str] = None) -> None:
    """
    Render a dictionary as a two-column key-value table.

    Args:
        data: Dictionary to display
        title: Optional table title
    """
    if title:
        st.markdown(f"**{title}**")

    if not data:
        st.info("No data to display.")
        return

    # Create two-column layout
    for key, value in data.items():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**{key}:**")
        with col2:
            st.text(str(value) if value is not None else "N/A")

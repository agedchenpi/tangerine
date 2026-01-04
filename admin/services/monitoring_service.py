"""Service layer for monitoring ETL system - logs, datasets, and statistics"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from common.db_utils import fetch_dict


def get_logs(
    time_range_hours: Optional[int] = 24,
    process_type: Optional[str] = None,
    run_uuid: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get ETL logs with optional filters.

    Args:
        time_range_hours: Filter logs from last N hours (None for all)
        process_type: Filter by process type
        run_uuid: Filter by specific run UUID
        limit: Maximum number of logs to return

    Returns:
        List of log entry dictionaries
    """
    query = """
        SELECT
            logentryid,
            run_uuid,
            processtype,
            stepcounter,
            message,
            stepruntime,
            timestamp
        FROM dba.tlogentry
        WHERE 1=1
    """
    params = []

    # Time range filter
    if time_range_hours is not None:
        query += " AND timestamp >= NOW() - INTERVAL '%s hours'"
        params.append(time_range_hours)

    # Process type filter
    if process_type:
        query += " AND processtype = %s"
        params.append(process_type)

    # Run UUID filter
    if run_uuid:
        query += " AND run_uuid = %s"
        params.append(run_uuid)

    query += " ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)

    return fetch_dict(query, tuple(params)) if params else fetch_dict(query)


def get_distinct_process_types() -> List[str]:
    """
    Get list of distinct process types from logs.

    Returns:
        List of process type strings
    """
    query = """
        SELECT DISTINCT processtype
        FROM dba.tlogentry
        ORDER BY processtype
    """
    results = fetch_dict(query)
    return [r['processtype'] for r in results] if results else []


def get_datasets(
    datasource: Optional[str] = None,
    datasettype: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get datasets with optional filters.

    Args:
        datasource: Filter by data source
        datasettype: Filter by dataset type
        date_from: Filter datasets created after this date
        date_to: Filter datasets created before this date
        limit: Maximum number of datasets to return

    Returns:
        List of dataset dictionaries
    """
    query = """
        SELECT
            d.datasetid,
            d.label,
            src.sourcename as datasource,
            typ.typename as datasettype,
            d.createddate,
            stat.statusname as status,
            d.efffromdate,
            d.effthrudate,
            d.isactive
        FROM dba.tdataset d
        LEFT JOIN dba.tdatasource src ON d.datasourceid = src.datasourceid
        LEFT JOIN dba.tdatasettype typ ON d.datasettypeid = typ.datasettypeid
        LEFT JOIN dba.tdatastatus stat ON d.datastatusid = stat.datastatusid
        WHERE 1=1
    """
    params = []

    # Datasource filter
    if datasource:
        query += " AND src.sourcename = %s"
        params.append(datasource)

    # Datasettype filter
    if datasettype:
        query += " AND typ.typename = %s"
        params.append(datasettype)

    # Date range filters
    if date_from:
        query += " AND d.createddate >= %s"
        params.append(date_from)

    if date_to:
        query += " AND d.createddate <= %s"
        params.append(date_to)

    query += " ORDER BY d.createddate DESC LIMIT %s"
    params.append(limit)

    return fetch_dict(query, tuple(params)) if params else fetch_dict(query)


def get_dataset_sources() -> List[str]:
    """
    Get list of distinct datasources from datasets.

    Returns:
        List of datasource strings
    """
    query = """
        SELECT DISTINCT src.sourcename
        FROM dba.tdataset d
        LEFT JOIN dba.tdatasource src ON d.datasourceid = src.datasourceid
        WHERE src.sourcename IS NOT NULL
        ORDER BY src.sourcename
    """
    results = fetch_dict(query)
    return [r['sourcename'] for r in results] if results else []


def get_dataset_types_from_datasets() -> List[str]:
    """
    Get list of distinct dataset types from datasets.

    Returns:
        List of datasettype strings
    """
    query = """
        SELECT DISTINCT typ.typename
        FROM dba.tdataset d
        LEFT JOIN dba.tdatasettype typ ON d.datasettypeid = typ.datasettypeid
        WHERE typ.typename IS NOT NULL
        ORDER BY typ.typename
    """
    results = fetch_dict(query)
    return [r['typename'] for r in results] if results else []


def get_statistics_metrics() -> Dict[str, Any]:
    """
    Get system-wide statistics metrics.

    Returns:
        Dictionary with various metrics
    """
    # Total logs in last 24 hours
    logs_24h_query = """
        SELECT COUNT(*) as count
        FROM dba.tlogentry
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
    """
    logs_24h = fetch_dict(logs_24h_query)
    total_logs_24h = logs_24h[0]['count'] if logs_24h else 0

    # Unique processes in last 24 hours
    processes_query = """
        SELECT COUNT(DISTINCT processtype) as count
        FROM dba.tlogentry
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
    """
    processes = fetch_dict(processes_query)
    unique_processes = processes[0]['count'] if processes else 0

    # Average runtime per step
    runtime_query = """
        SELECT AVG(stepruntime) as avg_runtime
        FROM dba.tlogentry
        WHERE stepruntime IS NOT NULL
        AND timestamp >= NOW() - INTERVAL '24 hours'
    """
    runtime = fetch_dict(runtime_query)
    avg_runtime = runtime[0]['avg_runtime'] if runtime and runtime[0]['avg_runtime'] else 0

    # Total datasets in last 30 days
    datasets_query = """
        SELECT COUNT(*) as count
        FROM dba.tdataset
        WHERE createddate >= NOW() - INTERVAL '30 days'
    """
    datasets = fetch_dict(datasets_query)
    total_datasets_30d = datasets[0]['count'] if datasets else 0

    # Active datasets
    active_datasets_query = """
        SELECT COUNT(*) as count
        FROM dba.tdataset
        WHERE isactive = TRUE
    """
    active_datasets = fetch_dict(active_datasets_query)
    total_active_datasets = active_datasets[0]['count'] if active_datasets else 0

    # Total import configs
    configs_query = """
        SELECT COUNT(*) as count
        FROM dba.timportconfig
        WHERE is_active = TRUE
    """
    configs = fetch_dict(configs_query)
    total_active_configs = configs[0]['count'] if configs else 0

    return {
        'total_logs_24h': total_logs_24h,
        'unique_processes': unique_processes,
        'avg_runtime': round(avg_runtime, 2),
        'total_datasets_30d': total_datasets_30d,
        'total_active_datasets': total_active_datasets,
        'total_active_configs': total_active_configs
    }


def get_jobs_per_day(days: int = 30) -> List[Dict[str, Any]]:
    """
    Get count of jobs per day for the last N days.

    Args:
        days: Number of days to look back

    Returns:
        List of dictionaries with date and job count
    """
    query = """
        SELECT
            DATE(timestamp) as job_date,
            COUNT(DISTINCT run_uuid) as job_count
        FROM dba.tlogentry
        WHERE timestamp >= NOW() - INTERVAL '%s days'
        AND processtype = 'GenericImportJob'
        GROUP BY DATE(timestamp)
        ORDER BY job_date ASC
    """
    return fetch_dict(query, (days,)) or []


def get_process_type_distribution(days: int = 30) -> List[Dict[str, Any]]:
    """
    Get distribution of process types over last N days.

    Args:
        days: Number of days to look back

    Returns:
        List of dictionaries with process type and count
    """
    query = """
        SELECT
            processtype,
            COUNT(DISTINCT run_uuid) as run_count
        FROM dba.tlogentry
        WHERE timestamp >= NOW() - INTERVAL '%s days'
        GROUP BY processtype
        ORDER BY run_count DESC
    """
    return fetch_dict(query, (days,)) or []


def get_runtime_statistics(days: int = 7) -> List[Dict[str, Any]]:
    """
    Get runtime statistics by process type over last N days.

    Args:
        days: Number of days to look back

    Returns:
        List of dictionaries with process type and runtime stats
    """
    query = """
        SELECT
            processtype,
            COUNT(*) as step_count,
            AVG(stepruntime) as avg_runtime,
            MIN(stepruntime) as min_runtime,
            MAX(stepruntime) as max_runtime
        FROM dba.tlogentry
        WHERE timestamp >= NOW() - INTERVAL '%s days'
        AND stepruntime IS NOT NULL
        GROUP BY processtype
        ORDER BY avg_runtime DESC
    """
    return fetch_dict(query, (days,)) or []


def export_logs_to_csv(logs: List[Dict[str, Any]]) -> str:
    """
    Convert logs to CSV format.

    Args:
        logs: List of log dictionaries

    Returns:
        CSV string
    """
    if not logs:
        return "No logs to export"

    # CSV header
    headers = ['logentryid', 'run_uuid', 'processtype', 'stepcounter', 'message', 'stepruntime', 'timestamp']
    csv_lines = [','.join(headers)]

    # CSV rows
    for log in logs:
        # Escape quotes in message
        message = log.get('message', '')
        escaped_message = message.replace('"', '""')

        row = [
            str(log.get('logentryid', '')),
            str(log.get('run_uuid', '')),
            str(log.get('processtype', '')),
            str(log.get('stepcounter', '')),
            f'"{escaped_message}"',
            str(log.get('stepruntime', '')),
            str(log.get('timestamp', ''))
        ]
        csv_lines.append(','.join(row))

    return '\n'.join(csv_lines)

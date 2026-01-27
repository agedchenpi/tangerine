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


# ============================================================================
# Dataset CRUD Operations
# ============================================================================

def get_dataset_by_id(dataset_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a single dataset by ID with all details.

    Args:
        dataset_id: Dataset ID

    Returns:
        Dataset dictionary or None if not found
    """
    query = """
        SELECT
            d.datasetid,
            d.label,
            d.datasetdate,
            d.datasourceid,
            src.sourcename as datasource,
            d.datasettypeid,
            typ.typename as datasettype,
            d.datastatusid,
            stat.statusname as status,
            d.efffromdate,
            d.effthrudate,
            d.isactive,
            d.createddate,
            d.createdby
        FROM dba.tdataset d
        LEFT JOIN dba.tdatasource src ON d.datasourceid = src.datasourceid
        LEFT JOIN dba.tdatasettype typ ON d.datasettypeid = typ.datasettypeid
        LEFT JOIN dba.tdatastatus stat ON d.datastatusid = stat.datastatusid
        WHERE d.datasetid = %s
    """
    results = fetch_dict(query, (dataset_id,))
    return results[0] if results else None


def create_dataset(
    label: str,
    datasetdate: Any,
    datasourceid: int,
    datasettypeid: int,
    datastatusid: int = 1
) -> int:
    """
    Create a new dataset record.

    Args:
        label: Dataset label
        datasetdate: Dataset date
        datasourceid: Data source ID
        datasettypeid: Dataset type ID
        datastatusid: Data status ID (default: 1 = Active)

    Returns:
        New dataset ID
    """
    from common.db_utils import db_transaction

    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.tdataset (
                label, datasetdate, datasourceid, datasettypeid, datastatusid
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING datasetid
        """, (label, datasetdate, datasourceid, datasettypeid, datastatusid))
        return cursor.fetchone()['datasetid']


def update_dataset(
    dataset_id: int,
    label: str,
    datasetdate: Any,
    datasourceid: int,
    datasettypeid: int,
    datastatusid: int,
    isactive: bool = True
) -> bool:
    """
    Update an existing dataset.

    Args:
        dataset_id: Dataset ID to update
        label: New label
        datasetdate: New dataset date
        datasourceid: New data source ID
        datasettypeid: New dataset type ID
        datastatusid: New data status ID
        isactive: Active flag

    Returns:
        True if updated successfully
    """
    from common.db_utils import db_transaction

    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE dba.tdataset
            SET label = %s,
                datasetdate = %s,
                datasourceid = %s,
                datasettypeid = %s,
                datastatusid = %s,
                isactive = %s
            WHERE datasetid = %s
        """, (label, datasetdate, datasourceid, datasettypeid, datastatusid, isactive, dataset_id))
        return cursor.rowcount > 0


def delete_dataset(dataset_id: int) -> bool:
    """
    Delete a dataset record.

    Args:
        dataset_id: Dataset ID to delete

    Returns:
        True if deleted successfully
    """
    from common.db_utils import db_transaction

    with db_transaction() as cursor:
        cursor.execute(
            "DELETE FROM dba.tdataset WHERE datasetid = %s",
            (dataset_id,)
        )
        return cursor.rowcount > 0


def get_dataset_dependencies(dataset_id: int) -> List[Dict[str, Any]]:
    """
    Check for dependencies on a dataset (e.g., regression tests).

    Args:
        dataset_id: Dataset ID to check

    Returns:
        List of dependent records
    """
    query = """
        SELECT
            'Regression Test' as dependency_type,
            testid as dependency_id,
            testname as dependency_name
        FROM dba.tregressiontest
        WHERE datasetid = %s
    """
    return fetch_dict(query, (dataset_id,)) or []


def get_all_data_statuses() -> List[Dict[str, Any]]:
    """
    Get all available data statuses.

    Returns:
        List of status dictionaries
    """
    query = """
        SELECT datastatusid, statusname
        FROM dba.tdatastatus
        ORDER BY datastatusid
    """
    return fetch_dict(query) or []


def archive_dataset(dataset_id: int) -> bool:
    """
    Archive a dataset (soft delete by setting status to Inactive).

    Args:
        dataset_id: Dataset ID to archive

    Returns:
        True if archived successfully
    """
    from common.db_utils import db_transaction

    with db_transaction() as cursor:
        # Status 2 = Inactive
        cursor.execute("""
            UPDATE dba.tdataset
            SET datastatusid = 2,
                isactive = FALSE
            WHERE datasetid = %s
        """, (dataset_id,))
        return cursor.rowcount > 0


# ============================================================================
# Log Purge Operations
# ============================================================================

def preview_log_purge(days_old: int) -> Dict[str, Any]:
    """
    Preview how many logs would be deleted.

    Args:
        days_old: Delete logs older than this many days

    Returns:
        Dictionary with count and date range info
    """
    query = """
        SELECT
            COUNT(*) as log_count,
            MIN(timestamp) as oldest_log,
            MAX(timestamp) as newest_log
        FROM dba.tlogentry
        WHERE timestamp < NOW() - INTERVAL '%s days'
    """
    results = fetch_dict(query, (days_old,))
    return results[0] if results else {'log_count': 0, 'oldest_log': None, 'newest_log': None}


def purge_logs(days_old: int) -> int:
    """
    Delete logs older than specified days.

    Args:
        days_old: Delete logs older than this many days

    Returns:
        Number of logs deleted
    """
    from common.db_utils import db_transaction

    with db_transaction() as cursor:
        cursor.execute("""
            DELETE FROM dba.tlogentry
            WHERE timestamp < NOW() - INTERVAL '%s days'
        """, (days_old,))
        return cursor.rowcount


def export_logs_for_purge(days_old: int) -> List[Dict[str, Any]]:
    """
    Export logs that would be purged (for archival before deletion).

    Args:
        days_old: Get logs older than this many days

    Returns:
        List of log dictionaries
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
        WHERE timestamp < NOW() - INTERVAL '%s days'
        ORDER BY timestamp DESC
    """
    return fetch_dict(query, (days_old,)) or []


def get_log_statistics() -> Dict[str, Any]:
    """
    Get statistics about log entries.

    Returns:
        Dictionary with log statistics
    """
    query = """
        SELECT
            COUNT(*) as total_logs,
            COUNT(DISTINCT run_uuid) as total_runs,
            MIN(timestamp) as oldest_log,
            MAX(timestamp) as newest_log,
            SUM(CASE WHEN timestamp >= NOW() - INTERVAL '7 days' THEN 1 ELSE 0 END) as logs_last_7_days,
            SUM(CASE WHEN timestamp >= NOW() - INTERVAL '30 days' THEN 1 ELSE 0 END) as logs_last_30_days
        FROM dba.tlogentry
    """
    results = fetch_dict(query)
    return results[0] if results else {}

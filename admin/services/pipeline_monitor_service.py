"""Service layer for Pipeline Monitor - job runs, steps, and import logs."""

from typing import Dict, Any, List, Optional
from common.db_utils import fetch_dict


def get_recent_job_runs(
    limit: int = 50,
    status_filter: Optional[str] = None,
    job_name_filter: Optional[str] = None,
    hours: Optional[int] = 24,
) -> List[Dict[str, Any]]:
    """
    Query tjobrun with aggregated step counts and total duration.

    Returns one row per job run, newest first.
    """
    query = """
        SELECT
            r.jobrunid,
            r.job_name,
            r.config_name,
            r.run_uuid,
            r.started_at,
            r.completed_at,
            r.status,
            r.triggered_by,
            r.dry_run,
            r.error_message,
            EXTRACT(EPOCH FROM (COALESCE(r.completed_at, NOW()) - r.started_at)) AS duration_seconds,
            COUNT(s.jobstepid) AS step_count,
            SUM(CASE WHEN s.status = 'success' THEN 1 ELSE 0 END) AS steps_success,
            SUM(CASE WHEN s.status = 'failed'  THEN 1 ELSE 0 END) AS steps_failed
        FROM dba.tjobrun r
        LEFT JOIN dba.tjobstep s ON s.jobrunid = r.jobrunid
        WHERE 1=1
    """
    params = []

    if hours is not None:
        query += " AND r.started_at >= NOW() - INTERVAL '%s hours'"
        params.append(hours)

    if status_filter:
        query += " AND r.status = %s"
        params.append(status_filter)

    if job_name_filter:
        query += " AND r.job_name = %s"
        params.append(job_name_filter)

    query += " GROUP BY r.jobrunid ORDER BY r.started_at DESC LIMIT %s"
    params.append(limit)

    return fetch_dict(query, tuple(params))


def get_job_run_steps(jobrunid: int) -> List[Dict[str, Any]]:
    """All tjobstep rows for one run, ordered by step_order."""
    query = """
        SELECT
            jobstepid,
            jobrunid,
            step_name,
            step_order,
            display_name,
            started_at,
            completed_at,
            status,
            records_in,
            records_out,
            step_runtime,
            log_run_uuid,
            message
        FROM dba.tjobstep
        WHERE jobrunid = %s
        ORDER BY step_order ASC
    """
    return fetch_dict(query, (jobrunid,))


def get_step_logs(log_run_uuid: str) -> List[Dict[str, Any]]:
    """tlogentry rows for one import run, ordered by stepcounter."""
    query = """
        SELECT
            logentryid,
            timestamp,
            stepcounter,
            message,
            stepruntime
        FROM dba.tlogentry
        WHERE run_uuid = %s
        ORDER BY stepcounter ASC
    """
    return fetch_dict(query, (log_run_uuid,))


def get_pipeline_stats(hours: int = 24) -> Dict[str, Any]:
    """Total, success, failed, running counts + avg duration over last N hours."""
    query = """
        SELECT
            COUNT(*)                                                         AS total,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)             AS success,
            SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END)             AS failed,
            SUM(CASE WHEN status = 'partial' THEN 1 ELSE 0 END)             AS partial,
            SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END)             AS running,
            AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))            AS avg_duration_seconds
        FROM dba.tjobrun
        WHERE started_at >= NOW() - INTERVAL '%s hours'
    """
    results = fetch_dict(query, (hours,))
    row = results[0] if results else {}
    return {
        'total': int(row.get('total') or 0),
        'success': int(row.get('success') or 0),
        'failed': int(row.get('failed') or 0),
        'partial': int(row.get('partial') or 0),
        'running': int(row.get('running') or 0),
        'avg_duration_seconds': round(float(row.get('avg_duration_seconds') or 0), 1),
    }


def mark_step_overridden(jobstepid: int) -> None:
    """Mark a failed step as manually overridden."""
    from common.db_utils import execute_query
    execute_query(
        "UPDATE dba.tjobstep SET status = 'overridden', completed_at = NOW() WHERE jobstepid = %s",
        (jobstepid,)
    )


def get_distinct_job_names() -> List[str]:
    """All distinct job_name values from tjobrun, for filter dropdowns."""
    query = """
        SELECT DISTINCT job_name
        FROM dba.tjobrun
        ORDER BY job_name
    """
    results = fetch_dict(query)
    return [r['job_name'] for r in results] if results else []

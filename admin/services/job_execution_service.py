"""Service layer for executing ETL jobs"""

import subprocess
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime, date
from common.db_utils import fetch_dict


def get_recent_job_runs(config_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent job runs from log entries.

    Args:
        config_id: Optional config_id to filter by
        limit: Maximum number of runs to return

    Returns:
        List of recent job run dictionaries
    """
    query = """
        SELECT
            run_uuid,
            processtype,
            MIN(timestamp) as starttime,
            COUNT(*) as total_steps,
            CASE
                WHEN MAX(CASE WHEN message LIKE '%%ERROR%%' OR message LIKE '%%FAIL%%' THEN 1 ELSE 0 END) > 0 THEN 'Failed'
                WHEN MAX(CASE WHEN message LIKE '%%SUCCESS%%' OR message LIKE '%%COMPLETE%%' THEN 1 ELSE 0 END) > 0 THEN 'Success'
                ELSE 'Running'
            END as status,
            COALESCE(SUM(stepruntime), 0) as total_runtime
        FROM dba.tlogentry
        WHERE processtype = 'GenericImportJob'
        GROUP BY run_uuid, processtype
        ORDER BY MIN(timestamp) DESC
        LIMIT %s
    """

    result = fetch_dict(query, (limit,))
    return result if result else []


def get_job_output(run_uuid: str) -> List[Dict[str, Any]]:
    """
    Get detailed output for a specific job run.

    Args:
        run_uuid: The run UUID to get logs for

    Returns:
        List of log entry dictionaries
    """
    query = """
        SELECT
            stepcounter,
            message,
            stepruntime,
            timestamp
        FROM dba.tlogentry
        WHERE run_uuid = %s
        ORDER BY stepcounter ASC
    """

    return fetch_dict(query, (run_uuid,)) or []


def execute_import_job(
    config_id: int,
    run_date: Optional[date] = None,
    dry_run: bool = False,
    timeout: int = 300
) -> Generator[str, None, None]:
    """
    Execute an import job and stream output in real-time.

    Args:
        config_id: Import configuration ID to run
        run_date: Optional date for the import (default: today)
        dry_run: If True, runs in dry-run mode (no database writes)
        timeout: Maximum execution time in seconds (default: 5 minutes)

    Yields:
        Output lines from the job execution

    Raises:
        subprocess.TimeoutExpired: If job exceeds timeout
        Exception: For other execution errors
    """
    # Build command
    cmd = [
        "docker", "compose", "exec", "-T", "tangerine",
        "python", "etl/jobs/generic_import.py",
        "--config-id", str(config_id)
    ]

    if run_date:
        cmd.extend(["--date", run_date.strftime("%Y-%m-%d")])

    if dry_run:
        cmd.append("--dry-run")

    # Execute command and stream output
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Stream output line by line
        for line in process.stdout:
            yield line.rstrip('\n')

        # Wait for process to complete
        process.wait(timeout=timeout)

        # Check exit code
        if process.returncode != 0:
            yield f"\n❌ Job failed with exit code {process.returncode}"
        else:
            yield f"\n✅ Job completed successfully"

    except subprocess.TimeoutExpired:
        process.kill()
        yield f"\n⏱️ Job execution exceeded timeout of {timeout} seconds"
        raise
    except Exception as e:
        yield f"\n❌ Error executing job: {str(e)}"
        raise


def validate_import_config(config_id: int) -> tuple[bool, Optional[str]]:
    """
    Validate that an import configuration exists and is active.

    Args:
        config_id: Configuration ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    query = """
        SELECT config_id, config_name, is_active
        FROM dba.timportconfig
        WHERE config_id = %s
    """

    result = fetch_dict(query, (config_id,))

    if not result:
        return False, f"Configuration with ID {config_id} not found"

    config = result[0]

    if not config['is_active']:
        return False, f"Configuration '{config['config_name']}' is inactive. Activate it before running."

    return True, None


def get_active_configs_for_execution() -> List[Dict[str, Any]]:
    """
    Get all active import configurations suitable for execution.

    Returns:
        List of active configuration dictionaries
    """
    query = """
        SELECT
            c.config_id,
            c.config_name,
            c.file_type,
            c.datasource,
            c.datasettype,
            c.target_table,
            s.name as strategy_name
        FROM dba.timportconfig c
        LEFT JOIN dba.timportstrategy s ON c.importstrategyid = s.importstrategyid
        WHERE c.is_active = TRUE
        ORDER BY c.config_name
    """

    return fetch_dict(query) or []


def get_dataset_count_for_config(config_name: str, days: int = 7) -> int:
    """
    Get count of datasets created by this config in recent days.

    Args:
        config_name: Configuration name
        days: Number of days to look back

    Returns:
        Count of datasets
    """
    query = """
        SELECT COUNT(*) as count
        FROM dba.tdataset
        WHERE label LIKE %s
        AND createddate >= CURRENT_DATE - INTERVAL '%s days'
    """

    # Use LIKE to match configs that may have timestamps in labels
    pattern = f"%{config_name}%"

    result = fetch_dict(query, (pattern, days))
    return result[0]['count'] if result else 0

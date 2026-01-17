"""Business logic for scheduler management"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from common.db_utils import fetch_dict, db_transaction
import subprocess

# Optional croniter for next run calculation
try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False


def list_schedules(
    active_only: bool = False,
    job_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List scheduler configurations with optional filters.

    Args:
        active_only: Only return active schedules
        job_type: Filter by job type (inbox_processor, report, import, custom)

    Returns:
        List of scheduler dictionaries
    """
    query = """
        SELECT
            s.*,
            CASE
                WHEN s.job_type = 'inbox_processor' THEN ic.config_name
                WHEN s.job_type = 'report' THEN rm.report_name
                WHEN s.job_type = 'import' THEN imp.config_name
                ELSE NULL
            END as linked_config_name
        FROM dba.tscheduler s
        LEFT JOIN dba.tinboxconfig ic ON s.job_type = 'inbox_processor' AND s.config_id = ic.inbox_config_id
        LEFT JOIN dba.treportmanager rm ON s.job_type = 'report' AND s.config_id = rm.report_id
        LEFT JOIN dba.timportconfig imp ON s.job_type = 'import' AND s.config_id = imp.config_id
        WHERE 1=1
    """
    params = []

    if active_only:
        query += " AND s.is_active = %s"
        params.append(True)

    if job_type:
        query += " AND s.job_type = %s"
        params.append(job_type)

    query += " ORDER BY s.scheduler_id DESC"

    return fetch_dict(query, tuple(params) if params else None) or []


def get_schedule(scheduler_id: int) -> Optional[Dict[str, Any]]:
    """
    Get single schedule by ID.

    Args:
        scheduler_id: Scheduler ID

    Returns:
        Scheduler dictionary or None if not found
    """
    query = """
        SELECT
            s.*,
            CASE
                WHEN s.job_type = 'inbox_processor' THEN ic.config_name
                WHEN s.job_type = 'report' THEN rm.report_name
                WHEN s.job_type = 'import' THEN imp.config_name
                ELSE NULL
            END as linked_config_name
        FROM dba.tscheduler s
        LEFT JOIN dba.tinboxconfig ic ON s.job_type = 'inbox_processor' AND s.config_id = ic.inbox_config_id
        LEFT JOIN dba.treportmanager rm ON s.job_type = 'report' AND s.config_id = rm.report_id
        LEFT JOIN dba.timportconfig imp ON s.job_type = 'import' AND s.config_id = imp.config_id
        WHERE s.scheduler_id = %s
    """
    results = fetch_dict(query, (scheduler_id,))
    return results[0] if results else None


def create_schedule(schedule_data: Dict[str, Any]) -> int:
    """
    Create new scheduler configuration.

    Args:
        schedule_data: Dictionary of scheduler fields

    Returns:
        New scheduler_id

    Raises:
        Exception: For database errors
    """
    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.tscheduler (
                job_name, job_type, cron_minute, cron_hour, cron_day,
                cron_month, cron_weekday, script_path, config_id, is_active,
                created_at, last_modified_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING scheduler_id
        """, (
            schedule_data['job_name'],
            schedule_data['job_type'],
            schedule_data.get('cron_minute', '*'),
            schedule_data.get('cron_hour', '*'),
            schedule_data.get('cron_day', '*'),
            schedule_data.get('cron_month', '*'),
            schedule_data.get('cron_weekday', '*'),
            schedule_data.get('script_path'),
            schedule_data.get('config_id'),
            schedule_data.get('is_active', True),
            datetime.now(),
            datetime.now()
        ))

        result = cursor.fetchone()
        if not result:
            raise Exception("Failed to create schedule")

        scheduler_id = result[0]

        # Calculate and set next_run_at if croniter available
        if HAS_CRONITER:
            try:
                cron_expr = build_cron_expression(schedule_data)
                next_run = calculate_next_run(cron_expr)
                if next_run:
                    cursor.execute(
                        "UPDATE dba.tscheduler SET next_run_at = %s WHERE scheduler_id = %s",
                        (next_run, scheduler_id)
                    )
            except Exception:
                pass

        return scheduler_id


def update_schedule(scheduler_id: int, schedule_data: Dict[str, Any]) -> None:
    """
    Update existing scheduler configuration.

    Args:
        scheduler_id: ID of schedule to update
        schedule_data: Dictionary of fields to update

    Raises:
        Exception: If schedule not found
    """
    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE dba.tscheduler
            SET
                job_name = COALESCE(%s, job_name),
                job_type = COALESCE(%s, job_type),
                cron_minute = COALESCE(%s, cron_minute),
                cron_hour = COALESCE(%s, cron_hour),
                cron_day = COALESCE(%s, cron_day),
                cron_month = COALESCE(%s, cron_month),
                cron_weekday = COALESCE(%s, cron_weekday),
                script_path = COALESCE(%s, script_path),
                config_id = COALESCE(%s, config_id),
                is_active = COALESCE(%s, is_active),
                last_modified_at = %s
            WHERE scheduler_id = %s
        """, (
            schedule_data.get('job_name'),
            schedule_data.get('job_type'),
            schedule_data.get('cron_minute'),
            schedule_data.get('cron_hour'),
            schedule_data.get('cron_day'),
            schedule_data.get('cron_month'),
            schedule_data.get('cron_weekday'),
            schedule_data.get('script_path'),
            schedule_data.get('config_id'),
            schedule_data.get('is_active'),
            datetime.now(),
            scheduler_id
        ))

        if cursor.rowcount == 0:
            raise Exception(f"Schedule {scheduler_id} not found")

        # Recalculate next_run_at if cron fields changed
        if HAS_CRONITER and any(k.startswith('cron_') for k in schedule_data.keys()):
            schedule = get_schedule(scheduler_id)
            if schedule:
                try:
                    cron_expr = build_cron_expression(schedule)
                    next_run = calculate_next_run(cron_expr)
                    if next_run:
                        cursor.execute(
                            "UPDATE dba.tscheduler SET next_run_at = %s WHERE scheduler_id = %s",
                            (next_run, scheduler_id)
                        )
                except Exception:
                    pass


def delete_schedule(scheduler_id: int) -> None:
    """
    Delete scheduler configuration.

    Args:
        scheduler_id: ID of schedule to delete

    Raises:
        Exception: If schedule not found or referenced
    """
    with db_transaction() as cursor:
        # Check for references in treportmanager
        cursor.execute(
            "SELECT COUNT(*) as count FROM dba.treportmanager WHERE schedule_id = %s",
            (scheduler_id,)
        )
        result = cursor.fetchone()
        if result and result[0] > 0:
            raise Exception(f"Schedule {scheduler_id} is referenced by reports. Remove report references first.")

        cursor.execute(
            "DELETE FROM dba.tscheduler WHERE scheduler_id = %s",
            (scheduler_id,)
        )

        if cursor.rowcount == 0:
            raise Exception(f"Schedule {scheduler_id} not found")


def toggle_active(scheduler_id: int, is_active: bool) -> None:
    """
    Toggle schedule active status.

    Args:
        scheduler_id: ID of schedule
        is_active: New active status
    """
    update_schedule(scheduler_id, {'is_active': is_active})


def build_cron_expression(schedule: Dict[str, Any]) -> str:
    """
    Build cron expression from schedule fields.

    Args:
        schedule: Schedule dictionary with cron_* fields

    Returns:
        Cron expression string
    """
    return ' '.join([
        schedule.get('cron_minute', '*'),
        schedule.get('cron_hour', '*'),
        schedule.get('cron_day', '*'),
        schedule.get('cron_month', '*'),
        schedule.get('cron_weekday', '*')
    ])


def calculate_next_run(cron_expr: str) -> Optional[datetime]:
    """
    Calculate next run time from cron expression.

    Args:
        cron_expr: Cron expression string (5 fields)

    Returns:
        Next run datetime, or None if croniter not available
    """
    if not HAS_CRONITER:
        return None

    try:
        cron = croniter(cron_expr, datetime.now())
        return cron.get_next(datetime)
    except Exception:
        return None


def get_scheduler_stats() -> Dict[str, int]:
    """
    Get statistics about scheduled jobs.

    Returns:
        Dictionary with total, active, inactive counts by job_type
    """
    query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN NOT is_active THEN 1 ELSE 0 END) as inactive,
            SUM(CASE WHEN job_type = 'inbox_processor' THEN 1 ELSE 0 END) as inbox_count,
            SUM(CASE WHEN job_type = 'report' THEN 1 ELSE 0 END) as report_count,
            SUM(CASE WHEN job_type = 'import' THEN 1 ELSE 0 END) as import_count,
            SUM(CASE WHEN job_type = 'custom' THEN 1 ELSE 0 END) as custom_count
        FROM dba.tscheduler
    """
    result = fetch_dict(query)
    if result:
        return {
            'total': result[0]['total'] or 0,
            'active': result[0]['active'] or 0,
            'inactive': result[0]['inactive'] or 0,
            'inbox_count': result[0]['inbox_count'] or 0,
            'report_count': result[0]['report_count'] or 0,
            'import_count': result[0]['import_count'] or 0,
            'custom_count': result[0]['custom_count'] or 0
        }
    return {'total': 0, 'active': 0, 'inactive': 0, 'inbox_count': 0, 'report_count': 0, 'import_count': 0, 'custom_count': 0}


def job_name_exists(job_name: str, exclude_id: Optional[int] = None) -> bool:
    """
    Check if a job name already exists.

    Args:
        job_name: Name to check
        exclude_id: Optional scheduler_id to exclude (for updates)

    Returns:
        True if name exists, False otherwise
    """
    query = "SELECT COUNT(*) as count FROM dba.tscheduler WHERE job_name = %s"
    params = [job_name]

    if exclude_id is not None:
        query += " AND scheduler_id != %s"
        params.append(exclude_id)

    result = fetch_dict(query, tuple(params))
    return result[0]['count'] > 0 if result else False


def regenerate_crontab() -> bool:
    """
    Regenerate and apply container crontab from scheduler table.

    Returns:
        True if successful, False otherwise
    """
    try:
        result = subprocess.run(
            ['python', 'etl/jobs/generate_crontab.py', '--apply'],
            capture_output=True,
            text=True,
            cwd='/app'
        )
        return result.returncode == 0
    except Exception:
        return False


def get_crontab_preview() -> str:
    """
    Get preview of generated crontab.

    Returns:
        Crontab content string
    """
    try:
        result = subprocess.run(
            ['python', 'etl/jobs/generate_crontab.py', '--preview'],
            capture_output=True,
            text=True,
            cwd='/app'
        )
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Error generating preview: {e}"


def get_job_types() -> List[Dict[str, str]]:
    """
    Get list of available job types.

    Returns:
        List of job type dictionaries with value and label
    """
    return [
        {'value': 'inbox_processor', 'label': 'Inbox Processor', 'description': 'Process Gmail inbox rules'},
        {'value': 'report', 'label': 'Report', 'description': 'Generate and send reports'},
        {'value': 'import', 'label': 'Import', 'description': 'Run import configurations'},
        {'value': 'custom', 'label': 'Custom', 'description': 'Run custom Python script'}
    ]


def get_config_options(job_type: str) -> List[Dict[str, Any]]:
    """
    Get config options for a specific job type.

    Args:
        job_type: Type of job

    Returns:
        List of config options with id and name
    """
    if job_type == 'inbox_processor':
        query = "SELECT inbox_config_id as id, config_name as name FROM dba.tinboxconfig WHERE is_active = TRUE ORDER BY config_name"
    elif job_type == 'report':
        query = "SELECT report_id as id, report_name as name FROM dba.treportmanager WHERE is_active = TRUE ORDER BY report_name"
    elif job_type == 'import':
        query = "SELECT config_id as id, config_name as name FROM dba.timportconfig WHERE is_active = TRUE ORDER BY config_name"
    else:
        return []

    return fetch_dict(query) or []


def create_schedule_for_report(
    report_id: int,
    job_name: str,
    cron_minute: str = '0',
    cron_hour: str = '8',
    cron_day: str = '*',
    cron_month: str = '*',
    cron_weekday: str = '1-5'
) -> int:
    """
    Create a schedule specifically for a report, link them, and regenerate crontab.

    Args:
        report_id: ID of the report to schedule
        job_name: Unique name for the schedule
        cron_minute: Cron minute field (default: 0)
        cron_hour: Cron hour field (default: 8)
        cron_day: Cron day field (default: *)
        cron_month: Cron month field (default: *)
        cron_weekday: Cron weekday field (default: 1-5, weekdays)

    Returns:
        New scheduler_id

    Raises:
        Exception: If job_name already exists or database error
    """
    # Check for duplicate job name
    if job_name_exists(job_name):
        raise Exception(f"Schedule name '{job_name}' already exists")

    # Create the schedule
    schedule_data = {
        'job_name': job_name,
        'job_type': 'report',
        'cron_minute': cron_minute,
        'cron_hour': cron_hour,
        'cron_day': cron_day,
        'cron_month': cron_month,
        'cron_weekday': cron_weekday,
        'config_id': report_id,
        'is_active': True
    }

    scheduler_id = create_schedule(schedule_data)

    # Link the report to the schedule
    with db_transaction() as cursor:
        cursor.execute(
            "UPDATE dba.treportmanager SET schedule_id = %s, last_modified_at = %s WHERE report_id = %s",
            (scheduler_id, datetime.now(), report_id)
        )

    # Regenerate crontab to apply changes
    regenerate_crontab()

    return scheduler_id

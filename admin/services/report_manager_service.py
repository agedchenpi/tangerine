"""Business logic for report manager"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from common.db_utils import fetch_dict, db_transaction


def list_reports(
    active_only: bool = False
) -> List[Dict[str, Any]]:
    """
    List report configurations with optional filters.

    Args:
        active_only: Only return active reports

    Returns:
        List of report dictionaries
    """
    query = """
        SELECT
            r.*,
            s.job_name as schedule_name,
            s.cron_minute || ' ' || s.cron_hour || ' ' || s.cron_day || ' ' ||
            s.cron_month || ' ' || s.cron_weekday as cron_expression
        FROM dba.treportmanager r
        LEFT JOIN dba.tscheduler s ON r.schedule_id = s.scheduler_id
        WHERE 1=1
    """
    params = []

    if active_only:
        query += " AND r.is_active = %s"
        params.append(True)

    query += " ORDER BY r.report_id DESC"

    return fetch_dict(query, tuple(params) if params else None) or []


def get_report(report_id: int) -> Optional[Dict[str, Any]]:
    """
    Get single report by ID.

    Args:
        report_id: Report ID

    Returns:
        Report dictionary or None if not found
    """
    query = """
        SELECT
            r.*,
            s.job_name as schedule_name,
            s.cron_minute || ' ' || s.cron_hour || ' ' || s.cron_day || ' ' ||
            s.cron_month || ' ' || s.cron_weekday as cron_expression
        FROM dba.treportmanager r
        LEFT JOIN dba.tscheduler s ON r.schedule_id = s.scheduler_id
        WHERE r.report_id = %s
    """
    results = fetch_dict(query, (report_id,))
    return results[0] if results else None


def create_report(report_data: Dict[str, Any]) -> int:
    """
    Create new report configuration.

    Args:
        report_data: Dictionary of report fields

    Returns:
        New report_id

    Raises:
        Exception: For database errors
    """
    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.treportmanager (
                report_name, description, recipients, cc_recipients,
                subject_line, body_template, output_format, attachment_filename,
                schedule_id, is_active, created_at, last_modified_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING report_id
        """, (
            report_data['report_name'],
            report_data.get('description'),
            report_data['recipients'],
            report_data.get('cc_recipients'),
            report_data['subject_line'],
            report_data['body_template'],
            report_data.get('output_format', 'html'),
            report_data.get('attachment_filename'),
            report_data.get('schedule_id'),
            report_data.get('is_active', True),
            datetime.now(),
            datetime.now()
        ))

        result = cursor.fetchone()
        if not result:
            raise Exception("Failed to create report")

        return result[0]


def update_report(report_id: int, report_data: Dict[str, Any]) -> None:
    """
    Update existing report configuration.

    Args:
        report_id: ID of report to update
        report_data: Dictionary of fields to update

    Raises:
        Exception: If report not found
    """
    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE dba.treportmanager
            SET
                report_name = COALESCE(%s, report_name),
                description = COALESCE(%s, description),
                recipients = COALESCE(%s, recipients),
                cc_recipients = COALESCE(%s, cc_recipients),
                subject_line = COALESCE(%s, subject_line),
                body_template = COALESCE(%s, body_template),
                output_format = COALESCE(%s, output_format),
                attachment_filename = COALESCE(%s, attachment_filename),
                schedule_id = COALESCE(%s, schedule_id),
                is_active = COALESCE(%s, is_active),
                last_modified_at = %s
            WHERE report_id = %s
        """, (
            report_data.get('report_name'),
            report_data.get('description'),
            report_data.get('recipients'),
            report_data.get('cc_recipients'),
            report_data.get('subject_line'),
            report_data.get('body_template'),
            report_data.get('output_format'),
            report_data.get('attachment_filename'),
            report_data.get('schedule_id'),
            report_data.get('is_active'),
            datetime.now(),
            report_id
        ))

        if cursor.rowcount == 0:
            raise Exception(f"Report {report_id} not found")


def delete_report(report_id: int) -> None:
    """
    Delete report configuration.

    Args:
        report_id: ID of report to delete

    Raises:
        Exception: If report not found or referenced
    """
    with db_transaction() as cursor:
        # Check for references in tscheduler
        cursor.execute(
            "SELECT COUNT(*) as count FROM dba.tscheduler WHERE job_type = 'report' AND config_id = %s",
            (report_id,)
        )
        result = cursor.fetchone()
        if result and result[0] > 0:
            raise Exception(f"Report {report_id} is referenced by schedules. Remove schedule references first.")

        cursor.execute(
            "DELETE FROM dba.treportmanager WHERE report_id = %s",
            (report_id,)
        )

        if cursor.rowcount == 0:
            raise Exception(f"Report {report_id} not found")


def toggle_active(report_id: int, is_active: bool) -> None:
    """
    Toggle report active status.

    Args:
        report_id: ID of report
        is_active: New active status
    """
    update_report(report_id, {'is_active': is_active})


def get_report_stats() -> Dict[str, int]:
    """
    Get statistics about reports.

    Returns:
        Dictionary with total, active, inactive, success, failed counts
    """
    query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN NOT is_active THEN 1 ELSE 0 END) as inactive,
            SUM(CASE WHEN last_run_status = 'Success' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN last_run_status = 'Failed' THEN 1 ELSE 0 END) as failed
        FROM dba.treportmanager
    """
    result = fetch_dict(query)
    if result:
        return {
            'total': result[0]['total'] or 0,
            'active': result[0]['active'] or 0,
            'inactive': result[0]['inactive'] or 0,
            'success': result[0]['success'] or 0,
            'failed': result[0]['failed'] or 0
        }
    return {'total': 0, 'active': 0, 'inactive': 0, 'success': 0, 'failed': 0}


def report_name_exists(report_name: str, exclude_id: Optional[int] = None) -> bool:
    """
    Check if a report name already exists.

    Args:
        report_name: Name to check
        exclude_id: Optional report_id to exclude (for updates)

    Returns:
        True if name exists, False otherwise
    """
    query = "SELECT COUNT(*) as count FROM dba.treportmanager WHERE report_name = %s"
    params = [report_name]

    if exclude_id is not None:
        query += " AND report_id != %s"
        params.append(exclude_id)

    result = fetch_dict(query, tuple(params))
    return result[0]['count'] > 0 if result else False


def get_schedules() -> List[Dict[str, Any]]:
    """
    Get list of available schedules for linking.

    Returns:
        List of schedule dictionaries
    """
    query = """
        SELECT scheduler_id, job_name,
               cron_minute || ' ' || cron_hour || ' ' || cron_day || ' ' ||
               cron_month || ' ' || cron_weekday as cron_expression
        FROM dba.tscheduler
        WHERE is_active = TRUE AND job_type = 'report'
        ORDER BY job_name
    """
    return fetch_dict(query) or []


def get_output_formats() -> List[Dict[str, str]]:
    """
    Get list of available output formats.

    Returns:
        List of format dictionaries with value, label, description
    """
    return [
        {'value': 'html', 'label': 'HTML Only', 'description': 'Inline HTML tables in email body'},
        {'value': 'csv', 'label': 'CSV Attachment', 'description': 'CSV file attachment only'},
        {'value': 'excel', 'label': 'Excel Attachment', 'description': 'Excel file attachment only'},
        {'value': 'html_csv', 'label': 'HTML + CSV', 'description': 'Both inline tables and CSV attachment'},
        {'value': 'html_excel', 'label': 'HTML + Excel', 'description': 'Both inline tables and Excel attachment'}
    ]


def test_report_preview(report_id: int) -> Dict[str, Any]:
    """
    Generate a preview of the report without sending.

    Args:
        report_id: Report ID to preview

    Returns:
        Dictionary with preview HTML and metadata
    """
    import subprocess

    try:
        result = subprocess.run(
            ['python', 'etl/jobs/run_report_generator.py', '--report-id', str(report_id), '--dry-run'],
            capture_output=True,
            text=True,
            cwd='/app',
            timeout=60
        )

        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': None,
            'error': 'Report generation timed out after 60 seconds'
        }
    except Exception as e:
        return {
            'success': False,
            'output': None,
            'error': str(e)
        }

"""Business logic for pub-sub event system management."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from common.db_utils import fetch_dict, db_transaction
import json


# =============================================================================
# Event Management
# =============================================================================

def list_events(
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List events with optional filters.

    Args:
        status: Filter by status (pending, processing, completed, failed)
        event_type: Filter by event type
        limit: Maximum records to return
        offset: Pagination offset

    Returns:
        List of event dictionaries
    """
    query = """
        SELECT
            event_id,
            event_type,
            event_source,
            event_data,
            status,
            priority,
            created_at,
            processed_at,
            completed_at,
            error_message,
            retry_count,
            max_retries
        FROM dba.tpubsub_events
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND status = %s"
        params.append(status)

    if event_type:
        query += " AND event_type = %s"
        params.append(event_type)

    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return fetch_dict(query, tuple(params)) or []


def get_event(event_id: int) -> Optional[Dict[str, Any]]:
    """Get single event by ID."""
    query = """
        SELECT *
        FROM dba.tpubsub_events
        WHERE event_id = %s
    """
    results = fetch_dict(query, (event_id,))
    return results[0] if results else None


def create_event(
    event_type: str,
    event_source: str,
    event_data: Dict[str, Any] = None,
    priority: int = 5
) -> int:
    """
    Create a new event in the queue.

    Args:
        event_type: Type of event
        event_source: Source identifier
        event_data: Optional JSON data
        priority: Priority (1-10, default 5)

    Returns:
        New event_id
    """
    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.tpubsub_events (
                event_type, event_source, event_data, priority, status, created_at
            ) VALUES (%s, %s, %s, %s, 'pending', CURRENT_TIMESTAMP)
            RETURNING event_id
        """, (
            event_type,
            event_source,
            json.dumps(event_data or {}),
            priority
        ))

        result = cursor.fetchone()
        return result[0]


def update_event_status(
    event_id: int,
    status: str,
    error_message: Optional[str] = None
) -> None:
    """Update event status."""
    with db_transaction() as cursor:
        if status in ('completed', 'failed', 'cancelled'):
            cursor.execute("""
                UPDATE dba.tpubsub_events
                SET status = %s, completed_at = CURRENT_TIMESTAMP, error_message = %s
                WHERE event_id = %s
            """, (status, error_message, event_id))
        elif status == 'processing':
            cursor.execute("""
                UPDATE dba.tpubsub_events
                SET status = %s, processed_at = CURRENT_TIMESTAMP
                WHERE event_id = %s
            """, (status, event_id))
        else:
            cursor.execute("""
                UPDATE dba.tpubsub_events
                SET status = %s
                WHERE event_id = %s
            """, (status, event_id))


def cancel_event(event_id: int) -> None:
    """Cancel a pending event."""
    update_event_status(event_id, 'cancelled')


def retry_event(event_id: int) -> None:
    """Reset a failed event for retry."""
    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE dba.tpubsub_events
            SET status = 'pending', error_message = NULL
            WHERE event_id = %s AND status = 'failed'
        """, (event_id,))


def get_event_stats() -> Dict[str, int]:
    """Get event statistics by status."""
    query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
        FROM dba.tpubsub_events
    """
    result = fetch_dict(query)
    if result:
        return {
            'total': result[0]['total'] or 0,
            'pending': result[0]['pending'] or 0,
            'processing': result[0]['processing'] or 0,
            'completed': result[0]['completed'] or 0,
            'failed': result[0]['failed'] or 0,
            'cancelled': result[0]['cancelled'] or 0
        }
    return {'total': 0, 'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0, 'cancelled': 0}


def get_recent_event_counts(days: int = 7) -> List[Dict[str, Any]]:
    """Get event counts per day for the last N days."""
    query = """
        SELECT
            DATE(created_at) as date,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM dba.tpubsub_events
        WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY DATE(created_at)
        ORDER BY date
    """
    return fetch_dict(query, (days,)) or []


# =============================================================================
# Subscriber Management
# =============================================================================

def list_subscribers(
    active_only: bool = False,
    event_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List subscribers with optional filters.

    Args:
        active_only: Only return active subscribers
        event_type: Filter by event type

    Returns:
        List of subscriber dictionaries
    """
    query = """
        SELECT
            s.*,
            CASE
                WHEN s.job_type = 'import' THEN ic.config_name
                WHEN s.job_type = 'inbox_processor' THEN inbox.config_name
                WHEN s.job_type = 'report' THEN rm.report_name
                ELSE NULL
            END as config_name
        FROM dba.tpubsub_subscribers s
        LEFT JOIN dba.timportconfig ic ON s.job_type = 'import' AND s.config_id = ic.config_id
        LEFT JOIN dba.tinboxconfig inbox ON s.job_type = 'inbox_processor' AND s.config_id = inbox.inbox_config_id
        LEFT JOIN dba.treportmanager rm ON s.job_type = 'report' AND s.config_id = rm.report_id
        WHERE 1=1
    """
    params = []

    if active_only:
        query += " AND s.is_active = TRUE"

    if event_type:
        query += " AND s.event_type = %s"
        params.append(event_type)

    query += " ORDER BY s.subscriber_id DESC"

    return fetch_dict(query, tuple(params) if params else None) or []


def get_subscriber(subscriber_id: int) -> Optional[Dict[str, Any]]:
    """Get single subscriber by ID."""
    query = """
        SELECT *
        FROM dba.tpubsub_subscribers
        WHERE subscriber_id = %s
    """
    results = fetch_dict(query, (subscriber_id,))
    return results[0] if results else None


def create_subscriber(subscriber_data: Dict[str, Any]) -> int:
    """
    Create a new subscriber.

    Args:
        subscriber_data: Subscriber configuration

    Returns:
        New subscriber_id
    """
    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.tpubsub_subscribers (
                subscriber_name, description, event_type, event_filter,
                job_type, config_id, script_path, is_active,
                created_at, last_modified_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING subscriber_id
        """, (
            subscriber_data['subscriber_name'],
            subscriber_data.get('description'),
            subscriber_data['event_type'],
            json.dumps(subscriber_data.get('event_filter', {})),
            subscriber_data['job_type'],
            subscriber_data.get('config_id'),
            subscriber_data.get('script_path'),
            subscriber_data.get('is_active', True)
        ))

        result = cursor.fetchone()
        return result[0]


def update_subscriber(subscriber_id: int, subscriber_data: Dict[str, Any]) -> None:
    """Update existing subscriber."""
    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE dba.tpubsub_subscribers
            SET
                subscriber_name = COALESCE(%s, subscriber_name),
                description = COALESCE(%s, description),
                event_type = COALESCE(%s, event_type),
                event_filter = COALESCE(%s, event_filter),
                job_type = COALESCE(%s, job_type),
                config_id = COALESCE(%s, config_id),
                script_path = COALESCE(%s, script_path),
                is_active = COALESCE(%s, is_active),
                last_modified_at = CURRENT_TIMESTAMP
            WHERE subscriber_id = %s
        """, (
            subscriber_data.get('subscriber_name'),
            subscriber_data.get('description'),
            subscriber_data.get('event_type'),
            json.dumps(subscriber_data['event_filter']) if 'event_filter' in subscriber_data else None,
            subscriber_data.get('job_type'),
            subscriber_data.get('config_id'),
            subscriber_data.get('script_path'),
            subscriber_data.get('is_active'),
            subscriber_id
        ))

        if cursor.rowcount == 0:
            raise Exception(f"Subscriber {subscriber_id} not found")


def delete_subscriber(subscriber_id: int) -> None:
    """Delete a subscriber."""
    with db_transaction() as cursor:
        cursor.execute(
            "DELETE FROM dba.tpubsub_subscribers WHERE subscriber_id = %s",
            (subscriber_id,)
        )
        if cursor.rowcount == 0:
            raise Exception(f"Subscriber {subscriber_id} not found")


def toggle_subscriber_active(subscriber_id: int, is_active: bool) -> None:
    """Toggle subscriber active status."""
    update_subscriber(subscriber_id, {'is_active': is_active})


def subscriber_name_exists(name: str, exclude_id: Optional[int] = None) -> bool:
    """Check if subscriber name exists."""
    query = "SELECT COUNT(*) as count FROM dba.tpubsub_subscribers WHERE subscriber_name = %s"
    params = [name]

    if exclude_id:
        query += " AND subscriber_id != %s"
        params.append(exclude_id)

    result = fetch_dict(query, tuple(params))
    return result[0]['count'] > 0 if result else False


def get_subscriber_stats() -> Dict[str, int]:
    """Get subscriber statistics."""
    query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN NOT is_active THEN 1 ELSE 0 END) as inactive,
            SUM(trigger_count) as total_triggers
        FROM dba.tpubsub_subscribers
    """
    result = fetch_dict(query)
    if result:
        return {
            'total': result[0]['total'] or 0,
            'active': result[0]['active'] or 0,
            'inactive': result[0]['inactive'] or 0,
            'total_triggers': result[0]['total_triggers'] or 0
        }
    return {'total': 0, 'active': 0, 'inactive': 0, 'total_triggers': 0}


# =============================================================================
# Configuration Lookup
# =============================================================================

def get_import_configs() -> List[Dict[str, Any]]:
    """Get list of import configurations for linking."""
    query = """
        SELECT config_id, config_name
        FROM dba.timportconfig
        WHERE is_active = TRUE
        ORDER BY config_name
    """
    return fetch_dict(query) or []


def get_inbox_configs() -> List[Dict[str, Any]]:
    """Get list of inbox configurations for linking."""
    query = """
        SELECT inbox_config_id as config_id, config_name
        FROM dba.tinboxconfig
        WHERE is_active = TRUE
        ORDER BY config_name
    """
    return fetch_dict(query) or []


def get_report_configs() -> List[Dict[str, Any]]:
    """Get list of report configurations for linking."""
    query = """
        SELECT report_id as config_id, report_name as config_name
        FROM dba.treportmanager
        WHERE is_active = TRUE
        ORDER BY report_name
    """
    return fetch_dict(query) or []


def get_event_types() -> List[str]:
    """Get available event types."""
    return ['file_received', 'email_received', 'import_complete', 'report_sent', 'custom']


def get_job_types() -> List[str]:
    """Get available job types."""
    return ['import', 'inbox_processor', 'report', 'custom']

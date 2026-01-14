"""Business logic for inbox configuration management"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from common.db_utils import fetch_dict, db_transaction
from admin.components.validators import check_regex_match, check_glob_match, check_patterns_batch


def list_inbox_configs(
    active_only: bool = False
) -> List[Dict[str, Any]]:
    """
    List inbox configurations with optional filters.

    Args:
        active_only: Only return active configs

    Returns:
        List of configuration dictionaries
    """
    query = """
        SELECT
            ic.*,
            imp.config_name as linked_import_name
        FROM dba.tinboxconfig ic
        LEFT JOIN dba.timportconfig imp ON ic.linked_import_config_id = imp.config_id
        WHERE 1=1
    """
    params = []

    if active_only:
        query += " AND ic.is_active = %s"
        params.append(True)

    query += " ORDER BY ic.inbox_config_id DESC"

    return fetch_dict(query, tuple(params) if params else None) or []


def get_inbox_config(inbox_config_id: int) -> Optional[Dict[str, Any]]:
    """
    Get single inbox configuration by ID.

    Args:
        inbox_config_id: Inbox configuration ID

    Returns:
        Configuration dictionary or None if not found
    """
    query = """
        SELECT
            ic.*,
            imp.config_name as linked_import_name
        FROM dba.tinboxconfig ic
        LEFT JOIN dba.timportconfig imp ON ic.linked_import_config_id = imp.config_id
        WHERE ic.inbox_config_id = %s
    """
    results = fetch_dict(query, (inbox_config_id,))
    return results[0] if results else None


def create_inbox_config(config_data: Dict[str, Any]) -> int:
    """
    Create new inbox configuration.

    Args:
        config_data: Dictionary of configuration fields

    Returns:
        New inbox_config_id

    Raises:
        Exception: For database errors
    """
    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.tinboxconfig (
                config_name, description, subject_pattern, sender_pattern,
                attachment_pattern, target_directory, date_prefix_format,
                save_eml, mark_processed, processed_label, error_label,
                linked_import_config_id, is_active, created_at, last_modified_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING inbox_config_id
        """, (
            config_data['config_name'],
            config_data.get('description'),
            config_data.get('subject_pattern'),
            config_data.get('sender_pattern'),
            config_data['attachment_pattern'],
            config_data.get('target_directory', '/app/data/source/inbox'),
            config_data.get('date_prefix_format', 'yyyyMMdd'),
            config_data.get('save_eml', False),
            config_data.get('mark_processed', True),
            config_data.get('processed_label', 'Processed'),
            config_data.get('error_label', 'ErrorFolder'),
            config_data.get('linked_import_config_id'),
            config_data.get('is_active', True),
            datetime.now(),
            datetime.now()
        ))

        result = cursor.fetchone()
        if not result:
            raise Exception("Failed to create inbox configuration")

        return result[0]


def update_inbox_config(inbox_config_id: int, config_data: Dict[str, Any]) -> None:
    """
    Update existing inbox configuration.

    Args:
        inbox_config_id: ID of configuration to update
        config_data: Dictionary of fields to update

    Raises:
        Exception: If configuration not found
    """
    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE dba.tinboxconfig
            SET
                config_name = COALESCE(%s, config_name),
                description = COALESCE(%s, description),
                subject_pattern = COALESCE(%s, subject_pattern),
                sender_pattern = COALESCE(%s, sender_pattern),
                attachment_pattern = COALESCE(%s, attachment_pattern),
                target_directory = COALESCE(%s, target_directory),
                date_prefix_format = COALESCE(%s, date_prefix_format),
                save_eml = COALESCE(%s, save_eml),
                mark_processed = COALESCE(%s, mark_processed),
                processed_label = COALESCE(%s, processed_label),
                error_label = COALESCE(%s, error_label),
                linked_import_config_id = COALESCE(%s, linked_import_config_id),
                is_active = COALESCE(%s, is_active),
                last_modified_at = %s
            WHERE inbox_config_id = %s
        """, (
            config_data.get('config_name'),
            config_data.get('description'),
            config_data.get('subject_pattern'),
            config_data.get('sender_pattern'),
            config_data.get('attachment_pattern'),
            config_data.get('target_directory'),
            config_data.get('date_prefix_format'),
            config_data.get('save_eml'),
            config_data.get('mark_processed'),
            config_data.get('processed_label'),
            config_data.get('error_label'),
            config_data.get('linked_import_config_id'),
            config_data.get('is_active'),
            datetime.now(),
            inbox_config_id
        ))

        if cursor.rowcount == 0:
            raise Exception(f"Inbox configuration {inbox_config_id} not found")


def delete_inbox_config(inbox_config_id: int) -> None:
    """
    Delete inbox configuration.

    Args:
        inbox_config_id: ID of configuration to delete

    Raises:
        Exception: If configuration not found or referenced
    """
    with db_transaction() as cursor:
        # Check for references in tscheduler
        cursor.execute(
            "SELECT COUNT(*) as count FROM dba.tscheduler WHERE job_type = 'inbox_processor' AND config_id = %s",
            (inbox_config_id,)
        )
        result = cursor.fetchone()
        if result and result[0] > 0:
            raise Exception(f"Inbox configuration {inbox_config_id} is referenced by schedules. Remove schedule references first.")

        cursor.execute(
            "DELETE FROM dba.tinboxconfig WHERE inbox_config_id = %s",
            (inbox_config_id,)
        )

        if cursor.rowcount == 0:
            raise Exception(f"Inbox configuration {inbox_config_id} not found")


def toggle_active(inbox_config_id: int, is_active: bool) -> None:
    """
    Toggle configuration active status.

    Args:
        inbox_config_id: ID of configuration
        is_active: New active status
    """
    update_inbox_config(inbox_config_id, {'is_active': is_active})


def get_inbox_stats() -> Dict[str, int]:
    """
    Get statistics about inbox configurations.

    Returns:
        Dictionary with total, active, inactive counts
    """
    query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN NOT is_active THEN 1 ELSE 0 END) as inactive
        FROM dba.tinboxconfig
    """
    result = fetch_dict(query)
    if result:
        return {
            'total': result[0]['total'] or 0,
            'active': result[0]['active'] or 0,
            'inactive': result[0]['inactive'] or 0
        }
    return {'total': 0, 'active': 0, 'inactive': 0}


def config_name_exists(config_name: str, exclude_id: Optional[int] = None) -> bool:
    """
    Check if a configuration name already exists.

    Args:
        config_name: Name to check
        exclude_id: Optional inbox_config_id to exclude (for updates)

    Returns:
        True if name exists, False otherwise
    """
    query = "SELECT COUNT(*) as count FROM dba.tinboxconfig WHERE config_name = %s"
    params = [config_name]

    if exclude_id is not None:
        query += " AND inbox_config_id != %s"
        params.append(exclude_id)

    result = fetch_dict(query, tuple(params))
    return result[0]['count'] > 0 if result else False


def get_import_configs() -> List[Dict[str, Any]]:
    """
    Get list of active import configurations for linking.

    Returns:
        List of import config dictionaries with config_id and config_name
    """
    query = """
        SELECT config_id, config_name
        FROM dba.timportconfig
        WHERE is_active = TRUE
        ORDER BY config_name
    """
    return fetch_dict(query) or []


# =============================================================================
# Pattern Testing Functions
# =============================================================================

def validate_subject_pattern(
    pattern: str,
    sample_subjects: List[str]
) -> List[Dict[str, Any]]:
    """
    Validate a subject pattern (regex) against sample email subjects.

    Args:
        pattern: Regex pattern to test
        sample_subjects: List of sample subject lines

    Returns:
        List of test results with match status and captured groups
    """
    return check_patterns_batch(pattern, sample_subjects, pattern_type='regex')


def validate_sender_pattern(
    pattern: str,
    sample_senders: List[str]
) -> List[Dict[str, Any]]:
    """
    Validate a sender pattern (regex) against sample email addresses.

    Args:
        pattern: Regex pattern to test
        sample_senders: List of sample sender addresses

    Returns:
        List of test results with match status and captured groups
    """
    return check_patterns_batch(pattern, sample_senders, pattern_type='regex')


def validate_attachment_pattern(
    pattern: str,
    sample_filenames: List[str]
) -> List[Dict[str, Any]]:
    """
    Validate an attachment pattern (glob) against sample filenames.

    Args:
        pattern: Glob pattern to test (e.g., *.csv, report_*.xlsx)
        sample_filenames: List of sample attachment filenames

    Returns:
        List of test results with match status
    """
    return check_patterns_batch(pattern, sample_filenames, pattern_type='glob')




def get_pattern_test_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of pattern test results.

    Args:
        results: List of test results from test_*_pattern functions

    Returns:
        Summary dictionary with counts and status
    """
    total = len(results)
    matches = sum(1 for r in results if r.get('matches', False))
    has_error = any(r.get('error') for r in results)

    return {
        'total': total,
        'matches': matches,
        'non_matches': total - matches,
        'match_rate': (matches / total * 100) if total > 0 else 0,
        'has_error': has_error,
        'pattern_valid': all(r.get('is_valid', False) for r in results) if results else False
    }

"""Business logic for import configuration management"""

from typing import List, Dict, Any, Optional
from common.db_utils import fetch_dict, db_transaction, execute_query
import psycopg2


def list_configs(
    active_only: bool = False,
    file_type: Optional[str] = None,
    strategy_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    List import configurations with optional filters.

    Args:
        active_only: Only return active configs
        file_type: Filter by file type (CSV, XLS, XLSX, JSON, XML)
        strategy_id: Filter by import strategy ID

    Returns:
        List of configuration dictionaries
    """
    query = """
        SELECT
            ic.*,
            ist.name as strategy_name,
            ist.description as strategy_description
        FROM dba.timportconfig ic
        LEFT JOIN dba.timportstrategy ist ON ic.importstrategyid = ist.importstrategyid
        WHERE 1=1
    """
    params = []

    if active_only:
        query += " AND ic.is_active = %s"
        params.append(True)

    if file_type:
        query += " AND ic.file_type = %s"
        params.append(file_type)

    if strategy_id:
        query += " AND ic.importstrategyid = %s"
        params.append(strategy_id)

    query += " ORDER BY ic.config_id DESC"

    return fetch_dict(query, tuple(params) if params else None)


def get_config(config_id: int) -> Optional[Dict[str, Any]]:
    """
    Get single configuration by ID.

    Args:
        config_id: Configuration ID

    Returns:
        Configuration dictionary or None if not found
    """
    query = """
        SELECT
            ic.*,
            ist.name as strategy_name,
            ist.description as strategy_description
        FROM dba.timportconfig ic
        LEFT JOIN dba.timportstrategy ist ON ic.importstrategyid = ist.importstrategyid
        WHERE ic.config_id = %s
    """
    results = fetch_dict(query, (config_id,))
    return results[0] if results else None


def create_config(config_data: Dict[str, Any]) -> int:
    """
    Create new import configuration.

    Calls the dba.pimportconfigi stored procedure.

    Args:
        config_data: Dictionary of configuration fields

    Returns:
        New config_id

    Raises:
        psycopg2.IntegrityError: If validation fails or duplicate name
        Exception: For other database errors
    """
    with db_transaction() as cursor:
        cursor.execute("""
            CALL dba.pimportconfigi(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            config_data['config_name'],
            config_data['datasource'],
            config_data['datasettype'],
            config_data['source_directory'],
            config_data['archive_directory'],
            config_data['file_pattern'],
            config_data['file_type'],
            config_data['metadata_label_source'],
            config_data.get('metadata_label_location'),
            config_data['dateconfig'],
            config_data.get('datelocation'),
            config_data.get('dateformat'),
            config_data.get('delimiter'),
            config_data['target_table'],
            config_data['importstrategyid'],
            config_data.get('is_active', True),
            config_data.get('is_blob', False)
        ))

        # Get the newly created config_id
        cursor.execute(
            "SELECT config_id FROM dba.timportconfig WHERE config_name = %s",
            (config_data['config_name'],)
        )
        result = cursor.fetchone()
        if not result:
            raise Exception("Failed to retrieve new config_id")

        return result[0]


def update_config(config_id: int, config_data: Dict[str, Any]) -> None:
    """
    Update existing import configuration.

    Calls the dba.pimportconfigu stored procedure.
    Only updates fields that are provided (partial updates supported).

    Args:
        config_id: ID of configuration to update
        config_data: Dictionary of fields to update

    Raises:
        Exception: If config not found or validation fails
    """
    with db_transaction() as cursor:
        cursor.execute("""
            CALL dba.pimportconfigu(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            config_id,
            config_data.get('config_name'),
            config_data.get('datasource'),
            config_data.get('datasettype'),
            config_data.get('source_directory'),
            config_data.get('archive_directory'),
            config_data.get('file_pattern'),
            config_data.get('file_type'),
            config_data.get('metadata_label_source'),
            config_data.get('metadata_label_location'),
            config_data.get('dateconfig'),
            config_data.get('datelocation'),
            config_data.get('dateformat'),
            config_data.get('delimiter'),
            config_data.get('target_table'),
            config_data.get('importstrategyid'),
            config_data.get('is_active'),
            config_data.get('is_blob')
        ))


def delete_config(config_id: int) -> None:
    """
    Delete import configuration.

    Note: This is a hard delete. Consider using soft delete
    (setting is_active=FALSE) in production to preserve history.

    Args:
        config_id: ID of configuration to delete

    Raises:
        Exception: If config not found or referenced by other records
    """
    with db_transaction() as cursor:
        # Check if config exists
        cursor.execute(
            "SELECT config_id FROM dba.timportconfig WHERE config_id = %s",
            (config_id,)
        )
        if not cursor.fetchone():
            raise Exception(f"Configuration {config_id} not found")

        # Delete the configuration
        cursor.execute(
            "DELETE FROM dba.timportconfig WHERE config_id = %s",
            (config_id,)
        )


def toggle_active(config_id: int, is_active: bool) -> None:
    """
    Toggle configuration active status.

    This is a safer alternative to deletion for temporarily
    disabling configurations.

    Args:
        config_id: ID of configuration
        is_active: New active status

    Raises:
        Exception: If config not found
    """
    update_config(config_id, {'is_active': is_active})


def count_configs(active_only: bool = True) -> int:
    """
    Count import configurations.

    Args:
        active_only: Only count active configs

    Returns:
        Configuration count
    """
    query = "SELECT COUNT(*) as count FROM dba.timportconfig"
    if active_only:
        query += " WHERE is_active = TRUE"

    result = fetch_dict(query)
    return result[0]['count'] if result else 0


def get_datasources() -> List[str]:
    """
    Get list of all datasource names.

    Returns:
        List of datasource names
    """
    query = "SELECT sourcename FROM dba.tdatasource ORDER BY sourcename"
    results = fetch_dict(query)
    return [row['sourcename'] for row in results] if results else []


def get_datasettypes() -> List[str]:
    """
    Get list of all dataset type names.

    Returns:
        List of dataset type names
    """
    query = "SELECT typename FROM dba.tdatasettype ORDER BY typename"
    results = fetch_dict(query)
    return [row['typename'] for row in results] if results else []


def get_strategies() -> List[Dict[str, Any]]:
    """
    Get list of all import strategies.

    Returns:
        List of strategy dictionaries with id, name, description
    """
    query = """
        SELECT importstrategyid, name, description
        FROM dba.timportstrategy
        ORDER BY importstrategyid
    """
    return fetch_dict(query)


def get_config_stats() -> Dict[str, int]:
    """
    Get statistics about import configurations.

    Returns:
        Dictionary with total, active, and inactive config counts
    """
    query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN NOT is_active THEN 1 ELSE 0 END) as inactive
        FROM dba.timportconfig
    """
    result = fetch_dict(query)
    if result:
        return {
            'total': result[0]['total'],
            'active': result[0]['active'] or 0,
            'inactive': result[0]['inactive'] or 0
        }
    return {'total': 0, 'active': 0, 'inactive': 0}


def config_name_exists(config_name: str, exclude_id: Optional[int] = None) -> bool:
    """
    Check if a configuration name already exists.

    Args:
        config_name: Name to check
        exclude_id: Optional config_id to exclude (for updates)

    Returns:
        True if name exists, False otherwise
    """
    query = "SELECT COUNT(*) as count FROM dba.timportconfig WHERE config_name = %s"
    params = [config_name]

    if exclude_id is not None:
        query += " AND config_id != %s"
        params.append(exclude_id)

    result = fetch_dict(query, tuple(params))
    return result[0]['count'] > 0 if result else False

"""Service layer for reference data management (datasources, datasettypes, strategies)"""

from typing import List, Dict, Any, Optional
from common.db_utils import fetch_dict, execute_query, db_transaction


# ============================================================================
# DATA SOURCE OPERATIONS
# ============================================================================

def list_datasources() -> List[Dict[str, Any]]:
    """
    Get all data sources.

    Returns:
        List of datasource dictionaries
    """
    query = """
        SELECT
            datasourceid,
            sourcename,
            description,
            createddate,
            createdby
        FROM dba.tdatasource
        ORDER BY sourcename
    """
    return fetch_dict(query) or []


def get_datasource(datasourceid: int) -> Optional[Dict[str, Any]]:
    """
    Get a single datasource by ID.

    Args:
        datasourceid: Datasource ID

    Returns:
        Datasource dictionary or None if not found
    """
    query = """
        SELECT
            datasourceid,
            sourcename,
            description,
            createddate,
            createdby
        FROM dba.tdatasource
        WHERE datasourceid = %s
    """
    result = fetch_dict(query, (datasourceid,))
    return result[0] if result else None


def create_datasource(sourcename: str, description: Optional[str] = None) -> int:
    """
    Create a new datasource.

    Args:
        sourcename: Unique name for the datasource
        description: Optional description

    Returns:
        New datasourceid

    Raises:
        Exception: If datasource name already exists or database error
    """
    with db_transaction() as cursor:
        cursor.execute(
            """
            INSERT INTO dba.tdatasource (sourcename, description)
            VALUES (%s, %s)
            RETURNING datasourceid
            """,
            (sourcename, description)
        )
        result = cursor.fetchone()
        if not result:
            raise Exception("Failed to retrieve new datasourceid")
        return result[0]


def update_datasource(
    datasourceid: int,
    sourcename: Optional[str] = None,
    description: Optional[str] = None
) -> None:
    """
    Update an existing datasource.

    Args:
        datasourceid: Datasource ID to update
        sourcename: Optional new name
        description: Optional new description

    Raises:
        Exception: If datasource not found or database error
    """
    updates = []
    params = []

    if sourcename is not None:
        updates.append("sourcename = %s")
        params.append(sourcename)

    if description is not None:
        updates.append("description = %s")
        params.append(description)

    if not updates:
        return  # Nothing to update

    params.append(datasourceid)

    with db_transaction() as cursor:
        cursor.execute(
            f"""
            UPDATE dba.tdatasource
            SET {', '.join(updates)}
            WHERE datasourceid = %s
            """,
            tuple(params)
        )
        if cursor.rowcount == 0:
            raise Exception(f"Datasource {datasourceid} not found")


def delete_datasource(datasourceid: int) -> None:
    """
    Delete a datasource.

    Args:
        datasourceid: Datasource ID to delete

    Raises:
        Exception: If datasource not found or referenced by other records
    """
    with db_transaction() as cursor:
        # Check if datasource is referenced by any import configs
        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM dba.timportconfig
            WHERE datasource = (
                SELECT sourcename FROM dba.tdatasource WHERE datasourceid = %s
            )
            """,
            (datasourceid,)
        )
        result = cursor.fetchone()
        if result and result[0] > 0:
            raise Exception(
                f"Cannot delete datasource: referenced by {result[0]} import configuration(s). "
                "Delete or update those configurations first."
            )

        # Delete the datasource
        cursor.execute(
            "DELETE FROM dba.tdatasource WHERE datasourceid = %s",
            (datasourceid,)
        )
        if cursor.rowcount == 0:
            raise Exception(f"Datasource {datasourceid} not found")


def datasource_name_exists(sourcename: str, exclude_id: Optional[int] = None) -> bool:
    """
    Check if a datasource name already exists.

    Args:
        sourcename: Name to check
        exclude_id: Optional datasourceid to exclude (for updates)

    Returns:
        True if name exists, False otherwise
    """
    query = "SELECT COUNT(*) as count FROM dba.tdatasource WHERE sourcename = %s"
    params = [sourcename]

    if exclude_id is not None:
        query += " AND datasourceid != %s"
        params.append(exclude_id)

    result = fetch_dict(query, tuple(params))
    return result[0]['count'] > 0 if result else False


# ============================================================================
# DATASET TYPE OPERATIONS
# ============================================================================

def list_datasettypes() -> List[Dict[str, Any]]:
    """
    Get all dataset types.

    Returns:
        List of datasettype dictionaries
    """
    query = """
        SELECT
            datasettypeid,
            typename,
            description,
            createddate,
            createdby
        FROM dba.tdatasettype
        ORDER BY typename
    """
    return fetch_dict(query) or []


def get_datasettype(datasettypeid: int) -> Optional[Dict[str, Any]]:
    """
    Get a single dataset type by ID.

    Args:
        datasettypeid: Dataset type ID

    Returns:
        Dataset type dictionary or None if not found
    """
    query = """
        SELECT
            datasettypeid,
            typename,
            description,
            createddate,
            createdby
        FROM dba.tdatasettype
        WHERE datasettypeid = %s
    """
    result = fetch_dict(query, (datasettypeid,))
    return result[0] if result else None


def create_datasettype(typename: str, description: Optional[str] = None) -> int:
    """
    Create a new dataset type.

    Args:
        typename: Unique name for the dataset type
        description: Optional description

    Returns:
        New datasettypeid

    Raises:
        Exception: If typename already exists or database error
    """
    with db_transaction() as cursor:
        cursor.execute(
            """
            INSERT INTO dba.tdatasettype (typename, description)
            VALUES (%s, %s)
            RETURNING datasettypeid
            """,
            (typename, description)
        )
        result = cursor.fetchone()
        if not result:
            raise Exception("Failed to retrieve new datasettypeid")
        return result[0]


def update_datasettype(
    datasettypeid: int,
    typename: Optional[str] = None,
    description: Optional[str] = None
) -> None:
    """
    Update an existing dataset type.

    Args:
        datasettypeid: Dataset type ID to update
        typename: Optional new name
        description: Optional new description

    Raises:
        Exception: If dataset type not found or database error
    """
    updates = []
    params = []

    if typename is not None:
        updates.append("typename = %s")
        params.append(typename)

    if description is not None:
        updates.append("description = %s")
        params.append(description)

    if not updates:
        return  # Nothing to update

    params.append(datasettypeid)

    with db_transaction() as cursor:
        cursor.execute(
            f"""
            UPDATE dba.tdatasettype
            SET {', '.join(updates)}
            WHERE datasettypeid = %s
            """,
            tuple(params)
        )
        if cursor.rowcount == 0:
            raise Exception(f"Dataset type {datasettypeid} not found")


def delete_datasettype(datasettypeid: int) -> None:
    """
    Delete a dataset type.

    Args:
        datasettypeid: Dataset type ID to delete

    Raises:
        Exception: If dataset type not found or referenced by other records
    """
    with db_transaction() as cursor:
        # Check if dataset type is referenced by any import configs
        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM dba.timportconfig
            WHERE datasettype = (
                SELECT typename FROM dba.tdatasettype WHERE datasettypeid = %s
            )
            """,
            (datasettypeid,)
        )
        result = cursor.fetchone()
        if result and result[0] > 0:
            raise Exception(
                f"Cannot delete dataset type: referenced by {result[0]} import configuration(s). "
                "Delete or update those configurations first."
            )

        # Delete the dataset type
        cursor.execute(
            "DELETE FROM dba.tdatasettype WHERE datasettypeid = %s",
            (datasettypeid,)
        )
        if cursor.rowcount == 0:
            raise Exception(f"Dataset type {datasettypeid} not found")


def datasettype_name_exists(typename: str, exclude_id: Optional[int] = None) -> bool:
    """
    Check if a dataset type name already exists.

    Args:
        typename: Name to check
        exclude_id: Optional datasettypeid to exclude (for updates)

    Returns:
        True if name exists, False otherwise
    """
    query = "SELECT COUNT(*) as count FROM dba.tdatasettype WHERE typename = %s"
    params = [typename]

    if exclude_id is not None:
        query += " AND datasettypeid != %s"
        params.append(exclude_id)

    result = fetch_dict(query, tuple(params))
    return result[0]['count'] > 0 if result else False


# ============================================================================
# IMPORT STRATEGY OPERATIONS (READ-ONLY)
# ============================================================================

def list_strategies() -> List[Dict[str, Any]]:
    """
    Get all import strategies (read-only).

    Returns:
        List of strategy dictionaries
    """
    query = """
        SELECT
            importstrategyid,
            name,
            description,
            createddate,
            createdby
        FROM dba.timportstrategy
        ORDER BY importstrategyid
    """
    return fetch_dict(query) or []


def get_strategy(importstrategyid: int) -> Optional[Dict[str, Any]]:
    """
    Get a single import strategy by ID.

    Args:
        importstrategyid: Strategy ID

    Returns:
        Strategy dictionary or None if not found
    """
    query = """
        SELECT
            importstrategyid,
            name,
            description,
            createddate,
            createdby
        FROM dba.timportstrategy
        WHERE importstrategyid = %s
    """
    result = fetch_dict(query, (importstrategyid,))
    return result[0] if result else None


# ============================================================================
# USAGE QUERIES
# ============================================================================

def get_datasource_usage(sourcename: str) -> List[str]:
    """
    Get list of import config names that reference a datasource.

    Args:
        sourcename: Name of the datasource

    Returns:
        List of config_name strings that use this datasource
    """
    query = """
        SELECT config_name
        FROM dba.timportconfig
        WHERE datasource = %s
        ORDER BY config_name
    """
    result = fetch_dict(query, (sourcename,))
    return [r['config_name'] for r in result] if result else []


def get_datasettype_usage(typename: str) -> List[str]:
    """
    Get list of import config names that reference a dataset type.

    Args:
        typename: Name of the dataset type

    Returns:
        List of config_name strings that use this dataset type
    """
    query = """
        SELECT config_name
        FROM dba.timportconfig
        WHERE datasettype = %s
        ORDER BY config_name
    """
    result = fetch_dict(query, (typename,))
    return [r['config_name'] for r in result] if result else []


def get_datasource_usage_count(sourcename: str) -> int:
    """
    Get count of import configs that reference a datasource.

    Args:
        sourcename: Name of the datasource

    Returns:
        Count of configs using this datasource
    """
    query = """
        SELECT COUNT(*) as count
        FROM dba.timportconfig
        WHERE datasource = %s
    """
    result = fetch_dict(query, (sourcename,))
    return result[0]['count'] if result else 0


def get_datasettype_usage_count(typename: str) -> int:
    """
    Get count of import configs that reference a dataset type.

    Args:
        typename: Name of the dataset type

    Returns:
        Count of configs using this dataset type
    """
    query = """
        SELECT COUNT(*) as count
        FROM dba.timportconfig
        WHERE datasettype = %s
    """
    result = fetch_dict(query, (typename,))
    return result[0]['count'] if result else 0


# ============================================================================
# STATISTICS
# ============================================================================

def get_reference_stats() -> Dict[str, int]:
    """
    Get statistics about reference data.

    Returns:
        Dictionary with counts for datasources, datasettypes, and strategies
    """
    query_datasources = "SELECT COUNT(*) as count FROM dba.tdatasource"
    query_datasettypes = "SELECT COUNT(*) as count FROM dba.tdatasettype"
    query_strategies = "SELECT COUNT(*) as count FROM dba.timportstrategy"

    datasources_count = fetch_dict(query_datasources)
    datasettypes_count = fetch_dict(query_datasettypes)
    strategies_count = fetch_dict(query_strategies)

    return {
        'datasources': datasources_count[0]['count'] if datasources_count else 0,
        'datasettypes': datasettypes_count[0]['count'] if datasettypes_count else 0,
        'strategies': strategies_count[0]['count'] if strategies_count else 0
    }

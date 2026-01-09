"""Database-specific test fixtures

This module provides fixtures for database operations, log entries,
and dataset records.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List


def get_sample_log_entry(
    run_uuid: Optional[str] = None,
    processtype: str = 'GenericImportJob',
    stepcounter: int = 1,
    message: str = 'Test log message',
    stepruntime: float = 0.5
) -> Dict[str, Any]:
    """
    Returns a sample log entry dictionary.

    Args:
        run_uuid: Run UUID (auto-generated if None)
        processtype: Process type
        stepcounter: Step counter
        message: Log message
        stepruntime: Step runtime in seconds

    Returns:
        Dictionary with log entry fields
    """
    if run_uuid is None:
        run_uuid = str(uuid.uuid4())

    return {
        'run_uuid': run_uuid,
        'processtype': processtype,
        'stepcounter': stepcounter,
        'message': message,
        'stepruntime': stepruntime,
        'timestamp': datetime.now()
    }


def get_multiple_log_entries(
    count: int = 10,
    run_uuid: Optional[str] = None,
    process_types: Optional[List[str]] = None,
    time_range_hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Returns list of sample log entries.

    Args:
        count: Number of log entries to generate
        run_uuid: Run UUID (auto-generated if None, same for all)
        process_types: List of process types to rotate through
        time_range_hours: Distribute entries over this time range

    Returns:
        List of log entry dictionaries
    """
    if run_uuid is None:
        run_uuid = str(uuid.uuid4())

    if process_types is None:
        process_types = ['GenericImportJob', 'DataValidation', 'DataTransform']

    logs = []
    time_increment = timedelta(hours=time_range_hours) / count

    for i in range(count):
        timestamp = datetime.now() - timedelta(hours=time_range_hours) + (time_increment * i)
        logs.append({
            'run_uuid': run_uuid,
            'processtype': process_types[i % len(process_types)],
            'stepcounter': i + 1,
            'message': f'Test log message {i}',
            'stepruntime': 0.1 * (i + 1),
            'timestamp': timestamp
        })

    return logs


def get_sample_dataset(
    label: Optional[str] = None,
    datasourceid: int = 1,
    datasettypeid: int = 1,
    datastatusid: int = 1,
    isactive: bool = True
) -> Dict[str, Any]:
    """
    Returns a sample dataset dictionary.

    Args:
        label: Dataset label (auto-generated if None)
        datasourceid: Datasource ID
        datasettypeid: Dataset type ID
        datastatusid: Data status ID
        isactive: Active status

    Returns:
        Dictionary with dataset fields
    """
    if label is None:
        label = f'AdminTest_Dataset_{uuid.uuid4().hex[:8]}'

    now = datetime.now()
    return {
        'label': label,
        'datasourceid': datasourceid,
        'datasettypeid': datasettypeid,
        'datastatusid': datastatusid,
        'createddate': now,
        'efffromdate': now,
        'effthrudate': now + timedelta(days=365),
        'isactive': isactive
    }


def get_multiple_datasets(
    count: int = 10,
    datasourceid: int = 1,
    datasettypeid: int = 1,
    date_range_days: int = 30
) -> List[Dict[str, Any]]:
    """
    Returns list of sample datasets distributed over a date range.

    Args:
        count: Number of datasets to generate
        datasourceid: Datasource ID
        datasettypeid: Dataset type ID
        date_range_days: Distribute datasets over this many days

    Returns:
        List of dataset dictionaries
    """
    datasets = []
    time_increment = timedelta(days=date_range_days) / count

    for i in range(count):
        created_date = datetime.now() - timedelta(days=date_range_days) + (time_increment * i)
        dataset = get_sample_dataset(
            datasourceid=datasourceid,
            datasettypeid=datasettypeid,
            isactive=i % 2 == 0  # Alternate active/inactive
        )
        dataset['createddate'] = created_date
        datasets.append(dataset)

    return datasets


def insert_log_entries(cursor, log_entries: List[Dict[str, Any]]) -> List[int]:
    """
    Insert multiple log entries and return their IDs.

    Args:
        cursor: Database cursor
        log_entries: List of log entry dictionaries

    Returns:
        List of logentryid values
    """
    ids = []
    for log in log_entries:
        cursor.execute("""
            INSERT INTO dba.tlogentry (
                run_uuid, processtype, stepcounter, message, stepruntime, timestamp
            ) VALUES (
                %(run_uuid)s, %(processtype)s, %(stepcounter)s,
                %(message)s, %(stepruntime)s, %(timestamp)s
            )
            RETURNING logentryid
        """, log)
        ids.append(cursor.fetchone()['logentryid'])

    return ids


def insert_datasets(cursor, datasets: List[Dict[str, Any]]) -> List[int]:
    """
    Insert multiple datasets and return their IDs.

    Args:
        cursor: Database cursor
        datasets: List of dataset dictionaries

    Returns:
        List of datasetid values
    """
    ids = []
    for dataset in datasets:
        cursor.execute("""
            INSERT INTO dba.tdataset (
                label, datasourceid, datasettypeid, datastatusid,
                createddate, efffromdate, effthrudate, isactive
            ) VALUES (
                %(label)s, %(datasourceid)s, %(datasettypeid)s, %(datastatusid)s,
                %(createddate)s, %(efffromdate)s, %(effthrudate)s, %(isactive)s
            )
            RETURNING datasetid
        """, dataset)
        ids.append(cursor.fetchone()['datasetid'])

    return ids

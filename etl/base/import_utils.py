"""
Shared utilities for ETL import scripts.

Provides common functions for saving JSON, running generic imports,
parsing dates/numbers, and generating audit columns.
"""

import json
from datetime import datetime
from pathlib import Path

from common.db_utils import fetch_dict
from common.logging_utils import get_logger

logger = get_logger('import_utils')


def get_config_id(config_name: str) -> int:
    """Lookup config_id by config_name from dba.timportconfig."""
    rows = fetch_dict(
        "SELECT config_id FROM dba.timportconfig "
        "WHERE config_name = %s AND is_active = TRUE",
        (config_name,)
    )
    if not rows:
        raise ValueError(f"Config '{config_name}' not found or inactive in dba.timportconfig")
    return rows[0]['config_id']


def save_json(data: list, config_name: str, source: str) -> Path:
    """Save JSON array to /app/data/source/{source}/{source}_{slug}_{timestamp}.json"""
    source_dir = Path(f"/app/data/source/{source}")
    source_dir.mkdir(parents=True, exist_ok=True)

    # Derive slug from config_name: e.g. 'NewYorkFed_ReferenceRates_Latest' -> 'referencerates_latest'
    prefix_map = {
        'newyorkfed': 'NewYorkFed_',
        'bankofengland': 'BankOfEngland_',
    }
    prefix = prefix_map.get(source, '')
    slug = config_name.replace(prefix, '').lower()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source}_{slug}_{timestamp}.json"
    filepath = source_dir / filename

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved {len(data)} records to {filepath}")
    return filepath


def run_generic_import(config_name: str, dry_run: bool = False) -> int:
    """Lookup config_id by name, run GenericImportJob. Returns 0 on success, 1 on failure."""
    from etl.jobs.generic_import import GenericImportJob, ConfigNotFoundError

    try:
        config_id = get_config_id(config_name)
    except ValueError as e:
        logger.error(str(e))
        return 1

    try:
        job = GenericImportJob(config_id=config_id, dry_run=dry_run)
    except ConfigNotFoundError as e:
        logger.error(f"Config not found: {e}")
        return 1

    print(f"Run UUID: {job.run_uuid}")

    try:
        job.run()
        logger.info(
            f"Import completed: {job.records_loaded} records loaded "
            f"from {len(job.matched_files)} file(s)"
        )
        return 0
    except Exception as e:
        logger.error(f"Generic import failed: {e}")
        return 1


def parse_date(value: str) -> str | None:
    """Parse YYYY-MM-DD to ISO date string, or None."""
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d').strftime('%Y-%m-%d')


def parse_numeric(value, strip_commas: bool = False) -> float | None:
    """Parse numeric value, optionally stripping commas."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if strip_commas:
        value = str(value).replace(',', '')
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None


def audit_cols() -> dict:
    """Return {'created_date': ..., 'created_by': 'etl_user'}."""
    return {
        'created_date': datetime.now().isoformat(),
        'created_by': 'etl_user',
    }

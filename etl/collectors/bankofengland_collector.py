"""
Bank of England data collector.

Fetches data from Bank of England APIs, applies source-specific transforms,
saves JSON to the source directory, then runs generic_import to load into
the database.

Usage:
    python etl/collectors/bankofengland_collector.py --config-id 13
    python etl/collectors/bankofengland_collector.py --config-id 13 --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from common.db_utils import fetch_dict, db_transaction
from common.logging_utils import get_logger
from etl.clients.bankofengland_client import BankOfEnglandAPIClient

SOURCE_DIR = Path("/app/data/source/bankofengland")

logger = get_logger('bankofengland_collector')


# ---------------------------------------------------------------------------
# Shared infrastructure
# ---------------------------------------------------------------------------

def load_config(config_id: int) -> dict:
    """Load import config from timportconfig."""
    rows = fetch_dict(
        "SELECT config_id, config_name, api_base_url, api_endpoint_path, "
        "api_response_root_path, api_response_format, source_directory, file_pattern "
        "FROM dba.timportconfig WHERE config_id = %s AND is_active = TRUE",
        (config_id,)
    )
    if not rows:
        raise ValueError(f"Config ID {config_id} not found or inactive")
    return rows[0]


def save_json(data: list, config: dict) -> Path:
    """Save transformed data as JSON file in source directory."""
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    slug = config['config_name'].replace('BankOfEngland_', '').lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bankofengland_{slug}_{timestamp}.json"
    filepath = SOURCE_DIR / filename

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved {len(data)} records to {filepath}")
    return filepath


def ensure_source_directory(config_id: int):
    """Update timportconfig.source_directory if not already set."""
    rows = fetch_dict(
        "SELECT source_directory FROM dba.timportconfig WHERE config_id = %s",
        (config_id,)
    )
    if rows and (not rows[0]['source_directory'] or rows[0]['source_directory'].strip() == ''):
        with db_transaction() as cursor:
            cursor.execute(
                "UPDATE dba.timportconfig SET source_directory = %s WHERE config_id = %s",
                (str(SOURCE_DIR), config_id)
            )
        logger.info(f"Updated source_directory to {SOURCE_DIR} for config {config_id}")


def run_generic_import(config_id: int, dry_run: bool) -> bool:
    """Run the generic import for the saved JSON file."""
    from etl.jobs.generic_import import GenericImportJob, ConfigNotFoundError

    try:
        job = GenericImportJob(config_id=config_id, dry_run=dry_run)
    except ConfigNotFoundError as e:
        logger.error(f"Config not found: {e}")
        return False

    print(f"Run UUID: {job.run_uuid}")

    try:
        job.run()
        logger.info(
            f"Import completed: {job.records_loaded} records loaded "
            f"from {len(job.matched_files)} file(s)"
        )
        return True
    except Exception as e:
        logger.error(f"Generic import failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------

def fetch_sonia_rates(config: dict) -> list:
    """Fetch SONIA rates from Bank of England IADB."""
    base_url = config.get('api_base_url') or 'https://www.bankofengland.co.uk'
    client = BankOfEnglandAPIClient(base_url=base_url)
    try:
        logger.info("Fetching SONIA rates from Bank of England")
        data = client.get_sonia_rates(days=60)
        logger.info(f"Fetched {len(data)} SONIA rate records")
        return data
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Transform functions
# ---------------------------------------------------------------------------

def transform_sonia_rates(raw_data: list) -> list:
    """
    Transform raw BoE SONIA CSV data to database schema.

    - Parse date strings ('03 Jan 2025') to ISO date strings
    - Coerce rate strings to float
    - Skip records with missing or non-numeric rates
    - Add audit columns
    """
    transformed = []
    now = datetime.now().isoformat()

    for record in raw_data:
        date_str = record.get('date')
        rate_str = record.get('rate')

        if not date_str or not rate_str:
            logger.warning(f"Skipping record with missing data: {record}")
            continue

        try:
            rate_value = float(rate_str)
        except (ValueError, TypeError):
            logger.warning(f"Skipping non-numeric rate: {rate_str} for date {date_str}")
            continue

        # Parse BoE date format '03 Jan 2025' to ISO '2025-01-03'
        effective_date = datetime.strptime(date_str, '%d %b %Y').strftime('%Y-%m-%d')

        transformed.append({
            'effective_date': effective_date,
            'rate_percent': rate_value,
            'created_date': now,
            'created_by': 'etl_user'
        })

    logger.info(f"Transformed {len(transformed)} SONIA rate records")
    return transformed


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

COLLECTORS = {
    'BankOfEngland_SONIA_Rates': {
        'fetch': fetch_sonia_rates,
        'transform': transform_sonia_rates,
    },
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Fetch Bank of England API data, transform, and import via generic import'
    )
    parser.add_argument('--config-id', type=int, required=True, help='Config ID from dba.timportconfig')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    if not os.getenv('DB_URL'):
        print("ERROR: DB_URL environment variable not set")
        return 1

    try:
        # 1. Load config
        config = load_config(args.config_id)
        config_name = config['config_name']
        logger.info(f"Loaded config: {config_name} (id={args.config_id})")

        # 2. Lookup collector
        collector = COLLECTORS.get(config_name)
        if not collector:
            logger.error(f"No collector registered for config '{config_name}'")
            print(f"ERROR: No collector registered for config '{config_name}'")
            print(f"Available collectors: {', '.join(COLLECTORS.keys())}")
            return 1

        # 3. Fetch data from API
        raw_data = collector['fetch'](config)
        if not raw_data:
            logger.warning("No data returned from API")
            print("No data returned from API")
            return 0

        # 4. Transform
        transformed = collector['transform'](raw_data)
        if not transformed:
            logger.warning("No records after transform")
            print("No records after transform")
            return 0

        # 5. Save JSON to source directory
        filepath = save_json(transformed, config)
        print(f"Saved {len(transformed)} records to {filepath}")

        # 6. Ensure source_directory is set in config
        ensure_source_directory(args.config_id)

        # 7. Run generic import
        success = run_generic_import(args.config_id, args.dry_run)
        if success:
            print(f"Import completed successfully for config {args.config_id}")
            return 0
        else:
            print(f"Import failed for config {args.config_id}")
            return 1

    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        print(f"ERROR: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

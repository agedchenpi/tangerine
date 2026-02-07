"""
Unified NewYorkFed API fetch + generic import runner.

Fetches data from the NewYorkFed Markets API using config-driven endpoint paths
from timportconfig, saves JSON to the source directory, then runs the generic
import to load the file into the database.

Usage:
    python etl/jobs/run_newyorkfed_api_import.py --config-id 1
    python etl/jobs/run_newyorkfed_api_import.py --config-id 1 --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from common.db_utils import fetch_dict, db_transaction
from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient

SOURCE_DIR = Path("/app/data/source/newyorkfed")


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


def fetch_data(config: dict, logger) -> list:
    """Fetch data from NewYorkFed API using endpoint config from timportconfig."""
    endpoint_path = config.get('api_endpoint_path')
    if not endpoint_path:
        raise ValueError(f"No api_endpoint_path set for config '{config['config_name']}'")

    response_format = config.get('api_response_format') or 'json'
    response_root_path = config.get('api_response_root_path')
    base_url = config.get('api_base_url') or 'https://markets.newyorkfed.org'

    client = NewYorkFedAPIClient(base_url=base_url)
    try:
        logger.info(f"Fetching {endpoint_path} (root_path={response_root_path})")
        data = client.fetch_endpoint(
            endpoint_path=endpoint_path,
            response_format=response_format,
            response_root_path=response_root_path,
        )
        logger.info(f"Fetched {len(data)} records")
        return data
    finally:
        client.close()


def save_json(data: list, config: dict, logger) -> Path:
    """Save API response as JSON file in source directory."""
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    # Build filename slug from config_name: NewYorkFed_SOMA_Holdings -> soma_holdings
    slug = config['config_name'].replace('NewYorkFed_', '').lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"newyorkfed_{slug}_{timestamp}.json"
    filepath = SOURCE_DIR / filename

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved {len(data)} records to {filepath}")
    return filepath


def ensure_source_directory(config_id: int, logger):
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


def run_generic_import(config_id: int, dry_run: bool, logger) -> bool:
    """Run the generic import for the saved JSON file."""
    from etl.jobs.generic_import import GenericImportJob, ConfigNotFoundError

    try:
        job = GenericImportJob(config_id=config_id, dry_run=dry_run)
    except ConfigNotFoundError as e:
        logger.error(f"Config not found: {e}")
        return False

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


def main():
    parser = argparse.ArgumentParser(
        description='Fetch NewYorkFed API data and import via generic import'
    )
    parser.add_argument('--config-id', type=int, required=True, help='Config ID from dba.timportconfig')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    if not os.getenv('DB_URL'):
        print("ERROR: DB_URL environment variable not set")
        return 1

    logger = get_logger('run_newyorkfed_api_import')

    try:
        # 1. Load config
        config = load_config(args.config_id)
        logger.info(f"Loaded config: {config['config_name']} (id={args.config_id})")

        # 2. Fetch data from API
        data = fetch_data(config, logger)
        if not data:
            logger.warning("No data returned from API")
            print("No data returned from API")
            return 0

        # 3. Save JSON to source directory
        filepath = save_json(data, config, logger)
        print(f"Saved {len(data)} records to {filepath}")

        # 4. Ensure source_directory is set in config
        ensure_source_directory(args.config_id, logger)

        # 5. Run generic import
        success = run_generic_import(args.config_id, args.dry_run, logger)
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

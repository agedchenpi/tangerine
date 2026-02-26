"""
Fetch and import NewYorkFed Primary Dealer Statistics (passthrough, no transform).

Usage:
    python etl/jobs/run_newyorkfed_pd_statistics.py
    python etl/jobs/run_newyorkfed_pd_statistics.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import

CONFIG_NAME = 'NewYorkFed_PD_Statistics'

logger = get_logger('run_newyorkfed_pd_statistics')


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed PD Statistics')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    client = NewYorkFedAPIClient()
    try:
        raw_data = client.fetch_endpoint(
            endpoint_path='/api/pd/get/all/timeseries.{format}',
            response_root_path='pd',
        )
    finally:
        client.close()

    if not raw_data:
        print("No data returned from API")
        return 0

    logger.info(f"Passthrough: {len(raw_data)} records (no transform)")
    save_json(raw_data, CONFIG_NAME, source='newyorkfed')
    return run_generic_import(CONFIG_NAME, args.dry_run)


if __name__ == '__main__':
    sys.exit(main())

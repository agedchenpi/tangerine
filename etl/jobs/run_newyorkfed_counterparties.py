"""
Fetch and import NewYorkFed FX Swap counterparties.

Usage:
    python etl/jobs/run_newyorkfed_counterparties.py
    python etl/jobs/run_newyorkfed_counterparties.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, audit_cols

CONFIG_NAME = 'NewYorkFed_Counterparties'

logger = get_logger('run_newyorkfed_counterparties')


def transform(data: list) -> list:
    """Transform FX swap counterparties list."""
    transformed = []
    for record in data:
        counterparty_name = record.get('counterparty_name')
        if not counterparty_name:
            logger.warning(f"Skipping record with no counterparty name: {record}")
            continue

        transformed.append({
            'counterparty_name': counterparty_name,
            'counterparty_type': 'Central Bank',
            'is_active': True,
            **audit_cols(),
        })

    logger.info(f"Transformed {len(transformed)} counterparty records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed Counterparties')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    client = NewYorkFedAPIClient()
    try:
        raw_data = client.get_counterparties()
    finally:
        client.close()

    if not raw_data:
        print("No data returned from API")
        return 0

    transformed = transform(raw_data)
    if not transformed:
        print("No records after transform")
        return 0

    save_json(transformed, CONFIG_NAME, source='newyorkfed')
    return run_generic_import(CONFIG_NAME, args.dry_run)


if __name__ == '__main__':
    sys.exit(main())

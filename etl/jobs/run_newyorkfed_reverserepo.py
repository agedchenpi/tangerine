"""
Fetch and import NewYorkFed Reverse Repo Operations.

Usage:
    python etl/jobs/run_newyorkfed_reverserepo.py
    python etl/jobs/run_newyorkfed_reverserepo.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, parse_date, audit_cols

CONFIG_NAME = 'NewYorkFed_ReverseRepo_Operations'

logger = get_logger('run_newyorkfed_reverserepo')


def transform(data: list) -> list:
    """Transform reverse repo operations."""
    transformed = []
    for record in data:
        try:
            operation_type_raw = record.get('operationType', '').lower().replace(' ', '')

            transformed.append({
                'operation_date': parse_date(record.get('operationDate')),
                'operation_type': operation_type_raw,
                'operation_id': record.get('operationId'),
                'maturity_date': parse_date(record.get('maturityDate')),
                'term_days': record.get('termCalenderDays'),
                'operation_status': record.get('auctionStatus'),
                'amount_submitted': record.get('totalAmtSubmitted'),
                'amount_accepted': record.get('totalAmtAccepted'),
                'award_rate': None,
                **audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform reverse repo record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} reverse repo operation records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed Reverse Repo Operations')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    client = NewYorkFedAPIClient()
    try:
        raw_data = client.get_repo_operations()
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

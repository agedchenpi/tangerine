"""
Fetch and import NewYorkFed Treasury securities operations.

Usage:
    python etl/jobs/run_newyorkfed_treasury.py
    python etl/jobs/run_newyorkfed_treasury.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, parse_date, audit_cols

CONFIG_NAME = 'NewYorkFed_Treasury_Operations'

logger = get_logger('run_newyorkfed_treasury')


def transform(data: list) -> list:
    """Transform Treasury securities operations."""
    transformed = []
    for record in data:
        try:
            transformed.append({
                'operation_date': parse_date(record.get('operationDate')),
                'operation_type': record.get('operationType'),
                'cusip': record.get('cusip'),
                'security_description': record.get('securityDescription'),
                'issue_date': parse_date(record.get('issueDate')),
                'maturity_date': parse_date(record.get('maturityDate')),
                'coupon_rate': record.get('couponRate'),
                'security_term': record.get('securityTerm'),
                'operation_amount': record.get('operationAmount'),
                'total_submitted': record.get('totalAmtSubmitted'),
                'total_accepted': record.get('totalAmtAccepted'),
                'high_price': record.get('highPrice'),
                'low_price': record.get('lowPrice'),
                'stop_out_rate': record.get('stopOutRate'),
                **audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform Treasury record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} Treasury operation records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed Treasury Operations')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    client = NewYorkFedAPIClient()
    try:
        raw_data = client.get_treasury_operations()
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

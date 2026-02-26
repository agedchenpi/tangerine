"""
Fetch and import NewYorkFed SOMA monthly Treasury holdings.

Usage:
    python etl/jobs/run_newyorkfed_soma_holdings.py
    python etl/jobs/run_newyorkfed_soma_holdings.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, parse_date, parse_numeric, audit_cols

CONFIG_NAME = 'NewYorkFed_SOMA_Holdings'

logger = get_logger('run_newyorkfed_soma_holdings')


def transform(data: list) -> list:
    """Transform SOMA monthly Treasury holdings."""
    transformed = []
    for record in data:
        try:
            par_value = parse_numeric(record.get('parValue', ''), strip_commas=True)
            current_face_value = parse_numeric(record.get('currentFaceValue', ''), strip_commas=True)

            transformed.append({
                'as_of_date': parse_date(record.get('asOfDate')),
                'security_type': record.get('securityType'),
                'cusip': record.get('cusip'),
                'security_description': record.get('securityDescription'),
                'maturity_date': parse_date(record.get('maturityDate')),
                'par_value': par_value,
                'current_face_value': current_face_value,
                **audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform SOMA record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} SOMA holdings records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed SOMA Holdings')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    client = NewYorkFedAPIClient()
    try:
        raw_data = client.get_soma_holdings()
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

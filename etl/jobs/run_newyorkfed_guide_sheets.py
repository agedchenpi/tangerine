"""
Fetch and import NewYorkFed Guide Sheets.

Usage:
    python etl/jobs/run_newyorkfed_guide_sheets.py
    python etl/jobs/run_newyorkfed_guide_sheets.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, parse_date, audit_cols

CONFIG_NAME = 'NewYorkFed_Guide_Sheets'

logger = get_logger('run_newyorkfed_guide_sheets')


def transform(data: list) -> list:
    """Transform guide sheets with nested array extraction."""
    transformed = []

    if not data:
        logger.warning("No guide sheet data to transform")
        return transformed

    si_object = data[0]

    publication_date_str = si_object.get('reportWeeksFromDate')
    if not publication_date_str:
        logger.error("No reportWeeksFromDate found in SI object")
        return transformed

    publication_date = parse_date(publication_date_str)
    guide_type = si_object.get('title', 'SI')

    details = si_object.get('details', [])
    for record in details:
        try:
            transformed.append({
                'publication_date': publication_date,
                'guide_type': guide_type,
                'security_type': record.get('secType'),
                'cusip': record.get('cusip'),
                'issue_date': parse_date(record.get('issueDate')),
                'maturity_date': parse_date(record.get('maturityDate')),
                'coupon_rate': record.get('percentCouponRate'),
                'settlement_price': record.get('settlementPrice'),
                'accrued_interest': record.get('accruedInterest'),
                **audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform guide sheet record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} guide sheet records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed Guide Sheets')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    client = NewYorkFedAPIClient()
    try:
        raw_data = client.get_guide_sheets()
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

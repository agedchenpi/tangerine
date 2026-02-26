"""
Fetch and import NewYorkFed Agency MBS operation announcements.

Usage:
    python etl/jobs/run_newyorkfed_agency_mbs.py
    python etl/jobs/run_newyorkfed_agency_mbs.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, parse_date, audit_cols, JobRunLogger

CONFIG_NAME = 'NewYorkFed_Agency_MBS'

logger = get_logger('run_newyorkfed_agency_mbs')


def transform(data: list) -> list:
    """Transform Agency MBS operation announcements."""
    transformed = []
    for record in data:
        try:
            transformed.append({
                'operation_date': parse_date(record.get('operationDate')),
                'operation_type': record.get('operationType'),
                'cusip': record.get('cusip'),
                'security_description': record.get('securityDescription'),
                'settlement_date': parse_date(record.get('settlementDate')),
                'maturity_date': parse_date(record.get('maturityDate')),
                'operation_amount': record.get('operationAmount'),
                'total_accepted': record.get('totalAmtAccepted'),
                **audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform Agency MBS record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} Agency MBS records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed Agency MBS')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    with JobRunLogger('run_newyorkfed_agency_mbs', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        try:
            client = NewYorkFedAPIClient()
            try:
                raw_data = client.get_agency_mbs()
            finally:
                client.close()
            if not raw_data:
                job_log.complete_step(step_id, records_in=0, records_out=0, message="No data from API")
                return 0
            transformed = transform(raw_data)
            if not transformed:
                job_log.complete_step(step_id, records_in=len(raw_data), records_out=0, message="No records after transform")
                return 0
            save_json(transformed, CONFIG_NAME, source='newyorkfed')
            job_log.complete_step(step_id, records_in=len(raw_data), records_out=len(transformed))
        except Exception as e:
            job_log.fail_step(step_id, str(e))
            return 1

        return run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)


if __name__ == '__main__':
    sys.exit(main())

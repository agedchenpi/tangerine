"""
Fetch and import NewYorkFed Securities Lending operations.

Usage:
    python etl/jobs/run_newyorkfed_securities_lending.py
    python etl/jobs/run_newyorkfed_securities_lending.py --dry-run
"""

import argparse
import sys
from datetime import datetime

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, parse_date, audit_cols, JobRunLogger

CONFIG_NAME = 'NewYorkFed_Securities_Lending'

logger = get_logger('run_newyorkfed_securities_lending')


def transform(data: list) -> list:
    """Transform securities lending operations with term_days calculation."""
    transformed = []
    for record in data:
        try:
            loan_date = parse_date(record.get('loanDate'))
            return_date = parse_date(record.get('returnDate'))

            term_days = None
            if loan_date and return_date:
                ld = datetime.strptime(loan_date, '%Y-%m-%d')
                rd = datetime.strptime(return_date, '%Y-%m-%d')
                term_days = (rd - ld).days

            transformed.append({
                'operation_date': parse_date(record.get('operationDate')),
                'operation_type': record.get('operationType'),
                'cusip': record.get('cusip'),
                'security_description': record.get('securityDescription'),
                'loan_date': loan_date,
                'return_date': return_date,
                'term_days': term_days,
                'par_amount': record.get('totalParAmtAccepted') or record.get('parAmount'),
                'fee_rate': record.get('feeRate'),
                'operation_status': record.get('operationStatus'),
                **audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform securities lending record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} securities lending records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed Securities Lending')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    with JobRunLogger('run_newyorkfed_securities_lending', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        try:
            client = NewYorkFedAPIClient()
            try:
                raw_data = client.get_securities_lending()
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

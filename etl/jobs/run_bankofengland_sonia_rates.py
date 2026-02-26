"""
Fetch and import Bank of England SONIA daily rates.

Usage:
    python etl/jobs/run_bankofengland_sonia_rates.py
    python etl/jobs/run_bankofengland_sonia_rates.py --dry-run
"""

import argparse
import sys
from datetime import datetime

from common.logging_utils import get_logger
from etl.clients.bankofengland_client import BankOfEnglandAPIClient
from etl.base.import_utils import save_json, run_generic_import, JobRunLogger

CONFIG_NAME = 'BankOfEngland_SONIA_Rates'

logger = get_logger('run_bankofengland_sonia_rates')


def transform(raw_data: list) -> list:
    """Transform raw BoE SONIA CSV data to database schema."""
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

        effective_date = datetime.strptime(date_str, '%d %b %Y').strftime('%Y-%m-%d')

        transformed.append({
            'effective_date': effective_date,
            'rate_percent': rate_value,
            'created_date': now,
            'created_by': 'etl_user',
        })

    logger.info(f"Transformed {len(transformed)} SONIA rate records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import Bank of England SONIA Rates')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    with JobRunLogger('run_bankofengland_sonia_rates', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        try:
            client = BankOfEnglandAPIClient()
            try:
                raw_data = client.get_sonia_rates(days=60)
            finally:
                client.close()
            if not raw_data:
                job_log.complete_step(step_id, records_in=0, records_out=0, message="No data from API")
                return 0
            transformed = transform(raw_data)
            if not transformed:
                job_log.complete_step(step_id, records_in=len(raw_data), records_out=0, message="No records after transform")
                return 0
            save_json(transformed, CONFIG_NAME, source='bankofengland')
            job_log.complete_step(step_id, records_in=len(raw_data), records_out=len(transformed))
        except Exception as e:
            job_log.fail_step(step_id, str(e))
            return 1

        return run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)


if __name__ == '__main__':
    sys.exit(main())

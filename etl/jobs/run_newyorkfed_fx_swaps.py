"""
Fetch and import NewYorkFed FX Swap operations.

Usage:
    python etl/jobs/run_newyorkfed_fx_swaps.py
    python etl/jobs/run_newyorkfed_fx_swaps.py --dry-run
"""

import argparse
import sys
from datetime import datetime

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, parse_date, audit_cols, JobRunLogger

CONFIG_NAME = 'NewYorkFed_FX_Swaps'

logger = get_logger('run_newyorkfed_fx_swaps')


def transform(data: list) -> list:
    """Transform FX swap operations with term_days calculation."""
    transformed = []
    for record in data:
        try:
            swap_date_str = record.get('swapDate') or record.get('operationDate')
            swap_date = parse_date(swap_date_str)
            maturity_date = parse_date(record.get('maturityDate'))

            term_days = None
            if swap_date and maturity_date:
                sd = datetime.strptime(swap_date, '%Y-%m-%d')
                md = datetime.strptime(maturity_date, '%Y-%m-%d')
                term_days = (md - sd).days

            transformed.append({
                'swap_date': swap_date,
                'counterparty': record.get('counterparty'),
                'currency_code': record.get('currencyCode') or record.get('currency'),
                'maturity_date': maturity_date,
                'term_days': term_days,
                'usd_amount': record.get('usdAmount'),
                'foreign_currency_amount': record.get('foreignCurrencyAmount'),
                'exchange_rate': record.get('exchangeRate'),
                **audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform FX swap record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} FX swap records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed FX Swaps')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    with JobRunLogger('run_newyorkfed_fx_swaps', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        try:
            client = NewYorkFedAPIClient()
            try:
                raw_data = client.get_fx_swaps()
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

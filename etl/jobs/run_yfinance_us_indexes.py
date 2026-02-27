"""
Fetch and import Yahoo Finance US market index OHLCV data.

Fetches the most recent daily price for 8 major US market indexes
(S&P 500, NASDAQ Composite, NASDAQ-100, Dow Jones, Russell 2000,
VIX, 10-Year Treasury Yield, 30-Year Treasury Yield) via the yfinance library.

Usage:
    python etl/jobs/run_yfinance_us_indexes.py
    python etl/jobs/run_yfinance_us_indexes.py --dry-run
"""

import argparse
import sys
from datetime import datetime

from common.logging_utils import get_logger
from etl.clients.yfinance_client import YFinanceClient
from etl.base.import_utils import save_json, run_generic_import, JobRunLogger

CONFIG_NAME = 'YFinance_US_Indexes'

logger = get_logger('run_yfinance_us_indexes')


def transform(raw_data: list) -> list:
    """Validate and add audit columns to US index price records."""
    transformed = []
    now = datetime.now().isoformat()

    for record in raw_data:
        if not record.get('symbol') or not record.get('price_date'):
            logger.warning(f"Skipping record with missing required fields: {record}")
            continue

        transformed.append({
            'symbol': record['symbol'],
            'index_name': record.get('index_name'),
            'price_date': record['price_date'],
            'open': record.get('open'),
            'high': record.get('high'),
            'low': record.get('low'),
            'close': record.get('close'),
            'volume': record.get('volume'),
            'created_date': now,
            'created_by': 'etl_user',
        })

    logger.info(f"Transformed {len(transformed)} US index price records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import Yahoo Finance US market index prices')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    with JobRunLogger('run_yfinance_us_indexes', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        try:
            client = YFinanceClient()
            raw_data = client.get_us_index_prices()
            if not raw_data:
                job_log.complete_step(step_id, records_in=0, records_out=0, message="No data from yfinance")
                return 0
            transformed = transform(raw_data)
            if not transformed:
                job_log.complete_step(step_id, records_in=len(raw_data), records_out=0, message="No records after transform")
                return 0
            save_json(transformed, CONFIG_NAME, source='yfinance')
            job_log.complete_step(step_id, records_in=len(raw_data), records_out=len(transformed))
        except Exception as e:
            job_log.fail_step(step_id, str(e))
            return 1

        return run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)


if __name__ == '__main__':
    sys.exit(main())

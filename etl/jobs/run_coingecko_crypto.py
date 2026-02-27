"""
Fetch and import CoinGecko cryptocurrency OHLC data.

Fetches daily aggregated OHLC for top 5 cryptocurrencies (BTC, ETH, BNB,
SOL, XRP) via the CoinGecko free REST API. The API's 4-hour candles are
aggregated to a single daily record per coin.

Usage:
    python etl/jobs/run_coingecko_crypto.py
    python etl/jobs/run_coingecko_crypto.py --dry-run
"""

import argparse
import sys
from datetime import datetime

from common.logging_utils import get_logger
from etl.clients.coingecko_client import CoinGeckoClient
from etl.base.import_utils import save_json, run_generic_import, JobRunLogger

CONFIG_NAME = 'CoinGecko_Crypto'

logger = get_logger('run_coingecko_crypto')


def transform(raw_data: list) -> list:
    """Validate and add audit columns to crypto OHLC records."""
    transformed = []
    now = datetime.now().isoformat()

    for record in raw_data:
        if not record.get('symbol') or not record.get('price_date'):
            logger.warning(f"Skipping record with missing required fields: {record}")
            continue

        transformed.append({
            'symbol': record['symbol'],
            'coin_id': record.get('coin_id'),
            'price_date': record['price_date'],
            'open': record.get('open'),
            'high': record.get('high'),
            'low': record.get('low'),
            'close': record.get('close'),
            'created_date': now,
            'created_by': 'etl_user',
        })

    logger.info(f"Transformed {len(transformed)} crypto OHLC records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import CoinGecko cryptocurrency OHLC data')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    with JobRunLogger('run_coingecko_crypto', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        try:
            client = CoinGeckoClient()
            try:
                raw_data = client.get_crypto_ohlc_daily()
            finally:
                client.close()
            if not raw_data:
                job_log.complete_step(step_id, records_in=0, records_out=0, message="No data from CoinGecko API")
                return 0
            transformed = transform(raw_data)
            if not transformed:
                job_log.complete_step(step_id, records_in=len(raw_data), records_out=0, message="No records after transform")
                return 0
            save_json(transformed, CONFIG_NAME, source='coingecko')
            job_log.complete_step(step_id, records_in=len(raw_data), records_out=len(transformed))
        except Exception as e:
            job_log.fail_step(step_id, str(e))
            return 1

        return run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)


if __name__ == '__main__':
    sys.exit(main())

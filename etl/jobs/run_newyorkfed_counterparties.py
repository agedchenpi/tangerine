"""
Fetch and import NewYorkFed FX Swap counterparties.

Usage:
    python etl/jobs/run_newyorkfed_counterparties.py
    python etl/jobs/run_newyorkfed_counterparties.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, audit_cols, JobRunLogger

CONFIG_NAME = 'NewYorkFed_Counterparties'

logger = get_logger('run_newyorkfed_counterparties')


def transform(data: list) -> list:
    """Transform FX swap counterparties list."""
    transformed = []
    for record in data:
        counterparty_name = record.get('counterparty_name')
        if not counterparty_name:
            logger.warning(f"Skipping record with no counterparty name: {record}")
            continue

        transformed.append({
            'counterparty_name': counterparty_name,
            'counterparty_type': 'Central Bank',
            'is_active': True,
            **audit_cols(),
        })

    logger.info(f"Transformed {len(transformed)} counterparty records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed Counterparties')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    with JobRunLogger('run_newyorkfed_counterparties', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        try:
            client = NewYorkFedAPIClient()
            try:
                raw_data = client.get_counterparties()
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

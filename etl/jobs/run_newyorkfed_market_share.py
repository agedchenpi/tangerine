"""
Fetch and import NewYorkFed Market Share data (passthrough, no transform).

Usage:
    python etl/jobs/run_newyorkfed_market_share.py
    python etl/jobs/run_newyorkfed_market_share.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, JobRunLogger

CONFIG_NAME = 'NewYorkFed_Market_Share'

logger = get_logger('run_newyorkfed_market_share')


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed Market Share')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    with JobRunLogger('run_newyorkfed_market_share', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        try:
            client = NewYorkFedAPIClient()
            try:
                raw_data = client.fetch_endpoint(
                    endpoint_path='/api/marketshare/qtrly/latest.{format}',
                    response_root_path='marketshare',
                )
            finally:
                client.close()
            if not raw_data:
                job_log.complete_step(step_id, records_in=0, records_out=0, message="No data from API")
                return 0
            logger.info(f"Passthrough: {len(raw_data)} records (no transform)")
            save_json(raw_data, CONFIG_NAME, source='newyorkfed')
            job_log.complete_step(step_id, records_in=len(raw_data), records_out=len(raw_data))
        except Exception as e:
            job_log.fail_step(step_id, str(e))
            return 1

        return run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)


if __name__ == '__main__':
    sys.exit(main())

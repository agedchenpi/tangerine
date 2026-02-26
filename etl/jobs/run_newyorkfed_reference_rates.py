"""
Fetch and import NewYorkFed Reference Rates (SOFR, EFFR, OBFR, TGCR, BGCR).

Usage:
    python etl/jobs/run_newyorkfed_reference_rates.py
    python etl/jobs/run_newyorkfed_reference_rates.py --dry-run
"""

import argparse
import sys

from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.base.import_utils import save_json, run_generic_import, parse_date, audit_cols, JobRunLogger

CONFIG_NAME = 'NewYorkFed_ReferenceRates_Latest'

logger = get_logger('run_newyorkfed_reference_rates')


def transform(data: list) -> list:
    """Transform reference rates (SOFR, EFFR, OBFR, TGCR, BGCR)."""
    transformed = []
    for record in data:
        effective_date = parse_date(record.get('effectiveDate'))
        if not effective_date:
            logger.warning(f"Missing effectiveDate in record: {record}")
            continue

        transformed.append({
            'rate_type': record.get('type'),
            'effective_date': effective_date,
            'rate_percent': record.get('percentRate'),
            'volume_billions': record.get('volumeInBillions'),
            'percentile_1': record.get('percentile1'),
            'percentile_25': record.get('percentile25'),
            'percentile_75': record.get('percentile75'),
            'percentile_99': record.get('percentile99'),
            'target_range_from': record.get('targetRangeFrom'),
            'target_range_to': record.get('targetRangeTo'),
            **audit_cols(),
        })

    logger.info(f"Transformed {len(transformed)} reference rate records")
    return transformed


def main():
    parser = argparse.ArgumentParser(description='Fetch and import NewYorkFed Reference Rates')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    with JobRunLogger('run_newyorkfed_reference_rates', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        try:
            client = NewYorkFedAPIClient()
            try:
                raw_data = client.get_reference_rates_latest()
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

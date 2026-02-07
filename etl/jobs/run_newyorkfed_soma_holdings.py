"""
NewYorkFed SOMA Holdings ETL Job.

Imports System Open Market Account (SOMA) monthly Treasury holdings from NewYorkFed Markets API.

Endpoint: /api/soma/tsy/get/monthly.json

Usage:
    python etl/jobs/run_newyorkfed_soma_holdings.py [--dry-run]
"""

import argparse
import sys
from datetime import date, datetime
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.loaders.postgres_loader import PostgresLoader


class NewYorkFedSOMAHoldingsJob(BaseETLJob):
    """Import SOMA holdings from NewYorkFed Markets API."""

    def __init__(self, run_date: date = None, dry_run: bool = False):
        run_date_val = run_date or date.today()
        super().__init__(
            run_date=run_date_val,
            dataset_type='SOMAHoldings',
            data_source='NewYorkFed',
            dry_run=dry_run,
            username='etl_user',
            dataset_label=f'SOMAHoldings_{run_date_val}'
        )
        self.client = None
        self.loader = None

    def setup(self):
        self.logger.info("Initializing NewYorkFed API client", extra={'stepcounter': 'setup'})
        self.client = NewYorkFedAPIClient()
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        self.logger.info("Fetching SOMA monthly Treasury holdings", extra={'stepcounter': 'extract'})
        return self.client.get_soma_holdings()

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed = []
        for record in data:
            try:
                # Parse as_of_date
                as_of_date_str = record.get('asOfDate')
                as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date() if as_of_date_str else None

                # Parse maturity_date (optional for some holdings)
                maturity_date_str = record.get('maturityDate')
                maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d').date() if maturity_date_str else None

                # Parse numeric values (may be strings with commas or empty)
                par_value_str = record.get('parValue', '').replace(',', '')
                par_value = float(par_value_str) if par_value_str else None

                current_face_value_str = record.get('currentFaceValue', '').replace(',', '')
                current_face_value = float(current_face_value_str) if current_face_value_str else None

                transformed.append({
                    'as_of_date': as_of_date,
                    'security_type': record.get('securityType'),
                    'cusip': record.get('cusip'),
                    'security_description': record.get('securityDescription'),
                    'maturity_date': maturity_date,
                    'par_value': par_value,
                    'current_face_value': current_face_value,
                    'created_date': datetime.now(),
                    'created_by': self.username
                })
            except Exception as e:
                self.logger.error(f"Failed to transform record: {e}", extra={'metadata': {'record': record}})
                continue

        return transformed

    def load(self, data: List[Dict[str, Any]]):
        if not self.dry_run:
            self.records_loaded = self.loader.load(
                table='newyorkfed_soma_holdings',
                data=data,
                dataset_id=self.dataset_id
            )
        else:
            self.logger.info(f"DRY RUN: Would load {len(data)} records", extra={'stepcounter': 'load'})
            self.records_loaded = len(data)

    def cleanup(self):
        if self.client:
            self.client.close()


def main():
    parser = argparse.ArgumentParser(description='Import SOMA monthly Treasury holdings from NewYorkFed API')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--date', type=str, help='Run date (YYYY-MM-DD)')
    args = parser.parse_args()

    run_date = None
    if args.date:
        run_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    job = NewYorkFedSOMAHoldingsJob(run_date=run_date, dry_run=args.dry_run)
    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

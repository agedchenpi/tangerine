"""
NewYorkFed FX Swap Counterparties ETL Job.

Imports list of central bank counterparties for FX swap operations from NewYorkFed Markets API.

Endpoint: /api/fxs/list/counterparties.json

Usage:
    python etl/jobs/run_newyorkfed_counterparties.py [--dry-run]
"""

import argparse
import sys
from datetime import date, datetime
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.loaders.postgres_loader import PostgresLoader


class NewYorkFedCounterpartiesJob(BaseETLJob):
    """Import FX swap counterparties list from NewYorkFed Markets API."""

    def __init__(self, run_date: date = None, dry_run: bool = False):
        run_date_val = run_date or date.today()
        super().__init__(
            run_date=run_date_val,
            dataset_type='FXCounterparties',
            data_source='NewYorkFed',
            dry_run=dry_run,
            username='etl_user',
            dataset_label=f'FXCounterparties_{run_date_val}'
        )
        self.client = None
        self.loader = None

    def setup(self):
        self.logger.info("Initializing NewYorkFed API client", extra={'stepcounter': 'setup'})
        self.client = NewYorkFedAPIClient()
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        self.logger.info("Fetching FX swap counterparties list", extra={'stepcounter': 'extract'})
        data = self.client.get_counterparties()

        if not data or len(data) == 0:
            self.logger.warning(
                "API returned 0 counterparties",
                extra={
                    'stepcounter': 'extract',
                    'metadata': {
                        'reason': 'No counterparties available from Fed',
                        'expected': 'Job will complete successfully with 0 records loaded'
                    }
                }
            )

        return data

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform counterparties API response to database schema.

        Maps API fields to database columns for FX swap counterparties.
        """
        transformed = []
        for record in data:
            try:
                # The client already converts string list to dict list
                counterparty_name = record.get('counterparty_name')

                if not counterparty_name:
                    self.logger.warning(f"Skipping record with no counterparty name: {record}")
                    continue

                transformed.append({
                    'counterparty_name': counterparty_name,
                    'counterparty_type': 'Central Bank',
                    'is_active': True,
                    'created_date': datetime.now(),
                    'created_by': self.username
                })
            except Exception as e:
                self.logger.error(f"Failed to transform record: {e}", extra={'metadata': {'record': record}})
                continue

        self.logger.info(
            f"Transformed {len(transformed)} counterparty records",
            extra={'stepcounter': 'transform'}
        )
        return transformed

    def load(self, data: List[Dict[str, Any]]):
        if not self.dry_run:
            # Load counterparties (unique constraint will prevent duplicates)
            self.records_loaded = self.loader.load(
                table='newyorkfed_counterparties',
                data=data,
                dataset_id=self.dataset_id
            )
            self.logger.info(
                f"Loaded {self.records_loaded} records to feeds.newyorkfed_counterparties",
                extra={'stepcounter': 'load'}
            )
        else:
            self.logger.info(f"DRY RUN: Would load {len(data)} records", extra={'stepcounter': 'load'})
            self.records_loaded = len(data)

    def cleanup(self):
        if self.client:
            self.client.close()


def main():
    parser = argparse.ArgumentParser(description='Import FX swap counterparties from NewYorkFed API')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--date', type=str, help='Run date (YYYY-MM-DD)')
    args = parser.parse_args()

    run_date = None
    if args.date:
        run_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    job = NewYorkFedCounterpartiesJob(run_date=run_date, dry_run=args.dry_run)
    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

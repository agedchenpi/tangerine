"""
NewYorkFed Agency MBS ETL Job.

Imports latest Agency MBS operation announcements from NewYorkFed Markets API.

Endpoint: /api/ambs/all/announcements/summary/latest.json

Usage:
    python etl/jobs/run_newyorkfed_agency_mbs.py [--dry-run]
"""

import argparse
import sys
from datetime import date, datetime
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.loaders.postgres_loader import PostgresLoader


class NewYorkFedAgencyMBSJob(BaseETLJob):
    """Import Agency MBS operations from NewYorkFed Markets API."""

    def __init__(self, run_date: date = None, dry_run: bool = False):
        run_date_val = run_date or date.today()
        super().__init__(
            run_date=run_date_val,
            dataset_type='AgencyMBS',
            data_source='NewYorkFed',
            dry_run=dry_run,
            username='etl_user',
            dataset_label=f'AgencyMBS_{run_date_val}'
        )
        self.client = None
        self.loader = None

    def setup(self):
        self.logger.info("Initializing NewYorkFed API client", extra={'stepcounter': 'setup'})
        self.client = NewYorkFedAPIClient()
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        self.logger.info("Fetching latest Agency MBS operation announcements", extra={'stepcounter': 'extract'})
        data = self.client.get_agency_mbs()

        if not data or len(data) == 0:
            self.logger.warning(
                "API returned 0 records - Federal Reserve has no current Agency MBS operations",
                extra={
                    'stepcounter': 'extract',
                    'metadata': {
                        'reason': 'No data available from Fed',
                        'expected': 'Job will complete successfully with 0 records loaded'
                    }
                }
            )

        return data

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform Agency MBS API response to database schema.

        Maps API fields to database columns for Agency MBS operations.
        """
        transformed = []
        for record in data:
            try:
                # Parse dates
                operation_date_str = record.get('operationDate')
                operation_date = datetime.strptime(operation_date_str, '%Y-%m-%d').date() if operation_date_str else None

                settlement_date_str = record.get('settlementDate')
                settlement_date = datetime.strptime(settlement_date_str, '%Y-%m-%d').date() if settlement_date_str else None

                maturity_date_str = record.get('maturityDate')
                maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d').date() if maturity_date_str else None

                transformed.append({
                    'operation_date': operation_date,
                    'operation_type': record.get('operationType'),
                    'cusip': record.get('cusip'),
                    'security_description': record.get('securityDescription'),
                    'settlement_date': settlement_date,
                    'maturity_date': maturity_date,
                    'operation_amount': record.get('operationAmount'),
                    'total_accepted': record.get('totalAmtAccepted'),
                    'created_date': datetime.now(),
                    'created_by': self.username
                })
            except Exception as e:
                self.logger.error(f"Failed to transform record: {e}", extra={'metadata': {'record': record}})
                continue

        self.logger.info(
            f"Transformed {len(transformed)} records",
            extra={'stepcounter': 'transform'}
        )
        return transformed

    def load(self, data: List[Dict[str, Any]]):
        if not self.dry_run:
            self.records_loaded = self.loader.load(
                table='newyorkfed_agency_mbs',
                data=data,
                dataset_id=self.dataset_id
            )
            self.logger.info(
                f"Loaded {self.records_loaded} records to feeds.newyorkfed_agency_mbs",
                extra={'stepcounter': 'load'}
            )
        else:
            self.logger.info(f"DRY RUN: Would load {len(data)} records", extra={'stepcounter': 'load'})
            self.records_loaded = len(data)

    def cleanup(self):
        if self.client:
            self.client.close()


def main():
    parser = argparse.ArgumentParser(description='Import Agency MBS operations from NewYorkFed API')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--date', type=str, help='Run date (YYYY-MM-DD)')
    args = parser.parse_args()

    run_date = None
    if args.date:
        run_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    job = NewYorkFedAgencyMBSJob(run_date=run_date, dry_run=args.dry_run)
    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

"""
NewYorkFed Treasury Operations ETL Job.

Imports last two weeks of Treasury securities operation results from NewYorkFed Markets API.

Endpoint: /api/tsy/all/results/summary/lastTwoWeeks.json

Usage:
    python etl/jobs/run_newyorkfed_treasury.py [--dry-run]
"""

import argparse
import sys
from datetime import date, datetime
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.loaders.postgres_loader import PostgresLoader


class NewYorkFedTreasuryJob(BaseETLJob):
    """Import Treasury operations from NewYorkFed Markets API."""

    def __init__(self, run_date: date = None, dry_run: bool = False):
        run_date_val = run_date or date.today()
        super().__init__(
            run_date=run_date_val,
            dataset_type='TreasuryOperations',
            data_source='NewYorkFed',
            dry_run=dry_run,
            username='etl_user',
            dataset_label=f'TreasuryOperations_{run_date_val}'
        )
        self.client = None
        self.loader = None

    def setup(self):
        self.logger.info("Initializing NewYorkFed API client", extra={'stepcounter': 'setup'})
        self.client = NewYorkFedAPIClient()
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        self.logger.info("Fetching last two weeks of Treasury operation results", extra={'stepcounter': 'extract'})
        data = self.client.get_treasury_operations()

        if not data or len(data) == 0:
            self.logger.warning(
                "API returned 0 records - Federal Reserve has no Treasury operations in last two weeks",
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
        Transform Treasury operations API response to database schema.

        Maps API fields to database columns for Treasury securities operations.
        """
        transformed = []
        for record in data:
            try:
                # Parse dates
                operation_date_str = record.get('operationDate')
                operation_date = datetime.strptime(operation_date_str, '%Y-%m-%d').date() if operation_date_str else None

                issue_date_str = record.get('issueDate')
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else None

                maturity_date_str = record.get('maturityDate')
                maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d').date() if maturity_date_str else None

                transformed.append({
                    'operation_date': operation_date,
                    'operation_type': record.get('operationType'),
                    'cusip': record.get('cusip'),
                    'security_description': record.get('securityDescription'),
                    'issue_date': issue_date,
                    'maturity_date': maturity_date,
                    'coupon_rate': record.get('couponRate'),
                    'security_term': record.get('securityTerm'),
                    'operation_amount': record.get('operationAmount'),
                    'total_submitted': record.get('totalAmtSubmitted'),
                    'total_accepted': record.get('totalAmtAccepted'),
                    'high_price': record.get('highPrice'),
                    'low_price': record.get('lowPrice'),
                    'stop_out_rate': record.get('stopOutRate'),
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
                table='newyorkfed_treasury_operations',
                data=data,
                dataset_id=self.dataset_id
            )
            self.logger.info(
                f"Loaded {self.records_loaded} records to feeds.newyorkfed_treasury_operations",
                extra={'stepcounter': 'load'}
            )
        else:
            self.logger.info(f"DRY RUN: Would load {len(data)} records", extra={'stepcounter': 'load'})
            self.records_loaded = len(data)

    def cleanup(self):
        if self.client:
            self.client.close()


def main():
    parser = argparse.ArgumentParser(description='Import Treasury operations from NewYorkFed API')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--date', type=str, help='Run date (YYYY-MM-DD)')
    args = parser.parse_args()

    run_date = None
    if args.date:
        run_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    job = NewYorkFedTreasuryJob(run_date=run_date, dry_run=args.dry_run)
    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

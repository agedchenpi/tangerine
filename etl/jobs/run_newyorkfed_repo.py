"""
NewYorkFed Repo Operations ETL Job.

Imports last two weeks of repo and reverse repo operations from NewYorkFed Markets API.

Endpoint: /api/rp/all/all/results/lastTwoWeeks.json

Usage:
    python etl/jobs/run_newyorkfed_repo.py [--dry-run]
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.loaders.postgres_loader import PostgresLoader


class NewYorkFedRepoOperationsJob(BaseETLJob):
    """Import repo operations from NewYorkFed Markets API."""

    def __init__(self, run_date: date = None, dry_run: bool = False):
        run_date_val = run_date or date.today()
        super().__init__(
            run_date=run_date_val,
            dataset_type='RepoOperations',
            data_source='NewYorkFed',
            dry_run=dry_run,
            username='etl_user',
            dataset_label=f'RepoOperations_{run_date_val}'
        )
        self.client = None
        self.loader = None

    def setup(self):
        self.logger.info("Initializing NewYorkFed API client", extra={'stepcounter': 'setup'})
        self.client = NewYorkFedAPIClient()
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        self.logger.info("Fetching last two weeks of repo operations", extra={'stepcounter': 'extract'})
        return self.client.get_repo_operations()

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed = []
        for record in data:
            try:
                # Parse dates
                operation_date_str = record.get('operationDate')
                operation_date = datetime.strptime(operation_date_str, '%Y-%m-%d').date() if operation_date_str else None

                maturity_date_str = record.get('maturityDate')
                maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d').date() if maturity_date_str else None

                # Get operation type from record (API returns 'Repo' or 'Reverse Repo')
                operation_type_raw = record.get('operationType', '').lower().replace(' ', '')

                # Parse numeric values
                total_amt_submitted = record.get('totalAmtSubmitted')
                total_amt_accepted = record.get('totalAmtAccepted')

                # Extract term days
                term_days = record.get('termCalenderDays')  # Note: API uses "Calender" (typo in API)

                transformed.append({
                    'operation_date': operation_date,
                    'operation_type': operation_type_raw,
                    'operation_id': record.get('operationId'),
                    'maturity_date': maturity_date,
                    'term_days': term_days,
                    'operation_status': record.get('auctionStatus'),  # API uses 'auctionStatus'
                    'amount_submitted': total_amt_submitted,
                    'amount_accepted': total_amt_accepted,
                    'award_rate': None,  # Award rate is in details array, not top level
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
                table='newyorkfed_repo_operations',
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
    parser = argparse.ArgumentParser(description='Import last two weeks of repo operations from NewYorkFed API')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--date', type=str, help='Run date (YYYY-MM-DD)')
    args = parser.parse_args()

    run_date = None
    if args.date:
        run_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    job = NewYorkFedRepoOperationsJob(run_date=run_date, dry_run=args.dry_run)
    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

"""
NewYorkFed Repo Operations ETL Job.

Imports repo and reverse repo operations from NewYorkFed Markets API.

Endpoints:
- /api/repo/results/search.json
- /api/reverserepo/results/search.json

Usage:
    python etl/jobs/run_newyorkfed_repo.py [--operation-type repo|reverserepo] [--dry-run]
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

    def __init__(self, operation_type: str = 'repo', run_date: date = None, dry_run: bool = False, run_uuid: str = None):
        super().__init__(
            run_date=run_date or date.today(),
            dataset_type='RepoOperations',
            data_source='NewYorkFed',
            dry_run=dry_run,
            run_uuid=run_uuid,
            username='etl_user'
        )
        self.operation_type = operation_type
        self.client = None
        self.loader = None

    def setup(self):
        self.logger.info("Initializing NewYorkFed API client", extra={'stepcounter': 'setup'})
        self.client = NewYorkFedAPIClient()
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        self.logger.info(f"Fetching {self.operation_type} operations", extra={'stepcounter': 'extract'})
        return self.client.get_repo_operations(operation_type=self.operation_type)

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed = []
        for record in data:
            try:
                # Parse dates
                operation_date_str = record.get('operationDate')
                operation_date = datetime.strptime(operation_date_str, '%Y-%m-%d').date() if operation_date_str else None

                maturity_date_str = record.get('maturityDate')
                maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d').date() if maturity_date_str else None

                transformed.append({
                    'operation_date': operation_date,
                    'operation_type': self.operation_type,
                    'operation_id': record.get('operationId'),
                    'maturity_date': maturity_date,
                    'term_days': record.get('termDays'),
                    'operation_status': record.get('operationStatus'),
                    'amount_submitted': record.get('amountSubmitted'),
                    'amount_accepted': record.get('amountAccepted'),
                    'award_rate': record.get('awardRate'),
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
    parser = argparse.ArgumentParser(description='Import repo operations from NewYorkFed API')
    parser.add_argument('--operation-type', choices=['repo', 'reverserepo'], default='repo')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--date', type=str, help='Run date (YYYY-MM-DD)')
    args = parser.parse_args()

    run_date = None
    if args.date:
        run_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    job = NewYorkFedRepoOperationsJob(
        operation_type=args.operation_type,
        run_date=run_date,
        dry_run=args.dry_run
    )
    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

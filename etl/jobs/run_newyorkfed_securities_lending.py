"""
NewYorkFed Securities Lending ETL Job.

Imports latest securities lending operations from NewYorkFed Markets API.

Endpoint: /api/seclending/all/results/summary/latest.json

Usage:
    python etl/jobs/run_newyorkfed_securities_lending.py [--dry-run]
"""

import argparse
import sys
from datetime import date, datetime
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.loaders.postgres_loader import PostgresLoader


class NewYorkFedSecuritiesLendingJob(BaseETLJob):
    """Import securities lending operations from NewYorkFed Markets API."""

    def __init__(self, run_date: date = None, dry_run: bool = False):
        run_date_val = run_date or date.today()
        super().__init__(
            run_date=run_date_val,
            dataset_type='SecuritiesLending',
            data_source='NewYorkFed',
            dry_run=dry_run,
            username='etl_user',
            dataset_label=f'SecuritiesLending_{run_date_val}'
        )
        self.client = None
        self.loader = None

    def setup(self):
        self.logger.info("Initializing NewYorkFed API client", extra={'stepcounter': 'setup'})
        self.client = NewYorkFedAPIClient()
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        self.logger.info("Fetching latest securities lending operations", extra={'stepcounter': 'extract'})
        return self.client.get_securities_lending()

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform securities lending API response to database schema.

        API Response Format:
            {
              "seclending": {
                "operations": [
                  {
                    "operationId": "SL 020626 1",
                    "operationDate": "2026-02-06",
                    "totalParAmtSubmitted": 34732000000,
                    "totalParAmtAccepted": 34434000000,
                    ...
                  }
                ]
              }
            }
        """
        transformed = []
        for record in data:
            try:
                # Parse operation date
                operation_date_str = record.get('operationDate')
                operation_date = datetime.strptime(operation_date_str, '%Y-%m-%d').date() if operation_date_str else None

                # Parse loan and return dates if available
                loan_date_str = record.get('loanDate')
                loan_date = datetime.strptime(loan_date_str, '%Y-%m-%d').date() if loan_date_str else None

                return_date_str = record.get('returnDate')
                return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date() if return_date_str else None

                # Calculate term days if both dates available
                term_days = None
                if loan_date and return_date:
                    term_days = (return_date - loan_date).days

                transformed.append({
                    'operation_date': operation_date,
                    'operation_type': record.get('operationType'),
                    'cusip': record.get('cusip'),
                    'security_description': record.get('securityDescription'),
                    'loan_date': loan_date,
                    'return_date': return_date,
                    'term_days': term_days,
                    'par_amount': record.get('totalParAmtAccepted') or record.get('parAmount'),
                    'fee_rate': record.get('feeRate'),
                    'operation_status': record.get('operationStatus'),
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
                table='newyorkfed_securities_lending',
                data=data,
                dataset_id=self.dataset_id
            )
            self.logger.info(
                f"Loaded {self.records_loaded} records to feeds.newyorkfed_securities_lending",
                extra={'stepcounter': 'load'}
            )
        else:
            self.logger.info(f"DRY RUN: Would load {len(data)} records", extra={'stepcounter': 'load'})
            self.records_loaded = len(data)

    def cleanup(self):
        if self.client:
            self.client.close()


def main():
    parser = argparse.ArgumentParser(description='Import securities lending operations from NewYorkFed API')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--date', type=str, help='Run date (YYYY-MM-DD)')
    args = parser.parse_args()

    run_date = None
    if args.date:
        run_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    job = NewYorkFedSecuritiesLendingJob(run_date=run_date, dry_run=args.dry_run)
    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

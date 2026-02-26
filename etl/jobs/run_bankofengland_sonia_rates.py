"""
Bank of England SONIA Rates ETL Job.

Imports Sterling Overnight Index Average (SONIA) daily rates from the
Bank of England Interactive Statistical Database (IADB).

SONIA is published daily at ~10:00 AM London time on business days.

Usage:
    python etl/jobs/run_bankofengland_sonia_rates.py [--days 60] [--dry-run]

Examples:
    # Fetch last 60 days of SONIA rates
    python etl/jobs/run_bankofengland_sonia_rates.py

    # Fetch last 30 days
    python etl/jobs/run_bankofengland_sonia_rates.py --days 30

    # Dry run (no database writes)
    python etl/jobs/run_bankofengland_sonia_rates.py --dry-run
"""

import argparse
import sys
from datetime import date, datetime
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.clients.bankofengland_client import BankOfEnglandAPIClient
from etl.loaders.postgres_loader import PostgresLoader


class BankOfEnglandSONIARatesJob(BaseETLJob):
    """
    Import SONIA daily rates from Bank of England IADB.

    Lifecycle:
        1. setup() - Initialize API client and loader
        2. extract() - Fetch SONIA rates CSV from BoE
        3. transform() - Parse dates/rates, add audit columns
        4. load() - Bulk insert to feeds.bankofengland_sonia_rates
        5. cleanup() - Close connections
    """

    def __init__(
        self,
        days: int = 60,
        run_date: date = None,
        dry_run: bool = False,
        run_uuid: str = None
    ):
        run_date_val = run_date or date.today()
        super().__init__(
            run_date=run_date_val,
            dataset_type='Rates',
            data_source='BankOfEngland',
            dry_run=dry_run,
            run_uuid=run_uuid,
            username='etl_user',
            dataset_label=f'SONIA_{run_date_val}'
        )
        self.days = days
        self.client = None
        self.loader = None

    def setup(self):
        """Initialize API client and database loader."""
        self.logger.info("Initializing BankOfEngland API client", extra={'stepcounter': 'setup'})
        self.client = BankOfEnglandAPIClient()

        self.logger.info("Initializing PostgreSQL loader", extra={'stepcounter': 'setup'})
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        """
        Fetch SONIA rates from Bank of England IADB.

        Returns:
            List of dicts with keys 'date' and 'rate' from CSV response
        """
        self.logger.info(
            f"Fetching SONIA rates for last {self.days} days",
            extra={'stepcounter': 'extract', 'metadata': {'days': self.days}}
        )
        return self.client.get_sonia_rates(days=self.days)

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform raw CSV data to database schema.

        Transformations:
            - Parse date strings ('03 Jan 2025') to date objects
            - Coerce rate strings to float
            - Skip records with missing or non-numeric rates
            - Add audit columns (created_date, created_by)
        """
        transformed = []

        for record in data:
            try:
                date_str = record.get('date')
                rate_str = record.get('rate')

                if not date_str or not rate_str:
                    self.logger.warning(f"Skipping record with missing data: {record}")
                    continue

                # Parse rate - skip non-numeric values
                try:
                    rate_value = float(rate_str)
                except (ValueError, TypeError):
                    self.logger.warning(f"Skipping non-numeric rate: {rate_str} for date {date_str}")
                    continue

                # Parse date from BoE format: '03 Jan 2025'
                effective_date = datetime.strptime(date_str, '%d %b %Y').date()

                transformed.append({
                    'effective_date': effective_date,
                    'rate_percent': rate_value,
                    'created_date': datetime.now(),
                    'created_by': self.username
                })

            except Exception as e:
                self.logger.error(
                    f"Failed to transform record: {e}",
                    extra={'metadata': {'record': record}},
                    exc_info=True
                )
                continue

        self.logger.info(
            f"Transformed {len(transformed)} records",
            extra={'stepcounter': 'transform'}
        )
        return transformed

    def load(self, data: List[Dict[str, Any]]):
        """Load transformed data to feeds.bankofengland_sonia_rates."""
        if not self.dry_run:
            self.records_loaded = self.loader.load(
                table='bankofengland_sonia_rates',
                data=data,
                dataset_id=self.dataset_id
            )
            self.logger.info(
                f"Loaded {self.records_loaded} records to feeds.bankofengland_sonia_rates",
                extra={
                    'stepcounter': 'load',
                    'metadata': {
                        'records': self.records_loaded,
                        'dataset_id': self.dataset_id
                    }
                }
            )
        else:
            self.logger.info(
                f"DRY RUN: Would load {len(data)} records to feeds.bankofengland_sonia_rates",
                extra={'stepcounter': 'load', 'metadata': {'dry_run': True}}
            )
            self.records_loaded = len(data)

    def cleanup(self):
        """Close API client connection."""
        if self.client:
            self.client.close()


def main():
    """CLI entry point for SONIA rates job."""
    parser = argparse.ArgumentParser(
        description='Import SONIA rates from Bank of England IADB'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=60,
        help='Number of days of history to fetch (default: 60)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch and transform data but do not load to database'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Run date in YYYY-MM-DD format (default: today)'
    )

    args = parser.parse_args()

    run_date = None
    if args.date:
        try:
            run_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
            return 1

    job = BankOfEnglandSONIARatesJob(
        days=args.days,
        run_date=run_date,
        dry_run=args.dry_run
    )

    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

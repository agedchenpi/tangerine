"""
NewYorkFed Reference Rates ETL Job.

Imports Federal Reserve reference rates (SOFR, EFFR, OBFR, TGCR, BGCR) from
the Federal Reserve Bank of New York Markets API.

Endpoints:
- Latest rates: /api/rates/all/latest.json
- Historical search: /api/rates/all/search.json (date range)

Usage:
    python etl/jobs/run_newyorkfed_reference_rates.py [--endpoint-type latest|search] [--dry-run]

Examples:
    # Fetch latest rates
    python etl/jobs/run_newyorkfed_reference_rates.py --endpoint-type latest

    # Fetch last 30 days of rates
    python etl/jobs/run_newyorkfed_reference_rates.py --endpoint-type search

    # Dry run (no database writes)
    python etl/jobs/run_newyorkfed_reference_rates.py --dry-run
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.loaders.postgres_loader import PostgresLoader


class NewYorkFedReferenceRatesJob(BaseETLJob):
    """
    Import Federal Reserve reference rates from NewYorkFed Markets API.

    Lifecycle:
        1. setup() - Initialize API client and loader
        2. extract() - Fetch rates from API (latest or search endpoint)
        3. transform() - Normalize field names and add audit columns
        4. load() - Bulk insert to feeds.newyorkfed_reference_rates
        5. cleanup() - Close connections
    """

    def __init__(
        self,
        endpoint_type: str = 'latest',
        run_date: date = None,
        dry_run: bool = False,
        run_uuid: str = None
    ):
        """
        Initialize reference rates job.

        Args:
            endpoint_type: 'latest' for latest rates, 'search' for date range
            run_date: Date for this ETL run (default: today)
            dry_run: If True, fetch and transform but don't load to database
            run_uuid: Optional run UUID for tracing
        """
        super().__init__(
            run_date=run_date or date.today(),
            dataset_type='ReferenceRates',
            data_source='NewYorkFed',
            dry_run=dry_run,
            run_uuid=run_uuid,
            username='etl_user'
        )
        self.endpoint_type = endpoint_type
        self.client = None
        self.loader = None

    def setup(self):
        """Initialize API client and database loader."""
        self.logger.info("Initializing NewYorkFed API client", extra={'stepcounter': 'setup'})
        self.client = NewYorkFedAPIClient()

        self.logger.info("Initializing PostgreSQL loader", extra={'stepcounter': 'setup'})
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        """
        Fetch reference rates from NewYorkFed API.

        Returns:
            List of rate dictionaries from API response

        API Response Format:
            {
              "refRates": [
                {
                  "type": "SOFR",
                  "effectiveDate": "2024-01-15",
                  "percentRate": 5.32,
                  "volumeInBillions": 1542.0,
                  "percentile1": 5.30,
                  "percentile25": 5.31,
                  "percentile75": 5.33,
                  "percentile99": 5.35
                },
                ...
              ]
            }
        """
        if self.endpoint_type == 'latest':
            self.logger.info("Fetching latest reference rates", extra={'stepcounter': 'extract'})
            return self.client.get_reference_rates_latest()

        elif self.endpoint_type == 'search':
            # Fetch last 30 days of data
            end_date = self.run_date
            start_date = self.run_date - timedelta(days=30)

            self.logger.info(
                f"Fetching reference rates from {start_date} to {end_date}",
                extra={
                    'stepcounter': 'extract',
                    'metadata': {
                        'start_date': str(start_date),
                        'end_date': str(end_date)
                    }
                }
            )

            return self.client.get_reference_rates_search(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )

        else:
            raise ValueError(f"Invalid endpoint_type: {self.endpoint_type}. Must be 'latest' or 'search'")

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform API response to database schema.

        Args:
            data: List of rate dictionaries from API

        Returns:
            List of transformed dictionaries ready for database insertion

        Transformations:
            - Rename fields to match database schema (camelCase -> snake_case)
            - Parse dates from string to date objects
            - Add audit columns (created_date, created_by)
            - Handle missing/null fields gracefully
        """
        transformed = []

        for record in data:
            try:
                # Parse effective date
                effective_date_str = record.get('effectiveDate')
                if effective_date_str:
                    effective_date = datetime.strptime(effective_date_str, '%Y-%m-%d').date()
                else:
                    self.logger.warning(f"Missing effectiveDate in record: {record}")
                    continue

                transformed_record = {
                    # Identification
                    'rate_type': record.get('type'),
                    'effective_date': effective_date,

                    # Rate values
                    'rate_percent': record.get('percentRate'),
                    'volume_billions': record.get('volumeInBillions'),

                    # Percentiles
                    'percentile_1': record.get('percentile1'),
                    'percentile_25': record.get('percentile25'),
                    'percentile_75': record.get('percentile75'),
                    'percentile_99': record.get('percentile99'),

                    # Target range (mainly for EFFR)
                    'target_range_from': record.get('targetRangeFrom'),
                    'target_range_to': record.get('targetRangeTo'),

                    # Audit
                    'created_date': datetime.now(),
                    'created_by': self.username
                }

                transformed.append(transformed_record)

            except Exception as e:
                self.logger.error(
                    f"Failed to transform record: {e}",
                    extra={'metadata': {'record': record}},
                    exc_info=True
                )
                continue

        # Log rate type breakdown
        rate_type_counts = {}
        for record in transformed:
            rate_type = record['rate_type']
            rate_type_counts[rate_type] = rate_type_counts.get(rate_type, 0) + 1

        self.logger.info(
            f"Transformed {len(transformed)} records",
            extra={
                'stepcounter': 'transform',
                'metadata': {'rate_types': rate_type_counts}
            }
        )

        return transformed

    def load(self, data: List[Dict[str, Any]]):
        """
        Load transformed data to feeds.newyorkfed_reference_rates.

        Args:
            data: List of transformed dictionaries
        """
        if not self.dry_run:
            self.records_loaded = self.loader.load(
                table='newyorkfed_reference_rates',
                data=data,
                dataset_id=self.dataset_id
            )
            self.logger.info(
                f"Loaded {self.records_loaded} records to feeds.newyorkfed_reference_rates",
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
                f"DRY RUN: Would load {len(data)} records to feeds.newyorkfed_reference_rates",
                extra={'stepcounter': 'load', 'metadata': {'dry_run': True}}
            )
            self.records_loaded = len(data)

    def cleanup(self):
        """Close API client connection."""
        if self.client:
            self.client.close()


def main():
    """CLI entry point for reference rates job."""
    parser = argparse.ArgumentParser(
        description='Import Federal Reserve reference rates from NewYorkFed Markets API'
    )
    parser.add_argument(
        '--endpoint-type',
        choices=['latest', 'search'],
        default='latest',
        help='Endpoint type: "latest" for latest rates, "search" for date range (last 30 days)'
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

    # Parse run date
    run_date = None
    if args.date:
        try:
            run_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
            return 1

    # Create and run job
    job = NewYorkFedReferenceRatesJob(
        endpoint_type=args.endpoint_type,
        run_date=run_date,
        dry_run=args.dry_run
    )

    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

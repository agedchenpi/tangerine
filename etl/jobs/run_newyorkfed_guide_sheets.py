"""
NewYorkFed Guide Sheets ETL Job.

Imports latest guide sheet data from NewYorkFed Markets API.

Endpoint: /api/guidesheets/si/latest.json

Usage:
    python etl/jobs/run_newyorkfed_guide_sheets.py [--dry-run]
"""

import argparse
import sys
from datetime import date, datetime
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.loaders.postgres_loader import PostgresLoader


class NewYorkFedGuideSheetsJob(BaseETLJob):
    """Import guide sheet data from NewYorkFed Markets API."""

    def __init__(self, run_date: date = None, dry_run: bool = False):
        run_date_val = run_date or date.today()
        super().__init__(
            run_date=run_date_val,
            dataset_type='GuideSheets',
            data_source='NewYorkFed',
            dry_run=dry_run,
            username='etl_user',
            dataset_label=f'GuideSheets_{run_date_val}'
        )
        self.client = None
        self.loader = None

    def setup(self):
        self.logger.info("Initializing NewYorkFed API client", extra={'stepcounter': 'setup'})
        self.client = NewYorkFedAPIClient()
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict[str, Any]]:
        self.logger.info("Fetching latest guide sheet data", extra={'stepcounter': 'extract'})
        return self.client.get_guide_sheets()

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform guide sheets API response to database schema.

        Maps API fields to database columns for guide sheet publications.
        API returns full SI object with metadata and details array.
        """
        transformed = []

        # Extract the SI object (should be single-element list)
        if not data or len(data) == 0:
            self.logger.warning("No guide sheet data to transform")
            return transformed

        si_object = data[0]

        # Get publication date from top-level metadata
        publication_date_str = si_object.get('reportWeeksFromDate')
        if not publication_date_str:
            self.logger.error("No reportWeeksFromDate found in SI object")
            return transformed

        publication_date = datetime.strptime(publication_date_str, '%Y-%m-%d').date()

        # Get guide type from title (e.g., "FR 2004SI Guide Sheet")
        guide_type = si_object.get('title', 'SI')

        # Process each detail record
        details = si_object.get('details', [])
        for record in details:
            try:
                # Parse dates from detail record
                issue_date_str = record.get('issueDate')
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else None

                maturity_date_str = record.get('maturityDate')
                maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d').date() if maturity_date_str else None

                transformed.append({
                    'publication_date': publication_date,
                    'guide_type': guide_type,
                    'security_type': record.get('secType'),
                    'cusip': record.get('cusip'),
                    'issue_date': issue_date,
                    'maturity_date': maturity_date,
                    'coupon_rate': record.get('percentCouponRate'),
                    'settlement_price': record.get('settlementPrice'),
                    'accrued_interest': record.get('accruedInterest'),
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
                table='newyorkfed_guide_sheets',
                data=data,
                dataset_id=self.dataset_id
            )
            self.logger.info(
                f"Loaded {self.records_loaded} records to feeds.newyorkfed_guide_sheets",
                extra={'stepcounter': 'load'}
            )
        else:
            self.logger.info(f"DRY RUN: Would load {len(data)} records", extra={'stepcounter': 'load'})
            self.records_loaded = len(data)

    def cleanup(self):
        if self.client:
            self.client.close()


def main():
    parser = argparse.ArgumentParser(description='Import guide sheet data from NewYorkFed API')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--date', type=str, help='Run date (YYYY-MM-DD)')
    args = parser.parse_args()

    run_date = None
    if args.date:
        run_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    job = NewYorkFedGuideSheetsJob(run_date=run_date, dry_run=args.dry_run)
    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

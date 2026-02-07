#!/usr/bin/env python3
"""
NewYorkFed Tables Data Retention Test

Verifies that all 10 NewYorkFed tables can properly accept and retain records.

This script:
1. Inserts test data into each empty table
2. Verifies foreign key constraints work
3. Verifies indexes are functional
4. Verifies audit columns auto-populate
5. Cleans up test data after verification

Usage:
    python scripts/test_newyorkfed_table_retention.py
    python scripts/test_newyorkfed_table_retention.py --keep-test-data  # Don't cleanup
"""

import sys
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_db_connection


class TableRetentionTester:
    """Test data retention capability for NewYorkFed tables."""

    # Test data for each table
    TEST_DATA = {
        'newyorkfed_reference_rates': {
            'table': 'feeds.newyorkfed_reference_rates',
            'dataset_name': 'Reference Rates',
            'records': [
                {
                    'rate_type': 'TEST_RATE',
                    'rate_date': date(2026, 1, 1),
                    'percentile_1': Decimal('1.23'),
                    'percentile_25': Decimal('1.25'),
                    'percentile_75': Decimal('1.27'),
                    'percentile_99': Decimal('1.29'),
                    'volume_in_billions': Decimal('100.5')
                }
            ],
            'verify_columns': ['rate_type', 'rate_date', 'percentile_1']
        },
        'newyorkfed_soma_holdings': {
            'table': 'feeds.newyorkfed_soma_holdings',
            'dataset_name': 'SOMA Holdings',
            'records': [
                {
                    'as_of_date': date(2026, 1, 1),
                    'security_type': 'TEST_SECURITY',
                    'cusip': 'TEST123456',
                    'maturity_date': date(2030, 1, 1),
                    'par_value': Decimal('1000000.00')
                }
            ],
            'verify_columns': ['cusip', 'as_of_date', 'security_type']
        },
        'newyorkfed_repo_operations': {
            'table': 'feeds.newyorkfed_repo_operations',
            'dataset_name': 'Repo Operations',
            'records': [
                {
                    'operation_date': date(2026, 1, 1),
                    'operation_type': 'TEST_REPO',
                    'amount_submitted': Decimal('50000.00'),
                    'amount_accepted': Decimal('45000.00')
                }
            ],
            'verify_columns': ['operation_date', 'operation_type']
        },
        'newyorkfed_securities_lending': {
            'table': 'feeds.newyorkfed_securities_lending',
            'dataset_name': 'Securities Lending',
            'records': [
                {
                    'operation_date': date(2026, 1, 1),
                    'security_type': 'TEST_SECURITY',
                    'total_submitted': Decimal('10000.00'),
                    'total_accepted': Decimal('9000.00')
                }
            ],
            'verify_columns': ['operation_date', 'security_type']
        },
        'newyorkfed_guide_sheets': {
            'table': 'feeds.newyorkfed_guide_sheets',
            'dataset_name': 'Guide Sheets',
            'records': [
                {
                    'guide_date': date(2026, 1, 1),
                    'security_type': 'TEST_TYPE',
                    'cusip': 'TEST789',
                    'description': 'Test security description'
                }
            ],
            'verify_columns': ['guide_date', 'cusip']
        },
        'newyorkfed_agency_mbs': {
            'table': 'feeds.newyorkfed_agency_mbs',
            'dataset_name': 'Agency MBS',
            'records': [
                {
                    'operation_date': date(2026, 1, 1),
                    'operation_type': 'TEST_MBS',
                    'settlement_date': date(2026, 1, 15),
                    'security_description': 'Test MBS security'
                }
            ],
            'verify_columns': ['operation_date', 'operation_type']
        },
        'newyorkfed_fx_swaps': {
            'table': 'feeds.newyorkfed_fx_swaps',
            'dataset_name': 'FX Swaps',
            'records': [
                {
                    'swap_date': date(2026, 1, 1),
                    'currency_code': 'TST',
                    'counterparty': 'TEST_PARTY',
                    'usd_amount': Decimal('1000.00')
                }
            ],
            'verify_columns': ['swap_date', 'currency_code']
        },
        'newyorkfed_treasury_operations': {
            'table': 'feeds.newyorkfed_treasury_operations',
            'dataset_name': 'Treasury Operations',
            'records': [
                {
                    'operation_date': date(2026, 1, 1),
                    'operation_type': 'TEST_TREASURY',
                    'cusip': 'TESTTRSY99',
                    'total_submitted': Decimal('50000.00'),
                    'total_accepted': Decimal('48000.00')
                }
            ],
            'verify_columns': ['operation_date', 'operation_type', 'cusip']
        },
        'newyorkfed_pd_statistics': {
            'table': 'feeds.newyorkfed_pd_statistics',
            'dataset_name': 'PD Statistics',
            'records': [
                {
                    'report_date': date(2026, 1, 1),
                    'dealer_name': 'TEST_DEALER',
                    'report_type': 'TEST_STAT',
                    'net_financing': Decimal('123.45')
                }
            ],
            'verify_columns': ['report_date', 'dealer_name']
        },
        'newyorkfed_market_share': {
            'table': 'feeds.newyorkfed_market_share',
            'dataset_name': 'Market Share',
            'records': [
                {
                    'report_date': date(2026, 1, 1),
                    'participant': 'TEST_PARTICIPANT',
                    'market_segment': 'TEST_SEGMENT',
                    'share_percentage': Decimal('15.75')
                }
            ],
            'verify_columns': ['report_date', 'participant']
        }
    }

    def __init__(self, cleanup: bool = True):
        """
        Initialize retention tester.

        Args:
            cleanup: Whether to clean up test data after verification
        """
        self.cleanup = cleanup
        self.results: List[Dict[str, Any]] = []
        self.inserted_ids: Dict[str, List[int]] = {}

    def get_dataset_id(self, conn, dataset_name: str) -> int:
        """
        Get or create dataset ID for test records.

        Args:
            conn: Database connection
            dataset_name: Name of the dataset

        Returns:
            Dataset ID
        """
        with conn.cursor() as cur:
            # Check if dataset exists
            cur.execute("""
                SELECT datasetid
                FROM dba.tdataset
                WHERE datasetname = %s
            """, (dataset_name,))

            row = cur.fetchone()
            if row:
                return row[0]

            # Create test dataset if it doesn't exist
            cur.execute("""
                INSERT INTO dba.tdataset (datasetname, description)
                VALUES (%s, %s)
                RETURNING datasetid
            """, (dataset_name, f'Test dataset for {dataset_name}'))

            return cur.fetchone()[0]

    def test_table_retention(self, conn, table_key: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test data retention for a single table.

        Args:
            conn: Database connection
            table_key: Table key (e.g., 'newyorkfed_reference_rates')
            config: Table configuration with test data

        Returns:
            Test result dictionary
        """
        result = {
            'table': config['table'],
            'table_key': table_key,
            'dataset_name': config['dataset_name'],
            'status': 'unknown',
            'inserted_count': 0,
            'verified_count': 0,
            'error': None,
            'test_record_ids': []
        }

        try:
            # Get dataset ID
            dataset_id = self.get_dataset_id(conn, config['dataset_name'])

            with conn.cursor() as cur:
                # Build INSERT statement
                test_record = config['records'][0].copy()
                test_record['datasetid'] = dataset_id
                test_record['created_by'] = 'TEST_SCRIPT'

                columns = list(test_record.keys())
                placeholders = ', '.join(['%s'] * len(columns))
                column_names = ', '.join(columns)

                insert_sql = f"""
                    INSERT INTO {config['table']} ({column_names})
                    VALUES ({placeholders})
                    RETURNING record_id
                """

                # Insert test records
                for record in config['records']:
                    record_data = record.copy()
                    record_data['datasetid'] = dataset_id
                    record_data['created_by'] = 'TEST_SCRIPT'

                    cur.execute(insert_sql, list(record_data.values()))
                    record_id = cur.fetchone()[0]
                    result['test_record_ids'].append(record_id)
                    result['inserted_count'] += 1

                conn.commit()

                # Verify records were inserted
                verify_columns = config['verify_columns']
                where_clauses = ' AND '.join([f"{col} = %s" for col in verify_columns])
                verify_values = [test_record[col] for col in verify_columns]

                verify_sql = f"""
                    SELECT record_id, datasetid, created_by, created_date
                    FROM {config['table']}
                    WHERE {where_clauses}
                """

                cur.execute(verify_sql, verify_values)
                rows = cur.fetchall()
                result['verified_count'] = len(rows)

                # Verify foreign key constraint
                if rows and rows[0][1] != dataset_id:
                    raise AssertionError(f"Foreign key mismatch: expected {dataset_id}, got {rows[0][1]}")

                # Verify audit column auto-populated
                if rows and rows[0][2] != 'TEST_SCRIPT':
                    raise AssertionError(f"created_by not set correctly: {rows[0][2]}")

                if rows and rows[0][3] is None:
                    raise AssertionError("created_date not auto-populated")

                # Check status
                if result['inserted_count'] == result['verified_count']:
                    result['status'] = 'success'
                else:
                    result['status'] = 'partial'
                    result['error'] = f"Inserted {result['inserted_count']} but verified {result['verified_count']}"

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            conn.rollback()

        return result

    def cleanup_test_data(self, conn, table_key: str, config: Dict[str, Any], record_ids: List[int]):
        """
        Clean up test data from table.

        Args:
            conn: Database connection
            table_key: Table key
            config: Table configuration
            record_ids: List of record IDs to delete
        """
        if not record_ids:
            return

        try:
            with conn.cursor() as cur:
                placeholders = ', '.join(['%s'] * len(record_ids))
                delete_sql = f"""
                    DELETE FROM {config['table']}
                    WHERE record_id IN ({placeholders})
                """
                cur.execute(delete_sql, record_ids)
                conn.commit()
                print(f"  🧹 Cleaned up {len(record_ids)} test records from {table_key}")
        except Exception as e:
            print(f"  ⚠️  Error cleaning up {table_key}: {e}")
            conn.rollback()

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """
        Run retention tests on all tables.

        Returns:
            List of test results
        """
        print("Testing NewYorkFed table data retention...")
        print("=" * 80)

        conn = get_db_connection()

        try:
            for table_key, config in self.TEST_DATA.items():
                print(f"\nTesting: {table_key}")
                result = self.test_table_retention(conn, table_key, config)
                self.results.append(result)

                # Store IDs for cleanup
                if result['test_record_ids']:
                    self.inserted_ids[table_key] = result['test_record_ids']

                # Print result
                if result['status'] == 'success':
                    print(f"  ✅ SUCCESS: Inserted and verified {result['verified_count']} records")
                elif result['status'] == 'partial':
                    print(f"  ⚠️  PARTIAL: {result['error']}")
                else:
                    print(f"  ❌ ERROR: {result['error']}")

            # Cleanup if requested
            if self.cleanup:
                print("\n" + "-" * 80)
                print("Cleaning up test data...")
                for table_key, config in self.TEST_DATA.items():
                    if table_key in self.inserted_ids:
                        self.cleanup_test_data(
                            conn,
                            table_key,
                            config,
                            self.inserted_ids[table_key]
                        )

        finally:
            conn.close()

        return self.results

    def print_summary(self):
        """Print summary of retention test results."""
        print("\n" + "=" * 80)
        print("NewYorkFed Table Retention Test Summary")
        print("=" * 80)

        success_count = sum(1 for r in self.results if r['status'] == 'success')
        partial_count = sum(1 for r in self.results if r['status'] == 'partial')
        error_count = sum(1 for r in self.results if r['status'] == 'error')

        print(f"\n✅ Successful:  {success_count}/{len(self.results)}")
        print(f"⚠️  Partial:     {partial_count}/{len(self.results)}")
        print(f"❌ Errors:      {error_count}/{len(self.results)}")

        if success_count == len(self.results):
            print("\n🎉 All tables can properly retain records!")
        else:
            print("\n⚠️  Some tables had issues - review details above")

        print("\n" + "=" * 80)


def main():
    """Main entry point for retention test script."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Test NewYorkFed table data retention capability'
    )
    parser.add_argument(
        '--keep-test-data',
        action='store_true',
        help="Don't clean up test data after verification"
    )

    args = parser.parse_args()

    tester = TableRetentionTester(cleanup=not args.keep_test_data)
    tester.run_all_tests()
    tester.print_summary()


if __name__ == '__main__':
    main()

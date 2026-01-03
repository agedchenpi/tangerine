"""
Regression test suite for generic import system.

Executes all configured regression tests and logs results to dba.tregressiontest.
Continues testing even on failures to provide comprehensive test coverage reporting.

Usage:
    # Run all tests
    python etl/regression/run_regression_tests.py

    # Run specific category
    python etl/regression/run_regression_tests.py --category csv

    # Verbose output
    python etl/regression/run_regression_tests.py --verbose

    # Skip cleanup (leave test data in archive)
    python etl/regression/run_regression_tests.py --no-cleanup
"""

import argparse
import sys
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

from common.db_utils import db_connection, db_transaction, fetch_dict
from common.logging_utils import get_logger
from etl.jobs.generic_import import GenericImportJob, ConfigNotFoundError


@dataclass
class TestCase:
    """Represents a single regression test case."""
    config_id: int
    config_name: str
    test_name: str
    test_category: str
    expected_records: int
    file_path: str
    validation_rules: Optional[Dict] = None


class RegressionTestRunner:
    """
    Executes regression tests for generic import system.

    Features:
    - Non-blocking execution (continues on failure)
    - Database result persistence
    - Detailed error capture
    - Summary reporting
    """

    def __init__(self, suite_run_uuid: Optional[str] = None, verbose: bool = False):
        """
        Initialize regression test runner.

        Args:
            suite_run_uuid: Optional UUID for test suite run (generates new if not provided)
            verbose: Enable verbose logging
        """
        self.suite_run_uuid = suite_run_uuid or str(uuid.uuid4())
        self.verbose = verbose
        self.logger = get_logger('RegressionTestRunner', level='DEBUG' if verbose else 'INFO')

        self.test_results: List[Dict] = []
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_error = 0
        self.tests_skipped = 0

    def discover_tests(self, category: Optional[str] = None) -> List[TestCase]:
        """
        Discover regression test cases from database configurations.

        Args:
            category: Optional category filter (csv, xls, xlsx, json, xml)

        Returns:
            List of TestCase objects
        """
        self.logger.info(f"Discovering regression tests (category={category or 'all'})")

        query = """
            SELECT
                config_id,
                config_name,
                file_type,
                source_directory,
                file_pattern,
                target_table,
                importstrategyid
            FROM dba.timportconfig
            WHERE datasource = 'RegressionTest'
              AND datasettype = 'RegressionTest'
              AND is_active = TRUE
        """

        if category:
            query += f" AND file_type = '{category.upper()}'"

        query += " ORDER BY config_id"

        results = fetch_dict(query)

        test_cases = []
        for row in results:
            # Use config_name as-is (no REGRESSION_ prefix in configs anymore)
            test_name = row['config_name']
            test_category = row['file_type'].lower()

            # Get expected record count from test metadata
            expected_records = self._get_expected_records(test_name)

            # Construct file path
            file_path = self._construct_file_path(
                row['source_directory'],
                row['file_pattern']
            )

            test_case = TestCase(
                config_id=row['config_id'],
                config_name=row['config_name'],
                test_name=test_name,
                test_category=test_category,
                expected_records=expected_records,
                file_path=file_path
            )
            test_cases.append(test_case)

        self.logger.info(f"Discovered {len(test_cases)} test cases")
        return test_cases

    def _get_expected_records(self, test_name: str) -> int:
        """Map test names to expected record counts."""
        expected_map = {
            'CSV_Strategy1_AutoAddColumns': 5,
            'CSV_Strategy2_IgnoreExtraColumns': 3,
            'CSV_Strategy3_StrictValidation': 4,
            'CSV_MetadataFromFilename': 2,
            'CSV_EmptyFile': 0,
            'CSV_MalformedData': 2,
            'XLS_Strategy1_Inventory': 7,
            'XLS_MetadataFromContent': 4,
            'XLS_MultipleSheets': 3,
            'XLSX_Strategy2_Sales': 10,
            'XLSX_DateFromContent': 5,
            'XLSX_LargeFile': 1000,
            'JSON_ArrayFormat': 6,
            'JSON_ObjectFormat': 1,
            'JSON_NestedObjects': 1,
            'XML_StructuredFormat': 3,
            'XML_BlobFormat': 2,
        }
        return expected_map.get(test_name, 0)

    def _construct_file_path(self, source_dir: str, file_pattern: str) -> str:
        """Construct expected file path from pattern."""
        # Remove regex escaping for display purposes
        filename = file_pattern.replace('\\', '')
        return f"{source_dir}/{filename}"

    def run_test(self, test_case: TestCase) -> Dict:
        """
        Execute a single test case.

        Args:
            test_case: TestCase to execute

        Returns:
            Test result dictionary
        """
        self.logger.info(f"Running test: {test_case.test_name}")

        test_result = {
            'test_suite_run_uuid': self.suite_run_uuid,
            'test_name': test_case.test_name,
            'test_category': test_case.test_category,
            'config_id': test_case.config_id,
            'status': 'pending',
            'error_code': None,
            'error_message': None,
            'stack_trace': None,
            'expected_records': test_case.expected_records,
            'records_extracted': 0,
            'records_transformed': 0,
            'records_loaded': 0,
            'file_path': test_case.file_path,
            'run_uuid': None,
            'datasetid': None,
            'start_time': datetime.now(),
            'end_time': None,
            'duration_seconds': None,
            'test_metadata': {
                'config_name': test_case.config_name,
                'verbose': self.verbose
            }
        }

        try:
            # Execute import job
            job = GenericImportJob(
                config_id=test_case.config_id,
                dry_run=False
            )

            success = job.run()

            # Capture results
            test_result['records_extracted'] = job.records_extracted
            test_result['records_transformed'] = job.records_transformed
            test_result['records_loaded'] = job.records_loaded
            test_result['run_uuid'] = job.run_uuid
            test_result['datasetid'] = job.dataset_id

            # Validate results
            if test_result['records_loaded'] == test_case.expected_records:
                test_result['status'] = 'passed'
                self.tests_passed += 1
                self.logger.info(f"✓ PASSED: {test_case.test_name} ({test_result['records_loaded']} records)")
            else:
                test_result['status'] = 'failed'
                test_result['error_code'] = 'RECORD_COUNT_MISMATCH'
                test_result['error_message'] = (
                    f"Expected {test_case.expected_records} records, "
                    f"loaded {test_result['records_loaded']}"
                )
                self.tests_failed += 1
                self.logger.warning(f"✗ FAILED: {test_case.test_name} - {test_result['error_message']}")

        except ConfigNotFoundError as e:
            test_result['status'] = 'error'
            test_result['error_code'] = 'CONFIG_NOT_FOUND'
            test_result['error_message'] = str(e)
            test_result['stack_trace'] = traceback.format_exc()
            self.tests_error += 1
            self.logger.error(f"✗ ERROR: {test_case.test_name} - {test_result['error_message']}")

        except Exception as e:
            test_result['status'] = 'error'
            test_result['error_code'] = type(e).__name__
            test_result['error_message'] = str(e)
            test_result['stack_trace'] = traceback.format_exc()
            self.tests_error += 1
            self.logger.error(f"✗ ERROR: {test_case.test_name} - {test_result['error_message']}")
            if self.verbose:
                self.logger.debug(test_result['stack_trace'])

        finally:
            test_result['end_time'] = datetime.now()
            duration = (test_result['end_time'] - test_result['start_time']).total_seconds()
            test_result['duration_seconds'] = round(duration, 3)

        return test_result

    def save_test_result(self, test_result: Dict):
        """
        Save test result to dba.tregressiontest table.

        Args:
            test_result: Test result dictionary
        """
        insert_sql = """
            INSERT INTO dba.tregressiontest (
                test_suite_run_uuid, test_name, test_category, config_id,
                status, error_code, error_message, stack_trace,
                expected_records, records_extracted, records_transformed, records_loaded,
                file_path, run_uuid, datasetid,
                start_time, end_time, duration_seconds, test_metadata
            ) VALUES (
                %(test_suite_run_uuid)s, %(test_name)s, %(test_category)s, %(config_id)s,
                %(status)s, %(error_code)s, %(error_message)s, %(stack_trace)s,
                %(expected_records)s, %(records_extracted)s, %(records_transformed)s, %(records_loaded)s,
                %(file_path)s, %(run_uuid)s, %(datasetid)s,
                %(start_time)s, %(end_time)s, %(duration_seconds)s, %(test_metadata)s::jsonb
            )
        """

        # Convert test_metadata dict to JSON string
        test_result_copy = test_result.copy()
        test_result_copy['test_metadata'] = json.dumps(test_result['test_metadata'])

        try:
            with db_transaction() as cursor:
                cursor.execute(insert_sql, test_result_copy)
            self.logger.debug(f"Saved test result: {test_result['test_name']}")
        except Exception as e:
            self.logger.error(f"Failed to save test result: {e}")

    def run_all(self, category: Optional[str] = None) -> bool:
        """
        Run all regression tests.

        Args:
            category: Optional category filter

        Returns:
            True if all tests passed, False otherwise
        """
        self.logger.info(f"Starting regression test suite: {self.suite_run_uuid}")
        suite_start = datetime.now()

        # Discover tests
        test_cases = self.discover_tests(category=category)

        if not test_cases:
            self.logger.warning("No test cases discovered")
            return False

        # Execute tests (non-blocking - continue on failure)
        for test_case in test_cases:
            test_result = self.run_test(test_case)
            self.test_results.append(test_result)
            self.save_test_result(test_result)

        # Print summary
        suite_end = datetime.now()
        suite_duration = (suite_end - suite_start).total_seconds()

        self.print_summary(suite_duration)

        return self.tests_failed == 0 and self.tests_error == 0

    def print_summary(self, duration: float):
        """Print test suite summary."""
        total_tests = len(self.test_results)

        print("\n" + "="*80)
        print("REGRESSION TEST SUITE SUMMARY")
        print("="*80)
        print(f"Suite Run UUID:    {self.suite_run_uuid}")
        print(f"Total Tests:       {total_tests}")
        print(f"Passed:            {self.tests_passed} ({100*self.tests_passed/total_tests if total_tests > 0 else 0:.1f}%)")
        print(f"Failed:            {self.tests_failed}")
        print(f"Errors:            {self.tests_error}")
        print(f"Skipped:           {self.tests_skipped}")
        print(f"Total Duration:    {duration:.2f} seconds")
        print("="*80)

        if self.tests_failed > 0 or self.tests_error > 0:
            print("\nFAILED/ERROR TESTS:")
            for result in self.test_results:
                if result['status'] in ('failed', 'error'):
                    print(f"  - {result['test_name']}: {result['error_message']}")
            print()

        print(f"\nDetailed results stored in: dba.tregressiontest")
        print(f"Query: SELECT * FROM dba.tregressiontest WHERE test_suite_run_uuid = '{self.suite_run_uuid}';")
        print(f"Summary: SELECT * FROM dba.vregressiontest_summary WHERE test_suite_run_uuid = '{self.suite_run_uuid}';")
        print()


def main():
    """Main entry point for regression test suite."""
    parser = argparse.ArgumentParser(
        description='Run regression tests for generic import system'
    )
    parser.add_argument(
        '--category',
        type=str,
        choices=['csv', 'xls', 'xlsx', 'json', 'xml'],
        help='Run tests for specific file type only'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--suite-uuid',
        type=str,
        help='Use specific suite UUID (for reruns)'
    )

    args = parser.parse_args()

    # Run tests
    runner = RegressionTestRunner(
        suite_run_uuid=args.suite_uuid,
        verbose=args.verbose
    )

    success = runner.run_all(category=args.category)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

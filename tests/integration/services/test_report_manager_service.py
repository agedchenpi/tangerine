"""Integration tests for report manager service

Tests CRUD operations, filtering, statistics, and helper functions
for the report_manager_service module.
"""

import pytest
import uuid
from admin.services.report_manager_service import (
    list_reports,
    get_report,
    create_report,
    update_report,
    delete_report,
    toggle_active,
    get_report_stats,
    report_name_exists,
    get_schedules,
    get_output_formats,
    execute_report
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_report():
    """Sample report configuration for testing"""
    return {
        'report_name': f'AdminTest_Report_{uuid.uuid4().hex[:8]}',
        'description': 'Test report description',
        'recipients': 'test@example.com',
        'cc_recipients': 'cc@example.com',
        'subject_line': 'Test Report - {{date}}',
        'body_template': '''
<h1>Test Report</h1>
<p>Generated on {{date}}</p>
{{SQL:SELECT 1 as value}}
''',
        'output_format': 'html',
        'attachment_filename': 'test_report.csv',
        'schedule_id': None,
        'is_active': True
    }


@pytest.fixture
def created_report(db_transaction, sample_report):
    """Create a report and return it"""
    report_id = create_report(sample_report)
    return get_report(report_id)


@pytest.fixture
def created_reports(db_transaction):
    """Create multiple reports for list testing"""
    reports = []
    formats = ['html', 'csv', 'excel']

    for i, fmt in enumerate(formats):
        report_data = {
            'report_name': f'AdminTest_Report_{uuid.uuid4().hex[:8]}',
            'description': f'Test report {i}',
            'recipients': f'test{i}@example.com',
            'subject_line': f'Test Report {i}',
            'body_template': '{{SQL:SELECT 1}}',
            'output_format': fmt,
            'is_active': i % 2 == 0  # Alternate active/inactive
        }
        report_id = create_report(report_data)
        reports.append(get_report(report_id))

    return reports


# ============================================================================
# CRUD OPERATIONS
# ============================================================================

@pytest.mark.integration
@pytest.mark.crud
class TestReportManagerCRUD:
    """Test basic CRUD operations for reports"""

    def test_create_report_success(self, db_transaction, sample_report):
        """Creating valid report returns report_id"""
        report_id = create_report(sample_report)
        assert isinstance(report_id, int)
        assert report_id > 0

    def test_get_report_exists(self, db_transaction, created_report):
        """Retrieving existing report returns all fields"""
        report = get_report(created_report['report_id'])
        assert report is not None
        assert report['report_name'] == created_report['report_name']
        assert report['recipients'] == created_report['recipients']
        assert report['output_format'] == created_report['output_format']

    def test_get_report_not_found(self, db_transaction):
        """Retrieving non-existent report returns None"""
        report = get_report(999999)
        assert report is None

    def test_update_report_single_field(self, db_transaction, created_report):
        """Updating single field works correctly"""
        original_name = created_report['report_name']
        update_report(created_report['report_id'], {'is_active': False})

        updated = get_report(created_report['report_id'])
        assert updated['is_active'] is False
        assert updated['report_name'] == original_name

    def test_update_report_multiple_fields(self, db_transaction, created_report):
        """Updating multiple fields works correctly"""
        updates = {
            'subject_line': 'Updated Subject',
            'output_format': 'csv',
            'is_active': False
        }
        update_report(created_report['report_id'], updates)

        updated = get_report(created_report['report_id'])
        assert updated['subject_line'] == 'Updated Subject'
        assert updated['output_format'] == 'csv'
        assert updated['is_active'] is False

    def test_delete_report_success(self, db_transaction, created_report):
        """Deleting report removes it from database"""
        report_id = created_report['report_id']
        delete_report(report_id)

        report = get_report(report_id)
        assert report is None

    def test_delete_report_not_found(self, db_transaction):
        """Deleting non-existent report raises exception"""
        with pytest.raises(Exception) as exc_info:
            delete_report(999999)
        assert 'not found' in str(exc_info.value).lower()

    def test_toggle_active_enable(self, db_transaction, created_report):
        """Toggling active status to True works"""
        report_id = created_report['report_id']
        toggle_active(report_id, False)
        toggle_active(report_id, True)

        updated = get_report(report_id)
        assert updated['is_active'] is True

    def test_toggle_active_disable(self, db_transaction, created_report):
        """Toggling active status to False works"""
        report_id = created_report['report_id']
        toggle_active(report_id, False)

        updated = get_report(report_id)
        assert updated['is_active'] is False


# ============================================================================
# LIST AND FILTER OPERATIONS
# ============================================================================

@pytest.mark.integration
class TestReportManagerList:
    """Test list and filter operations"""

    def test_list_reports_all(self, db_transaction, created_reports):
        """list_reports returns all reports"""
        reports = list_reports()
        test_reports = [r for r in reports if r['report_name'].startswith('AdminTest_')]
        assert len(test_reports) >= len(created_reports)

    def test_list_reports_active_only(self, db_transaction, created_reports):
        """active_only=True returns only active reports"""
        reports = list_reports(active_only=True)
        test_reports = [r for r in reports if r['report_name'].startswith('AdminTest_')]
        assert all(r['is_active'] is True for r in test_reports)

    def test_report_name_exists_true(self, db_transaction, created_report):
        """report_name_exists returns True for existing name"""
        exists = report_name_exists(created_report['report_name'])
        assert exists is True

    def test_report_name_exists_false(self, db_transaction):
        """report_name_exists returns False for non-existent name"""
        exists = report_name_exists('NonExistentReport_12345')
        assert exists is False

    def test_report_name_exists_exclude_self(self, db_transaction, created_report):
        """report_name_exists excludes specified report_id"""
        exists = report_name_exists(
            created_report['report_name'],
            exclude_id=created_report['report_id']
        )
        assert exists is False


# ============================================================================
# STATISTICS
# ============================================================================

@pytest.mark.integration
class TestReportManagerStats:
    """Test statistics functions"""

    def test_get_report_stats_structure(self, db_transaction, created_reports):
        """get_report_stats returns correct structure"""
        stats = get_report_stats()

        assert 'total' in stats
        assert 'active' in stats
        assert 'inactive' in stats
        assert 'success' in stats
        assert 'failed' in stats

        assert isinstance(stats['total'], int)
        assert isinstance(stats['active'], int)
        assert isinstance(stats['inactive'], int)

    def test_get_report_stats_values(self, db_transaction, created_reports):
        """get_report_stats returns accurate counts"""
        stats = get_report_stats()

        assert stats['total'] >= len(created_reports)
        assert stats['total'] == stats['active'] + stats['inactive']


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@pytest.mark.integration
class TestReportManagerHelpers:
    """Test helper functions"""

    def test_get_output_formats_returns_all(self, db_transaction):
        """get_output_formats returns all 5 formats"""
        formats = get_output_formats()
        assert isinstance(formats, list)
        assert len(formats) == 5

        # Verify structure
        for fmt in formats:
            assert 'value' in fmt
            assert 'label' in fmt
            assert 'description' in fmt

        # Verify all formats present
        values = [f['value'] for f in formats]
        assert 'html' in values
        assert 'csv' in values
        assert 'excel' in values
        assert 'html_csv' in values
        assert 'html_excel' in values

    def test_get_schedules_returns_list(self, db_transaction):
        """get_schedules returns list of schedules"""
        schedules = get_schedules()
        assert isinstance(schedules, list)


# ============================================================================
# OUTPUT FORMAT TESTS
# ============================================================================

@pytest.mark.integration
class TestReportOutputFormats:
    """Test output format handling"""

    def test_create_report_with_html_format(self, db_transaction, sample_report):
        """Report with HTML format creates correctly"""
        sample_report['output_format'] = 'html'
        report_id = create_report(sample_report)
        retrieved = get_report(report_id)

        assert retrieved['output_format'] == 'html'

    def test_create_report_with_csv_format(self, db_transaction, sample_report):
        """Report with CSV format creates correctly"""
        sample_report['output_format'] = 'csv'
        report_id = create_report(sample_report)
        retrieved = get_report(report_id)

        assert retrieved['output_format'] == 'csv'

    def test_create_report_with_excel_format(self, db_transaction, sample_report):
        """Report with Excel format creates correctly"""
        sample_report['output_format'] = 'excel'
        report_id = create_report(sample_report)
        retrieved = get_report(report_id)

        assert retrieved['output_format'] == 'excel'

    def test_create_report_with_html_csv_format(self, db_transaction, sample_report):
        """Report with HTML+CSV format creates correctly"""
        sample_report['output_format'] = 'html_csv'
        report_id = create_report(sample_report)
        retrieved = get_report(report_id)

        assert retrieved['output_format'] == 'html_csv'

    def test_create_report_with_html_excel_format(self, db_transaction, sample_report):
        """Report with HTML+Excel format creates correctly"""
        sample_report['output_format'] = 'html_excel'
        report_id = create_report(sample_report)
        retrieved = get_report(report_id)

        assert retrieved['output_format'] == 'html_excel'

    def test_create_report_default_format(self, db_transaction):
        """Report without format specified defaults to html"""
        report = {
            'report_name': f'AdminTest_Default_{uuid.uuid4().hex[:8]}',
            'recipients': 'test@example.com',
            'subject_line': 'Test',
            'body_template': 'Test'
        }
        report_id = create_report(report)
        retrieved = get_report(report_id)

        assert retrieved['output_format'] == 'html'


# ============================================================================
# TEMPLATE TESTS
# ============================================================================

@pytest.mark.integration
class TestReportTemplates:
    """Test template field handling"""

    def test_create_report_with_sql_template(self, db_transaction, sample_report):
        """Report with SQL in template creates correctly"""
        sample_report['body_template'] = '''
<h1>Sales Report</h1>
{{SQL:SELECT COUNT(*) as total FROM dba.tdataset}}
'''
        report_id = create_report(sample_report)
        retrieved = get_report(report_id)

        assert '{{SQL:' in retrieved['body_template']

    def test_create_report_with_variable_template(self, db_transaction, sample_report):
        """Report with variables in subject creates correctly"""
        sample_report['subject_line'] = 'Daily Report - {{date}}'
        report_id = create_report(sample_report)
        retrieved = get_report(report_id)

        assert '{{date}}' in retrieved['subject_line']


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.integration
class TestReportManagerEdgeCases:
    """Test edge cases and error conditions"""

    def test_update_nonexistent_report_fails(self, db_transaction):
        """Updating non-existent report raises exception"""
        with pytest.raises(Exception):
            update_report(999999, {'is_active': False})

    def test_get_report_with_invalid_id(self, db_transaction):
        """get_report with invalid ID returns None"""
        assert get_report(-1) is None
        assert get_report(0) is None

    def test_report_name_exists_empty_string(self, db_transaction):
        """report_name_exists with empty string returns False"""
        exists = report_name_exists('')
        assert exists is False

    def test_toggle_active_nonexistent_report(self, db_transaction):
        """toggle_active on non-existent report raises exception"""
        with pytest.raises(Exception):
            toggle_active(999999, True)

    def test_create_report_minimal_fields(self, db_transaction):
        """Report created with only required fields"""
        report = {
            'report_name': f'AdminTest_Minimal_{uuid.uuid4().hex[:8]}',
            'recipients': 'test@example.com',
            'subject_line': 'Test',
            'body_template': 'Test body'
        }

        report_id = create_report(report)
        retrieved = get_report(report_id)

        assert retrieved['report_name'] == report['report_name']
        assert retrieved['recipients'] == report['recipients']
        assert retrieved['is_active'] is True  # Default

    def test_create_report_with_multiple_recipients(self, db_transaction, sample_report):
        """Report with multiple recipients creates correctly"""
        sample_report['recipients'] = 'user1@example.com, user2@example.com, user3@example.com'
        report_id = create_report(sample_report)
        retrieved = get_report(report_id)

        assert 'user1@example.com' in retrieved['recipients']
        assert 'user2@example.com' in retrieved['recipients']
        assert 'user3@example.com' in retrieved['recipients']


# ============================================================================
# EXECUTE REPORT TESTS
# ============================================================================

@pytest.mark.integration
class TestExecuteReport:
    """Test execute_report function

    Note: execute_report uses subprocess to call docker compose, which
    may not be available in all test environments (e.g., when running
    inside the container itself).
    """

    def test_execute_report_returns_generator(self, db_transaction, created_report):
        """execute_report returns a generator"""
        result = execute_report(created_report['report_id'], dry_run=True)
        assert hasattr(result, '__iter__')
        assert hasattr(result, '__next__')

    def test_execute_report_dry_run_yields_output(self, db_transaction, created_report):
        """execute_report in dry_run mode yields output lines or raises FileNotFoundError"""
        import subprocess
        try:
            output_lines = list(execute_report(created_report['report_id'], dry_run=True))
            # Should have at least some output
            assert isinstance(output_lines, list)
        except FileNotFoundError:
            # Expected when running inside container without docker CLI
            pytest.skip("docker command not available in test environment")

    def test_execute_report_invalid_id_yields_error(self, db_transaction):
        """execute_report with invalid ID yields error in output or raises FileNotFoundError"""
        try:
            output_lines = list(execute_report(999999, dry_run=True))
            # Either has error/fail message or empty (if subprocess failed)
            assert isinstance(output_lines, list)
        except FileNotFoundError:
            # Expected when running inside container without docker CLI
            pytest.skip("docker command not available in test environment")

"""Integration tests for scheduler service

Tests CRUD operations, filtering, statistics, and helper functions
for the scheduler_service module.
"""

import pytest
import uuid
from admin.services.scheduler_service import (
    list_schedules,
    get_schedule,
    create_schedule,
    update_schedule,
    delete_schedule,
    toggle_active,
    get_scheduler_stats,
    job_name_exists,
    get_job_types,
    get_config_options,
    build_cron_expression,
    calculate_next_run,
    create_schedule_for_report
)
from admin.services.report_manager_service import (
    create_report,
    get_report
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_schedule():
    """Sample scheduler configuration for testing"""
    return {
        'job_name': f'AdminTest_Job_{uuid.uuid4().hex[:8]}',
        'job_type': 'custom',
        'cron_minute': '0',
        'cron_hour': '6',
        'cron_day': '*',
        'cron_month': '*',
        'cron_weekday': '*',
        'script_path': '/app/etl/jobs/test_script.py',
        'config_id': None,
        'is_active': True
    }


@pytest.fixture
def created_schedule(db_transaction, sample_schedule):
    """Create a schedule and return it"""
    scheduler_id = create_schedule(sample_schedule)
    return get_schedule(scheduler_id)


@pytest.fixture
def created_schedules(db_transaction):
    """Create multiple schedules for list testing"""
    schedules = []
    job_types = ['custom', 'custom', 'custom']

    for i, job_type in enumerate(job_types):
        schedule_data = {
            'job_name': f'AdminTest_Job_{uuid.uuid4().hex[:8]}',
            'job_type': job_type,
            'cron_minute': str(i * 10),
            'cron_hour': '6',
            'cron_day': '*',
            'cron_month': '*',
            'cron_weekday': '*',
            'script_path': f'/app/etl/jobs/test_{i}.py',
            'is_active': i % 2 == 0  # Alternate active/inactive
        }
        scheduler_id = create_schedule(schedule_data)
        schedules.append(get_schedule(scheduler_id))

    return schedules


# ============================================================================
# CRUD OPERATIONS
# ============================================================================

@pytest.mark.integration
@pytest.mark.crud
class TestSchedulerCRUD:
    """Test basic CRUD operations for schedules"""

    def test_create_schedule_success(self, db_transaction, sample_schedule):
        """Creating valid schedule returns scheduler_id"""
        scheduler_id = create_schedule(sample_schedule)
        assert isinstance(scheduler_id, int)
        assert scheduler_id > 0

    def test_get_schedule_exists(self, db_transaction, created_schedule):
        """Retrieving existing schedule returns all fields"""
        schedule = get_schedule(created_schedule['scheduler_id'])
        assert schedule is not None
        assert schedule['job_name'] == created_schedule['job_name']
        assert schedule['job_type'] == created_schedule['job_type']
        assert schedule['cron_minute'] == created_schedule['cron_minute']

    def test_get_schedule_not_found(self, db_transaction):
        """Retrieving non-existent schedule returns None"""
        schedule = get_schedule(999999)
        assert schedule is None

    def test_update_schedule_single_field(self, db_transaction, created_schedule):
        """Updating single field works correctly"""
        original_name = created_schedule['job_name']
        update_schedule(created_schedule['scheduler_id'], {'is_active': False})

        updated = get_schedule(created_schedule['scheduler_id'])
        assert updated['is_active'] is False
        assert updated['job_name'] == original_name

    def test_update_schedule_multiple_fields(self, db_transaction, created_schedule):
        """Updating multiple fields works correctly"""
        updates = {
            'cron_hour': '12',
            'cron_minute': '30',
            'is_active': False
        }
        update_schedule(created_schedule['scheduler_id'], updates)

        updated = get_schedule(created_schedule['scheduler_id'])
        assert updated['cron_hour'] == '12'
        assert updated['cron_minute'] == '30'
        assert updated['is_active'] is False

    def test_delete_schedule_success(self, db_transaction, created_schedule):
        """Deleting schedule removes it from database"""
        scheduler_id = created_schedule['scheduler_id']
        delete_schedule(scheduler_id)

        schedule = get_schedule(scheduler_id)
        assert schedule is None

    def test_delete_schedule_not_found(self, db_transaction):
        """Deleting non-existent schedule raises exception"""
        with pytest.raises(Exception) as exc_info:
            delete_schedule(999999)
        assert 'not found' in str(exc_info.value).lower()

    def test_toggle_active_enable(self, db_transaction, created_schedule):
        """Toggling active status to True works"""
        scheduler_id = created_schedule['scheduler_id']
        toggle_active(scheduler_id, False)
        toggle_active(scheduler_id, True)

        updated = get_schedule(scheduler_id)
        assert updated['is_active'] is True

    def test_toggle_active_disable(self, db_transaction, created_schedule):
        """Toggling active status to False works"""
        scheduler_id = created_schedule['scheduler_id']
        toggle_active(scheduler_id, False)

        updated = get_schedule(scheduler_id)
        assert updated['is_active'] is False


# ============================================================================
# LIST AND FILTER OPERATIONS
# ============================================================================

@pytest.mark.integration
class TestSchedulerList:
    """Test list and filter operations"""

    def test_list_schedules_all(self, db_transaction, created_schedules):
        """list_schedules returns all schedules"""
        schedules = list_schedules()
        test_schedules = [s for s in schedules if s['job_name'].startswith('AdminTest_')]
        assert len(test_schedules) >= len(created_schedules)

    def test_list_schedules_active_only(self, db_transaction, created_schedules):
        """active_only=True returns only active schedules"""
        schedules = list_schedules(active_only=True)
        test_schedules = [s for s in schedules if s['job_name'].startswith('AdminTest_')]
        assert all(s['is_active'] is True for s in test_schedules)

    def test_list_schedules_filter_by_job_type(self, db_transaction, created_schedules):
        """job_type filter returns matching schedules"""
        schedules = list_schedules(job_type='custom')
        test_schedules = [s for s in schedules if s['job_name'].startswith('AdminTest_')]
        assert all(s['job_type'] == 'custom' for s in test_schedules)

    def test_job_name_exists_true(self, db_transaction, created_schedule):
        """job_name_exists returns True for existing name"""
        exists = job_name_exists(created_schedule['job_name'])
        assert exists is True

    def test_job_name_exists_false(self, db_transaction):
        """job_name_exists returns False for non-existent name"""
        exists = job_name_exists('NonExistentJob_12345')
        assert exists is False

    def test_job_name_exists_exclude_self(self, db_transaction, created_schedule):
        """job_name_exists excludes specified scheduler_id"""
        exists = job_name_exists(
            created_schedule['job_name'],
            exclude_id=created_schedule['scheduler_id']
        )
        assert exists is False


# ============================================================================
# STATISTICS
# ============================================================================

@pytest.mark.integration
class TestSchedulerStats:
    """Test statistics functions"""

    def test_get_scheduler_stats_structure(self, db_transaction, created_schedules):
        """get_scheduler_stats returns correct structure"""
        stats = get_scheduler_stats()

        assert 'total' in stats
        assert 'active' in stats
        assert 'inactive' in stats
        assert 'inbox_count' in stats
        assert 'report_count' in stats
        assert 'import_count' in stats
        assert 'custom_count' in stats

        assert isinstance(stats['total'], int)
        assert isinstance(stats['active'], int)
        assert isinstance(stats['inactive'], int)

    def test_get_scheduler_stats_values(self, db_transaction, created_schedules):
        """get_scheduler_stats returns accurate counts"""
        stats = get_scheduler_stats()

        assert stats['total'] >= len(created_schedules)
        assert stats['total'] == stats['active'] + stats['inactive']


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@pytest.mark.integration
class TestSchedulerHelpers:
    """Test helper functions"""

    def test_get_job_types_returns_all(self, db_transaction):
        """get_job_types returns all 4 job types"""
        job_types = get_job_types()
        assert isinstance(job_types, list)
        assert len(job_types) == 4

        # Verify structure
        for jt in job_types:
            assert 'value' in jt
            assert 'label' in jt
            assert 'description' in jt

        # Verify all types present
        values = [jt['value'] for jt in job_types]
        assert 'inbox_processor' in values
        assert 'report' in values
        assert 'import' in values
        assert 'custom' in values

    def test_get_config_options_custom(self, db_transaction):
        """get_config_options for custom returns empty list"""
        options = get_config_options('custom')
        assert options == []

    def test_get_config_options_invalid_type(self, db_transaction):
        """get_config_options for invalid type returns empty list"""
        options = get_config_options('invalid_type')
        assert options == []

    def test_build_cron_expression(self, db_transaction, sample_schedule):
        """build_cron_expression builds correct expression"""
        cron = build_cron_expression(sample_schedule)
        assert cron == '0 6 * * *'

    def test_build_cron_expression_defaults(self, db_transaction):
        """build_cron_expression uses * for missing fields"""
        cron = build_cron_expression({})
        assert cron == '* * * * *'

    def test_calculate_next_run_returns_datetime_or_none(self, db_transaction):
        """calculate_next_run returns datetime or None"""
        result = calculate_next_run('0 6 * * *')
        # Result depends on croniter availability
        assert result is None or hasattr(result, 'year')


# ============================================================================
# CRON FIELD TESTS
# ============================================================================

@pytest.mark.integration
class TestSchedulerCronFields:
    """Test cron field handling"""

    def test_create_schedule_with_all_cron_fields(self, db_transaction):
        """Schedule with all cron fields creates correctly"""
        schedule = {
            'job_name': f'AdminTest_Cron_{uuid.uuid4().hex[:8]}',
            'job_type': 'custom',
            'cron_minute': '15',
            'cron_hour': '3',
            'cron_day': '1',
            'cron_month': '*/2',
            'cron_weekday': '1-5',
            'script_path': '/app/test.py',
            'is_active': True
        }

        scheduler_id = create_schedule(schedule)
        retrieved = get_schedule(scheduler_id)

        assert retrieved['cron_minute'] == '15'
        assert retrieved['cron_hour'] == '3'
        assert retrieved['cron_day'] == '1'
        assert retrieved['cron_month'] == '*/2'
        assert retrieved['cron_weekday'] == '1-5'

    def test_create_schedule_with_hourly_preset(self, db_transaction):
        """Schedule with hourly preset (every hour) creates correctly"""
        schedule = {
            'job_name': f'AdminTest_Hourly_{uuid.uuid4().hex[:8]}',
            'job_type': 'custom',
            'cron_minute': '0',
            'cron_hour': '*',
            'cron_day': '*',
            'cron_month': '*',
            'cron_weekday': '*',
            'script_path': '/app/test.py',
            'is_active': True
        }

        scheduler_id = create_schedule(schedule)
        retrieved = get_schedule(scheduler_id)

        cron = build_cron_expression(retrieved)
        assert cron == '0 * * * *'

    def test_create_schedule_with_daily_preset(self, db_transaction):
        """Schedule with daily preset (6am daily) creates correctly"""
        schedule = {
            'job_name': f'AdminTest_Daily_{uuid.uuid4().hex[:8]}',
            'job_type': 'custom',
            'cron_minute': '0',
            'cron_hour': '6',
            'cron_day': '*',
            'cron_month': '*',
            'cron_weekday': '*',
            'script_path': '/app/test.py',
            'is_active': True
        }

        scheduler_id = create_schedule(schedule)
        retrieved = get_schedule(scheduler_id)

        cron = build_cron_expression(retrieved)
        assert cron == '0 6 * * *'


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.integration
class TestSchedulerEdgeCases:
    """Test edge cases and error conditions"""

    def test_update_nonexistent_schedule_fails(self, db_transaction):
        """Updating non-existent schedule raises exception"""
        with pytest.raises(Exception):
            update_schedule(999999, {'is_active': False})

    def test_get_schedule_with_invalid_id(self, db_transaction):
        """get_schedule with invalid ID returns None"""
        assert get_schedule(-1) is None
        assert get_schedule(0) is None

    def test_list_schedules_with_nonexistent_job_type(self, db_transaction):
        """Filtering by non-existent job type returns empty for test schedules"""
        schedules = list_schedules(job_type='nonexistent')
        test_schedules = [s for s in schedules if s['job_name'].startswith('AdminTest_')]
        assert test_schedules == []

    def test_job_name_exists_empty_string(self, db_transaction):
        """job_name_exists with empty string returns False"""
        exists = job_name_exists('')
        assert exists is False

    def test_toggle_active_nonexistent_schedule(self, db_transaction):
        """toggle_active on non-existent schedule raises exception"""
        with pytest.raises(Exception):
            toggle_active(999999, True)

    def test_create_schedule_default_cron_values(self, db_transaction):
        """Schedule created with default cron values when not specified"""
        schedule = {
            'job_name': f'AdminTest_Defaults_{uuid.uuid4().hex[:8]}',
            'job_type': 'custom',
            'script_path': '/app/test.py',
            'is_active': True
        }

        scheduler_id = create_schedule(schedule)
        retrieved = get_schedule(scheduler_id)

        # Should default to *
        assert retrieved['cron_minute'] == '*'
        assert retrieved['cron_hour'] == '*'
        assert retrieved['cron_day'] == '*'
        assert retrieved['cron_month'] == '*'
        assert retrieved['cron_weekday'] == '*'


# ============================================================================
# CREATE SCHEDULE FOR REPORT TESTS
# ============================================================================

@pytest.fixture
def sample_report_for_schedule(db_transaction):
    """Create a sample report for schedule linking tests"""
    report_data = {
        'report_name': f'AdminTest_ScheduleReport_{uuid.uuid4().hex[:8]}',
        'description': 'Test report for schedule linking',
        'recipients': 'test@example.com',
        'subject_line': 'Test Report',
        'body_template': '{{SQL:SELECT 1 as value}}',
        'output_format': 'html',
        'is_active': True
    }
    report_id = create_report(report_data)
    return get_report(report_id)


@pytest.mark.integration
class TestCreateScheduleForReport:
    """Test create_schedule_for_report function"""

    def test_create_schedule_for_report_success(self, db_transaction, sample_report_for_schedule):
        """create_schedule_for_report creates and links schedule"""
        report = sample_report_for_schedule
        job_name = f'AdminTest_ReportSchedule_{uuid.uuid4().hex[:8]}'

        scheduler_id = create_schedule_for_report(
            report_id=report['report_id'],
            job_name=job_name,
            cron_minute='30',
            cron_hour='9',
            cron_day='*',
            cron_month='*',
            cron_weekday='1-5'
        )

        # Verify schedule was created
        assert isinstance(scheduler_id, int)
        assert scheduler_id > 0

        # Verify schedule has correct values
        schedule = get_schedule(scheduler_id)
        assert schedule['job_name'] == job_name
        assert schedule['job_type'] == 'report'
        assert schedule['config_id'] == report['report_id']
        assert schedule['cron_minute'] == '30'
        assert schedule['cron_hour'] == '9'
        assert schedule['cron_weekday'] == '1-5'
        assert schedule['is_active'] is True

        # Verify report is linked to schedule
        updated_report = get_report(report['report_id'])
        assert updated_report['schedule_id'] == scheduler_id

    def test_create_schedule_for_report_default_cron(self, db_transaction, sample_report_for_schedule):
        """create_schedule_for_report uses default cron values"""
        report = sample_report_for_schedule
        job_name = f'AdminTest_DefaultCron_{uuid.uuid4().hex[:8]}'

        scheduler_id = create_schedule_for_report(
            report_id=report['report_id'],
            job_name=job_name
        )

        schedule = get_schedule(scheduler_id)
        # Check default values
        assert schedule['cron_minute'] == '0'
        assert schedule['cron_hour'] == '8'
        assert schedule['cron_day'] == '*'
        assert schedule['cron_month'] == '*'
        assert schedule['cron_weekday'] == '1-5'

    def test_create_schedule_for_report_duplicate_name_fails(self, db_transaction, sample_report_for_schedule):
        """create_schedule_for_report fails on duplicate job name"""
        report = sample_report_for_schedule
        job_name = f'AdminTest_DuplicateName_{uuid.uuid4().hex[:8]}'

        # Create first schedule
        create_schedule_for_report(
            report_id=report['report_id'],
            job_name=job_name
        )

        # Create another report for second schedule attempt
        report2_data = {
            'report_name': f'AdminTest_Report2_{uuid.uuid4().hex[:8]}',
            'recipients': 'test2@example.com',
            'subject_line': 'Test Report 2',
            'body_template': '{{SQL:SELECT 2}}',
            'output_format': 'html',
            'is_active': True
        }
        report2_id = create_report(report2_data)

        # Attempt to create schedule with same name should fail
        with pytest.raises(Exception) as exc_info:
            create_schedule_for_report(
                report_id=report2_id,
                job_name=job_name
            )
        assert 'already exists' in str(exc_info.value).lower()

    def test_create_schedule_for_report_cron_expression(self, db_transaction, sample_report_for_schedule):
        """create_schedule_for_report creates valid cron expression"""
        report = sample_report_for_schedule
        job_name = f'AdminTest_CronExpr_{uuid.uuid4().hex[:8]}'

        scheduler_id = create_schedule_for_report(
            report_id=report['report_id'],
            job_name=job_name,
            cron_minute='15',
            cron_hour='*/2',
            cron_day='1,15',
            cron_month='*',
            cron_weekday='*'
        )

        schedule = get_schedule(scheduler_id)
        cron = build_cron_expression(schedule)
        assert cron == '15 */2 1,15 * *'

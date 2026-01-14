"""Integration tests for inbox configuration service

Tests CRUD operations and pattern testing functions for inbox configs.
This is part of Phase 1 regression tests.
"""

import pytest
import uuid
from admin.services.inbox_config_service import (
    list_inbox_configs,
    get_inbox_config,
    create_inbox_config,
    update_inbox_config,
    delete_inbox_config,
    toggle_active,
    get_inbox_stats,
    config_name_exists,
    get_import_configs,
    validate_subject_pattern,
    validate_sender_pattern,
    validate_attachment_pattern,
    get_pattern_test_summary
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_inbox_config():
    """Sample inbox configuration for testing"""
    return {
        'config_name': f'AdminTest_Inbox_{uuid.uuid4().hex[:8]}',
        'description': 'Test inbox configuration',
        'subject_pattern': r'.*Report.*',
        'sender_pattern': r'.*@company\.com$',
        'attachment_pattern': '*.csv',
        'target_directory': '/app/data/source/inbox',
        'date_prefix_format': 'yyyyMMdd',
        'save_eml': False,
        'mark_processed': True,
        'processed_label': 'TestProcessed',
        'error_label': 'TestError',
        'linked_import_config_id': None,
        'is_active': True
    }


@pytest.fixture
def created_inbox_config(db_transaction, sample_inbox_config):
    """Create an inbox config and return it"""
    config_id = create_inbox_config(sample_inbox_config)
    return get_inbox_config(config_id)


@pytest.fixture
def created_inbox_configs(db_transaction):
    """Create multiple inbox configs for list testing"""
    configs = []
    for i in range(3):
        config_data = {
            'config_name': f'AdminTest_Inbox_{uuid.uuid4().hex[:8]}',
            'attachment_pattern': f'*.{"csv" if i % 2 == 0 else "xlsx"}',
            'target_directory': '/app/data/source/inbox',
            'is_active': i % 2 == 0
        }
        config_id = create_inbox_config(config_data)
        configs.append(get_inbox_config(config_id))
    return configs


# ============================================================================
# CRUD OPERATIONS
# ============================================================================

@pytest.mark.integration
@pytest.mark.crud
class TestInboxConfigCRUD:
    """Test basic CRUD operations for inbox configs"""

    def test_create_inbox_config_success(self, db_transaction, sample_inbox_config):
        """Creating valid config returns config_id"""
        config_id = create_inbox_config(sample_inbox_config)
        assert isinstance(config_id, int)
        assert config_id > 0

    def test_get_inbox_config_exists(self, db_transaction, created_inbox_config):
        """Retrieving existing config returns all fields"""
        config = get_inbox_config(created_inbox_config['inbox_config_id'])
        assert config is not None
        assert config['config_name'] == created_inbox_config['config_name']
        assert config['attachment_pattern'] == created_inbox_config['attachment_pattern']

    def test_get_inbox_config_not_found(self, db_transaction):
        """Retrieving non-existent config returns None"""
        config = get_inbox_config(999999)
        assert config is None

    def test_update_inbox_config_single_field(self, db_transaction, created_inbox_config):
        """Updating single field works correctly"""
        original_name = created_inbox_config['config_name']
        update_inbox_config(created_inbox_config['inbox_config_id'], {'is_active': False})

        updated = get_inbox_config(created_inbox_config['inbox_config_id'])
        assert updated['is_active'] is False
        assert updated['config_name'] == original_name

    def test_update_inbox_config_multiple_fields(self, db_transaction, created_inbox_config):
        """Updating multiple fields works correctly"""
        updates = {
            'attachment_pattern': '*.xlsx',
            'subject_pattern': r'.*Invoice.*',
            'is_active': False
        }
        update_inbox_config(created_inbox_config['inbox_config_id'], updates)

        updated = get_inbox_config(created_inbox_config['inbox_config_id'])
        assert updated['attachment_pattern'] == updates['attachment_pattern']
        assert updated['subject_pattern'] == updates['subject_pattern']
        assert updated['is_active'] == updates['is_active']

    def test_delete_inbox_config_success(self, db_transaction, created_inbox_config):
        """Deleting config removes it from database"""
        config_id = created_inbox_config['inbox_config_id']
        delete_inbox_config(config_id)

        config = get_inbox_config(config_id)
        assert config is None

    def test_delete_inbox_config_not_found(self, db_transaction):
        """Deleting non-existent config raises exception"""
        with pytest.raises(Exception) as exc_info:
            delete_inbox_config(999999)
        assert 'not found' in str(exc_info.value).lower()

    def test_toggle_active_enable(self, db_transaction, created_inbox_config):
        """Toggling active status to True works"""
        config_id = created_inbox_config['inbox_config_id']
        toggle_active(config_id, False)
        toggle_active(config_id, True)

        updated = get_inbox_config(config_id)
        assert updated['is_active'] is True

    def test_toggle_active_disable(self, db_transaction, created_inbox_config):
        """Toggling active status to False works"""
        config_id = created_inbox_config['inbox_config_id']
        toggle_active(config_id, False)

        updated = get_inbox_config(config_id)
        assert updated['is_active'] is False


# ============================================================================
# LIST AND FILTER OPERATIONS
# ============================================================================

@pytest.mark.integration
class TestInboxConfigList:
    """Test list and filter operations"""

    def test_list_inbox_configs_all(self, db_transaction, created_inbox_configs):
        """list_inbox_configs returns all configs"""
        configs = list_inbox_configs()
        test_configs = [c for c in configs if c['config_name'].startswith('AdminTest_')]
        assert len(test_configs) >= len(created_inbox_configs)

    def test_list_inbox_configs_active_only(self, db_transaction, created_inbox_configs):
        """active_only=True returns only active configs"""
        configs = list_inbox_configs(active_only=True)
        test_configs = [c for c in configs if c['config_name'].startswith('AdminTest_')]
        assert all(c['is_active'] is True for c in test_configs)

    def test_config_name_exists_true(self, db_transaction, created_inbox_config):
        """config_name_exists returns True for existing name"""
        exists = config_name_exists(created_inbox_config['config_name'])
        assert exists is True

    def test_config_name_exists_false(self, db_transaction):
        """config_name_exists returns False for non-existent name"""
        exists = config_name_exists('NonExistentConfig_12345')
        assert exists is False

    def test_config_name_exists_exclude_self(self, db_transaction, created_inbox_config):
        """config_name_exists excludes specified config_id"""
        exists = config_name_exists(
            created_inbox_config['config_name'],
            exclude_id=created_inbox_config['inbox_config_id']
        )
        assert exists is False


# ============================================================================
# STATISTICS
# ============================================================================

@pytest.mark.integration
class TestInboxConfigStats:
    """Test statistics functions"""

    def test_get_inbox_stats_structure(self, db_transaction, created_inbox_configs):
        """get_inbox_stats returns correct structure"""
        stats = get_inbox_stats()

        assert 'total' in stats
        assert 'active' in stats
        assert 'inactive' in stats

        assert isinstance(stats['total'], int)
        assert isinstance(stats['active'], int)
        assert isinstance(stats['inactive'], int)

    def test_get_inbox_stats_values(self, db_transaction, created_inbox_configs):
        """get_inbox_stats returns accurate counts"""
        stats = get_inbox_stats()

        assert stats['total'] >= len(created_inbox_configs)
        assert stats['total'] == stats['active'] + stats['inactive']


# ============================================================================
# PATTERN TESTING - PHASE 1 FEATURE
# ============================================================================

@pytest.mark.integration
class TestPatternTesting:
    """Test pattern testing functions added in Phase 1"""

    def test_validate_subject_pattern_matches(self):
        """validate_subject_pattern correctly identifies matches"""
        pattern = r'.*Daily Report.*'
        subjects = [
            'Daily Report Q1 2026',
            'Weekly Summary',
            'Daily Report Q2 2026',
            'Invoice 123'
        ]

        results = validate_subject_pattern(pattern, subjects)

        assert len(results) == 4
        assert results[0]['matches'] is True  # Daily Report Q1
        assert results[1]['matches'] is False  # Weekly Summary
        assert results[2]['matches'] is True  # Daily Report Q2
        assert results[3]['matches'] is False  # Invoice 123

    def test_validate_subject_pattern_with_groups(self):
        """validate_subject_pattern captures regex groups"""
        pattern = r'Report-(\d{4})-(\w+)'
        subjects = ['Report-2026-Q1', 'Report-2025-Annual']

        results = validate_subject_pattern(pattern, subjects)

        assert results[0]['groups'] == ['2026', 'Q1']
        assert results[1]['groups'] == ['2025', 'Annual']

    def test_validate_subject_pattern_invalid_regex(self):
        """validate_subject_pattern handles invalid regex"""
        pattern = r'[unclosed'
        subjects = ['test']

        results = validate_subject_pattern(pattern, subjects)

        assert results[0]['is_valid'] is False
        assert results[0]['error'] is not None

    def test_validate_sender_pattern_matches(self):
        """validate_sender_pattern correctly identifies matches"""
        pattern = r'.*@company\.com$'
        senders = [
            'reports@company.com',
            'john@external.org',
            'alerts@company.com',
            'spam@unknown.net'
        ]

        results = validate_sender_pattern(pattern, senders)

        assert len(results) == 4
        assert results[0]['matches'] is True  # reports@company.com
        assert results[1]['matches'] is False  # john@external.org
        assert results[2]['matches'] is True  # alerts@company.com
        assert results[3]['matches'] is False  # spam@unknown.net

    def test_validate_sender_pattern_email_validation(self):
        """validate_sender_pattern works with email patterns"""
        pattern = r'(reports|alerts)@.*'
        senders = ['reports@example.com', 'alerts@test.com', 'user@example.com']

        results = validate_sender_pattern(pattern, senders)

        assert results[0]['matches'] is True
        assert results[1]['matches'] is True
        assert results[2]['matches'] is False

    def test_validate_attachment_pattern_glob(self):
        """validate_attachment_pattern uses glob matching"""
        pattern = '*.csv'
        filenames = [
            'report_2026.csv',
            'data.xlsx',
            'daily.csv',
            'image.png'
        ]

        results = validate_attachment_pattern(pattern, filenames)

        assert len(results) == 4
        assert results[0]['matches'] is True  # report_2026.csv
        assert results[1]['matches'] is False  # data.xlsx
        assert results[2]['matches'] is True  # daily.csv
        assert results[3]['matches'] is False  # image.png

    def test_validate_attachment_pattern_prefix(self):
        """validate_attachment_pattern works with prefix patterns"""
        pattern = 'report_*.xlsx'
        filenames = ['report_q1.xlsx', 'data_q1.xlsx', 'report_annual.xlsx']

        results = validate_attachment_pattern(pattern, filenames)

        assert results[0]['matches'] is True
        assert results[1]['matches'] is False
        assert results[2]['matches'] is True

    def test_validate_attachment_pattern_character_class(self):
        """validate_attachment_pattern works with character classes"""
        pattern = '*_202[0-9].csv'
        filenames = ['report_2026.csv', 'report_2019.csv', 'report_2025.csv']

        results = validate_attachment_pattern(pattern, filenames)

        assert results[0]['matches'] is True  # 2026
        assert results[1]['matches'] is False  # 2019
        assert results[2]['matches'] is True  # 2025


# ============================================================================
# PATTERN TEST SUMMARY
# ============================================================================

@pytest.mark.integration
class TestPatternTestSummary:
    """Test get_pattern_test_summary function"""

    def test_summary_all_match(self):
        """Summary with all matching results"""
        results = [
            {'matches': True, 'is_valid': True, 'error': None},
            {'matches': True, 'is_valid': True, 'error': None},
            {'matches': True, 'is_valid': True, 'error': None}
        ]

        summary = get_pattern_test_summary(results)

        assert summary['total'] == 3
        assert summary['matches'] == 3
        assert summary['non_matches'] == 0
        assert summary['match_rate'] == 100.0
        assert summary['has_error'] is False
        assert summary['pattern_valid'] is True

    def test_summary_partial_match(self):
        """Summary with partial matching results"""
        results = [
            {'matches': True, 'is_valid': True, 'error': None},
            {'matches': False, 'is_valid': True, 'error': None},
            {'matches': True, 'is_valid': True, 'error': None},
            {'matches': False, 'is_valid': True, 'error': None}
        ]

        summary = get_pattern_test_summary(results)

        assert summary['total'] == 4
        assert summary['matches'] == 2
        assert summary['non_matches'] == 2
        assert summary['match_rate'] == 50.0
        assert summary['has_error'] is False

    def test_summary_with_error(self):
        """Summary with error in results"""
        results = [
            {'matches': False, 'is_valid': False, 'error': 'Invalid regex'},
            {'matches': False, 'is_valid': False, 'error': 'Invalid regex'}
        ]

        summary = get_pattern_test_summary(results)

        assert summary['has_error'] is True
        assert summary['pattern_valid'] is False

    def test_summary_empty_results(self):
        """Summary with empty results list"""
        summary = get_pattern_test_summary([])

        assert summary['total'] == 0
        assert summary['matches'] == 0
        assert summary['match_rate'] == 0
        assert summary['pattern_valid'] is False

    def test_summary_no_matches(self):
        """Summary with no matches"""
        results = [
            {'matches': False, 'is_valid': True, 'error': None},
            {'matches': False, 'is_valid': True, 'error': None}
        ]

        summary = get_pattern_test_summary(results)

        assert summary['matches'] == 0
        assert summary['match_rate'] == 0.0
        assert summary['pattern_valid'] is True

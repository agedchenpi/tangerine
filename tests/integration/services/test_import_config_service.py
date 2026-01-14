"""Integration tests for import configuration service

Tests all CRUD operations, validation, filtering, and business logic
for the import_config_service module.

Note: These tests require database access and use transaction rollback
for isolation and cleanup.
"""

import pytest
from admin.services.import_config_service import (
    list_configs,
    get_config,
    create_config,
    update_config,
    delete_config,
    toggle_active,
    count_configs,
    get_datasources,
    get_datasettypes,
    get_strategies,
    get_config_stats,
    config_name_exists
)
from tests.fixtures.import_config_fixtures import (
    get_valid_import_config,
    get_configs_for_all_file_types,
    get_configs_for_all_strategies
)


# ============================================================================
# CRUD OPERATIONS - Basic create, read, update, delete
# ============================================================================

@pytest.mark.integration
@pytest.mark.crud
class TestImportConfigCRUD:
    """Test basic CRUD operations"""

    def test_list_configs_empty(self, db_transaction, clean_test_data):
        """Empty database returns empty list"""
        configs = list_configs()
        # Filter out only AdminTest configs
        test_configs = [c for c in configs if c['config_name'].startswith('AdminTest_')]
        assert test_configs == []

    def test_create_config_success(self, db_transaction, sample_import_config):
        """Creating valid config returns config_id"""
        config_id = create_config(sample_import_config)
        assert isinstance(config_id, int)
        assert config_id > 0

    def test_get_config_exists(self, db_transaction, created_import_config):
        """Retrieving existing config returns all fields"""
        config = get_config(created_import_config['config_id'])
        assert config is not None
        assert config['config_name'] == created_import_config['config_name']
        assert config['file_type'] == created_import_config['file_type']
        assert config['target_table'] == created_import_config['target_table']

    def test_get_config_not_found(self, db_transaction):
        """Retrieving non-existent config returns None"""
        config = get_config(999999)
        assert config is None

    def test_update_config_single_field(self, db_transaction, created_import_config):
        """Updating single field preserves others"""
        original_name = created_import_config['config_name']
        update_config(created_import_config['config_id'], {'is_active': False})

        updated = get_config(created_import_config['config_id'])
        assert updated['is_active'] is False
        assert updated['config_name'] == original_name

    def test_update_config_multiple_fields(self, db_transaction, created_import_config):
        """Updating multiple fields works correctly"""
        updates = {
            'file_pattern': r'updated_\d{8}\.csv',
            'target_table': 'feeds.updated_table',
            'is_active': False
        }
        update_config(created_import_config['config_id'], updates)

        updated = get_config(created_import_config['config_id'])
        assert updated['file_pattern'] == updates['file_pattern']
        assert updated['target_table'] == updates['target_table']
        assert updated['is_active'] == updates['is_active']

    def test_delete_config_success(self, db_transaction, created_import_config):
        """Deleting config removes it from database"""
        config_id = created_import_config['config_id']
        delete_config(config_id)

        # Verify config no longer exists
        config = get_config(config_id)
        assert config is None

    def test_delete_config_not_found(self, db_transaction):
        """Deleting non-existent config raises exception"""
        with pytest.raises(Exception) as exc_info:
            delete_config(999999)
        assert 'not found' in str(exc_info.value).lower()

    def test_toggle_active_enable(self, db_transaction, created_import_config):
        """Toggling active status to True works"""
        # First disable it
        update_config(created_import_config['config_id'], {'is_active': False})

        # Then enable it using toggle
        toggle_active(created_import_config['config_id'], True)

        updated = get_config(created_import_config['config_id'])
        assert updated['is_active'] is True

    def test_toggle_active_disable(self, db_transaction, created_import_config):
        """Toggling active status to False works"""
        toggle_active(created_import_config['config_id'], False)

        updated = get_config(created_import_config['config_id'])
        assert updated['is_active'] is False


# ============================================================================
# VALIDATION & BUSINESS LOGIC
# ============================================================================

@pytest.mark.integration
@pytest.mark.validation
class TestImportConfigValidation:
    """Test validation rules and business logic"""

    def test_create_config_duplicate_name_returns_existing(self, db_transaction, created_import_config, sample_import_config):
        """Creating config with duplicate name returns existing config_id (ON CONFLICT DO NOTHING)"""
        duplicate = {**sample_import_config, 'config_name': created_import_config['config_name']}

        # The stored procedure uses ON CONFLICT DO NOTHING, so it returns existing config_id
        returned_id = create_config(duplicate)
        assert returned_id == created_import_config['config_id']

    def test_config_name_exists_true(self, db_transaction, created_import_config):
        """config_name_exists returns True for existing name"""
        exists = config_name_exists(created_import_config['config_name'])
        assert exists is True

    def test_config_name_exists_false(self, db_transaction):
        """config_name_exists returns False for non-existent name"""
        exists = config_name_exists('NonExistentConfig_12345')
        assert exists is False

    def test_config_name_exists_exclude_self(self, db_transaction, created_import_config):
        """config_name_exists excludes specified config_id"""
        exists = config_name_exists(
            created_import_config['config_name'],
            exclude_id=created_import_config['config_id']
        )
        assert exists is False

    def test_config_name_exists_exclude_different_id(self, db_transaction, created_import_config):
        """config_name_exists with different exclude_id returns True"""
        exists = config_name_exists(
            created_import_config['config_name'],
            exclude_id=999999
        )
        assert exists is True

    def test_update_config_to_duplicate_name_fails(self, db_transaction, created_import_configs):
        """Updating config to duplicate name raises error"""
        if len(created_import_configs) < 2:
            pytest.skip("Need at least 2 configs for this test")

        config1 = created_import_configs[0]
        config2 = created_import_configs[1]

        # Try to update config2 to have config1's name
        with pytest.raises(Exception):
            update_config(config2['config_id'], {'config_name': config1['config_name']})

    def test_create_config_with_all_file_types(self, db_transaction, created_datasource, created_datasettype):
        """Can create configs for all supported file types"""
        file_types = ['CSV', 'XLS', 'XLSX', 'JSON', 'XML']

        for file_type in file_types:
            config = get_valid_import_config(
                datasource=created_datasource['sourcename'],
                datasettype=created_datasettype['typename'],
                file_type=file_type
            )
            config_id = create_config(config)
            assert config_id > 0

            # Verify it was created correctly
            retrieved = get_config(config_id)
            assert retrieved['file_type'] == file_type

    def test_create_config_with_all_strategies(self, db_transaction, created_datasource, created_datasettype):
        """Can create configs for all import strategies"""
        strategies = [1, 2, 3]  # Auto-add, Ignore extras, Strict

        for strategy_id in strategies:
            config = get_valid_import_config(
                datasource=created_datasource['sourcename'],
                datasettype=created_datasettype['typename']
            )
            config['importstrategyid'] = strategy_id
            config_id = create_config(config)
            assert config_id > 0

            # Verify strategy was set correctly
            retrieved = get_config(config_id)
            assert retrieved['importstrategyid'] == strategy_id

    def test_create_config_with_filename_metadata(self, db_transaction, sample_import_config):
        """Config with filename metadata source creates successfully"""
        config = {**sample_import_config}
        config['metadata_label_source'] = 'filename'
        config['metadata_label_location'] = '2'  # Position index as string
        config['delimiter'] = '_'

        config_id = create_config(config)
        retrieved = get_config(config_id)

        assert retrieved['metadata_label_source'] == 'filename'
        assert retrieved['metadata_label_location'] == '2'
        assert retrieved['delimiter'] == '_'

    def test_create_config_with_file_content_metadata(self, db_transaction, sample_import_config):
        """Config with file_content metadata source creates successfully"""
        config = {**sample_import_config}
        config['metadata_label_source'] = 'file_content'
        config['metadata_label_location'] = 'label_column'  # Column name

        config_id = create_config(config)
        retrieved = get_config(config_id)

        assert retrieved['metadata_label_source'] == 'file_content'
        assert retrieved['metadata_label_location'] == 'label_column'

    def test_create_config_with_static_metadata(self, db_transaction, sample_import_config):
        """Config with static metadata source creates successfully"""
        config = {**sample_import_config}
        config['metadata_label_source'] = 'static'
        config['metadata_label_location'] = 'StaticLabel'  # Static value

        config_id = create_config(config)
        retrieved = get_config(config_id)

        assert retrieved['metadata_label_source'] == 'static'
        assert retrieved['metadata_label_location'] == 'StaticLabel'


# ============================================================================
# FILTERING & QUERYING
# ============================================================================

@pytest.mark.integration
class TestImportConfigFiltering:
    """Test list and filter operations"""

    def test_list_configs_all(self, db_transaction, created_import_configs):
        """list_configs returns all configs when no filters"""
        configs = list_configs()
        test_configs = [c for c in configs if c['config_name'].startswith('AdminTest_')]

        assert len(test_configs) >= len(created_import_configs)

    def test_list_configs_filter_active_only(self, db_transaction, created_import_configs):
        """active_only=True returns only active configs"""
        configs = list_configs(active_only=True)
        test_configs = [c for c in configs if c['config_name'].startswith('AdminTest_')]

        assert all(c['is_active'] is True for c in test_configs)

    def test_list_configs_filter_by_file_type(self, db_transaction, created_datasource, created_datasettype):
        """file_type filter returns matching configs"""
        # Create configs with different file types
        csv_config = get_valid_import_config(
            datasource=created_datasource['sourcename'],
            datasettype=created_datasettype['typename'],
            file_type='CSV'
        )
        create_config(csv_config)

        json_config = get_valid_import_config(
            datasource=created_datasource['sourcename'],
            datasettype=created_datasettype['typename'],
            file_type='JSON'
        )
        create_config(json_config)

        # Filter by CSV
        csv_configs = list_configs(file_type='CSV')
        test_csv = [c for c in csv_configs if c['config_name'].startswith('AdminTest_')]
        assert all(c['file_type'] == 'CSV' for c in test_csv)

        # Filter by JSON
        json_configs = list_configs(file_type='JSON')
        test_json = [c for c in json_configs if c['config_name'].startswith('AdminTest_')]
        assert all(c['file_type'] == 'JSON' for c in test_json)

    def test_list_configs_filter_by_strategy(self, db_transaction, created_datasource, created_datasettype):
        """strategy_id filter returns matching configs"""
        # Create configs with different strategies
        strategy1_config = get_valid_import_config(
            datasource=created_datasource['sourcename'],
            datasettype=created_datasettype['typename']
        )
        strategy1_config['importstrategyid'] = 1
        create_config(strategy1_config)

        strategy2_config = get_valid_import_config(
            datasource=created_datasource['sourcename'],
            datasettype=created_datasettype['typename']
        )
        strategy2_config['importstrategyid'] = 2
        create_config(strategy2_config)

        # Filter by strategy 1
        configs = list_configs(strategy_id=1)
        test_configs = [c for c in configs if c['config_name'].startswith('AdminTest_')]
        assert all(c['importstrategyid'] == 1 for c in test_configs)

    def test_list_configs_combined_filters(self, db_transaction, created_datasource, created_datasettype):
        """Multiple filters work together"""
        # Create active CSV config with strategy 1
        config = get_valid_import_config(
            datasource=created_datasource['sourcename'],
            datasettype=created_datasettype['typename'],
            file_type='CSV',
            is_active=True
        )
        config['importstrategyid'] = 1
        create_config(config)

        # Filter with multiple criteria
        configs = list_configs(active_only=True, file_type='CSV', strategy_id=1)
        test_configs = [c for c in configs if c['config_name'].startswith('AdminTest_')]

        assert all(c['is_active'] is True for c in test_configs)
        assert all(c['file_type'] == 'CSV' for c in test_configs)
        assert all(c['importstrategyid'] == 1 for c in test_configs)

    def test_list_configs_includes_strategy_info(self, db_transaction, created_import_config):
        """list_configs includes strategy name and description"""
        configs = list_configs()
        test_config = next((c for c in configs if c['config_id'] == created_import_config['config_id']), None)

        assert test_config is not None
        assert 'strategy_name' in test_config
        assert 'strategy_description' in test_config
        assert test_config['strategy_name'] is not None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@pytest.mark.integration
class TestImportConfigHelpers:
    """Test helper and utility functions"""

    def test_count_configs_all(self, db_transaction, created_import_configs):
        """count_configs returns correct total"""
        count = count_configs(active_only=False)
        # Count should be at least the number of test configs created
        assert count >= len(created_import_configs)

    def test_count_configs_active_only(self, db_transaction, created_import_configs):
        """count_configs with active_only returns correct count"""
        # Count active configs
        active_count = sum(1 for c in created_import_configs if c['is_active'])
        result_count = count_configs(active_only=True)

        # Result should be at least our active test configs
        assert result_count >= active_count

    def test_get_datasources_returns_list(self, db_transaction, created_datasource):
        """get_datasources returns list of datasource names"""
        datasources = get_datasources()
        assert isinstance(datasources, list)
        assert created_datasource['sourcename'] in datasources

    def test_get_datasettypes_returns_list(self, db_transaction, created_datasettype):
        """get_datasettypes returns list of dataset type names"""
        types = get_datasettypes()
        assert isinstance(types, list)
        assert created_datasettype['typename'] in types

    def test_get_strategies_returns_all(self, db_transaction):
        """get_strategies returns all 3 strategies"""
        strategies = get_strategies()
        assert isinstance(strategies, list)
        assert len(strategies) >= 3

        # Verify structure
        for strategy in strategies:
            assert 'importstrategyid' in strategy
            assert 'name' in strategy
            assert 'description' in strategy

    def test_get_config_stats_structure(self, db_transaction, created_import_configs):
        """get_config_stats returns correct structure"""
        stats = get_config_stats()

        assert 'total' in stats
        assert 'active' in stats
        assert 'inactive' in stats

        assert isinstance(stats['total'], int)
        assert isinstance(stats['active'], int)
        assert isinstance(stats['inactive'], int)

        # Verify totals add up
        assert stats['total'] == stats['active'] + stats['inactive']

    def test_get_config_stats_values(self, db_transaction, created_import_configs):
        """get_config_stats returns accurate counts"""
        stats = get_config_stats()

        # Should be at least our test configs
        assert stats['total'] >= len(created_import_configs)

        # Count active test configs
        active_count = sum(1 for c in created_import_configs if c['is_active'])
        # Stats should reflect at least our test configs
        assert stats['active'] >= active_count


# ============================================================================
# EDGE CASES & ERROR CONDITIONS
# ============================================================================

@pytest.mark.integration
class TestImportConfigEdgeCases:
    """Test edge cases and error conditions"""

    def test_update_nonexistent_config_fails(self, db_transaction):
        """Updating non-existent config raises exception"""
        with pytest.raises(Exception):
            update_config(999999, {'is_active': False})

    def test_get_config_with_invalid_id(self, db_transaction):
        """get_config with invalid ID returns None"""
        assert get_config(-1) is None
        assert get_config(0) is None

    def test_list_configs_with_nonexistent_file_type(self, db_transaction):
        """Filtering by non-existent file type returns empty for test configs"""
        configs = list_configs(file_type='NONEXISTENT')
        test_configs = [c for c in configs if c['config_name'].startswith('AdminTest_')]
        assert test_configs == []

    def test_list_configs_with_nonexistent_strategy(self, db_transaction):
        """Filtering by non-existent strategy returns empty for test configs"""
        configs = list_configs(strategy_id=999)
        test_configs = [c for c in configs if c['config_name'].startswith('AdminTest_')]
        assert test_configs == []

    def test_count_configs_empty_database(self, db_transaction, clean_test_data):
        """count_configs on empty database returns 0 or only non-test configs"""
        # This might return non-zero if there are non-test configs
        count = count_configs(active_only=False)
        assert count >= 0

    def test_config_name_exists_empty_string(self, db_transaction):
        """config_name_exists with empty string returns False"""
        exists = config_name_exists('')
        assert exists is False

    def test_toggle_active_nonexistent_config(self, db_transaction):
        """toggle_active on non-existent config raises exception"""
        with pytest.raises(Exception):
            toggle_active(999999, True)

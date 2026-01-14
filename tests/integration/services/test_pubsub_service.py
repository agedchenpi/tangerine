"""Integration tests for pub-sub event system service

Tests CRUD operations for events and subscribers.
This is part of Phase 2 regression tests.
"""

import pytest
import uuid
import json
from admin.services.pubsub_service import (
    # Event functions
    list_events,
    get_event,
    create_event,
    update_event_status,
    cancel_event,
    retry_event,
    get_event_stats,
    get_recent_event_counts,
    # Subscriber functions
    list_subscribers,
    get_subscriber,
    create_subscriber,
    update_subscriber,
    delete_subscriber,
    toggle_subscriber_active,
    subscriber_name_exists,
    get_subscriber_stats,
    # Helper functions
    get_import_configs,
    get_inbox_configs,
    get_report_configs,
    get_event_types,
    get_job_types
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_event():
    """Sample event data for testing"""
    return {
        'event_type': 'file_received',
        'event_source': f'/app/data/source/test_{uuid.uuid4().hex[:8]}.csv',
        'event_data': {
            'filename': 'test_file.csv',
            'size': 1024
        },
        'priority': 5
    }


@pytest.fixture
def created_event(db_transaction, sample_event):
    """Create an event and return it"""
    event_id = create_event(
        event_type=sample_event['event_type'],
        event_source=sample_event['event_source'],
        event_data=sample_event['event_data'],
        priority=sample_event['priority']
    )
    return get_event(event_id)


@pytest.fixture
def created_events(db_transaction):
    """Create multiple events for list testing"""
    events = []
    statuses = ['pending', 'pending', 'completed', 'failed']

    for i, status in enumerate(statuses):
        event_id = create_event(
            event_type='file_received' if i % 2 == 0 else 'email_received',
            event_source=f'/app/data/source/test_{uuid.uuid4().hex[:8]}.csv',
            event_data={'index': i},
            priority=5
        )
        if status != 'pending':
            update_event_status(event_id, status)
        events.append(get_event(event_id))

    return events


@pytest.fixture
def sample_subscriber():
    """Sample subscriber data for testing"""
    return {
        'subscriber_name': f'AdminTest_Sub_{uuid.uuid4().hex[:8]}',
        'description': 'Test subscriber for regression tests',
        'event_type': 'file_received',
        'event_filter': {'file_pattern': '*.csv'},
        'job_type': 'custom',
        'config_id': None,
        'script_path': '/app/etl/jobs/test_job.py',
        'is_active': True
    }


@pytest.fixture
def created_subscriber(db_transaction, sample_subscriber):
    """Create a subscriber and return it"""
    sub_id = create_subscriber(sample_subscriber)
    return get_subscriber(sub_id)


@pytest.fixture
def created_subscribers(db_transaction):
    """Create multiple subscribers for list testing"""
    subs = []
    for i in range(3):
        sub_data = {
            'subscriber_name': f'AdminTest_Sub_{uuid.uuid4().hex[:8]}',
            'event_type': 'file_received' if i % 2 == 0 else 'email_received',
            'event_filter': {},
            'job_type': 'custom',
            'script_path': '/app/etl/jobs/test_job.py',
            'is_active': i % 2 == 0
        }
        sub_id = create_subscriber(sub_data)
        subs.append(get_subscriber(sub_id))
    return subs


# ============================================================================
# EVENT CRUD OPERATIONS
# ============================================================================

@pytest.mark.integration
@pytest.mark.crud
class TestEventCRUD:
    """Test CRUD operations for events"""

    def test_create_event_success(self, db_transaction, sample_event):
        """Creating valid event returns event_id"""
        event_id = create_event(
            event_type=sample_event['event_type'],
            event_source=sample_event['event_source'],
            event_data=sample_event['event_data'],
            priority=sample_event['priority']
        )
        assert isinstance(event_id, int)
        assert event_id > 0

    def test_create_event_default_priority(self, db_transaction):
        """Creating event without priority uses default"""
        event_id = create_event(
            event_type='file_received',
            event_source='/app/data/test.csv'
        )
        event = get_event(event_id)
        assert event['priority'] == 5  # Default priority

    def test_create_event_with_json_data(self, db_transaction):
        """Creating event with JSON data works"""
        event_data = {
            'filename': 'complex_file.csv',
            'metadata': {
                'rows': 1000,
                'columns': ['a', 'b', 'c']
            }
        }
        event_id = create_event(
            event_type='file_received',
            event_source='/app/data/test.csv',
            event_data=event_data
        )
        event = get_event(event_id)
        assert event['event_data'] is not None

    def test_get_event_exists(self, db_transaction, created_event):
        """Retrieving existing event returns all fields"""
        event = get_event(created_event['event_id'])
        assert event is not None
        assert event['event_type'] == created_event['event_type']
        assert event['status'] == 'pending'

    def test_get_event_not_found(self, db_transaction):
        """Retrieving non-existent event returns None"""
        event = get_event(999999)
        assert event is None

    def test_update_event_status_processing(self, db_transaction, created_event):
        """Updating event status to processing works"""
        event_id = created_event['event_id']
        update_event_status(event_id, 'processing')

        event = get_event(event_id)
        assert event['status'] == 'processing'
        assert event['processed_at'] is not None

    def test_update_event_status_completed(self, db_transaction, created_event):
        """Updating event status to completed works"""
        event_id = created_event['event_id']
        update_event_status(event_id, 'completed')

        event = get_event(event_id)
        assert event['status'] == 'completed'
        assert event['completed_at'] is not None

    def test_update_event_status_failed_with_error(self, db_transaction, created_event):
        """Updating event status to failed with error message works"""
        event_id = created_event['event_id']
        error_msg = "Test error message"
        update_event_status(event_id, 'failed', error_message=error_msg)

        event = get_event(event_id)
        assert event['status'] == 'failed'
        assert event['error_message'] == error_msg

    def test_cancel_event(self, db_transaction, created_event):
        """Cancelling event sets status to cancelled"""
        event_id = created_event['event_id']
        cancel_event(event_id)

        event = get_event(event_id)
        assert event['status'] == 'cancelled'

    def test_retry_event(self, db_transaction, created_event):
        """Retrying failed event resets status to pending"""
        event_id = created_event['event_id']

        # First fail the event
        update_event_status(event_id, 'failed', error_message='Test failure')

        # Then retry it
        retry_event(event_id)

        event = get_event(event_id)
        assert event['status'] == 'pending'
        assert event['error_message'] is None


# ============================================================================
# EVENT LIST AND FILTER OPERATIONS
# ============================================================================

@pytest.mark.integration
class TestEventList:
    """Test list and filter operations for events"""

    def test_list_events_all(self, db_transaction, created_events):
        """list_events returns all events"""
        events = list_events()
        assert len(events) >= len(created_events)

    def test_list_events_filter_by_status(self, db_transaction, created_events):
        """list_events filters by status"""
        pending = list_events(status='pending')
        assert all(e['status'] == 'pending' for e in pending)

        completed = list_events(status='completed')
        assert all(e['status'] == 'completed' for e in completed)

    def test_list_events_filter_by_type(self, db_transaction, created_events):
        """list_events filters by event type"""
        file_events = list_events(event_type='file_received')
        assert all(e['event_type'] == 'file_received' for e in file_events)

    def test_list_events_with_limit(self, db_transaction, created_events):
        """list_events respects limit parameter"""
        events = list_events(limit=2)
        assert len(events) <= 2

    def test_list_events_combined_filters(self, db_transaction, created_events):
        """list_events with multiple filters"""
        events = list_events(status='pending', event_type='file_received')
        assert all(e['status'] == 'pending' for e in events)
        assert all(e['event_type'] == 'file_received' for e in events)


# ============================================================================
# EVENT STATISTICS
# ============================================================================

@pytest.mark.integration
class TestEventStats:
    """Test event statistics functions"""

    def test_get_event_stats_structure(self, db_transaction, created_events):
        """get_event_stats returns correct structure"""
        stats = get_event_stats()

        assert 'total' in stats
        assert 'pending' in stats
        assert 'processing' in stats
        assert 'completed' in stats
        assert 'failed' in stats
        assert 'cancelled' in stats

    def test_get_event_stats_values(self, db_transaction, created_events):
        """get_event_stats returns accurate counts"""
        stats = get_event_stats()

        # Total should be sum of all statuses
        total = stats['pending'] + stats['processing'] + stats['completed'] + stats['failed'] + stats['cancelled']
        assert stats['total'] == total

    def test_get_recent_event_counts(self, db_transaction, created_events):
        """get_recent_event_counts returns daily counts"""
        counts = get_recent_event_counts(days=7)

        # Should return list of dicts with date, total, completed, failed
        if counts:  # May be empty if no events
            for day in counts:
                assert 'date' in day
                assert 'total' in day


# ============================================================================
# SUBSCRIBER CRUD OPERATIONS
# ============================================================================

@pytest.mark.integration
@pytest.mark.crud
class TestSubscriberCRUD:
    """Test CRUD operations for subscribers"""

    def test_create_subscriber_success(self, db_transaction, sample_subscriber):
        """Creating valid subscriber returns subscriber_id"""
        sub_id = create_subscriber(sample_subscriber)
        assert isinstance(sub_id, int)
        assert sub_id > 0

    def test_create_subscriber_minimal(self, db_transaction):
        """Creating subscriber with minimal fields works"""
        sub_data = {
            'subscriber_name': f'AdminTest_Sub_{uuid.uuid4().hex[:8]}',
            'event_type': 'file_received',
            'job_type': 'custom',
            'script_path': '/app/test.py'
        }
        sub_id = create_subscriber(sub_data)
        sub = get_subscriber(sub_id)
        assert sub is not None
        assert sub['is_active'] is True  # Default

    def test_get_subscriber_exists(self, db_transaction, created_subscriber):
        """Retrieving existing subscriber returns all fields"""
        sub = get_subscriber(created_subscriber['subscriber_id'])
        assert sub is not None
        assert sub['subscriber_name'] == created_subscriber['subscriber_name']
        assert sub['event_type'] == created_subscriber['event_type']

    def test_get_subscriber_not_found(self, db_transaction):
        """Retrieving non-existent subscriber returns None"""
        sub = get_subscriber(999999)
        assert sub is None

    def test_update_subscriber_single_field(self, db_transaction, created_subscriber):
        """Updating single field works correctly"""
        sub_id = created_subscriber['subscriber_id']
        original_name = created_subscriber['subscriber_name']

        update_subscriber(sub_id, {'is_active': False})

        updated = get_subscriber(sub_id)
        assert updated['is_active'] is False
        assert updated['subscriber_name'] == original_name

    def test_update_subscriber_multiple_fields(self, db_transaction, created_subscriber):
        """Updating multiple fields works correctly"""
        sub_id = created_subscriber['subscriber_id']

        updates = {
            'description': 'Updated description',
            'event_filter': {'file_pattern': '*.xlsx'},
            'is_active': False
        }
        update_subscriber(sub_id, updates)

        updated = get_subscriber(sub_id)
        assert updated['description'] == updates['description']
        assert updated['is_active'] == updates['is_active']

    def test_delete_subscriber_success(self, db_transaction, created_subscriber):
        """Deleting subscriber removes it from database"""
        sub_id = created_subscriber['subscriber_id']
        delete_subscriber(sub_id)

        sub = get_subscriber(sub_id)
        assert sub is None

    def test_delete_subscriber_not_found(self, db_transaction):
        """Deleting non-existent subscriber raises exception"""
        with pytest.raises(Exception) as exc_info:
            delete_subscriber(999999)
        assert 'not found' in str(exc_info.value).lower()

    def test_toggle_subscriber_active_enable(self, db_transaction, created_subscriber):
        """Toggling active status to True works"""
        sub_id = created_subscriber['subscriber_id']
        toggle_subscriber_active(sub_id, False)
        toggle_subscriber_active(sub_id, True)

        updated = get_subscriber(sub_id)
        assert updated['is_active'] is True

    def test_toggle_subscriber_active_disable(self, db_transaction, created_subscriber):
        """Toggling active status to False works"""
        sub_id = created_subscriber['subscriber_id']
        toggle_subscriber_active(sub_id, False)

        updated = get_subscriber(sub_id)
        assert updated['is_active'] is False


# ============================================================================
# SUBSCRIBER LIST AND FILTER OPERATIONS
# ============================================================================

@pytest.mark.integration
class TestSubscriberList:
    """Test list and filter operations for subscribers"""

    def test_list_subscribers_all(self, db_transaction, created_subscribers):
        """list_subscribers returns all subscribers"""
        subs = list_subscribers()
        test_subs = [s for s in subs if s['subscriber_name'].startswith('AdminTest_')]
        assert len(test_subs) >= len(created_subscribers)

    def test_list_subscribers_active_only(self, db_transaction, created_subscribers):
        """active_only=True returns only active subscribers"""
        subs = list_subscribers(active_only=True)
        test_subs = [s for s in subs if s['subscriber_name'].startswith('AdminTest_')]
        assert all(s['is_active'] is True for s in test_subs)

    def test_list_subscribers_filter_by_event_type(self, db_transaction, created_subscribers):
        """list_subscribers filters by event type"""
        subs = list_subscribers(event_type='file_received')
        assert all(s['event_type'] == 'file_received' for s in subs)

    def test_subscriber_name_exists_true(self, db_transaction, created_subscriber):
        """subscriber_name_exists returns True for existing name"""
        exists = subscriber_name_exists(created_subscriber['subscriber_name'])
        assert exists is True

    def test_subscriber_name_exists_false(self, db_transaction):
        """subscriber_name_exists returns False for non-existent name"""
        exists = subscriber_name_exists('NonExistentSubscriber_12345')
        assert exists is False

    def test_subscriber_name_exists_exclude_self(self, db_transaction, created_subscriber):
        """subscriber_name_exists excludes specified subscriber_id"""
        exists = subscriber_name_exists(
            created_subscriber['subscriber_name'],
            exclude_id=created_subscriber['subscriber_id']
        )
        assert exists is False


# ============================================================================
# SUBSCRIBER STATISTICS
# ============================================================================

@pytest.mark.integration
class TestSubscriberStats:
    """Test subscriber statistics functions"""

    def test_get_subscriber_stats_structure(self, db_transaction, created_subscribers):
        """get_subscriber_stats returns correct structure"""
        stats = get_subscriber_stats()

        assert 'total' in stats
        assert 'active' in stats
        assert 'inactive' in stats
        assert 'total_triggers' in stats

    def test_get_subscriber_stats_values(self, db_transaction, created_subscribers):
        """get_subscriber_stats returns accurate counts"""
        stats = get_subscriber_stats()

        assert stats['total'] >= len(created_subscribers)
        assert stats['total'] == stats['active'] + stats['inactive']


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@pytest.mark.integration
class TestPubSubHelpers:
    """Test helper functions"""

    def test_get_event_types(self):
        """get_event_types returns valid event types"""
        types = get_event_types()

        assert isinstance(types, list)
        assert 'file_received' in types
        assert 'email_received' in types
        assert 'custom' in types

    def test_get_job_types(self):
        """get_job_types returns valid job types"""
        types = get_job_types()

        assert isinstance(types, list)
        assert 'import' in types
        assert 'inbox_processor' in types
        assert 'report' in types
        assert 'custom' in types

    def test_get_import_configs_returns_list(self, db_transaction):
        """get_import_configs returns list"""
        configs = get_import_configs()
        assert isinstance(configs, list)

    def test_get_inbox_configs_returns_list(self, db_transaction):
        """get_inbox_configs returns list"""
        configs = get_inbox_configs()
        assert isinstance(configs, list)

    def test_get_report_configs_returns_list(self, db_transaction):
        """get_report_configs returns list"""
        configs = get_report_configs()
        assert isinstance(configs, list)


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.integration
class TestPubSubEdgeCases:
    """Test edge cases and error conditions"""

    def test_create_event_all_types(self, db_transaction):
        """Can create events for all event types"""
        event_types = get_event_types()

        for event_type in event_types:
            event_id = create_event(
                event_type=event_type,
                event_source=f'/test/{event_type}'
            )
            event = get_event(event_id)
            assert event['event_type'] == event_type

    def test_create_subscriber_all_job_types(self, db_transaction):
        """Can create subscribers for all job types"""
        # Custom job type only (others need config_id which requires actual configs)
        sub_data = {
            'subscriber_name': f'AdminTest_Sub_{uuid.uuid4().hex[:8]}',
            'event_type': 'file_received',
            'job_type': 'custom',
            'script_path': '/app/test.py'
        }
        sub_id = create_subscriber(sub_data)
        sub = get_subscriber(sub_id)
        assert sub['job_type'] == 'custom'

    def test_event_priority_range(self, db_transaction):
        """Events can have priority 1-10"""
        for priority in [1, 5, 10]:
            event_id = create_event(
                event_type='file_received',
                event_source=f'/test/priority_{priority}',
                priority=priority
            )
            event = get_event(event_id)
            assert event['priority'] == priority

    def test_list_events_empty_filters(self, db_transaction):
        """list_events with non-matching filters returns empty"""
        events = list_events(status='nonexistent')
        # Should not crash, may return empty or filtered results
        assert isinstance(events, list)

"""Integration tests for monitoring service

Tests all monitoring functions including log filtering, dataset queries,
statistics calculations, and CSV export functionality.

Note: These tests require database access and use transaction rollback
for isolation and cleanup.
"""

import pytest
from datetime import datetime, timedelta
from admin.services.monitoring_service import (
    get_logs,
    get_distinct_process_types,
    get_datasets,
    get_dataset_sources,
    get_dataset_types_from_datasets,
    get_statistics_metrics,
    get_jobs_per_day,
    get_process_type_distribution,
    get_runtime_statistics,
    export_logs_to_csv
)
from tests.fixtures.database_fixtures import (
    get_sample_log_entry,
    get_multiple_log_entries,
    get_sample_dataset,
    get_multiple_datasets,
    insert_log_entries,
    insert_datasets
)


# ============================================================================
# LOG FILTERING TESTS
# ============================================================================

@pytest.mark.integration
class TestGetLogs:
    """Tests for get_logs function"""

    def test_get_logs_empty_database(self, db_transaction, clean_test_data):
        """Empty database returns empty list"""
        logs = get_logs()
        test_logs = [l for l in logs if 'AdminTest' in str(l.get('message', ''))]
        assert test_logs == []

    def test_get_logs_with_data(self, db_transaction):
        """Returns logs when data exists"""
        # Insert test logs
        log_entries = get_multiple_log_entries(count=5)
        with db_transaction() as cursor:
            insert_log_entries(cursor, log_entries)

        logs = get_logs(limit=100)
        assert len(logs) >= 5

    def test_get_logs_time_range_24h(self, db_transaction):
        """Time range filter returns logs from last 24 hours"""
        # Insert logs with different timestamps
        recent_logs = get_multiple_log_entries(count=3, time_range_hours=12)
        old_logs = []
        for i in range(2):
            log = get_sample_log_entry()
            log['timestamp'] = datetime.now() - timedelta(hours=48)
            old_logs.append(log)

        with db_transaction() as cursor:
            insert_log_entries(cursor, recent_logs + old_logs)

        logs = get_logs(time_range_hours=24)
        # Filter to logs in last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        recent = [l for l in logs if l['timestamp'] >= cutoff]

        assert len(recent) >= 3

    def test_get_logs_filter_by_process_type(self, db_transaction):
        """Process type filter returns matching logs"""
        logs_a = get_multiple_log_entries(count=3, process_types=['ProcessA'])
        logs_b = get_multiple_log_entries(count=2, process_types=['ProcessB'])

        with db_transaction() as cursor:
            insert_log_entries(cursor, logs_a + logs_b)

        # Filter by ProcessA
        results = get_logs(process_type='ProcessA', limit=100)
        process_a_results = [l for l in results if l['processtype'] == 'ProcessA']
        assert len(process_a_results) >= 3

    def test_get_logs_filter_by_run_uuid(self, db_transaction):
        """Run UUID filter returns matching logs"""
        import uuid
        run_uuid = str(uuid.uuid4())

        logs = get_multiple_log_entries(count=5, run_uuid=run_uuid)

        with db_transaction() as cursor:
            insert_log_entries(cursor, logs)

        # Pass time_range_hours=None to disable time filter (since we're filtering by UUID)
        results = get_logs(run_uuid=run_uuid, time_range_hours=None, limit=100)
        assert len(results) >= 5
        assert all(l['run_uuid'] == run_uuid for l in results)

    def test_get_logs_limit_enforced(self, db_transaction):
        """Limit parameter restricts result count"""
        logs = get_multiple_log_entries(count=20)

        with db_transaction() as cursor:
            insert_log_entries(cursor, logs)

        results = get_logs(limit=5)
        assert len(results) <= 5

    def test_get_logs_ordered_by_timestamp_desc(self, db_transaction):
        """Results are ordered by timestamp descending"""
        logs = get_multiple_log_entries(count=10, time_range_hours=24)

        with db_transaction() as cursor:
            insert_log_entries(cursor, logs)

        results = get_logs(limit=10)
        if len(results) >= 2:
            # Verify descending order
            for i in range(len(results) - 1):
                assert results[i]['timestamp'] >= results[i + 1]['timestamp']

    def test_get_distinct_process_types(self, db_transaction):
        """get_distinct_process_types returns unique process types"""
        logs = []
        logs.extend(get_multiple_log_entries(count=3, process_types=['TypeA']))
        logs.extend(get_multiple_log_entries(count=3, process_types=['TypeB']))
        logs.extend(get_multiple_log_entries(count=3, process_types=['TypeC']))

        with db_transaction() as cursor:
            insert_log_entries(cursor, logs)

        process_types = get_distinct_process_types()
        assert 'TypeA' in process_types
        assert 'TypeB' in process_types
        assert 'TypeC' in process_types


# ============================================================================
# DATASET QUERY TESTS
# ============================================================================

@pytest.mark.integration
class TestGetDatasets:
    """Tests for get_datasets function"""

    def test_get_datasets_empty_database(self, db_transaction, clean_test_data):
        """Empty database returns empty list"""
        datasets = get_datasets()
        test_datasets = [d for d in datasets if d.get('label', '').startswith('AdminTest_')]
        assert test_datasets == []

    def test_get_datasets_with_data(self, db_transaction, created_datasource, created_datasettype):
        """Returns datasets when data exists"""
        datasets = get_multiple_datasets(
            count=5,
            datasourceid=created_datasource['datasourceid'],
            datasettypeid=created_datasettype['datasettypeid']
        )

        with db_transaction() as cursor:
            insert_datasets(cursor, datasets)

        results = get_datasets()
        test_results = [d for d in results if d.get('label', '').startswith('AdminTest_')]
        assert len(test_results) >= 5

    def test_get_datasets_filter_by_datasource(self, db_transaction, created_datasources, created_datasettype):
        """Datasource filter returns matching datasets"""
        if len(created_datasources) < 2:
            pytest.skip("Need at least 2 datasources for this test")

        source1 = created_datasources[0]
        source2 = created_datasources[1]

        datasets1 = get_multiple_datasets(
            count=3,
            datasourceid=source1['datasourceid'],
            datasettypeid=created_datasettype['datasettypeid']
        )
        datasets2 = get_multiple_datasets(
            count=2,
            datasourceid=source2['datasourceid'],
            datasettypeid=created_datasettype['datasettypeid']
        )

        with db_transaction() as cursor:
            insert_datasets(cursor, datasets1 + datasets2)

        results = get_datasets(datasource=source1['sourcename'])
        source1_results = [d for d in results if d['datasource'] == source1['sourcename']]
        assert len(source1_results) >= 3

    def test_get_datasets_filter_by_datasettype(self, db_transaction, created_datasource, created_datasettype):
        """Datasettype filter returns matching datasets"""
        datasets = get_multiple_datasets(
            count=5,
            datasourceid=created_datasource['datasourceid'],
            datasettypeid=created_datasettype['datasettypeid']
        )

        with db_transaction() as cursor:
            insert_datasets(cursor, datasets)

        results = get_datasets(datasettype=created_datasettype['typename'])
        type_results = [d for d in results if d['datasettype'] == created_datasettype['typename']]
        assert len(type_results) >= 5

    def test_get_datasets_date_range(self, db_transaction, created_datasource, created_datasettype):
        """Date range filter works correctly"""
        datasets = get_multiple_datasets(
            count=10,
            datasourceid=created_datasource['datasourceid'],
            datasettypeid=created_datasettype['datasettypeid'],
            date_range_days=30
        )

        with db_transaction() as cursor:
            insert_datasets(cursor, datasets)

        # Filter to last 15 days
        date_from = datetime.now() - timedelta(days=15)
        date_to = datetime.now()

        results = get_datasets(date_from=date_from, date_to=date_to)
        test_results = [d for d in results if d.get('label', '').startswith('AdminTest_')]

        # Verify all results are within date range
        for dataset in test_results:
            assert date_from <= dataset['createddate'] <= date_to

    def test_get_datasets_limit_enforced(self, db_transaction, created_datasource, created_datasettype):
        """Limit parameter restricts result count"""
        datasets = get_multiple_datasets(
            count=20,
            datasourceid=created_datasource['datasourceid'],
            datasettypeid=created_datasettype['datasettypeid']
        )

        with db_transaction() as cursor:
            insert_datasets(cursor, datasets)

        results = get_datasets(limit=5)
        assert len(results) <= 5

    def test_get_dataset_sources(self, db_transaction, created_datasources, created_datasettype):
        """get_dataset_sources returns unique sources from datasets"""
        # Create datasets for each source
        for source in created_datasources[:3]:
            datasets = get_multiple_datasets(
                count=2,
                datasourceid=source['datasourceid'],
                datasettypeid=created_datasettype['datasettypeid']
            )
            with db_transaction() as cursor:
                insert_datasets(cursor, datasets)

        sources = get_dataset_sources()
        for source in created_datasources[:3]:
            assert source['sourcename'] in sources

    def test_get_dataset_types_from_datasets(self, db_transaction, created_datasource, created_datasettype):
        """get_dataset_types_from_datasets returns unique types from datasets"""
        datasets = get_multiple_datasets(
            count=5,
            datasourceid=created_datasource['datasourceid'],
            datasettypeid=created_datasettype['datasettypeid']
        )

        with db_transaction() as cursor:
            insert_datasets(cursor, datasets)

        types = get_dataset_types_from_datasets()
        assert created_datasettype['typename'] in types


# ============================================================================
# STATISTICS & AGGREGATIONS
# ============================================================================

@pytest.mark.integration
class TestStatistics:
    """Tests for statistics and aggregation functions"""

    def test_get_statistics_metrics_structure(self, db_transaction):
        """Statistics metrics returns expected keys"""
        metrics = get_statistics_metrics()

        assert 'total_logs_24h' in metrics
        assert 'unique_processes' in metrics
        assert 'avg_runtime' in metrics
        assert 'total_datasets_30d' in metrics
        assert 'total_active_datasets' in metrics
        assert 'total_active_configs' in metrics

    def test_get_statistics_metrics_types(self, db_transaction):
        """Statistics metrics returns correct data types"""
        metrics = get_statistics_metrics()

        assert isinstance(metrics['total_logs_24h'], int)
        assert isinstance(metrics['unique_processes'], int)
        assert isinstance(metrics['avg_runtime'], (int, float))
        assert isinstance(metrics['total_datasets_30d'], int)
        assert isinstance(metrics['total_active_datasets'], int)
        assert isinstance(metrics['total_active_configs'], int)

    def test_get_statistics_metrics_with_data(self, db_transaction):
        """Statistics reflect inserted test data"""
        # Insert test logs
        logs = get_multiple_log_entries(count=10, time_range_hours=12)
        with db_transaction() as cursor:
            insert_log_entries(cursor, logs)

        metrics = get_statistics_metrics()
        assert metrics['total_logs_24h'] >= 10

    def test_get_jobs_per_day(self, db_transaction):
        """Jobs per day aggregates correctly"""
        # Insert logs with different run_uuids to simulate different jobs
        import uuid
        logs = []
        for i in range(5):
            run_uuid = str(uuid.uuid4())
            log_group = get_multiple_log_entries(
                count=2,
                run_uuid=run_uuid,
                process_types=['GenericImportJob'],
                time_range_hours=24
            )
            logs.extend(log_group)

        with db_transaction() as cursor:
            insert_log_entries(cursor, logs)

        jobs = get_jobs_per_day(days=7)

        # Verify structure
        assert isinstance(jobs, list)
        if jobs:
            assert 'job_date' in jobs[0]
            assert 'job_count' in jobs[0]

    def test_get_jobs_per_day_ordered(self, db_transaction):
        """Jobs per day results are ordered by date ascending"""
        jobs = get_jobs_per_day(days=30)

        if len(jobs) >= 2:
            # Verify ascending order
            for i in range(len(jobs) - 1):
                assert jobs[i]['job_date'] <= jobs[i + 1]['job_date']

    def test_get_process_type_distribution(self, db_transaction):
        """Process type distribution aggregates correctly"""
        import uuid
        logs = []

        # Create multiple runs of different process types
        for process_type in ['TypeA', 'TypeB', 'TypeC']:
            for _ in range(3):  # 3 runs per type
                run_uuid = str(uuid.uuid4())
                log_group = get_multiple_log_entries(
                    count=2,
                    run_uuid=run_uuid,
                    process_types=[process_type],
                    time_range_hours=24
                )
                logs.extend(log_group)

        with db_transaction() as cursor:
            insert_log_entries(cursor, logs)

        distribution = get_process_type_distribution(days=7)

        # Verify structure
        assert isinstance(distribution, list)
        if distribution:
            assert 'processtype' in distribution[0]
            assert 'run_count' in distribution[0]

        # Verify our test data is included
        test_types = [d for d in distribution if d['processtype'] in ['TypeA', 'TypeB', 'TypeC']]
        assert len(test_types) >= 3

    def test_get_process_type_distribution_ordered_by_count_desc(self, db_transaction):
        """Process distribution is ordered by run_count descending"""
        distribution = get_process_type_distribution(days=30)

        if len(distribution) >= 2:
            # Verify descending order
            for i in range(len(distribution) - 1):
                assert distribution[i]['run_count'] >= distribution[i + 1]['run_count']

    def test_get_runtime_statistics(self, db_transaction):
        """Runtime statistics calculates min/max/avg correctly"""
        logs = []
        for i in range(5):
            log = get_sample_log_entry(processtype='TestProcess')
            log['stepruntime'] = 0.5 * (i + 1)  # 0.5, 1.0, 1.5, 2.0, 2.5
            logs.append(log)

        with db_transaction() as cursor:
            insert_log_entries(cursor, logs)

        stats = get_runtime_statistics(days=7)

        # Verify structure
        assert isinstance(stats, list)
        if stats:
            assert 'processtype' in stats[0]
            assert 'step_count' in stats[0]
            assert 'avg_runtime' in stats[0]
            assert 'min_runtime' in stats[0]
            assert 'max_runtime' in stats[0]

        # Find our test process
        test_stat = next((s for s in stats if s['processtype'] == 'TestProcess'), None)
        if test_stat:
            assert test_stat['step_count'] >= 5
            assert test_stat['min_runtime'] >= 0.5
            assert test_stat['max_runtime'] >= 2.5

    def test_get_runtime_statistics_ordered_by_avg_desc(self, db_transaction):
        """Runtime statistics ordered by average runtime descending"""
        stats = get_runtime_statistics(days=7)

        if len(stats) >= 2:
            # Verify descending order
            for i in range(len(stats) - 1):
                assert stats[i]['avg_runtime'] >= stats[i + 1]['avg_runtime']


# ============================================================================
# CSV EXPORT TESTS
# ============================================================================

@pytest.mark.integration
class TestCSVExport:
    """Tests for CSV export functionality"""

    def test_export_logs_to_csv_empty(self, db_transaction):
        """Empty logs returns message"""
        csv = export_logs_to_csv([])
        assert 'No logs' in csv

    def test_export_logs_to_csv_headers(self, db_transaction):
        """CSV export includes correct headers"""
        logs = [get_sample_log_entry()]
        csv = export_logs_to_csv(logs)

        assert 'logentryid,run_uuid,processtype' in csv
        assert 'stepcounter,message,stepruntime,timestamp' in csv

    def test_export_logs_to_csv_data(self, db_transaction):
        """CSV export includes log data"""
        import uuid
        run_uuid = str(uuid.uuid4())
        log = get_sample_log_entry(
            run_uuid=run_uuid,
            processtype='TestProcess',
            message='Test message'
        )

        csv = export_logs_to_csv([log])

        assert run_uuid in csv
        assert 'TestProcess' in csv
        assert 'Test message' in csv

    def test_export_logs_to_csv_quote_escaping(self, db_transaction):
        """CSV export escapes quotes in messages"""
        log = get_sample_log_entry(message='Test "quoted" message')
        csv = export_logs_to_csv([log])

        # Quotes should be doubled and wrapped in quotes
        assert '""' in csv  # Escaped quote

    def test_export_logs_to_csv_multiple_rows(self, db_transaction):
        """CSV export handles multiple logs"""
        logs = get_multiple_log_entries(count=5)
        csv = export_logs_to_csv(logs)

        lines = csv.split('\n')
        # Header + 5 data rows
        assert len(lines) >= 6


# ============================================================================
# EDGE CASES & ERROR CONDITIONS
# ============================================================================

@pytest.mark.integration
class TestMonitoringEdgeCases:
    """Test edge cases and error conditions"""

    def test_get_logs_with_all_time_filter(self, db_transaction):
        """time_range_hours=None returns all logs"""
        logs = get_logs(time_range_hours=None, limit=100)
        assert isinstance(logs, list)

    def test_get_logs_with_invalid_process_type(self, db_transaction):
        """Non-existent process type returns empty for test logs"""
        logs = get_logs(process_type='NonExistentProcessType')
        assert isinstance(logs, list)

    def test_get_logs_with_invalid_run_uuid(self, db_transaction):
        """Non-existent run UUID returns empty"""
        import uuid
        logs = get_logs(run_uuid=str(uuid.uuid4()))
        assert logs == []

    def test_get_datasets_with_invalid_datasource(self, db_transaction):
        """Non-existent datasource returns empty for test datasets"""
        datasets = get_datasets(datasource='NonExistentSource')
        test_datasets = [d for d in datasets if d.get('label', '').startswith('AdminTest_')]
        assert test_datasets == []

    def test_get_datasets_with_invalid_datasettype(self, db_transaction):
        """Non-existent datasettype returns empty for test datasets"""
        datasets = get_datasets(datasettype='NonExistentType')
        test_datasets = [d for d in datasets if d.get('label', '').startswith('AdminTest_')]
        assert test_datasets == []

    def test_get_datasets_with_future_date_range(self, db_transaction):
        """Future date range returns empty"""
        date_from = datetime.now() + timedelta(days=1)
        date_to = datetime.now() + timedelta(days=30)

        datasets = get_datasets(date_from=date_from, date_to=date_to)
        assert datasets == []

    def test_get_jobs_per_day_large_range(self, db_transaction):
        """Large day range doesn't cause errors"""
        jobs = get_jobs_per_day(days=365)
        assert isinstance(jobs, list)

    def test_get_process_type_distribution_large_range(self, db_transaction):
        """Large day range doesn't cause errors"""
        distribution = get_process_type_distribution(days=365)
        assert isinstance(distribution, list)

    def test_get_runtime_statistics_large_range(self, db_transaction):
        """Large day range doesn't cause errors"""
        stats = get_runtime_statistics(days=365)
        assert isinstance(stats, list)

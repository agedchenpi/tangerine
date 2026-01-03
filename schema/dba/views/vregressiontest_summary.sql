-- Regression test suite summary view
-- Aggregates test results by suite run for quick status overview

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_views
        WHERE schemaname = 'dba' AND viewname = 'vregressiontest_summary'
    ) THEN
        EXECUTE '
        CREATE VIEW dba.vregressiontest_summary AS
        SELECT
            test_suite_run_uuid,
            MIN(start_time) as suite_start_time,
            MAX(end_time) as suite_end_time,
            EXTRACT(EPOCH FROM (MAX(end_time) - MIN(start_time))) as total_duration_seconds,
            COUNT(*) as total_tests,
            COUNT(*) FILTER (WHERE status = ''passed'') as passed_tests,
            COUNT(*) FILTER (WHERE status = ''failed'') as failed_tests,
            COUNT(*) FILTER (WHERE status = ''error'') as error_tests,
            COUNT(*) FILTER (WHERE status = ''skipped'') as skipped_tests,
            ROUND(100.0 * COUNT(*) FILTER (WHERE status = ''passed'') / COUNT(*), 2) as pass_rate_pct,
            SUM(expected_records) as total_expected_records,
            SUM(records_loaded) as total_loaded_records,
            ARRAY_AGG(test_name ORDER BY tregressiontestid) FILTER (WHERE status != ''passed'') as failed_test_names
        FROM dba.tregressiontest
        GROUP BY test_suite_run_uuid
        ORDER BY suite_start_time DESC;
        ';

        COMMENT ON VIEW dba.vregressiontest_summary IS 'Aggregated summary of regression test suite runs.';
    END IF;
END $$;

GRANT SELECT ON dba.vregressiontest_summary TO PUBLIC;

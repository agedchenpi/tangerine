-- Regression test results table
-- Stores execution results for generic import system regression tests

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tregressiontest') THEN
        CREATE TABLE dba.tregressiontest (
            tregressiontestid SERIAL PRIMARY KEY,
            test_suite_run_uuid VARCHAR(36) NOT NULL,
            test_name VARCHAR(200) NOT NULL,
            test_category VARCHAR(50) NOT NULL CHECK (test_category IN ('csv', 'xls', 'xlsx', 'json', 'xml', 'edge_case', 'integration')),
            config_id INT REFERENCES dba.timportconfig(config_id),
            status VARCHAR(20) NOT NULL CHECK (status IN ('passed', 'failed', 'skipped', 'error')),
            error_code VARCHAR(50),
            error_message TEXT,
            stack_trace TEXT,
            expected_records INT,
            records_extracted INT,
            records_transformed INT,
            records_loaded INT,
            file_path VARCHAR(500),
            run_uuid VARCHAR(36),
            datasetid INT REFERENCES dba.tdataset(datasetid),
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            duration_seconds NUMERIC(10, 3),
            test_metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT chk_valid_duration CHECK (end_time IS NULL OR end_time >= start_time)
        );

        COMMENT ON TABLE dba.tregressiontest IS 'Stores regression test results for generic import system validation.';
        COMMENT ON COLUMN dba.tregressiontest.tregressiontestid IS 'Unique identifier for individual test execution.';
        COMMENT ON COLUMN dba.tregressiontest.test_suite_run_uuid IS 'UUID grouping all tests in a single regression suite run.';
        COMMENT ON COLUMN dba.tregressiontest.test_name IS 'Descriptive name of the test case.';
        COMMENT ON COLUMN dba.tregressiontest.test_category IS 'Category of test (file type or special category).';
        COMMENT ON COLUMN dba.tregressiontest.config_id IS 'Foreign key to timportconfig used for this test.';
        COMMENT ON COLUMN dba.tregressiontest.status IS 'Test result status (passed/failed/skipped/error).';
        COMMENT ON COLUMN dba.tregressiontest.error_code IS 'Error classification code if test failed.';
        COMMENT ON COLUMN dba.tregressiontest.error_message IS 'Human-readable error message.';
        COMMENT ON COLUMN dba.tregressiontest.stack_trace IS 'Full stack trace for debugging failures.';
        COMMENT ON COLUMN dba.tregressiontest.expected_records IS 'Expected number of records to be loaded.';
        COMMENT ON COLUMN dba.tregressiontest.records_extracted IS 'Actual records extracted.';
        COMMENT ON COLUMN dba.tregressiontest.records_transformed IS 'Actual records transformed.';
        COMMENT ON COLUMN dba.tregressiontest.records_loaded IS 'Actual records loaded to database.';
        COMMENT ON COLUMN dba.tregressiontest.file_path IS 'Path to test data file.';
        COMMENT ON COLUMN dba.tregressiontest.run_uuid IS 'ETL job run_uuid from the import execution.';
        COMMENT ON COLUMN dba.tregressiontest.datasetid IS 'Dataset ID created by the import job.';
        COMMENT ON COLUMN dba.tregressiontest.start_time IS 'Test start timestamp.';
        COMMENT ON COLUMN dba.tregressiontest.end_time IS 'Test end timestamp.';
        COMMENT ON COLUMN dba.tregressiontest.duration_seconds IS 'Test execution duration in seconds.';
        COMMENT ON COLUMN dba.tregressiontest.test_metadata IS 'Additional test metadata as JSON (strategy_id, file_type, validation_details, etc.).';
        COMMENT ON COLUMN dba.tregressiontest.created_at IS 'Record creation timestamp.';

        -- Create indexes for common queries
        CREATE INDEX idx_tregressiontest_suite_uuid ON dba.tregressiontest(test_suite_run_uuid);
        CREATE INDEX idx_tregressiontest_status ON dba.tregressiontest(status);
        CREATE INDEX idx_tregressiontest_category ON dba.tregressiontest(test_category);
        CREATE INDEX idx_tregressiontest_config_id ON dba.tregressiontest(config_id);
        CREATE INDEX idx_tregressiontest_created_at ON dba.tregressiontest(created_at);
    END IF;
END $$;

GRANT SELECT ON dba.tregressiontest TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tregressiontest TO app_rw;
GRANT ALL ON dba.tregressiontest TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tregressiontest_tregressiontestid_seq TO app_rw, app_ro;

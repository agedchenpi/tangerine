DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tlogentry') THEN
        CREATE TABLE dba.tlogentry (
            logentryid SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            run_uuid VARCHAR(36) NOT NULL,
            processtype VARCHAR(50) NOT NULL,
            stepcounter VARCHAR(50),
            username VARCHAR(50),
            stepruntime FLOAT,
            totalruntime FLOAT,
            message TEXT NOT NULL
        );
        COMMENT ON TABLE dba.tlogentry IS 'Stores log entries for ETL processes.';
        COMMENT ON COLUMN dba.tlogentry.logentryid IS 'Primary key for the log entry.';
        COMMENT ON COLUMN dba.tlogentry.timestamp IS 'Timestamp of the log entry.';
        COMMENT ON COLUMN dba.tlogentry.run_uuid IS 'Unique identifier for the ETL run.';
        COMMENT ON COLUMN dba.tlogentry.processtype IS 'Type of process (e.g., EventProcessing, FinalSave).';
        COMMENT ON COLUMN dba.tlogentry.stepcounter IS 'Step identifier within the process.';
        COMMENT ON COLUMN dba.tlogentry.username IS 'User who executed the process.';
        COMMENT ON COLUMN dba.tlogentry.stepruntime IS 'Runtime of the step in seconds.';
        COMMENT ON COLUMN dba.tlogentry.totalruntime IS 'Total runtime of the script in seconds.';
        COMMENT ON COLUMN dba.tlogentry.message IS 'Log message.';
    END IF;
END   $$;
GRANT SELECT ON dba.tlogentry TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tlogentry TO app_rw;
GRANT ALL ON dba.tlogentry TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tlogentry_logentryid_seq TO app_rw, app_ro;
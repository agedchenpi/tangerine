DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tddllogs') THEN
        CREATE TABLE dba.tddllogs (
            logid SERIAL PRIMARY KEY,
            eventtime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            eventtype TEXT NOT NULL,
            schemaname TEXT,
            objectname TEXT,
            objecttype TEXT NOT NULL,
            sqlstatement TEXT NOT NULL,
            username VARCHAR(50) NOT NULL DEFAULT CURRENT_USER
        );
        COMMENT ON TABLE dba.tddllogs IS 'Logs DDL changes in the database.';
        COMMENT ON COLUMN dba.tddllogs.logid IS 'Primary key for the log entry.';
        COMMENT ON COLUMN dba.tddllogs.eventtime IS 'Timestamp of the DDL event.';
        COMMENT ON COLUMN dba.tddllogs.eventtype IS 'Type of DDL event (e.g., CREATE, ALTER, DROP).';
        COMMENT ON COLUMN dba.tddllogs.schemaname IS 'Schema of the affected object.';
        COMMENT ON COLUMN dba.tddllogs.objectname IS 'Identifier of the affected object.';
        COMMENT ON COLUMN dba.tddllogs.objecttype IS 'Type of the affected object (e.g., TABLE, FUNCTION).';
        COMMENT ON COLUMN dba.tddllogs.sqlstatement IS 'SQL statement tag that triggered the event.';
        COMMENT ON COLUMN dba.tddllogs.username IS 'User who performed the DDL operation.';
    END IF;
END   $$;
GRANT SELECT ON dba.tddllogs TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tddllogs TO app_rw;
GRANT ALL ON dba.tddllogs TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tddllogs_logid_seq TO app_rw, app_ro;
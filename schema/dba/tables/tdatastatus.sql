DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tdatastatus') THEN
        CREATE TABLE dba.tdatastatus (
            datastatusid SERIAL PRIMARY KEY,
            statusname VARCHAR(50) NOT NULL UNIQUE,
            description TEXT,
            createddate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            createdby VARCHAR(50) NOT NULL DEFAULT CURRENT_USER
        );
        COMMENT ON TABLE dba.tdatastatus IS 'Stores status codes for datasets (e.g., Active, Inactive, Deleted).';
        COMMENT ON COLUMN dba.tdatastatus.datastatusid IS 'Primary key for status.';
        COMMENT ON COLUMN dba.tdatastatus.statusname IS 'Unique name of the status.';
        COMMENT ON COLUMN dba.tdatastatus.description IS 'Optional description of the status.';
        COMMENT ON COLUMN dba.tdatastatus.createddate IS 'Timestamp when the record was created.';
        COMMENT ON COLUMN dba.tdatastatus.createdby IS 'User who created the record.';
    END IF;
END   $$;
GRANT SELECT ON dba.tdatastatus TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tdatastatus TO app_rw;
GRANT ALL ON dba.tdatastatus TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tdatastatus_datastatusid_seq TO app_rw, app_ro;
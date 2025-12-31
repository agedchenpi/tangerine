DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tdatasource') THEN
        CREATE TABLE dba.tdatasource (
            datasourceid SERIAL PRIMARY KEY,
            sourcename VARCHAR(50) NOT NULL UNIQUE,
            description TEXT,
            createddate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            createdby VARCHAR(50) NOT NULL DEFAULT CURRENT_USER
        );
        COMMENT ON TABLE dba.tdatasource IS 'Stores data source definitions ';
        COMMENT ON COLUMN dba.tdatasource.datasourceid IS 'Primary key for data source.';
        COMMENT ON COLUMN dba.tdatasource.sourcename IS 'Unique name of the data source.';
        COMMENT ON COLUMN dba.tdatasource.description IS 'Optional description of the data source.';
        COMMENT ON COLUMN dba.tdatasource.createddate IS 'Timestamp when the record was created.';
        COMMENT ON COLUMN dba.tdatasource.createdby IS 'User who created the record.';
    END IF;
END   $$;
GRANT SELECT ON dba.tdatasource TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tdatasource TO app_rw;
GRANT ALL ON dba.tdatasource TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tdatasource_datasourceid_seq TO app_rw, app_ro;
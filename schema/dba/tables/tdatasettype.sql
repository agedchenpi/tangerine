DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tdatasettype') THEN
        CREATE TABLE dba.tdatasettype (
            datasettypeid SERIAL PRIMARY KEY,
            typename VARCHAR(50) NOT NULL UNIQUE,
            description TEXT,
            createddate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            createdby VARCHAR(50) NOT NULL DEFAULT CURRENT_USER
        );
        COMMENT ON TABLE dba.tdatasettype IS 'Stores dataset type definitions';
        COMMENT ON COLUMN dba.tdatasettype.datasettypeid IS 'Primary key for dataset type.';
        COMMENT ON COLUMN dba.tdatasettype.typename IS 'Unique name of the dataset type.';
        COMMENT ON COLUMN dba.tdatasettype.description IS 'Optional description of the dataset type.';
        COMMENT ON COLUMN dba.tdatasettype.createddate IS 'Timestamp when the record was created.';
        COMMENT ON COLUMN dba.tdatasettype.createdby IS 'User who created the record.';
    END IF;
END $$;
GRANT SELECT ON dba.tdatasettype TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tdatasettype TO app_rw;
GRANT ALL ON dba.tdatasettype TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tdatasettype_datasettypeid_seq TO app_rw, app_ro;
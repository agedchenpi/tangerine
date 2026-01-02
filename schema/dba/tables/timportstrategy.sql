DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'timportstrategy') THEN
        CREATE TABLE dba.timportstrategy (
            importstrategyid SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            createddate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            createdby VARCHAR(50) NOT NULL DEFAULT CURRENT_USER
        );
        COMMENT ON TABLE dba.timportstrategy IS 'Reference table defining import strategies for timportconfig, specifying how to handle column mismatches during data import.';
        COMMENT ON COLUMN dba.timportstrategy.importstrategyid IS 'Unique identifier for the import strategy.';
        COMMENT ON COLUMN dba.timportstrategy.name IS 'Descriptive name of the import strategy.';
        COMMENT ON COLUMN dba.timportstrategy.description IS 'Detailed description of the import strategy behavior.';
        COMMENT ON COLUMN dba.timportstrategy.createddate IS 'Timestamp when the record was created.';
        COMMENT ON COLUMN dba.timportstrategy.createdby IS 'User who created the record.';
    END IF;
END $$;
GRANT SELECT ON dba.timportstrategy TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.timportstrategy TO app_rw;
GRANT ALL ON dba.timportstrategy TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.timportstrategy_importstrategyid_seq TO app_rw, app_ro;

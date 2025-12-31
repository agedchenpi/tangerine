DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'dba') THEN
        CREATE SCHEMA dba;
        COMMENT ON SCHEMA dba IS 'Schema for ETL pipeline maintenance, logging, and dataset metadata.';
    END IF;
END $$;
GRANT ALL ON SCHEMA dba TO admin;
GRANT USAGE, CREATE ON SCHEMA dba TO app_rw;
GRANT USAGE ON SCHEMA dba TO app_ro;
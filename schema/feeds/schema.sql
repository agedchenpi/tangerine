DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'feeds') THEN
        CREATE SCHEMA feeds;
        COMMENT ON SCHEMA feeds IS 'Schema for storing raw data feeds in the ETL pipeline.';
    END IF;
END $$;
GRANT ALL ON SCHEMA feeds TO admin;
GRANT USAGE, CREATE ON SCHEMA feeds TO app_rw;
GRANT USAGE ON SCHEMA feeds TO app_ro;
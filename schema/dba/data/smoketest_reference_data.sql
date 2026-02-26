-- Smoketest Reference Data
-- Inserts data source and dataset type for hourly cron scheduler smoketest
-- This file is sourced during initial database setup via init.sh

DO $$
BEGIN
    -- Insert Smoketest data source if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM dba.tdatasource WHERE sourcename = 'Smoketest') THEN
        INSERT INTO dba.tdatasource (sourcename, description, createdby)
        VALUES (
            'Smoketest',
            'Internal smoketest and regression testing',
            'admin'
        );
        RAISE NOTICE 'Created data source: Smoketest';
    END IF;

    -- Insert Smoketest dataset type if it doesn't exist
    INSERT INTO dba.tdatasettype (typename, description, createdby) VALUES
        ('Smoketest', 'Hourly cron scheduler smoketest', 'admin')
    ON CONFLICT (typename) DO NOTHING;

    RAISE NOTICE 'Smoketest reference data setup complete';
END $$;

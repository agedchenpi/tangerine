-- BankOfEngland Reference Data
-- Inserts data source and dataset types for Bank of England IADB
-- This file is sourced during initial database setup via init.sh

DO $$
BEGIN
    -- Insert BankOfEngland data source if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM dba.tdatasource WHERE sourcename = 'BankOfEngland') THEN
        INSERT INTO dba.tdatasource (sourcename, description, createdby)
        VALUES (
            'BankOfEngland',
            'Bank of England Interactive Statistical Database (IADB)',
            'admin'
        );
        RAISE NOTICE 'Created data source: BankOfEngland';
    END IF;

    -- Insert dataset type if it doesn't exist
    INSERT INTO dba.tdatasettype (typename, description, createdby) VALUES
        ('Rates', 'Interest rates and benchmark rates', 'admin')
    ON CONFLICT (typename) DO NOTHING;

    RAISE NOTICE 'BankOfEngland reference data setup complete';
END $$;

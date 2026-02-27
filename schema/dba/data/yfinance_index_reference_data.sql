-- YFinance Index Reference Data
-- Ensures datasource and datasettype exist for market index imports

DO $$ BEGIN
    INSERT INTO dba.tdatasource (sourcename, description, createdby)
    VALUES ('YFinance', 'Yahoo Finance market data', 'admin')
    ON CONFLICT (sourcename) DO NOTHING;

    INSERT INTO dba.tdatasettype (typename, description, createdby)
    VALUES ('Index', 'Market index and benchmark data', 'admin')
    ON CONFLICT (typename) DO NOTHING;
END $$;

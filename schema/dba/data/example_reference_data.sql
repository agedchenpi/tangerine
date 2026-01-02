-- Reference data for Example ETL job
-- This data is required for ExampleETLJob to run successfully

-- Insert Example dataset type if it doesn't exist
INSERT INTO dba.tdatasettype (typename, description)
SELECT 'Example', 'Example dataset type for ETL framework demonstration'
WHERE NOT EXISTS (
    SELECT 1 FROM dba.tdatasettype WHERE typename = 'Example'
);

-- Insert ExampleAPI data source if it doesn't exist
INSERT INTO dba.tdatasource (sourcename, description)
SELECT 'ExampleAPI', 'Example API source for ETL framework demonstration'
WHERE NOT EXISTS (
    SELECT 1 FROM dba.tdatasource WHERE sourcename = 'ExampleAPI'
);

-- Insert ETL-specific statuses if they don't exist
INSERT INTO dba.tdatastatus (statusname, description)
SELECT 'New', 'Dataset created but not yet loaded'
WHERE NOT EXISTS (
    SELECT 1 FROM dba.tdatastatus WHERE statusname = 'New'
);

INSERT INTO dba.tdatastatus (statusname, description)
SELECT 'Failed', 'Dataset load failed'
WHERE NOT EXISTS (
    SELECT 1 FROM dba.tdatastatus WHERE statusname = 'Failed'
);

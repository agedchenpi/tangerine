DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tdataset') THEN
        CREATE TABLE dba.tdataset (
            datasetid SERIAL PRIMARY KEY,
            datasetdate DATE NOT NULL,
            label VARCHAR(100) NOT NULL,
            datasettypeid INTEGER NOT NULL,
            datasourceid INTEGER NOT NULL,
            datastatusid INTEGER NOT NULL,
            efffromdate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            effthrudate TIMESTAMP NOT NULL DEFAULT '9999-01-01',
            isactive BOOLEAN NOT NULL DEFAULT TRUE,
            createddate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            createdby VARCHAR(50) NOT NULL DEFAULT CURRENT_USER,
            CONSTRAINT fk_dataset_type FOREIGN KEY (datasettypeid) REFERENCES dba.tdatasettype (datasettypeid),
            CONSTRAINT fk_dataset_source FOREIGN KEY (datasourceid) REFERENCES dba.tdatasource (datasourceid),
            CONSTRAINT fk_dataset_status FOREIGN KEY (datastatusid) REFERENCES dba.tdatastatus (datastatusid),
            CONSTRAINT chk_eff_dates CHECK (efffromdate <= effthrudate)
        );
        COMMENT ON TABLE dba.tdataset IS 'Tracks metadata for dataset loads in the ETL pipeline.';
        COMMENT ON COLUMN dba.tdataset.datasetid IS 'Primary key for the dataset.';
        COMMENT ON COLUMN dba.tdataset.datasetdate IS 'Date associated with the dataset (e.g., data reference date).';
        COMMENT ON COLUMN dba.tdataset.label IS 'Descriptive label for the dataset.';
        COMMENT ON COLUMN dba.tdataset.datasettypeid IS 'Foreign key to tdatasettype, indicating dataset type.';
        COMMENT ON COLUMN dba.tdataset.datasourceid IS 'Foreign key to tdatasource, indicating data source.';
        COMMENT ON COLUMN dba.tdataset.datastatusid IS 'Foreign key to tdatastatus, indicating dataset status.';
        COMMENT ON COLUMN dba.tdataset.efffromdate IS 'Effective start date, defaults to creation time.';
        COMMENT ON COLUMN dba.tdataset.effthrudate IS 'Effective end date, defaults to 9999-01-01 for active records.';
        COMMENT ON COLUMN dba.tdataset.isactive IS 'Indicates if the dataset is active (TRUE) or inactive (FALSE).';
        COMMENT ON COLUMN dba.tdataset.createddate IS 'Timestamp when the record was created.';
        COMMENT ON COLUMN dba.tdataset.createdby IS 'User who created the record.';
    END IF;
END   $$;
GRANT SELECT ON dba.tdataset TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tdataset TO app_rw;
GRANT ALL ON dba.tdataset TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tdataset_datasetid_seq TO app_rw, app_ro;
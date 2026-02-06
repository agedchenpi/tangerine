-- NewYorkFed Agency MBS Table
-- Agency mortgage-backed securities operations
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_agency_mbs') THEN
        CREATE TABLE feeds.newyorkfed_agency_mbs (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Operation identification
            operation_date DATE NOT NULL,
            operation_type VARCHAR(50),
            cusip VARCHAR(9),
            security_description TEXT,

            -- Operation details
            settlement_date DATE,
            maturity_date DATE,

            -- Amounts
            operation_amount NUMERIC(20, 2),
            total_accepted NUMERIC(20, 2),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_agency_mbs_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_agency_mbs_dataset ON feeds.newyorkfed_agency_mbs(datasetid);
        CREATE INDEX idx_newyorkfed_agency_mbs_date ON feeds.newyorkfed_agency_mbs(operation_date);
        CREATE INDEX idx_newyorkfed_agency_mbs_cusip ON feeds.newyorkfed_agency_mbs(cusip);

        COMMENT ON TABLE feeds.newyorkfed_agency_mbs IS 'Agency mortgage-backed securities (MBS) operations';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_agency_mbs TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_agency_mbs TO app_rw;
GRANT ALL ON feeds.newyorkfed_agency_mbs TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_agency_mbs_record_id_seq TO app_rw;

-- NewYorkFed Guide Sheets Table
-- Guide sheet publications: FR 2004SI, WI (When-Issued), F-Series
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_guide_sheets') THEN
        CREATE TABLE feeds.newyorkfed_guide_sheets (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Publication identification
            publication_date DATE NOT NULL,
            guide_type VARCHAR(50),
            security_type VARCHAR(50),
            cusip VARCHAR(9),

            -- Security details
            issue_date DATE,
            maturity_date DATE,
            coupon_rate NUMERIC(10, 4),

            -- Guide values
            settlement_price NUMERIC(15, 6),
            accrued_interest NUMERIC(15, 6),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_guide_sheets_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_guide_sheets_dataset ON feeds.newyorkfed_guide_sheets(datasetid);
        CREATE INDEX idx_newyorkfed_guide_sheets_date ON feeds.newyorkfed_guide_sheets(publication_date);
        CREATE INDEX idx_newyorkfed_guide_sheets_type ON feeds.newyorkfed_guide_sheets(guide_type);
        CREATE INDEX idx_newyorkfed_guide_sheets_cusip ON feeds.newyorkfed_guide_sheets(cusip);

        COMMENT ON TABLE feeds.newyorkfed_guide_sheets IS 'Guide sheet publications: FR 2004SI, WI, F-Series';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_guide_sheets TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_guide_sheets TO app_rw;
GRANT ALL ON feeds.newyorkfed_guide_sheets TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_guide_sheets_record_id_seq TO app_rw;

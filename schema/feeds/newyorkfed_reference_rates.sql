-- NewYorkFed Reference Rates Table
-- Federal Reserve reference rates: SOFR, EFFR, OBFR, TGCR, BGCR
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_reference_rates') THEN
        CREATE TABLE feeds.newyorkfed_reference_rates (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Rate identification
            rate_type VARCHAR(10) NOT NULL,
            effective_date DATE NOT NULL,

            -- Rate values
            rate_percent NUMERIC(10, 4),
            volume_billions NUMERIC(15, 2),

            -- Percentile distribution
            percentile_1 NUMERIC(10, 4),
            percentile_25 NUMERIC(10, 4),
            percentile_75 NUMERIC(10, 4),
            percentile_99 NUMERIC(10, 4),

            -- Target range (for EFFR)
            target_range_from NUMERIC(10, 4),
            target_range_to NUMERIC(10, 4),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT uq_newyorkfed_ref_rates UNIQUE (rate_type, effective_date, datasetid),
            CONSTRAINT fk_newyorkfed_ref_rates_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_ref_rates_dataset ON feeds.newyorkfed_reference_rates(datasetid);
        CREATE INDEX idx_newyorkfed_ref_rates_date ON feeds.newyorkfed_reference_rates(effective_date);
        CREATE INDEX idx_newyorkfed_ref_rates_type ON feeds.newyorkfed_reference_rates(rate_type);

        COMMENT ON TABLE feeds.newyorkfed_reference_rates IS 'Federal Reserve reference rates: SOFR, EFFR, OBFR, TGCR, BGCR from NewYorkFed Markets API';
        COMMENT ON COLUMN feeds.newyorkfed_reference_rates.rate_type IS 'Rate type: SOFR (Secured Overnight Financing Rate), EFFR (Effective Federal Funds Rate), OBFR (Overnight Bank Funding Rate), TGCR (Tri-Party General Collateral Rate), BGCR (Broad General Collateral Rate)';
        COMMENT ON COLUMN feeds.newyorkfed_reference_rates.effective_date IS 'Date for which the rate is effective';
        COMMENT ON COLUMN feeds.newyorkfed_reference_rates.rate_percent IS 'Rate value in percentage';
        COMMENT ON COLUMN feeds.newyorkfed_reference_rates.volume_billions IS 'Transaction volume in billions of dollars';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_reference_rates TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_reference_rates TO app_rw;
GRANT ALL ON feeds.newyorkfed_reference_rates TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_reference_rates_record_id_seq TO app_rw;

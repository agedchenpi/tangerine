-- NewYorkFed Primary Dealer Statistics Table
-- Primary dealer statistics, survey results, and positions
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_pd_statistics') THEN
        CREATE TABLE feeds.newyorkfed_pd_statistics (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Report identification
            report_date DATE NOT NULL,
            report_type VARCHAR(50),
            dealer_name VARCHAR(100),

            -- Statistics
            security_type VARCHAR(50),
            position_type VARCHAR(50),

            -- Amounts
            gross_financing_in NUMERIC(20, 2),
            gross_financing_out NUMERIC(20, 2),
            net_financing NUMERIC(20, 2),
            securities_in NUMERIC(20, 2),
            securities_out NUMERIC(20, 2),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_pd_statistics_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_pd_statistics_dataset ON feeds.newyorkfed_pd_statistics(datasetid);
        CREATE INDEX idx_newyorkfed_pd_statistics_date ON feeds.newyorkfed_pd_statistics(report_date);
        CREATE INDEX idx_newyorkfed_pd_statistics_type ON feeds.newyorkfed_pd_statistics(report_type);
        CREATE INDEX idx_newyorkfed_pd_statistics_dealer ON feeds.newyorkfed_pd_statistics(dealer_name);

        COMMENT ON TABLE feeds.newyorkfed_pd_statistics IS 'Primary dealer statistics, survey results, and positions';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_pd_statistics TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_pd_statistics TO app_rw;
GRANT ALL ON feeds.newyorkfed_pd_statistics TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_pd_statistics_record_id_seq TO app_rw;

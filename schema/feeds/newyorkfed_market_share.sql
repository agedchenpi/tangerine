-- NewYorkFed Market Share Table
-- Primary dealer market share data (quarterly and year-to-date)
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_market_share') THEN
        CREATE TABLE feeds.newyorkfed_market_share (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Period identification
            report_date DATE NOT NULL,
            report_period VARCHAR(20),
            dealer_name VARCHAR(100),

            -- Market share metrics
            security_type VARCHAR(50),
            market_segment VARCHAR(50),

            -- Share percentages
            market_share_pct NUMERIC(10, 4),
            transaction_volume NUMERIC(20, 2),
            transaction_count INT,

            -- Rankings
            rank_position INT,

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_market_share_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_market_share_dataset ON feeds.newyorkfed_market_share(datasetid);
        CREATE INDEX idx_newyorkfed_market_share_date ON feeds.newyorkfed_market_share(report_date);
        CREATE INDEX idx_newyorkfed_market_share_dealer ON feeds.newyorkfed_market_share(dealer_name);
        CREATE INDEX idx_newyorkfed_market_share_type ON feeds.newyorkfed_market_share(security_type);

        COMMENT ON TABLE feeds.newyorkfed_market_share IS 'Primary dealer market share data: quarterly and year-to-date statistics';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_market_share TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_market_share TO app_rw;
GRANT ALL ON feeds.newyorkfed_market_share TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_market_share_record_id_seq TO app_rw;

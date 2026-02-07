-- NewYorkFed FX Swap Counterparties Table
-- List of central bank counterparties for foreign exchange swap operations
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_counterparties') THEN
        CREATE TABLE feeds.newyorkfed_counterparties (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Counterparty identification
            counterparty_name VARCHAR(200) NOT NULL,

            -- Optional metadata
            counterparty_type VARCHAR(50) DEFAULT 'Central Bank',
            is_active BOOLEAN DEFAULT TRUE,

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_counterparties_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid),
            CONSTRAINT uk_newyorkfed_counterparties_name UNIQUE (counterparty_name, datasetid)
        );

        CREATE INDEX idx_newyorkfed_counterparties_dataset ON feeds.newyorkfed_counterparties(datasetid);
        CREATE INDEX idx_newyorkfed_counterparties_name ON feeds.newyorkfed_counterparties(counterparty_name);
        CREATE INDEX idx_newyorkfed_counterparties_active ON feeds.newyorkfed_counterparties(is_active);

        COMMENT ON TABLE feeds.newyorkfed_counterparties IS 'Central bank counterparties for FX swap operations';
        COMMENT ON COLUMN feeds.newyorkfed_counterparties.counterparty_name IS 'Official name of central bank counterparty';
        COMMENT ON COLUMN feeds.newyorkfed_counterparties.is_active IS 'Whether this counterparty is currently active in FX swap operations';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_counterparties TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_counterparties TO app_rw;
GRANT ALL ON feeds.newyorkfed_counterparties TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_counterparties_record_id_seq TO app_rw;

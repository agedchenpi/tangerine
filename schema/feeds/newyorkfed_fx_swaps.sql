-- NewYorkFed FX Swaps Table
-- Central bank liquidity swaps and foreign exchange operations
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_fx_swaps') THEN
        CREATE TABLE feeds.newyorkfed_fx_swaps (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Swap identification
            swap_date DATE NOT NULL,
            counterparty VARCHAR(100),
            currency_code VARCHAR(3),

            -- Swap details
            maturity_date DATE,
            term_days INT,

            -- Amounts
            usd_amount NUMERIC(20, 2),
            foreign_currency_amount NUMERIC(20, 2),
            exchange_rate NUMERIC(15, 6),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_fx_swaps_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_fx_swaps_dataset ON feeds.newyorkfed_fx_swaps(datasetid);
        CREATE INDEX idx_newyorkfed_fx_swaps_date ON feeds.newyorkfed_fx_swaps(swap_date);
        CREATE INDEX idx_newyorkfed_fx_swaps_currency ON feeds.newyorkfed_fx_swaps(currency_code);

        COMMENT ON TABLE feeds.newyorkfed_fx_swaps IS 'Central bank liquidity swaps and foreign exchange operations';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_fx_swaps TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_fx_swaps TO app_rw;
GRANT ALL ON feeds.newyorkfed_fx_swaps TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_fx_swaps_record_id_seq TO app_rw;

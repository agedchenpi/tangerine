-- Bank of England SONIA Rates Table
-- Sterling Overnight Index Average (SONIA) daily rates
-- Source: Bank of England Interactive Statistical Database (IADB)

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'bankofengland_sonia_rates') THEN
        CREATE TABLE feeds.bankofengland_sonia_rates (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Rate data
            effective_date DATE NOT NULL,
            rate_percent NUMERIC(10, 4),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT uq_boe_sonia_rates UNIQUE (effective_date, datasetid),
            CONSTRAINT fk_boe_sonia_rates_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_boe_sonia_rates_dataset ON feeds.bankofengland_sonia_rates(datasetid);
        CREATE INDEX idx_boe_sonia_rates_date ON feeds.bankofengland_sonia_rates(effective_date);

        COMMENT ON TABLE feeds.bankofengland_sonia_rates IS 'Sterling Overnight Index Average (SONIA) daily rates from Bank of England IADB';
        COMMENT ON COLUMN feeds.bankofengland_sonia_rates.effective_date IS 'Date for which the SONIA rate is effective';
        COMMENT ON COLUMN feeds.bankofengland_sonia_rates.rate_percent IS 'SONIA rate value in percentage';
    END IF;
END $$;

GRANT SELECT ON feeds.bankofengland_sonia_rates TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.bankofengland_sonia_rates TO app_rw;
GRANT ALL ON feeds.bankofengland_sonia_rates TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.bankofengland_sonia_rates_record_id_seq TO app_rw;

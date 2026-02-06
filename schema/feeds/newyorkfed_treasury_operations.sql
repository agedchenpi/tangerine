-- NewYorkFed Treasury Operations Table
-- Treasury securities operations including purchases, sales, and auction results
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_treasury_operations') THEN
        CREATE TABLE feeds.newyorkfed_treasury_operations (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Operation identification
            operation_date DATE NOT NULL,
            operation_type VARCHAR(50),
            cusip VARCHAR(9),
            security_description TEXT,

            -- Security details
            issue_date DATE,
            maturity_date DATE,
            coupon_rate NUMERIC(10, 4),
            security_term VARCHAR(20),

            -- Operation amounts
            operation_amount NUMERIC(20, 2),
            total_submitted NUMERIC(20, 2),
            total_accepted NUMERIC(20, 2),

            -- Pricing
            high_price NUMERIC(15, 6),
            low_price NUMERIC(15, 6),
            stop_out_rate NUMERIC(10, 4),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_treasury_operations_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_treasury_operations_dataset ON feeds.newyorkfed_treasury_operations(datasetid);
        CREATE INDEX idx_newyorkfed_treasury_operations_date ON feeds.newyorkfed_treasury_operations(operation_date);
        CREATE INDEX idx_newyorkfed_treasury_operations_type ON feeds.newyorkfed_treasury_operations(operation_type);
        CREATE INDEX idx_newyorkfed_treasury_operations_cusip ON feeds.newyorkfed_treasury_operations(cusip);

        COMMENT ON TABLE feeds.newyorkfed_treasury_operations IS 'Treasury securities operations including purchases, sales, and auction results';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_treasury_operations TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_treasury_operations TO app_rw;
GRANT ALL ON feeds.newyorkfed_treasury_operations TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_treasury_operations_record_id_seq TO app_rw;

-- NewYorkFed Securities Lending Table
-- Securities lending operations including program details and transactions
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_securities_lending') THEN
        CREATE TABLE feeds.newyorkfed_securities_lending (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Operation identification
            operation_date DATE NOT NULL,
            operation_type VARCHAR(50),
            cusip VARCHAR(9),
            security_description TEXT,

            -- Lending details
            loan_date DATE,
            return_date DATE,
            term_days INT,

            -- Amounts
            par_amount NUMERIC(20, 2),
            fee_rate NUMERIC(10, 4),

            -- Status
            operation_status VARCHAR(20),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_securities_lending_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_securities_lending_dataset ON feeds.newyorkfed_securities_lending(datasetid);
        CREATE INDEX idx_newyorkfed_securities_lending_date ON feeds.newyorkfed_securities_lending(operation_date);
        CREATE INDEX idx_newyorkfed_securities_lending_cusip ON feeds.newyorkfed_securities_lending(cusip);

        COMMENT ON TABLE feeds.newyorkfed_securities_lending IS 'Securities lending operations including program details and transaction data';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_securities_lending TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_securities_lending TO app_rw;
GRANT ALL ON feeds.newyorkfed_securities_lending TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_securities_lending_record_id_seq TO app_rw;

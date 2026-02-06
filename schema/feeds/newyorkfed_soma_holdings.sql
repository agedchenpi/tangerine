-- NewYorkFed SOMA Holdings Table
-- System Open Market Account holdings: Treasury, Agency Debt, Agency MBS
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_soma_holdings') THEN
        CREATE TABLE feeds.newyorkfed_soma_holdings (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Holding identification
            as_of_date DATE NOT NULL,
            security_type VARCHAR(50),
            cusip VARCHAR(9),
            security_description TEXT,

            -- Maturity info
            maturity_date DATE,

            -- Holdings values
            par_value NUMERIC(20, 2),
            current_face_value NUMERIC(20, 2),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_soma_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_soma_dataset ON feeds.newyorkfed_soma_holdings(datasetid);
        CREATE INDEX idx_newyorkfed_soma_date ON feeds.newyorkfed_soma_holdings(as_of_date);
        CREATE INDEX idx_newyorkfed_soma_type ON feeds.newyorkfed_soma_holdings(security_type);
        CREATE INDEX idx_newyorkfed_soma_cusip ON feeds.newyorkfed_soma_holdings(cusip);

        COMMENT ON TABLE feeds.newyorkfed_soma_holdings IS 'System Open Market Account (SOMA) holdings: Treasury securities, Agency Debt, Agency MBS';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_soma_holdings TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_soma_holdings TO app_rw;
GRANT ALL ON feeds.newyorkfed_soma_holdings TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_soma_holdings_record_id_seq TO app_rw;

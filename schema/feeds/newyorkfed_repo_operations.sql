-- NewYorkFed Repo Operations Table
-- Repurchase agreement (repo) and reverse repo operations
-- Source: Federal Reserve Bank of New York Markets API

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'newyorkfed_repo_operations') THEN
        CREATE TABLE feeds.newyorkfed_repo_operations (
            record_id SERIAL PRIMARY KEY,
            datasetid INT NOT NULL,

            -- Operation identification
            operation_date DATE NOT NULL,
            operation_type VARCHAR(20) NOT NULL,
            operation_id VARCHAR(50),

            -- Operation details
            maturity_date DATE,
            term_days INT,
            operation_status VARCHAR(20),

            -- Amounts
            amount_submitted NUMERIC(20, 2),
            amount_accepted NUMERIC(20, 2),
            award_rate NUMERIC(10, 4),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT fk_newyorkfed_repo_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_newyorkfed_repo_dataset ON feeds.newyorkfed_repo_operations(datasetid);
        CREATE INDEX idx_newyorkfed_repo_date ON feeds.newyorkfed_repo_operations(operation_date);
        CREATE INDEX idx_newyorkfed_repo_type ON feeds.newyorkfed_repo_operations(operation_type);

        COMMENT ON TABLE feeds.newyorkfed_repo_operations IS 'Federal Reserve repo and reverse repo operations';
    END IF;
END $$;

GRANT SELECT ON feeds.newyorkfed_repo_operations TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.newyorkfed_repo_operations TO app_rw;
GRANT ALL ON feeds.newyorkfed_repo_operations TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.newyorkfed_repo_operations_record_id_seq TO app_rw;

-- YFinance Global Market Indexes Price Table
-- Daily OHLCV data for 7 major global indexes from Yahoo Finance
-- Regions: Europe (FTSE, DAX, CAC 40, Euro Stoxx 50), Asia (Nikkei, Hang Seng, ASX)

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'yfinance_global_indexes') THEN
        CREATE TABLE feeds.yfinance_global_indexes (
            record_id    SERIAL PRIMARY KEY,
            datasetid    INT NOT NULL,

            -- Index identifiers
            symbol       VARCHAR(20) NOT NULL,   -- e.g. ^FTSE, ^N225, ^HSI
            index_name   VARCHAR(100),           -- e.g. FTSE 100, Nikkei 225
            region       VARCHAR(50),            -- Europe, Asia

            -- Price data
            price_date   DATE NOT NULL,
            open         NUMERIC(18, 6),
            high         NUMERIC(18, 6),
            low          NUMERIC(18, 6),
            close        NUMERIC(18, 6),
            volume       BIGINT,

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by   VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT uq_yfinance_global_indexes UNIQUE (symbol, price_date, datasetid),
            CONSTRAINT fk_yfinance_global_indexes_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_yfinance_global_indexes_dataset ON feeds.yfinance_global_indexes(datasetid);
        CREATE INDEX idx_yfinance_global_indexes_date ON feeds.yfinance_global_indexes(price_date);
        CREATE INDEX idx_yfinance_global_indexes_symbol ON feeds.yfinance_global_indexes(symbol);

        COMMENT ON TABLE feeds.yfinance_global_indexes IS 'Daily OHLCV prices for global market indexes from Yahoo Finance';
        COMMENT ON COLUMN feeds.yfinance_global_indexes.symbol IS 'Yahoo Finance ticker symbol, e.g. ^FTSE, ^N225, ^HSI';
        COMMENT ON COLUMN feeds.yfinance_global_indexes.index_name IS 'Full index name, e.g. FTSE 100, Nikkei 225';
        COMMENT ON COLUMN feeds.yfinance_global_indexes.region IS 'Geographic region: Europe or Asia';
    END IF;
END $$;

GRANT SELECT ON feeds.yfinance_global_indexes TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.yfinance_global_indexes TO app_rw;
GRANT ALL ON feeds.yfinance_global_indexes TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.yfinance_global_indexes_record_id_seq TO app_rw;

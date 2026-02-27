-- YFinance US Market Indexes Price Table
-- Daily OHLCV data for 8 major US indexes from Yahoo Finance

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'yfinance_us_indexes') THEN
        CREATE TABLE feeds.yfinance_us_indexes (
            record_id    SERIAL PRIMARY KEY,
            datasetid    INT NOT NULL,

            -- Index identifiers
            symbol       VARCHAR(20) NOT NULL,   -- e.g. ^GSPC, ^VIX, ^TNX
            index_name   VARCHAR(100),           -- e.g. S&P 500

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

            CONSTRAINT uq_yfinance_us_indexes UNIQUE (symbol, price_date, datasetid),
            CONSTRAINT fk_yfinance_us_indexes_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_yfinance_us_indexes_dataset ON feeds.yfinance_us_indexes(datasetid);
        CREATE INDEX idx_yfinance_us_indexes_date ON feeds.yfinance_us_indexes(price_date);
        CREATE INDEX idx_yfinance_us_indexes_symbol ON feeds.yfinance_us_indexes(symbol);

        COMMENT ON TABLE feeds.yfinance_us_indexes IS 'Daily OHLCV prices for US market indexes from Yahoo Finance';
        COMMENT ON COLUMN feeds.yfinance_us_indexes.symbol IS 'Yahoo Finance ticker symbol, e.g. ^GSPC, ^VIX, ^TNX';
        COMMENT ON COLUMN feeds.yfinance_us_indexes.index_name IS 'Full index name, e.g. S&P 500, CBOE Volatility Index';
    END IF;
END $$;

GRANT SELECT ON feeds.yfinance_us_indexes TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.yfinance_us_indexes TO app_rw;
GRANT ALL ON feeds.yfinance_us_indexes TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.yfinance_us_indexes_record_id_seq TO app_rw;

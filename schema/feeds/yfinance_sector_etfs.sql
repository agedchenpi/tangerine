-- YFinance US Sector ETFs Price Table
-- Daily OHLCV data for 11 SPDR sector ETFs from Yahoo Finance
-- Full coverage: Financials, Technology, Energy, Health Care, Industrials, Utilities,
--               Materials, Real Estate, Consumer Discretionary, Consumer Staples, Communication Services

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'yfinance_sector_etfs') THEN
        CREATE TABLE feeds.yfinance_sector_etfs (
            record_id    SERIAL PRIMARY KEY,
            datasetid    INT NOT NULL,

            -- ETF identifiers
            symbol       VARCHAR(20) NOT NULL,   -- e.g. XLF, XLK, XLE
            etf_name     VARCHAR(100),           -- e.g. Financial Select Sector SPDR
            sector       VARCHAR(50),            -- e.g. Financials, Technology, Energy

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

            CONSTRAINT uq_yfinance_sector_etfs UNIQUE (symbol, price_date, datasetid),
            CONSTRAINT fk_yfinance_sector_etfs_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_yfinance_sector_etfs_dataset ON feeds.yfinance_sector_etfs(datasetid);
        CREATE INDEX idx_yfinance_sector_etfs_date ON feeds.yfinance_sector_etfs(price_date);
        CREATE INDEX idx_yfinance_sector_etfs_symbol ON feeds.yfinance_sector_etfs(symbol);

        COMMENT ON TABLE feeds.yfinance_sector_etfs IS 'Daily OHLCV prices for US sector ETFs from Yahoo Finance';
        COMMENT ON COLUMN feeds.yfinance_sector_etfs.symbol IS 'Yahoo Finance ticker symbol, e.g. XLF, XLK, XLE';
        COMMENT ON COLUMN feeds.yfinance_sector_etfs.etf_name IS 'Full ETF name, e.g. Financial Select Sector SPDR';
        COMMENT ON COLUMN feeds.yfinance_sector_etfs.sector IS 'Market sector, e.g. Financials, Technology, Energy';
    END IF;
END $$;

GRANT SELECT ON feeds.yfinance_sector_etfs TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.yfinance_sector_etfs TO app_rw;
GRANT ALL ON feeds.yfinance_sector_etfs TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.yfinance_sector_etfs_record_id_seq TO app_rw;

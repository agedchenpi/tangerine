-- YFinance Commodity Futures Price Table
-- Daily OHLCV data for 13 commodity futures from Yahoo Finance
-- Categories: Energy, Metals, Agriculture, Livestock, Softs

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'yfinance_commodities') THEN
        CREATE TABLE feeds.yfinance_commodities (
            record_id    SERIAL PRIMARY KEY,
            datasetid    INT NOT NULL,

            -- Commodity identifiers
            symbol       VARCHAR(20) NOT NULL,   -- e.g. CL, GC, NG
            ticker       VARCHAR(20),            -- e.g. CL=F, GC=F
            category     VARCHAR(50),            -- Energy, Metals, Agriculture, Livestock, Softs

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

            CONSTRAINT uq_yfinance_commodities UNIQUE (symbol, price_date, datasetid),
            CONSTRAINT fk_yfinance_commodities_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_yfinance_commodities_dataset ON feeds.yfinance_commodities(datasetid);
        CREATE INDEX idx_yfinance_commodities_date ON feeds.yfinance_commodities(price_date);
        CREATE INDEX idx_yfinance_commodities_symbol ON feeds.yfinance_commodities(symbol);

        COMMENT ON TABLE feeds.yfinance_commodities IS 'Daily OHLCV prices for commodity futures from Yahoo Finance';
        COMMENT ON COLUMN feeds.yfinance_commodities.symbol IS 'Short commodity symbol, e.g. CL, GC, NG';
        COMMENT ON COLUMN feeds.yfinance_commodities.ticker IS 'Full Yahoo Finance ticker, e.g. CL=F, GC=F';
        COMMENT ON COLUMN feeds.yfinance_commodities.category IS 'Commodity category: Energy, Metals, Agriculture, Livestock, Softs';
    END IF;
END $$;

GRANT SELECT ON feeds.yfinance_commodities TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.yfinance_commodities TO app_rw;
GRANT ALL ON feeds.yfinance_commodities TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.yfinance_commodities_record_id_seq TO app_rw;

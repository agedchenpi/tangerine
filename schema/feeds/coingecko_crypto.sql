-- CoinGecko Cryptocurrency OHLC Price Table
-- Daily aggregated OHLC from 4-hour candles for top 5 cryptocurrencies
-- Source: CoinGecko free API /coins/{id}/ohlc endpoint

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'coingecko_crypto') THEN
        CREATE TABLE feeds.coingecko_crypto (
            record_id    SERIAL PRIMARY KEY,
            datasetid    INT NOT NULL,

            -- Coin identifiers
            symbol       VARCHAR(20) NOT NULL,   -- e.g. BTC, ETH, BNB, SOL, XRP
            coin_id      VARCHAR(50) NOT NULL,   -- e.g. bitcoin, ethereum, solana

            -- Price data
            price_date   DATE NOT NULL,
            open         NUMERIC(18, 6),
            high         NUMERIC(18, 6),
            low          NUMERIC(18, 6),
            close        NUMERIC(18, 6),

            -- Audit columns
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by   VARCHAR(50) DEFAULT CURRENT_USER,

            CONSTRAINT uq_coingecko_crypto UNIQUE (symbol, price_date, datasetid),
            CONSTRAINT fk_coingecko_crypto_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
        );

        CREATE INDEX idx_coingecko_crypto_dataset ON feeds.coingecko_crypto(datasetid);
        CREATE INDEX idx_coingecko_crypto_date ON feeds.coingecko_crypto(price_date);
        CREATE INDEX idx_coingecko_crypto_symbol ON feeds.coingecko_crypto(symbol);

        COMMENT ON TABLE feeds.coingecko_crypto IS 'Daily OHLC cryptocurrency prices from CoinGecko (top 5 coins)';
        COMMENT ON COLUMN feeds.coingecko_crypto.symbol IS 'Ticker symbol, e.g. BTC, ETH, BNB, SOL, XRP';
        COMMENT ON COLUMN feeds.coingecko_crypto.coin_id IS 'CoinGecko coin ID, e.g. bitcoin, ethereum';
    END IF;
END $$;

GRANT SELECT ON feeds.coingecko_crypto TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.coingecko_crypto TO app_rw;
GRANT ALL ON feeds.coingecko_crypto TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.coingecko_crypto_record_id_seq TO app_rw;

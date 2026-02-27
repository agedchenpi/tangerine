-- CoinGecko Import Configurations
-- Creates timportconfig records for CoinGecko cryptocurrency OHLC data
-- Also ensures required datasource and datasettype reference rows exist

DO $$
DECLARE
    v_strategy_id INT;
BEGIN
    -- Ensure data source exists
    INSERT INTO dba.tdatasource (sourcename, description, createdby)
    VALUES ('CoinGecko', 'CoinGecko cryptocurrency market data API', 'admin')
    ON CONFLICT (sourcename) DO NOTHING;

    -- Ensure dataset type exists
    INSERT INTO dba.tdatasettype (typename, description, createdby)
    VALUES ('Crypto', 'Cryptocurrency market data', 'admin')
    ON CONFLICT (typename) DO NOTHING;

    -- Get import strategy: "Import only (ignores new columns)" — we control the schema
    SELECT importstrategyid INTO v_strategy_id
    FROM dba.timportstrategy
    WHERE importstrategyid = 2
    LIMIT 1;

    -- Cryptocurrency OHLC (BTC, ETH, BNB, SOL, XRP)
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob, import_mode
    ) VALUES (
        'CoinGecko_Crypto', 'CoinGecko', 'Crypto',
        '/app/data/source/coingecko', '/app/data/archive/coingecko',
        'coingecko_crypto_.*\.json', 'JSON',
        'static', 'Crypto',
        'file_content', 'price_date', 'yyyy-MM-dd', NULL,
        'feeds.coingecko_crypto', v_strategy_id, TRUE, FALSE, 'file'
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        file_type = EXCLUDED.file_type,
        dateformat = EXCLUDED.dateformat,
        target_table = EXCLUDED.target_table,
        is_active = EXCLUDED.is_active;

    RAISE NOTICE 'Created 1 CoinGecko import configuration (Crypto OHLC)';
END $$;

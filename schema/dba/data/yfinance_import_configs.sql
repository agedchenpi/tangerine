-- YFinance Import Configurations
-- Creates timportconfig records for Yahoo Finance commodity futures data
-- Also ensures required datasource and datasettype reference rows exist

DO $$
DECLARE
    v_strategy_id INT;
BEGIN
    -- Ensure data source exists
    INSERT INTO dba.tdatasource (sourcename, description, createdby)
    VALUES ('YFinance', 'Yahoo Finance commodity futures market data', 'admin')
    ON CONFLICT (sourcename) DO NOTHING;

    -- Ensure dataset type exists
    INSERT INTO dba.tdatasettype (typename, description, createdby)
    VALUES ('Commodities', 'Commodity futures market data', 'admin')
    ON CONFLICT (typename) DO NOTHING;

    -- Get import strategy: "Import only (ignores new columns)" — we control the schema
    SELECT importstrategyid INTO v_strategy_id
    FROM dba.timportstrategy
    WHERE importstrategyid = 2
    LIMIT 1;

    -- Commodity Futures OHLCV (13 tickers: Energy, Metals, Agriculture, Livestock, Softs)
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob, import_mode
    ) VALUES (
        'YFinance_Commodities', 'YFinance', 'Commodities',
        '/app/data/source/yfinance', '/app/data/archive/yfinance',
        'yfinance_commodities_.*\.json', 'JSON',
        'static', 'Commodities',
        'file_content', 'price_date', 'yyyy-MM-dd', NULL,
        'feeds.yfinance_commodities', v_strategy_id, TRUE, FALSE, 'file'
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        file_type = EXCLUDED.file_type,
        dateformat = EXCLUDED.dateformat,
        target_table = EXCLUDED.target_table,
        is_active = EXCLUDED.is_active;

    RAISE NOTICE 'Created 1 YFinance import configuration (Commodities)';
END $$;

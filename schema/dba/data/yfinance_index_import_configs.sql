-- YFinance Index Import Configurations
-- Creates timportconfig records for US indexes, global indexes, and sector ETFs
-- Also ensures required datasource and datasettype reference rows exist

DO $$
DECLARE
    v_strategy_id INT;
BEGIN
    -- Ensure data source exists
    INSERT INTO dba.tdatasource (sourcename, description, createdby)
    VALUES ('YFinance', 'Yahoo Finance market data', 'admin')
    ON CONFLICT (sourcename) DO NOTHING;

    -- Ensure dataset type exists
    INSERT INTO dba.tdatasettype (typename, description, createdby)
    VALUES ('Index', 'Market index and benchmark data', 'admin')
    ON CONFLICT (typename) DO NOTHING;

    -- Get import strategy: "Import only (ignores new columns)" — we control the schema
    SELECT importstrategyid INTO v_strategy_id
    FROM dba.timportstrategy
    WHERE importstrategyid = 2
    LIMIT 1;

    -- US Indexes (8 tickers: S&P 500, NASDAQ, Dow, Russell, VIX, Treasuries)
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob, import_mode
    ) VALUES (
        'YFinance_US_Indexes', 'YFinance', 'Index',
        '/app/data/source/yfinance', '/app/data/archive/yfinance',
        'yfinance_us_indexes_.*\.json', 'JSON',
        'static', 'US Indexes',
        'file_content', 'price_date', 'yyyy-MM-dd', NULL,
        'feeds.yfinance_us_indexes', v_strategy_id, TRUE, FALSE, 'file'
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        file_type = EXCLUDED.file_type,
        dateformat = EXCLUDED.dateformat,
        target_table = EXCLUDED.target_table,
        is_active = EXCLUDED.is_active;

    -- Global Indexes (7 tickers: FTSE, DAX, CAC 40, Euro Stoxx, Nikkei, Hang Seng, ASX)
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob, import_mode
    ) VALUES (
        'YFinance_Global_Indexes', 'YFinance', 'Index',
        '/app/data/source/yfinance', '/app/data/archive/yfinance',
        'yfinance_global_indexes_.*\.json', 'JSON',
        'static', 'Global Indexes',
        'file_content', 'price_date', 'yyyy-MM-dd', NULL,
        'feeds.yfinance_global_indexes', v_strategy_id, TRUE, FALSE, 'file'
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        file_type = EXCLUDED.file_type,
        dateformat = EXCLUDED.dateformat,
        target_table = EXCLUDED.target_table,
        is_active = EXCLUDED.is_active;

    -- Sector ETFs (11 tickers: all 11 SPDR sector ETFs)
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob, import_mode
    ) VALUES (
        'YFinance_Sector_ETFs', 'YFinance', 'Index',
        '/app/data/source/yfinance', '/app/data/archive/yfinance',
        'yfinance_sector_etfs_.*\.json', 'JSON',
        'static', 'Sector ETFs',
        'file_content', 'price_date', 'yyyy-MM-dd', NULL,
        'feeds.yfinance_sector_etfs', v_strategy_id, TRUE, FALSE, 'file'
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        file_type = EXCLUDED.file_type,
        dateformat = EXCLUDED.dateformat,
        target_table = EXCLUDED.target_table,
        is_active = EXCLUDED.is_active;

    RAISE NOTICE 'Created 3 YFinance index import configurations (US Indexes, Global Indexes, Sector ETFs)';
END $$;

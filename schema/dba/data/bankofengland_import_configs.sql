-- BankOfEngland Import Configurations
-- Creates timportconfig records for Bank of England API endpoints
-- Uses collector pattern: bankofengland_collector.py --config-id N

DO $$
DECLARE
    v_strategy_id INT;
BEGIN
    -- Get default import strategy ID
    SELECT importstrategyid INTO v_strategy_id
    FROM dba.timportstrategy
    WHERE name = 'Add New Columns' OR importstrategyid = 1
    LIMIT 1;

    -- SONIA Daily Rates
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_rate_limit_rpm
    ) VALUES (
        'BankOfEngland_SONIA_Rates',
        'BankOfEngland', 'Rates',
        '/app/data/source/bankofengland',
        '/app/data/archive/bankofengland',
        'bankofengland_sonia_rates_.*\.json',
        'JSON',
        'static', 'SONIA_Rates',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.bankofengland_sonia_rates', v_strategy_id, TRUE, FALSE,
        'api',
        'https://www.bankofengland.co.uk',
        '/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes',
        'GET', 'csv', 30
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        file_type = EXCLUDED.file_type,
        dateformat = EXCLUDED.dateformat,
        api_base_url = EXCLUDED.api_base_url,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        is_active = EXCLUDED.is_active;

    RAISE NOTICE 'Created 1 BankOfEngland import configuration (SONIA Rates)';
END $$;

-- NewYorkFed Import Configurations
-- Creates timportconfig records for each NewYorkFed API endpoint
-- All configs now use the collector pattern: newyorkfed_collector.py --config-id N

-- Helper function to get data source and type IDs
DO $$
DECLARE
    v_datasource_id INT;
    v_strategy_id INT;
BEGIN
    -- Get NewYorkFed datasource ID
    SELECT datasourceid INTO v_datasource_id
    FROM dba.tdatasource
    WHERE sourcename = 'NewYorkFed';

    -- Get default import strategy ID (likely 1 for "Add New Columns")
    SELECT importstrategyid INTO v_strategy_id
    FROM dba.timportstrategy
    WHERE name = 'Add New Columns' OR importstrategyid = 1
    LIMIT 1;

    -- 1. Reference Rates - Latest
    INSERT INTO dba.timportconfig (
        config_name,
        datasource,
        datasettype,
        source_directory,
        archive_directory,
        file_pattern,
        file_type,
        metadata_label_source,
        metadata_label_location,
        dateconfig,
        datelocation,
        dateformat,
        delimiter,
        target_table,
        importstrategyid,
        is_active,
        is_blob,
        import_mode,
        api_base_url,
        api_endpoint_path,
        api_http_method,
        api_response_format,
        api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_ReferenceRates_Latest',
        'NewYorkFed',
        'ReferenceRates',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_referencerates_latest_.*\.json',
        'JSON',
        'static',
        'ReferenceRates_Latest',
        'static',
        NULL,
        'yyyy-MM-dd',
        NULL,
        'feeds.newyorkfed_reference_rates',
        v_strategy_id,
        TRUE,
        FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/rates/all/latest.{format}',
        'GET',
        'json',
        'refRates',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_base_url = EXCLUDED.api_base_url,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path,
        is_active = EXCLUDED.is_active;

    -- 2. Reference Rates - Search (30 days)
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_query_params, api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_ReferenceRates_Search',
        'NewYorkFed', 'ReferenceRates',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_referencerates_search_.*\.json',
        'JSON',
        'static', 'ReferenceRates_Search',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_reference_rates', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/rates/all/search.{format}',
        'GET', 'json', 'refRates',
        '{"startDate": "{{date-30d}}", "endDate": "{{date}}"}'::jsonb,
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern;

    -- 3. SOMA Holdings
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_SOMA_Holdings',
        'NewYorkFed', 'SOMAHoldings',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_soma_holdings_.*\.json',
        'JSON',
        'static', 'SOMA_Holdings',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_soma_holdings', v_strategy_id, TRUE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/soma/tsy/get/monthly.{format}',
        'GET', 'json', 'soma.holdings',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 4. Repo Operations
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_Repo_Operations',
        'NewYorkFed', 'RepoOperations',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_repo_operations_.*\.json',
        'JSON',
        'static', 'Repo_Operations',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_repo_operations', v_strategy_id, TRUE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/rp/all/all/results/lastTwoWeeks.{format}',
        'GET', 'json', 'repo.operations',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 5. Reverse Repo Operations
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_ReverseRepo_Operations',
        'NewYorkFed', 'RepoOperations',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_reverserepo_operations_.*\.json',
        'JSON',
        'static', 'ReverseRepo_Operations',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_repo_operations', v_strategy_id, TRUE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/rp/reverserepo/all/results/lastTwoWeeks.{format}',
        'GET', 'json', 'repo.operations',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 6. Agency MBS
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_Agency_MBS',
        'NewYorkFed', 'AgencyMBS',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_agency_mbs_.*\.json',
        'JSON',
        'static', 'Agency_MBS',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_agency_mbs', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/ambs/all/announcements/summary/latest.{format}',
        'GET', 'json', 'ambs.auctions',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 7. FX Swaps
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_FX_Swaps',
        'NewYorkFed', 'FXSwaps',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_fx_swaps_.*\.json',
        'JSON',
        'static', 'FX_Swaps',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_fx_swaps', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/fxs/all/latest.{format}',
        'GET', 'json', 'fxSwaps.operations',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 8. Securities Lending
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_Securities_Lending',
        'NewYorkFed', 'SecuritiesLending',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_securities_lending_.*\.json',
        'JSON',
        'static', 'Securities_Lending',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_securities_lending', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/seclending/all/results/summary/latest.{format}',
        'GET', 'json', 'seclending.operations',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 9. Guide Sheets
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_Guide_Sheets',
        'NewYorkFed', 'GuideSheets',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_guide_sheets_.*\.json',
        'JSON',
        'static', 'Guide_Sheets',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_guide_sheets', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/guidesheets/si/latest.{format}',
        'GET', 'json', 'guidesheet.si',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 10. PD Statistics
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_PD_Statistics',
        'NewYorkFed', 'PDStatistics',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_pd_statistics_.*\.json',
        'JSON',
        'static', 'PD_Statistics',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_pd_statistics', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/pd/get/all/timeseries.{format}',
        'GET', 'json', 'pd',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 11. Market Share
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_Market_Share',
        'NewYorkFed', 'MarketShare',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_market_share_.*\.json',
        'JSON',
        'static', 'Market_Share',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_market_share', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/marketshare/qtrly/latest.{format}',
        'GET', 'json', 'marketshare',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 12. Treasury Operations
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_Treasury_Operations',
        'NewYorkFed', 'TreasuryOperations',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_treasury_operations_.*\.json',
        'JSON',
        'static', 'Treasury_Operations',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_treasury_operations', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/tsy/all/results/summary/lastTwoWeeks.{format}',
        'GET', 'json', 'treasury.auctions',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    -- 13. Counterparties
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_response_root_path,
        api_rate_limit_rpm
    ) VALUES (
        'NewYorkFed_Counterparties',
        'NewYorkFed', 'FXCounterparties',
        '/app/data/source/newyorkfed',
        '/app/data/archive/newyorkfed',
        'newyorkfed_counterparties_.*\.json',
        'JSON',
        'static', 'Counterparties',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_counterparties', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/fxs/list/counterparties.{format}',
        'GET', 'json', 'fxSwaps.counterparties',
        60
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
        api_response_root_path = EXCLUDED.api_response_root_path;

    RAISE NOTICE 'Created 13 NewYorkFed import configurations';
    RAISE NOTICE '  - 4 active (ReferenceRates Latest, SOMA, Repo, ReverseRepo)';
    RAISE NOTICE '  - 9 inactive (ReferenceRates Search, Agency MBS, FX Swaps, Securities Lending, Guide Sheets, PD Stats, Market Share, Treasury, Counterparties)';
END $$;

-- NewYorkFed Import Configurations
-- Creates timportconfig records for each NewYorkFed API endpoint

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
        '',  -- Not used for API imports
        '',  -- Not used for API imports
        '',  -- Not used for API imports
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
        api_base_url = EXCLUDED.api_base_url,
        api_endpoint_path = EXCLUDED.api_endpoint_path,
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
        '', '', '', 'JSON',
        'static', 'ReferenceRates_Search',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_reference_rates', v_strategy_id, FALSE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/rates/all/search.{format}',
        'GET', 'json', 'refRates',
        '{"startDate": "{{date-30d}}", "endDate": "{{date}}"}'::jsonb,
        60
    ) ON CONFLICT (config_name) DO NOTHING;

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
        '', '', '', 'JSON',
        'static', 'SOMA_Holdings',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_soma_holdings', v_strategy_id, TRUE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/soma/summary.{format}',
        'GET', 'json', 'soma',
        60
    ) ON CONFLICT (config_name) DO NOTHING;

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
        '', '', '', 'JSON',
        'static', 'Repo_Operations',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_repo_operations', v_strategy_id, TRUE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/repo/results/search.{format}',
        'GET', 'json', 'repo',
        60
    ) ON CONFLICT (config_name) DO NOTHING;

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
        '', '', '', 'JSON',
        'static', 'ReverseRepo_Operations',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.newyorkfed_repo_operations', v_strategy_id, TRUE, FALSE,
        'api',
        'https://markets.newyorkfed.org',
        '/api/reverserepo/results/search.{format}',
        'GET', 'json', 'reverserepo',
        60
    ) ON CONFLICT (config_name) DO NOTHING;

    -- 6-10: Stub configs for remaining endpoints
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob,
        import_mode, api_base_url, api_endpoint_path,
        api_http_method, api_response_format, api_rate_limit_rpm
    ) VALUES
        ('NewYorkFed_Agency_MBS', 'NewYorkFed', 'AgencyMBS',
         '', '', '', 'JSON', 'static', 'Agency_MBS',
         'static', NULL, 'yyyy-MM-dd', NULL,
         'feeds.newyorkfed_agency_mbs', v_strategy_id, FALSE, FALSE,
         'api', 'https://markets.newyorkfed.org', '/api/ambs/...', 'GET', 'json', 60),

        ('NewYorkFed_FX_Swaps', 'NewYorkFed', 'FXSwaps',
         '', '', '', 'JSON', 'static', 'FX_Swaps',
         'static', NULL, 'yyyy-MM-dd', NULL,
         'feeds.newyorkfed_fx_swaps', v_strategy_id, FALSE, FALSE,
         'api', 'https://markets.newyorkfed.org', '/api/fxswaps/...', 'GET', 'json', 60),

        ('NewYorkFed_Guide_Sheets', 'NewYorkFed', 'GuideSheets',
         '', '', '', 'JSON', 'static', 'Guide_Sheets',
         'static', NULL, 'yyyy-MM-dd', NULL,
         'feeds.newyorkfed_guide_sheets', v_strategy_id, FALSE, FALSE,
         'api', 'https://markets.newyorkfed.org', '/api/guidesheets/...', 'GET', 'json', 60),

        ('NewYorkFed_PD_Statistics', 'NewYorkFed', 'PDStatistics',
         '', '', '', 'JSON', 'static', 'PD_Statistics',
         'static', NULL, 'yyyy-MM-dd', NULL,
         'feeds.newyorkfed_pd_statistics', v_strategy_id, FALSE, FALSE,
         'api', 'https://markets.newyorkfed.org', '/api/pd/...', 'GET', 'json', 60),

        ('NewYorkFed_Market_Share', 'NewYorkFed', 'MarketShare',
         '', '', '', 'JSON', 'static', 'Market_Share',
         'static', NULL, 'yyyy-MM-dd', NULL,
         'feeds.newyorkfed_market_share', v_strategy_id, FALSE, FALSE,
         'api', 'https://markets.newyorkfed.org', '/api/marketshare/...', 'GET', 'json', 60),

        ('NewYorkFed_Securities_Lending', 'NewYorkFed', 'SecuritiesLending',
         '', '', '', 'JSON', 'static', 'Securities_Lending',
         'static', NULL, 'yyyy-MM-dd', NULL,
         'feeds.newyorkfed_securities_lending', v_strategy_id, FALSE, FALSE,
         'api', 'https://markets.newyorkfed.org', '/api/seclending/...', 'GET', 'json', 60),

        ('NewYorkFed_Treasury_Operations', 'NewYorkFed', 'TreasuryOperations',
         '', '', '', 'JSON', 'static', 'Treasury_Operations',
         'static', NULL, 'yyyy-MM-dd', NULL,
         'feeds.newyorkfed_treasury_operations', v_strategy_id, FALSE, FALSE,
         'api', 'https://markets.newyorkfed.org', '/api/treasury/...', 'GET', 'json', 60)
    ON CONFLICT (config_name) DO NOTHING;

    RAISE NOTICE 'Created 10 NewYorkFed import configurations';
    RAISE NOTICE '  - 4 active (ReferenceRates, SOMA, Repo, ReverseRepo)';
    RAISE NOTICE '  - 6 inactive (stubs awaiting endpoint details)';
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'timportconfig') THEN
        CREATE TABLE dba.timportconfig (
            config_id SERIAL PRIMARY KEY,
            config_name VARCHAR(100) NOT NULL UNIQUE,
            datasource VARCHAR(100) NOT NULL,
            datasettype VARCHAR(100) NOT NULL,
            source_directory VARCHAR(255) NOT NULL,
            archive_directory VARCHAR(255) NOT NULL,
            file_pattern VARCHAR(255) NOT NULL,
            file_type VARCHAR(10) NOT NULL CHECK (file_type IN ('CSV', 'XLS', 'XLSX', 'JSON', 'XML')),
            metadata_label_source VARCHAR(50) NOT NULL CHECK (metadata_label_source IN ('filename', 'file_content', 'static')),
            metadata_label_location VARCHAR(255),
            dateconfig VARCHAR(50) NOT NULL CHECK (dateconfig IN ('filename', 'file_content', 'static')),
            datelocation VARCHAR(255),
            dateformat VARCHAR(50),
            delimiter VARCHAR(10),
            target_table VARCHAR(100) NOT NULL,
            importstrategyid INT NOT NULL DEFAULT 1,
            is_active BOOLEAN DEFAULT TRUE,
            is_blob BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- API import columns (nullable for backward compatibility)
            import_mode VARCHAR(20) DEFAULT 'file' CHECK (import_mode IN ('file', 'api')),
            api_base_url VARCHAR(255),
            api_endpoint_path VARCHAR(255),
            api_http_method VARCHAR(10) DEFAULT 'GET',
            api_response_format VARCHAR(10) DEFAULT 'json',
            api_query_params JSONB,
            api_request_headers JSONB,
            api_auth_type VARCHAR(50) DEFAULT 'none',
            api_auth_credentials JSONB,
            api_rate_limit_rpm INT,
            api_response_root_path VARCHAR(255),

            CONSTRAINT fk_importstrategyid FOREIGN KEY (importstrategyid) REFERENCES dba.timportstrategy(importstrategyid),
            CONSTRAINT valid_directories CHECK (
                (import_mode = 'file' AND source_directory != archive_directory
                    AND source_directory ~ '^/.*[^/]$' AND archive_directory ~ '^/.*[^/]$')
                OR (import_mode = 'api')
            ),
            CONSTRAINT valid_api_config CHECK (
                (import_mode = 'file') OR
                (import_mode = 'api' AND api_base_url IS NOT NULL AND api_endpoint_path IS NOT NULL)
            ),
            CONSTRAINT valid_date CHECK (
                (dateconfig = 'filename' AND datelocation ~ '^[0-9]+$' AND delimiter IS NOT NULL AND dateformat IS NOT NULL)
                OR (dateconfig = 'file_content' AND datelocation ~ '^[a-zA-Z0-9_]+$' AND dateformat IS NOT NULL)
                OR (dateconfig = 'static' AND dateformat IS NOT NULL)
            )
        );
        COMMENT ON TABLE dba.timportconfig IS 'Configuration table for importing files (CSV, XLS, XLSX, JSON, XML) into the database, specifying file patterns, directories, metadata extraction, and import strategy.';
        COMMENT ON COLUMN dba.timportconfig.config_id IS 'Unique identifier for the configuration.';
        COMMENT ON COLUMN dba.timportconfig.config_name IS 'Descriptive name of the configuration.';
        COMMENT ON COLUMN dba.timportconfig.datasource IS 'Descriptive name of the data source (must exist in dba.tdatasource).';
        COMMENT ON COLUMN dba.timportconfig.datasettype IS 'Descriptive name of the dataset type (must exist in dba.tdatasettype).';
        COMMENT ON COLUMN dba.timportconfig.source_directory IS 'Absolute path to the directory containing input files.';
        COMMENT ON COLUMN dba.timportconfig.archive_directory IS 'Absolute path to the directory where files are archived after processing.';
        COMMENT ON COLUMN dba.timportconfig.file_pattern IS 'Pattern to match files (glob or regex, e.g., "*.csv" or "\d{8}T\d{6}_.*\.csv").';
        COMMENT ON COLUMN dba.timportconfig.file_type IS 'Type of file to process (CSV, XLS, XLSX, JSON, XML).';
        COMMENT ON COLUMN dba.timportconfig.metadata_label_source IS 'Source of the metadata label (filename, file_content, or static).';
        COMMENT ON COLUMN dba.timportconfig.metadata_label_location IS 'Location details for metadata extraction (position index for filename, column name for file_content, user-defined value for static).';
        COMMENT ON COLUMN dba.timportconfig.dateconfig IS 'Source of date metadata (filename, file_content, or static).';
        COMMENT ON COLUMN dba.timportconfig.datelocation IS 'Location details for date extraction (position index for filename, column name for file_content, fixed date for static).';
        COMMENT ON COLUMN dba.timportconfig.dateformat IS 'Format of the date (e.g., yyyyMMddTHHmmss, yyyy-MM-dd).';
        COMMENT ON COLUMN dba.timportconfig.delimiter IS 'Delimiter used for parsing filenames (e.g., _, NULL if not applicable).';
        COMMENT ON COLUMN dba.timportconfig.target_table IS 'Target database table for the imported data (schema.table format).';
        COMMENT ON COLUMN dba.timportconfig.importstrategyid IS 'Foreign key to timportstrategy, defining how to handle column mismatches.';
        COMMENT ON COLUMN dba.timportconfig.is_active IS 'Flag indicating whether the configuration is active.';
        COMMENT ON COLUMN dba.timportconfig.is_blob IS 'Flag indicating whether JSON/XML files should be stored as blobs (TRUE) or parsed as relational data (FALSE). Only applies to JSON and XML file types.';
        COMMENT ON COLUMN dba.timportconfig.created_at IS 'Timestamp when the configuration was created.';
        COMMENT ON COLUMN dba.timportconfig.last_modified_at IS 'Timestamp when the configuration was last modified.';

        -- API column comments
        COMMENT ON COLUMN dba.timportconfig.import_mode IS 'Import mode: "file" for file-based imports, "api" for API-based imports';
        COMMENT ON COLUMN dba.timportconfig.api_base_url IS 'Base URL for API (e.g., "https://api.example.com")';
        COMMENT ON COLUMN dba.timportconfig.api_endpoint_path IS 'API endpoint path (e.g., "/v1/data" or "/api/rates/{format}")';
        COMMENT ON COLUMN dba.timportconfig.api_http_method IS 'HTTP method (GET, POST, PUT, DELETE)';
        COMMENT ON COLUMN dba.timportconfig.api_response_format IS 'Expected response format (json, xml, csv)';
        COMMENT ON COLUMN dba.timportconfig.api_query_params IS 'Query parameters as JSON object';
        COMMENT ON COLUMN dba.timportconfig.api_request_headers IS 'Custom request headers as JSON object';
        COMMENT ON COLUMN dba.timportconfig.api_auth_type IS 'Authentication type (none, api_key, oauth, bearer)';
        COMMENT ON COLUMN dba.timportconfig.api_auth_credentials IS 'Authentication credentials as JSON object';
        COMMENT ON COLUMN dba.timportconfig.api_rate_limit_rpm IS 'Rate limit in requests per minute';
        COMMENT ON COLUMN dba.timportconfig.api_response_root_path IS 'JSON path to extract data (e.g., "data.results")';
    END IF;
END $$;
GRANT SELECT ON dba.timportconfig TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.timportconfig TO app_rw;
GRANT ALL ON dba.timportconfig TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.timportconfig_config_id_seq TO app_rw, app_ro;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tinboxconfig') THEN
        CREATE TABLE dba.tinboxconfig (
            inbox_config_id SERIAL PRIMARY KEY,
            config_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            subject_pattern VARCHAR(255),
            sender_pattern VARCHAR(255),
            attachment_pattern VARCHAR(255) NOT NULL,
            target_directory VARCHAR(255) NOT NULL DEFAULT '/app/data/source/inbox',
            date_prefix_format VARCHAR(50) DEFAULT 'yyyyMMdd',
            save_eml BOOLEAN DEFAULT FALSE,
            mark_processed BOOLEAN DEFAULT TRUE,
            processed_label VARCHAR(100) DEFAULT 'Processed',
            error_label VARCHAR(100) DEFAULT 'ErrorFolder',
            linked_import_config_id INT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_run_at TIMESTAMP,
            CONSTRAINT fk_linked_import_config FOREIGN KEY (linked_import_config_id)
                REFERENCES dba.timportconfig(config_id) ON DELETE SET NULL,
            CONSTRAINT valid_target_directory CHECK (target_directory ~ '^/.*[^/]$'),
            CONSTRAINT valid_attachment_pattern CHECK (attachment_pattern IS NOT NULL AND LENGTH(attachment_pattern) > 0)
        );
        COMMENT ON TABLE dba.tinboxconfig IS 'Configuration for Gmail inbox processing rules. Defines patterns to match emails and where to save attachments.';
        COMMENT ON COLUMN dba.tinboxconfig.inbox_config_id IS 'Unique identifier for the inbox configuration.';
        COMMENT ON COLUMN dba.tinboxconfig.config_name IS 'Descriptive name for the inbox rule.';
        COMMENT ON COLUMN dba.tinboxconfig.description IS 'Optional description of the inbox rule purpose.';
        COMMENT ON COLUMN dba.tinboxconfig.subject_pattern IS 'Regex pattern to match email subject lines (e.g., "Daily Report.*").';
        COMMENT ON COLUMN dba.tinboxconfig.sender_pattern IS 'Regex pattern to match sender email addresses.';
        COMMENT ON COLUMN dba.tinboxconfig.attachment_pattern IS 'Glob pattern to match attachment filenames (e.g., "*.csv", "report_*.xlsx").';
        COMMENT ON COLUMN dba.tinboxconfig.target_directory IS 'Directory where attachments are saved. Must be absolute path without trailing slash.';
        COMMENT ON COLUMN dba.tinboxconfig.date_prefix_format IS 'Date format for filename prefix (e.g., "yyyyMMdd"). Applied to downloaded files.';
        COMMENT ON COLUMN dba.tinboxconfig.save_eml IS 'If TRUE, saves the original .eml file alongside attachments.';
        COMMENT ON COLUMN dba.tinboxconfig.mark_processed IS 'If TRUE, applies Gmail label to processed emails.';
        COMMENT ON COLUMN dba.tinboxconfig.processed_label IS 'Gmail label to apply to successfully processed emails.';
        COMMENT ON COLUMN dba.tinboxconfig.error_label IS 'Gmail label for emails that could not be matched to any rule.';
        COMMENT ON COLUMN dba.tinboxconfig.linked_import_config_id IS 'Optional foreign key to timportconfig for automatic file processing after download.';
        COMMENT ON COLUMN dba.tinboxconfig.is_active IS 'Flag indicating whether the inbox rule is active.';
        COMMENT ON COLUMN dba.tinboxconfig.created_at IS 'Timestamp when the configuration was created.';
        COMMENT ON COLUMN dba.tinboxconfig.last_modified_at IS 'Timestamp when the configuration was last modified.';
        COMMENT ON COLUMN dba.tinboxconfig.last_run_at IS 'Timestamp of the last inbox processing run for this rule.';
    END IF;
END $$;
GRANT SELECT ON dba.tinboxconfig TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tinboxconfig TO app_rw;
GRANT ALL ON dba.tinboxconfig TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tinboxconfig_inbox_config_id_seq TO app_rw, app_ro;

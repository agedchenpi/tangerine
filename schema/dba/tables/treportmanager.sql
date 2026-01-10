DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'treportmanager') THEN
        CREATE TABLE dba.treportmanager (
            report_id SERIAL PRIMARY KEY,
            report_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            recipients TEXT NOT NULL,
            cc_recipients TEXT,
            subject_line VARCHAR(255) NOT NULL,
            body_template TEXT NOT NULL,
            output_format VARCHAR(50) NOT NULL DEFAULT 'html'
                CHECK (output_format IN ('html', 'csv', 'excel', 'html_csv', 'html_excel')),
            attachment_filename VARCHAR(100),
            schedule_id INT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_run_at TIMESTAMP,
            last_run_status VARCHAR(50) CHECK (last_run_status IS NULL OR last_run_status IN ('Success', 'Failed')),
            CONSTRAINT fk_schedule FOREIGN KEY (schedule_id)
                REFERENCES dba.tscheduler(scheduler_id) ON DELETE SET NULL,
            CONSTRAINT valid_recipients CHECK (recipients IS NOT NULL AND LENGTH(recipients) > 0),
            CONSTRAINT valid_subject CHECK (subject_line IS NOT NULL AND LENGTH(subject_line) > 0),
            CONSTRAINT valid_body CHECK (body_template IS NOT NULL AND LENGTH(body_template) > 0)
        );
        COMMENT ON TABLE dba.treportmanager IS 'Configuration for automated report generation and email delivery. Supports SQL-based data grids in email body and file attachments.';
        COMMENT ON COLUMN dba.treportmanager.report_id IS 'Unique identifier for the report configuration.';
        COMMENT ON COLUMN dba.treportmanager.report_name IS 'Descriptive name for the report.';
        COMMENT ON COLUMN dba.treportmanager.description IS 'Optional description of the report purpose.';
        COMMENT ON COLUMN dba.treportmanager.recipients IS 'Comma-separated list of email addresses to receive the report.';
        COMMENT ON COLUMN dba.treportmanager.cc_recipients IS 'Optional comma-separated list of CC email addresses.';
        COMMENT ON COLUMN dba.treportmanager.subject_line IS 'Email subject line for the report.';
        COMMENT ON COLUMN dba.treportmanager.body_template IS 'HTML template for the report body. Use {{SQL:query}} blocks for dynamic data grids.';
        COMMENT ON COLUMN dba.treportmanager.output_format IS 'Output format: html (inline tables), csv/excel (attachment only), html_csv/html_excel (both).';
        COMMENT ON COLUMN dba.treportmanager.attachment_filename IS 'Base filename for attachments (without extension). Extension added based on format.';
        COMMENT ON COLUMN dba.treportmanager.schedule_id IS 'Optional foreign key to tscheduler for automated report scheduling.';
        COMMENT ON COLUMN dba.treportmanager.is_active IS 'Flag indicating whether the report is active.';
        COMMENT ON COLUMN dba.treportmanager.created_at IS 'Timestamp when the report was created.';
        COMMENT ON COLUMN dba.treportmanager.last_modified_at IS 'Timestamp when the report was last modified.';
        COMMENT ON COLUMN dba.treportmanager.last_run_at IS 'Timestamp of the last report execution.';
        COMMENT ON COLUMN dba.treportmanager.last_run_status IS 'Status of the last run: Success or Failed.';
    END IF;
END $$;
GRANT SELECT ON dba.treportmanager TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.treportmanager TO app_rw;
GRANT ALL ON dba.treportmanager TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.treportmanager_report_id_seq TO app_rw, app_ro;

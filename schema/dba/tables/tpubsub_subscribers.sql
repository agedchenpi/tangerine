DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tpubsub_subscribers') THEN
        CREATE TABLE dba.tpubsub_subscribers (
            subscriber_id SERIAL PRIMARY KEY,
            subscriber_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('file_received', 'email_received', 'import_complete', 'report_sent', 'custom')),
            event_filter JSONB DEFAULT '{}',
            job_type VARCHAR(50) NOT NULL CHECK (job_type IN ('import', 'inbox_processor', 'report', 'custom')),
            config_id INT,
            script_path VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_triggered_at TIMESTAMP,
            trigger_count INT DEFAULT 0,
            CONSTRAINT valid_custom_subscriber CHECK (
                (job_type = 'custom' AND script_path IS NOT NULL)
                OR (job_type != 'custom')
            ),
            CONSTRAINT valid_config_reference CHECK (
                (job_type IN ('import', 'inbox_processor', 'report') AND config_id IS NOT NULL)
                OR (job_type = 'custom')
            )
        );

        -- Create indexes for efficient querying
        CREATE INDEX idx_pubsub_subscribers_event_type ON dba.tpubsub_subscribers(event_type) WHERE is_active = TRUE;
        CREATE INDEX idx_pubsub_subscribers_active ON dba.tpubsub_subscribers(is_active);

        COMMENT ON TABLE dba.tpubsub_subscribers IS 'Event-to-job mappings for pub-sub system. Defines which jobs run when specific events occur.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.subscriber_id IS 'Unique identifier for the subscriber.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.subscriber_name IS 'Descriptive name for the subscriber.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.description IS 'Optional description of what this subscriber does.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.event_type IS 'Type of event to subscribe to: file_received, email_received, import_complete, report_sent, or custom.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.event_filter IS 'JSON filter to match specific events (e.g., {"file_pattern": "*.csv"}).';
        COMMENT ON COLUMN dba.tpubsub_subscribers.job_type IS 'Type of job to trigger: import, inbox_processor, report, or custom.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.config_id IS 'Reference to related configuration (import config_id, inbox_config_id, or report_id).';
        COMMENT ON COLUMN dba.tpubsub_subscribers.script_path IS 'Path to Python script for custom job type (required for custom jobs).';
        COMMENT ON COLUMN dba.tpubsub_subscribers.is_active IS 'Flag indicating whether the subscriber is active.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.created_at IS 'Timestamp when the subscriber was created.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.last_modified_at IS 'Timestamp when the subscriber was last modified.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.last_triggered_at IS 'Timestamp of the last event trigger.';
        COMMENT ON COLUMN dba.tpubsub_subscribers.trigger_count IS 'Total number of times this subscriber has been triggered.';
    END IF;
END $$;
GRANT SELECT ON dba.tpubsub_subscribers TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tpubsub_subscribers TO app_rw;
GRANT ALL ON dba.tpubsub_subscribers TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tpubsub_subscribers_subscriber_id_seq TO app_rw, app_ro;

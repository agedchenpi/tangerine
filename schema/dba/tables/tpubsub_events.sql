DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tpubsub_events') THEN
        CREATE TABLE dba.tpubsub_events (
            event_id SERIAL PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('file_received', 'email_received', 'import_complete', 'report_sent', 'custom')),
            event_source VARCHAR(100) NOT NULL,
            event_data JSONB NOT NULL DEFAULT '{}',
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
            priority INT DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            retry_count INT DEFAULT 0,
            max_retries INT DEFAULT 3
        );

        -- Create indexes for efficient querying
        CREATE INDEX idx_pubsub_events_status ON dba.tpubsub_events(status) WHERE status IN ('pending', 'processing');
        CREATE INDEX idx_pubsub_events_type ON dba.tpubsub_events(event_type);
        CREATE INDEX idx_pubsub_events_created ON dba.tpubsub_events(created_at DESC);

        COMMENT ON TABLE dba.tpubsub_events IS 'Event queue for pub-sub system. Stores events that trigger automated jobs.';
        COMMENT ON COLUMN dba.tpubsub_events.event_id IS 'Unique identifier for the event.';
        COMMENT ON COLUMN dba.tpubsub_events.event_type IS 'Type of event: file_received, email_received, import_complete, report_sent, or custom.';
        COMMENT ON COLUMN dba.tpubsub_events.event_source IS 'Source that generated the event (e.g., file path, email ID, job name).';
        COMMENT ON COLUMN dba.tpubsub_events.event_data IS 'JSON payload with event-specific data (filename, metadata, etc.).';
        COMMENT ON COLUMN dba.tpubsub_events.status IS 'Processing status: pending, processing, completed, failed, or cancelled.';
        COMMENT ON COLUMN dba.tpubsub_events.priority IS 'Event priority (1=highest, 10=lowest). Default is 5.';
        COMMENT ON COLUMN dba.tpubsub_events.created_at IS 'Timestamp when the event was created.';
        COMMENT ON COLUMN dba.tpubsub_events.processed_at IS 'Timestamp when processing started.';
        COMMENT ON COLUMN dba.tpubsub_events.completed_at IS 'Timestamp when processing completed (success or failure).';
        COMMENT ON COLUMN dba.tpubsub_events.error_message IS 'Error details if event processing failed.';
        COMMENT ON COLUMN dba.tpubsub_events.retry_count IS 'Number of retry attempts made.';
        COMMENT ON COLUMN dba.tpubsub_events.max_retries IS 'Maximum number of retries before marking as failed.';
    END IF;
END $$;
GRANT SELECT ON dba.tpubsub_events TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tpubsub_events TO app_rw;
GRANT ALL ON dba.tpubsub_events TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tpubsub_events_event_id_seq TO app_rw, app_ro;

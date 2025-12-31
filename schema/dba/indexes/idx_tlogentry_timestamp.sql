DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'dba' AND indexname = 'idx_tlogentry_timestamp') THEN
        CREATE INDEX idx_tlogentry_timestamp ON dba.tlogentry (timestamp);
    END IF;
END   $$;
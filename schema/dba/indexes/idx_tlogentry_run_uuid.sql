DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'dba' AND indexname = 'idx_tlogentry_run_uuid') THEN
        CREATE INDEX idx_tlogentry_run_uuid ON dba.tlogentry (run_uuid);
    END IF;
END   $$;
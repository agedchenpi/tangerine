DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'dba' AND indexname = 'idx_tcalendardays_fulldate') THEN
        CREATE INDEX idx_tcalendardays_fulldate ON dba.tcalendardays (fulldate);
    END IF;
END   $$;
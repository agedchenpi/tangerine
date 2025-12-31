DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'dba' AND indexname = 'idx_tcalendardays_isbusday') THEN
        CREATE INDEX idx_tcalendardays_isbusday ON dba.tcalendardays (isbusday);
    END IF;
END   $$;
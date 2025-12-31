DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'ttriggerenforcesingleactivedataset' AND tgrelid = (SELECT oid FROM pg_class WHERE relname = 'tdataset' AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba'))) THEN
        CREATE TRIGGER ttriggerenforcesingleactivedataset
        AFTER INSERT OR UPDATE OF isactive
        ON dba.tdataset
        FOR EACH ROW
        WHEN (NEW.isactive = TRUE)
        EXECUTE FUNCTION dba.fenforcesingleactivedataset();
    END IF;
END   $$;
DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_event_trigger WHERE evtname = 'logddl') THEN
        CREATE EVENT TRIGGER logddl
        ON ddl_command_end
        EXECUTE FUNCTION dba.flogddlchanges();
    END IF;
END   $$;
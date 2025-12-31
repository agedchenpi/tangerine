DO $$  
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'flogddlchanges'
    ) THEN
        CREATE FUNCTION dba.flogddlchanges()
        RETURNS EVENT_TRIGGER AS $$  
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN SELECT * FROM pg_event_trigger_ddl_commands() LOOP
                INSERT INTO dba.tddllogs (eventtime, eventtype, schemaname, objectname, objecttype, sqlstatement)
                VALUES (CURRENT_TIMESTAMP, r.command_tag, COALESCE(r.schema_name, 'dba'), r.object_identity, r.object_type, r.command_tag);
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
    END IF;
END $$;
GRANT EXECUTE ON FUNCTION dba.flogddlchanges() TO app_rw, app_ro;
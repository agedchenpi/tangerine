DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba') AND proname = 'fenforcesingleactivedataset') THEN
        CREATE FUNCTION dba.fenforcesingleactivedataset()
        RETURNS TRIGGER AS $BODY$
        BEGIN
            IF NEW.isactive = TRUE THEN
                UPDATE dba.tdataset
                SET isactive = FALSE,
                    effthrudate = CURRENT_TIMESTAMP,
                    datastatusid = (SELECT datastatusid FROM dba.tdatastatus WHERE statusname = 'Inactive')
                WHERE label = NEW.label
                  AND datasettypeid = NEW.datasettypeid
                  AND datasetdate = NEW.datasetdate
                  AND datasetid != NEW.datasetid
                  AND isactive = TRUE;
            END IF;
            RETURN NEW;
        END;
        $BODY$ LANGUAGE plpgsql;

        GRANT EXECUTE ON FUNCTION dba.fenforcesingleactivedataset() TO app_rw, app_ro;
    END IF;
END $$;
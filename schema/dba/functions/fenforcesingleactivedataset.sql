DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba') AND proname = 'fenforcesingleactivedataset') THEN
        CREATE FUNCTION dba.fenforcesingleactivedataset()
        RETURNS TRIGGER AS $BODY$
        DECLARE
            v_max_date DATE;
        BEGIN
            IF NEW.isactive = TRUE THEN
                -- Find the max datasetdate for this label/type/source combination
                SELECT MAX(datasetdate) INTO v_max_date
                FROM dba.tdataset
                WHERE label = NEW.label
                  AND datasettypeid = NEW.datasettypeid
                  AND datasourceid = NEW.datasourceid;

                -- Only allow activation if this record has the max date
                IF NEW.datasetdate < v_max_date THEN
                    -- This record is not the latest - revert its isactive
                    UPDATE dba.tdataset
                    SET isactive = FALSE
                    WHERE datasetid = NEW.datasetid;
                ELSE
                    -- This record is the latest - deactivate all others for this combination
                    UPDATE dba.tdataset
                    SET isactive = FALSE,
                        effthrudate = CURRENT_TIMESTAMP,
                        datastatusid = (SELECT datastatusid FROM dba.tdatastatus WHERE statusname = 'Inactive')
                    WHERE label = NEW.label
                      AND datasettypeid = NEW.datasettypeid
                      AND datasourceid = NEW.datasourceid
                      AND datasetid != NEW.datasetid
                      AND isactive = TRUE;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $BODY$ LANGUAGE plpgsql;

        GRANT EXECUTE ON FUNCTION dba.fenforcesingleactivedataset() TO app_rw, app_ro;
    END IF;
END $$;
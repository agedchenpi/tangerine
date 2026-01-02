DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba') AND proname = 'f_dataset_iu') THEN
        CREATE FUNCTION dba.f_dataset_iu(
            p_datasetid INT,
            p_datasetdate DATE,
            p_datasettype VARCHAR,
            p_datasource VARCHAR,
            p_label VARCHAR,
            p_statusname VARCHAR,
            p_createduser VARCHAR
        ) RETURNS INT
        LANGUAGE plpgsql
        AS $INNER$
        DECLARE
            v_datasettypeid INT;
            v_datasourceid INT;
            v_datastatusid INT;
            v_efffromdate TIMESTAMP := CURRENT_TIMESTAMP;
            v_effthrudate TIMESTAMP := '9999-01-01';
            v_datasetid INT;
        BEGIN
            SELECT datasettypeid INTO v_datasettypeid FROM dba.tdatasettype WHERE typename = p_datasettype;
            IF v_datasettypeid IS NULL THEN
                RAISE EXCEPTION 'Dataset type % not found', p_datasettype;
            END IF;
            SELECT datasourceid INTO v_datasourceid FROM dba.tdatasource WHERE sourcename = p_datasource;
            IF v_datasourceid IS NULL THEN
                RAISE EXCEPTION 'Data source % not found', p_datasource;
            END IF;
            SELECT datastatusid INTO v_datastatusid FROM dba.tdatastatus WHERE statusname = p_statusname;
            IF v_datastatusid IS NULL THEN
                RAISE EXCEPTION 'Data status % not found', p_statusname;
            END IF;
            IF p_datasetid IS NULL THEN
                INSERT INTO dba.tdataset (
                    datasetdate, label, datasettypeid, datasourceid, datastatusid, isactive, createddate, createdby, efffromdate, effthrudate
                ) VALUES (
                    p_datasetdate, p_label, v_datasettypeid, v_datasourceid, v_datastatusid, FALSE, CURRENT_TIMESTAMP, p_createduser, v_efffromdate, v_effthrudate
                ) RETURNING datasetid INTO v_datasetid;
            ELSE
                UPDATE dba.tdataset
                SET datastatusid = v_datastatusid,
                    isactive = CASE WHEN p_statusname = 'Active' THEN TRUE ELSE isactive END
                WHERE datasetid = p_datasetid;
                IF p_statusname = 'Active' THEN
                    UPDATE dba.tdataset
                    SET isactive = FALSE,
                        effthrudate = CURRENT_TIMESTAMP,
                        datastatusid = (SELECT datastatusid FROM dba.tdatastatus WHERE statusname = 'Inactive')
                    WHERE label = p_label
                      AND datasettypeid = v_datasettypeid
                      AND datasetdate = p_datasetdate
                      AND datasetid != p_datasetid
                      AND isactive = TRUE;
                END IF;
                v_datasetid := p_datasetid;
            END IF;
            RETURN v_datasetid;
        END;
        $INNER$;

        COMMENT ON FUNCTION dba.f_dataset_iu IS 'Inserts or updates a dataset in tdataset, resolving type, source, and status IDs, and managing active status.';
        GRANT EXECUTE ON FUNCTION dba.f_dataset_iu(INT, DATE, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR) TO app_rw, app_ro;
    END IF;
END $$;
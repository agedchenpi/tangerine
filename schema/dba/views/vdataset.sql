-- View: dba.vdataset
-- Purpose: Provides a comprehensive view of datasets with meaningful names instead of IDs
-- Joins tdataset with tdatasettype, tdatasource, and tdatastatus

DO $$
BEGIN
    -- Drop view if it exists (for idempotent execution)
    DROP VIEW IF EXISTS dba.vdataset;

    -- Create the view
    CREATE VIEW dba.vdataset AS
    SELECT
        d.datasetid,
        d.datasetdate,
        d.label,
        dt.typename AS datasettype,
        dt.description AS datasettype_description,
        ds.sourcename AS datasource,
        ds.description AS datasource_description,
        dst.statusname AS datastatus,
        dst.description AS datastatus_description,
        d.efffromdate,
        d.effthrudate,
        d.isactive,
        d.createddate,
        d.createdby,
        -- Additional computed columns for convenience
        CASE
            WHEN d.isactive = TRUE THEN 'Yes'
            ELSE 'No'
        END AS is_active_display,
        CASE
            WHEN d.effthrudate = '9999-01-01' THEN 'Current'
            ELSE 'Expired'
        END AS effective_status,
        AGE(CURRENT_TIMESTAMP, d.createddate) AS age_since_creation,
        -- Show if dataset is effective right now
        CASE
            WHEN CURRENT_TIMESTAMP BETWEEN d.efffromdate AND d.effthrudate THEN 'Yes'
            ELSE 'No'
        END AS is_currently_effective
    FROM dba.tdataset d
    INNER JOIN dba.tdatasettype dt ON d.datasettypeid = dt.datasettypeid
    INNER JOIN dba.tdatasource ds ON d.datasourceid = ds.datasourceid
    INNER JOIN dba.tdatastatus dst ON d.datastatusid = dst.datastatusid;

    -- Add comment on view
    COMMENT ON VIEW dba.vdataset IS 'Comprehensive view of datasets with all related reference data resolved to meaningful names';

    -- Grant permissions
    GRANT SELECT ON dba.vdataset TO PUBLIC;
    GRANT SELECT ON dba.vdataset TO app_ro, app_rw;

END $$;

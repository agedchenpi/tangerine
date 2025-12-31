DO $$  
BEGIN
    IF (SELECT COUNT(*) FROM dba.tdatasettype) = 0 THEN
        INSERT INTO dba.tdatasettype (typename) VALUES
            ('Imported'),
            ('Normalized'),
            ('Transformed'),
            ('Exported'),
            ('DBATask');
        PERFORM setval('dba.tdatasettype_datasettypeid_seq', (SELECT MAX(datasettypeid) FROM dba.tdatasettype));
    END IF;
END $$;
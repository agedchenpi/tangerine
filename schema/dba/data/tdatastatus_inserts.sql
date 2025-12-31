DO $$  
BEGIN
    IF (SELECT COUNT(*) FROM dba.tdatastatus) = 0 THEN
        INSERT INTO dba.tdatastatus (statusname, description) VALUES
            ('Active', 'Dataset is currently active and in use'),
            ('Inactive', 'Dataset is no longer active but retained for history'),
            ('Deleted', 'Dataset has been marked for deletion'),
            ('New', 'Default status of every new dataset'),
            ('Failed', 'Status if something goes wrong'),
            ('Empty', 'Dataset has no data');
    END IF;
END   $$;
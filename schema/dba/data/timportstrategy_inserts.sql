DO $$
BEGIN
    IF (SELECT COUNT(*) FROM dba.timportstrategy) = 0 THEN
        INSERT INTO dba.timportstrategy (importstrategyid, name, description) VALUES
            (1, 'Import and create new columns if needed', 'Dynamically adds new columns to the target table when source file contains columns not present in the table.'),
            (2, 'Import only (ignores new columns)', 'Imports only columns that exist in the target table. Source columns without matching table columns are silently ignored.'),
            (3, 'Import or fail if columns are missing from source file', 'Requires all source file columns to exist in the target table. Fails with an error if source has columns not in the table.');
        PERFORM setval('dba.timportstrategy_importstrategyid_seq', (SELECT MAX(importstrategyid) FROM dba.timportstrategy));
    END IF;
END $$;

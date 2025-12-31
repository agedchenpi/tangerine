DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tholidays') THEN
        CREATE TABLE dba.tholidays (
            holiday_date DATE PRIMARY KEY,
            holiday_name TEXT,
            createddate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            createdby VARCHAR(50) NOT NULL DEFAULT CURRENT_USER
        );
        COMMENT ON TABLE dba.tholidays IS 'Stores holiday dates for business day calculations.';
        COMMENT ON COLUMN dba.tholidays.holiday_date IS 'The date of the holiday (primary key).';
        COMMENT ON COLUMN dba.tholidays.holiday_name IS 'Name of the holiday.';
        COMMENT ON COLUMN dba.tholidays.createddate IS 'Timestamp when the record was created.';
        COMMENT ON COLUMN dba.tholidays.createdby IS 'User who created the record.';
    END IF;
END   $$;
GRANT SELECT ON dba.tholidays TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tholidays TO app_rw;
GRANT ALL ON dba.tholidays TO admin;
DO $$  
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tcalendardays') THEN
        CREATE TABLE dba.tcalendardays (
            fulldate DATE PRIMARY KEY,
            downame VARCHAR(10),
            downum INT,
            isbusday BOOLEAN,
            isholiday BOOLEAN,
            previous_business_date DATE
        );
        COMMENT ON TABLE dba.tcalendardays IS 'Stores calendar dates with business day and holiday information for ETL date calculations.';
        COMMENT ON COLUMN dba.tcalendardays.fulldate IS 'The date (primary key).';
        COMMENT ON COLUMN dba.tcalendardays.downame IS 'Day of week name (e.g., Monday).';
        COMMENT ON COLUMN dba.tcalendardays.downum IS 'Day of week number (0=Sunday, 1=Monday, ..., 6=Saturday).';
        COMMENT ON COLUMN dba.tcalendardays.isbusday IS 'True if the date is a business day (Monday-Friday), False otherwise.';
        COMMENT ON COLUMN dba.tcalendardays.isholiday IS 'True if the date is a holiday, False otherwise.';
        COMMENT ON COLUMN dba.tcalendardays.previous_business_date IS 'The most recent business day before this date.';
    END IF;
END   $$;

GRANT SELECT ON dba.tcalendardays TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tcalendardays TO app_rw;
GRANT ALL ON dba.tcalendardays TO admin;
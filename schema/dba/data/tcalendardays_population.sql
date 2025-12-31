DO $$  
BEGIN
    IF (SELECT COUNT(*) FROM dba.tcalendardays) = 0 THEN
        INSERT INTO dba.tcalendardays (fulldate, downame, downum, isbusday, isholiday)
        SELECT 
            d AS fulldate,
            TRIM(TO_CHAR(d, 'Day')) AS downame,
            EXTRACT(DOW FROM d)::INT AS downum,
            EXTRACT(DOW FROM d) NOT IN (0, 6) AS isbusday,
            FALSE AS isholiday
        FROM generate_series('2000-01-01'::DATE, '2050-12-31'::DATE, '1 day'::INTERVAL) AS d
        ON CONFLICT (fulldate) DO NOTHING;

        UPDATE dba.tcalendardays c
        SET isholiday = TRUE
        FROM dba.tholidays h
        WHERE c.fulldate = h.holiday_date;

        -- Adjust isbusday to exclude holidays (after setting isholiday)
        UPDATE dba.tcalendardays
        SET isbusday = FALSE
        WHERE isholiday = TRUE;

        UPDATE dba.tcalendardays c1
        SET previous_business_date = (
            SELECT fulldate
            FROM dba.tcalendardays
            WHERE fulldate < c1.fulldate
              AND isbusday = TRUE
              AND isholiday = FALSE
            ORDER BY fulldate DESC
            LIMIT 1
        );
    END IF;
END $$;
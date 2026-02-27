-- YFinance Index Scheduler Jobs Configuration
-- US indexes, global indexes, sector ETFs: all markets settled by 23:00 UTC on weekdays
-- period='5d' handles any stale-data edge cases from holidays

DO $$
BEGIN
    INSERT INTO dba.tscheduler (
        job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
        script_path, is_active
    ) VALUES
        ('YFinance_US_Indexes', 'custom', '0', '23', '*', '*', '1-5',
         'etl/jobs/run_yfinance_us_indexes.py', TRUE),
        ('YFinance_Global_Indexes', 'custom', '0', '23', '*', '*', '1-5',
         'etl/jobs/run_yfinance_global_indexes.py', TRUE),
        ('YFinance_Sector_ETFs', 'custom', '0', '23', '*', '*', '1-5',
         'etl/jobs/run_yfinance_sector_etfs.py', TRUE)
    ON CONFLICT (job_name) DO UPDATE SET
        script_path = EXCLUDED.script_path,
        is_active   = EXCLUDED.is_active;

    RAISE NOTICE 'YFinance index scheduler jobs configured: 3 jobs (3 active)';
END $$;

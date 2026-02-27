-- YFinance Scheduler Jobs Configuration
-- Commodity futures: all major US markets settle by 3:00 PM ET (20:00 UTC)
-- Run at 23:00 UTC (6:00 PM ET) on weekdays to guarantee settlement data is available

DO $$
BEGIN
    INSERT INTO dba.tscheduler (
        job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
        script_path, is_active
    ) VALUES
        ('YFinance_Commodities', 'custom', '0', '23', '*', '*', '1-5',
         'etl/jobs/run_yfinance_commodities.py', TRUE)
    ON CONFLICT (job_name) DO UPDATE SET
        script_path = EXCLUDED.script_path,
        is_active   = EXCLUDED.is_active;

    RAISE NOTICE 'YFinance scheduler jobs configured: 1 job (1 active)';
END $$;

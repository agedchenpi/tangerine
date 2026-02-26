-- BankOfEngland Scheduler Jobs Configuration
-- Sets up automated scheduled jobs for Bank of England data imports
-- This file is sourced during initial database setup via init.sh
-- Uses collector pattern: bankofengland_collector.py --config-id N

DO $$
BEGIN
    -- SONIA rates: daily at 9:30 AM CST (15:30 UTC), weekdays only
    -- SONIA is published ~10:00 AM London time on business days

    INSERT INTO dba.tscheduler (
        job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
        script_path, is_active
    ) VALUES
        ('BankOfEngland_SONIA', 'custom', '30', '15', '*', '*', '1-5',
         'etl/collectors/bankofengland_collector.py --config-id 13', TRUE)
    ON CONFLICT (job_name) DO UPDATE SET
        script_path = EXCLUDED.script_path,
        is_active = EXCLUDED.is_active;

    RAISE NOTICE 'BankOfEngland scheduler jobs configured: 1 job (1 active)';
END $$;

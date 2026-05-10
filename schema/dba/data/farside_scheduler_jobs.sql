-- Far Side Scheduler Job Configuration
-- thefarside.com publishes 5 new comics daily; no specific publish time.
-- Run at 06:00 UTC every day to catch the daily update.

DO $$
BEGIN
    INSERT INTO dba.tscheduler (
        job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
        script_path, is_active
    ) VALUES
        ('FarSide_Daily', 'custom', '0', '6', '*', '*', '*',
         'etl/jobs/run_farside_daily.py', TRUE)
    ON CONFLICT (job_name) DO UPDATE SET
        script_path = EXCLUDED.script_path,
        is_active   = EXCLUDED.is_active;

    RAISE NOTICE 'Far Side scheduler jobs configured: 1 job (1 active)';
END $$;

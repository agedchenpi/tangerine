-- Daily database backup scheduler job
-- Runs at 03:00 UTC every day — deepest off-hours window between CoinGecko (00:05)
-- and the NewYorkFed batch (09:00), avoiding the hourly smoketest at :00.

DO $$
BEGIN
    INSERT INTO dba.tscheduler (
        job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
        script_path, is_active
    ) VALUES
        ('DB_Daily_Backup', 'custom', '0', '3', '*', '*', '*',
         'etl/jobs/run_database_backup.py', TRUE)
    ON CONFLICT (job_name) DO UPDATE SET
        script_path = EXCLUDED.script_path,
        is_active   = EXCLUDED.is_active;

    RAISE NOTICE 'Database backup scheduler job configured: 1 job (1 active)';
END $$;

-- CoinGecko Scheduler Jobs Configuration
-- Crypto markets run 24/7; midnight UTC is the natural daily reset point.
-- Run at 00:05 UTC every day (including weekends) to capture the full prior UTC day.

DO $$
BEGIN
    INSERT INTO dba.tscheduler (
        job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
        script_path, is_active
    ) VALUES
        ('CoinGecko_Crypto', 'custom', '5', '0', '*', '*', '*',
         'etl/jobs/run_coingecko_crypto.py', TRUE)
    ON CONFLICT (job_name) DO UPDATE SET
        script_path = EXCLUDED.script_path,
        is_active   = EXCLUDED.is_active;

    RAISE NOTICE 'CoinGecko scheduler jobs configured: 1 job (1 active)';
END $$;

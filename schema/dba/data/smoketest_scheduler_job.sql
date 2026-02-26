-- Smoketest Scheduler Job Configuration
-- Sets up hourly smoketest job to verify cron scheduler and dataset creation pipeline
-- This file is sourced during initial database setup via init.sh

INSERT INTO dba.tscheduler (job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday, script_path, is_active)
VALUES ('Hourly_Smoketest', 'custom', '0', '*', '*', '*', '*',
        'etl/jobs/hourly_smoketest.py', TRUE)
ON CONFLICT (job_name) DO UPDATE SET script_path = EXCLUDED.script_path, is_active = EXCLUDED.is_active;

-- NewYorkFed Scheduler Jobs Configuration
-- Sets up automated scheduled jobs for NewYorkFed data imports
-- This file is sourced during initial database setup via init.sh
-- All jobs now use the collector pattern: newyorkfed_collector.py --config-id N

DO $$
BEGIN
    -- Insert scheduler jobs for NewYorkFed API imports
    -- Staggered start times (5-min intervals) to avoid API rate limiting

    INSERT INTO dba.tscheduler (
        job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
        script_path, is_active
    ) VALUES
        -- Daily imports
        ('NewYorkFed_ReferenceRates', 'custom', '0', '9', '*', '*', '*',
         'etl/collectors/newyorkfed_collector.py --config-id 1', TRUE),
        ('NewYorkFed_Repo', 'custom', '5', '9', '*', '*', '*',
         'etl/collectors/newyorkfed_collector.py --config-id 4', TRUE),
        ('NewYorkFed_ReverseRepo', 'custom', '10', '9', '*', '*', '*',
         'etl/collectors/newyorkfed_collector.py --config-id 5', TRUE),
        ('NewYorkFed_SecLending', 'custom', '15', '9', '*', '*', '*',
         'etl/collectors/newyorkfed_collector.py --config-id 8', FALSE),
        ('NewYorkFed_Treasury', 'custom', '20', '9', '*', '*', '*',
         'etl/collectors/newyorkfed_collector.py --config-id 12', FALSE),

        -- Weekly imports
        ('NewYorkFed_SOMA', 'custom', '0', '10', '*', '*', '4',
         'etl/collectors/newyorkfed_collector.py --config-id 3', TRUE),
        ('NewYorkFed_AgencyMBS', 'custom', '0', '10', '*', '*', '5',
         'etl/collectors/newyorkfed_collector.py --config-id 6', FALSE),
        ('NewYorkFed_FXSwaps', 'custom', '5', '10', '*', '*', '5',
         'etl/collectors/newyorkfed_collector.py --config-id 7', FALSE),
        ('NewYorkFed_PDStatistics', 'custom', '10', '10', '*', '*', '5',
         'etl/collectors/newyorkfed_collector.py --config-id 10', FALSE),

        -- Monthly imports (first Monday of month)
        ('NewYorkFed_GuideSheets', 'custom', '0', '11', '1-7', '*', '1',
         'etl/collectors/newyorkfed_collector.py --config-id 9', FALSE),

        -- Quarterly imports (1st of Jan/Apr/Jul/Oct)
        ('NewYorkFed_MarketShare', 'custom', '0', '11', '1', '1,4,7,10', '*',
         'etl/collectors/newyorkfed_collector.py --config-id 11', FALSE)
    ON CONFLICT (job_name) DO UPDATE SET
        script_path = EXCLUDED.script_path,
        is_active = EXCLUDED.is_active;

    RAISE NOTICE 'NewYorkFed scheduler jobs configured: 11 jobs (4 active, 7 inactive)';
END $$;

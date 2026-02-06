-- NewYorkFed Scheduler Jobs Configuration
-- Sets up automated scheduled jobs for NewYorkFed data imports
-- This file is sourced during initial database setup via init.sh

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
         'python /app/etl/jobs/run_newyorkfed_reference_rates.py --endpoint-type latest', TRUE),
        ('NewYorkFed_Repo', 'custom', '5', '9', '*', '*', '*',
         'python /app/etl/jobs/run_newyorkfed_repo.py --operation-type repo', TRUE),
        ('NewYorkFed_ReverseRepo', 'custom', '10', '9', '*', '*', '*',
         'python /app/etl/jobs/run_newyorkfed_repo.py --operation-type reverserepo', TRUE),
        ('NewYorkFed_SecLending', 'custom', '15', '9', '*', '*', '*',
         'python /app/etl/jobs/run_newyorkfed_securities_lending.py', FALSE),
        ('NewYorkFed_Treasury', 'custom', '20', '9', '*', '*', '*',
         'python /app/etl/jobs/run_newyorkfed_treasury.py', FALSE),

        -- Weekly imports
        ('NewYorkFed_SOMA', 'custom', '0', '10', '*', '*', '4',
         'python /app/etl/jobs/run_newyorkfed_soma_holdings.py', TRUE),
        ('NewYorkFed_AgencyMBS', 'custom', '0', '10', '*', '*', '5',
         'python /app/etl/jobs/run_newyorkfed_agency_mbs.py', FALSE),
        ('NewYorkFed_FXSwaps', 'custom', '5', '10', '*', '*', '5',
         'python /app/etl/jobs/run_newyorkfed_fx_swaps.py', FALSE),
        ('NewYorkFed_PDStatistics', 'custom', '10', '10', '*', '*', '5',
         'python /app/etl/jobs/run_newyorkfed_pd_statistics.py', FALSE),

        -- Monthly imports (first Monday of month)
        ('NewYorkFed_GuideSheets', 'custom', '0', '11', '1-7', '*', '1',
         'python /app/etl/jobs/run_newyorkfed_guide_sheets.py', FALSE),

        -- Quarterly imports (1st of Jan/Apr/Jul/Oct)
        ('NewYorkFed_MarketShare', 'custom', '0', '11', '1', '1,4,7,10', '*',
         'python /app/etl/jobs/run_newyorkfed_market_share.py', FALSE)
    ON CONFLICT (job_name) DO UPDATE SET
        script_path = EXCLUDED.script_path,
        is_active = EXCLUDED.is_active;

    RAISE NOTICE 'NewYorkFed scheduler jobs configured: 11 jobs (4 active, 7 stub)';
END $$;

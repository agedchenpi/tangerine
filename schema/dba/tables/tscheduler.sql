DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'dba' AND tablename = 'tscheduler') THEN
        CREATE TABLE dba.tscheduler (
            scheduler_id SERIAL PRIMARY KEY,
            job_name VARCHAR(100) NOT NULL UNIQUE,
            job_type VARCHAR(50) NOT NULL CHECK (job_type IN ('inbox_processor', 'report', 'import', 'custom')),
            cron_minute VARCHAR(20) NOT NULL DEFAULT '*',
            cron_hour VARCHAR(20) NOT NULL DEFAULT '*',
            cron_day VARCHAR(20) NOT NULL DEFAULT '*',
            cron_month VARCHAR(20) NOT NULL DEFAULT '*',
            cron_weekday VARCHAR(20) NOT NULL DEFAULT '*',
            script_path VARCHAR(255),
            config_id INT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_run_at TIMESTAMP,
            last_run_status VARCHAR(50) CHECK (last_run_status IS NULL OR last_run_status IN ('Success', 'Failed', 'Running')),
            last_run_uuid VARCHAR(36),
            next_run_at TIMESTAMP,
            CONSTRAINT valid_custom_job CHECK (
                (job_type = 'custom' AND script_path IS NOT NULL)
                OR (job_type != 'custom')
            )
        );
        COMMENT ON TABLE dba.tscheduler IS 'Cron-based job scheduler for automated ETL tasks. Defines schedules for inbox processors, reports, imports, and custom scripts.';
        COMMENT ON COLUMN dba.tscheduler.scheduler_id IS 'Unique identifier for the schedule.';
        COMMENT ON COLUMN dba.tscheduler.job_name IS 'Descriptive name for the scheduled job.';
        COMMENT ON COLUMN dba.tscheduler.job_type IS 'Type of job: inbox_processor, report, import, or custom.';
        COMMENT ON COLUMN dba.tscheduler.cron_minute IS 'Cron minute field (0-59, *, */5, etc.).';
        COMMENT ON COLUMN dba.tscheduler.cron_hour IS 'Cron hour field (0-23, *, etc.).';
        COMMENT ON COLUMN dba.tscheduler.cron_day IS 'Cron day of month field (1-31, *, etc.).';
        COMMENT ON COLUMN dba.tscheduler.cron_month IS 'Cron month field (1-12, *, etc.).';
        COMMENT ON COLUMN dba.tscheduler.cron_weekday IS 'Cron day of week field (0-6, *, etc.). 0=Sunday.';
        COMMENT ON COLUMN dba.tscheduler.script_path IS 'Path to Python script for custom job type (required for custom jobs).';
        COMMENT ON COLUMN dba.tscheduler.config_id IS 'Reference to related configuration (inbox_config_id, report_id, or import config_id depending on job_type).';
        COMMENT ON COLUMN dba.tscheduler.is_active IS 'Flag indicating whether the schedule is active.';
        COMMENT ON COLUMN dba.tscheduler.created_at IS 'Timestamp when the schedule was created.';
        COMMENT ON COLUMN dba.tscheduler.last_modified_at IS 'Timestamp when the schedule was last modified.';
        COMMENT ON COLUMN dba.tscheduler.last_run_at IS 'Timestamp of the last execution.';
        COMMENT ON COLUMN dba.tscheduler.last_run_status IS 'Status of the last run: Success, Failed, or Running.';
        COMMENT ON COLUMN dba.tscheduler.last_run_uuid IS 'Run UUID from the last job execution, links to tlogentry for log retrieval.';
        COMMENT ON COLUMN dba.tscheduler.next_run_at IS 'Calculated timestamp for the next scheduled run.';
    END IF;
END $$;
GRANT SELECT ON dba.tscheduler TO app_ro;
GRANT SELECT, INSERT, UPDATE ON dba.tscheduler TO app_rw;
GRANT ALL ON dba.tscheduler TO admin;
GRANT USAGE, SELECT ON SEQUENCE dba.tscheduler_scheduler_id_seq TO app_rw, app_ro;

-- Migration: add last_run_output column to store stdout from ad-hoc runs
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'dba' AND table_name = 'tscheduler' AND column_name = 'last_run_output'
    ) THEN
        ALTER TABLE dba.tscheduler ADD COLUMN last_run_output TEXT;
        COMMENT ON COLUMN dba.tscheduler.last_run_output IS 'Captured stdout from the last ad-hoc job execution for debugging.';
    END IF;
END $$;

-- Migration: add last_run_uuid column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'dba' AND table_name = 'tscheduler' AND column_name = 'last_run_uuid'
    ) THEN
        ALTER TABLE dba.tscheduler ADD COLUMN last_run_uuid VARCHAR(36);
        COMMENT ON COLUMN dba.tscheduler.last_run_uuid IS 'Run UUID from the last job execution, links to tlogentry for log retrieval.';
    END IF;
END $$;

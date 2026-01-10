-- Insert procedure for tscheduler
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'pscheduleri'
    ) THEN
        CREATE PROCEDURE dba.pscheduleri(
            p_job_name VARCHAR,
            p_job_type VARCHAR,
            p_cron_minute VARCHAR DEFAULT '*',
            p_cron_hour VARCHAR DEFAULT '*',
            p_cron_day VARCHAR DEFAULT '*',
            p_cron_month VARCHAR DEFAULT '*',
            p_cron_weekday VARCHAR DEFAULT '*',
            p_script_path VARCHAR DEFAULT NULL,
            p_config_id INT DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT TRUE
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            INSERT INTO dba.tscheduler (
                job_name,
                job_type,
                cron_minute,
                cron_hour,
                cron_day,
                cron_month,
                cron_weekday,
                script_path,
                config_id,
                is_active,
                created_at,
                last_modified_at
            ) VALUES (
                p_job_name,
                p_job_type,
                p_cron_minute,
                p_cron_hour,
                p_cron_day,
                p_cron_month,
                p_cron_weekday,
                p_script_path,
                p_config_id,
                p_is_active,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            ) ON CONFLICT (job_name) DO NOTHING;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.pscheduleri IS 'Inserts a new scheduler configuration into tscheduler. Does nothing on conflict with existing job_name.';
    END IF;
END $$;

-- Update procedure for tscheduler
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'pscheduleru'
    ) THEN
        CREATE PROCEDURE dba.pscheduleru(
            p_scheduler_id INT,
            p_job_name VARCHAR DEFAULT NULL,
            p_job_type VARCHAR DEFAULT NULL,
            p_cron_minute VARCHAR DEFAULT NULL,
            p_cron_hour VARCHAR DEFAULT NULL,
            p_cron_day VARCHAR DEFAULT NULL,
            p_cron_month VARCHAR DEFAULT NULL,
            p_cron_weekday VARCHAR DEFAULT NULL,
            p_script_path VARCHAR DEFAULT NULL,
            p_config_id INT DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT NULL,
            p_last_run_at TIMESTAMP DEFAULT NULL,
            p_last_run_status VARCHAR DEFAULT NULL,
            p_next_run_at TIMESTAMP DEFAULT NULL
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            UPDATE dba.tscheduler
            SET
                job_name = COALESCE(p_job_name, job_name),
                job_type = COALESCE(p_job_type, job_type),
                cron_minute = COALESCE(p_cron_minute, cron_minute),
                cron_hour = COALESCE(p_cron_hour, cron_hour),
                cron_day = COALESCE(p_cron_day, cron_day),
                cron_month = COALESCE(p_cron_month, cron_month),
                cron_weekday = COALESCE(p_cron_weekday, cron_weekday),
                script_path = COALESCE(p_script_path, script_path),
                config_id = COALESCE(p_config_id, config_id),
                is_active = COALESCE(p_is_active, is_active),
                last_run_at = COALESCE(p_last_run_at, last_run_at),
                last_run_status = COALESCE(p_last_run_status, last_run_status),
                next_run_at = COALESCE(p_next_run_at, next_run_at),
                last_modified_at = CURRENT_TIMESTAMP
            WHERE scheduler_id = p_scheduler_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'No scheduler found with scheduler_id %', p_scheduler_id;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE EXCEPTION 'Error updating scheduler: %', SQLERRM;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.pscheduleru IS 'Updates an existing scheduler configuration in tscheduler. Only non-NULL parameters are updated.';
    END IF;
END $$;

-- Grant execute permissions
GRANT EXECUTE ON PROCEDURE dba.pscheduleri TO app_rw;
GRANT EXECUTE ON PROCEDURE dba.pscheduleru TO app_rw;

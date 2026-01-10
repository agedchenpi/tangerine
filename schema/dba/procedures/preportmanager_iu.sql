-- Insert procedure for treportmanager
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'preportmanageri'
    ) THEN
        CREATE PROCEDURE dba.preportmanageri(
            p_report_name VARCHAR,
            p_recipients TEXT,
            p_subject_line VARCHAR,
            p_body_template TEXT,
            p_description TEXT DEFAULT NULL,
            p_cc_recipients TEXT DEFAULT NULL,
            p_output_format VARCHAR DEFAULT 'html',
            p_attachment_filename VARCHAR DEFAULT NULL,
            p_schedule_id INT DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT TRUE
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            INSERT INTO dba.treportmanager (
                report_name,
                description,
                recipients,
                cc_recipients,
                subject_line,
                body_template,
                output_format,
                attachment_filename,
                schedule_id,
                is_active,
                created_at,
                last_modified_at
            ) VALUES (
                p_report_name,
                p_description,
                p_recipients,
                p_cc_recipients,
                p_subject_line,
                p_body_template,
                p_output_format,
                p_attachment_filename,
                p_schedule_id,
                p_is_active,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            ) ON CONFLICT (report_name) DO NOTHING;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.preportmanageri IS 'Inserts a new report configuration into treportmanager. Does nothing on conflict with existing report_name.';
    END IF;
END $$;

-- Update procedure for treportmanager
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'preportmanageru'
    ) THEN
        CREATE PROCEDURE dba.preportmanageru(
            p_report_id INT,
            p_report_name VARCHAR DEFAULT NULL,
            p_description TEXT DEFAULT NULL,
            p_recipients TEXT DEFAULT NULL,
            p_cc_recipients TEXT DEFAULT NULL,
            p_subject_line VARCHAR DEFAULT NULL,
            p_body_template TEXT DEFAULT NULL,
            p_output_format VARCHAR DEFAULT NULL,
            p_attachment_filename VARCHAR DEFAULT NULL,
            p_schedule_id INT DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT NULL,
            p_last_run_at TIMESTAMP DEFAULT NULL,
            p_last_run_status VARCHAR DEFAULT NULL
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            UPDATE dba.treportmanager
            SET
                report_name = COALESCE(p_report_name, report_name),
                description = COALESCE(p_description, description),
                recipients = COALESCE(p_recipients, recipients),
                cc_recipients = COALESCE(p_cc_recipients, cc_recipients),
                subject_line = COALESCE(p_subject_line, subject_line),
                body_template = COALESCE(p_body_template, body_template),
                output_format = COALESCE(p_output_format, output_format),
                attachment_filename = COALESCE(p_attachment_filename, attachment_filename),
                schedule_id = COALESCE(p_schedule_id, schedule_id),
                is_active = COALESCE(p_is_active, is_active),
                last_run_at = COALESCE(p_last_run_at, last_run_at),
                last_run_status = COALESCE(p_last_run_status, last_run_status),
                last_modified_at = CURRENT_TIMESTAMP
            WHERE report_id = p_report_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'No report found with report_id %', p_report_id;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE EXCEPTION 'Error updating report: %', SQLERRM;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.preportmanageru IS 'Updates an existing report configuration in treportmanager. Only non-NULL parameters are updated.';
    END IF;
END $$;

-- Grant execute permissions
GRANT EXECUTE ON PROCEDURE dba.preportmanageri TO app_rw;
GRANT EXECUTE ON PROCEDURE dba.preportmanageru TO app_rw;

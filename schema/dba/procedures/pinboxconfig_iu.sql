-- Insert procedure for tinboxconfig
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'pinboxconfigi'
    ) THEN
        CREATE PROCEDURE dba.pinboxconfigi(
            p_config_name VARCHAR,
            p_attachment_pattern VARCHAR,
            p_description TEXT DEFAULT NULL,
            p_subject_pattern VARCHAR DEFAULT NULL,
            p_sender_pattern VARCHAR DEFAULT NULL,
            p_target_directory VARCHAR DEFAULT '/app/data/source/inbox',
            p_date_prefix_format VARCHAR DEFAULT 'yyyyMMdd',
            p_save_eml BOOLEAN DEFAULT FALSE,
            p_mark_processed BOOLEAN DEFAULT TRUE,
            p_processed_label VARCHAR DEFAULT 'Processed',
            p_error_label VARCHAR DEFAULT 'ErrorFolder',
            p_linked_import_config_id INT DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT TRUE
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            INSERT INTO dba.tinboxconfig (
                config_name,
                description,
                subject_pattern,
                sender_pattern,
                attachment_pattern,
                target_directory,
                date_prefix_format,
                save_eml,
                mark_processed,
                processed_label,
                error_label,
                linked_import_config_id,
                is_active,
                created_at,
                last_modified_at
            ) VALUES (
                p_config_name,
                p_description,
                p_subject_pattern,
                p_sender_pattern,
                p_attachment_pattern,
                p_target_directory,
                p_date_prefix_format,
                p_save_eml,
                p_mark_processed,
                p_processed_label,
                p_error_label,
                p_linked_import_config_id,
                p_is_active,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            ) ON CONFLICT (config_name) DO NOTHING;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.pinboxconfigi IS 'Inserts a new inbox configuration into tinboxconfig. Does nothing on conflict with existing config_name.';
    END IF;
END $$;

-- Update procedure for tinboxconfig
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'pinboxconfigu'
    ) THEN
        CREATE PROCEDURE dba.pinboxconfigu(
            p_inbox_config_id INT,
            p_config_name VARCHAR DEFAULT NULL,
            p_description TEXT DEFAULT NULL,
            p_subject_pattern VARCHAR DEFAULT NULL,
            p_sender_pattern VARCHAR DEFAULT NULL,
            p_attachment_pattern VARCHAR DEFAULT NULL,
            p_target_directory VARCHAR DEFAULT NULL,
            p_date_prefix_format VARCHAR DEFAULT NULL,
            p_save_eml BOOLEAN DEFAULT NULL,
            p_mark_processed BOOLEAN DEFAULT NULL,
            p_processed_label VARCHAR DEFAULT NULL,
            p_error_label VARCHAR DEFAULT NULL,
            p_linked_import_config_id INT DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT NULL,
            p_last_run_at TIMESTAMP DEFAULT NULL
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            UPDATE dba.tinboxconfig
            SET
                config_name = COALESCE(p_config_name, config_name),
                description = COALESCE(p_description, description),
                subject_pattern = COALESCE(p_subject_pattern, subject_pattern),
                sender_pattern = COALESCE(p_sender_pattern, sender_pattern),
                attachment_pattern = COALESCE(p_attachment_pattern, attachment_pattern),
                target_directory = COALESCE(p_target_directory, target_directory),
                date_prefix_format = COALESCE(p_date_prefix_format, date_prefix_format),
                save_eml = COALESCE(p_save_eml, save_eml),
                mark_processed = COALESCE(p_mark_processed, mark_processed),
                processed_label = COALESCE(p_processed_label, processed_label),
                error_label = COALESCE(p_error_label, error_label),
                linked_import_config_id = COALESCE(p_linked_import_config_id, linked_import_config_id),
                is_active = COALESCE(p_is_active, is_active),
                last_run_at = COALESCE(p_last_run_at, last_run_at),
                last_modified_at = CURRENT_TIMESTAMP
            WHERE inbox_config_id = p_inbox_config_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'No inbox configuration found with inbox_config_id %', p_inbox_config_id;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE EXCEPTION 'Error updating inbox configuration: %', SQLERRM;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.pinboxconfigu IS 'Updates an existing inbox configuration in tinboxconfig. Only non-NULL parameters are updated.';
    END IF;
END $$;

-- Grant execute permissions
GRANT EXECUTE ON PROCEDURE dba.pinboxconfigi TO app_rw;
GRANT EXECUTE ON PROCEDURE dba.pinboxconfigu TO app_rw;

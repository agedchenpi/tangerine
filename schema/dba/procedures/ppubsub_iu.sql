-- =============================================================================
-- Pub-Sub Event Procedures
-- =============================================================================

-- Insert event into queue
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'ppubsub_event_create'
    ) THEN
        CREATE PROCEDURE dba.ppubsub_event_create(
            p_event_type VARCHAR,
            p_event_source VARCHAR,
            p_event_data JSONB DEFAULT '{}',
            p_priority INT DEFAULT 5
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            INSERT INTO dba.tpubsub_events (
                event_type,
                event_source,
                event_data,
                priority,
                status,
                created_at
            ) VALUES (
                p_event_type,
                p_event_source,
                p_event_data,
                p_priority,
                'pending',
                CURRENT_TIMESTAMP
            );
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.ppubsub_event_create IS 'Creates a new event in the pub-sub queue.';
    END IF;
END $$;

-- Update event status
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'ppubsub_event_update'
    ) THEN
        CREATE PROCEDURE dba.ppubsub_event_update(
            p_event_id INT,
            p_status VARCHAR DEFAULT NULL,
            p_error_message TEXT DEFAULT NULL,
            p_increment_retry BOOLEAN DEFAULT FALSE
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            UPDATE dba.tpubsub_events
            SET
                status = COALESCE(p_status, status),
                processed_at = CASE
                    WHEN p_status = 'processing' AND processed_at IS NULL THEN CURRENT_TIMESTAMP
                    ELSE processed_at
                END,
                completed_at = CASE
                    WHEN p_status IN ('completed', 'failed', 'cancelled') THEN CURRENT_TIMESTAMP
                    ELSE completed_at
                END,
                error_message = COALESCE(p_error_message, error_message),
                retry_count = CASE
                    WHEN p_increment_retry THEN retry_count + 1
                    ELSE retry_count
                END
            WHERE event_id = p_event_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'No event found with event_id %', p_event_id;
            END IF;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.ppubsub_event_update IS 'Updates an event status in the pub-sub queue.';
    END IF;
END $$;

-- =============================================================================
-- Pub-Sub Subscriber Procedures
-- =============================================================================

-- Insert subscriber
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'ppubsub_subscriberi'
    ) THEN
        CREATE PROCEDURE dba.ppubsub_subscriberi(
            p_subscriber_name VARCHAR,
            p_event_type VARCHAR,
            p_job_type VARCHAR,
            p_description TEXT DEFAULT NULL,
            p_event_filter JSONB DEFAULT '{}',
            p_config_id INT DEFAULT NULL,
            p_script_path VARCHAR DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT TRUE
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            INSERT INTO dba.tpubsub_subscribers (
                subscriber_name,
                description,
                event_type,
                event_filter,
                job_type,
                config_id,
                script_path,
                is_active,
                created_at,
                last_modified_at
            ) VALUES (
                p_subscriber_name,
                p_description,
                p_event_type,
                p_event_filter,
                p_job_type,
                p_config_id,
                p_script_path,
                p_is_active,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            ) ON CONFLICT (subscriber_name) DO NOTHING;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.ppubsub_subscriberi IS 'Creates a new subscriber in the pub-sub system.';
    END IF;
END $$;

-- Update subscriber
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'ppubsub_subscriberu'
    ) THEN
        CREATE PROCEDURE dba.ppubsub_subscriberu(
            p_subscriber_id INT,
            p_subscriber_name VARCHAR DEFAULT NULL,
            p_description TEXT DEFAULT NULL,
            p_event_type VARCHAR DEFAULT NULL,
            p_event_filter JSONB DEFAULT NULL,
            p_job_type VARCHAR DEFAULT NULL,
            p_config_id INT DEFAULT NULL,
            p_script_path VARCHAR DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT NULL,
            p_last_triggered_at TIMESTAMP DEFAULT NULL,
            p_increment_trigger BOOLEAN DEFAULT FALSE
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            UPDATE dba.tpubsub_subscribers
            SET
                subscriber_name = COALESCE(p_subscriber_name, subscriber_name),
                description = COALESCE(p_description, description),
                event_type = COALESCE(p_event_type, event_type),
                event_filter = COALESCE(p_event_filter, event_filter),
                job_type = COALESCE(p_job_type, job_type),
                config_id = COALESCE(p_config_id, config_id),
                script_path = COALESCE(p_script_path, script_path),
                is_active = COALESCE(p_is_active, is_active),
                last_triggered_at = COALESCE(p_last_triggered_at, last_triggered_at),
                trigger_count = CASE
                    WHEN p_increment_trigger THEN trigger_count + 1
                    ELSE trigger_count
                END,
                last_modified_at = CURRENT_TIMESTAMP
            WHERE subscriber_id = p_subscriber_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'No subscriber found with subscriber_id %', p_subscriber_id;
            END IF;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.ppubsub_subscriberu IS 'Updates an existing subscriber in the pub-sub system.';
    END IF;
END $$;

-- Grant execute permissions
GRANT EXECUTE ON PROCEDURE dba.ppubsub_event_create TO app_rw;
GRANT EXECUTE ON PROCEDURE dba.ppubsub_event_update TO app_rw;
GRANT EXECUTE ON PROCEDURE dba.ppubsub_subscriberi TO app_rw;
GRANT EXECUTE ON PROCEDURE dba.ppubsub_subscriberu TO app_rw;

-- Insert procedure for timportconfig
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'pimportconfigi'
    ) THEN
        CREATE PROCEDURE dba.pimportconfigi(
            p_config_name VARCHAR,
            p_datasource VARCHAR,
            p_datasettype VARCHAR,
            p_source_directory VARCHAR,
            p_archive_directory VARCHAR,
            p_file_pattern VARCHAR,
            p_file_type VARCHAR,
            p_metadata_label_source VARCHAR,
            p_metadata_label_location VARCHAR,
            p_dateconfig VARCHAR,
            p_datelocation VARCHAR,
            p_dateformat VARCHAR,
            p_delimiter VARCHAR,
            p_target_table VARCHAR,
            p_importstrategyid INT DEFAULT 1,
            p_is_active BOOLEAN DEFAULT TRUE,
            p_is_blob BOOLEAN DEFAULT FALSE
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            INSERT INTO dba.timportconfig (
                config_name,
                datasource,
                datasettype,
                source_directory,
                archive_directory,
                file_pattern,
                file_type,
                metadata_label_source,
                metadata_label_location,
                dateconfig,
                datelocation,
                dateformat,
                delimiter,
                target_table,
                importstrategyid,
                is_active,
                is_blob,
                created_at,
                last_modified_at
            ) VALUES (
                p_config_name,
                p_datasource,
                p_datasettype,
                p_source_directory,
                p_archive_directory,
                p_file_pattern,
                p_file_type,
                p_metadata_label_source,
                p_metadata_label_location,
                p_dateconfig,
                p_datelocation,
                p_dateformat,
                p_delimiter,
                p_target_table,
                p_importstrategyid,
                p_is_active,
                p_is_blob,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            ) ON CONFLICT (config_name) DO NOTHING;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.pimportconfigi IS 'Inserts a new import configuration into timportconfig. Does nothing on conflict with existing config_name.';
    END IF;
END $$;

-- Update procedure for timportconfig
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'dba')
        AND proname = 'pimportconfigu'
    ) THEN
        CREATE PROCEDURE dba.pimportconfigu(
            p_config_id INT,
            p_config_name VARCHAR DEFAULT NULL,
            p_datasource VARCHAR DEFAULT NULL,
            p_datasettype VARCHAR DEFAULT NULL,
            p_source_directory VARCHAR DEFAULT NULL,
            p_archive_directory VARCHAR DEFAULT NULL,
            p_file_pattern VARCHAR DEFAULT NULL,
            p_file_type VARCHAR DEFAULT NULL,
            p_metadata_label_source VARCHAR DEFAULT NULL,
            p_metadata_label_location VARCHAR DEFAULT NULL,
            p_dateconfig VARCHAR DEFAULT NULL,
            p_datelocation VARCHAR DEFAULT NULL,
            p_dateformat VARCHAR DEFAULT NULL,
            p_delimiter VARCHAR DEFAULT NULL,
            p_target_table VARCHAR DEFAULT NULL,
            p_importstrategyid INT DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT NULL,
            p_is_blob BOOLEAN DEFAULT NULL
        )
        LANGUAGE plpgsql
        AS $PROC$
        BEGIN
            UPDATE dba.timportconfig
            SET
                config_name = COALESCE(p_config_name, config_name),
                datasource = COALESCE(p_datasource, datasource),
                datasettype = COALESCE(p_datasettype, datasettype),
                source_directory = COALESCE(p_source_directory, source_directory),
                archive_directory = COALESCE(p_archive_directory, archive_directory),
                file_pattern = COALESCE(p_file_pattern, file_pattern),
                file_type = COALESCE(p_file_type, file_type),
                metadata_label_source = COALESCE(p_metadata_label_source, metadata_label_source),
                metadata_label_location = COALESCE(p_metadata_label_location, metadata_label_location),
                dateconfig = COALESCE(p_dateconfig, dateconfig),
                datelocation = COALESCE(p_datelocation, datelocation),
                dateformat = COALESCE(p_dateformat, dateformat),
                delimiter = COALESCE(p_delimiter, delimiter),
                target_table = COALESCE(p_target_table, target_table),
                importstrategyid = COALESCE(p_importstrategyid, importstrategyid),
                is_active = COALESCE(p_is_active, is_active),
                is_blob = COALESCE(p_is_blob, is_blob),
                last_modified_at = CURRENT_TIMESTAMP
            WHERE config_id = p_config_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'No configuration found with config_id %', p_config_id;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE EXCEPTION 'Error updating configuration: %', SQLERRM;
        END;
        $PROC$;

        COMMENT ON PROCEDURE dba.pimportconfigu IS 'Updates an existing import configuration in timportconfig. Only non-NULL parameters are updated.';
    END IF;
END $$;

-- Grant execute permissions
GRANT EXECUTE ON PROCEDURE dba.pimportconfigi TO app_rw;
GRANT EXECUTE ON PROCEDURE dba.pimportconfigu TO app_rw;

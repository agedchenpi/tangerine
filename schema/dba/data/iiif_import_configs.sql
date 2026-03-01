-- IIIF Import Configurations
-- Creates timportconfig record for Smithsonian Freer Gallery IIIF artwork data
-- Also ensures required datasource and datasettype reference rows exist

DO $$
DECLARE
    v_strategy_id INT;
BEGIN
    -- Ensure data source exists
    INSERT INTO dba.tdatasource (sourcename, description, createdby)
    VALUES ('IIIF', 'Smithsonian Institution IIIF Presentation API', 'admin')
    ON CONFLICT (sourcename) DO NOTHING;

    -- Ensure dataset type exists
    INSERT INTO dba.tdatasettype (typename, description, createdby)
    VALUES ('Artwork', 'Museum artwork records with image metadata', 'admin')
    ON CONFLICT (typename) DO NOTHING;

    -- Get import strategy: "Import only (ignores new columns)" — we control the schema
    SELECT importstrategyid INTO v_strategy_id
    FROM dba.timportstrategy
    WHERE importstrategyid = 2
    LIMIT 1;

    -- Freer Gallery artworks (3 manifests: F1909.174, F1911.494, F1916.580)
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob, import_mode
    ) VALUES (
        'IIIF_Freer_Artworks', 'IIIF', 'Artwork',
        '/app/data/source/iiif', '/app/data/archive/iiif',
        'iiif_freer_artworks_.*\.json', 'JSON',
        'static', 'Artwork',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.tiiif_artwork', v_strategy_id, TRUE, FALSE, 'file'
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        file_type = EXCLUDED.file_type,
        target_table = EXCLUDED.target_table,
        is_active = EXCLUDED.is_active;

    -- Getty Museum artworks (Linked Art API for provenance)
    INSERT INTO dba.timportconfig (
        config_name, datasource, datasettype,
        source_directory, archive_directory, file_pattern, file_type,
        metadata_label_source, metadata_label_location,
        dateconfig, datelocation, dateformat, delimiter,
        target_table, importstrategyid, is_active, is_blob, import_mode
    ) VALUES (
        'IIIF_Getty_Artworks', 'IIIF', 'Artwork',
        '/app/data/source/iiif', '/app/data/archive/iiif',
        'iiif_getty_artworks_.*\.json', 'JSON',
        'static', 'Artwork',
        'static', NULL, 'yyyy-MM-dd', NULL,
        'feeds.tiiif_artwork', v_strategy_id, TRUE, FALSE, 'file'
    ) ON CONFLICT (config_name) DO UPDATE SET
        source_directory = EXCLUDED.source_directory,
        archive_directory = EXCLUDED.archive_directory,
        file_pattern = EXCLUDED.file_pattern,
        file_type = EXCLUDED.file_type,
        target_table = EXCLUDED.target_table,
        is_active = EXCLUDED.is_active;

    RAISE NOTICE 'Created 2 IIIF import configurations (Freer Gallery + Getty Museum Artworks)';
END $$;

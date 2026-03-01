-- ============================================================================
-- Table: feeds.tiiif_artwork
-- Purpose: Artwork records ingested from Smithsonian IIIF manifests, including
--          IIIF service metadata, descriptive fields, and local image storage refs.
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'tiiif_artwork') THEN
        CREATE TABLE feeds.tiiif_artwork (
            record_id        SERIAL PRIMARY KEY,
            datasetid        INT NOT NULL,

            -- IIIF manifest identity
            manifest_id      VARCHAR(100) NOT NULL,       -- e.g. FS-6542_02
            manifest_url     TEXT NOT NULL,               -- https://ids.si.edu/ids/manifest/FS-6542_02
            iiif_service_url TEXT,                        -- https://ids.si.edu/ids/iiif/FS-6542_02
            iiif_profile     VARCHAR(200),                -- http://iiif.io/api/image/2/level2.json

            -- Artwork descriptive fields (all from manifest metadata[] array)
            accession_number VARCHAR(50),                 -- F1909.174
            title            TEXT NOT NULL,
            artist           TEXT,                        -- nullable; absent on many records
            medium           TEXT,                        -- Ink and color on silk
            dimensions_text  VARCHAR(200),                -- 25.5 x 24.2 cm (10 1/16 x 9 1/2 in)
            date_text        VARCHAR(100),                -- 1368-1644
            period           VARCHAR(100),                -- Ming dynasty
            origin           VARCHAR(100),                -- China
            artwork_type     VARCHAR(100),                -- Painting
            description      TEXT,
            collection       VARCHAR(200),                -- Freer Gallery of Art Collection
            data_source      VARCHAR(200),                -- National Museum of Asian Art
            credit_line      TEXT,                        -- Gift of Charles Lang Freer

            -- Rights and identity
            ark_guid           TEXT,                      -- Smithsonian: http://n2t.net/ark:/65665/ye3...
            metadata_usage     TEXT,                      -- CC0 | Not determined | CC BY 4.0 | (Getty: full HTML rights statement)

            -- Multi-value fields
            topics             TEXT[],                    -- {'landscape','pine tree','mountain',...}
            exhibition_history JSONB,                     -- [{"name":"On the River","dates":"April 01, 1995..."}, ...]

            -- Linked data API link (seeAlso in Getty manifests)
            api_url            TEXT,                      -- https://data.getty.edu/museum/collection/object/{uuid}

            -- Image metadata (from canvas/resource)
            image_url        TEXT,                        -- full IIIF download URL
            image_width      INT,                         -- pixels
            image_height     INT,                         -- pixels
            image_format     VARCHAR(50),                 -- image/jpeg

            -- Manifest-level attribution
            attribution      TEXT,                        -- Smithsonian Institution (Getty: full HTML attribution paragraph)
            license_url      TEXT,                        -- https://www.si.edu/termsofuse

            -- Local file storage
            local_directory  VARCHAR(500),                -- /app/data/images/iiif/
            local_filename   VARCHAR(200),                -- FS-6542_02.jpg

            -- Overflow: full raw metadata[] array from manifest for fields not explicitly mapped
            raw_metadata     JSONB,

            -- Audit columns
            created_date     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by       VARCHAR(50) NOT NULL DEFAULT CURRENT_USER,

            CONSTRAINT fk_tiiif_artwork_dataset
                FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid),

            CONSTRAINT uq_tiiif_artwork_manifest_dataset
                UNIQUE (manifest_id, datasetid)
        );

        CREATE INDEX idx_tiiif_artwork_dataset   ON feeds.tiiif_artwork(datasetid);
        CREATE INDEX idx_tiiif_artwork_accession ON feeds.tiiif_artwork(accession_number);
        CREATE INDEX idx_tiiif_artwork_manifest  ON feeds.tiiif_artwork(manifest_id);

        COMMENT ON TABLE feeds.tiiif_artwork IS
            'Artwork records from Smithsonian IIIF manifests. Each row is one artwork/canvas.';
        COMMENT ON COLUMN feeds.tiiif_artwork.manifest_id IS
            'IIIF manifest identifier, used to construct manifest_url and image_url.';
        COMMENT ON COLUMN feeds.tiiif_artwork.raw_metadata IS
            'Full metadata[] array from IIIF manifest as JSONB, for fields not explicitly mapped.';
        COMMENT ON COLUMN feeds.tiiif_artwork.local_directory IS
            'Host-mounted directory where the downloaded image file is stored.';
        COMMENT ON COLUMN feeds.tiiif_artwork.local_filename IS
            'Filename of the downloaded image (e.g. FS-6542_02.jpg).';
    END IF;
END $$;

-- Add new columns to existing tables (idempotent)
ALTER TABLE IF EXISTS feeds.tiiif_artwork ADD COLUMN IF NOT EXISTS ark_guid         TEXT;
ALTER TABLE IF EXISTS feeds.tiiif_artwork ADD COLUMN IF NOT EXISTS metadata_usage   TEXT;
ALTER TABLE IF EXISTS feeds.tiiif_artwork ALTER COLUMN metadata_usage TYPE TEXT;
ALTER TABLE IF EXISTS feeds.tiiif_artwork ADD COLUMN IF NOT EXISTS topics           TEXT[];
ALTER TABLE IF EXISTS feeds.tiiif_artwork ADD COLUMN IF NOT EXISTS exhibition_history JSONB;
ALTER TABLE IF EXISTS feeds.tiiif_artwork ADD COLUMN IF NOT EXISTS api_url          TEXT;
ALTER TABLE IF EXISTS feeds.tiiif_artwork ALTER COLUMN attribution TYPE TEXT;

GRANT SELECT ON feeds.tiiif_artwork TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.tiiif_artwork TO app_rw;
GRANT ALL ON feeds.tiiif_artwork TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.tiiif_artwork_record_id_seq TO app_rw;

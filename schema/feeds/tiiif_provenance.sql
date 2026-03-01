-- ============================================================================
-- Table: feeds.tiiif_provenance
-- Purpose: Ordered provenance chain for IIIF artworks (one row per holder).
--          FK to tiiif_artwork; cascades on artwork delete.
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'feeds' AND tablename = 'tiiif_provenance') THEN
        CREATE TABLE feeds.tiiif_provenance (
            provenance_id     SERIAL PRIMARY KEY,
            artwork_id        INT NOT NULL,           -- FK to tiiif_artwork.record_id

            sequence_order    INT NOT NULL,           -- 1 = earliest known holder
            holder_name       TEXT NOT NULL,          -- Charles Lang Freer
            holder_dates      VARCHAR(100),           -- (1854-1919)
            location          VARCHAR(200),           -- Shanghai; New York
            acquisition_notes TEXT,                   -- "purchased from Li in 1911"

            -- Audit
            created_date      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by        VARCHAR(50) NOT NULL DEFAULT CURRENT_USER,

            CONSTRAINT fk_tiiif_provenance_artwork
                FOREIGN KEY (artwork_id) REFERENCES feeds.tiiif_artwork(record_id)
                    ON DELETE CASCADE,

            CONSTRAINT uq_tiiif_provenance_artwork_seq
                UNIQUE (artwork_id, sequence_order)
        );

        CREATE INDEX idx_tiiif_provenance_artwork ON feeds.tiiif_provenance(artwork_id);

        COMMENT ON TABLE feeds.tiiif_provenance IS
            'Ordered provenance chain for IIIF artworks. Rows ordered by sequence_order (1=earliest).';
        COMMENT ON COLUMN feeds.tiiif_provenance.sequence_order IS
            '1-based position in the provenance chain; 1 is the earliest known holder.';
    END IF;
END $$;

GRANT SELECT ON feeds.tiiif_provenance TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.tiiif_provenance TO app_rw;
GRANT ALL ON feeds.tiiif_provenance TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.tiiif_provenance_provenance_id_seq TO app_rw;

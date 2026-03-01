# Plan: Smithsonian IIIF Artwork Ingestion

## Context
The Smithsonian Institution exposes artwork records via the IIIF Presentation API
(base: `https://ids.si.edu/ids/`). Each manifest contains structured descriptive metadata
(title, artist, medium, period, dimensions, accession number, provenance chain, etc.) and
a IIIF Image API service endpoint for downloading the full-resolution image.

This plan models the database tables from the three Freer Gallery examples, creates an IIIF
client, and builds the import job that fetches manifests + downloads images into a local
directory. Provenance is stored in a separate relational table per user request.

**Three example manifests used for schema design:**
| Accession | Manifest ID | Title |
|---|---|---|
| F1909.174 | FS-6542_02 | Fishing by a mountain torrent |
| F1911.494 | FS-7406_30 | Riding a donkey on a mountain road |
| F1916.580 | FS-5908_09 | Standing figure of Lü Dongbin |

**Image download URL pattern:** `https://ids.si.edu/ids/iiif/{manifest_id}/full/full/0/default.jpg`
**Local storage:** `/app/data/images/iiif/` → columns `local_directory` + `local_filename`

---

## Files to Create

| File | Action |
|---|---|
| `schema/feeds/tiiif_artwork.sql` | Main artwork table |
| `schema/feeds/tiiif_provenance.sql` | Provenance chain table (FK to artwork) |
| `etl/clients/iiif_client.py` | IIIF API client |
| `etl/jobs/run_iiif_freer_artworks.py` | Import job script |
| `schema/dba/data/iiif_import_config.sql` | timportconfig seed |

---

## Implementation

### 1. `schema/feeds/tiiif_artwork.sql`

```sql
-- ============================================================================
-- Table: feeds.tiiif_artwork
-- Purpose: Artwork records ingested from Smithsonian IIIF manifests, including
--          IIIF service metadata, descriptive fields, and local image storage refs.
-- ============================================================================
CREATE TABLE IF NOT EXISTS feeds.tiiif_artwork (
    record_id       SERIAL PRIMARY KEY,
    datasetid       INT NOT NULL,

    -- IIIF manifest identity
    manifest_id     VARCHAR(100) NOT NULL,          -- e.g. FS-6542_02
    manifest_url    TEXT NOT NULL,                  -- https://ids.si.edu/ids/manifest/FS-6542_02
    iiif_service_url TEXT,                          -- https://ids.si.edu/ids/iiif/FS-6542_02
    iiif_profile    VARCHAR(200),                   -- http://iiif.io/api/image/2/level2.json

    -- Artwork descriptive fields (all from manifest metadata[] array)
    accession_number VARCHAR(50),                   -- F1909.174
    title           TEXT NOT NULL,
    artist          TEXT,                           -- nullable; absent on many records
    medium          TEXT,                           -- Ink and color on silk
    dimensions_text VARCHAR(200),                   -- 25.5 x 24.2 cm (10 1/16 x 9 1/2 in)
    date_text       VARCHAR(100),                   -- 1368-1644
    period          VARCHAR(100),                   -- Ming dynasty
    origin          VARCHAR(100),                   -- China
    artwork_type    VARCHAR(100),                   -- Painting
    description     TEXT,
    collection      VARCHAR(200),                   -- Freer Gallery of Art Collection
    data_source     VARCHAR(200),                   -- National Museum of Asian Art
    credit_line     TEXT,                           -- Gift of Charles Lang Freer

    -- Image metadata (from canvas/resource)
    image_url       TEXT,                           -- full IIIF download URL
    image_width     INT,                            -- pixels
    image_height    INT,                            -- pixels
    image_format    VARCHAR(50),                    -- image/jpeg

    -- Manifest-level attribution
    attribution     VARCHAR(200),                   -- Smithsonian Institution
    license_url     TEXT,                           -- https://www.si.edu/termsofuse

    -- Local file storage
    local_directory VARCHAR(500),                   -- /app/data/images/iiif/
    local_filename  VARCHAR(200),                   -- FS-6542_02.jpg

    -- Overflow: full raw metadata[] array from manifest for fields not explicitly mapped
    raw_metadata    JSONB,

    -- Audit columns
    created_date    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(50) NOT NULL DEFAULT CURRENT_USER,

    CONSTRAINT fk_tiiif_artwork_dataset
        FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid),

    CONSTRAINT uq_tiiif_artwork_manifest_dataset
        UNIQUE (manifest_id, datasetid)
);

CREATE INDEX IF NOT EXISTS idx_tiiif_artwork_dataset
    ON feeds.tiiif_artwork(datasetid);

CREATE INDEX IF NOT EXISTS idx_tiiif_artwork_accession
    ON feeds.tiiif_artwork(accession_number);

CREATE INDEX IF NOT EXISTS idx_tiiif_artwork_manifest
    ON feeds.tiiif_artwork(manifest_id);

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
```

Grants follow the project pattern (`app_ro` SELECT; `app_rw` SELECT/INSERT/UPDATE; `admin` ALL).

---

### 2. `schema/feeds/tiiif_provenance.sql`

```sql
-- ============================================================================
-- Table: feeds.tiiif_provenance
-- Purpose: Ordered provenance chain for IIIF artworks (one row per holder).
-- ============================================================================
CREATE TABLE IF NOT EXISTS feeds.tiiif_provenance (
    provenance_id   SERIAL PRIMARY KEY,
    artwork_id      INT NOT NULL,                   -- FK to tiiif_artwork.record_id

    sequence_order  INT NOT NULL,                   -- 1 = earliest known holder
    holder_name     TEXT NOT NULL,                  -- Charles Lang Freer
    holder_dates    VARCHAR(100),                   -- (1854-1919)
    location        VARCHAR(200),                   -- Shanghai; New York
    acquisition_notes TEXT,                         -- "purchased from Li in 1911"

    -- Audit
    created_date    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(50) NOT NULL DEFAULT CURRENT_USER,

    CONSTRAINT fk_tiiif_provenance_artwork
        FOREIGN KEY (artwork_id) REFERENCES feeds.tiiif_artwork(record_id)
            ON DELETE CASCADE,

    CONSTRAINT uq_tiiif_provenance_artwork_seq
        UNIQUE (artwork_id, sequence_order)
);

CREATE INDEX IF NOT EXISTS idx_tiiif_provenance_artwork
    ON feeds.tiiif_provenance(artwork_id);

COMMENT ON TABLE feeds.tiiif_provenance IS
    'Ordered provenance chain for IIIF artworks. Rows ordered by sequence_order (1=earliest).';
```

---

### 3. `etl/clients/iiif_client.py`

Extends `BaseAPIClient`. Key methods:

```python
class IIIFClient(BaseAPIClient):
    BASE_URL = 'https://ids.si.edu'

    def get_manifest(self, manifest_id: str) -> dict:
        """Fetch IIIF manifest JSON for a given manifest ID."""
        return self.get(f'/ids/manifest/{manifest_id}')

    def parse_manifest(self, manifest: dict) -> dict:
        """
        Extract structured fields from a raw IIIF manifest.
        Returns flat dict with keys matching tiiif_artwork columns.
        Also returns 'provenance' list and 'raw_metadata' JSONB.
        """
        # Extract metadata[] key/value pairs into a dict
        # Extract canvas dimensions and image resource URL
        # Build image_url: {service_id}/full/full/0/default.jpg
        # Build local_filename: {manifest_id}.jpg
        # Parse provenance from description or metadata if present

    def download_image(self, image_url: str, dest_path: Path) -> int:
        """
        Stream full-resolution IIIF image to dest_path.
        Returns file size in bytes.
        """
        # Use requests streaming to avoid loading full image into memory
        # Write to dest_path with .tmp suffix, rename on success
```

`get_headers()` returns standard User-Agent / Accept headers (no auth needed for Smithsonian public API).

---

### 4. `etl/jobs/run_iiif_freer_artworks.py`

```
CONFIG_NAME = 'IIIF_Freer_Artworks'
IMAGE_DIR   = Path('/app/data/images/iiif')
```

**Manifest IDs to fetch** (the three examples, expandable):
```python
MANIFEST_IDS = ['FS-6542_02', 'FS-7406_30', 'FS-5908_09']
```

**Logic:**

1. `--dry-run` arg (standard)
2. Open `JobRunLogger`
3. **Step 1 — `data_collection` / "Manifest Fetch":**
   - For each manifest ID: call `client.get_manifest()` → `client.parse_manifest()`
   - Download image via `client.download_image()` to `IMAGE_DIR/{manifest_id}.jpg`
     - On dry-run: skip download, set `local_filename = None`
   - Build record dict matching `tiiif_artwork` columns
   - `save_json(records, CONFIG_NAME, source='iiif')`
   - `complete_step(records_in=len(MANIFEST_IDS), records_out=len(records))`
4. **Step 2 — `db_import`:**
   - `run_generic_import(CONFIG_NAME, dry_run, job_run_logger=job_log)`
   - Provenance rows inserted separately after the main import via a post-import step that reads the saved JSON and inserts into `tiiif_provenance`

> **Note on provenance insert:** Since `generic_import` only handles one target table, provenance
> rows are inserted in a dedicated Step 3 using `db_transaction` directly, after the main import
> populates `record_id` values that can be looked up by `manifest_id`.

---

### 5. `schema/dba/data/iiif_import_config.sql`

Standard `DO $$ ... ON CONFLICT DO UPDATE` seed:

```sql
INSERT INTO dba.timportconfig (
    config_name, datasource, datasettype, target_table,
    source_directory, archive_directory, file_pattern, file_type,
    metadata_label_source, dateconfig, dateformat, import_mode, is_active
) VALUES (
    'IIIF_Freer_Artworks', 'IIIF', 'Artwork',
    'feeds.tiiif_artwork',
    '/app/data/source/iiif', '/app/data/archive/iiif',
    'iiif_freer_artworks_*.json', 'JSON',
    'static', 'static', NULL, 'file', TRUE
) ON CONFLICT (config_name) DO UPDATE SET ...;
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Provenance storage | Separate `tiiif_provenance` table | User specified; enables filtering by holder |
| Local path | `local_directory` + `local_filename` columns | Easy to relocate a batch by updating directory only |
| Variable metadata | `raw_metadata JSONB` overflow column | Captures any new fields without schema changes |
| Artwork type field | `artwork_type` (not `type`) | Avoids SQL reserved word conflict |
| Unique constraint | `(manifest_id, datasetid)` | Consistent with all other feeds tables |
| Schema | `feeds` schema | Raw external data, same as all other imported datasets |

---

## Verification

1. Apply schema and confirm tables exist:
   ```bash
   docker compose exec db psql -U tangerine_admin -d tangerine_db \
     -c "\dt feeds.tiiif*"
   ```
2. Dry-run the job:
   ```bash
   docker compose exec tangerine python etl/jobs/run_iiif_freer_artworks.py --dry-run
   ```
3. Live run — fetches 3 manifests, downloads 3 images, loads to DB:
   ```bash
   docker compose exec tangerine python etl/jobs/run_iiif_freer_artworks.py
   ls -lh /opt/tangerine/.data/etl/images/iiif/
   ```
4. Verify DB rows:
   ```sql
   SELECT manifest_id, accession_number, title, image_width, image_height,
          local_directory, local_filename
   FROM feeds.tiiif_artwork;

   SELECT a.accession_number, p.sequence_order, p.holder_name, p.holder_dates
   FROM feeds.tiiif_provenance p
   JOIN feeds.tiiif_artwork a ON a.record_id = p.artwork_id
   ORDER BY a.accession_number, p.sequence_order;
   ```

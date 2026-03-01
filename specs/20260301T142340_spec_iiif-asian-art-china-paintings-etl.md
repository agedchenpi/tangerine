# Plan: IIIF Asian Art China Paintings ETL

## Context
The user wants to bulk-import all Chinese paintings from the Smithsonian National Museum of Asian Art
(`asia.si.edu`) — approximately 585 records reachable via the Smithsonian Open Access API.  For each
painting the pipeline must: (1) fetch the IIIF manifest, (2) download the full-resolution image to
`/app/data/images/iiif/`, and (3) populate `feeds.tiiif_artwork` + `feeds.tiiif_provenance` using the
existing generic_import infrastructure.  The existing `run_iiif_freer_artworks.py` (3 hardcoded IDs)
serves as the template; this new script extends that pattern to ~585 dynamically-discovered records.

---

## Approach

### Discovery: Smithsonian Open Access API
Query `https://api.si.edu/openaccess/api/v1.0/search` to get all Chinese paintings from FSG:

```
q=unit_code:FSG AND object_type:Paintings AND place:China
rows=1000  (max per page)
start=0    (offset, increment by rows until exhausted)
api_key=DEMO_KEY
```

Each result item contains `online_media.media[].idsId` (e.g. `"FS-7406_41"`) — these ARE the IIIF
manifest IDs, usable directly with the existing `IIIFClient.get_manifest(manifest_id)`.  Take `media[0].idsId`
as the primary manifest (one image per artwork record).

### ETL Script
Mirror `run_iiif_freer_artworks.py` exactly, adding a `discover_manifest_ids()` function and a
`manifest_discovery` JobRunLogger step before `data_collection`.

---

## Files to Create / Modify

| Action | File |
|--------|------|
| **Create** | `etl/jobs/run_iiif_asian_art_china_paintings.py` |
| **Modify** | `schema/dba/data/iiif_import_configs.sql` — append new config block |

---

## Implementation Details

### 1. `etl/jobs/run_iiif_asian_art_china_paintings.py`

```
CONFIG_NAME = 'IIIF_AsianArt_China_Paintings'
IMAGE_DIR   = Path('/app/data/images/iiif')

SI_API_BASE = 'https://api.si.edu/openaccess/api/v1.0'
SI_API_KEY  = 'DEMO_KEY'    # ~2-3 discovery calls only; well within free limit
```

**Functions** (reuse logic from `run_iiif_freer_artworks.py`):

| Function | Description |
|----------|-------------|
| `discover_manifest_ids()` | Paginate SI API (`rows=1000, start=0,1000,...`), collect `idsId` from `online_media.media[0]`; skip items with no `online_media` |
| `collect_records(manifest_ids, dry_run)` | Loop over IDs, call `IIIFClient.get_manifest()` + `parse_manifest()`, download image to `IMAGE_DIR/{manifest_id}.jpg` (skip if file exists) |
| `transform(records)` | Strip `provenance` key, add audit columns, JSON-serialize `raw_metadata` — identical to Freer version |
| `insert_provenance(records, dry_run)` | Identical to Freer version |

**4-step `main()`**:
1. `manifest_discovery` — call `discover_manifest_ids()`; fail fast if 0 returned
2. `data_collection` — call `collect_records()` + `transform()` + `save_json()`
3. `db_import` — call `run_generic_import(CONFIG_NAME, dry_run, job_run_logger=job_log)`
4. `provenance_insert` — call `insert_provenance()`

**Resilience details**:
- Image skip: `if dest.exists(): record['local_filename'] = dest.name; continue`
- Per-manifest try/except (log error, continue) — mirrors Freer script
- `ON CONFLICT DO NOTHING` is already in the `insert_provenance` SQL and `generic_import` handles
  upsert via the existing conflict strategy on `(manifest_id, datasetid)`

### 2. `schema/dba/data/iiif_import_configs.sql` — append inside existing DO $$ block

```sql
-- Asian Art Museum — Chinese Paintings (SI Open Access API discovery)
INSERT INTO dba.timportconfig (
    config_name, datasource, datasettype,
    source_directory, archive_directory, file_pattern, file_type,
    metadata_label_source, metadata_label_location,
    dateconfig, datelocation, dateformat, delimiter,
    target_table, importstrategyid, is_active, is_blob, import_mode
) VALUES (
    'IIIF_AsianArt_China_Paintings', 'IIIF', 'Artwork',
    '/app/data/source/iiif', '/app/data/archive/iiif',
    'iiif_asian_art_china_paintings_.*\.json', 'JSON',
    'static', 'Artwork',
    'static', NULL, 'yyyy-MM-dd', NULL,
    'feeds.tiiif_artwork', v_strategy_id, TRUE, FALSE, 'file'
) ON CONFLICT (config_name) DO UPDATE SET ...;
```

---

## Key Reused Utilities

| Utility | Path |
|---------|------|
| `IIIFClient` (manifest fetch, image download, parse) | `etl/clients/iiif_client.py` |
| `save_json`, `run_generic_import`, `JobRunLogger`, `audit_cols` | `etl/base/import_utils.py` |
| `db_transaction`, `fetch_dict` | `common/db_utils.py` |
| `get_logger` | `common/logging_utils.py` |
| `feeds.tiiif_artwork`, `feeds.tiiif_provenance` schema | `schema/feeds/tiiif_artwork.sql`, `tiiif_provenance.sql` |

---

## Verification

```bash
# Dry run (no DB writes, no image downloads)
docker compose exec app python etl/jobs/run_iiif_asian_art_china_paintings.py --dry-run

# Full run
docker compose exec app python etl/jobs/run_iiif_asian_art_china_paintings.py

# Confirm records in DB
docker compose exec db psql -U postgres -c \
  "SELECT count(*) FROM feeds.tiiif_artwork WHERE manifest_id NOT LIKE 'FS-6542%';"

# Check provenance
docker compose exec db psql -U postgres -c \
  "SELECT count(*) FROM feeds.tiiif_provenance;"

# Check images on disk
ls /opt/tangerine/data/images/iiif/ | wc -l
```

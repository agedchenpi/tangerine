# Plan: Getty Museum Open-Content Paintings ETL

## Context

The Getty Museum has 768 open-content paintings visible at:
`https://www.getty.edu/art/collection/search?open_content=true&images=true&classification_and_object_type=Painting`

An existing job `run_iiif_getty_artworks.py` already handles Getty IIIF imports but has only 1
hardcoded manifest UUID (Self-Portrait, Yawning). The full infrastructure is in place — `IIIFClient`
already has Getty-specific methods (`get_manifest_url`, `get_linked_art`,
`parse_linked_art_provenance`), and `IIIF_Getty_Artworks` is already registered in `dba.timportconfig`.
The goal is to add dynamic discovery of all 768 paintings and expand the job accordingly.

---

## API Feasibility: Yes — Getty SPARQL Endpoint

Research confirms Getty exposes a SPARQL endpoint at:
```
https://data.getty.edu/museum/collection/sparql
```

The Getty's Linked Art data model stores all collection objects as RDF triples queryable via SPARQL.
Each open-content painting has:
- Type: `crm:E22_Human-Made_Object` classified as AAT `300033618` (Paintings)
- Rights: `http://creativecommons.org/publicdomain/zero/1.0/` (CC0)
- IIIF manifest URL embedded in `la:equivalent` (e.g. `https://media.getty.edu/iiif/manifest/{uuid}`)

The SPARQL endpoint accepts HTTP POST with `Content-Type: application/sparql-query`. WebFetch GET
returns 400 (correct — SPARQL requires POST), confirming the endpoint is live. A GET to the SPARQL UI
at `/sparql-ui` confirmed the endpoint address and that it uses standard Yasgui interface.

**No web scraping needed.** The Getty website is a Vue.js SPA (not scrapeable without Playwright),
but SPARQL is the official, approved query mechanism.

---

## Approach: SPARQL Discovery → Existing IIIF + Linked Art Flow

### Discovery Query
```sparql
PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX la:  <https://linked.art/ns/terms/>

SELECT DISTINCT ?manifest WHERE {
  ?obj a crm:E22_Human-Made_Object ;
       crm:P2_has_type <http://vocab.getty.edu/aat/300033618> ;
       la:equivalent   ?manifest .
  FILTER(CONTAINS(STR(?manifest), "media.getty.edu/iiif/manifest"))
  FILTER EXISTS {
    ?obj crm:P104_is_subject_to ?right .
    FILTER(CONTAINS(STR(?right), "publicdomain/zero"))
  }
}
```

Returns IIIF manifest URLs. Extract UUID from URL suffix. Expected: ~768 results.

> **Note on SPARQL predicates**: The query above is based on the Getty Linked Art data model and the
> `HumanMadeObject` response observed for object `fb3dce25-68d9-415a-b57f-6efdf963027f`. If the
> predicate for rights differs (e.g. `crm:P75_is_protected_by`), the query needs adjustment — the
> first thing to verify in the dry-run step.

### ETL Flow (all infrastructure already exists)
1. `manifest_discovery` — POST SPARQL query → extract UUIDs → ~768 manifest URLs
2. `data_collection` — for each UUID:
   - `client.get_manifest_url(f"https://media.getty.edu/iiif/manifest/{uuid}")` → manifest
   - `client.parse_manifest(manifest)` → artwork dict
   - `client.get_linked_art(record['api_url'])` → provenance JSON-LD (seeAlso field)
   - `client.parse_linked_art_provenance(linked_art)` → provenance list
   - `client.download_image(record['image_url'], dest)` (skip if file exists)
3. `db_import` — `run_generic_import('IIIF_Getty_Artworks', dry_run, job_log)`
4. `provenance_insert` — `insert_provenance(raw_records, dry_run)`

---

## Files to Modify

| File | Change |
|------|--------|
| `etl/jobs/run_iiif_getty_artworks.py` | Add `discover_manifest_uuids()` using SPARQL POST, expand `main()` to 4 steps, add image-skip logic |

**No DB changes needed** — `IIIF_Getty_Artworks` config already in `dba.timportconfig`.

---

## Implementation Details

### `discover_manifest_uuids()` function
```python
SPARQL_ENDPOINT = 'https://data.getty.edu/museum/collection/sparql'

SPARQL_QUERY = """
PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX la:  <https://linked.art/ns/terms/>

SELECT DISTINCT ?manifest WHERE {
  ?obj a crm:E22_Human-Made_Object ;
       crm:P2_has_type <http://vocab.getty.edu/aat/300033618> ;
       la:equivalent   ?manifest .
  FILTER(CONTAINS(STR(?manifest), "media.getty.edu/iiif/manifest"))
  FILTER EXISTS {
    ?obj crm:P104_is_subject_to ?right .
    FILTER(CONTAINS(STR(?right), "publicdomain/zero"))
  }
}
"""
```

POST to `SPARQL_ENDPOINT` with headers:
- `Content-Type: application/sparql-query`
- `Accept: application/sparql-results+json`

Parse response `.json()['results']['bindings']`, extract each `row['manifest']['value']`, then split on
`/` to get the UUID suffix. Return deduplicated, sorted list of UUIDs.

### Changes to `collect_records(manifest_uuids, dry_run)`
- Accept `manifest_uuids` list (was no arg, used global `MANIFEST_IDS`)
- Add image-skip logic (same as Asian Art script):
  ```python
  dest = IMAGE_DIR / f"{uuid}.jpg"
  if dest.exists():
      record['local_filename'] = dest.name
  else:
      client.download_image(record['image_url'], dest)
      record['local_filename'] = dest.name
  ```

### `main()` — 4-step structure
```
Step 1: manifest_discovery  → discover_manifest_uuids()
Step 2: data_collection     → collect_records(manifest_uuids, dry_run)
Step 3: db_import           → run_generic_import(CONFIG_NAME, dry_run, job_log)
Step 4: provenance_insert   → insert_provenance(raw_records, dry_run)
```

---

## Key Reused Utilities

| Utility | Path |
|---------|------|
| `IIIFClient.get_manifest_url()` | `etl/clients/iiif_client.py` |
| `IIIFClient.parse_manifest()` | `etl/clients/iiif_client.py` |
| `IIIFClient.get_linked_art()` | `etl/clients/iiif_client.py` |
| `IIIFClient.parse_linked_art_provenance()` | `etl/clients/iiif_client.py` |
| `IIIFClient.download_image()` | `etl/clients/iiif_client.py` |
| `save_json`, `run_generic_import`, `JobRunLogger` | `etl/base/import_utils.py` |
| `db_transaction`, `fetch_dict` | `common/db_utils.py` |
| `IIIF_Getty_Artworks` config | already in `dba.timportconfig` (config_id=37 or similar) |

---

## Verification

```bash
# Step 1 — Test SPARQL query alone (dry run shows discovery count)
docker compose exec tangerine python etl/jobs/run_iiif_getty_artworks.py --dry-run
# Expect: "Discovered N unique manifest UUIDs" — verify N ≈ 768

# Step 2 — Full run (768 manifests + Linked Art + images)
docker compose exec tangerine python etl/jobs/run_iiif_getty_artworks.py

# Step 3 — Confirm DB counts
docker compose exec db psql -U tangerine_admin -d tangerine_db -c \
  "SELECT count(*) FROM feeds.tiiif_artwork WHERE manifest_id LIKE '%-%-%-%-%';"
# Note: Getty manifest IDs are UUIDs (have 4 hyphens); Freer/Smithsonian IDs start with 'FS-'

# Step 4 — Check images on disk
docker compose exec tangerine ls /app/data/images/iiif/ | grep -v 'FS-' | wc -l
```

### If SPARQL count ≠ 768
- Try alternative SPARQL predicate for rights: `crm:P75_is_protected_by` instead of `crm:P104_is_subject_to`
- Or remove the rights filter and filter locally (in `parse_manifest`) on `license_url` containing `publicdomain/zero`
- As absolute fallback, inspect browser network calls on the collection search page to find the internal XHR API endpoint (avoids Playwright)

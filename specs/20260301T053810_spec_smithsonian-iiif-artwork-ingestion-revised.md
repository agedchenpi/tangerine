# Plan: Smithsonian IIIF Artwork Ingestion (Revised)

## Context
The Smithsonian Institution exposes artwork records via the IIIF Presentation API
(base: `https://ids.si.edu/ids/`). Each manifest contains structured descriptive metadata
and a IIIF Image API service endpoint for downloading the full-resolution image.

**IIIF Content Search API — not applicable:**
Researched and probed. Smithsonian does NOT implement IIIF Content Search API endpoints
for these artworks (all tested patterns return 404). The Content Search API is designed for
annotation-level data (OCR text, researcher tags on manuscripts) — not relevant for these
paintings. The IIIF manifest is the sole authoritative source.

**Three example manifests used for schema design:**
| Accession | Manifest ID | Title | Metadata Usage |
|---|---|---|---|
| F1909.174 | FS-6542_02 | Fishing by a mountain torrent | CC0 |
| F1911.494 | FS-7406_30 | Riding a donkey on a mountain road | Not determined |
| F1916.580 | FS-5908_09 | Standing figure of Lü Dongbin | CC0 |

**Image download URL pattern:** `https://ids.si.edu/ids/iiif/{manifest_id}/full/full/0/default.jpg`
**Local storage:** `/app/data/images/iiif/` → columns `local_directory` + `local_filename`

### Additional metadata fields found in manifests (not in original schema)
| Field | Label in manifest | Notes |
|---|---|---|
| `ark_guid` | `"Guid"` | ARK persistent identifier, e.g. `http://n2t.net/ark:/65665/...` |
| `metadata_usage` | `"Metadata Usage"` | Rights: `"CC0"` or `"Not determined"` |
| `topics` | `"Topic"` (multi) | Multiple keyword entries → store as `TEXT[]` array |
| `exhibition_history` | `"Exhibition History"` (multi) | Multiple entries → store as `JSONB` array |

### Provenance structure confirmed (all three manifests)
The `metadata[]` array uses alternating pairs of `"Provenance"` entries:
```
date header:   "To 1909"
holder detail: "Loon Gu Sai, Beijing, to 1909 [1]"
date header:   "From 1909 to 1919"
holder detail: "Charles Lang Freer (1854-1919), purchased from Loon Gu Sai, Beijing, in 1909 [2]"
date header:   "From 1920"
holder detail: "Freer Gallery of Art, gift of Charles Lang Freer in 1920 [3]"
"Notes:"       ← end of chain; footnotes follow
"[1] See Original Panel List, L.130 ..."
```
→ 3 provenance rows per artwork. Footnotes captured as `acquisition_notes`.

---

## Getty vs Smithsonian Comparison

### Getty Object: "Self-Portrait, Yawning" — Joseph Ducreux (71.PA.56)

**Getty exposes two separate APIs:**
| Source | URL | Content |
|---|---|---|
| IIIF Manifest | `https://media.getty.edu/iiif/manifest/{uuid}` | Presentation 2.x, minimal metadata[] |
| Linked Art API | `https://data.getty.edu/museum/collection/object/{uuid}` | Full structured record incl. provenance |

**How Getty's manifest compares to Smithsonian:**
| Aspect | Smithsonian | Getty |
|---|---|---|
| IIIF version | Presentation 2.x | Presentation 2.x ✓ same |
| Provenance in manifest | ✅ Yes — `"Provenance"` entries in metadata[] | ❌ No — provenance lives in Linked Art API |
| `seeAlso` to API | None | ✅ Links to Linked Art JSON-LD API |
| Number of canvases | 1 | **3** (main, back, framed) |
| Search service | None | None |
| Metadata label names | "Artist", "Medium", "Guid" | "Artist/Maker", "Material", "Date Modified" |
| Rights field | `"Metadata Usage"`: CC0 | `"Rights Statement"`: CC0/CC BY 4.0 |

**Key schema implications:**
1. **Multiple canvases** — Getty has 3 images (main view, back, framed); our schema has one `image_url/width/height/local_filename`. For now: store primary (first) canvas only; this is a known limitation.
2. **Provenance source differs** — for Getty, `_parse_provenance` would return empty (no `"Provenance"` entries in manifest). A Getty job would need to call the Linked Art API separately. The table design is fine; the client call differs.
3. **Label synonyms** — `_LABEL_MAP` already handles "Artist/Maker" → `artist` and "Material" → `medium` patterns; just needs confirmation.
4. **`seeAlso` URL** — Getty manifest has a `seeAlso` field pointing to the Linked Art API. Adding an `api_url` column lets us store this for future enrichment.
5. **`description`** — Getty puts a rich description at the manifest top level (not in metadata[]); Smithsonian sometimes puts it inside metadata[]. Already handled by `parse_manifest`.

**Getty fits the existing schema** with one addition: `api_url` column for the `seeAlso` link.

---

## Files to Modify / Create

| File | Action |
|---|---|
| `schema/feeds/tiiif_artwork.sql` | **Modify** — add 5 new columns (`ark_guid`, `metadata_usage`, `topics`, `exhibition_history`, `api_url`) |
| `schema/feeds/tiiif_provenance.sql` | Already correct — no changes |
| `etl/clients/iiif_client.py` | **Modify** — fix `_parse_provenance`, add `parse_linked_art_provenance`, add `get_linked_art`, extract new fields |
| `etl/jobs/run_iiif_freer_artworks.py` | Already correct — no changes |
| `etl/jobs/run_iiif_getty_artworks.py` | **Create** — Getty job using Linked Art API for provenance |
| `schema/dba/data/iiif_import_configs.sql` | **Modify** — add Getty config entry |

---

## Changes Required

### 1. `schema/feeds/tiiif_artwork.sql` — add 5 columns

Add after `credit_line`:
```sql
-- Rights and identity
ark_guid           TEXT,                           -- Smithsonian: http://n2t.net/ark:/65665/ye3...
metadata_usage     VARCHAR(50),                    -- CC0 | Not determined | CC BY 4.0

-- Multi-value fields stored as arrays/JSONB
topics             TEXT[],                         -- {'landscape','pine tree','mountain',...}
exhibition_history JSONB,                          -- [{"name":"On the River","dates":"April 01, 1995..."}, ...]

-- Linked data API link (seeAlso in Getty manifests)
api_url            TEXT,                           -- https://data.getty.edu/museum/collection/object/{uuid}
```

---

### 2. `etl/clients/iiif_client.py` — five changes

**A. Add Getty label synonyms to `_LABEL_MAP`:**
```python
'artist/maker': 'artist',
'material': 'medium',
'rights statement': 'metadata_usage',
```

**B. `parse_manifest` — extract new fields + `seeAlso`:**
```python
# Multi-value fields
topics = [self._extract_value(m.get('value')) for m in metadata_list if str(m.get('label','')).lower() == 'topic']
exhibitions_raw = [self._extract_value(m.get('value')) for m in metadata_list if str(m.get('label','')).lower() == 'exhibition history']
ark_guid = next((self._extract_value(m.get('value')) for m in metadata_list if str(m.get('label','')).lower() == 'guid'), None)
# metadata_usage comes via _LABEL_MAP (already mapped)

# seeAlso → api_url (Getty pattern)
see_also = manifest.get('seeAlso', [])
if isinstance(see_also, list) and see_also:
    first = see_also[0]
    api_url = first.get('@id') if isinstance(first, dict) else str(first)
elif isinstance(see_also, str):
    api_url = see_also
else:
    api_url = None

# Parse exhibition history strings → JSONB-friendly list of dicts
exhibition_history = self._parse_exhibitions(exhibitions_raw)
```

**C. Replace `_parse_provenance` — Smithsonian alternating-pair pattern:**
```python
def _parse_provenance(self, metadata_list: list) -> list:
    """Parse Smithsonian manifest provenance: alternating date-header/detail pairs."""
    import re
    prov_entries = [m['value'] for m in metadata_list if str(m.get('label', '')).strip() == 'Provenance']

    chain, footnotes, notes_section = [], {}, False
    for entry in prov_entries:
        if entry.strip() == 'Notes:':
            notes_section = True; continue
        if notes_section:
            match = re.match(r'^\[(\d+)\]\s*(.*)', entry)
            if match:
                footnotes[int(match.group(1))] = match.group(2).strip()
        else:
            chain.append(entry)

    rows = []
    for i in range(0, len(chain) - 1, 2):
        date_header = chain[i]      # "To 1909" / "From 1909 to 1919"
        detail = chain[i + 1]       # "Loon Gu Sai, Beijing, to 1909 [1]"
        refs = [int(r) for r in re.findall(r'\[(\d+)\]', detail)]
        detail_clean = re.sub(r'\s*\[\d+\]', '', detail).strip()
        footnote_text = '; '.join(footnotes[r] for r in refs if r in footnotes) or None
        rows.append({
            'sequence_order':    len(rows) + 1,
            'holder_name':       detail_clean,
            'holder_dates':      date_header,
            'location':          None,    # embedded in holder_name string
            'acquisition_notes': footnote_text,
        })
    return rows
```

**D. New `get_linked_art(api_url)` method — fetch Getty Linked Art API:**
```python
def get_linked_art(self, api_url: str) -> dict:
    """Fetch a Linked Art JSON-LD record (e.g. Getty data.getty.edu API)."""
    self.logger.info(f"Fetching Linked Art: {api_url}")
    response = self.session.get(api_url, headers=self.get_headers(), timeout=self.timeout)
    response.raise_for_status()
    return response.json()
```

**E. New `parse_linked_art_provenance(linked_art)` method — Getty provenance from Linked Art:**
```python
def parse_linked_art_provenance(self, linked_art: dict) -> list:
    """
    Parse provenance from Getty Linked Art API `changed_ownership_through[]`.

    Each acquisition entry maps to one provenance row:
      holder_name   ← transferred_title_to[0]._label
      holder_dates  ← timespan.identified_by[0].content  (e.g. "by 1911 -")
      location      ← referred_to_by[classified=ProvLocationStatement].content
      acquisition_notes ← referred_to_by[classified=ProvenanceBiography].content
    """
    rows = []
    for acq in linked_art.get('changed_ownership_through', []):
        holders = acq.get('transferred_title_to', [])
        holder_name = holders[0].get('_label', '') if holders else ''

        activity = (acq.get('part_of') or [{}])[0]
        timespan = activity.get('timespan', {})
        holder_dates = next(
            (n.get('content') for n in timespan.get('identified_by', [])), None
        )

        notes_by_class = {}
        for note in activity.get('referred_to_by', []):
            label = (note.get('classified_as') or [{}])[0].get('_label', '')
            notes_by_class[label] = note.get('content', '')

        rows.append({
            'sequence_order':    len(rows) + 1,
            'holder_name':       holder_name,
            'holder_dates':      holder_dates,
            'location':          notes_by_class.get('Provenance Location Statement'),
            'acquisition_notes': notes_by_class.get('Provenance Biography'),
        })
    return rows
```

**F. Add `_parse_exhibitions` helper:**
```python
def _parse_exhibitions(self, raw: list) -> list:
    """Convert 'Name (dates)' strings to [{'name': ..., 'dates': ...}] dicts."""
    import re
    result = []
    for entry in raw:
        m = re.match(r'^(.*?)\s*\(([^)]+)\)\s*$', entry)
        if m:
            result.append({'name': m.group(1).strip(), 'dates': m.group(2).strip()})
        else:
            result.append({'name': entry.strip(), 'dates': None})
    return result
```

---

### 3. `etl/jobs/run_iiif_getty_artworks.py` — new Getty job

```python
CONFIG_NAME = 'IIIF_Getty_Artworks'
IMAGE_DIR   = Path('/app/data/images/iiif')

# Getty IIIF manifest UUIDs (Presentation 2.x)
MANIFEST_IDS = [
    'ed996cfb-16d9-4b94-af71-49c63ee57343',  # Self-Portrait, Yawning (71.PA.56)
]
MANIFEST_BASE = 'https://media.getty.edu/iiif/manifest'
```

**Key difference from Smithsonian job:**
- After `client.parse_manifest()`, check if `record['api_url']` is set
- If so, call `client.get_linked_art(api_url)` → `client.parse_linked_art_provenance(linked_art)`
- Otherwise provenance = `[]`

Step structure is identical to `run_iiif_freer_artworks.py` (3 steps).

---

### 4. `schema/dba/data/iiif_import_configs.sql` — add Getty config

```sql
-- Getty Museum artworks
INSERT INTO dba.timportconfig (config_name, datasource, datasettype, ..., target_table, ...)
VALUES ('IIIF_Getty_Artworks', 'IIIF', 'Artwork', ..., 'feeds.tiiif_artwork', ...)
ON CONFLICT (config_name) DO UPDATE SET ...;
```

---

## Key Design Decisions (final)

| Decision | Choice | Rationale |
|---|---|---|
| Smithsonian provenance source | `"Provenance"` metadata[] pairs | 3 holders incl. Freer Gallery; has date headers and footnotes |
| Getty provenance source | Linked Art API `changed_ownership_through[]` | Not in manifest; Linked Art has structured holder/date/location/notes |
| `holder_name` | Full cleaned detail line (Smithsonian) / `._label` (Getty) | Splitting name vs location is brittle for Smithsonian |
| `holder_dates` | Date-range header for SI; `timespan.identified_by.content` for Getty | Best available from each source |
| `acquisition_notes` | SI footnote text; Getty "Provenance Biography" note | Preserves archival citations |
| `api_url` | From `seeAlso` in manifest | Captures Getty Linked Art link for provenance + future enrichment |
| `topics` | `TEXT[]` array | Native PG array; queryable with `@>` operator |
| `exhibition_history` | `JSONB` array of `{name, dates}` | Variable structure; not worth a separate table |
| IIIF Content Search | Not used | Smithsonian returns 404; Getty also has no search service in manifest |
| Single canvas | First/primary canvas only | Getty has multiple (main, back, framed); schema designed for one |

---

## Verification

```bash
# Apply schema changes
docker compose exec db psql -U tangerine_admin -d tangerine_db \
  -f /schema/feeds/tiiif_artwork.sql \
  -f /schema/feeds/tiiif_provenance.sql \
  -f /schema/dba/data/iiif_import_configs.sql

# Dry-run both jobs
docker compose exec tangerine python etl/jobs/run_iiif_freer_artworks.py --dry-run
docker compose exec tangerine python etl/jobs/run_iiif_getty_artworks.py --dry-run

# Live run
docker compose exec tangerine python etl/jobs/run_iiif_freer_artworks.py
docker compose exec tangerine python etl/jobs/run_iiif_getty_artworks.py

# Verify
SELECT manifest_id, accession_number, title, metadata_usage,
       array_length(topics, 1) AS num_topics,
       jsonb_array_length(exhibition_history) AS num_exhibitions,
       api_url IS NOT NULL AS has_linked_art
FROM feeds.tiiif_artwork;

SELECT a.accession_number, p.sequence_order, p.holder_name,
       p.holder_dates, p.location, p.acquisition_notes
FROM feeds.tiiif_provenance p
JOIN feeds.tiiif_artwork a ON a.record_id = p.artwork_id
ORDER BY a.accession_number, p.sequence_order;
```

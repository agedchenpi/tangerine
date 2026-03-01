# Plan: Artwork Gallery — Enhanced Filtering + Smart Search

## Context
The gallery page currently has three sidebar filters (Source, Rights, Topic). The user wants
richer filtering driven from the `tiiif_artwork` table's descriptive columns (`date_text`,
`period`, `origin`, `artwork_type`, `medium`) plus a free-text search bar that does smart
ILIKE matching across all searchable fields with native Streamlit autocomplete behaviour.

---

## Files to modify

| File | Action |
|---|---|
| `admin/services/artwork_service.py` | Extend `get_artworks()` + add 5 `get_distinct_*` helpers + 1 search suggestions helper |
| `admin/pages/artwork_gallery.py` | Add search selectbox + 5 new attribute dropdowns to sidebar; pass new params |

No schema changes, no ETL changes, no `app.py` changes.

---

## Design decisions

### Search bar — "smart intellicense" approach
Streamlit 1.39.0 has no native autocomplete `text_input`. However, `st.selectbox` already
provides type-to-filter behaviour natively — this IS the autocomplete experience.

**Solution:** a single `st.selectbox` populated with every searchable value in the DB,
labelled with its field type:

```
"Title: Fishing by a mountain torrent"
"Artist: Anonymous"
"Period: Ming dynasty"
"Manifest ID: FS-6542_02"
"Accession: F1909.174"
"Medium: Ink and color on silk"
"Date: 1368–1644"
"Origin: China"
"Type: Painting"
```

The user types and the selectbox filters suggestions in real time (built-in Streamlit
behaviour). Selecting a suggestion extracts the raw value and passes it to the SQL
`ILIKE` search. First option is always `""` (no search).

This means no custom JS, no extra packages, and works perfectly in 1.39.0.

### 5 structured attribute filters
Standard `["All"] + distinct_values` selectbox pattern, matching existing pages (monitoring,
pipeline_monitor, imports). Each filter maps to a direct `WHERE column = %s` clause.

### Filter order in sidebar
```
🔍 Search          ← new selectbox (type-to-search)
── Attribute Filters ──
Date               ← new
Period             ← new
Origin             ← new
Type               ← new
Medium             ← new
── Existing Filters ──
Source
Rights
Topic
```

---

## `admin/services/artwork_service.py` changes

### Extend `get_artworks()` signature

```python
def get_artworks(
    source: Optional[str] = None,
    rights: Optional[str] = None,
    topic: Optional[str] = None,
    # --- new params ---
    search: Optional[str] = None,        # ILIKE against all text fields
    date_text: Optional[str] = None,     # exact match
    period: Optional[str] = None,
    origin: Optional[str] = None,
    artwork_type: Optional[str] = None,
    medium: Optional[str] = None,
) -> List[Dict[str, Any]]:
```

**SQL for `search`:**
```sql
AND (
    title             ILIKE %s
    OR artist         ILIKE %s
    OR manifest_id    ILIKE %s
    OR accession_number ILIKE %s
    OR medium         ILIKE %s
    OR period         ILIKE %s
    OR origin         ILIKE %s
    OR artwork_type   ILIKE %s
    OR date_text      ILIKE %s
)
```
Pattern value: `f"%{search}%"` — pass the same value 9 times in the params tuple.

### New service functions

```python
def get_distinct_periods() -> List[str]: ...
def get_distinct_origins() -> List[str]: ...
def get_distinct_artwork_types() -> List[str]: ...
def get_distinct_mediums() -> List[str]: ...
def get_distinct_date_texts() -> List[str]: ...
```
Each: `SELECT DISTINCT column FROM feeds.tiiif_artwork WHERE column IS NOT NULL ORDER BY column`

```python
def get_search_suggestions() -> List[Dict[str, str]]:
    """Returns [{field, value}] rows for all searchable text values across all artworks."""
```
UNION query across title, artist, manifest_id, accession_number, medium, period, origin,
artwork_type, date_text — returns `(field, value)` rows, ordered by field then value.

---

## `admin/pages/artwork_gallery.py` changes

### Sidebar — search selectbox
```python
try:
    suggestions = get_search_suggestions()
except Exception:
    suggestions = []

search_options = [""] + [f"{s['field']}: {s['value']}" for s in suggestions]
search_choice = st.selectbox(
    "🔍 Search",
    options=search_options,
    index=0,
    key="gallery_search",
    help="Type to filter suggestions across all fields"
)
search_term = search_choice.split(": ", 1)[1] if search_choice and ": " in search_choice else None
```

### Sidebar — 5 new attribute selectboxes (after search, before existing Source/Rights/Topic)
```python
st.markdown("##### Attribute Filters")

for label, getter, key in [
    ("Date",   get_distinct_date_texts,   "gallery_date"),
    ("Period", get_distinct_periods,      "gallery_period"),
    ("Origin", get_distinct_origins,      "gallery_origin"),
    ("Type",   get_distinct_artwork_types,"gallery_type"),
    ("Medium", get_distinct_mediums,      "gallery_medium"),
]:
    try:
        opts = ["All"] + getter()
    except Exception:
        opts = ["All"]
    selected = st.selectbox(label, opts, key=key)
    # map "All" → None for service call

st.markdown("##### Source & Rights")
# ... existing Source / Rights / Topic filters unchanged ...
```

### Pass all new params to `get_artworks()`
```python
artworks = get_artworks(
    source=source_filter,
    rights=rights_filter,
    topic=topic_value,
    search=search_term,
    date_text=date_filter,
    period=period_filter,
    origin=origin_filter,
    artwork_type=type_filter,
    medium=medium_filter,
)
```

---

## Verification

```bash
docker compose build admin && docker compose up -d admin
# Open http://localhost:8501 → Artwork Gallery

# Test 1: type "Ming" in Search selectbox → suggestions appear, select → gallery narrows
# Test 2: select Origin = "China" → only Chinese artworks shown
# Test 3: combine Medium + Origin filters → correct AND logic
# Test 4: clear all filters → all artworks return
# Test 5: rights + search combined → both conditions applied
```

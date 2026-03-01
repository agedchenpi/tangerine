# Plan: IIIF Collection Explorer — Discovery Only

## Context

The Getty ETL job imported 727 paintings. Before running any more import jobs, the user wants
a lightweight Streamlit page to browse what's available from museum APIs — no importing,
no manifest fetching per artwork, no image downloads. Pure discovery.

The implementation is **already complete** (files are untracked in git). This plan confirms
the scope and what needs to be verified before committing.

---

## Scope: Discovery Only (No Import)

The page has:
- A "Discover Paintings" button (Getty) and a "Search" button (Smithsonian)
- Results table showing what the API returns
- Status column: `✅ Imported` or `🆕 New` (cross-referenced against `feeds.tiiif_artwork`)
- **No import buttons, no ETL triggers, no write operations**

---

## Files (Already Implemented)

| File | Status | Role |
|------|--------|------|
| `admin/pages/collection_explorer.py` | ✅ Created | Two-tab discovery UI |
| `admin/services/collection_explorer_service.py` | ✅ Created | API calls + DB cross-ref |
| `admin/app.py` | ✅ Modified | "Collection Explorer" added to Collections nav |

---

## What Each File Does

### `collection_explorer_service.py`

- **`discover_getty_manifests()`** — POSTs SPARQL to `data.getty.edu/museum/collection/sparql`,
  returns `[{"uuid": "...", "manifest_url": "..."}]`. Reuses `SPARQL_ENDPOINT` + `SPARQL_QUERY`
  constants from `etl/jobs/run_iiif_getty_artworks.py`. One HTTP call, ~1-2s.

- **`discover_smithsonian_artworks(query, max_rows=500)`** — Paginates Smithsonian Open Access API,
  returns `[{"manifest_id", "title", "object_type", "date", "media_count"}]`. No per-item manifest
  fetch. Uses `SI_API_KEY` env var (falls back to `DEMO_KEY`).

- **`get_imported_manifest_ids()`** — `SELECT DISTINCT manifest_id FROM feeds.tiiif_artwork` →
  returns a `set[str]` for O(1) lookup.

### `collection_explorer.py`

- Getty tab: "Discover Paintings" → spinner → metrics (Discovered / Already Imported / New) →
  sortable dataframe with UUID, clickable Manifest URL (LinkColumn), Status
- Smithsonian tab: editable query input (default: FSG China paintings) → "Search" →
  same metrics + dataframe with Manifest ID, Title, Type, Date, Media, Status
- Results stored in `st.session_state` — survive rerenders without re-calling API

---

## Verification

```bash
# Rebuild to pick up untracked files
docker compose build tangerine && docker compose up -d tangerine

# Navigate to: http://localhost:8501 → Collections → Collection Explorer
# Getty tab:        click "Discover Paintings" → ~776 rows, some ✅ Imported
# Smithsonian tab:  click "Search"             → ~500 rows (max_rows cap)
# Confirm no import buttons exist anywhere on the page
```

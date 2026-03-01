# Plan: Getty Filter UI — Collection Explorer

## Context

The Getty tab in Collection Explorer has a single hardcoded "Discover Paintings" button
with no filters. Unlike the Smithsonian (which has a REST API), Getty only exposes a
SPARQL endpoint (`https://data.getty.edu/museum/collection/sparql`) using the CIDOC-CRM
ontology. The existing query hard-codes `aat:300033618` (paintings) as the sole filter.

We'll add a structured filter panel that builds a dynamic SPARQL query, supporting:
- **Object type** (multiselect, using AAT codes)
- **Date range** (year from / to)
- **Culture** (text input → CONTAINS filter on production place label)
- **Medium** (text input → CONTAINS filter on material label)

Results will also return **title** so the discovery table is more useful.

---

## Scope

| File | Change |
|------|--------|
| `admin/pages/collection_explorer.py` | Replace Getty button with filter panel |
| `admin/services/collection_explorer_service.py` | Dynamic SPARQL builder + title in results |
| `etl/jobs/run_iiif_getty_artworks.py` | **No change** — ETL keeps its own hardcoded query |

---

## AAT Object Type Codes

```python
GETTY_OBJECT_TYPES = {
    "Paintings":    "300033618",
    "Drawings":     "300033973",
    "Prints":       "300041273",
    "Sculpture":    "300047090",
    "Ceramics":     "300151343",
    "Photographs":  "300046300",
    "Textiles":     "300231565",
    "Decorative Arts": "300054168",
}
```

---

## Service Layer — `admin/services/collection_explorer_service.py`

### 1. Define constants locally (decouple from ETL job)

```python
GETTY_SPARQL_ENDPOINT = "https://data.getty.edu/museum/collection/sparql"
```

Remove `from etl.jobs.run_iiif_getty_artworks import SPARQL_ENDPOINT, SPARQL_QUERY`.

### 2. New signature

```python
def discover_getty_manifests(
    object_type_aats: list[str] | None = None,  # defaults to ["300033618"] (paintings)
    date_from: int | None = None,
    date_to: int | None = None,
    culture: str = "",
    medium: str = "",
) -> list[dict]:
```

### 3. Dynamic SPARQL builder

```python
def _build_getty_sparql(
    object_type_aats: list[str],
    date_from: int | None,
    date_to: int | None,
    culture: str,
    medium: str,
) -> str:
    lines = [
        "PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>",
        "PREFIX aat: <http://vocab.getty.edu/aat/>",
        "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>",
        "",
        "SELECT DISTINCT ?manifest ?title WHERE {",
        "  ?obj a crm:E22_Human-Made_Object ;",
        "       crm:P67i_is_referred_to_by <http://creativecommons.org/publicdomain/zero/1.0/> ;",
        "       crm:P129i_is_subject_of ?manifest .",
        "  FILTER(CONTAINS(STR(?manifest), 'media.getty.edu/iiif/manifest'))",
        "",
    ]

    # Object type filter
    if len(object_type_aats) == 1:
        lines.append(f"  ?obj crm:P2_has_type <http://vocab.getty.edu/aat/{object_type_aats[0]}> .")
    else:
        values = " ".join(f"<http://vocab.getty.edu/aat/{a}>" for a in object_type_aats)
        lines += [
            f"  VALUES ?objType {{ {values} }}",
            "  ?obj crm:P2_has_type ?objType .",
        ]

    # Title (optional)
    lines += [
        "",
        "  OPTIONAL {",
        "    ?obj crm:P102_has_title ?titleNode .",
        "    ?titleNode crm:P190_has_symbolic_content ?title .",
        "  }",
    ]

    # Date range (optional)
    if date_from or date_to:
        lines += [
            "",
            "  ?obj crm:P108i_was_produced_by ?prod .",
            "  ?prod crm:P4_has_time_span ?ts .",
        ]
        if date_from:
            lines.append(f"  ?ts crm:P82b_end_of_the_end ?endDate .")
            lines.append(f"  FILTER(?endDate >= '{date_from}-01-01'^^xsd:dateTime)")
        if date_to:
            lines.append(f"  ?ts crm:P82a_begin_of_the_begin ?startDate .")
            lines.append(f"  FILTER(?startDate <= '{date_to}-12-31'^^xsd:dateTime)")

    # Culture (optional text CONTAINS on production place label)
    if culture:
        lines += [
            "",
            "  ?obj crm:P108i_was_produced_by ?cultureProduction .",
            "  ?cultureProduction crm:P7_took_place_at ?place .",
            "  ?place rdfs:label ?placeLabel .",
            f"  FILTER(CONTAINS(LCASE(STR(?placeLabel)), '{culture.lower()}'))",
        ]

    # Medium (optional text CONTAINS on material label)
    if medium:
        lines += [
            "",
            "  ?obj crm:P45_consists_of ?mat .",
            "  ?mat rdfs:label ?matLabel .",
            f"  FILTER(CONTAINS(LCASE(STR(?matLabel)), '{medium.lower()}'))",
        ]

    lines.append("}")
    return "\n".join(lines)
```

### 4. Result dict changes

Add `"title"` field (extracted from SPARQL `?title` binding, fallback `""`).
Return list of `{"uuid", "manifest_url", "title"}`.

---

## UI — `admin/pages/collection_explorer.py` — Getty tab only

```
┌─────────────────────────────────────────────────────────┐
│  Object Type  (multiselect, required)                   │
│  [Paintings ×]  ▾                                       │
├─────────────────────────────────────────────────────────┤
│  Date Range (optional)                                  │
│  From year [______]    To year [______]                 │
├─────────────────────────────────────────────────────────┤
│  Culture (optional)    [____________]  e.g. China       │
├─────────────────────────────────────────────────────────┤
│  Medium (optional)     [____________]  e.g. oil         │
├─────────────────────────────────────────────────────────┤
│  ▶ Generated SPARQL  (expander, shows full query)       │
├─────────────────────────────────────────────────────────┤
│  [  Discover  ]                                         │
└─────────────────────────────────────────────────────────┘
```

- **Object Type** — `st.multiselect`, options from `GETTY_OBJECT_TYPES` keys, default `["Paintings"]`
- **Date From / To** — `st.number_input(min_value=1, max_value=2100, step=1, value=None)`
  — placed side-by-side in two columns
- **Culture** — `st.text_input("Culture (optional)", value="", placeholder="e.g. China, Japan")`
- **Medium** — `st.text_input("Medium (optional)", value="", placeholder="e.g. oil, watercolor")`
- **SPARQL expander** — calls `_build_getty_sparql(...)` and shows the string via `st.code(query, language="sparql")`
- **Discover button** — disabled if no object types selected; calls `discover_getty_manifests(object_type_aats=[...], ...)`

Results table: add **Title** column (between UUID and Manifest URL).

---

## Critical Implementation Notes

1. **`rdfs:label` prefix** — add `PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>` to SPARQL for culture/medium text filters.
2. **Date range traversal quirk** — if only date_from or only date_to is set, only one production event binding is needed. Both using the same `?prod`/`?ts` is fine when both are set; but to keep it OPTIONAL-safe, wrap the entire date block in OPTIONAL when desired. For simplicity, make the date filter required (non-OPTIONAL) — objects without date data are excluded. This is acceptable since the user explicitly requested date filtering.
3. **Culture + date both use `?prod`** — these need separate production event variables (`?prod` vs `?cultureProduction`) to avoid accidental join failure when one is missing.
4. **SPARQL query is built at render time** — same as Smithsonian's query string, shown live in expander before clicking Discover.
5. **Service decouples from ETL** — `GETTY_SPARQL_ENDPOINT` defined directly in service; `SPARQL_ENDPOINT` import from ETL job removed.

---

## Verification

```bash
docker compose build admin && docker compose up -d admin

# http://localhost:8501 → Collections → Collection Explorer → Getty Museum tab
# 1. Default: Paintings selected → SPARQL matches old hardcoded query → same results
# 2. Add Drawings → verify VALUES clause appears in generated SPARQL
# 3. Set Date From=1400, Date To=1600 → verify date FILTER lines appear
# 4. Type "China" in Culture → verify place CONTAINS filter appears
# 5. Type "oil" in Medium → verify material CONTAINS filter appears
# 6. Clear all object types → Discover button disabled
# 7. Run a search → results table shows Title column
```

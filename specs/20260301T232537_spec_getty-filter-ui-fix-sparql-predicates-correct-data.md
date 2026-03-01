# Plan: Getty Filter UI — Fix SPARQL Predicates (Correct Data Model)

## Context

The Getty filter UI was implemented but used incorrect SPARQL predicates for culture and
medium filters — based on theoretical CIDOC-CRM rather than the actual Getty triple store.

Research into the Getty Linked Art API (live object inspection at
`data.getty.edu/museum/collection/object/{uuid}`) confirmed the actual data model:

- **Culture** is stored as a `referred_to_by` LinguisticObject classified as `aat:300055768`
  with a `content` text string — NOT as a place/location predicate (`P7_took_place_at`)
- **Medium** is stored as a `referred_to_by` LinguisticObject classified as `aat:300435429`
  (Materials Description) with `content` text — NOT as `P45_consists_of` material entity
- **Title** is most reliably retrieved via `rdfs:label` (confirmed from working example
  queries on openartdata.org) — NOT via `crm:P102_has_title` chain
- **Object type** (`crm:P2_has_type` → AAT) and **date** (`crm:P108i_was_produced_by` →
  `crm:P4_has_time_span` → `P82a`/`P82b`) predicates are correctly modeled

The Getty website (`https://www.getty.edu/art/collection/search`) is a Vue.js SPA that
calls JavaScript APIs not inspectable via static HTTP. SPARQL remains the correct
programmatic access path — it's what the Getty exposes for all structured queries.

---

## Scope

Only one file needs to change:

| File | Change |
|------|--------|
| `admin/services/collection_explorer_service.py` | Fix `_build_getty_sparql()` predicates |

The UI (`admin/pages/collection_explorer.py`) is already correct — no changes needed there.

---

## Correct SPARQL Predicates (Research-Verified)

| Filter | Wrong (current) | Correct |
|--------|-----------------|---------|
| Title | `crm:P102_has_title` / `P190_has_symbolic_content` | `rdfs:label` |
| Culture | `crm:P7_took_place_at` / `rdfs:label` on place | `crm:P67i_is_referred_to_by` typed `aat:300055768` + `crm:P190_has_symbolic_content` |
| Medium | `crm:P45_consists_of` / `rdfs:label` on material | `crm:P67i_is_referred_to_by` typed `aat:300435429` + `crm:P190_has_symbolic_content` |
| Object type | `crm:P2_has_type` → AAT | Same — already correct |
| Date | `crm:P108i_was_produced_by` → `P4_has_time_span` | Same — already correct |

---

## Updated `_build_getty_sparql()` in `admin/services/collection_explorer_service.py`

### Prefixes (no change to existing, `rdfs:` already present)

```sparql
PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX aat: <http://vocab.getty.edu/aat/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
```

### Title block — replace `crm:P102_has_title` with `rdfs:label`

**Remove:**
```sparql
  OPTIONAL {
    ?obj crm:P102_has_title ?titleNode .
    ?titleNode crm:P190_has_symbolic_content ?title .
  }
```

**Replace with:**
```sparql
  OPTIONAL {
    ?obj rdfs:label ?title .
  }
```

### Culture block — replace place predicate with linguistic statement pattern

**Remove:**
```python
lines += [
    "",
    "  ?obj crm:P108i_was_produced_by ?cultureProduction .",
    "  ?cultureProduction crm:P7_took_place_at ?place .",
    "  ?place rdfs:label ?placeLabel .",
    f"  FILTER(CONTAINS(LCASE(STR(?placeLabel)), '{culture.lower()}'))",
]
```

**Replace with:**
```python
lines += [
    "",
    "  ?obj crm:P67i_is_referred_to_by ?cultureStmt .",
    "  ?cultureStmt crm:P2_has_type <http://vocab.getty.edu/aat/300055768> ;",
    "               crm:P190_has_symbolic_content ?cultureText .",
    f"  FILTER(CONTAINS(LCASE(STR(?cultureText)), '{culture.lower()}'))",
]
```

### Medium block — replace material entity predicate with linguistic statement pattern

**Remove:**
```python
lines += [
    "",
    "  ?obj crm:P45_consists_of ?mat .",
    "  ?mat rdfs:label ?matLabel .",
    f"  FILTER(CONTAINS(LCASE(STR(?matLabel)), '{medium.lower()}'))",
]
```

**Replace with:**
```python
lines += [
    "",
    "  ?obj crm:P67i_is_referred_to_by ?mediumStmt .",
    "  ?mediumStmt crm:P2_has_type <http://vocab.getty.edu/aat/300435429> ;",
    "              crm:P190_has_symbolic_content ?mediumText .",
    f"  FILTER(CONTAINS(LCASE(STR(?mediumText)), '{medium.lower()}'))",
]
```

---

## Why This Is Correct

From live inspection of `data.getty.edu/museum/collection/object/08eaed9f-...` (a drawing):

```json
"referred_to_by": [
  {
    "type": "LinguisticObject",
    "classified_as": [{"id": "http://vocab.getty.edu/aat/300055768"}],  // Culture
    "content": "Flemish"
  },
  {
    "type": "LinguisticObject",
    "classified_as": [{"id": "http://vocab.getty.edu/aat/300435429"}],  // Materials Desc
    "content": "Pen and brown ink"
  }
]
```

In SPARQL, `referred_to_by` in JSON-LD maps to `crm:P67i_is_referred_to_by`, which is
already used in the WORKING original query for CC0 rights. So the predicate is confirmed.

---

## Verification

```bash
docker compose build admin && docker compose up -d admin

# http://localhost:8501 → Collections → Collection Explorer → Getty Museum tab

# 1. Default (Paintings only) — expand SPARQL expander, confirm rdfs:label for title
# 2. Type "French" in Culture — SPARQL shows crm:P67i_is_referred_to_by + aat:300055768
# 3. Type "oil" in Medium — SPARQL shows crm:P67i_is_referred_to_by + aat:300435429
# 4. Click Discover — results load with Title column populated
# 5. Date From=1400, To=1600 — results narrow to that range
# 6. Culture "Flemish" + Drawings type — should return Flemish drawings
```

---

## Files Modified

- `admin/services/collection_explorer_service.py` — `_build_getty_sparql()` function only
  (3 targeted edits: title block, culture block, medium block)

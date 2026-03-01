# Plan: Smithsonian Filter UI — Collection Explorer

## Context

The Smithsonian tab in Collection Explorer has a raw Lucene query text box, which
requires knowing the query syntax. The user wants a structured filter panel with
checkboxes/inputs that automatically build the query — keeping the raw query bar
as an optional "extra keywords" escape hatch.

---

## Scope

Only `admin/pages/collection_explorer.py` changes. The service layer
(`discover_smithsonian_artworks(query, max_rows)`) is unchanged — it still takes
a plain query string.

---

## UI Design

Replace the single `st.text_input("Search query", ...)` with a structured filter
panel above the Search button:

```
┌─────────────────────────────────────────────────────────┐
│  Museum Unit (multiselect, required)                    │
│  [FSG ×] [SAAM ×]  ▾                                   │
├─────────────────────────────────────────────────────────┤
│  Object Type  (checkboxes, 4 per row)                   │
│  ☑ Paintings  ☐ Drawings  ☐ Prints  ☐ Sculpture        │
│  ☐ Ceramics   ☐ Photographs  ☐ Textiles                │
├─────────────────────────────────────────────────────────┤
│  Place / Region (optional text)   [____________]        │
├─────────────────────────────────────────────────────────┤
│  Extra keywords  (optional)       [____________]        │
├─────────────────────────────────────────────────────────┤
│  ▶ Generated query  (expander, shows Lucene string)     │
├─────────────────────────────────────────────────────────┤
│  [  Search  ]                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation

### File: `admin/pages/collection_explorer.py` — Smithsonian tab only

**Museum Unit — `st.multiselect`** (defaults to `["FSG"]`):
```
FSG   — National Museum of Asian Art (Freer|Sackler)
SAAM  — Smithsonian American Art Museum
CHNDM — Cooper Hewitt Design Museum
HMSG  — Hirshhorn Museum and Sculpture Garden
NPG   — National Portrait Gallery
NMAI  — National Museum of the American Indian
NMAH  — National Museum of American History
NMNH  — National Museum of Natural History
```

**Object Type — checkboxes in a 4-column grid** (defaults: Paintings=True, rest=False):
```
Paintings | Drawings | Prints | Sculpture
Ceramics  | Photographs | Textiles | (empty)
```

**Place** — `st.text_input("Place / Region", value="China", ...)` — free text

**Extra keywords** — `st.text_input("Additional keywords (optional)", value="", ...)`

**Query builder** (runs on every rerender, shown in expander):
```python
parts = []
if unit_codes:
    parts.append("(" + " OR ".join(f"unit_code:{u}" for u in unit_codes) + ")")
if object_types:
    parts.append("(" + " OR ".join(f'object_type:"{t}"' for t in object_types) + ")")
if place:
    parts.append(f"place:{place}")
if extra_keywords:
    parts.append(extra_keywords)
query = " AND ".join(parts) if parts else "*"
```

**Search button** — passes the built `query` to `discover_smithsonian_artworks(query)`.
Disabled if `not unit_codes` (require at least one unit).

Results display unchanged (metrics + dataframe with Status flags).

---

## Critical Files

| File | Change |
|------|--------|
| `admin/pages/collection_explorer.py` | Replace SI text input with filter panel |
| `admin/services/collection_explorer_service.py` | No change |

---

## Verification

```bash
docker compose up -d admin   # no rebuild needed — Python files are mounted live
# OR if not mounted:
docker compose build admin && docker compose up -d admin

# http://localhost:8501 → Collections → Collection Explorer → Smithsonian Asian Art tab
# 1. Default loads: FSG selected, Paintings checked, Place=China
# 2. Click Search → same results as before (query identical to old default)
# 3. Add SAAM to units, check Drawings → verify generated query updates
# 4. Expand "Generated query" → confirm Lucene string is correct
# 5. Clear all units → Search button disabled
```

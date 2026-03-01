# Action: Rebuild Admin Container

## Context

All code changes for the Getty filter UI are already on disk:

1. **`admin/pages/collection_explorer.py`** — Getty tab has full filter panel:
   - Object Type multiselect (Paintings default)
   - Date From / To number inputs
   - Culture text input
   - Medium text input
   - Generated SPARQL expander
   - Discover button

2. **`admin/services/collection_explorer_service.py`** — `_build_getty_sparql()` has corrected predicates:
   - Title: `rdfs:label` (not `P102_has_title` chain)
   - Culture: `P67i_is_referred_to_by` typed `aat:300055768` (not place predicate)
   - Medium: `P67i_is_referred_to_by` typed `aat:300435429` (not `P45_consists_of`)

The running Docker container still has the **old code** — changes are on disk but the container image hasn't been rebuilt.

## Action Required

```bash
docker compose build admin && docker compose up -d admin
```

Then visit `http://localhost:8501` → Collections → Collection Explorer → Getty Museum tab.

## Expected UI

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

## No code changes needed — just the Docker rebuild.

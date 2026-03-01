# Research: Getty + Freer Gallery — Pull Frequency Decision

## Context
The user wants to decide between automated daily pulls vs manual pulls for the
IIIF artwork ETL (Getty Museum + Freer Gallery / Smithsonian). Two scripts exist
(`run_iiif_getty_artworks.py`, `run_iiif_freer_artworks.py`) with no scheduler
jobs defined yet — currently manual-only.

---

## Important Nuance: Current Pipeline Pulls Known Manifests, Not Discovery

The current ETL scripts do **not** enumerate or search the APIs for new artworks.
They pull **specific, pre-configured manifest IDs**:

| Source | Current Data |
|--------|-------------|
| Getty  | 1 artwork — `ed996cfb-...` (Self-Portrait, Yawning) |
| Freer  | 3 artworks — `FS-6542_02`, `FS-7406_30`, `FS-5908_09` |

So there are actually **two separate questions**:
1. How often should we **refresh metadata** for artworks already in the DB?
2. How do we **discover and add new artworks** to the pipeline?

---

## API Update Cadence (Research Findings)

| Source | Documented Update Frequency | Changelog/Delta Endpoint | Last-Modified Field |
|--------|---------------------------|--------------------------|-------------------|
| **Smithsonian (Freer)** | **Weekly** — explicitly stated in SI Open Access docs | No | Not confirmed |
| **Getty Museum** | Not documented publicly | No | Not confirmed |
| **IIIF standard** | Defines a Change Discovery API 1.0 (timestamp-based) | Yes (if implemented) | Via activity timestamps |

Neither museum exposes a "what changed since date X" endpoint at the IIIF manifest level.
Both are **bulk pull / full-refresh** APIs.

---

## Recommendation

### For metadata refresh (artworks already in DB)
**Weekly is sufficient for both sources**, matching Smithsonian's documented cadence.
Getty has no documented cadence but collections don't change faster than weekly in practice.
The pipeline is idempotent (`ON CONFLICT DO NOTHING`) so re-running is safe.

**Suggested schedule:** Sunday 02:00 UTC — both jobs
```sql
-- Pattern (see coingecko_scheduler_jobs.sql for format)
cron: '0 2 * * 0'  -- weekly, Sunday 02:00 UTC
```

### For new artwork discovery
This is **not currently supported** by the ETL design. Adding new artworks requires
one of:
- **Manual curation** (current approach): add manifest IDs to the script config, run once
- **Search API integration**: query Getty's collection search or Smithsonian's `api.si.edu`
  search endpoint to discover new acquisitions, then pull their manifests
- **Bulk download**: Smithsonian publishes full Open Access data dumps on GitHub
  (`github.com/Smithsonian/OpenAccess`) — updated periodically

---

## Decision Matrix

| Scenario | Recommendation |
|----------|---------------|
| Small curated collection (current) | **Manual pull** when you add new manifest IDs; **weekly refresh** for existing |
| Growing collection, hands-off | **Weekly discovery job** using Smithsonian search API + manual Getty curation |
| Daily is fine, want latest metadata | **Daily is overkill** — neither source updates that frequently |

---

## No Code Changes Required
This is advisory only. If the user decides to add a scheduler job, the pattern is
in `/opt/tangerine/schema/dba/data/coingecko_scheduler_jobs.sql` and would need
a new `iiif_scheduler_jobs.sql` file. Both scripts already support `--dry-run`.

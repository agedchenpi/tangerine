# Plan: Documentation Review & Agentic Prompting Guidance

## Context

The Tangerine project has grown significantly since its initial 1.0.0 release (Jan 2026) — from 8 services to 16, from a handful of ETL jobs to 30, with 19 Streamlit pages and 7 API clients. However, the documentation (CLAUDE.large.md, CHANGELOG.md, codemaps) hasn't kept pace. Additionally, one skill (`streamlit-design`) lacks auto-activation rules, and a dead hook script (`spec-generator.py`) creates confusion. This plan updates all stale documentation and provides recommendations for future agentic prompting improvements.

---

## Tier 1: Fix Broken/Outdated Documentation

### 1A. CLAUDE.large.md — Fix 6 issues

File: `/opt/tangerine/CLAUDE.large.md`

| Line | Issue | Fix |
|------|-------|-----|
| 16 | References `CLAUDE.concise.md` (doesn't exist) | Change to `CLAUDE.md` |
| 57 | References `admin/pages/1_Import_Configs.py` (old naming) | Change to `admin/pages/imports.py` |
| 117-122 | Skills table missing `streamlit-design` | Add row |
| 128-134 | Hooks table lists `spec-generator.py` as active (it's dead) | Remove row, update `build-checker.py` description to include spec generation |
| 217 | References `claude.concise.md` | Change to `CLAUDE.md` |

### 1B. CHANGELOG.md — Add missing Unreleased features

File: `/opt/tangerine/CHANGELOG.md`

The Unreleased section is missing all features added since late January 2026. Add entries for:

**Pages & UI:**
- Far Side Gallery with scrape triggers (daily + backfill from sidebar)
- YouTube Downloader (MP4/MP3 with quality selection)
- Music Visualizer (audio-reactive video generation with cv2 optimizations)
- Media Editor (image/video editing with timeline)
- Artwork Gallery (IIIF artwork viewer with filtering)
- Collection Explorer (cross-collection search)
- Server Monitor Docker cleanup buttons (build cache, unused images/volumes)
- SQL Runner tool
- Pipeline Monitor with retry/manual override

**ETL & Data Sources:**
- Far Side scraper + backfill (`run_farside_daily.py`, `run_farside_backfill.py`)
- 12 New York Fed endpoints (reference rates, SOMA holdings, repo, reverse repo, agency MBS, FX swaps, counterparties, securities lending, guide sheets, treasury, PD statistics, market share)
- Bank of England SONIA rates
- YFinance: commodities (13 futures), US indexes (8), global indexes (7), sector ETFs (11)
- CoinGecko crypto (BTC, ETH, BNB, SOL, XRP)
- IIIF artwork scrapers (Freer, Getty, Asian Art)
- Database backup job, hourly smoketest

**API Clients (`etl/clients/`):**
- `BaseAPIClient` pattern with retry, rate limiting, session management
- 6 clients: newyorkfed, bankofengland, yfinance, coingecko, iiif, farside

**Services (8 new):**
- farside_service, artwork_service, collection_explorer_service, server_monitor_service, youtube_downloader_service, pipeline_monitor_service, holiday_service

**Infrastructure:**
- Docker socket write access for admin container
- New dependencies: beautifulsoup4, opencv-python-headless, docker>=7.0.0, yt-dlp>=2025.1.0
- `.dockerignore` excludes `.data/` to prevent 12GB+ build contexts

**Database Tables:**
- `feeds.tfarside`, `feeds.coingecko_crypto`, `feeds.yfinance_commodities`, `feeds.yfinance_us_indexes`, `feeds.yfinance_global_indexes`, `feeds.yfinance_sector_etfs`, `feeds.bankofengland_sonia_rates`, plus newyorkfed and artwork tables

### 1C. skill-rules.json — Add streamlit-design triggers

File: `/opt/tangerine/.claude/skill-rules.json`

Add entry for `streamlit-design` skill (exists in `.claude/skills/` but has no auto-activation):

```json
"streamlit-design": {
  "type": "domain",
  "priority": "medium",
  "description": "Production-grade Streamlit interface design patterns",
  "promptTriggers": {
    "keywords": ["design", "beautiful", "distinctive", "custom styling", "look better", "improve ui", "dashboard design", "css", "theme", "gradient", "animation", "micro-interaction"],
    "intentPatterns": [
      "(make|create|build).*?(beautiful|distinctive|polished)",
      "(improve|enhance|upgrade).*?(ui|design|look|appearance)",
      "(custom|branded).*?(dashboard|interface|styling)"
    ]
  },
  "fileTriggers": {
    "pathPatterns": ["admin/styles/*.css", "admin/components/*.py"],
    "contentPatterns": ["unsafe_allow_html", "gradient", "@keyframes"]
  }
}
```

---

## Tier 2: Update Codemaps

### 2A. admin-services.md — Add 8 missing services

File: `/opt/tangerine/.claude/codemaps/admin-services.md`

The Service Files table (lines 36-45) lists 8 services but 16 now exist. Add:

| File | Domain | Key Functions |
|------|--------|---------------|
| `holiday_service.py` | Holiday management | get_holidays, create_holiday, delete_holiday |
| `farside_service.py` | Far Side comics | get_comics, get_comic_count, scrape_date, scrape_range |
| `artwork_service.py` | IIIF artwork | get_artworks, get_artwork_count |
| `collection_explorer_service.py` | Collection search | search_collections |
| `server_monitor_service.py` | Server health | get_docker_disk_usage, run_docker_cleanup |
| `youtube_downloader_service.py` | YouTube downloads | get_video_info, download_media |
| `pipeline_monitor_service.py` | Pipeline status | get_pipeline_status, retry_job |

### 2B. etl-framework.md — Add API clients section

File: `/opt/tangerine/.claude/codemaps/etl-framework.md`

Add section documenting `etl/clients/` directory and the `BaseAPIClient` pattern. List all 6 clients with their data sources and patterns (REST API vs web scraping).

### 2C. architecture-overview.md — Update page categories

File: `/opt/tangerine/.claude/codemaps/architecture-overview.md`

Update to reflect 6 navigation groups: Home, Configuration, Operations, Collections, Tools, System. Add `etl/clients/` to key directories.

---

## Tier 3: Cleanup

### 3A. Delete dead spec-generator.py

File: `/opt/tangerine/.claude/hooks/spec-generator.py`

This script is NOT registered in `settings.json`. Its functionality was absorbed into `build-checker.py` (lines 160-189). Remove to prevent confusion.

---

## Tier 4: Future Agentic Prompting Recommendations

These are guidance items to present to the user — not changes to implement now.

### 4A. New Skill: `web-scraper` / `api-client`

The project now has 6 API clients following a consistent `BaseAPIClient` pattern. A dedicated skill would:
- Auto-activate when creating new scrapers or API clients
- Guide toward the established pattern: extend `BaseAPIClient`, implement `get_headers()`, use `_make_request()` for HTML, `.get()` for JSON
- Enforce rate limiting, retry, and atomic download patterns
- Trigger keywords: scraper, api client, beautifulsoup, web scraping, data source

### 4B. Hook Enhancement: File-Aware Skill Activation

Currently `skill-activator.py` only evaluates prompt keywords. The `fileTriggers` section in `skill-rules.json` is defined but never used because file context isn't available at `UserPromptSubmit` time. Options:
1. Add a `PostToolUse:Read` hook that checks recently-read file paths against `fileTriggers.pathPatterns`
2. Accept prompt-only triggering and remove unused `fileTriggers` to reduce config confusion

Recommendation: Option 1 provides higher value — reading a service file should auto-activate `service-developer` even without keyword matches.

### 4C. CHANGELOG Drift Prevention

Add logic to `build-checker.py` Stop hook that detects when new files are created in `admin/pages/`, `admin/services/`, `etl/jobs/`, or `etl/clients/` and reminds the user to update CHANGELOG.md. This prevents the significant drift observed in this review.

### 4D. Codemap Refresh Reminders

Similarly, extend `build-checker.py` to detect new service/page files and suggest running `/update-codemaps`. The current gap of 7 missing services from the codemap shows this drifts quickly.

### 4E. Memory Maintenance

The MEMORY.md index is 69 days old and missing significant additions (Far Side, YouTube, IIIF, etc.). Consider a periodic review cadence or a hook that reminds when memory hasn't been updated after significant feature work.

### 4F. Skill for Media/Creative Tools

The project has grown a media tools surface (Music Visualizer, Media Editor, YouTube Downloader). A `media-tools` skill could guide toward established patterns: progress callbacks, session state for results, atomic file operations, FFmpeg integration.

---

## Verification

After implementation:
1. Confirm `CLAUDE.large.md` has no references to non-existent files — grep for `concise`, `1_Import`
2. Confirm `skill-rules.json` is valid JSON — `python3 -c "import json; json.load(open('.claude/skill-rules.json'))"`
3. Confirm `spec-generator.py` is deleted and not referenced in `settings.json`
4. Read each updated codemap and verify service/page counts match `ls admin/services/ | wc -l` and `ls admin/pages/ | wc -l`
5. Review CHANGELOG entries against `git log --oneline` to ensure completeness

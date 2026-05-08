# Agentic Prompting Improvements

Identified during comprehensive project and documentation review on 2026-05-08.

## Priority: High

### 1. New Skill: `web-scraper` / `api-client`

The project has 6 API clients following a consistent `BaseAPIClient` pattern in `etl/clients/`. A dedicated skill would:
- Auto-activate when creating new scrapers or API clients
- Guide toward the established pattern: extend `BaseAPIClient`, implement `get_headers()`, use `_make_request()` for HTML, `.get()` for JSON
- Enforce rate limiting, retry, and atomic download patterns
- Trigger keywords: scraper, api client, beautifulsoup, web scraping, data source

**Files to create:** `.claude/skills/web-scraper/SKILL.md`, update `.claude/skill-rules.json`

### 2. File-Aware Skill Activation

Currently `skill-activator.py` (UserPromptSubmit hook) only evaluates prompt keywords. The `fileTriggers` section in `skill-rules.json` is defined but never used because file context isn't available at prompt time.

**Proposed:** Add a `PostToolUse:Read` hook that checks recently-read file paths against `fileTriggers.pathPatterns` and injects skill reminders. Example: reading `admin/services/farside_service.py` should auto-activate `service-developer`.

**Files to modify:** `.claude/settings.json` (add PostToolUse:Read hook), create new hook script or extend `skill-activator.py`

### 3. CHANGELOG Drift Prevention

Extend `build-checker.py` (Stop hook) to detect when new files are created in key directories and remind user to update CHANGELOG.md.

**Directories to watch:** `admin/pages/`, `admin/services/`, `etl/jobs/`, `etl/clients/`

**Files to modify:** `.claude/hooks/build-checker.py`

## Priority: Medium

### 4. Codemap Refresh Reminders

Extend `build-checker.py` to detect new service/page files and suggest running `/update-codemaps`. The gap of 7 missing services from the codemap shows this drifts quickly.

**Files to modify:** `.claude/hooks/build-checker.py`

### 5. New Skill: `media-tools`

The project has grown a media tools surface (Music Visualizer, Media Editor, YouTube Downloader). A skill would guide toward established patterns:
- Progress callbacks with `st.progress`
- Session state for storing results across reruns
- Atomic file operations
- FFmpeg integration patterns

**Files to create:** `.claude/skills/media-tools/SKILL.md`, update `.claude/skill-rules.json`

### 6. Memory Maintenance Automation

MEMORY.md went 69 days without updates, missing many additions (Far Side, YouTube, IIIF, etc.). Consider a hook-based reminder after significant feature work (e.g., when >=3 new files are created in a session).

**Files to modify:** `.claude/hooks/build-checker.py`

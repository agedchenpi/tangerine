# Repository Cleanup: Unused Files & Documentation

## Context
The repo has accumulated stale documentation, completed spec files, backup files, and a deprecated function. This plan removes/archives dead weight to keep the codebase clean.

---

## 1. Archive root-level implementation docs → `docs/archive/`

Create `docs/archive/` and move these 9 files:

- `NEWYORKFED_IMPLEMENTATION_SUMMARY.md`
- `NEWYORKFED_FINAL_IMPLEMENTATION_SUMMARY.md`
- `NEWYORKFED_IMPLEMENTATION_COMPLETE.md`
- `NEWYORKFED_BUG_FIX_SUMMARY.md`
- `NEWYORKFED_COMPLETE_MAPPING.md`
- `NEWYORKFED_SCHEMA_ORGANIZATION.md`
- `NEWYORKFED_SCHEMA_VERIFICATION.md`
- `NEWYORKFED_TESTING_SUMMARY.md`
- `REBUILD_IMPLEMENTATION_SUMMARY.md`

Also move `docs/NEWYORKFED_API_ENDPOINTS_RESEARCH.md` → `docs/archive/`

## 2. Delete completed spec files (30 files)

**Dark mode series (Jan 27–29, 17 files):**
- `specs/20260127T085138_spec_fix-dark-mode-sidebar-visibility-theme-persistence.md`
- `specs/20260127T091622_spec_fix-dark-mode-sidebar-header-visibility-css-moveme.md`
- `specs/20260128T024101_spec_fix-dark-mode-text-contrast-issues.md`
- `specs/20260128T032053_spec_fix-dark-mode-tab-text-contrast.md`
- `specs/20260129T002842_spec_wcag-aa-dark-mode-accessibility-compliance.md`
- `specs/20260129T003933_spec_fix-dark-mode-contrast-issues-css-variable-overrid.md`
- `specs/20260129T010000_implementation_comprehensive-dark-mode-accessibility-fix.md`
- `specs/20260129T014625_spec_comprehensive-dark-mode-accessibility-fix-all-text.md`
- `specs/20260129T015811_spec_dark-mode-accessibility-current-state-analysis-req.md`
- `specs/20260129T052043_spec_fix-light-on-light-contrast-issues.md`
- `specs/20260129T053350_spec_fix-dark-mode-gray-text-on-light-backgrounds.md`
- `specs/20260129T055409_spec_fix-white-container-backgrounds-in-dark-mode.md`
- `specs/20260129T063639_spec_fix-metric-card-background-override-in-dark-mode.md`
- `specs/20260129T065131_spec_fix-metric-card-white-backgrounds-in-dark-mode.md`
- `specs/20260129T071127_spec_fix-container-card-white-backgrounds-in-dark-mode.md`
- `specs/20260129T170858_spec_apply-dashboard-s-superior-metric-styling-to-all-p.md`
- `specs/20260129T182508_spec_fix-selectbox-dark-mode-visibility-issues.md`

**NewYorkFed integration (Feb 6–7, 4 files):**
- `specs/20260206T040212_spec_newyorkfed-markets-api-integration-plan.md`
- `specs/20260206T202010_spec_newyorkfed-markets-api-integration-bug-fix-plan.md`
- `specs/20260206T211236_spec_newyorkfed-markets-api-integration-complete-implem.md`
- `specs/20260206T232659_spec_newyorkfed-feeds-tables-debug-and-data-retention-p.md`

**Database rebuild (1 file):**
- `specs/20260207T031106_spec_drop-docker-volume-and-rebuild-database-from-scrat.md`

**Completed UI/UX & documentation specs (8 files):**
- `specs/20260117T051743_spec_streamlit-ui-ux-improvement-with-grouped-navigatio.md`
- `specs/20260117T171543_spec_report-workflow-ui-ux-improvements.md`
- `specs/20260122T060014_spec_ux-improvements-inline-create-for-dependencies.md`
- `specs/20260122T060448_spec_spec-generator-hook-not-triggering.md`
- `specs/20260122T090801_spec_ui-ux-improvements-status-review.md`
- `specs/20260122T091919_spec_dark-light-mode-toggle-theme-contrast-improvements.md`
- `specs/20260123T020907_spec_claude-code-hooks-skills-documentation.md`
- `specs/20260123T021856_spec_update-readme-md-with-diagrams-and-docker-commands.md`

## 3. Delete stale root-level docs

- `claude_doc.md` — superseded by `.claude/hooks/README.md` and skills docs
- `opencode_pickle.md` — old planning doc, not referenced by code

## 4. Delete backup test files

- `tests/ui/test_imports_ui.py.bak`
- `tests/ui/test_reference_data_ui.py.bak`
- `tests/ui/test_scheduler_ui.py.bak`

## 5. Remove deprecated `connect_db()` function

**File:** `common/db_utils.py` (lines 274–291)
- Marked as "Legacy function for backward compatibility"
- Never imported anywhere in the codebase
- Delete the comment + function definition

---

## Files kept (not touched)
- All active pages, services, components, utils — verified in use
- `specs/` files from Feb 7+ (recent/in-progress)
- `specs/ui-ux-enhancement-2026-01.md`, `specs/20260123T023443_spec_repository-cleanup-analysis.md`, `specs/20260124T*` — keeping general reference specs
- `docs/DATABASE_REBUILD_GUIDE.md`, `docs/REBUILD_QUICK_START.md`, `docs/NEWYORKFED_MONITORING_TOOLS.md` — active operational docs
- All `.claude/` configs, codemaps, skills, commands
- `admin/components/tables.py`, requirements packages — per user preference

## Verification
1. `git diff --stat` — confirm only expected files moved/deleted
2. `docker compose up -d --build admin` — verify admin UI starts cleanly
3. `docker compose exec tangerine python -c "from common.db_utils import fetch_dict"` — verify db_utils still imports correctly after removing `connect_db`

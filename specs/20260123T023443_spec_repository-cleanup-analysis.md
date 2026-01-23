# Repository Cleanup Analysis

Review of `/opt/tangerine` for files that may be worth removing.

---

## High Priority - Safe to Remove

### 1. Duplicate Documentation Files

| File | Reason |
|------|--------|
| `/opt/tangerine/CLAUDE.concise.md` | **Exact duplicate** of `CLAUDE.md` (byte-for-byte identical) |
| `/opt/tangerine/dataetlregressionREADME.md` | **Redundant copy** - original exists at `.data/etl/regression/README.md` |

### 2. Empty/Placeholder Files

| File | Reason |
|------|--------|
| `/opt/tangerine/schema/dba/data/tholidays_inserts.sql` | Empty file - contains only `--do later` comment |
| `/opt/tangerine/schema/shared_queries.sql` | Placeholder - only contains `-- Add common queries here...` |
| `/opt/tangerine/common/shared_queries.sql` | Duplicate placeholder (68 bytes, no real content) |
| `/opt/tangerine/admin/styles/__init__.py` | Completely empty (0 bytes) |

### 3. Example/Demo Code (Not Used in Production)

| File | Reason |
|------|--------|
| `/opt/tangerine/etl/jobs/example_etl_job.py` | Demo file - never executed, references non-existent `feeds.example_products` table |
| `/opt/tangerine/etl/extractors/example_api_extractor.py` | Demo file - never imported or instantiated anywhere |

---

## Medium Priority - Should Review

### 4. Outdated/Unreferenced Documentation

| File | Reason |
|------|--------|
| `/opt/tangerine/PROJECT_STATUS.md` | **Outdated** - last updated Jan 14, README.md is current (Jan 23) and more comprehensive |
| `/opt/tangerine/opencode_readme.md` | **Unreferenced** - no imports or references to "opencode" in codebase |
| `/opt/tangerine/opencode_specs.md` | **Unreferenced** - appears to be old external documentation |
| `/opt/tangerine/claude_doc.md` | **Unintegrated** - recently added but not referenced anywhere, overlaps with README |

### 5. Non-Functional Script

| File | Reason |
|------|--------|
| `/opt/tangerine/run_all.sh` | Contains placeholder comments, not actual automation - never completed |

---

## Low Priority - Maintenance

### 6. Unused Python Functions (Dead Code)

**`/opt/tangerine/admin/utils/db_helpers.py`:**
- `get_distinct_values()` - never called
- `get_table_columns()` - shadowed by implementation in `generic_import.py`

**`/opt/tangerine/admin/utils/formatters.py`:**
- `format_date()` - never called
- `format_number()` - never called
- `format_filesize()` - never called
- `format_list()` - never called
- `format_status_badge()` - never called
- `format_null()` - never called

**`/opt/tangerine/admin/components/notifications.py`:**
- `show_validation_error()` - never called
- `show_status()` - never called

**`/opt/tangerine/admin/components/dependency_checker.py`:**
- `render_dependency_status()` - never called from any page

### 7. Empty Schema Directories

These directories exist but contain no files (may have been created for future use):
- `schema/extensions/`, `schema/functions/`, `schema/indexes/`
- `schema/materialized_views/`, `schema/procedures/`, `schema/sequences/`
- `schema/tables/`, `schema/triggers/`, `schema/types/`, `schema/views/`

(All actual schema is in `schema/dba/` subdirectories)

### 8. Build Artifacts (~280 KB)

`__pycache__/` directories - regenerated automatically, can be cleaned:
- `.claude/hooks/__pycache__/`
- `admin/__pycache__/`
- `admin/pages/__pycache__/`
- `admin/components/__pycache__/`
- `admin/services/__pycache__/`
- `admin/utils/__pycache__/`

### 9. Test Artifacts (Should Add to .gitignore)

`/opt/tangerine/.data/etl/regression/archive/` - 35+ test data files created during test execution

---

## Summary

| Priority | Count | Action |
|----------|-------|--------|
| High | 8 files | Safe to delete immediately |
| Medium | 5 files | Review before deleting |
| Low | 11 functions + directories | Code cleanup / maintenance |

---

## Verification

After removal:
1. Run `docker compose up --build` to verify no import errors
2. Run `pytest tests/ -v` to verify tests still pass
3. Check `docker compose logs admin` for any missing module errors

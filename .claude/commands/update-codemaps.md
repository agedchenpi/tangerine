---
name: update-codemaps
description: Refresh architecture codemaps after codebase changes
---

# Update Codemaps Command

Refresh the architecture documentation in `.claude/codemaps/` to reflect current codebase state.

## Codemaps to Update

| File | Source | Focus |
|------|--------|-------|
| `architecture-overview.md` | Project structure | System design, data flow |
| `admin-services.md` | `admin/services/*.py` | Service layer patterns |
| `etl-framework.md` | `etl/` directory | Job structure, extractors |
| `database-schema.md` | `schema/dba/tables/*.sql` | Tables, relationships |
| `email-services.md` | `common/gmail_client.py`, `etl/jobs/run_*.py` | Email integration |
| `pubsub-system.md` | `pubsub/`, `admin/services/pubsub_service.py` | Event system |

## Workflow

1. **Read each codemap** from `.claude/codemaps/`
2. **Read corresponding source files** to check for changes
3. **Compare and identify** outdated sections:
   - New files or modules not documented
   - Removed files still referenced
   - Changed function signatures or patterns
   - New tables or columns
4. **Update outdated sections** with current information
5. **Report changes** made to each codemap

## What to Check

### architecture-overview.md
- New services or pages added?
- Docker services changed?
- Data flow patterns updated?

### admin-services.md
- New service files in `admin/services/`?
- New CRUD functions added?
- Service patterns changed?

### etl-framework.md
- New ETL jobs added?
- New extractors or loaders?
- Import strategies changed?

### database-schema.md
- New tables in `schema/dba/tables/`?
- New stored procedures?
- Column changes?

### email-services.md
- Gmail client changes?
- New report types?
- Inbox processor updates?

### pubsub-system.md
- New event types?
- New subscribers?
- Listener changes?

## Notes

- Run after significant architectural changes
- Each codemap should reflect current codebase state
- Keep codemaps concise but comprehensive
- Update the "Key Files" sections when files are added/removed

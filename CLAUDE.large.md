# CLAUDE.large.md

Extended context file for Claude Code. Use for deep work on complex features.

This file includes the full CLAUDE.md content plus additional architectural context and patterns.

---

## R&D Framework

**Reduce and Delegate** - Core principles for efficient agent operation:

### Reduce
- Load only context needed for the current task
- Use `CLAUDE.concise.md` for quick tasks
- Clear unnecessary context before starting new work
- Monitor usage with `/context`

### Delegate
- Use Task tool with sub-agents for isolated work
- Sub-agent context stays separate from primary
- Delegate: web scraping, code analysis, research
- See `.claude/agents/` for sub-agent prompts

---

## Full Project Context

*(Include everything from CLAUDE.md)*

### Working Instructions

**Load up context prompt:**
Take a look at the app and architecture. Understand deeply how it works inside and out.

**Tool use summaries:**
After completing a task that involves tool use, provide a quick summary.

**Adjust eagerness down:**
Do not jump into implementation unless clearly instructed. Default to providing information and recommendations.

**Use parallel tool calls:**
Call independent tools in parallel. Never use placeholders or guess missing parameters.

**Reduce hallucinations:**
Never speculate about unread code. Read files BEFORE answering.

---

## Architecture Deep Dive

### Vertical Slice Architecture (VSA)

Each feature is self-contained:
```
Feature: Import Configuration
├── UI: admin/pages/1_Import_Configs.py
├── Logic: admin/services/import_config_service.py
├── Data: schema/dba/tables/timportconfig.sql
└── Tests: tests/integration/test_import_config_service.py
```

### Service Layer Pattern

```python
# Standard service structure
def get_all() -> list[dict]:
    """Fetch all records."""

def get_by_id(id: int) -> dict | None:
    """Fetch single record."""

def create(data: dict) -> int:
    """Insert new record, return ID."""

def update(id: int, data: dict) -> bool:
    """Update existing record."""

def delete(id: int) -> bool:
    """Delete record."""
```

### Database Transaction Pattern

```python
from common.db_utils import db_transaction

def create_record(data: dict) -> int:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO dba.ttable (...) VALUES (...) RETURNING id",
                (data['field1'], data['field2'])
            )
            return cur.fetchone()[0]
```

---

## Codemaps Reference

Load relevant codemap for deep architectural context:

| Codemap | Use When |
|---------|----------|
| `architecture-overview.md` | System design, adding components |
| `admin-services.md` | Service layer, CRUD operations |
| `etl-framework.md` | Import jobs, extractors |
| `database-schema.md` | Schema changes, new tables |
| `email-services.md` | Gmail, reports, inbox |
| `pubsub-system.md` | Event system, subscribers |

---

## Skills Quick Reference

| Skill | Triggers | Purpose |
|-------|----------|---------|
| `etl-developer` | etl, import, csv, json | ETL patterns |
| `service-developer` | service, crud | Service CRUD |
| `database-operations` | schema, table, sql | **GUARDRAIL** |
| `streamlit-admin` | streamlit, page, ui | UI patterns |

---

## Hooks System

| Hook | Event | Purpose |
|------|-------|---------|
| `skill-activator.py` | Before prompt | Injects skill reminders |
| `dangerous-command-blocker.py` | Before Bash | **BLOCKS** dangerous commands |
| `file-validator.py` | After Edit/Write | Validates syntax |
| `spec-generator.py` | After ExitPlanMode | Generates specs |
| `build-checker.py` | After response | Linting reminders |

---

## Key Tables

**Configuration:**
- `dba.timportconfig` - Import job configs
- `dba.tdatasource` - Data source reference
- `dba.tdatasettype` - Dataset type reference

**Email:**
- `dba.tinboxconfig` - Inbox processing rules
- `dba.treportmanager` - Report configs
- `dba.tscheduler` - Cron scheduler

**Tracking:**
- `dba.tdataset` - Dataset metadata
- `dba.tlogentry` - ETL logs
- `dba.tpubsub_events` - Event queue

---

## Common Patterns

### Streamlit Form with Validation

```python
with st.form(key="unique_form_key"):
    name = st.text_input("Name", value=existing.get('name', ''))

    if st.form_submit_button("Save"):
        if not name:
            st.error("Name is required")
        elif service.exists_by_name(name):
            st.error("Name already exists")
        else:
            service.create({'name': name})
            st.session_state.success_message = "Created!"
            st.rerun()
```

### ETL Job with Logging

```python
from common.logging_utils import get_etl_logger

logger = get_etl_logger('my_job', run_uuid)

try:
    logger.info("Starting job")
    # ... process ...
    logger.info(f"Processed {count} records")
except Exception as e:
    logger.error(f"Job failed: {e}")
    raise
```

---

## Commands

| Command | Purpose |
|---------|---------|
| `/test` | Run pytest |
| `/run-job` | Execute ETL jobs |
| `/logs` | View Docker logs |
| `/prime` | Prime codebase understanding |
| `/prime_cc` | Prime Claude Code config |
| `/context` | Monitor token usage |
| `/dev-docs` | Create task docs |
| `/doc-feature` | Document completed feature |

---

## When to Use This File

Load `claude.large.md` when:
- Implementing complex features spanning multiple areas
- Need full architectural context
- Working on integration between systems
- Debugging cross-cutting issues

For simpler tasks, use `claude.concise.md` to save context.

---
*A focused agent is a performant agent.*

# Claude Code Hooks & Skills Documentation

This document describes all Claude Code hooks and skills configured for the Tangerine project.

## Overview

**Hooks** are automation scripts that run at specific points in Claude Code's workflow:
- Before user prompts are processed
- Before/after tool executions
- When a conversation stops

**Skills** are domain-specific guideline documents that provide patterns and best practices for different areas of the codebase.

### Configuration Files

| File | Purpose |
|------|---------|
| `.claude/settings.json` | Hook configurations (triggers, commands, timeouts) |
| `.claude/skill-rules.json` | Skill activation rules (keywords, patterns, priorities) |
| `.claude/hooks/*.py` | Hook implementation scripts |
| `.claude/skills/*/SKILL.md` | Skill documentation files |

---

## Hooks

### 1. UserPromptSubmit: `skill-activator.py`

| Property | Value |
|----------|-------|
| **Trigger** | Before Claude sees user message |
| **Timeout** | 5 seconds |
| **File** | `.claude/hooks/skill-activator.py` |

**Purpose:** Auto-detect and suggest relevant skills based on keywords/patterns in the user's prompt.

**How It Works:**
1. Reads the user's prompt from stdin
2. Matches against keyword and intent patterns defined in `skill-rules.json`
3. If matches found, injects a reminder into the conversation context listing relevant skills
4. Guardrail skills (like `database-operations`) are highlighted with warnings

**Use Cases:**
- Ensures developers follow correct patterns for domain areas
- Automatically loads context for ETL, service, UI, or database work
- Warns when working in areas with safety-critical guidelines

**Example Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 SKILL ACTIVATION CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Relevant skills: database-operations, service-developer

Before proceeding, load and follow patterns from:
  • .claude/skills/database-operations/SKILL.md
  • .claude/skills/service-developer/SKILL.md

⚠️  GUARDRAIL SKILLS ACTIVE: database-operations
   Follow these guidelines strictly!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 2. PreToolUse: `dangerous-command-blocker.py`

| Property | Value |
|----------|-------|
| **Trigger** | Before Bash command execution |
| **Matcher** | `Bash` tool only |
| **Timeout** | 5 seconds |
| **File** | `.claude/hooks/dangerous-command-blocker.py` |

**Purpose:** Block dangerous SQL and Docker commands that could cause data loss.

**Blocked Patterns (Critical):**

| Pattern | Description |
|---------|-------------|
| `DROP TABLE` (without IF EXISTS) | Drops table without safety check |
| `DROP DATABASE` | Destroys entire database |
| `DROP SCHEMA` | Destroys entire schema |
| `TRUNCATE` | Removes all rows (non-recoverable) |
| `DELETE FROM table;` | DELETE without WHERE clause |
| `DELETE ... WHERE 1=1` | Deletes all rows |
| `docker compose down --volumes` | Destroys database volumes |
| `docker volume rm` | Destroys data volumes |

**Blocked Patterns (High Risk):**

| Pattern | Description |
|---------|-------------|
| `UPDATE ... SET` (without WHERE) | Updates all rows |
| `ALTER TABLE ... DROP COLUMN` | Removes column data |

**Use Cases:**
- Prevent accidental data destruction
- Force manual execution of dangerous operations outside Claude Code
- Protect against SQL injection-like mistakes

---

### 3. PostToolUse: `file-validator.py`

| Property | Value |
|----------|-------|
| **Trigger** | After Edit/Write/MultiEdit operations |
| **Matcher** | `Edit\|Write\|MultiEdit` |
| **Timeout** | 10 seconds |
| **File** | `.claude/hooks/file-validator.py` |

**Purpose:** Validate Python syntax and detect dangerous SQL patterns in edited files.

**Validations Performed:**

| File Type | Validation |
|-----------|------------|
| `.py` | Python syntax check via `py_compile` (runs in Docker) |
| `.sql` | Checks for DELETE without WHERE, DROP without IF EXISTS, TRUNCATE, UPDATE without WHERE |

**Use Cases:**
- Catch Python syntax errors immediately after edits
- Warn about unsafe SQL patterns in migration files
- Provide early feedback before running code

**Example Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 FILE VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Python syntax error in service.py:
   SyntaxError: unexpected EOF while parsing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 4. PostToolUse: `spec-generator.py`

| Property | Value |
|----------|-------|
| **Trigger** | After ExitPlanMode tool |
| **Timeout** | 10 seconds |
| **File** | `.claude/hooks/spec-generator.py` |

**Purpose:** Auto-save plan files as timestamped specs when exiting plan mode.

**How It Works:**
1. Detects when `ExitPlanMode` tool is called
2. Finds the most recent plan file in `~/.claude/plans/`
3. Extracts the key feature name from the first heading
4. Copies to `/opt/tangerine/specs/` with timestamped filename

**Output Format:** `{YYYYMMDDTHHMMSS}_spec_{feature-slug}.md`

**Use Cases:**
- Preserve implementation plans for future reference
- Enable session handoffs (stop and resume with saved plan)
- Build a history of implementation decisions

**Debug Mode:** Set `SPEC_GENERATOR_DEBUG=1` for verbose output.

---

### 5. Stop: `build-checker.py`

| Property | Value |
|----------|-------|
| **Trigger** | When conversation stops |
| **Timeout** | 30 seconds |
| **File** | `.claude/hooks/build-checker.py` |

**Purpose:** Run quality checks and provide reminders after Claude finishes responding.

**Checks Performed:**

| Check | Action |
|-------|--------|
| Ruff linter | Runs `ruff check` and reports issues |
| Active dev docs | Reminds about updating `dev/active/` task docs |
| Significant work detection | Suggests `/doc-feature`, `CHANGELOG.md` updates |
| Plan completion | Reminds about feature docs when plan appears complete |
| Spec generation | Creates spec file if recent plan exists |

**Use Cases:**
- Ensure code quality checks before session ends
- Remind about documentation updates
- Catch linting issues early

**Example Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 POST-RESPONSE CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Spec saved: specs/20260123T143022_spec_new-feature.md

🔍 Linting: 3 issue(s) found
   admin/services/foo.py:12:1: F401 unused import

📝 Significant changes detected - consider:
   • Run `/doc-feature` to document the feature
   • Update `CHANGELOG.md` with the change

💡 Run /test to verify changes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Skills

Skills are activated automatically when prompts match their trigger patterns. They provide domain-specific guidelines to ensure consistent patterns across the codebase.

### 1. `streamlit-admin`

| Property | Value |
|----------|-------|
| **Type** | Domain |
| **Priority** | Medium |
| **File** | `.claude/skills/streamlit-admin/SKILL.md` |

**Purpose:** Streamlit UI patterns for the Tangerine admin interface.

**Trigger Keywords:** `streamlit`, `admin`, `page`, `ui`, `form`, `component`, `tab`, `expander`, `button`, `session state`, `st.form`, `st.tabs`

**Key Patterns:**
- Session state for persisting messages across `st.rerun()`
- Unique form keys (especially in loops)
- Tabs for CRUD operations
- Expanders for detail views
- Services for business logic (no SQL in pages)

**Directory Structure:**
```
admin/
├── app.py           # Landing page
├── pages/           # Auto-discovered pages (numbered)
├── components/      # Reusable UI components
├── services/        # Business logic (no UI code)
└── utils/           # Helpers
```

---

### 2. `etl-developer`

| Property | Value |
|----------|-------|
| **Type** | Domain |
| **Priority** | High |
| **File** | `.claude/skills/etl-developer/SKILL.md` |

**Purpose:** ETL job development patterns for config-driven imports.

**Trigger Keywords:** `etl`, `import`, `extract`, `transform`, `load`, `csv`, `excel`, `json`, `xml`, `file processing`, `generic_import`, `schema manager`, `extractor`

**Key Patterns:**
- Config-driven imports via `dba.timportconfig` table
- Always support `--dry-run` flag
- Use `get_etl_logger()` for logging
- Create `tdataset` records for tracking
- Archive files after processing

**Import Strategies:**
| ID | Name | Behavior |
|----|------|----------|
| 1 | Auto-add | Add new columns from file |
| 2 | Ignore | Skip unknown columns |
| 3 | Strict | Fail on mismatched columns |

---

### 3. `service-developer`

| Property | Value |
|----------|-------|
| **Type** | Domain |
| **Priority** | High |
| **File** | `.claude/skills/service-developer/SKILL.md` |

**Purpose:** Service layer CRUD patterns and database access.

**Trigger Keywords:** `service`, `crud`, `repository`, `transaction`, `get_all`, `get_by_id`, `create_`, `update_`, `delete_`

**Key Patterns:**
- Always use `db_transaction()` context manager
- Return dicts, not database row objects
- Use parameterized queries (never string formatting for SQL)
- Handle None/empty cases explicitly
- Services contain no UI code

**CRUD Functions:**
```python
get_all() -> list[dict]
get_by_id(id) -> dict | None
create(data) -> int
update(id, data) -> bool
delete(id) -> bool
```

---

### 4. `database-operations` (GUARDRAIL)

| Property | Value |
|----------|-------|
| **Type** | Guardrail (Critical) |
| **Priority** | Critical |
| **File** | `.claude/skills/database-operations/SKILL.md` |

**Purpose:** PostgreSQL schema safety and conventions.

**Trigger Keywords:** `schema`, `table`, `column`, `migration`, `sql`, `procedure`, `trigger`, `index`, `constraint`, `alter table`, `create table`, `drop`

**Safety Rules - NEVER Do These:**
1. `DELETE` without `WHERE` clause
2. `DROP` without `IF EXISTS`
3. `UPDATE` without `WHERE` clause
4. `TRUNCATE` on production tables
5. Schema changes without backup

**Naming Conventions:**
| Object | Prefix | Example |
|--------|--------|---------|
| Table | t | `timportconfig` |
| Procedure | p | `pimportconfigi` |
| Function | f | `fgetlabel` |
| View | v | `vimportstatus` |
| Index | idx_ | `idx_dataset_date` |
| Foreign Key | fk_ | `fk_dataset_source` |

**Migration Workflow:**
1. Create backup of affected tables
2. Write migration with IF EXISTS/IF NOT EXISTS guards
3. Test on dev database first
4. Review with another person
5. Execute during low-traffic window
6. Verify data integrity after migration

---

## Configuration Reference

### settings.json Structure

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/script.py",
            "timeout": 5
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "ToolName",
        "hooks": [...]
      }
    ],
    "PostToolUse": [...],
    "Stop": [...]
  }
}
```

### skill-rules.json Structure

```json
{
  "skill-name": {
    "type": "domain|guardrail",
    "priority": "critical|high|medium|low",
    "description": "Brief description",
    "promptTriggers": {
      "keywords": ["keyword1", "keyword2"],
      "intentPatterns": ["regex pattern"]
    },
    "fileTriggers": {
      "pathPatterns": ["glob/pattern/*.py"],
      "contentPatterns": ["regex pattern"]
    }
  }
}
```

### Adding a New Hook

1. Create Python script in `.claude/hooks/`
2. Script reads JSON from stdin, writes JSON to stdout
3. Add configuration to `.claude/settings.json`
4. Test with debug output (`print(..., file=sys.stderr)`)

### Adding a New Skill

1. Create directory `.claude/skills/{skill-name}/`
2. Create `SKILL.md` with frontmatter and guidelines
3. Add activation rules to `.claude/skill-rules.json`
4. Test by using trigger keywords in prompts

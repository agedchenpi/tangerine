# Claude Code Hooks

This directory contains custom hooks that enhance Claude Code's behavior when working with the Tangerine ETL project.

## Available Hooks

### PreToolUse Hooks

#### dangerous-command-blocker.py
**Trigger:** Before executing any Bash command
**Purpose:** Prevent accidental data loss by blocking dangerous database and Docker commands

**Blocked Patterns:**
- `DROP TABLE` (without IF EXISTS)
- `DROP DATABASE`
- `DROP SCHEMA`
- `TRUNCATE`
- `DELETE FROM` (without WHERE clause)
- `DELETE FROM ... WHERE 1=1`
- `UPDATE` (without WHERE clause)
- `ALTER TABLE ... DROP COLUMN`
- `docker compose down --volumes` or `-v`
- `docker volume rm`

**Allowed Patterns:**
- `DROP TABLE IF EXISTS` (safe idempotent pattern)
- `DELETE/UPDATE` with proper WHERE clauses
- All SELECT, INSERT, CREATE statements
- Read-only Docker commands

**Testing:** Run `python3 .claude/hooks/test_dangerous_command_blocker.py` to verify behavior.

---

### UserPromptSubmit Hooks

#### skill-activator.py
**Trigger:** When user submits a prompt
**Purpose:** Automatically activates relevant skills based on keyword detection

Analyzes user prompts and injects reminders to load relevant skills from `.claude/skills/`:
- `etl-developer` - ETL jobs, imports, extractors
- `service-developer` - CRUD operations, transactions
- `database-operations` - Schema changes, SQL (GUARDRAIL)
- `streamlit-admin` - UI components, forms

---

### PostToolUse Hooks

#### file-validator.py
**Trigger:** After Edit/Write/MultiEdit tool use
**Purpose:** Validate Python syntax and check for dangerous SQL patterns

**Checks:**
- Python syntax errors (using `py_compile`)
- SQL injection risks (f-strings with SQL)
- Dangerous SQL without WHERE clauses
- Missing parameterized queries

#### spec-generator.py
**Trigger:** After ExitPlanMode tool use
**Purpose:** Generate plan specification file from plan mode transcript

Creates a structured markdown file documenting:
- Plan overview and goals
- Implementation steps
- Files to be modified
- Design decisions

---

### Stop Hooks

#### build-checker.py
**Trigger:** When conversation stops (user idle or explicit stop)
**Purpose:** Remind about testing, linting, and documentation

**Reminders:**
- Run tests if code was modified
- Run `ruff check` for Python linting
- Document features with `/doc-feature`
- Update dev docs before context compaction

---

## Hook Configuration

Hooks are registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [...],
    "PreToolUse": [...],
    "PostToolUse": [...],
    "Stop": [...]
  }
}
```

## Testing Hooks

Each hook can be tested independently:

```bash
# Test dangerous command blocker
python3 .claude/hooks/test_dangerous_command_blocker.py

# Test file validator (requires test file)
echo '{"file_path": "test.py"}' | python3 .claude/hooks/file-validator.py

# Test skill activator (requires user prompt)
echo '{"user_prompt": "help me create an import job"}' | python3 .claude/hooks/skill-activator.py
```

## Creating New Hooks

1. Create Python script in `.claude/hooks/`
2. Accept JSON input from stdin
3. Output JSON result to stdout
4. Use exit codes:
   - `0` - Success/Allow
   - `1` - Error
   - `2` - Block (PreToolUse only)
5. Register in `.claude/settings.json`

**Example PreToolUse hook:**
```python
#!/usr/bin/env python3
import json
import sys

input_data = json.load(sys.stdin)
tool_name = input_data.get("tool_name")
tool_input = input_data.get("tool_input", {})

# Check if should block
if should_block:
    output = {
        "decision": "block",
        "reason": "Explanation of why blocked"
    }
    print(json.dumps(output))
    sys.exit(2)  # Block

sys.exit(0)  # Allow
```

## Debugging Hooks

Hooks run automatically but errors are captured. To debug:

1. Run hook manually with test input
2. Check Claude Code output for hook errors
3. Verify hook file permissions (must be readable)
4. Test JSON parsing with `python3 -m json.tool`

## Hook Best Practices

- **Fast execution:** Hooks should complete in < 5 seconds
- **Clear messages:** Provide actionable feedback to Claude
- **Fail gracefully:** If hook errors, don't block operation
- **Test thoroughly:** Use automated tests for pattern matching
- **Document patterns:** Explain what triggers blocks/warnings

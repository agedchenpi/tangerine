# Claude Code Hooks & Skills Documentation

## Task
Create a `claude_doc.md` file documenting all Claude Code hooks and skills in this project.

---

## Output File
**Location:** `/opt/tangerine/claude_doc.md`

---

## Document Structure

### 1. Overview Section
- Brief explanation of what hooks and skills are
- How they enhance Claude Code workflow
- Configuration file locations

### 2. Hooks Section

#### 2.1 UserPromptSubmit: `skill-activator.py`
- **Trigger:** Before Claude sees user message
- **Purpose:** Auto-detect and suggest relevant skills based on keywords/patterns
- **Use Cases:** Ensures developers follow correct patterns for domain areas

#### 2.2 PreToolUse: `dangerous-command-blocker.py`
- **Trigger:** Before Bash command execution
- **Purpose:** Block dangerous SQL/Docker commands that could cause data loss
- **Use Cases:** Prevent accidental `DROP TABLE`, `DELETE` without WHERE, volume destruction

#### 2.3 PostToolUse: `file-validator.py`
- **Trigger:** After Edit/Write operations
- **Purpose:** Validate Python syntax and detect dangerous SQL patterns
- **Use Cases:** Catch syntax errors early, warn about unsafe SQL in migrations

#### 2.4 PostToolUse: `spec-generator.py`
- **Trigger:** After ExitPlanMode
- **Purpose:** Auto-save plan files as timestamped specs
- **Use Cases:** Preserve implementation plans for future reference

#### 2.5 Stop: `build-checker.py`
- **Trigger:** When conversation stops
- **Purpose:** Remind about testing, linting, and documentation
- **Use Cases:** Ensure code quality checks before session ends

### 3. Skills Section

#### 3.1 `streamlit-admin`
- **Purpose:** Streamlit UI patterns for admin pages
- **Use Cases:** Building pages, forms, components, notifications
- **Key Patterns:** Session state, unique form keys, service separation

#### 3.2 `etl-developer`
- **Purpose:** ETL job development patterns
- **Use Cases:** Creating import configs, extractors, file processing
- **Key Patterns:** Config-driven imports, dry-run support, file archiving

#### 3.3 `service-developer`
- **Purpose:** Service layer CRUD operations
- **Use Cases:** Database access, business logic, transactions
- **Key Patterns:** Parameterized queries, db_transaction, dict returns

#### 3.4 `database-operations` (GUARDRAIL)
- **Purpose:** PostgreSQL schema safety and conventions
- **Use Cases:** Table design, migrations, naming conventions
- **Key Patterns:** Safety rules, migration workflow, backup requirements

### 4. Configuration Reference
- `settings.json` structure
- `skill-rules.json` structure
- How to add new hooks/skills

---

## Files to Read (for accuracy)
- `.claude/settings.json` - Hook configurations
- `.claude/skill-rules.json` - Skill activation rules
- `.claude/hooks/*.py` - Hook implementations
- `.claude/skills/*/SKILL.md` - Skill documentation

---

## Verification
1. File created at `/opt/tangerine/claude_doc.md`
2. All 5 hooks documented with triggers and use cases
3. All 4 skills documented with purposes and patterns
4. Clear, scannable format with headers and tables

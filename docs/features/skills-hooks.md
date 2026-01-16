# Feature: Skills & Hooks Auto-Activation System

**Added:** 2026-01-16
**Related Files:** `.claude/hooks/`, `.claude/skills/`, `.claude/skill-rules.json`

## Overview

An auto-activation system that ensures Claude Code follows project-specific patterns and guidelines. Instead of relying on Claude to remember to check documentation, hooks automatically inject reminders and validate work.

## How It Works

### Components

- `.claude/hooks/skill-activator.py` - Analyzes prompts and injects skill reminders
- `.claude/hooks/file-validator.py` - Validates files after edits
- `.claude/hooks/build-checker.py` - Runs linting and documentation reminders
- `.claude/skill-rules.json` - Configuration mapping keywords to skills
- `.claude/skills/*/SKILL.md` - Domain-specific guidelines and patterns

### Data Flow

1. User submits a prompt
2. `UserPromptSubmit` hook runs `skill-activator.py`
3. Script analyzes prompt for keywords/patterns
4. Matching skills identified from `skill-rules.json`
5. Reminder injected into Claude's context
6. Claude sees skill suggestions before processing prompt
7. After response, `Stop` hook runs checks and reminders

## Skills Available

| Skill | Type | Triggers |
|-------|------|----------|
| `etl-developer` | Domain | etl, import, extract, csv, json |
| `service-developer` | Domain | service, crud, transaction |
| `database-operations` | Guardrail | schema, table, sql, migration |
| `streamlit-admin` | Domain | streamlit, page, form, ui |

### Skill Types

- **Domain**: Best practices for a specific area
- **Guardrail**: Critical rules that must be followed (e.g., SQL safety)

## Configuration

### skill-rules.json Structure

```json
{
  "skill-name": {
    "type": "domain|guardrail",
    "priority": "critical|high|medium|low",
    "promptTriggers": {
      "keywords": ["word1", "word2"],
      "intentPatterns": ["regex pattern"]
    },
    "fileTriggers": {
      "pathPatterns": ["glob/pattern/*.py"],
      "contentPatterns": ["regex in file"]
    }
  }
}
```

### Hook Configuration (settings.json)

```json
{
  "hooks": {
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "..."}]}],
    "PostToolUse": [{"matcher": "Edit|Write", "hooks": [...]}],
    "Stop": [{"hooks": [...]}]
  }
}
```

## Usage

### Automatic Activation

When you mention keywords like "create an import job", you'll see:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 SKILL ACTIVATION CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Relevant skills: etl-developer

Before proceeding, load and follow patterns from:
  • .claude/skills/etl-developer/SKILL.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Manual Loading

```
Read .claude/skills/etl-developer/SKILL.md
```

### Post-Response Checks

After Claude finishes, you may see:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 POST-RESPONSE CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Significant changes detected - consider:
   • Run /doc-feature to document the feature
   • Update CHANGELOG.md with the change
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Adding New Skills

1. Create directory: `.claude/skills/{skill-name}/`
2. Create `SKILL.md` with frontmatter and guidelines
3. Add entry to `.claude/skill-rules.json`
4. Test by using trigger keywords

### Skill Template

```markdown
---
name: skill-name
description: Brief description for activation
---

# Skill Name Guidelines

## Overview
What this skill covers.

## Patterns
Code patterns to follow.

## Examples
Example code.

## Common Pitfalls
What to avoid.
```

## Testing

Test skill activation:
```
# Should trigger etl-developer
"create a new import job"

# Should trigger database-operations (guardrail)
"add a new table to the schema"

# Should trigger service-developer
"add a new service for managing users"
```

## Known Limitations

- Keyword matching is case-insensitive but simple
- Intent patterns use basic regex
- File triggers only checked when files are mentioned
- No learning/adaptation over time

## Future Improvements

- More sophisticated NLP for intent detection
- Skill chaining (one skill can suggest another)
- Usage analytics to improve trigger accuracy
- Custom skill creation via admin UI

---
name: doc-feature
description: Create documentation for a completed feature
---

# Document Feature

After implementing a feature, create documentation to help future developers understand it.

## Steps

1. **Determine the feature name** from the work just completed

2. **Create feature documentation:**
   ```bash
   touch docs/features/{feature-name}.md
   ```

3. **Use this template for the feature doc:**

```markdown
# Feature: {Feature Name}

**Added:** {date}
**Related Files:** List key files

## Overview

Brief description of what this feature does and why it exists.

## How It Works

### Components

- `path/to/file.py` - What this component does
- `path/to/another.py` - What this component does

### Data Flow

1. Step 1 of how data/control flows
2. Step 2
3. Step 3

## Usage

### Basic Usage

```python
# Example code showing how to use the feature
```

### Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| setting_1 | What it does | value |

## Database

Tables involved:
- `dba.ttablename` - Purpose

## Admin UI

If there's a UI component:
- Page location: `admin/pages/X_PageName.py`
- How to access: Navigate to...

## Testing

```bash
# How to test this feature
docker compose exec tangerine pytest tests/integration/... -v
```

## Known Limitations

- Limitation 1
- Limitation 2

## Future Improvements

- Potential improvement 1
- Potential improvement 2
```

4. **Update the feature index:**

   Add an entry to `docs/features/README.md`:
   ```markdown
   | {Feature Name} | Brief description | {date} |
   ```

5. **Update CHANGELOG.md:**

   Add an entry under the current version:
   ```markdown
   ### Added
   - **{Feature Name}**: Brief description of what was added
   ```

## Quick Reference

After implementing, you need to update:
- [ ] `docs/features/{feature-name}.md` - Full feature documentation
- [ ] `docs/features/README.md` - Add to feature index
- [ ] `CHANGELOG.md` - Add changelog entry

## Example

For a "Gmail Inbox Processor" feature:

**docs/features/gmail-inbox-processor.md:**
```markdown
# Feature: Gmail Inbox Processor

**Added:** 2026-01-16
**Related Files:** etl/jobs/run_gmail_inbox_processor.py, admin/pages/5_Inbox_Configs.py

## Overview

Downloads email attachments from Gmail based on configurable rules...
```

**CHANGELOG.md entry:**
```markdown
### Added
- **Gmail Inbox Processor**: Download email attachments based on subject, sender, and attachment patterns
```

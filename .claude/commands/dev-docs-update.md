---
name: dev-docs-update
description: Update dev docs before context compaction or session end
---

# Dev Docs: Update Before Compaction

Before context gets low or ending a session, update the task documentation to preserve state.

## Steps

1. **Find the active task directory:**
   ```bash
   ls dev/active/
   ```

2. **Update {task-name}-context.md:**

   Add a session summary:
   ```markdown
   ## Session: {date}

   ### Accomplished
   - Completed item 1
   - Completed item 2
   - Made progress on item 3

   ### Decisions Made
   - Decided to use approach X because Y

   ### Issues Encountered
   - Issue 1: How we resolved it
   - Issue 2: Still pending

   ### Next Steps (for resumption)
   1. Continue with X - specific details
   2. Then do Y - specific details
   3. Finally Z - specific details

   ### Files to Review
   - `path/to/file.py` - needs attention because...
   ```

3. **Update {task-name}-tasks.md:**

   - Mark completed tasks with `[x]`
   - Move current work to "In Progress"
   - Add any new tasks discovered
   - Note any blockers

4. **Verify documentation is complete:**

   Before compacting, ensure:
   - [ ] Context file has clear "Next Steps"
   - [ ] Tasks file is up to date
   - [ ] Any important decisions are documented
   - [ ] Files modified this session are listed

## Resuming Work

When starting a new session:

1. Check `dev/active/` for existing tasks
2. Read all three files for the task
3. Follow the "Next Steps" from context
4. Continue from the tasks checklist

## Example Update

Before:
```markdown
## In Progress
- [ ] Implement feature X
```

After:
```markdown
## Completed
- [x] Implement feature X - completed 2026-01-16, see file.py

## In Progress
- [ ] Write tests for feature X
```

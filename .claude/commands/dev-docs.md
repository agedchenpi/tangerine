---
name: dev-docs
description: Create development documentation for a new task
---

# Dev Docs: Create Task Documentation

When starting a large task or feature, create structured documentation to prevent context loss.

## Steps

1. **Create task directory:**
   ```bash
   mkdir -p dev/active/{task-name}/
   ```

2. **Create three documentation files:**

### {task-name}-plan.md

```markdown
# Task: {task-name}

## Objective
One-paragraph description of what we're building.

## Background
Why this task is needed and any relevant context.

## Key Files
- `path/to/file.py` - what it does
- `path/to/another.py` - what it does

## Implementation Steps
1. Step one - description
2. Step two - description
3. Step three - description

## Success Criteria
- [ ] Tests pass
- [ ] No linting errors
- [ ] Feature works as expected
- [ ] Documentation updated

## Risks & Considerations
- Risk 1: Mitigation strategy
- Risk 2: Mitigation strategy
```

### {task-name}-context.md

```markdown
# Context: {task-name}

Last Updated: {timestamp}

## Current State
Where we are in the implementation.

## Key Decisions Made
| Decision | Rationale | Date |
|----------|-----------|------|
| Decision 1 | Why we chose this | 2026-01-16 |

## Files Modified
- `path/to/file.py` - changes made
- `path/to/another.py` - changes made

## Dependencies Discovered
- Dependency on X component
- Need to update Y before Z

## Next Steps
1. Immediate next action
2. Following action
3. Final action
```

### {task-name}-tasks.md

```markdown
# Tasks: {task-name}

Last Updated: {timestamp}

## Completed
- [x] Task 1 - description
- [x] Task 2 - description

## In Progress
- [ ] Task 3 - current focus

## Pending
- [ ] Task 4 - description
- [ ] Task 5 - description

## Blocked
None currently.

## Notes
Any additional notes or reminders.
```

## After Creating

1. Review the plan with the user
2. Begin implementation from the tasks checklist
3. Update context file as you learn new information
4. Mark tasks complete as you finish them
5. Before compacting, run `/dev-docs-update`

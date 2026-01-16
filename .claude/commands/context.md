---
description: Monitor context usage and token consumption.
---
# Context Monitor

Analyze and report on current context usage.

## Instructions

Estimate the current context window usage:

1. **Count Active Context:**
   - List files you've read in this session
   - Estimate tokens per file (~4 chars = 1 token)
   - Sum total estimated tokens

2. **Calculate Usage:**
   - Context window: 200,000 tokens
   - Report: tokens used, percentage, tokens remaining

3. **Identify Large Items:**
   - Flag any files over 5,000 tokens
   - Suggest if any can be delegated to sub-agents

4. **Recommendations:**
   - If >70% used: Suggest delegation or context reset
   - If <30% used: Context is healthy
   - List any redundant context that could be cleared

## Output Format

```
Context Status: [HEALTHY/WARNING/CRITICAL]
Estimated Usage: ~XX,XXX tokens (XX%)
Remaining: ~XXX,XXX tokens

Large Files in Context:
- filename.py (~X,XXX tokens)

Recommendations:
- [suggestions]
```

## R&D Reminder

- **Reduce:** Can any loaded context be cleared?
- **Delegate:** Should sub-agents handle isolated tasks?

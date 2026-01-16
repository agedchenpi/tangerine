# Agent Aliases and Shortcuts

Quick reference for common patterns and modes.

## Context Management Aliases

### R&D
**Reduce and Delegate** - Core framework reminder
- Reduce: Minimize context, load only what's needed
- Delegate: Use sub-agents for isolated tasks

### Focus
Reminder to stay focused:
- Complete current task before starting new ones
- Don't load unnecessary context
- Use `/context` to check usage

### CLLD
**Clear/Load/Learn/Do** - Session reset pattern:
1. Clear - Start fresh context
2. Load - Prime with `/prime` or `/prime_cc`
3. Learn - Understand the task requirements
4. Do - Execute with minimal context

## Execution Modes

### YOLO Mode
Experimental/dangerous operations flag:
- Skip confirmations
- Allow risky operations
- User takes full responsibility

**Usage:** "YOLO mode: [operation]"

**Note:** dangerous-command-blocker.py still blocks critical operations regardless of YOLO mode.

### Dry Run
Safe exploration without changes:
- Read and analyze only
- No file modifications
- No database changes

**Usage:** "Dry run: [operation]"

## Sub-Agent Shortcuts

| Alias | Sub-Agent | Use For |
|-------|-----------|---------|
| scrape | doc_scraper | Fetch web docs |
| analyze | code_analyzer | Analyze code |
| research | researcher | Web research |

**Usage:** "Delegate to [alias]: [task]"

## Quick Commands

| Alias | Command | Purpose |
|-------|---------|---------|
| prime | /prime | Understand codebase |
| primecc | /prime_cc | Understand Claude Code config |
| ctx | /context | Check token usage |
| test | /test | Run tests |

## Token-Saving Reminders

- **Before deep work:** Check `/context`
- **Large files:** Consider delegation
- **Web content:** Always delegate to scraper
- **Multi-file analysis:** Delegate to analyzer
- **Research tasks:** Delegate to researcher

---
*A focused agent is a performant agent.*

# CLAUDE.md

Slim context file for Claude Code. Use for quick tasks or context-limited sessions.

## Core Principles

**R&D Framework:** Reduce and Delegate
- Reduce: Minimize context, load only what's needed
- Delegate: Use sub-agents for isolated tasks

## Essential Rules

1. **No Hallucination:** Never speculate about unread code. Read files before answering.
2. **Parallel Tools:** Call independent tools in parallel to maximize efficiency.
3. **Ask First:** When intent is ambiguous, ask questions before making changes.
4. **Summarize Work:** After tool use, provide a quick summary of completed work.

## Quick Reference

- **Code Style:** See `CODE_STYLE.md`
- **Full Context:** See `README.md`
- **Extended Context:** See `CLAUDE.large.md`
- **Commands:** `/test`, `/run-job`, `/logs`, `/prime`, `/context`
- **Codemaps:** `.claude/codemaps/` for architecture docs
- **Skills:** Auto-activated via hooks when relevant

## Project Stack

- PostgreSQL 18 + Python 3.11 + Docker + Streamlit
- ETL pipeline with config-driven imports
- Vertical Slice Architecture

## When to Load More Context

Load full `README.md` when:
- Starting a complex feature
- Need detailed patterns (services, ETL, database)
- Working across multiple system areas

---
*A focused agent is a performant agent.*

# Fix: spec-generator Hook Not Triggering

## Problem
The `spec-generator.py` hook is configured to run after `ExitPlanMode` but isn't being triggered. Last spec file was created on Jan 17, despite multiple plan mode sessions since then.

## Root Cause Analysis

**Finding:** The hook is configured as a `PostToolUse` hook matching `ExitPlanMode`:
```json
{
  "matcher": "ExitPlanMode",
  "hooks": [{
    "type": "command",
    "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/spec-generator.py"
  }]
}
```

**Issue:** `ExitPlanMode` may not trigger `PostToolUse` hooks because:
1. It's a special plan-mode transition command, not a standard tool
2. PostToolUse hooks are documented to work with tools like `Edit`, `Write`, `Bash`, `Task`, etc.
3. `ExitPlanMode` isn't listed as a valid PostToolUse matcher in Claude Code documentation

**Evidence:**
- Manual execution of the hook works correctly
- Last specs created Jan 17 = before recent plan sessions
- Hook script logic is correct, just never being invoked

---

## Solution Options

### Option A: Use Stop Hook (Recommended)
Move spec generation to a `Stop` hook that runs when the conversation ends/pauses.

**Pros:**
- Stop hooks are reliably triggered
- Can check if plan mode was active during session
- Already have a Stop hook (`build-checker.py`) that works

**Cons:**
- Runs on every stop, not just plan exits
- Need to detect if plan was involved

### Option B: Use Write Hook on Plan File
Trigger on `Write` to `~/.claude/plans/*.md` files.

**Pros:**
- Triggers when plan file is written/updated
- More targeted than Stop hook

**Cons:**
- May trigger multiple times during planning
- Harder to detect "final" plan state

### Option C: Integrate into build-checker.py
Add spec generation logic to the existing Stop hook.

**Pros:**
- Single hook handles end-of-session tasks
- Already works reliably
- Can share plan detection logic

**Cons:**
- Makes build-checker.py more complex

---

## Recommended Plan: Option C

Integrate spec generation into `build-checker.py` since:
1. Stop hooks are proven to work
2. Consolidates end-of-session logic
3. Can check if plan file was modified during session

### Implementation

**File: `.claude/hooks/build-checker.py`**

Add logic to:
1. Check if any plan file in `~/.claude/plans/` was modified in last 30 minutes
2. If yes, copy to `/opt/tangerine/specs/` with timestamp
3. Skip if spec already exists for this plan (avoid duplicates)

**File: `.claude/settings.json`**

Remove the non-functional ExitPlanMode PostToolUse hook (cleanup).

---

## Files to Modify

| File | Changes |
|------|---------|
| `.claude/hooks/build-checker.py` | Add spec generation logic from spec-generator.py |
| `.claude/settings.json` | Remove ExitPlanMode PostToolUse hook entry |

---

## Verification

1. Start a new Claude Code session
2. Enter plan mode and create/modify a plan
3. Exit plan mode (approve or cancel)
4. End the session or let it timeout
5. Check `/opt/tangerine/specs/` for new spec file
6. Verify spec filename includes timestamp and feature name

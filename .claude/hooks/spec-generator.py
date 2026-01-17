#!/usr/bin/env python3
"""
PostToolUse Hook: Generate spec file when ExitPlanMode is called.
Copies the finalized plan to /opt/tangerine/specs/ with timestamped naming.

Workflow support:
1. User runs plan mode -> Claude creates plan in ~/.claude/plans/
2. ExitPlanMode is called -> this hook fires
3. Hook copies plan to /opt/tangerine/specs/ with timestamp
4. User can stop Claude and resume later with auto-accept

Debug: Set SPEC_GENERATOR_DEBUG=1 to see verbose output
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

SPECS_DIR = Path("/opt/tangerine/specs")
DEBUG = os.environ.get("SPEC_GENERATOR_DEBUG", "0") == "1"


def debug_log(msg: str) -> None:
    """Log debug message to stderr (visible in hook output)."""
    if DEBUG:
        print(f"[spec-generator] {msg}", file=sys.stderr)


def extract_key_feature(content: str) -> str:
    """Extract key feature from first heading in plan.

    Parses the first # or ## heading and converts it to a URL-friendly slug.
    Returns 'unnamed' if no heading is found.
    """
    # Match first # or ## heading
    match = re.search(r'^#+ (.+)$', content, re.MULTILINE)
    if match:
        title = match.group(1).strip()
        # Remove common prefixes like "Plan:" or "Spec:"
        title = re.sub(r'^(Plan|Spec|Feature):\s*', '', title, flags=re.IGNORECASE)
        # Convert to slug: lowercase, replace spaces/special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        return slug[:50]  # Limit length
    return "unnamed"


def find_recent_plan_file(max_age_minutes: int = 5) -> str | None:
    """Find most recently modified plan file within time window.

    Args:
        max_age_minutes: Only consider files modified within this many minutes

    Returns:
        Path to plan file or None if not found
    """
    plans_dir = Path.home() / ".claude" / "plans"
    if not plans_dir.exists():
        debug_log(f"Plans directory does not exist: {plans_dir}")
        return None

    plan_files = list(plans_dir.glob("*.md"))
    if not plan_files:
        debug_log("No .md files found in plans directory")
        return None

    # Filter to recent files only (within max_age_minutes)
    now = datetime.now()
    cutoff = now - timedelta(minutes=max_age_minutes)

    recent_files = []
    for pf in plan_files:
        mtime = datetime.fromtimestamp(pf.stat().st_mtime)
        if mtime >= cutoff:
            recent_files.append((pf, mtime))
            debug_log(f"Found recent plan: {pf.name} (modified {mtime})")
        else:
            debug_log(f"Skipping old plan: {pf.name} (modified {mtime})")

    if not recent_files:
        debug_log(f"No plans modified within last {max_age_minutes} minutes")
        # Fall back to most recent file regardless of age
        most_recent = max(plan_files, key=lambda p: p.stat().st_mtime)
        debug_log(f"Falling back to most recent: {most_recent.name}")
        return str(most_recent)

    # Get most recently modified among recent files
    most_recent = max(recent_files, key=lambda x: x[1])[0]
    debug_log(f"Selected plan file: {most_recent}")
    return str(most_recent)


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        debug_log(f"JSON decode error: {e}")
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    debug_log(f"Tool name: {tool_name}")

    if tool_name != "ExitPlanMode":
        sys.exit(0)

    debug_log(f"Input data keys: {list(input_data.keys())}")

    # Get plan file from tool_input (ExitPlanMode may pass plan file info)
    tool_input = input_data.get("tool_input", {})
    debug_log(f"Tool input: {tool_input}")

    # Try multiple sources for plan file path
    plan_file = None
    source = None

    # Check if plan file path is in tool_input
    if isinstance(tool_input, dict):
        plan_file = tool_input.get("plan_file", "")
        if plan_file:
            source = "tool_input"

    # Check session_info as fallback
    if not plan_file:
        session_info = input_data.get("session_info", {})
        plan_file = session_info.get("plan_file", "")
        if plan_file:
            source = "session_info"
        debug_log(f"Session info: {session_info}")

    # Check tool_result for plan file path
    if not plan_file:
        tool_result = input_data.get("tool_result", "")
        debug_log(f"Tool result type: {type(tool_result)}")
        if isinstance(tool_result, str):
            debug_log(f"Tool result (first 500 chars): {tool_result[:500]}")
            # Look for plan file path in result text
            match = re.search(r'(/[^\s]+\.md)', tool_result)
            if match:
                plan_file = match.group(1)
                source = "tool_result"

    # If no plan file found, try to find most recent plan in ~/.claude/plans/
    if not plan_file:
        debug_log("Trying to find recent plan file...")
        plan_file = find_recent_plan_file(max_age_minutes=10)
        if plan_file:
            source = "recent_file_scan"

    debug_log(f"Plan file: {plan_file} (source: {source})")

    if not plan_file:
        # Output warning so user knows spec wasn't created
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "⚠️ Spec NOT saved: Could not find plan file. Check ~/.claude/plans/"
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    if not Path(plan_file).exists():
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"⚠️ Spec NOT saved: Plan file not found: {plan_file}"
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Read plan content
    content = Path(plan_file).read_text()
    debug_log(f"Plan content length: {len(content)} chars")

    # Generate spec filename
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    key_feature = extract_key_feature(content)
    spec_filename = f"{timestamp}_spec_{key_feature}.md"

    # Ensure specs directory exists
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    # Write spec file
    spec_path = SPECS_DIR / spec_filename
    spec_path.write_text(content)
    debug_log(f"Wrote spec file: {spec_path}")

    # Also record the source plan file for debugging
    plan_name = Path(plan_file).name

    # Output confirmation
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"📋 Spec saved: specs/{spec_filename} (from {plan_name})"
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()

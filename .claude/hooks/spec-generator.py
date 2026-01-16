#!/usr/bin/env python3
"""
PostToolUse Hook: Generate spec file when ExitPlanMode is called.
Copies the finalized plan to /opt/tangerine/specs/ with timestamped naming.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SPECS_DIR = Path("/opt/tangerine/specs")


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


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "ExitPlanMode":
        sys.exit(0)

    # Get plan file from tool_input (ExitPlanMode may pass plan file info)
    tool_input = input_data.get("tool_input", {})

    # Try multiple sources for plan file path
    plan_file = None

    # Check if plan file path is in tool_input
    if isinstance(tool_input, dict):
        plan_file = tool_input.get("plan_file", "")

    # Check session_info as fallback
    if not plan_file:
        session_info = input_data.get("session_info", {})
        plan_file = session_info.get("plan_file", "")

    # Check tool_result for plan file path
    if not plan_file:
        tool_result = input_data.get("tool_result", "")
        if isinstance(tool_result, str):
            # Look for plan file path in result text
            match = re.search(r'plan.*?(/[^\s]+\.md)', tool_result, re.IGNORECASE)
            if match:
                plan_file = match.group(1)

    # If no plan file found, try to find most recent plan in ~/.claude/plans/
    if not plan_file:
        plans_dir = Path.home() / ".claude" / "plans"
        if plans_dir.exists():
            plan_files = list(plans_dir.glob("*.md"))
            if plan_files:
                # Get most recently modified
                plan_file = str(max(plan_files, key=lambda p: p.stat().st_mtime))

    if not plan_file or not Path(plan_file).exists():
        sys.exit(0)

    # Read plan content
    content = Path(plan_file).read_text()

    # Generate spec filename
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    key_feature = extract_key_feature(content)
    spec_filename = f"{timestamp}_spec_{key_feature}.md"

    # Ensure specs directory exists
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    # Write spec file
    spec_path = SPECS_DIR / spec_filename
    spec_path.write_text(content)

    # Output confirmation
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"📋 Spec saved: specs/{spec_filename}"
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()

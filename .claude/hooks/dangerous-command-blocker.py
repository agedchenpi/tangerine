#!/usr/bin/env python3
"""
PreToolUse Hook: Block dangerous database commands before execution.

This hook prevents accidental data loss by blocking dangerous SQL and Docker
commands that could destroy database data or volumes.
"""
import json
import re
import sys

# Critical patterns that cause unrecoverable data loss
CRITICAL_PATTERNS = [
    # SQL patterns
    (r'\bDROP\s+TABLE\b(?!\s+IF\s+EXISTS)', "DROP TABLE without IF EXISTS"),
    (r'\bDROP\s+DATABASE\b', "DROP DATABASE"),
    (r'\bDROP\s+SCHEMA\b', "DROP SCHEMA"),
    (r'\bTRUNCATE\b', "TRUNCATE"),
    (r'\bDELETE\s+FROM\s+\w+\s*;', "DELETE without WHERE clause"),
    (r'\bDELETE\s+FROM\s+\w+\s+WHERE\s+1\s*=\s*1', "DELETE WHERE 1=1 (deletes all)"),
    # Docker patterns that destroy database volumes
    (r'docker\s+compose\s+down\s+.*--volumes', "docker compose down --volumes (destroys DB)"),
    (r'docker\s+compose\s+down\s+.*-v\b', "docker compose down -v (destroys DB)"),
    (r'docker\s+volume\s+rm', "docker volume rm (destroys data)"),
]

# High risk patterns that modify data broadly
HIGH_RISK_PATTERNS = [
    (r'\bUPDATE\s+\w+\s+SET\b(?!.*\bWHERE\b)', "UPDATE without WHERE clause"),
    (r'\bALTER\s+TABLE\s+\w+\s+DROP\s+COLUMN\b', "DROP COLUMN"),
]


def check_command(command: str) -> tuple[bool, str]:
    """
    Check command for dangerous patterns.

    Args:
        command: The bash command to check

    Returns:
        Tuple of (is_dangerous, reason)
    """
    # Check critical patterns (case-insensitive)
    for pattern, reason in CRITICAL_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, f"🚫 CRITICAL: {reason}"

    # Check high risk patterns (case-insensitive)
    for pattern, reason in HIGH_RISK_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, f"⚠️ HIGH RISK: {reason}"

    return False, ""


def main():
    """Main hook execution."""
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "")

    # Only check Bash commands
    if tool_name != "Bash":
        sys.exit(0)  # Allow non-Bash tools

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    is_dangerous, reason = check_command(command)

    if is_dangerous:
        # Truncate command for display if too long
        command_display = command[:200]
        if len(command) > 200:
            command_display += "..."

        output = {
            "decision": "block",
            "reason": f"{reason}\n\nCommand: {command_display}\n\n"
                     f"This command could cause unrecoverable data loss. "
                     f"If you need to run this command, execute it manually outside Claude Code."
        }
        print(json.dumps(output))
        sys.exit(2)  # Block execution

    sys.exit(0)  # Allow execution


if __name__ == "__main__":
    main()

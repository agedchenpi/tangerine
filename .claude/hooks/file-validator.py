#!/usr/bin/env python3
"""
PostToolUse Hook: Validate edited files for syntax errors.
Runs AFTER Edit/Write/MultiEdit operations.
"""
import json
import subprocess
import sys
from pathlib import Path


def validate_python_syntax(file_path: str) -> tuple[bool, str]:
    """Validate Python syntax using py_compile in Docker container."""
    try:
        # Convert absolute path to container path
        container_path = file_path.replace("/opt/tangerine/", "/app/")

        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "tangerine",
             "python", "-m", "py_compile", container_path],
            capture_output=True,
            timeout=10,
            cwd="/opt/tangerine"
        )
        if result.returncode != 0:
            error_msg = result.stderr.decode().strip()
            # Clean up the error message
            if error_msg:
                return False, error_msg
        return True, ""
    except subprocess.TimeoutExpired:
        return True, ""  # Don't block on timeout
    except FileNotFoundError:
        return True, ""  # Docker not available
    except Exception:
        return True, ""  # Don't block on validation errors


def validate_sql_patterns(file_path: str) -> tuple[bool, list]:
    """Check for dangerous SQL patterns."""
    try:
        content = Path(file_path).read_text()
        content_upper = content.upper()
        warnings = []

        # Check for DELETE without WHERE
        if "DELETE FROM" in content_upper and "WHERE" not in content_upper:
            warnings.append("DELETE without WHERE clause detected")

        # Check for DROP TABLE without IF EXISTS
        if "DROP TABLE" in content_upper and "IF EXISTS" not in content_upper:
            warnings.append("DROP TABLE without IF EXISTS detected")

        # Check for TRUNCATE (usually dangerous)
        if "TRUNCATE" in content_upper:
            warnings.append("TRUNCATE statement detected - verify this is intentional")

        # Check for UPDATE without WHERE
        lines = content.split('\n')
        in_update = False
        for line in lines:
            line_upper = line.upper().strip()
            if line_upper.startswith("UPDATE "):
                in_update = True
            elif in_update and line_upper.startswith("SET "):
                continue
            elif in_update and "WHERE" in line_upper:
                in_update = False
            elif in_update and line_upper.endswith(";"):
                warnings.append("UPDATE without WHERE clause detected")
                in_update = False

        return len(warnings) == 0, warnings
    except Exception:
        return True, []


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name not in ["Edit", "Write", "MultiEdit"]:
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    messages = []

    # Validate Python files
    if file_path.endswith(".py"):
        valid, error = validate_python_syntax(file_path)
        if not valid:
            messages.append(f"❌ Python syntax error in {Path(file_path).name}:")
            messages.append(f"   {error}")

    # Validate SQL files
    elif file_path.endswith(".sql"):
        valid, warnings = validate_sql_patterns(file_path)
        if not valid:
            messages.append(f"⚠️  SQL warnings in {Path(file_path).name}:")
            for warning in warnings:
                messages.append(f"   • {warning}")

    if messages:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n".join([
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    "📝 FILE VALIDATION",
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    *messages,
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ])
            }
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for dangerous-command-blocker hook.
Run: python3 test_dangerous_command_blocker.py
"""
import json
import subprocess
import sys

# Test cases: (command, should_block, description)
TEST_CASES = [
    # Critical patterns - should block
    ("DROP TABLE users;", True, "DROP TABLE without IF EXISTS"),
    ("DROP DATABASE tangerine_db;", True, "DROP DATABASE"),
    ("DROP SCHEMA feeds;", True, "DROP SCHEMA"),
    ("TRUNCATE TABLE tdataset;", True, "TRUNCATE"),
    ("DELETE FROM users;", True, "DELETE without WHERE"),
    ("DELETE FROM users WHERE 1=1;", True, "DELETE WHERE 1=1"),
    ("docker compose down --volumes", True, "docker compose down --volumes"),
    ("docker compose down -v", True, "docker compose down -v"),
    ("docker volume rm tangerine_data", True, "docker volume rm"),

    # High risk patterns - should block
    ("UPDATE users SET active=false;", True, "UPDATE without WHERE"),
    ("ALTER TABLE users DROP COLUMN email;", True, "DROP COLUMN"),

    # Safe patterns - should allow
    ("SELECT * FROM dba.tdatasource;", False, "SELECT query"),
    ("INSERT INTO tdatasource VALUES (1, 'Test');", False, "INSERT"),
    ("CREATE TABLE IF NOT EXISTS test (id INT);", False, "CREATE TABLE"),
    ("DROP TABLE IF EXISTS test;", False, "DROP TABLE IF EXISTS"),
    ("DELETE FROM users WHERE id = 5;", False, "DELETE with WHERE"),
    ("UPDATE users SET active=false WHERE id = 5;", False, "UPDATE with WHERE"),
    ("docker compose up -d", False, "docker compose up"),
    ("docker compose logs admin", False, "docker compose logs"),
]


def test_command(command: str) -> tuple[bool, str]:
    """Test a command against the hook. Returns (was_blocked, reason)."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {
            "command": command
        }
    }

    try:
        result = subprocess.run(
            ["python3", "dangerous-command-blocker.py"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd="/opt/tangerine/.claude/hooks"
        )

        if result.returncode == 2:  # Blocked
            output = json.loads(result.stdout)
            return True, output.get("reason", "Unknown")
        elif result.returncode == 0:  # Allowed
            return False, "Allowed"
        else:
            return False, f"Unexpected exit code: {result.returncode}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    """Run all test cases."""
    print("=" * 80)
    print("Testing Dangerous Command Blocker Hook")
    print("=" * 80)

    passed = 0
    failed = 0

    for command, should_block, description in TEST_CASES:
        was_blocked, reason = test_command(command)

        # Check if result matches expectation
        success = (was_blocked == should_block)

        if success:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"\n{status}: {description}")
        print(f"  Command: {command[:60]}...")
        print(f"  Expected: {'BLOCK' if should_block else 'ALLOW'}")
        print(f"  Got: {'BLOCKED' if was_blocked else 'ALLOWED'}")
        if was_blocked:
            print(f"  Reason: {reason[:100]}")

    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print("=" * 80)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

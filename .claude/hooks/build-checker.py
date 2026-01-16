#!/usr/bin/env python3
"""
Stop Hook: Run quick checks after Claude finishes responding.
Provides reminders about code quality and documentation.
"""
import json
import os
import subprocess
import sys
from pathlib import Path


def run_ruff_check() -> tuple[int, str]:
    """Run ruff linter and return error count."""
    try:
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "tangerine",
             "ruff", "check", "--quiet", "--output-format=concise", "."],
            capture_output=True,
            timeout=30,
            cwd="/opt/tangerine"
        )
        if result.returncode != 0:
            output = result.stdout.decode().strip()
            if output:
                lines = [l for l in output.split('\n') if l.strip()]
                return len(lines), output[:500]
        return 0, ""
    except subprocess.TimeoutExpired:
        return 0, ""
    except FileNotFoundError:
        return 0, ""
    except Exception:
        return 0, ""


def check_active_dev_docs() -> str | None:
    """Check if there's an active task in dev/active/."""
    dev_active = Path("/opt/tangerine/dev/active")
    if not dev_active.exists():
        return None

    # Find task directories (not .gitkeep)
    tasks = [d for d in dev_active.iterdir() if d.is_dir()]
    if tasks:
        return tasks[0].name  # Return first active task
    return None


def detect_significant_work(transcript_path: str) -> dict:
    """Analyze transcript to detect if significant work was done."""
    indicators = {
        "files_edited": 0,
        "tests_run": False,
        "feature_work": False,
        "has_plan": False,
    }

    try:
        if not transcript_path or not Path(transcript_path).exists():
            return indicators

        content = Path(transcript_path).read_text()

        # Count file edits (rough heuristic)
        indicators["files_edited"] = content.count('"tool_name": "Edit"')
        indicators["files_edited"] += content.count('"tool_name": "Write"')

        # Check for test runs
        indicators["tests_run"] = "pytest" in content.lower()

        # Check for feature-related work
        feature_keywords = ["implement", "feature", "add", "create", "build"]
        indicators["feature_work"] = any(kw in content.lower() for kw in feature_keywords)

        # Check for plan mode
        indicators["has_plan"] = "plan" in content.lower() and "approved" in content.lower()

    except Exception:
        pass

    return indicators


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    transcript_path = input_data.get("transcript_path", "")
    messages = []
    doc_reminders = []

    # Run quick lint check
    error_count, lint_output = run_ruff_check()

    if error_count > 0:
        if error_count <= 5:
            messages.append(f"🔍 Linting: {error_count} issue(s) found")
            for line in lint_output.split('\n')[:5]:
                if line.strip():
                    messages.append(f"   {line}")
        else:
            messages.append(f"🔍 Linting: {error_count} issues found")
            messages.append("   Run `ruff check .` to see details")

    # Check for active dev docs
    active_task = check_active_dev_docs()
    if active_task:
        doc_reminders.append(f"📋 Active task: `{active_task}` - remember to update dev docs")

    # Detect significant work and remind about documentation
    work = detect_significant_work(transcript_path)

    if work["files_edited"] >= 3 or work["feature_work"]:
        doc_reminders.append("📝 Significant changes detected - consider:")
        doc_reminders.append("   • Run `/doc-feature` to document the feature")
        doc_reminders.append("   • Update `CHANGELOG.md` with the change")

    if work["has_plan"] and work["files_edited"] >= 5:
        doc_reminders.append("✅ Plan appears complete - don't forget to:")
        doc_reminders.append("   • Document the feature in `docs/features/`")
        doc_reminders.append("   • Add entry to `CHANGELOG.md`")
        doc_reminders.append("   • Run `/dev-docs-update` if task is done")

    # Only output if there are issues or reminders
    # Note: Stop hooks don't support hookSpecificOutput, so we print to stderr
    # for informational purposes (visible in debug mode) and optionally set stopReason
    if messages or doc_reminders:
        output_lines = [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 POST-RESPONSE CHECK",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        if messages:
            output_lines.extend(messages)
            output_lines.append("")

        if doc_reminders:
            output_lines.extend(doc_reminders)

        output_lines.append("")
        output_lines.append("💡 Run /test to verify changes")
        output_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Print to stderr for visibility (doesn't affect JSON validation)
        print("\n".join(output_lines), file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()

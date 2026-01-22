#!/usr/bin/env python3
"""
Stop Hook: Run quick checks after Claude finishes responding.
Provides reminders about code quality and documentation.

Also handles spec generation when plan mode was used during session.
(Moved from spec-generator.py since ExitPlanMode doesn't trigger PostToolUse hooks)
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

SPECS_DIR = Path("/opt/tangerine/specs")


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


def extract_key_feature(content: str) -> str:
    """Extract key feature from first heading in plan.

    Parses the first # or ## heading and converts it to a URL-friendly slug.
    Returns 'unnamed' if no heading is found.
    """
    match = re.search(r'^#+ (.+)$', content, re.MULTILINE)
    if match:
        title = match.group(1).strip()
        # Remove common prefixes like "Plan:" or "Spec:"
        title = re.sub(r'^(Plan|Spec|Feature|Fix):\s*', '', title, flags=re.IGNORECASE)
        # Convert to slug: lowercase, replace spaces/special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        return slug[:50]  # Limit length
    return "unnamed"


def find_recent_plan_file(max_age_minutes: int = 30) -> Path | None:
    """Find most recently modified plan file within time window.

    Args:
        max_age_minutes: Only consider files modified within this many minutes

    Returns:
        Path to plan file or None if not found
    """
    plans_dir = Path.home() / ".claude" / "plans"
    if not plans_dir.exists():
        return None

    plan_files = list(plans_dir.glob("*.md"))
    if not plan_files:
        return None

    # Filter to recent files only
    now = datetime.now()
    cutoff = now - timedelta(minutes=max_age_minutes)

    recent_files = []
    for pf in plan_files:
        mtime = datetime.fromtimestamp(pf.stat().st_mtime)
        if mtime >= cutoff:
            recent_files.append((pf, mtime))

    if not recent_files:
        return None

    # Return most recently modified
    return max(recent_files, key=lambda x: x[1])[0]


def spec_already_exists(plan_content: str) -> bool:
    """Check if a spec already exists for this plan content.

    Compares first heading to avoid duplicate specs.
    """
    if not SPECS_DIR.exists():
        return False

    key_feature = extract_key_feature(plan_content)
    if key_feature == "unnamed":
        return False

    # Check for existing spec with same feature name (any timestamp)
    existing = list(SPECS_DIR.glob(f"*_spec_{key_feature}.md"))
    return len(existing) > 0


def generate_spec_from_plan() -> str | None:
    """Check for recent plan and generate spec if needed.

    Returns:
        Message about spec generation, or None if nothing done
    """
    plan_file = find_recent_plan_file(max_age_minutes=30)
    if not plan_file:
        return None

    content = plan_file.read_text()
    if not content.strip():
        return None

    # Skip if spec already exists for this plan
    if spec_already_exists(content):
        return None

    # Generate spec filename
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    key_feature = extract_key_feature(content)
    spec_filename = f"{timestamp}_spec_{key_feature}.md"

    # Ensure specs directory exists
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    # Write spec file
    spec_path = SPECS_DIR / spec_filename
    spec_path.write_text(content)

    return f"📋 Spec saved: specs/{spec_filename}"


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

    # Check for recent plan files and generate spec if needed
    spec_message = generate_spec_from_plan()
    if spec_message:
        messages.insert(0, spec_message)

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

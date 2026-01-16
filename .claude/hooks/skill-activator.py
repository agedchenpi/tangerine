#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Analyze prompt and inject skill activation reminders.
Runs BEFORE Claude sees the user message.
"""
import json
import re
import sys
from pathlib import Path


def load_skill_rules():
    """Load skill activation rules from config file."""
    rules_path = Path(__file__).parent.parent / "skill-rules.json"
    if rules_path.exists():
        return json.loads(rules_path.read_text())
    return {}


def check_keyword_match(prompt: str, keywords: list) -> bool:
    """Check if any keywords appear in the prompt."""
    prompt_lower = prompt.lower()
    return any(kw.lower() in prompt_lower for kw in keywords)


def check_intent_match(prompt: str, patterns: list) -> bool:
    """Check if any intent patterns match the prompt."""
    for pattern in patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            return True
    return False


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    rules = load_skill_rules()
    triggered_skills = []

    for skill_name, config in rules.items():
        triggers = config.get("promptTriggers", {})
        keywords = triggers.get("keywords", [])
        patterns = triggers.get("intentPatterns", [])

        if check_keyword_match(prompt, keywords) or check_intent_match(prompt, patterns):
            priority = config.get("priority", "medium")
            skill_type = config.get("type", "domain")
            triggered_skills.append({
                "name": skill_name,
                "priority": priority,
                "type": skill_type
            })

    if triggered_skills:
        # Sort by priority (critical > high > medium > low)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        triggered_skills.sort(key=lambda x: priority_order.get(x["priority"], 2))

        skill_names = [s["name"] for s in triggered_skills]
        critical_skills = [s["name"] for s in triggered_skills if s["type"] == "guardrail"]

        reminder_parts = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🎯 SKILL ACTIVATION CHECK",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Relevant skills: {', '.join(skill_names)}",
            "",
            "Before proceeding, load and follow patterns from:",
        ]

        for skill in triggered_skills:
            reminder_parts.append(f"  • .claude/skills/{skill['name']}/SKILL.md")

        if critical_skills:
            reminder_parts.extend([
                "",
                f"⚠️  GUARDRAIL SKILLS ACTIVE: {', '.join(critical_skills)}",
                "   Follow these guidelines strictly!",
            ])

        reminder_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "\n".join(reminder_parts)
            }
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()

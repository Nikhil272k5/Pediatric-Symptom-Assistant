import json
from pathlib import Path


def load_kb(path: str) -> list[dict]:
    """Load knowledge base from JSONL file."""
    rules = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rules.append(json.loads(line))
    return rules


def format_kb_for_prompt(rules: list[dict]) -> str:
    """Format KB rules as a readable string for injection into prompts."""
    lines = []
    for rule in rules:
        lines.append(
            f"ID: {rule['id']} | Signal: {rule['signal']} | "
            f"Keywords: {', '.join(rule['keywords'])} | "
            f"Triage floor: {rule['triage_floor']}"
        )
    return "\n".join(lines)

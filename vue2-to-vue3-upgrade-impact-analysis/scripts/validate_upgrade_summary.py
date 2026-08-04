#!/usr/bin/env python3
"""Validate the compact, standalone Vue2→Vue3 analysis summary."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


MAX_BYTES = 12 * 1024
PLACEHOLDER = re.compile(r"^(?:|<[^>]+>|tbd|todo|n/?a|none|null|待定|待补)$", re.I)
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
ENUMS = {
    "schema": {"vue3-upgrade-summary/v1"},
    "producer": {"vue2-to-vue3-upgrade-impact-analysis"},
    "analysis_status": {"partial", "blocked", "complete"},
    "decision_status": {"needs_choice", "not_needed", "decided"},
    "batch_implementation_gate": {"frozen", "ready"},
    "visual_acceptance_required": {"yes", "no"},
}


def validate(data: Any, raw_size: int) -> list[str]:
    errors: list[str] = []
    if raw_size > MAX_BYTES:
        errors.append(f"summary exceeds {MAX_BYTES} bytes")
    if not isinstance(data, dict):
        return errors + ["summary root must be an object"]
    for field, allowed in ENUMS.items():
        if data.get(field) not in allowed:
            errors.append(f"{field} must be one of {sorted(allowed)}")
    for field in ["recommended_path", "report_path", "inventory_path", "next_action"]:
        value = data.get(field)
        if not isinstance(value, str) or PLACEHOLDER.match(value.strip()):
            errors.append(f"{field} must be a concrete string")
    axes = data.get("axes")
    if not isinstance(axes, dict) or set(axes) != {"runtime", "build", "topology"}:
        errors.append("axes must contain runtime, build, and topology")
    for field, limit in [("decision_records", 20), ("blockers", 20), ("high_risks", 20)]:
        value = data.get(field)
        if not isinstance(value, list) or len(value) > limit or not all(isinstance(item, str) for item in value):
            errors.append(f"{field} must be a string array with at most {limit} items")
    visual = data.get("ui_visual_risk")
    if data.get("visual_acceptance_required") == "yes":
        if not isinstance(visual, dict):
            errors.append("ui_visual_risk is required when visual acceptance is required")
        else:
            states = visual.get("required_states")
            if not isinstance(states, list) or not states or len(states) > 20:
                errors.append("ui_visual_risk.required_states must contain 1..20 items")
            action = visual.get("recommended_next_action")
            if not isinstance(action, str) or PLACEHOLDER.match(action.strip()):
                errors.append("ui_visual_risk.recommended_next_action is required")
    generated_at = data.get("generated_at")
    if not isinstance(generated_at, str) or not RFC3339.match(generated_at):
        errors.append("generated_at must be RFC3339")
    if any(field in data for field in ["required_skill", "consumer_skill", "handoff_skill"]):
        errors.append("summary must not declare another Skill dependency")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_upgrade_summary.py <upgrade-summary.json>", file=sys.stderr)
        return 4
    path = Path(argv[1])
    if not path.is_file():
        print(f"ERROR: summary not found: {path}", file=sys.stderr)
        return 4
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
        return 3
    errors = validate(data, len(raw))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 3
    print("PASS: compact Vue upgrade summary valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

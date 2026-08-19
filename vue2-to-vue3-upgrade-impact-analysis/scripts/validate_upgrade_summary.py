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
    "lockfile_status": {"present", "absent", "unparsed"},
}
RECIPE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
# Fixed implementation-stage phase order. A recipe may only be sequenced after one
# of these anchors or after another named recipe.
SEQUENCE_ANCHORS = (
    "baseline-green",
    "visual-baseline",
    "node-lane",
    "first-install",
    "runtime-cutover",
    "post-cutover",
)


def first_cycle(edges: dict[str, list[str]]) -> list[str]:
    """Return one recipe→recipe cycle as a path, or an empty list when acyclic."""
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str]:
        state[node] = 1
        stack.append(node)
        for following in edges.get(node, []):
            if state.get(following) == 1:
                return stack[stack.index(following) :] + [following]
            if state.get(following, 0) == 0 and following in edges:
                found = visit(following)
                if found:
                    return found
        stack.pop()
        state[node] = 2
        return []

    for node in edges:
        if state.get(node, 0) == 0:
            found = visit(node)
            if found:
                return found
    return []


def validate_recipe_constraints(data: Any, recipes: list[str], status: Any) -> list[str]:
    errors: list[str] = []
    value = data.get("recipe_constraints")
    if value is None:
        if status == "complete" and recipes:
            errors.append("complete summary requires recipe_constraints")
        return errors
    if not isinstance(value, list) or len(value) > 20:
        errors.append("recipe_constraints must be an array with at most 20 items")
        return errors
    allowed_after = set(SEQUENCE_ANCHORS) | set(recipes)
    edges: dict[str, list[str]] = {}
    seen: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            errors.append("recipe_constraints items must be objects")
            return errors
        raw_id = item.get("id")
        if not isinstance(raw_id, str) or not RECIPE_ID.fullmatch(raw_id.strip()):
            errors.append("recipe_constraints[].id must be a kebab/ascii recipe id")
            continue
        recipe_id = raw_id.strip()
        seen.append(recipe_id)
        if item.get("atomic") not in {"yes", "no"}:
            errors.append(f"recipe_constraints[{recipe_id}].atomic must be yes or no")
        after = item.get("after")
        if not isinstance(after, list) or not all(isinstance(entry, str) for entry in after):
            errors.append(f"recipe_constraints[{recipe_id}].after must be a string array")
            continue
        cleaned = [entry.strip() for entry in after]
        unknown = sorted({entry for entry in cleaned if entry not in allowed_after})
        if unknown:
            errors.append(
                f"recipe_constraints[{recipe_id}].after must reference a sequence anchor "
                f"{list(SEQUENCE_ANCHORS)} or a named recipe: " + ", ".join(unknown)
            )
        if recipe_id in cleaned:
            errors.append(f"recipe_constraints[{recipe_id}].after must not reference itself")
        edges[recipe_id] = [entry for entry in cleaned if entry in set(recipes)]
    duplicates = sorted({item for item in seen if seen.count(item) > 1})
    if duplicates:
        errors.append("recipe_constraints ids must be unique: " + ", ".join(duplicates))
    if recipes:
        missing = sorted(set(recipes) - set(seen))
        if missing:
            errors.append(
                "recipe_constraints must cover each named_recipes id: " + ", ".join(missing)
            )
        extra = sorted(set(seen) - set(recipes))
        if extra:
            errors.append(
                "recipe_constraints must not add ids outside named_recipes: " + ", ".join(extra)
            )
    cycle = first_cycle(edges)
    if cycle:
        errors.append("recipe_constraints after edges must not form a cycle: " + " -> ".join(cycle))
    return errors


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
            # Downstream visual gates (e.g. delivery-visual-evidence/v1) hard-require
            # at least five unique required-state evidence rows.
            if not isinstance(states, list) or len(states) < 5 or len(states) > 20:
                errors.append("ui_visual_risk.required_states must contain 5..20 items")
            action = visual.get("recommended_next_action")
            if not isinstance(action, str) or PLACEHOLDER.match(action.strip()):
                errors.append("ui_visual_risk.recommended_next_action is required")
    for field, limit in [("named_recipes", 20), ("named_validations", 20)]:
        value = data.get(field)
        if not isinstance(value, list) or len(value) > limit:
            errors.append(f"{field} must be a string array with at most {limit} items")
            continue
        if not all(isinstance(item, str) and item.strip() and not PLACEHOLDER.match(item.strip()) for item in value):
            errors.append(f"{field} items must be non-empty concrete strings")
            continue
        if field == "named_recipes" and not all(RECIPE_ID.fullmatch(item.strip()) for item in value):
            errors.append("named_recipes items must be kebab/ascii recipe ids")
    recipes = data.get("named_recipes") if isinstance(data.get("named_recipes"), list) else []
    validations = data.get("named_validations") if isinstance(data.get("named_validations"), list) else []
    status = data.get("analysis_status")
    decision = data.get("decision_status")
    gate = data.get("batch_implementation_gate")
    path = data.get("recommended_path")
    if status == "complete" and path != "deferred-inventory-only" and not recipes:
        errors.append("complete summary requires named_recipes")
    if status == "complete" and not validations:
        errors.append("complete summary requires named_validations")
    if status == "complete" and data.get("next_action") != "analysis_complete":
        errors.append("complete summary next_action must be analysis_complete")
    if decision == "needs_choice" and data.get("next_action") == "analysis_complete":
        errors.append("needs_choice summary must not use next_action=analysis_complete")
    if gate == "ready" and data.get("lockfile_status") != "present":
        errors.append("batch_implementation_gate=ready requires lockfile_status=present")
    if recipes and validations:
        blob = " ".join(str(item) for item in validations)
        missing = [item for item in recipes if item not in blob]
        if missing:
            errors.append(
                "named_validations must mention each named_recipes id: " + ", ".join(missing)
            )
    errors.extend(
        validate_recipe_constraints(
            data, [item.strip() for item in recipes if isinstance(item, str)], status
        )
    )
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

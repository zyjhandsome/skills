#!/usr/bin/env python3
"""Validate the compact, standalone visual parity summary."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


MAX_BYTES = 8 * 1024
PLACEHOLDER = re.compile(r"^(?:|<[^>]+>|tbd|todo|n/?a|none|null|待定|待补)$", re.I)
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
ENUMS = {
    "schema": {"visual-parity-summary/v1"},
    "producer": {"frontend-ui-stack-visual-parity"},
    "analysis_status": {"partial", "blocked", "complete"},
    "strategy_status": {"needs_choice", "decided", "not_needed"},
    "remediation_status": {"not_started", "awaiting_go", "in_progress", "done", "skipped"},
    "assessment_mode": {"strict_parity", "consistency_review"},
    "final_visual_result": {"pending", "pass", "fail"},
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
    for field in ["source_snapshot", "baseline_source", "report_path"]:
        value = data.get(field)
        if not isinstance(value, str) or PLACEHOLDER.match(value.strip()):
            errors.append(f"{field} must be a concrete string")
    for field, limit in [
        ("primary_routes", 10),
        ("top_findings", 10),
        ("change_candidates", 10),
        ("required_states", 20),
    ]:
        value = data.get(field)
        if not isinstance(value, list) or len(value) > limit or not all(isinstance(item, str) for item in value):
            errors.append(f"{field} must be a string array with at most {limit} items")
    artifact_index = data.get("artifact_index")
    if not isinstance(artifact_index, dict) or not isinstance(artifact_index.get("capture_manifest"), str):
        errors.append("artifact_index.capture_manifest is required")
    generated_at = data.get("generated_at")
    if not isinstance(generated_at, str) or not RFC3339.match(generated_at):
        errors.append("generated_at must be RFC3339")
    if "data:" in json.dumps(data) or "base64" in json.dumps(data).lower():
        errors.append("summary must reference artifacts by path, never embed image data")
    if data.get("analysis_status") == "complete" and data.get("final_visual_result") != "pass":
        errors.append("complete summary requires final_visual_result=pass")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_visual_summary.py <visual-summary.json>", file=sys.stderr)
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
    print("PASS: compact visual summary valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

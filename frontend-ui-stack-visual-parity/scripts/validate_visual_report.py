#!/usr/bin/env python3
"""Validate the machine anchors of a UI stack visual parity report.

Exit 0: valid shape. Exit 3: validation errors. Exit 4: path missing.
Zero third-party dependencies.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


PLACEHOLDER = re.compile(r"^(?:|<[^>]+>|tbd|todo|n/?a|none|null|待定|待补)$", re.I)
REQUIRED_CHECKS = ["V0", "V1", "V2", "V3", "V4", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
REQUIRED_STATUS = {
    "schema": {"visual-parity-report/v1"},
    "producer": {"frontend-ui-stack-visual-parity"},
    "execution_scope": {"analysis_only", "analysis_and_remediation"},
    "analysis_status": {"partial", "blocked", "complete"},
    "strategy_status": {"needs_choice", "decided", "not_needed"},
    "remediation_status": {"not_started", "awaiting_go", "in_progress", "done", "skipped"},
    "assessment_mode": {"strict_parity", "consistency_review"},
    "behavior_parity_required": {"yes", "no"},
    "visual_acceptance_required": {"yes", "no"},
    "final_visual_result": {"pending", "pass", "fail"},
}
OPTIONAL_STATUS = {
    "parity_topology": {"same-repo", "cross-repo"},
}


def clean(value: str) -> str:
    return value.strip().strip("`").strip()


def table_map(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if not match:
            continue
        key, value = clean(match.group(1)), clean(match.group(2))
        if key and key not in {"字段", "Id", "id", "---"} and not set(key) <= {"-", ":"}:
            values.setdefault(key, value)
    return values


def checklist(text: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\|\s*`?([VPS]\d+)`?\s*\|\s*([^|]+?)\s*\|", line, re.I)
        if match:
            rows[match.group(1).upper()] = clean(match.group(2)).lower()
    return rows


def section_value(text: str, label: str) -> str | None:
    match = re.search(rf"^-\s*{re.escape(label)}\s*[：:]\s*(.+)$", text, re.M | re.I)
    return clean(match.group(1)) if match else None


def validate(text: str) -> list[str]:
    errors: list[str] = []
    fields = table_map(text)
    for field, allowed in REQUIRED_STATUS.items():
        value = clean(fields.get(field, ""))
        if value not in allowed:
            errors.append(f"{field} must be one of {sorted(allowed)}")
    for field, allowed in OPTIONAL_STATUS.items():
        if field in fields:
            value = clean(fields.get(field, ""))
            if value not in allowed:
                errors.append(f"{field} must be one of {sorted(allowed)}")

    scope = clean(fields.get("execution_scope", ""))
    source_snapshot = clean(fields.get("source_snapshot", ""))
    assessment = clean(fields.get("assessment_mode", ""))
    analysis = clean(fields.get("analysis_status", ""))
    strategy = clean(fields.get("strategy_status", ""))
    remediation = clean(fields.get("remediation_status", ""))
    final_result = clean(fields.get("final_visual_result", ""))
    topology = clean(fields.get("parity_topology", "same-repo")) or "same-repo"

    if PLACEHOLDER.match(source_snapshot):
        errors.append("report requires a concrete source_snapshot")
    if scope == "analysis_and_remediation" and remediation == "done":
        phase_b_go = section_value(text, "Phase B go")
        if phase_b_go is None or PLACEHOLDER.match(phase_b_go) or phase_b_go.lower() in {"未批准", "n/a-analysis-only"}:
            errors.append("completed remediation requires a revision-bound Phase B go")

    baseline = section_value(text, "baseline_source / substitute_standard")
    if assessment == "strict_parity" and (baseline is None or PLACEHOLDER.match(baseline)):
        errors.append("strict_parity requires a traceable baseline_source")
    if assessment == "consistency_review" and (baseline is None or PLACEHOLDER.match(baseline)):
        errors.append("consistency_review requires an approved substitute standard")

    if topology == "cross-repo":
        for label in ("baseline_root", "candidate_root", "forbid_baseline_mutation"):
            value = section_value(text, label)
            if value is None or PLACEHOLDER.match(value):
                # also allow status-table fields
                value = clean(fields.get(label, ""))
            if not value or PLACEHOLDER.match(value):
                errors.append(f"cross-repo requires concrete {label}")
            elif label == "forbid_baseline_mutation" and value.lower() not in {"yes", "true"}:
                errors.append("cross-repo forbid_baseline_mutation must be yes")

    artifacts = section_value(text, "baseline_artifacts_status")
    if artifacts is None:
        artifacts = clean(fields.get("baseline_artifacts_status", ""))
    if assessment == "strict_parity":
        if artifacts not in {"present", "missing", "unverified"}:
            errors.append(
                "strict_parity requires baseline_artifacts_status: present|missing|unverified"
            )
        elif analysis == "complete" and artifacts != "present":
            errors.append(
                "complete strict_parity requires baseline_artifacts_status=present"
            )
        elif artifacts == "missing" and analysis not in {"blocked", "partial"}:
            errors.append(
                "baseline_artifacts_status=missing requires analysis_status blocked|partial"
            )

    for field in [
        "adapter / browser",
        "viewport / device_scale_factor",
        "locale / timezone / theme",
        "font_ready_condition",
        "animation_policy",
        "data_fixture / dynamic_masks",
    ]:
        if PLACEHOLDER.match(clean(fields.get(field, ""))):
            errors.append(f"capture context missing {field}")

    state_rows = re.findall(r"^\|\s*(?!id\b|---)([^|]+)\|[^\n]*\|\s*(pass|fail|pending|skip)\s*\|\s*$", text, re.M | re.I)
    if len(state_rows) < 5:
        errors.append("required state evidence must contain at least five result rows")

    checks = checklist(text)
    for check in REQUIRED_CHECKS:
        result = checks.get(check)
        if result is None:
            errors.append(f"missing verification row {check}")
        elif analysis == "complete" and result != "pass":
            errors.append(f"complete report requires {check}=pass")

    if analysis == "complete":
        if strategy == "needs_choice":
            errors.append("complete report cannot have strategy_status=needs_choice")
        if remediation == "done" and final_result != "pass":
            errors.append("remediation_status=done requires final_visual_result=pass")
        if final_result != "pass":
            errors.append("complete report requires final_visual_result=pass")

    for label in [
        "blocking_decisions",
        "change_candidates",
        "validation_scope",
        "residual_risks",
        "artifact_index",
        "next_action",
    ]:
        value = section_value(text, label)
        if value is None or PLACEHOLDER.match(value):
            errors.append(f"output index missing {label}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_visual_report.py <report.md>", file=sys.stderr)
        return 4
    path = Path(argv[1])
    if not path.is_file():
        print(f"ERROR: report not found: {path}", file=sys.stderr)
        return 4
    errors = validate(path.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 3
    print("PASS: visual parity report contract valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

#!/usr/bin/env python3
"""Validate a Delivery Family handoff JSON object using only the standard library."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Compatibility is major-based: any delivery-family/<SUPPORTED_FAMILY_MAJOR>.x is accepted
# so additive minor bumps do not require editing this validator. CURRENT_FAMILY_VERSION is
# the version the templates currently emit; it is informational only.
SUPPORTED_FAMILY_MAJOR = 1
CURRENT_FAMILY_VERSION = "delivery-family/1.1"
SCHEMA_VERSION = "delivery-handoff/v1"
STAGES = {
    "delivery-explore",
    "delivery-frame-spec",
    "delivery-plan-tasks",
    "delivery-execute-verify",
}
TOP_LEVEL = {
    "schema_version",
    "family_version",
    "type",
    "handoff_id",
    "generated_at",
    "stage",
    "source_revision",
    "state_source",
    "capability_snapshot",
    "capability_bindings",
    "presentation_capability",
    "gate_status",
    "evidence_mode",
    "next_skill",
    "next_action",
    "required_inputs",
    "stop_condition",
    "stage_payload",
    "presentation",
}
STAGE_PAYLOAD_KEYS = {
    "delivery-explore": {
        "direction_alignment",
        "chosen_direction",
        "non_goals",
        "code_anchors",
        "risk_signal",
        "unknowns",
    },
    "delivery-frame-spec": {
        "route",
        "risk",
        "confirmed_artifacts",
        "forbidden_scope",
        "open_questions",
    },
    "delivery-plan-tasks": {
        "plan_tasks",
        "plan_decisions",
        "traceability",
        "readiness_result",
        "validation_plan",
        "risk_gates",
        "parallel_ownership",
    },
    "delivery-execute-verify": {
        "overall_status",
        "task_status",
        "current_failures_or_blocks",
        "artifact_backflow",
        "alignment_backflow",
        "fresh_verification_evidence",
        "spec_coherence",
        "code_review",
        "archive",
        "asset_writeback",
    },
}


def family_major(value: Any) -> int | None:
    if not isinstance(value, str) or not value.startswith("delivery-family/"):
        return None
    tail = value.split("/", 1)[1]
    try:
        return int(tail.split(".", 1)[0])
    except ValueError:
        return None


def is_rfc3339(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def require_object(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return {}
    return value


def require_array(value: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return []
    return value


def require_keys(obj: dict[str, Any], keys: set[str], path: str, errors: list[str]) -> None:
    missing = sorted(keys - set(obj))
    if missing:
        errors.append(f"{path} missing keys: {', '.join(missing)}")


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    root = require_object(data, "$", errors)
    require_keys(root, TOP_LEVEL, "$", errors)
    # Forward-compatible extension: keys prefixed with "x_" are reserved for additive,
    # non-authoritative extensions and are ignored by this validator.
    extras = sorted(k for k in set(root) - TOP_LEVEL if not k.startswith("x_"))
    if extras:
        errors.append(f"$ has unsupported top-level keys: {', '.join(extras)}")

    if root.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if family_major(root.get("family_version")) != SUPPORTED_FAMILY_MAJOR:
        errors.append(
            f"family_version major must be {SUPPORTED_FAMILY_MAJOR} "
            f"(e.g. {CURRENT_FAMILY_VERSION}); got {root.get('family_version')!r}"
        )
    if root.get("type") != "delivery-handoff":
        errors.append("type must be delivery-handoff")
    if not isinstance(root.get("handoff_id"), str) or not root.get("handoff_id"):
        errors.append("handoff_id must be a non-empty string")
    if not is_rfc3339(root.get("generated_at")):
        errors.append("generated_at must be an RFC3339 timestamp")

    stage = root.get("stage")
    if stage not in STAGES:
        errors.append(f"stage must be one of: {', '.join(sorted(STAGES))}")

    revision = require_object(root.get("source_revision"), "source_revision", errors)
    require_keys(revision, {"repo_head", "artifact_revision", "state_observed_at"}, "source_revision", errors)
    if revision.get("repo_head") is not None and not isinstance(revision.get("repo_head"), str):
        errors.append("source_revision.repo_head must be a string or null")
    if revision.get("artifact_revision") is not None and not isinstance(revision.get("artifact_revision"), str):
        errors.append("source_revision.artifact_revision must be a string or null")
    if not is_rfc3339(revision.get("state_observed_at")):
        errors.append("source_revision.state_observed_at must be RFC3339")

    state = require_object(root.get("state_source"), "state_source", errors)
    require_keys(state, {"kind", "label", "anchor"}, "state_source", errors)
    if state.get("kind") not in {"none", "openspec_change"}:
        errors.append("state_source.kind must be none or openspec_change")
    if state.get("kind") == "openspec_change" and not state.get("anchor"):
        errors.append("state_source.anchor is required for openspec_change")
    if state.get("kind") == "none" and state.get("anchor") is not None:
        errors.append("state_source.anchor must be null when kind is none")

    snapshot = require_object(root.get("capability_snapshot"), "capability_snapshot", errors)
    require_keys(snapshot, {"memory", "openspec", "superpowers"}, "capability_snapshot", errors)
    if snapshot.get("memory") not in {"ok", "stale-index", "down"}:
        errors.append("capability_snapshot.memory has an invalid value")
    if snapshot.get("openspec") not in {"initialized", "cli-only", "unavailable"}:
        errors.append("capability_snapshot.openspec has an invalid value")
    superpowers = snapshot.get("superpowers")
    if not (superpowers in {"loaded", "missing"} or (isinstance(superpowers, str) and superpowers.startswith("partial("))):
        errors.append("capability_snapshot.superpowers has an invalid value")

    bindings = require_object(root.get("capability_bindings"), "capability_bindings", errors)
    require_keys(bindings, {"openspec", "memory", "superpowers", "subagents"}, "capability_bindings", errors)

    presentation_cap = require_object(root.get("presentation_capability"), "presentation_capability", errors)
    require_keys(presentation_cap, {"mode", "source"}, "presentation_capability", errors)
    if presentation_cap.get("mode") not in {"delivery-ui/v1", "legacy-v0", "markdown"}:
        errors.append("presentation_capability.mode has an invalid value")
    if presentation_cap.get("source") not in {"host-declared", "detected", "unknown"}:
        errors.append("presentation_capability.source has an invalid value")

    gate = require_object(root.get("gate_status"), "gate_status", errors)
    require_keys(
        gate,
        {
            "status",
            "summary",
            "evidence",
            "approved_by",
            "approved_at",
            "binds_to_revision",
            "accepted_warning_ids",
        },
        "gate_status",
        errors,
    )
    if gate.get("status") not in {"n/a", "pending", "pass", "warn", "block"}:
        errors.append("gate_status.status has an invalid value")
    require_array(gate.get("evidence"), "gate_status.evidence", errors)
    warnings = require_array(gate.get("accepted_warning_ids"), "gate_status.accepted_warning_ids", errors)
    if any(not isinstance(warning, str) or not warning for warning in warnings):
        errors.append("gate_status.accepted_warning_ids must contain non-empty strings")
    approval_values = (gate.get("approved_by"), gate.get("approved_at"), gate.get("binds_to_revision"))
    if any(value is not None for value in approval_values):
        if any(value is None for value in approval_values):
            errors.append("gate approval requires approved_by, approved_at, and binds_to_revision together")
        if not is_rfc3339(gate.get("approved_at")):
            errors.append("gate_status.approved_at must be RFC3339 when approval exists")
        if gate.get("binds_to_revision") != revision.get("artifact_revision"):
            errors.append("gate approval must bind source_revision.artifact_revision")
    if gate.get("status") == "warn" and (root.get("next_skill") or root.get("next_action")) and not warnings:
        errors.append("a continuing warn gate requires accepted_warning_ids")
    visible_gate = json.dumps(
        {"summary": gate.get("summary"), "evidence": gate.get("evidence")},
        ensure_ascii=False,
    )
    for warning in warnings:
        if isinstance(warning, str) and warning and warning not in visible_gate:
            errors.append(f"accepted warning id is not visible in gate summary/evidence: {warning}")

    if root.get("evidence_mode") not in {"full", "degraded"}:
        errors.append("evidence_mode must be full or degraded")
    if root.get("next_skill") is not None and root.get("next_action") is not None:
        errors.append("next_skill and next_action cannot both be non-null")
    require_array(root.get("required_inputs"), "required_inputs", errors)
    if not isinstance(root.get("stop_condition"), str):
        errors.append("stop_condition must be a string")

    payload = require_object(root.get("stage_payload"), "stage_payload", errors)
    if stage in STAGE_PAYLOAD_KEYS:
        require_keys(payload, STAGE_PAYLOAD_KEYS[stage], "stage_payload", errors)

    presentation = require_object(root.get("presentation"), "presentation", errors)
    require_keys(
        presentation,
        {"schema", "from_task", "to_task", "summary", "evidence", "continue_prompt"},
        "presentation",
        errors,
    )
    if presentation.get("schema") != "delivery-presentation/v1":
        errors.append("presentation.schema must be delivery-presentation/v1")
    require_array(presentation.get("evidence"), "presentation.evidence", errors)

    if stage == "delivery-explore":
        if payload.get("direction_alignment") not in {"selected", "needs_choice"}:
            errors.append("Explore direction_alignment must be selected or needs_choice")
        if state.get("kind") != "none":
            errors.append("Explore must use state_source.kind none")
        if root.get("next_skill") not in {None, "delivery-frame-spec"}:
            errors.append("Explore next_skill may only be delivery-frame-spec or null")
        if payload.get("direction_alignment") == "selected" and root.get("next_skill") != "delivery-frame-spec":
            errors.append("selected Explore direction must transition to delivery-frame-spec")
        if payload.get("direction_alignment") == "needs_choice" and root.get("next_skill") is not None:
            errors.append("needs_choice Explore state cannot transition")
    elif stage == "delivery-frame-spec":
        if root.get("next_skill") not in {None, "delivery-explore", "delivery-plan-tasks", "delivery-execute-verify"}:
            errors.append("Frame next_skill is invalid")
        if root.get("next_skill") in {"delivery-plan-tasks", "delivery-execute-verify"}:
            if state.get("kind") != "openspec_change":
                errors.append("Frame mutation transition requires openspec_change state")
            if gate.get("status") not in {"pass", "warn"}:
                errors.append("Frame mutation transition requires a pass or accepted warn gate")
            if gate.get("binds_to_revision") is None:
                errors.append("Frame mutation transition requires revision-bound approval")
            if not revision.get("artifact_revision"):
                errors.append("Frame mutation transition requires artifact_revision")
    elif stage == "delivery-plan-tasks":
        if state.get("kind") != "openspec_change":
            errors.append("Plan must use openspec_change state")
        if root.get("next_skill") not in {None, "delivery-execute-verify"}:
            errors.append("Plan next_skill may only be delivery-execute-verify or null")
        if root.get("next_skill") == "delivery-execute-verify":
            if gate.get("status") not in {"pass", "warn"}:
                errors.append("Plan execution transition requires a pass or accepted warn gate")
            if gate.get("binds_to_revision") is None:
                errors.append("Plan execution transition requires revision-bound approval")
            if not revision.get("artifact_revision"):
                errors.append("Plan execution transition requires artifact_revision")
    elif stage == "delivery-execute-verify":
        if state.get("kind") != "openspec_change":
            errors.append("Execute must use openspec_change state")
        if root.get("next_skill") is not None:
            errors.append("Execute must use next_action, not next_skill")
        archive = require_object(payload.get("archive"), "stage_payload.archive", errors)
        review = require_object(payload.get("code_review"), "stage_payload.code_review", errors)
        if payload.get("overall_status") == "verified":
            if archive.get("status") != "deferred_to_openspec":
                errors.append("verified Execute handoff must defer archive to OpenSpec")
            if root.get("next_action") is None:
                errors.append("verified Execute handoff requires the resolved archive next_action")
            # G7: Medium/High cannot close on self_fresh_context.
            # Risk is not always in stage_payload for execute; infer from review fields.
            mode = review.get("mode")
            indep = review.get("independent_review")
            if mode is None or indep is None:
                errors.append(
                    "verified Execute handoff requires code_review.mode and code_review.independent_review"
                )
            elif mode == "self_fresh_context" and indep not in {"low_accepted"}:
                errors.append(
                    "verified Execute handoff cannot use self_fresh_context except low_accepted"
                )
            elif mode == "independent" and indep not in {
                "required_pass",
                "required_warn_accepted",
            }:
                errors.append(
                    "independent code_review.independent_review must be required_pass or required_warn_accepted"
                )
            elif mode not in {"independent", "self_fresh_context"}:
                errors.append("code_review.mode must be independent or self_fresh_context")
            if review.get("status") not in {"pass", "warn"}:
                errors.append("verified Execute handoff requires code_review.status pass or warn")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON file path, or - for stdin")
    args = parser.parse_args()

    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID JSON: {exc}", file=sys.stderr)
        return 2

    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: valid delivery-handoff/v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

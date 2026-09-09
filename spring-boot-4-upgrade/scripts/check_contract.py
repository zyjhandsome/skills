"""Read-only consistency check of recorded migration evidence, not a command runner."""
import argparse
import hashlib
import json
from pathlib import Path
import re


BASE_CHECKS = {"resolution", "build", "tests", "runtime", "contracts"}


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value):
        return None
    return tuple(map(int, value.split(".")))


def check_contract(data, base, gate, snapshot):
    """Return errors; evidence authenticity and the caller's snapshot need separate review."""
    errors = []
    if not isinstance(data, dict):
        return ["contract must be an object"]
    if data.get("schema_version") != 1:
        errors.append("unsupported schema_version")
    if data.get("mode") != "migrate":
        errors.append("migration gates require mode=migrate; assess cannot authorize writes")
    source, target = version(data.get("source_boot")), version(data.get("target_boot"))
    if not source or source[0] not in (3, 4):
        errors.append("source must be an exact Boot 3.x or 4.x GA version")
    if not target or target[0] != 4:
        errors.append("target must be an exact Boot 4.x GA version")
    if source and target and source > target:
        errors.append("downgrade is outside this upgrade contract")
    if not snapshot or snapshot.strip().lower() in {"unknown", "pending"}:
        errors.append("supply a current, independently checked code snapshot identifier")
    scope = data.get("scope")
    if not isinstance(scope, dict):
        return errors + ["scope must be an object"]
    included = scope.get("included")
    if not isinstance(included, list) or not included or any(not isinstance(x, str) or not x.strip() for x in included):
        errors.append("scope.included must describe actual modules/profiles/runtime")
    required = scope.get("required_checks")
    if not isinstance(required, list) or any(not isinstance(x, str) or not x for x in required):
        return errors + ["scope.required_checks must be a list of check names"]
    if not BASE_CHECKS.issubset(required):
        errors.append("required_checks must include resolution/build/tests/runtime/contracts")
    exclusions = scope.get("excluded", [])
    if not isinstance(exclusions, list):
        errors.append("scope.excluded must be a list")
    else:
        for item in exclusions:
            if not isinstance(item, dict) or not item.get("item") or not item.get("reason"):
                errors.append("each excluded scope needs item and reason")
    if gate == "boot4":
        if not source or source[0] != 3 or source[:2] > (3, 5):
            errors.append("boot4 gate is for the 3.x-to-4 transition, not 4.x patch upgrades")
        stage = data.get("baseline35")
        if not isinstance(stage, dict):
            return errors + ["missing baseline35 checkpoint"]
        resolved = version(stage.get("resolved_boot"))
        if not resolved or resolved[:2] != (3, 5):
            errors.append("checkpoint must resolve to exact Boot 3.5.x")
    else:
        stage = data.get("final")
        if not isinstance(stage, dict):
            return errors + ["missing final evidence"]
        if version(stage.get("resolved_boot")) != target:
            errors.append("final resolved_boot differs from exact target")
        for key in ("properties_migrator_present", "temporary_rewrite_present"):
            if stage.get(key) is not False:
                errors.append(f"final.{key} must be false, supported by final resolution/build evidence")
        bridges = stage.get("bridges")
        if not isinstance(bridges, list):
            errors.append("final.bridges must be an explicit list")
        elif gate == "verified" and bridges:
            errors.append("bridges remain; cannot report verified")
        elif gate == "verified-with-bridges":
            if not bridges:
                errors.append("use verified when no compatibility bridges remain")
            for bridge in bridges:
                if not isinstance(bridge, dict) or not all(bridge.get(k) for k in ("component", "reason", "exit_condition")):
                    errors.append("each bridge needs component/reason/exit_condition")
    if stage.get("snapshot") != snapshot:
        errors.append("checkpoint does not match supplied current snapshot")
    checks = stage.get("checks")
    if not isinstance(checks, dict):
        return errors + ["stage.checks must be an object"]
    for name in sorted(set(required) | BASE_CHECKS):
        item = checks.get(name)
        if not isinstance(item, dict):
            errors.append(f"missing required check: {name}")
            continue
        if item.get("status") != "passed" or type(item.get("exit_code")) is not int or item["exit_code"] != 0:
            errors.append(f"{name}: required check did not pass")
        if item.get("snapshot") != snapshot:
            errors.append(f"{name}: stale snapshot")
        if not all(isinstance(item.get(k), str) and item[k].strip() for k in ("command", "cwd", "environment")):
            errors.append(f"{name}: missing command/cwd/environment")
        artifacts = item.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{name}: no evidence artifacts")
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str) or not artifact["path"]:
                errors.append(f"{name}: invalid artifact path")
                continue
            try:
                raw = (base / artifact["path"]).read_bytes()
                if not raw or hashlib.sha256(raw).hexdigest() != artifact.get("sha256"):
                    errors.append(f"{name}: empty or mismatched artifact")
            except (OSError, ValueError):
                errors.append(f"{name}: evidence artifact unavailable")
        if name == "tests":
            counts = [item.get(k) for k in ("executed", "failures", "errors", "skipped")]
            if any(type(v) is not int or v < 0 for v in counts):
                errors.append("tests: invalid execution counts")
            elif counts[0] < 1 or counts[1] or counts[2]:
                errors.append("tests: no executed tests or tests failed")
            if item.get("skipped") and not item.get("skip_coverage_reason"):
                errors.append("tests: unexplained skipped tests")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--gate", required=True, choices=("boot4", "verified", "verified-with-bridges"))
    parser.add_argument("--snapshot", required=True, help="Independently checked HEAD + worktree/config fingerprint")
    args = parser.parse_args()
    try:
        data = json.loads(args.contract.read_text(encoding="utf-8-sig"))
        errors = check_contract(data, args.contract.resolve().parent, args.gate, args.snapshot)
    except (OSError, ValueError) as exc:
        errors = [f"cannot read contract: {exc}"]
    print(json.dumps({"gate": args.gate, "consistent": not errors, "errors": errors,
                      "limit": "Checks recorded evidence only; does not run tests or verify snapshot authenticity."}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

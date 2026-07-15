#!/usr/bin/env python3
"""Run deterministic, non-mutating checks on a Delivery/OpenSpec change directory."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


TASK_START = re.compile(r"(?m)^- \[(?P<status>[ xX])\] .+$")
FIELD_PATTERNS = {
    "target": re.compile(r"(?mi)^\s+-\s+(?:目标文件/符号|Exact files/symbols)\s*:\s*(\S.*)$"),
    "command": re.compile(r"(?mi)^\s+-\s+(?:验证命令/动作|Validation command/action)\s*:\s*(\S.*)$"),
    "expected": re.compile(r"(?mi)^\s+-\s+(?:预期结果|Expected result)\s*:\s*(\S.*)$"),
}
VERIFICATION_PATTERNS = {
    "command": re.compile(r"(?mi)^\s*(?:[-*]\s*)?(?:命令|command)\s*:\s*(\S.*)$"),
    "time": re.compile(r"(?mi)^\s*(?:[-*]\s*)?(?:时间|timestamp|date)\s*:\s*(\S.*)$"),
    "result": re.compile(r"(?mi)^\s*(?:[-*]\s*)?(?:结果|result)\s*:\s*(\S.*)$"),
}
PLACEHOLDER = re.compile(r"^(?:<[^>]+>|tbd|todo|n/?a|none|null|待定|待补)$", re.IGNORECASE)


def task_blocks(text: str) -> list[tuple[str, str]]:
    starts = list(TASK_START.finditer(text))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        blocks.append((match.group("status"), text[match.start() : end]))
    return blocks


def contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER.fullmatch(value.strip().strip("`")))


def is_rfc3339(value: str) -> bool:
    try:
        datetime.fromisoformat(value.strip().strip("`").replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("change_dir", type=Path)
    parser.add_argument("--tasks", type=Path, help="Tasks path; defaults to <change_dir>/tasks.md")
    parser.add_argument("--verification", type=Path, help="Verification path; defaults to <change_dir>/verification.md")
    parser.add_argument("--repo-root", type=Path, help="Optional repo root for competing-root-state checks")
    parser.add_argument("--claim-verified", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    change_dir = args.change_dir.resolve()
    if not change_dir.is_dir():
        print(f"ERROR: change directory does not exist: {change_dir}", file=sys.stderr)
        return 2

    tasks_path = (args.tasks or change_dir / "tasks.md").resolve()
    verification_path = (args.verification or change_dir / "verification.md").resolve()

    if not tasks_path.is_file():
        errors.append(f"tasks artifact missing: {tasks_path}")
        blocks: list[tuple[str, str]] = []
    else:
        tasks_text = tasks_path.read_text(encoding="utf-8")
        blocks = task_blocks(tasks_text)
        if not blocks:
            errors.append("tasks artifact has no checkbox task blocks")
        for number, (_, block) in enumerate(blocks, 1):
            for field, pattern in FIELD_PATTERNS.items():
                match = pattern.search(block)
                if not match or is_placeholder(match.group(1)):
                    errors.append(f"task {number} missing non-empty {field} field")

    if args.repo_root:
        repo_root = args.repo_root.resolve()
        for name in ("brief.md", "workflow-state.yaml"):
            candidate = repo_root / name
            if candidate.exists():
                errors.append(f"possible competing root state source: {candidate}")

    if args.claim_verified:
        incomplete = [number for number, (status, _) in enumerate(blocks, 1) if status == " "]
        if incomplete:
            errors.append(f"verified claim has incomplete tasks: {', '.join(map(str, incomplete))}")
        if not verification_path.is_file():
            errors.append(f"verification artifact missing: {verification_path}")
        else:
            verification = verification_path.read_text(encoding="utf-8")
            evidence: dict[str, str] = {}
            for label, pattern in VERIFICATION_PATTERNS.items():
                match = pattern.search(verification)
                if not match or is_placeholder(match.group(1)):
                    errors.append(f"verification artifact missing {label} evidence")
                else:
                    evidence[label] = match.group(1)
            if "time" in evidence and not is_rfc3339(evidence["time"]):
                errors.append("verification time evidence must be RFC3339")
            if "result" in evidence and not contains_any(
                evidence["result"], [r"\bpass(?:ed)?\b", r"\bfail(?:ed)?\b", r"exit\s*code", r"退出码", r"通过", r"失败"]
            ):
                errors.append("verification result must state pass/fail or an exit code")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: delivery change checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

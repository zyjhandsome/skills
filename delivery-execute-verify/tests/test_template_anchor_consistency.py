#!/usr/bin/env python3
"""P0-2 regression lock: the machine anchors documented in the Chinese templates must
stay parseable by validate_delivery_change.py.

Guards against the R3 failure mode where tasks were written with near-synonym labels
("文件/符号", "验证：") and --claim-verified silently failed, forcing a tasks rewrite
and a full revision re-bind.

Checks:
1. tasks-template.md task field labels -> FIELD_PATTERNS all match.
2. verification-template.md 主验证证据 labels -> VERIFICATION_PATTERNS all match,
   and the filled sample passes the RFC3339/result-shape checks.

Standard library only. Exit 0 = consistent, 1 = drift detected.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import validate_delivery_change as vdc  # noqa: E402

TASKS_TEMPLATE = SKILL_DIR.parent / "delivery-plan-tasks" / "references" / "tasks-template.md"
VERIFICATION_TEMPLATE = SKILL_DIR / "references" / "verification-template.md"

# The three anchors every task block must carry (must stay in sync with FIELD_PATTERNS).
REQUIRED_TASK_FIELDS = ("target", "command", "expected")
SAMPLE_TASK_VALUES = {
    "target": "src/example.py::do_thing",
    "command": "pytest tests/test_example.py -q",
    "expected": "exit 0，全部通过",
}


def fail(messages: list[str]) -> int:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    return 1


def extract_task_label_lines(template_text: str) -> list[str]:
    """Return the indented '- <label>：' lines of the first checkbox task in the template."""
    match = vdc.TASK_START.search(template_text)
    if not match:
        return []
    tail = template_text[match.start():]
    end = tail.find("\n## ")
    block = tail if end == -1 else tail[:end]
    return re.findall(r"(?m)^(\s+-\s+[^:：\n]+)[:：]\s*$", block)


def check_tasks_template() -> list[str]:
    errors: list[str] = []
    if not TASKS_TEMPLATE.is_file():
        return [f"tasks template missing: {TASKS_TEMPLATE}"]
    text = TASKS_TEMPLATE.read_text(encoding="utf-8")

    label_lines = extract_task_label_lines(text)
    if not label_lines:
        return ["could not locate the example task block in tasks-template.md"]

    # Rebuild the template's own task block with sample values filled in, then run the
    # exact production patterns against it.
    filled_lines = ["- [x] 任务 1：模板锚点一致性样例"]
    filled_lines.extend(f"{label}：占位样例值" for label in label_lines)
    synthetic = "\n".join(filled_lines) + "\n"
    # Overwrite the three machine-anchor values with realistic samples so the
    # placeholder filter cannot mask a label mismatch.
    for field in REQUIRED_TASK_FIELDS:
        pattern = vdc.FIELD_PATTERNS[field]
        if not pattern.search(synthetic):
            errors.append(
                f"tasks-template.md label drift: FIELD_PATTERNS[{field!r}] does not match "
                "any label line in the template task block"
            )

    # And the fully-valid sample must satisfy the real per-task check end to end.
    valid_block = "\n".join(
        ["- [x] 任务 1：模板锚点一致性样例"]
        + [f"  - 目标文件/符号：{SAMPLE_TASK_VALUES['target']}"]
        + [f"  - 验证命令/动作：{SAMPLE_TASK_VALUES['command']}"]
        + [f"  - 预期结果：{SAMPLE_TASK_VALUES['expected']}"]
    )
    for field in REQUIRED_TASK_FIELDS:
        match = vdc.FIELD_PATTERNS[field].search(valid_block)
        if not match or vdc.is_placeholder(match.group(1)):
            errors.append(f"canonical sample task block failed FIELD_PATTERNS[{field!r}]")
    return errors


def check_verification_template() -> list[str]:
    errors: list[str] = []
    if not VERIFICATION_TEMPLATE.is_file():
        return [f"verification template missing: {VERIFICATION_TEMPLATE}"]
    text = VERIFICATION_TEMPLATE.read_text(encoding="utf-8")

    for label in ("命令", "时间", "结果"):
        if not re.search(rf"(?m)^\s*-\s*{label}[:：]", text):
            errors.append(f"verification-template.md no longer contains the anchor line '- {label}：'")

    sample = (
        "### 主验证证据\n"
        "- 命令：pytest -q\n"
        "- 时间：2026-07-17T00:00:00Z\n"
        "- 结果：exit 0 / 通过\n"
    )
    evidence: dict[str, str] = {}
    for field, pattern in vdc.VERIFICATION_PATTERNS.items():
        match = pattern.search(sample)
        if not match or vdc.is_placeholder(match.group(1)):
            errors.append(f"canonical verification sample failed VERIFICATION_PATTERNS[{field!r}]")
        else:
            evidence[field] = match.group(1)
    if "time" in evidence and not vdc.is_rfc3339(evidence["time"]):
        errors.append("canonical verification sample time failed the RFC3339 check")
    if "result" in evidence and not vdc.contains_any(
        evidence["result"],
        [r"\bpass(?:ed)?\b", r"\bfail(?:ed)?\b", r"exit\s*code", r"退出码", r"通过", r"失败", r"exit\s*\d+"],
    ):
        errors.append("canonical verification sample result failed the pass/fail shape check")
    return errors


# P3-2 lock: the accepted limited synonym set, and writings that must stay rejected.
# Extending FIELD_PATTERNS without updating both lists here is a test failure by design.
ACCEPTED_ALIASES = {
    "target": ["目标文件/符号", "文件/符号", "Exact files/symbols", "Target files/symbols"],
    "command": ["验证命令/动作", "验证命令", "验证动作", "验证", "Validation command/action", "Validation command"],
    "expected": ["预期结果", "预期", "期望结果", "Expected result"],
}
REJECTED_LABELS = {
    "target": ["目标", "涉及文件", "改动文件"],
    "command": ["最小验证", "命令", "测试命令", "失败测试或已批准替代验证"],
    "expected": ["结果", "验收标准", "完成定义"],
}


def check_synonym_lock() -> list[str]:
    errors: list[str] = []
    for field, aliases in ACCEPTED_ALIASES.items():
        pattern = vdc.FIELD_PATTERNS[field]
        for alias in aliases:
            if not pattern.search(f"  - {alias}：样例值\n"):
                errors.append(f"accepted alias no longer matches FIELD_PATTERNS[{field!r}]: {alias!r}")
    for field, labels in REJECTED_LABELS.items():
        pattern = vdc.FIELD_PATTERNS[field]
        for label in labels:
            if pattern.search(f"  - {label}：样例值\n"):
                errors.append(
                    f"FIELD_PATTERNS[{field!r}] became over-broad: undocumented label {label!r} matches"
                )
    return errors


def main() -> int:
    errors = check_tasks_template() + check_verification_template() + check_synonym_lock()
    if errors:
        return fail(errors)
    print("PASS: template machine anchors are consistent with validate_delivery_change.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

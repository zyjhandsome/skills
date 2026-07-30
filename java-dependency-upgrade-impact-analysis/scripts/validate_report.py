#!/usr/bin/env python3
"""Validate a Java dependency upgrade decision packet against the report contract.

This validator checks structure and internal consistency only. It never reads a
build file, resolves versions, or reaches the network — a passing report is still
just a well-formed report, not verified evidence.

Usage:
    python scripts/validate_report.py <report.md> [--json]
    python scripts/validate_report.py --evidence-dir <dir> [--json]

Exit codes:
    0  no errors
    2  usage error
    3  validation errors found
    4  path not found
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPORT_NAME = "java-dependency-upgrade-report.md"
BATCH_INDEX_NAME = "BATCH-INDEX.md"

STATUS_ENUMS: dict[str, set[str]] = {
    "analysis_status": {"partial", "blocked", "complete"},
    "decision_status": {"needs_choice", "not_needed", "decided"},
    "batch_implementation_gate": {"frozen", "ready"},
    "behavior_parity_required": {"yes", "no"},
    "network_mode": {"online", "offline", "partial"},
}
FREE_TEXT_STATUS = ("report_path",)

REQUIRED_SECTIONS = (
    "基线与假设",
    "依赖清单与解析路径",
    "主 Owner 决策",
    "残差冲突与 Override",
    "六层影响分析",
    "风险与 SemVer 分类",
    "确认队列",
    "验证矩阵",
    "回滚与责任人",
    "未决问题与证据缺口",
)

INVENTORY_COLUMNS = (
    "组件",
    "当前解析版本",
    "目标版本",
    "目标存在性",
    "建议处置",
    "有效 Owner",
    "权威层",
)
QUEUE_COLUMNS = ("组件", "状态", "选项")

EXISTENCE_VALUES = {"yes", "no", "unknown", "n/a"}
TREATMENT_VALUES = {
    "remove",
    "upgrade-self",
    "upgrade-owner",
    "upgrade-introducer",
    "exclude",
    "force-align",
    "replace-component",
    "replace-introducer",
    "defer",
}
NO_TARGET_TREATMENTS = {"remove", "exclude", "defer"}
QUEUE_STATUSES = {"ready", "blocked", "decided", "deferred"}
# Match Maven/Spring qualifiers with optional trailing digits: RC1, Alpha5, Beta2, M5.
NON_GA_PATTERN = re.compile(
    r"(?i)(?:^|[.\-])(?:alpha|beta|rc|cr|m|milestone|snapshot)\d*(?:[.\-]|$)"
)

ENTRY_KINDS = {"exact", "open-target"}
AUTHORITY_LAYERS = {"jdk", "boot-bom", "platform-plugin", "app-library"}

GAV_TOKEN = re.compile(r"[A-Za-z0-9_.\-]+:[A-Za-z0-9_.\-*]+")


@dataclass
class Findings:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def extend(self, other: "Findings", prefix: str) -> None:
        self.errors.extend(f"{prefix}{item}" for item in other.errors)
        self.warnings.extend(f"{prefix}{item}" for item in other.warnings)


def clean_cell(cell: str) -> str:
    return cell.replace("`", "").replace("*", "").strip()


def split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [clean_cell(cell) for cell in stripped.split("|")]


def is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s|:\-]+\|?", line.strip()))


def is_table_line(line: str) -> bool:
    return line.strip().startswith("|")


def looks_like_placeholder(value: str) -> bool:
    """Template values such as ``partial / blocked / complete`` were never filled."""
    return " / " in value or not value or value in {"-", "—", "TBD", "待填"}


def read_tables(lines: list[str]) -> list[list[list[str]]]:
    """Return every markdown table as a list of rows (header first, separator dropped)."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in lines:
        if is_table_line(line):
            if not is_separator(line):
                current.append(split_row(line))
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def section_bounds(lines: list[str]) -> dict[str, tuple[int, int]]:
    heading_at: list[tuple[int, str]] = [
        (index, line) for index, line in enumerate(lines) if line.startswith("#")
    ]
    bounds: dict[str, tuple[int, int]] = {}
    for position, (index, line) in enumerate(heading_at):
        end = heading_at[position + 1][0] if position + 1 < len(heading_at) else len(lines)
        for name in REQUIRED_SECTIONS:
            if name in line and name not in bounds:
                bounds[name] = (index + 1, end)
    return bounds


def gav_tokens(cell: str) -> set[str]:
    return set(GAV_TOKEN.findall(cell))


def check_status_table(lines: list[str], findings: Findings) -> dict[str, str]:
    values: dict[str, str] = {}
    for table in read_tables(lines):
        for row in table:
            if len(row) < 2:
                continue
            key = row[0]
            if key in STATUS_ENUMS or key in FREE_TEXT_STATUS:
                values.setdefault(key, row[1])

    for key in list(STATUS_ENUMS) + list(FREE_TEXT_STATUS):
        if key not in values:
            findings.error(f"状态字段缺失：{key}")
            continue
        value = values[key]
        if looks_like_placeholder(value):
            findings.error(f"状态字段未填写（仍是模板取值）：{key} = {value or '空'}")
        elif key in STATUS_ENUMS and value not in STATUS_ENUMS[key]:
            allowed = " / ".join(sorted(STATUS_ENUMS[key]))
            findings.error(f"状态字段取值非法：{key} = {value}（允许：{allowed}）")

    analysis = values.get("analysis_status")
    decision = values.get("decision_status")
    if analysis == "complete" and decision == "needs_choice":
        findings.error(
            "analysis_status=complete 与 decision_status=needs_choice 冲突：确认队列未清空不得完成分析"
        )
    return values


def check_sections(lines: list[str], findings: Findings) -> dict[str, tuple[int, int]]:
    bounds = section_bounds(lines)
    missing = [name for name in REQUIRED_SECTIONS if name not in bounds]
    for name in missing:
        findings.error(f"必选章节缺失：{name}")

    present = [(bounds[name][0], name) for name in REQUIRED_SECTIONS if name in bounds]
    ordered = [name for _, name in sorted(present)]
    expected = [name for name in REQUIRED_SECTIONS if name in bounds]
    if ordered != expected:
        findings.error(f"章节顺序与契约不一致：实际顺序 {' → '.join(ordered)}")
    return bounds


def find_table(lines: list[str], bounds: tuple[int, int], columns: tuple[str, ...]) -> list[list[str]] | None:
    start, end = bounds
    for table in read_tables(lines[start:end]):
        header = table[0]
        if all(any(column == cell for cell in header) for column in columns):
            return table
    return None


def check_inventory(
    lines: list[str],
    bounds: dict[str, tuple[int, int]],
    findings: Findings,
) -> list[tuple[str, str, str, str]]:
    """Return (component, existence, target, row_text) for each inventory row."""
    section = "依赖清单与解析路径"
    if section not in bounds:
        return []
    table = find_table(lines, bounds[section], INVENTORY_COLUMNS)
    if table is None:
        findings.error(
            f"「{section}」缺少契约要求的表头列：{'、'.join(INVENTORY_COLUMNS)}"
        )
        return []
    header, rows = table[0], table[1:]
    if not rows:
        findings.error(f"「{section}」表为空：至少需要一个候选行")
        return []

    component_at = header.index("组件")
    existence_at = header.index("目标存在性")
    treatment_at = header.index("建议处置")
    target_at = header.index("目标版本")
    results: list[tuple[str, str, str, str]] = []
    for row in rows:
        needed = max(component_at, existence_at, treatment_at, target_at)
        if len(row) <= needed:
            findings.error(f"依赖清单行列数不足：{' | '.join(row)}")
            continue
        component = row[component_at]
        existence = row[existence_at].lower()
        treatment = row[treatment_at].lower()
        target = row[target_at]
        row_text = " | ".join(row)
        if not component:
            findings.error("依赖清单存在空组件行")
            continue
        if existence not in EXISTENCE_VALUES:
            findings.error(
                f"目标存在性取值非法：{component} = {row[existence_at] or '空'}"
                f"（允许：{' / '.join(sorted(EXISTENCE_VALUES))}）"
            )
            continue
        if treatment not in TREATMENT_VALUES:
            findings.error(
                f"建议处置取值非法：{component} = {row[treatment_at] or '空'}"
                f"（允许：{' / '.join(sorted(TREATMENT_VALUES))}）"
            )
            continue
        if existence == "n/a" and treatment not in NO_TARGET_TREATMENTS:
            findings.error(
                f"目标存在性 n/a 仅允许无目标处置（remove/exclude/defer）："
                f"{component} 当前为 {treatment}"
            )
        if target and NON_GA_PATTERN.search(target) and existence == "yes":
            findings.warn(
                f"目标版本疑似非 GA，却标记目标存在性=yes：{component} → {target}"
                "（须 target_channel=non-ga；未显式 non-ga-allowed 时队列不得 ready）"
            )
        results.append((component, existence, target, row_text))
    return results


def check_queue(
    lines: list[str],
    bounds: dict[str, tuple[int, int]],
    inventory: list[tuple[str, str, str, str]],
    statuses: dict[str, str],
    findings: Findings,
) -> None:
    section = "确认队列"
    if section not in bounds:
        return
    table = find_table(lines, bounds[section], QUEUE_COLUMNS)
    if table is None:
        findings.error(f"「{section}」缺少契约要求的表头列：{'、'.join(QUEUE_COLUMNS)}")
        return
    header, rows = table[0], table[1:]
    if not rows:
        if statuses.get("decision_status") != "not_needed":
            findings.error(
                f"「{section}」表为空，但 decision_status 不是 not_needed：确认队列必须出现过"
            )
        return

    component_at = header.index("组件")
    status_at = header.index("状态")
    queue: list[tuple[str, str, str]] = []
    for row in rows:
        if len(row) <= max(component_at, status_at):
            findings.error(f"确认队列行列数不足：{' | '.join(row)}")
            continue
        status = row[status_at].lower()
        if status not in QUEUE_STATUSES:
            findings.error(
                f"确认队列状态非法：{row[component_at]} = {row[status_at] or '空'}"
                f"（允许：{' / '.join(sorted(QUEUE_STATUSES))}）"
            )
            continue
        queue.append((row[component_at], status, " | ".join(row)))

    for component, existence, target, inv_row in inventory:
        matches = [entry for entry in queue if same_component(component, entry[0])]
        if not matches:
            findings.error(f"依赖清单组件缺少确认队列条目：{component}")
            continue
        if existence in {"no", "unknown"} and any(
            status != "blocked" for _, status, _ in matches
        ):
            findings.error(
                f"目标存在性为 {existence} 的组件必须在确认队列中为 blocked：{component}"
            )
        if target and NON_GA_PATTERN.search(target):
            ready_hits = [m for m in matches if m[1] == "ready"]
            if ready_hits:
                allow_markers = (inv_row + " " + " ".join(m[2] for m in matches)).lower()
                if "non-ga-allowed" not in allow_markers:
                    findings.error(
                        f"非 GA 目标不得进入 ready（须显式 non-ga-allowed）："
                        f"{component} → {target}"
                    )

    if statuses.get("analysis_status") == "complete":
        for component, status, _ in queue:
            if status == "ready":
                findings.error(
                    f"analysis_status=complete 时不得留下 ready 未决项：{component}"
                )
    if statuses.get("analysis_status") == "blocked":
        ready = [component for component, status, _ in queue if status == "ready"]
        if ready:
            findings.error(
                "analysis_status=blocked 时不得残留 ready："
                + "、".join(ready)
                + "（先清批级闸或改为 partial）"
            )
    if statuses.get("batch_implementation_gate") == "ready":
        blocked = [component for component, status, _ in queue if status == "blocked"]
        if blocked:
            findings.error(
                "存在 blocked 项时 batch_implementation_gate 不得为 ready："
                + "、".join(blocked)
            )
    elif statuses.get("batch_implementation_gate") == "frozen":
        if (
            queue
            and all(status in {"decided", "deferred"} for _, status, _ in queue)
            and statuses.get("analysis_status") == "complete"
        ):
            findings.warn(
                "队列已全部 decided/deferred 且无 blocked，"
                "按状态转移表 batch_implementation_gate 可为 ready（当前为 frozen）"
            )


def same_component(left: str, right: str) -> bool:
    left_tokens, right_tokens = gav_tokens(left), gav_tokens(right)
    if left_tokens and right_tokens:
        return bool(left_tokens & right_tokens)
    return clean_cell(left) == clean_cell(right)


def check_leftover_template(lines: list[str], findings: Findings) -> None:
    for line in lines:
        if line.startswith("> 填写后保存为"):
            findings.error("这是未填写的模板文件，不是决策包")
            return


def validate_report(path: Path) -> Findings:
    findings = Findings()
    lines = path.read_text(encoding="utf-8").splitlines()
    check_leftover_template(lines, findings)
    statuses = check_status_table(lines, findings)
    bounds = check_sections(lines, findings)
    inventory = check_inventory(lines, bounds, findings)
    check_queue(lines, bounds, inventory, statuses, findings)
    return findings


def check_batch_index(directory: Path, reports: list[Path], findings: Findings) -> None:
    """Require BATCH-INDEX.md to mention each batch path and the three status axes."""
    index_path = directory / BATCH_INDEX_NAME
    if not index_path.is_file():
        return
    text = index_path.read_text(encoding="utf-8")
    if not text.strip():
        findings.error(f"{BATCH_INDEX_NAME} 为空：须索引每个批次目录与状态")
        return
    for token in ("analysis_status", "decision_status", "batch_implementation_gate"):
        if token not in text:
            findings.error(f"{BATCH_INDEX_NAME} 缺少状态字段名：{token}")
    for report in reports:
        relative = report.relative_to(directory)
        if len(relative.parts) != 3:
            continue
        batch_key = f"{relative.parts[0]}/{relative.parts[1]}"
        if batch_key not in text and relative.parts[1] not in text:
            findings.error(f"{BATCH_INDEX_NAME} 未索引批次：{batch_key}")


def validate_batch_layout(directory: Path) -> tuple[Findings, list[Path]]:
    findings = Findings()
    reports = sorted(directory.rglob(REPORT_NAME))
    if not reports:
        findings.error(f"证据目录下找不到 {REPORT_NAME}")
        return findings, []

    root_report = directory / REPORT_NAME
    if len(reports) == 1:
        if reports[0] != root_report:
            findings.error(
                f"单批次时报告须写在证据目录根：实际为 {reports[0].relative_to(directory).as_posix()}"
            )
        return findings, reports

    if not (directory / BATCH_INDEX_NAME).is_file():
        findings.error(f"多批次时证据目录根必须有 {BATCH_INDEX_NAME}")
    else:
        check_batch_index(directory, reports, findings)
    if root_report.is_file():
        findings.error(f"多批次时不应同时在根目录写 {REPORT_NAME}")

    for report in reports:
        relative = report.relative_to(directory)
        parts = relative.parts
        if len(parts) != 3:
            findings.error(
                "批次报告路径不符合 <entry-kind>/<authority-layer>__<boot-line>/"
                f"{REPORT_NAME}：{relative.as_posix()}"
            )
            continue
        entry_kind, batch_dir = parts[0], parts[1]
        if entry_kind not in ENTRY_KINDS:
            findings.error(
                f"entry-kind 非法：{entry_kind}（允许：{' / '.join(sorted(ENTRY_KINDS))}）"
            )
        if "__" not in batch_dir:
            findings.error(f"批次目录名缺少 __ 分隔：{batch_dir}")
            continue
        layer, boot_line = batch_dir.split("__", 1)
        if layer not in AUTHORITY_LAYERS:
            findings.error(
                f"authority-layer 非法：{layer}（允许：{' / '.join(sorted(AUTHORITY_LAYERS))}）"
            )
        if boot_line != "no-boot" and not boot_line.startswith("boot-"):
            findings.error(f"boot-line 非法：{boot_line}（须为 boot-<线> 或 no-boot）")
    return findings, reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("report", nargs="?", help=f"path to a {REPORT_NAME}")
    parser.add_argument(
        "--evidence-dir",
        help="validate batch layout plus every report under an evidence directory",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args(argv)

    if bool(args.report) == bool(args.evidence_dir):
        parser.error("give exactly one of <report.md> or --evidence-dir")

    findings = Findings()
    checked: list[Path] = []

    if args.evidence_dir:
        directory = Path(args.evidence_dir)
        if not directory.is_dir():
            print(f"路径不存在或不是目录：{directory}", file=sys.stderr)
            return 4
        layout, reports = validate_batch_layout(directory)
        findings.extend(layout, "[layout] ")
        for report in reports:
            findings.extend(
                validate_report(report), f"[{report.relative_to(directory).as_posix()}] "
            )
            checked.append(report)
    else:
        report = Path(args.report)
        if not report.is_file():
            print(f"文件不存在：{report}", file=sys.stderr)
            return 4
        findings.extend(validate_report(report), "")
        checked.append(report)

    if args.json:
        print(
            json.dumps(
                {
                    "checked": [path.as_posix() for path in checked],
                    "errors": findings.errors,
                    "warnings": findings.warnings,
                    "result": "fail" if findings.errors else "pass",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for message in findings.errors:
            print(f"ERROR {message}")
        for message in findings.warnings:
            print(f"WARN  {message}")
        checked_names = ", ".join(path.name for path in checked) or "无"
        if findings.errors:
            print(f"\n校验失败：{len(findings.errors)} 个错误（已检查：{checked_names}）")
        else:
            print(f"校验通过（已检查：{checked_names}）")
            print("提示：结构合规不代表证据充分，仍需人工复核 owner 与上游依据。")

    return 3 if findings.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

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
DECISION_RECORDS_DIR = "decision-records"

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
    "模块",
    "当前解析版本",
    "目标版本",
    "方向",
    "目标存在性",
    "建议处置",
    "推荐替代",
    "替代存在性",
    "依赖路径",
    "有效 Owner",
    "权威层",
    "风险",
)
QUEUE_COLUMNS = ("组件", "状态", "问题", "选项")

EXISTENCE_VALUES = {"yes", "no", "unknown", "n/a"}
TREATMENT_VALUES = {
    "remove",
    "upgrade-self",
    "upgrade-owner",
    "upgrade-introducer",
    "move-self",
    "move-owner",
    "move-introducer",
    "exclude",
    "force-align",
    "replace-component",
    "replace-introducer",
    "choose-alternative",
    "no-viable-path",
}
NO_TARGET_TREATMENTS = {"remove", "exclude", "no-viable-path"}
QUEUE_STATUSES = {"ready", "pending", "blocked", "decided", "deferred"}
# Match Maven/Spring qualifiers with optional trailing digits: RC1, Alpha5, Beta2, M5.
NON_GA_PATTERN = re.compile(
    r"(?i)(?:^|[.\-])"
    r"(?:alpha|beta|rc|cr|m|milestone|snapshot|preview|pre|ea|eap|dev|nightly|candidate)"
    r"\d*(?:[.\-]|$)"
)
PENDING_MARKERS = ("待补证", "pending-baseline", "pending baseline", "补证清单")
PENDING_OPTION_EXACT = {"defer", "other"}

ENTRY_KINDS = {"exact", "open-target"}
AUTHORITY_LAYERS = {"jdk", "boot-bom", "platform-plugin", "app-library"}
BOOT_LINE_PATTERN = re.compile(r"^boot-[A-Za-z0-9][A-Za-z0-9._-]*$")
DECISION_DOMAIN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

GAV_TOKEN = re.compile(r"[A-Za-z0-9_.\-]+:[A-Za-z0-9_.\-*]+")
PROCEED_OPTION = re.compile(
    r"^proceed:([A-Za-z0-9_.\-]+):([A-Za-z0-9_.\-*]+):([A-Za-z0-9_.+\-]+)$"
)
REPLACE_OPTION = re.compile(
    r"^replace:([A-Za-z0-9_.\-]+):([A-Za-z0-9_.\-*]+)"
    r"(?::([A-Za-z0-9_.+\-]+))?$"
)
BLOCKED_OPTION_EXACT = {"remove", "exclude", "defer"}
BLOCKED_RESTATE_MARKERS = ("重述", "restate")
MOVE_TREATMENTS = {
    "upgrade-self",
    "upgrade-owner",
    "upgrade-introducer",
    "move-self",
    "move-owner",
    "move-introducer",
    "force-align",
}
REPLACE_TREATMENTS = {"replace-component", "replace-introducer"}
ALTERNATIVE_TREATMENTS = REPLACE_TREATMENTS | {"choose-alternative"}
DIRECTION_VALUES = {"upgrade", "downgrade", "same", "unknown"}
UPGRADE_TREATMENTS = {"upgrade-self", "upgrade-owner", "upgrade-introducer"}
NEUTRAL_MOVE_TREATMENTS = {"move-self", "move-owner", "move-introducer"}
SIX_LAYER_LABELS = ("代码", "配置", "数据", "接口", "测试", "部署")
DECISION_RECORD_REQUIRED_FIELDS = (
    "组件",
    "模块",
    "版本（当前解析 → 目标）",
    "目标存在性",
    "建议处置",
    "scope",
    "optional",
    "exclusions_present",
    "依赖路径",
    "有效 Owner",
    "权威层",
    "构建变体",
    "批次范围",
    "方向",
    "入口来源",
    "主 Owner 动作",
    "兼容性证据（URL）",
    "已命名验证项",
    "回滚触发条件 + 恢复目标",
    "责任人",
    "推荐确认选项",
    "确认队列状态",
    "人工答复",
)


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


@dataclass
class InventoryItem:
    component: str
    current: str
    target: str
    direction: str
    existence: str
    treatment: str
    replacement: str
    replacement_existence: str
    row_text: str


def clean_cell(cell: str) -> str:
    # Keep single '*' (family wildcards like netty-*); strip markdown bold only.
    return cell.replace("`", "").replace("**", "").strip()


def split_options(options: str) -> list[str]:
    return [
        clean_cell(option).strip()
        for option in re.split(r"\s+/\s+", options)
        if clean_cell(option).strip()
    ]


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
        heading = line.lstrip("#").strip()
        heading = re.sub(r"^\d+\.\s*", "", heading)
        for name in REQUIRED_SECTIONS:
            if heading == name and name not in bounds:
                bounds[name] = (index + 1, end)
    return bounds


def gav_tokens(cell: str) -> set[str]:
    return set(GAV_TOKEN.findall(cell))


def check_status_table(lines: list[str], findings: Findings) -> dict[str, str]:
    values: dict[str, str] = {}
    occurrences: dict[str, list[str]] = {}
    for table in read_tables(lines):
        for row in table:
            if len(row) < 2:
                continue
            key = row[0]
            if key in STATUS_ENUMS or key in FREE_TEXT_STATUS:
                occurrences.setdefault(key, []).append(row[1])

    for key, found in occurrences.items():
        if len(found) > 1:
            findings.error(
                f"状态字段重复：{key} 出现 {len(found)} 次"
                f"（取值：{' / '.join(value or '空' for value in found)}）"
            )
        values[key] = found[0]

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
) -> list[InventoryItem]:
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
    module_at = header.index("模块")
    current_at = header.index("当前解析版本")
    direction_at = header.index("方向")
    existence_at = header.index("目标存在性")
    treatment_at = header.index("建议处置")
    target_at = header.index("目标版本")
    replacement_at = header.index("推荐替代")
    replacement_existence_at = header.index("替代存在性")
    path_at = header.index("依赖路径")
    owner_at = header.index("有效 Owner")
    authority_at = header.index("权威层")
    risk_at = header.index("风险")
    results: list[InventoryItem] = []
    for row in rows:
        needed = max(
            component_at,
            module_at,
            current_at,
            direction_at,
            existence_at,
            treatment_at,
            target_at,
            replacement_at,
            replacement_existence_at,
            path_at,
            owner_at,
            authority_at,
            risk_at,
        )
        if len(row) <= needed:
            findings.error(f"依赖清单行列数不足：{' | '.join(row)}")
            continue
        component = row[component_at]
        current = row[current_at]
        direction = row[direction_at].lower()
        existence = row[existence_at].lower()
        treatment = row[treatment_at].lower()
        target = row[target_at]
        replacement = row[replacement_at]
        replacement_existence = row[replacement_existence_at].lower()
        row_text = " | ".join(row)
        if not component:
            findings.error("依赖清单存在空组件行")
            continue
        if treatment == "defer":
            findings.error(
                f"建议处置不得再用 defer（已改名为 no-viable-path）：{component}"
            )
            continue
        required_cells = {
            "模块": row[module_at],
            "当前解析版本": row[current_at],
            "依赖路径": row[path_at],
            "有效 Owner": row[owner_at],
            "权威层": row[authority_at],
            "风险": row[risk_at],
            "方向": row[direction_at],
        }
        for column, value in required_cells.items():
            if not value:
                findings.error(f"依赖清单必填单元格为空：{component} / {column}")
        authority = row[authority_at].lower()
        if direction not in DIRECTION_VALUES:
            findings.error(
                f"方向取值非法：{component} = {row[direction_at] or '空'}"
                f"（允许：{' / '.join(sorted(DIRECTION_VALUES))}）"
            )
        if direction == "downgrade" and not re.search(
            r"(?i)(高|high)", row[risk_at]
        ):
            findings.error(f"显式降级必须标为高风险/High scrutiny：{component}")
        if direction in {"downgrade", "same"} and treatment in UPGRADE_TREATMENTS:
            findings.error(
                f"{direction} 方向不得使用 upgrade-* 处置；请改用对应 move-*：{component}"
            )
        if direction == "upgrade" and treatment in NEUTRAL_MOVE_TREATMENTS:
            findings.error(f"upgrade 方向不得使用 move-* 处置：{component}")
        if authority and authority not in AUTHORITY_LAYERS:
            findings.error(
                f"权威层取值非法：{component} = {row[authority_at]}"
                f"（允许：{' / '.join(sorted(AUTHORITY_LAYERS))}）"
            )
        if existence not in EXISTENCE_VALUES:
            findings.error(
                f"目标存在性取值非法：{component} = {row[existence_at] or '空'}"
                f"（允许：{' / '.join(sorted(EXISTENCE_VALUES))}）"
            )
            continue
        if replacement_existence not in EXISTENCE_VALUES:
            findings.error(
                f"替代存在性取值非法：{component} = "
                f"{row[replacement_existence_at] or '空'}"
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
                f"目标存在性 n/a 仅允许无目标处置（remove/exclude/no-viable-path）："
                f"{component} 当前为 {treatment}"
            )
        if treatment in MOVE_TREATMENTS:
            if not target or target in {"-", "—"}:
                findings.error(f"版本移动处置必须填写目标版本：{component} / {treatment}")
            if existence != "yes":
                findings.error(
                    f"版本移动处置的目标存在性必须为 yes："
                    f"{component} / {treatment} / {existence}"
                )
        if treatment in ALTERNATIVE_TREATMENTS:
            if not replacement or replacement in {"-", "—"}:
                findings.error(f"替代选择处置必须填写推荐替代 GAV:version：{component}")
            elif parse_ga_version(replacement)[1] is None:
                findings.error(f"推荐替代缺少合法 GAV:version：{component} = {replacement}")
            if replacement_existence != "yes":
                findings.error(
                    f"替代选择处置的推荐替代存在性必须为 yes："
                    f"{component} = {replacement_existence}"
                )
            if treatment == "choose-alternative" and existence not in {"no", "unknown"}:
                findings.error(
                    f"choose-alternative 仅用于请求目标不存在/未知：{component} = {existence}"
                )
        elif replacement_existence != "n/a":
            findings.error(
                f"非替换处置的替代存在性必须为 n/a："
                f"{component} / {treatment} / {replacement_existence}"
            )
        if treatment not in ALTERNATIVE_TREATMENTS and replacement not in {"", "-", "—"}:
            findings.error(f"非替换处置不得填写推荐替代：{component} = {replacement}")
        if (
            existence in {"no", "unknown"}
            and treatment not in ALTERNATIVE_TREATMENTS
            and treatment != "no-viable-path"
        ):
            findings.warn(
                f"目标存在性为 {existence} 时建议处置宜为 no-viable-path"
                f"（当前为 {treatment}）：{component}"
            )
        if target and NON_GA_PATTERN.search(target) and existence == "yes":
            findings.warn(
                f"目标版本疑似非 GA，却标记目标存在性=yes：{component} → {target}"
                "（须 target_channel=non-ga；未显式 non-ga-allowed 时队列不得 ready）"
            )
        results.append(
            InventoryItem(
                component=component,
                current=current,
                target=target,
                direction=direction,
                existence=existence,
                treatment=treatment,
                replacement=replacement,
                replacement_existence=replacement_existence,
                row_text=row_text,
            )
        )
    return results


def option_is_forbidden_on_blocked(option: str) -> bool:
    lowered = option.lower()
    if lowered in BLOCKED_OPTION_EXACT:
        return True
    if lowered.startswith("proceed:") or lowered.startswith("replace:"):
        return True
    return False


def option_is_forbidden_on_pending(option: str) -> bool:
    """pending = tooling/baseline catch-up; no version-move confirm tokens yet."""
    lowered = option.lower()
    if lowered in {"remove", "exclude"}:
        return True
    if lowered.startswith("proceed:") or lowered.startswith("replace:"):
        return True
    return False


def blocked_options_allow_restate(options: str, option_tokens: list[str]) -> bool:
    joined = options.lower()
    if any(marker.lower() in joined for marker in BLOCKED_RESTATE_MARKERS):
        return True
    if any(token.lower() == "other" for token in option_tokens):
        return True
    return False


def pending_options_allow_catchup(option_tokens: list[str]) -> bool:
    return any(token.lower() in PENDING_OPTION_EXACT for token in option_tokens)


def pending_question_has_marker(question: str, options: str, row_text: str) -> bool:
    joined = f"{question} {options} {row_text}".lower()
    return any(marker.lower() in joined for marker in PENDING_MARKERS)


def primary_gav(component: str) -> str | None:
    tokens = sorted(gav_tokens(component))
    return tokens[0] if tokens else None


def decision_record_slug(component: str) -> str:
    gav = primary_gav(component) or clean_cell(component)
    group, _, artifact = gav.partition(":")
    artifact = artifact.replace("*", "ALL")
    safe = re.sub(r"[^A-Za-z0-9_.\-]+", "-", f"{group}__{artifact or 'unknown'}")
    return safe.strip("-") or "unknown"


def parse_ga_version(cell: str) -> tuple[str | None, str | None]:
    tokens = gav_tokens(cell)
    if not tokens:
        version_match = re.search(r"([A-Za-z0-9_.+\-]+)\s*$", clean_cell(cell))
        return None, version_match.group(1) if version_match else None
    token = sorted(tokens)[0]
    group, _, rest = token.partition(":")
    artifact, _, version = rest.partition(":")
    if version:
        return f"{group}:{artifact}", version
    # replacement cell may be g:a:v already captured as one token without third colon
    # when version was separate — handle g:a only
    parts = clean_cell(cell).split(":")
    if len(parts) >= 3:
        return f"{parts[0]}:{parts[1]}", parts[2]
    return f"{group}:{artifact}", None


def wildcard_artifact_match(pattern: str, concrete: str) -> bool:
    if pattern == concrete:
        return True
    if "*" not in pattern:
        return False
    # Treat trailing -* / * as family prefix match (netty-* ↔ netty-handler).
    if pattern.endswith("-*"):
        prefix = pattern[:-2]
        return concrete == prefix or concrete.startswith(prefix + "-")
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        return concrete.startswith(prefix)
    return False


def same_component(left: str, right: str) -> bool:
    left_tokens, right_tokens = gav_tokens(left), gav_tokens(right)
    if left_tokens and right_tokens:
        if left_tokens & right_tokens:
            return True
        for left_token in left_tokens:
            left_group, _, left_artifact = left_token.partition(":")
            for right_token in right_tokens:
                right_group, _, right_artifact = right_token.partition(":")
                if left_group != right_group:
                    continue
                if wildcard_artifact_match(left_artifact, right_artifact) or wildcard_artifact_match(
                    right_artifact, left_artifact
                ):
                    return True
        return False
    return clean_cell(left) == clean_cell(right)


def check_option_target_consistency(
    item: InventoryItem,
    options: list[str],
    findings: Findings,
) -> None:
    if item.treatment in MOVE_TREATMENTS:
        expected = item.target
        for option in options:
            match = PROCEED_OPTION.fullmatch(option)
            if not match:
                continue
            version = match.group(3)
            if expected and expected not in {"-", "—"} and version != expected:
                findings.error(
                    f"proceed 版本与清单目标不一致：{item.component} "
                    f"清单={expected} 选项={version}"
                )
    if item.treatment in ALTERNATIVE_TREATMENTS:
        expected_ga, expected_version = parse_ga_version(item.replacement)
        for option in options:
            proceed = PROCEED_OPTION.fullmatch(option)
            if proceed and item.treatment == "choose-alternative":
                option_ga = f"{proceed.group(1)}:{proceed.group(2)}"
                if expected_ga and not same_component(expected_ga, option_ga):
                    findings.error(
                        f"proceed 坐标与清单推荐替代不一致：{item.component} "
                        f"清单={expected_ga} 选项={option_ga}"
                    )
                if expected_version and proceed.group(3) != expected_version:
                    findings.error(
                        f"proceed 版本与清单推荐替代不一致：{item.component} "
                        f"清单={expected_version} 选项={proceed.group(3)}"
                    )
            match = REPLACE_OPTION.fullmatch(option)
            if not match:
                continue
            option_ga = f"{match.group(1)}:{match.group(2)}"
            option_version = match.group(3)
            if expected_ga and not same_component(expected_ga, option_ga):
                findings.error(
                    f"replace 坐标与清单推荐替代不一致：{item.component} "
                    f"清单={expected_ga} 选项={option_ga}"
                )
            if (
                expected_version
                and option_version
                and expected_version != option_version
            ):
                findings.error(
                    f"replace 版本与清单推荐替代不一致：{item.component} "
                    f"清单={expected_version} 选项={option_version}"
                )


def check_queue(
    lines: list[str],
    bounds: dict[str, tuple[int, int]],
    inventory: list[InventoryItem],
    statuses: dict[str, str],
    findings: Findings,
) -> list[tuple[str, str]]:
    """Validate confirmation queue; return [(component, status), ...] for cross-checks."""
    section = "确认队列"
    if section not in bounds:
        return []
    table = find_table(lines, bounds[section], QUEUE_COLUMNS)
    if table is None:
        findings.error(f"「{section}」缺少契约要求的表头列：{'、'.join(QUEUE_COLUMNS)}")
        return []
    header, rows = table[0], table[1:]
    if not rows:
        if statuses.get("decision_status") != "not_needed":
            findings.error(
                f"「{section}」表为空，但 decision_status 不是 not_needed：确认队列必须出现过"
            )
        return []

    component_at = header.index("组件")
    status_at = header.index("状态")
    question_at = header.index("问题") if "问题" in header else None
    options_at = header.index("选项")
    queue: list[tuple[str, str, str, str, str]] = []
    for row in rows:
        needed = max(component_at, status_at, options_at, question_at or 0)
        if len(row) <= needed:
            findings.error(f"确认队列行列数不足：{' | '.join(row)}")
            continue
        component = row[component_at]
        status = row[status_at].lower()
        question = row[question_at] if question_at is not None else ""
        options = row[options_at]
        if not component:
            findings.error("确认队列存在空组件行")
            continue
        if status not in QUEUE_STATUSES:
            findings.error(
                f"确认队列状态非法：{row[component_at]} = {row[status_at] or '空'}"
                f"（允许：{' / '.join(sorted(QUEUE_STATUSES))}）"
            )
            continue
        if question_at is not None and not question:
            findings.error(f"确认队列问题为空：{component}")
        if status in {"ready", "pending", "blocked"} and not options:
            findings.error(f"确认队列选项为空：{component} / {status}")
        option_tokens = split_options(options)
        if status == "blocked":
            if any(option_is_forbidden_on_blocked(token) for token in option_tokens):
                findings.error(
                    f"blocked 行不得提供 proceed/remove/exclude/replace/defer：{component}"
                )
            if not blocked_options_allow_restate(options, option_tokens):
                findings.error(
                    f"blocked 行只能提供重述目标/restate target 或 other：{component}"
                )
        if status == "pending":
            if any(option_is_forbidden_on_pending(token) for token in option_tokens):
                findings.error(
                    f"pending 行不得提供 proceed/remove/exclude/replace：{component}"
                )
            if not pending_options_allow_catchup(option_tokens):
                findings.error(
                    f"pending 行选项须含 defer 或 other（补证承诺/暂缓）：{component}"
                )
            if not pending_question_has_marker(question, options, " | ".join(row)):
                findings.error(
                    f"pending 行问题须标注待补证/pending-baseline/补证清单：{component}"
                )
        queue.append((component, status, question, options, " | ".join(row)))

    for item in inventory:
        matches = [entry for entry in queue if same_component(item.component, entry[0])]
        if not matches:
            findings.error(f"依赖清单组件缺少确认队列条目：{item.component}")
            continue
        effective_existence = (
            item.replacement_existence
            if item.treatment in ALTERNATIVE_TREATMENTS
            else item.existence
        )
        if effective_existence in {"no", "unknown"} and any(
            status != "blocked" for _, status, _, _, _ in matches
        ):
            findings.error(
                f"目标存在性为 {effective_existence} 的组件必须在确认队列中为 blocked："
                f"{item.component}"
            )
        if item.treatment == "no-viable-path" and any(
            status != "blocked" for _, status, _, _, _ in matches
        ):
            findings.error(
                f"no-viable-path 必须在确认队列中为 blocked（不得 ready/pending/defer）："
                f"{item.component}"
            )
        target_for_channel = (
            item.replacement if item.treatment in ALTERNATIVE_TREATMENTS else item.target
        )
        if target_for_channel and NON_GA_PATTERN.search(target_for_channel):
            ready_hits = [match for match in matches if match[1] == "ready"]
            if ready_hits:
                allow_markers = (
                    item.row_text + " " + " ".join(match[4] for match in matches)
                ).lower()
                if "non-ga-allowed" not in allow_markers:
                    findings.error(
                        f"非 GA 目标不得进入 ready（须显式 non-ga-allowed）："
                        f"{item.component} → {target_for_channel}"
                    )
        if item.direction == "downgrade":
            downgrade_notice = " ".join(match[4] for match in matches).lower()
            if "降级" not in downgrade_notice and "downgrade" not in downgrade_notice:
                findings.error(
                    f"显式降级必须在确认问题中醒目标注“降级/downgrade”：{item.component}"
                )
        for component, status, _, options, _ in matches:
            if status != "ready":
                continue
            cleaned_options = split_options(options)
            if item.treatment == "remove" and "remove" not in cleaned_options:
                findings.error(f"remove 处置的 ready 行缺少 remove 选项：{component}")
            elif item.treatment == "exclude" and "exclude" not in cleaned_options:
                findings.error(f"exclude 处置的 ready 行缺少 exclude 选项：{component}")
            elif item.treatment in MOVE_TREATMENTS:
                if not any(PROCEED_OPTION.fullmatch(option) for option in cleaned_options):
                    findings.error(
                        f"版本移动处置的 ready 行缺少合法 proceed:g:a:v：{component}"
                    )
                check_option_target_consistency(item, cleaned_options, findings)
            elif item.treatment in REPLACE_TREATMENTS:
                if not any(REPLACE_OPTION.fullmatch(option) for option in cleaned_options):
                    findings.error(
                        f"替换处置的 ready 行缺少合法 replace:g:a[:v]：{component}"
                    )
                check_option_target_consistency(item, cleaned_options, findings)
            elif item.treatment == "choose-alternative":
                expected_ga, _ = parse_ga_version(item.replacement)
                original_ga = primary_gav(item.component)
                same_gav = bool(
                    expected_ga and original_ga and same_component(expected_ga, original_ga)
                )
                expected_kind = PROCEED_OPTION if same_gav else REPLACE_OPTION
                expected_label = "proceed:g:a:v" if same_gav else "replace:g:a:v"
                if not any(expected_kind.fullmatch(option) for option in cleaned_options):
                    findings.error(
                        f"choose-alternative 的 ready 行缺少合法 {expected_label}：{component}"
                    )
                check_option_target_consistency(item, cleaned_options, findings)

    ready = [component for component, status, _, _, _ in queue if status == "ready"]
    pending = [component for component, status, _, _, _ in queue if status == "pending"]
    blocked = [component for component, status, _, _, _ in queue if status == "blocked"]
    askable = ready + pending
    cleared = [
        component
        for component, status, _, _, _ in queue
        if status in {"decided", "deferred"}
    ]
    decision_status = statuses.get("decision_status")
    analysis_status = statuses.get("analysis_status")
    if askable and decision_status != "needs_choice":
        findings.error(
            f"确认队列仍有 ready/pending 时 decision_status 必须为 needs_choice："
            + "、".join(askable)
        )
    if decision_status == "needs_choice" and not askable:
        findings.error(
            "decision_status=needs_choice 但确认队列没有 ready/pending 项"
        )
    if decision_status == "decided" and askable:
        findings.error("decision_status=decided 时不得残留 ready/pending")
    if decision_status == "not_needed" and (askable or cleared):
        findings.error(
            "decision_status=not_needed 与 ready/pending/decided/deferred 队列项冲突"
        )
    if askable and analysis_status != "partial":
        findings.error(
            "确认队列存在 ready/pending 时 analysis_status 必须为 partial"
        )
    if statuses.get("analysis_status") == "complete":
        for component in askable:
            findings.error(
                f"analysis_status=complete 时不得留下 ready/pending 未决项：{component}"
            )
    if statuses.get("analysis_status") == "blocked":
        if askable:
            findings.error(
                "analysis_status=blocked 时不得残留 ready/pending："
                + "、".join(askable)
                + "（先清批级闸或改为 partial）"
            )
    if statuses.get("batch_implementation_gate") == "ready":
        if blocked or askable:
            findings.error(
                "存在 blocked/ready/pending 项时 batch_implementation_gate 不得为 ready："
                + "、".join(blocked + askable)
            )
        if analysis_status != "complete":
            findings.error("batch_implementation_gate=ready 时 analysis_status 必须为 complete")
    elif statuses.get("batch_implementation_gate") == "frozen":
        if (
            queue
            and all(
                status in {"decided", "deferred"}
                for _, status, _, _, _ in queue
            )
            and statuses.get("analysis_status") == "complete"
        ):
            findings.error(
                "队列已全部 decided/deferred 且无 blocked/pending，"
                "analysis_status=complete 时 batch_implementation_gate 必须为 ready"
            )
    return [(component, status) for component, status, _, _, _ in queue]


def check_decision_records(
    report_path: Path,
    inventory: list[InventoryItem],
    analysis_status: str | None,
    findings: Findings,
    queue_rows: list[tuple[str, str]] | None = None,
) -> None:
    if not inventory:
        return
    records_dir = report_path.parent / DECISION_RECORDS_DIR
    if not records_dir.is_dir():
        message = (
            f"缺少决策记录目录：{DECISION_RECORDS_DIR}/"
            f"（须为每个清单组件提供 {DECISION_RECORDS_DIR}/<group>__<artifact>.md）"
        )
        if analysis_status == "complete":
            findings.error(message)
        else:
            findings.warn(message)
        return
    files = list(records_dir.glob("*.md"))
    if not files:
        message = f"决策记录目录为空：{DECISION_RECORDS_DIR}/"
        if analysis_status == "complete":
            findings.error(message)
        else:
            findings.warn(message)
        return
    file_text = {path: path.read_text(encoding="utf-8") for path in files}
    for item in inventory:
        slug = decision_record_slug(item.component)
        matched_path: Path | None = None
        matched_text = ""
        for path, text in file_text.items():
            if path.stem == slug or same_component(item.component, path.stem.replace("__", ":")):
                matched_path, matched_text = path, text
                break
            if same_component(item.component, text) or slug in path.stem:
                matched_path, matched_text = path, text
                break
            if primary_gav(item.component) and primary_gav(item.component) in text:
                matched_path, matched_text = path, text
                break
        if matched_path is None:
            findings.error(
                f"依赖清单组件缺少决策记录文件：{item.component} "
                f"（期望 {DECISION_RECORDS_DIR}/{slug}.md 或正文含该 GAV）"
            )
            continue
        report_statuses = [
            status
            for component, status in (queue_rows or [])
            if same_component(item.component, component)
        ]
        report_is_pending = "pending" in report_statuses
        # Full field checks remain complete-only; pending catch-up fields also apply on partial.
        if analysis_status != "complete" and not report_is_pending:
            continue
        tables = read_tables(matched_text.splitlines())
        field_table = next(
            (
                table
                for table in tables
                if table and len(table[0]) >= 2
                and table[0][0] == "字段"
                and table[0][1] == "内容"
            ),
            None,
        )
        if field_table is None or len(field_table) == 1:
            findings.error(f"决策记录为空或缺少“字段/内容”表：{matched_path.name}")
            continue
        fields = {
            row[0]: row[1]
            for row in field_table[1:]
            if len(row) >= 2 and row[0]
        }
        queue_status = fields.get("确认队列状态", "").lower()
        if report_is_pending or queue_status == "pending":
            baseline = fields.get("baseline_evidence_status", "").lower()
            if baseline not in {"pending-tooling", "pending-tree", "mismatch"}:
                findings.error(
                    f"pending 决策记录须填写 baseline_evidence_status="
                    f"pending-tooling|pending-tree|mismatch：{matched_path.name}"
                )
            next_steps = fields.get("下一步补证", "")
            if not next_steps or next_steps in {"-", "—", "TBD", "待填"}:
                findings.error(
                    f"pending 决策记录须填写下一步补证：{matched_path.name}"
                )
            if analysis_status != "complete":
                if queue_status and queue_status != "pending":
                    findings.error(
                        f"决策记录确认队列状态与报告确认队列不一致："
                        f"{matched_path.name} 记录={queue_status} 报告=pending"
                    )
                continue
        for field_name in DECISION_RECORD_REQUIRED_FIELDS:
            value = fields.get(field_name, "")
            if field_name == "人工答复" and fields.get("确认队列状态", "").lower() in {
                "ready",
                "pending",
                "blocked",
            }:
                continue
            if not value or value in {"-", "—", "TBD", "待填"}:
                findings.error(
                    f"决策记录必填字段缺失/未填写：{matched_path.name} / {field_name}"
                )
        if fields.get("组件") and not same_component(item.component, fields["组件"]):
            findings.error(f"决策记录组件与清单不一致：{matched_path.name}")
        if fields.get("目标存在性", "").lower() != item.existence:
            findings.error(f"决策记录目标存在性与清单不一致：{matched_path.name}")
        if fields.get("建议处置", "").lower() != item.treatment:
            findings.error(f"决策记录建议处置与清单不一致：{matched_path.name}")
        if fields.get("方向", "").lower() != item.direction:
            findings.error(f"决策记录方向与清单不一致：{matched_path.name}")
        if queue_status not in QUEUE_STATUSES:
            findings.error(f"决策记录确认队列状态非法：{matched_path.name}")
        if report_statuses and queue_status in QUEUE_STATUSES:
            if queue_status not in report_statuses:
                findings.error(
                    f"决策记录确认队列状态与报告确认队列不一致："
                    f"{matched_path.name} 记录={queue_status} "
                    f"报告={'/'.join(report_statuses)}"
                )
        answer = fields.get("人工答复", "")
        if queue_status in {"decided", "deferred"} and (
            not answer or answer in {"-", "—", "TBD", "待填"}
        ):
            findings.error(f"已决策的决策记录必须填写人工答复：{matched_path.name}")
        if item.treatment in ALTERNATIVE_TREATMENTS:
            for field_name in ("请求目标（GAV / 版本 / 存在性）", "推荐替代目标（GAV / 版本 / 存在性）", "替代候选"):
                if fields.get(field_name, "") in {"", "-", "—", "TBD", "待填"}:
                    findings.error(
                        f"替代选择决策记录缺少字段：{matched_path.name} / {field_name}"
                    )


def check_six_layer_coverage(
    lines: list[str],
    bounds: dict[str, tuple[int, int]],
    analysis_status: str | None,
    findings: Findings,
) -> None:
    section = "六层影响分析"
    if section not in bounds:
        return
    start, end = bounds[section]
    body = "\n".join(lines[start:end])
    missing = [label for label in SIX_LAYER_LABELS if label not in body]
    if missing:
        message = "六层影响分析未点名全部层级（可写「不适用」）：" + "、".join(missing)
        if analysis_status == "complete":
            findings.error(message)
        else:
            findings.warn(message)


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
    queue_rows = check_queue(lines, bounds, inventory, statuses, findings)
    check_six_layer_coverage(lines, bounds, statuses.get("analysis_status"), findings)
    check_decision_records(
        path,
        inventory,
        statuses.get("analysis_status"),
        findings,
        queue_rows=queue_rows,
    )
    return findings


def parse_batch_dir(
    batch_dir: str,
) -> tuple[str, str, str, str, str | None] | None:
    parts = batch_dir.split("__")
    if len(parts) not in {4, 5}:
        return None
    layer, boot_line, variant_part, scope_part = parts[:4]
    if not variant_part.startswith("variant-") or not scope_part.startswith("scope-"):
        return None
    build_variant = variant_part.removeprefix("variant-")
    batch_scope = scope_part.removeprefix("scope-")
    decision_domain = None
    if len(parts) == 5:
        if not parts[4].startswith("domain-"):
            return None
        decision_domain = parts[4].removeprefix("domain-")
    if not build_variant or not batch_scope:
        return None
    return layer, boot_line, build_variant, batch_scope, decision_domain


def find_header_index(header: list[str], aliases: tuple[str, ...]) -> int | None:
    for alias in aliases:
        if alias in header:
            return header.index(alias)
    return None


def check_batch_index(directory: Path, reports: list[Path], findings: Findings) -> None:
    """Require a structured BATCH-INDEX.md row for every batch."""
    index_path = directory / BATCH_INDEX_NAME
    if not index_path.is_file():
        return
    text = index_path.read_text(encoding="utf-8")
    if not text.strip():
        findings.error(f"{BATCH_INDEX_NAME} 为空：须索引每个批次目录与状态")
        return
    tables = read_tables(text.splitlines())
    required_aliases = {
        "path": ("目录", "批次目录"),
        "layer": ("权威层",),
        "boot": ("Boot 线", "Boot线"),
        "variant": ("构建变体", "build_variant"),
        "scope": ("批次范围", "batch_scope"),
        "domain": ("决策域", "decision_domain"),
        "members": ("成员", "成员 GAV"),
        "analysis_status": ("analysis_status",),
        "decision_status": ("decision_status",),
        "batch_implementation_gate": ("batch_implementation_gate",),
    }
    selected: tuple[list[str], list[list[str]], dict[str, int]] | None = None
    for table in tables:
        header, rows = table[0], table[1:]
        indexes: dict[str, int] = {}
        for key, aliases in required_aliases.items():
            index = find_header_index(header, aliases)
            if index is None:
                break
            indexes[key] = index
        if len(indexes) == len(required_aliases):
            selected = header, rows, indexes
            break
    if selected is None:
        findings.error(
            f"{BATCH_INDEX_NAME} 缺少结构化索引表："
            "目录/权威层/Boot 线/构建变体/批次范围/决策域/成员及 analysis_status/decision_status/"
            "batch_implementation_gate 均为必填"
        )
        for report in reports:
            relative = report.relative_to(directory)
            if len(relative.parts) == 3:
                findings.error(
                    f"{BATCH_INDEX_NAME} 未索引批次："
                    f"{relative.parts[0]}/{relative.parts[1]}"
                )
        return
    header, rows, indexes = selected
    row_by_path: dict[str, list[str]] = {}
    for row in rows:
        needed = max(indexes.values())
        if len(row) <= needed:
            findings.error(f"{BATCH_INDEX_NAME} 行列数不足：{' | '.join(row)}")
            continue
        path_value = row[indexes["path"]].strip().rstrip("/")
        if not path_value:
            findings.error(f"{BATCH_INDEX_NAME} 存在空目录行")
            continue
        if path_value in row_by_path:
            findings.error(f"{BATCH_INDEX_NAME} 批次目录重复：{path_value}")
        row_by_path[path_value] = row
        for key in ("layer", "boot", "variant", "scope", "members"):
            if not row[indexes[key]].strip():
                findings.error(f"{BATCH_INDEX_NAME} 必填值为空：{path_value} / {key}")
        for key in ("analysis_status", "decision_status", "batch_implementation_gate"):
            value = row[indexes[key]].strip()
            if value not in STATUS_ENUMS[key]:
                findings.error(
                    f"{BATCH_INDEX_NAME} 状态值非法：{path_value} / {key} = {value or '空'}"
                )
    for report in reports:
        relative = report.relative_to(directory)
        if len(relative.parts) != 3:
            continue
        batch_key = f"{relative.parts[0]}/{relative.parts[1]}"
        row = row_by_path.get(batch_key)
        if row is None:
            findings.error(f"{BATCH_INDEX_NAME} 未索引批次：{batch_key}")
            continue
        parsed = parse_batch_dir(relative.parts[1])
        if parsed is None:
            continue
        layer, boot_line, build_variant, batch_scope, decision_domain = parsed
        if row[indexes["layer"]].strip() != layer:
            findings.error(f"{BATCH_INDEX_NAME} 权威层与目录不一致：{batch_key}")
        if row[indexes["boot"]].strip() != boot_line:
            findings.error(f"{BATCH_INDEX_NAME} Boot 线与目录不一致：{batch_key}")
        if row[indexes["variant"]].strip() != build_variant:
            findings.error(f"{BATCH_INDEX_NAME} 构建变体与目录不一致：{batch_key}")
        if row[indexes["scope"]].strip() != batch_scope:
            findings.error(f"{BATCH_INDEX_NAME} 批次范围与目录不一致：{batch_key}")
        expected_domain = decision_domain or "—"
        if row[indexes["domain"]].strip() != expected_domain:
            findings.error(f"{BATCH_INDEX_NAME} 决策域与目录不一致：{batch_key}")


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
                "批次报告路径不符合 <entry-kind>/<authority-layer>__<boot-line>"
                "__variant-<build-variant>__scope-<batch-scope>/"
                f"{REPORT_NAME}：{relative.as_posix()}"
            )
            continue
        entry_kind, batch_dir = parts[0], parts[1]
        if entry_kind not in ENTRY_KINDS:
            findings.error(
                f"entry-kind 非法：{entry_kind}（允许：{' / '.join(sorted(ENTRY_KINDS))}）"
            )
        parsed = parse_batch_dir(batch_dir)
        if parsed is None:
            findings.error(
                f"批次目录名须为 <authority-layer>__<boot-line>"
                f"__variant-<build-variant>__scope-<batch-scope>"
                f"[__domain-<decision-domain>]：{batch_dir}"
            )
            continue
        layer, boot_line, build_variant, batch_scope, decision_domain = parsed
        if layer not in AUTHORITY_LAYERS:
            findings.error(
                f"authority-layer 非法：{layer}（允许：{' / '.join(sorted(AUTHORITY_LAYERS))}）"
            )
        if boot_line != "no-boot" and not BOOT_LINE_PATTERN.fullmatch(boot_line):
            findings.error(f"boot-line 非法：{boot_line}（须为 boot-<线> 或 no-boot）")
        for label, value in (("build-variant", build_variant), ("batch-scope", batch_scope)):
            if not DECISION_DOMAIN_PATTERN.fullmatch(value):
                findings.error(f"{label} 非法：{value}（须为小写字母/数字/连字符 slug）")
        if decision_domain is not None and not DECISION_DOMAIN_PATTERN.fullmatch(
            decision_domain
        ):
            findings.error(
                f"decision-domain 非法：{decision_domain}"
                "（须为小写字母/数字/连字符 slug）"
            )
    return findings, reports


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    configure_utf8_console()
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

#!/usr/bin/env python3
"""Validate a Vue2→Vue3 impact-analysis packet.

This validator checks the visible Markdown structure and cross-file decision
contract. It never proves that evidence is true or sufficient, and it never
modifies the analyzed project.

Exit codes: 0 pass, 2 usage error, 3 validation error, 4 path not found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPORT_NAME = "vue2-to-vue3-upgrade-report.md"
BATCH_INDEX_NAME = "BATCH-INDEX.md"
DECISION_RECORDS_DIR = "decision-records"

STATUS_ENUMS = {
    "analysis_status": {"partial", "blocked", "complete"},
    "decision_status": {"needs_choice", "not_needed", "decided"},
    "batch_implementation_gate": {"frozen", "ready"},
    "implementation_readiness": {"not_assessed"},
    "behavior_parity_required": {"yes", "no"},
    "network_mode": {"online", "offline", "partial"},
}
OPTIONAL_STATUS_ENUMS = {
    "schema": {"vue3-upgrade-report/v1"},
    "producer": {"vue2-to-vue3-upgrade-impact-analysis"},
    "visual_acceptance_required": {"yes", "no"},
}
OPTIONAL_STATUS_TEXT = {"summary_path"}
STATUS_HEADERS = ("字段", "取值")
INVENTORY_HEADERS = ("包名", "当前版本", "Vue3 就绪度", "建议", "证据")
SUBSYSTEM_HEADERS = (
    "子系统",
    "scope_status",
    "风险",
    "就绪度",
    "required_for_path",
    "命名配方",
    "说明",
)
QUEUE_HEADERS = ("单元", "类型", "状态", "问题", "选项")
RECORD_HEADERS = ("字段", "内容")
YES_NO = {"yes", "no"}
AXIS_MARKERS = (
    ("runtime_axis:", {"compat", "direct-vue3"}),
    ("build_axis:", {"vite", "cli5-webpack5", "existing-vite"}),
    ("topology_axis:", {"single-cutover", "coexist"}),
)
LOCKFILE_STATUSES = {"present", "absent", "unparsed"}
PATH_IDS = {
    "compat-big-bang",
    "direct-vue3",
    "microfrontend-coexist",
    "deferred-inventory-only",
}
# Preset constraints from migration-path-ladder.md (build_axis may vary).
PATH_AXIS_CONSTRAINTS: dict[str, dict[str, str]] = {
    "compat-big-bang": {
        "runtime_axis": "compat",
        "topology_axis": "single-cutover",
    },
    "direct-vue3": {
        "runtime_axis": "direct-vue3",
        "topology_axis": "single-cutover",
    },
    "microfrontend-coexist": {
        "topology_axis": "coexist",
    },
}
DEFAULT_SUBSYSTEMS = (
    "core-vue",
    "router",
    "build",
    "store",
    "ui",
    "test",
    "lint-ide",
    "i18n-plugins",
    "composition-existing",
    "blockers",
)
RECOMMENDED_PATH_RE = re.compile(
    r"(?im)推荐路径\s*id\s*[:：]\s*`?([A-Za-z0-9_-]+)`?"
)
EVIDENCE_AS_OF_RE = re.compile(
    r"(?im)^\s*[-*]?\s*`?evidence_as_of`?\s*[:：]\s*`?(\d{4}-\d{2}-\d{2})`?"
)
HTTP_URL_RE = re.compile(r"https?://\S+")
SHALLOW_CHECKLIST_ANSWERS = {
    "已声明",
    "已检查",
    "已核对",
    "ok",
    "yes",
    "y",
    "done",
    "通过",
}

REQUIRED_SECTIONS = (
    "基线与假设",
    "仓画像与依赖就绪度",
    "推荐迁移路径",
    "子系统影响清单",
    "分层影响分析",
    "风险分级",
    "确认队列",
    "验证矩阵",
    "回滚与责任人",
    "未决问题与证据缺口",
)
REQUIRED_RECORD_FIELDS = (
    "单元键",
    "类型",
    "当前结论",
    "风险",
    "命名配方",
    "兼容性证据（URL）",
    "已命名验证项",
    "回滚触发条件 + 恢复目标",
    "责任人",
    "推荐确认选项",
    "确认队列状态",
    "人工答复",
)

SCOPE_STATUSES = {"in_scope", "not_applicable"}
RISKS = {"blocker", "high", "medium", "low", "n/a"}
READINESS = {"ready", "needs-major", "replace", "unknown", "unused"}
QUEUE_STATUSES = {"ready", "pending", "blocked", "decided", "deferred"}
UNIT_TYPES = {"path", "subsystem"}
HIGH_BLOCKER_RISKS = {"high", "blocker"}
COMPOSITION_MARKER = "Composition API 全仓重写：另立项，本次不评估工作量"
MANUAL_GAP_CHECKLIST_MARKER = "人工补搜检查"
MANUAL_GAP_ITEMS = (
    ("legacy slot syntax", ("slot-scope",)),
    ("global Vue.filter", ("Vue.filter",)),
    ("non-vue-prefixed Vue plugin", ("非 `vue-*`", "非 vue-*")),
    ("legacy global prototype mount", ("Vue.prototype",)),
    ("global mount migration target", ("globalProperties", "provide/inject")),
    ("lockfile reproducibility", ("lockfile",)),
)
CHECKLIST_PLACEHOLDERS = {"", "-", "—", "todo", "待填", "待填写"}
UNIT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
FENCE = re.compile(r"(?ms)^[ \t]*(```|~~~).*?^[ \t]*\1[ \t]*$")
HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")
VISUAL_PACKAGE_TRIGGERS = (
    "element-ui",
    "element-plus",
    "tailwindcss",
    "vxe-table",
    "wangeditor",
    "vue3-tree-org",
    "butterfly-dag",
)
VISUAL_RISK_MARKERS = (
    "triggers:",
    "legacy_selectors:",
    "css_entry_order:",
    "theme_and_teleport:",
    "tailwind_reset:",
    "primary_sample:",
    "secondary_sample:",
    "baseline_status:",
    "required_visual_states:",
    "recommended_next_action:",
)


@dataclass
class Finding:
    level: str
    message: str


@dataclass
class ReportResult:
    path: Path
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [item for item in self.findings if item.level == "ERROR"]

    def error(self, message: str) -> None:
        self.findings.append(Finding("ERROR", message))

    def warn(self, message: str) -> None:
        self.findings.append(Finding("WARN", message))


def visible_markdown(text: str) -> str:
    """Remove content that cannot satisfy the visible report contract."""
    return HTML_COMMENT.sub("", FENCE.sub("", text))


def clean_cell(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value


def parse_table(block: str, expected_headers: tuple[str, ...]) -> tuple[list[list[str]], list[str]]:
    """Parse the first Markdown table and require its exact header contract."""
    lines = block.splitlines()
    errors: list[str] = []
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        headers = tuple(clean_cell(cell) for cell in line.strip().strip("|").split("|"))
        if index + 1 >= len(lines) or not lines[index + 1].strip().startswith("|"):
            continue
        separator = [cell.strip() for cell in lines[index + 1].strip().strip("|").split("|")]
        if not separator or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
            continue
        if headers != expected_headers:
            errors.append(
                f"table headers {headers!r} do not match required {expected_headers!r}"
            )
            return [], errors
        rows: list[list[str]] = []
        for row_line in lines[index + 2 :]:
            if not row_line.strip().startswith("|"):
                break
            cells = [clean_cell(cell) for cell in row_line.strip().strip("|").split("|")]
            if len(cells) != len(expected_headers):
                errors.append(
                    f"table row has {len(cells)} cells; expected {len(expected_headers)}: {row_line.strip()}"
                )
                continue
            rows.append(cells)
        return rows, errors
    return [], [f"missing table with headers {expected_headers!r}"]


def split_sections(text: str) -> tuple[dict[str, str], list[str]]:
    """Require exactly the ten numbered H2 sections in contract order."""
    matches = list(re.finditer(r"(?m)^##[ \t]+(\d+)\.[ \t]+([^\r\n]+?)[ \t]*$", text))
    errors: list[str] = []
    observed = [(int(item.group(1)), item.group(2).strip()) for item in matches]
    expected = [(index, title) for index, title in enumerate(REQUIRED_SECTIONS, 1)]
    if observed != expected:
        errors.append(f"numbered sections/order mismatch: observed={observed!r}, expected={expected!r}")
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(2).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        if title in blocks:
            errors.append(f"duplicate section: {title}")
        blocks[title] = text[match.end() : end].strip()
    for title in REQUIRED_SECTIONS:
        block = blocks.get(title, "")
        compact = re.sub(r"\s+", "", block).lower()
        if not block or compact in {"x", "todo", "tbd", "待补", "-"}:
            errors.append(f"section is empty or placeholder-only: {title}")
    return blocks, errors


def parse_status(text: str) -> tuple[dict[str, str], list[str]]:
    matches = list(re.finditer(r"(?m)^##[ \t]+状态[ \t]*$", text))
    if len(matches) != 1:
        return {}, [f"expected exactly one visible '## 状态' section; found {len(matches)}"]
    start = matches[0].end()
    next_heading = re.search(r"(?m)^##[ \t]+", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    rows, errors = parse_table(text[start:end], STATUS_HEADERS)
    values: dict[str, str] = {}
    allowed_keys = set(STATUS_ENUMS) | set(OPTIONAL_STATUS_ENUMS) | OPTIONAL_STATUS_TEXT | {"report_path", "evidence_as_of"}
    for row in rows:
        key, value = row
        if key in values:
            errors.append(f"duplicate status field: {key}")
        elif key not in allowed_keys:
            errors.append(f"unknown status field: {key}")
        else:
            values[key] = value
    for key, allowed in STATUS_ENUMS.items():
        value = values.get(key)
        if not value:
            errors.append(f"missing status field: {key}")
        elif value not in allowed:
            errors.append(f"invalid {key}={value!r}; allowed={sorted(allowed)}")
    for key, allowed in OPTIONAL_STATUS_ENUMS.items():
        value = values.get(key)
        if not value:
            errors.append(f"missing status field: {key}")
        elif value not in allowed:
            errors.append(f"invalid {key}={value!r}; allowed={sorted(allowed)}")
    summary_path = values.get("summary_path", "").strip().strip("`")
    if not summary_path or summary_path.lower() in {"tbd", "todo", "null", "none"}:
        errors.append("missing concrete summary_path")
    elif not summary_path.replace("\\", "/").endswith("/upgrade-summary.json"):
        errors.append("summary_path must end with /upgrade-summary.json")
    if not values.get("report_path"):
        errors.append("missing status field: report_path")
    as_of = values.get("evidence_as_of")
    if not as_of:
        errors.append("missing status field: evidence_as_of")
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of):
        errors.append(
            f"invalid evidence_as_of={as_of!r}; expected YYYY-MM-DD"
        )
    return values, errors


def validate_ui_visual_risk(
    inventory_rows: list[list[str]], status: dict[str, str], impact_block: str, result: "ReportResult"
) -> None:
    packages = {row[0].strip("`").lower() for row in inventory_rows if row}
    triggered = any(any(trigger in package for trigger in VISUAL_PACKAGE_TRIGGERS) for package in packages)
    visual_required = status.get("visual_acceptance_required")
    if triggered and visual_required != "yes":
        result.error("UI/CSS package trigger requires visual_acceptance_required=yes")
    if not triggered:
        return
    if not re.search(r"(?m)^###\s+ui_visual_risk\s*$", impact_block):
        result.error("§5 UI/CSS package trigger requires ### ui_visual_risk")
        return
    for marker in VISUAL_RISK_MARKERS:
        match = re.search(rf"(?im)^\s*[-*]?\s*{re.escape(marker)}\s*(.+)$", impact_block)
        if not match or match.group(1).strip().lower() in {"", "-", "tbd", "todo", "待补"}:
            result.error(f"§5 ui_visual_risk missing substantive {marker}")


def path_matches_report(value: str, report: Path) -> bool:
    """Require a concrete path that resolve-equals the report directory.

    Bare `.` / `./` are rejected. Soft `endswith` matching is not allowed.
    Relative paths resolve against the process cwd (portable fixtures).
    Leading-`/` paths are treated as POSIX absolutes even on Windows.
    """
    text = value.strip().strip("`").replace("\\", "/").rstrip("/")
    if not text or text in {".", "./"}:
        return False
    expected = report.parent.resolve()
    expected_posix = expected.as_posix()

    if text.startswith("/"):
        if expected_posix == text or expected_posix.lower() == text.lower():
            return True
        if sys.platform == "win32":
            mapped = Path(expected.anchor + text.lstrip("/"))
            try:
                return mapped.resolve() == expected
            except OSError:
                return False
        try:
            return Path(text).resolve() == expected
        except OSError:
            return False

    candidate = Path(text)
    try:
        if candidate.is_absolute():
            return candidate.resolve() == expected
        return (Path.cwd() / text).resolve() == expected
    except OSError:
        return False


def parse_evidence_as_of_baseline(baseline: str, status_value: str | None, result: ReportResult) -> None:
    """Allow §1 to restate evidence_as_of; status table remains authoritative."""
    match = EVIDENCE_AS_OF_RE.search(baseline)
    if match and status_value and match.group(1) != status_value:
        result.error(
            f"§1 evidence_as_of {match.group(1)!r} != status evidence_as_of {status_value!r}"
        )


def parse_lockfile_status(baseline: str, result: ReportResult) -> str | None:
    match = re.search(
        r"(?im)^\s*[-*]?\s*`?lockfile_status`?\s*[:：]\s*`?([A-Za-z_-]+)`?",
        baseline,
    )
    if not match:
        result.error(
            "§1 missing structured lockfile_status: present / absent / unparsed"
        )
        return None
    value = match.group(1).lower()
    if value not in LOCKFILE_STATUSES:
        result.error(
            f"§1 invalid lockfile_status {value!r}; allowed={sorted(LOCKFILE_STATUSES)}"
        )
        return None
    return value


def _checklist_answer(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("|"):
        cells = [clean_cell(cell) for cell in stripped.strip("|").split("|")]
        return cells[-1].strip() if len(cells) >= 2 else ""
    match = re.search(r"[:：]\s*(.+?)\s*$", stripped)
    return match.group(1).strip() if match else ""


def validate_manual_gap_checklist(block: str, result: ReportResult) -> None:
    if MANUAL_GAP_CHECKLIST_MARKER not in block:
        result.error(f"§10 missing required checklist marker: {MANUAL_GAP_CHECKLIST_MARKER}")
        return
    lines = block.splitlines()
    matched_lines: dict[str, str] = {}
    for label, alternatives in MANUAL_GAP_ITEMS:
        matched = next(
            (
                line
                for line in lines
                if any(marker.lower() in line.lower() for marker in alternatives)
            ),
            None,
        )
        if matched is None:
            result.error(f"§10 manual checklist missing item: {label}")
            continue
        matched_lines[label] = matched
        answer = _checklist_answer(matched)
        if answer.lower() in CHECKLIST_PLACEHOLDERS:
            result.error(f"§10 manual checklist item has no answer: {label}")
        elif answer.lower() in {item.lower() for item in SHALLOW_CHECKLIST_ANSWERS}:
            result.error(
                f"§10 manual checklist item has shallow answer {answer!r}: {label}"
            )
    line_owners: dict[str, list[str]] = {}
    for label, line in matched_lines.items():
        line_owners.setdefault(line, []).append(label)
    for line, owners in line_owners.items():
        if len(owners) > 1:
            result.error(
                "§10 manual checklist items must each have a dedicated line; "
                f"shared line covers {owners!r}"
            )
            break


def parse_axes(path_block: str, result: ReportResult) -> dict[str, str]:
    axes: dict[str, str] = {}
    for marker, allowed in AXIS_MARKERS:
        match = re.search(
            rf"(?im)^\s*[-*]?\s*`?{re.escape(marker)}`?\s*`?([A-Za-z0-9_-]+)`?",
            path_block,
        )
        if not match:
            # also allow inline "runtime_axis: compat"
            match = re.search(
                rf"(?i){re.escape(marker)}\s*`?([A-Za-z0-9_-]+)`?",
                path_block,
            )
        if not match:
            result.error(f"§3 missing required axis marker {marker}")
            continue
        value = match.group(1).strip()
        if value not in allowed:
            result.error(
                f"§3 invalid {marker} {value!r}; allowed={sorted(allowed)}"
            )
            continue
        axes[marker.rstrip(":")] = value
    return axes


def validate_path_axis_consistency(
    path_id: str, axes: dict[str, str], result: ReportResult
) -> None:
    if path_id == "deferred-inventory-only":
        return
    constraints = PATH_AXIS_CONSTRAINTS.get(path_id)
    if not constraints:
        return
    for axis_key, expected in constraints.items():
        actual = axes.get(axis_key)
        if actual and actual != expected:
            result.error(
                f"path id {path_id!r} conflicts with {axis_key}={actual!r}; "
                f"preset requires {expected!r} "
                f"(Wave 1 `other` + matching path id, or change axes)"
            )


def parse_subsystems(block: str, result: ReportResult) -> list[dict[str, str]]:
    rows, errors = parse_table(block, SUBSYSTEM_HEADERS)
    for error in errors:
        result.error(f"§4 {error}")
    if not rows:
        result.error("§4 subsystem inventory must contain at least one data row")
    parsed: list[dict[str, str]] = []
    seen: set[str] = set()
    for cells in rows:
        sid, scope, risk, readiness, required, recipe, note = cells
        if not UNIT_ID.fullmatch(sid):
            result.error(f"invalid subsystem id: {sid!r}")
        if sid in seen:
            result.error(f"duplicate subsystem id: {sid}")
        seen.add(sid)
        if scope not in SCOPE_STATUSES:
            result.error(f"invalid scope_status for {sid}: {scope!r}")
        if risk not in RISKS:
            result.error(f"invalid risk for {sid}: {risk!r}")
        if readiness not in READINESS:
            result.error(f"invalid readiness for {sid}: {readiness!r}")
        if required not in YES_NO:
            result.error(f"invalid required_for_path for {sid}: {required!r}")
        if (
            scope == "in_scope"
            and risk in HIGH_BLOCKER_RISKS
            and required != "yes"
        ):
            result.error(
                f"in_scope high/blocker subsystem {sid!r} must set required_for_path=yes"
            )
        if not recipe or not note:
            result.error(f"subsystem row has blank recipe/note: {sid}")
        parsed.append(
            {
                "id": sid,
                "scope_status": scope,
                "risk": risk,
                "readiness": readiness,
                "required_for_path": required,
            }
        )
    missing_defaults = [sid for sid in DEFAULT_SUBSYSTEMS if sid not in seen]
    if missing_defaults:
        result.error(
            "§4 missing default subsystem rows (use not_applicable if unused): "
            + ", ".join(missing_defaults)
        )
    return parsed


def parse_queue(block: str, result: ReportResult) -> list[dict[str, str]]:
    rows, errors = parse_table(block, QUEUE_HEADERS)
    for error in errors:
        result.error(f"§7 {error}")
    if not rows:
        result.error("§7 confirmation queue must contain at least one data row")
    parsed: list[dict[str, str]] = []
    seen: set[str] = set()
    for unit, unit_type, status, question, options in rows:
        if unit in seen:
            result.error(f"duplicate queue unit: {unit}")
        seen.add(unit)
        if unit_type not in UNIT_TYPES:
            result.error(f"invalid queue type for {unit}: {unit_type!r}")
        prefix = f"{unit_type}:" if unit_type in UNIT_TYPES else ""
        unit_id = unit[len(prefix) :] if prefix and unit.startswith(prefix) else ""
        if not unit_id or not UNIT_ID.fullmatch(unit_id):
            result.error(f"queue unit/type mismatch or invalid id: {unit!r} / {unit_type!r}")
        if unit_type == "path" and unit_id and unit_id not in PATH_IDS:
            result.error(
                f"unknown path id {unit_id!r}; allowed={sorted(PATH_IDS)}"
            )
        if status not in QUEUE_STATUSES:
            result.error(f"invalid queue status for {unit}: {status!r}")
        if not question or not options:
            result.error(f"queue row has blank question/options: {unit}")
        proceed = f"proceed:{unit_type}:{unit_id}" if unit_id else ""
        if status in {"ready", "decided"} and proceed not in options:
            result.error(f"{status} queue row missing matching token {proceed!r}: {unit}")
        parsed.append(
            {"unit": unit, "type": unit_type, "id": unit_id, "status": status,
             "question": question, "options": options, "proceed": proceed}
        )
    path_rows = [row for row in parsed if row["type"] == "path"]
    if len(path_rows) != 1:
        result.error(f"confirmation queue requires exactly one path row; found {len(path_rows)}")
    return parsed


def parse_record(path: Path, expected_unit: str, expected_status: str, result: ReportResult) -> None:
    if not path.is_file():
        result.error(f"missing decision record: {path.name}")
        return
    text = visible_markdown(path.read_text(encoding="utf-8"))
    rows, errors = parse_table(text, RECORD_HEADERS)
    for error in errors:
        result.error(f"{path.name}: {error}")
    values: dict[str, str] = {}
    for field_name, value in rows:
        if field_name in values:
            result.error(f"{path.name}: duplicate field {field_name}")
        values[field_name] = value
    for field_name in REQUIRED_RECORD_FIELDS:
        if field_name not in values:
            result.error(f"{path.name}: missing field {field_name}")
        elif not values[field_name].strip():
            result.error(f"{path.name}: blank field {field_name}")
    if values.get("单元键") != expected_unit:
        result.error(f"{path.name}: 单元键 must be {expected_unit!r}")
    unit_type, unit_id = expected_unit.split(":", 1)
    if values.get("类型") != unit_type:
        result.error(f"{path.name}: 类型 must be {unit_type!r}")
    if values.get("风险") not in RISKS:
        result.error(f"{path.name}: invalid 风险 {values.get('风险')!r}")
    record_status = values.get("确认队列状态")
    if record_status not in QUEUE_STATUSES:
        result.error(f"{path.name}: invalid 确认队列状态 {record_status!r}")
    elif record_status != expected_status:
        result.error(
            f"{path.name}: record status {record_status!r} != queue status {expected_status!r}"
        )
    expected_token = f"proceed:{unit_type}:{unit_id}"
    options = values.get("推荐确认选项", "")
    answer = values.get("人工答复", "")
    if expected_status == "decided":
        if expected_token not in options:
            result.error(f"{path.name}: 推荐确认选项 missing {expected_token!r}")
        if answer != expected_token:
            result.error(f"{path.name}: decided 人工答复 must equal {expected_token!r}")
    elif expected_status == "deferred" and answer != "defer":
        result.error(f"{path.name}: deferred 人工答复 must equal 'defer'")
    evidence_url = values.get("兼容性证据（URL）", "")
    if evidence_url and not HTTP_URL_RE.search(evidence_url):
        result.error(
            f"{path.name}: 兼容性证据（URL） must contain an http(s) URL"
        )


def validate_report(path: Path) -> ReportResult:
    result = ReportResult(path=path)
    if not path.is_file():
        result.error(f"report not found: {path}")
        return result
    text = visible_markdown(path.read_text(encoding="utf-8"))

    status, errors = parse_status(text)
    for error in errors:
        result.error(error)
    if status.get("report_path") and not path_matches_report(status["report_path"], path):
        result.error(
            f"report_path {status['report_path']!r} does not match actual report directory {str(path.parent)!r}"
        )

    sections, errors = split_sections(text)
    for error in errors:
        result.error(error)

    inventory_rows, table_errors = parse_table(sections.get("仓画像与依赖就绪度", ""), INVENTORY_HEADERS)
    for error in table_errors:
        result.error(f"§2 {error}")
    if not inventory_rows:
        result.error("§2 dependency inventory must contain at least one data row")
    else:
        for row in inventory_rows:
            if row[2] not in READINESS:
                result.error(f"§2 invalid Vue3 readiness for {row[0]}: {row[2]!r}")
            if any(not cell for cell in row):
                result.error(f"§2 inventory row contains blank cells: {row[0]!r}")

    validate_ui_visual_risk(
        inventory_rows,
        status,
        sections.get("分层影响分析", ""),
        result,
    )

    baseline = sections.get("基线与假设", "")
    if "lockfile" not in baseline.lower():
        result.error("§1 must state lockfile status (e.g. path present, or 无 lockfile)")
    lock_status = parse_lockfile_status(baseline, result)
    parse_evidence_as_of_baseline(baseline, status.get("evidence_as_of"), result)

    path_block = sections.get("推荐迁移路径", "")
    if COMPOSITION_MARKER not in path_block:
        result.error(f"§3 missing required marker: {COMPOSITION_MARKER}")
    name_marker_ok = "Name, never run" in path_block or (
        "命名配方" in path_block and "不执行" in path_block
    )
    if not name_marker_ok:
        result.error("§3 missing Name-never-run marker")
    axes = parse_axes(path_block, result)
    recommended_match = RECOMMENDED_PATH_RE.search(path_block)
    recommended_path = recommended_match.group(1) if recommended_match else None
    if not recommended_path:
        result.error("§3 missing 推荐路径 id")
    elif recommended_path not in PATH_IDS:
        result.error(
            f"§3 unknown 推荐路径 id {recommended_path!r}; allowed={sorted(PATH_IDS)}"
        )
    else:
        validate_path_axis_consistency(recommended_path, axes, result)

    gap_block = sections.get("未决问题与证据缺口", "")
    validate_manual_gap_checklist(gap_block, result)

    subsystems = parse_subsystems(sections.get("子系统影响清单", ""), result)
    queue = parse_queue(sections.get("确认队列", ""), result)
    queue_by_unit = {row["unit"]: row for row in queue}
    path_rows = [row for row in queue if row["type"] == "path"]
    path_row = path_rows[0] if len(path_rows) == 1 else None
    if path_row and recommended_path and path_row["id"] != recommended_path:
        result.error(
            f"§7 path id {path_row['id']!r} does not match §3 推荐路径 id "
            f"{recommended_path!r}"
        )
    elif (
        path_row
        and path_row["id"] in PATH_IDS
        and path_row["id"] != recommended_path
    ):
        validate_path_axis_consistency(path_row["id"], axes, result)

    mandatory_ids = {
        row["id"]
        for row in subsystems
        if row["scope_status"] != "not_applicable"
        and (
            row["risk"] in HIGH_BLOCKER_RISKS
            or row.get("required_for_path") == "yes"
        )
    }
    for sid in sorted(mandatory_ids):
        if f"subsystem:{sid}" not in queue_by_unit:
            result.error(
                f"high/blocker or required_for_path subsystem {sid!r} missing from confirmation queue"
            )

    path_decided = bool(path_row and path_row["status"] == "decided")
    for row in queue:
        if row["type"] == "subsystem" and row["status"] == "ready" and not path_decided:
            result.error(f"subsystem {row['unit']} is ready before path is decided")

    analysis = status.get("analysis_status")
    decision = status.get("decision_status")
    gate = status.get("batch_implementation_gate")
    impl_ready = status.get("implementation_readiness")
    askable = [row for row in queue if row["status"] in {"ready", "pending"}]
    blocked_or_deferred = [row for row in queue if row["status"] in {"blocked", "deferred"}]
    if impl_ready and impl_ready != "not_assessed":
        result.error("implementation_readiness must be not_assessed in this skill")
    if analysis == "complete" and askable:
        result.error("analysis_status=complete while ready/pending queue rows remain")
    if analysis == "complete" and decision != "decided":
        result.error("analysis_status=complete requires decision_status=decided")
    if analysis == "blocked" and askable:
        result.error("analysis_status=blocked while ready/pending queue rows remain")
    if askable and decision != "needs_choice":
        result.error("ready/pending queue rows require decision_status=needs_choice")
    if gate == "ready" and (analysis != "complete" or decision != "decided"):
        result.error("batch_implementation_gate=ready requires complete/decided")
    if gate == "ready" and blocked_or_deferred:
        result.error("batch_implementation_gate=ready forbidden while blocked/deferred rows remain")
    if gate == "ready" and lock_status != "present":
        result.error(
            "batch_implementation_gate=ready requires lockfile_status=present"
        )
    if gate == "ready" and (not path_decided or any(
        queue_by_unit.get(f"subsystem:{sid}", {}).get("status") != "decided"
        for sid in mandatory_ids
    )):
        result.error(
            "batch_implementation_gate=ready requires path and every "
            "High/blocker/required_for_path subsystem decided"
        )

    records_dir = path.parent / DECISION_RECORDS_DIR
    if analysis == "complete":
        if not records_dir.is_dir():
            result.error("complete report requires decision-records/ directory")
        else:
            required_units: list[dict[str, str]] = []
            if path_row:
                required_units.append(path_row)
            for sid in sorted(mandatory_ids):
                row = queue_by_unit.get(f"subsystem:{sid}")
                if row:
                    required_units.append(row)
            for row in required_units:
                prefix = "migration-path" if row["type"] == "path" else "subsystem"
                record_path = records_dir / f"{prefix}__{row['id']}.md"
                parse_record(record_path, row["unit"], row["status"], result)
    elif analysis == "partial" and not records_dir.is_dir():
        result.warn("partial report missing decision-records/ (recommended)")

    if gate == "ready" and not any(
        "实施需另授权" in line or "不改代码" in line or "handoff only" in line.lower()
        for line in text.splitlines()
    ):
        result.error(
            "ready report must state that implementation needs separate authorization / "
            "this skill does not edit code / handoff only"
        )
    return result


def validate_batch_index(evidence_dir: Path, reports: list[Path], result: ReportResult) -> None:
    index = evidence_dir / BATCH_INDEX_NAME
    if not index.is_file():
        result.error(f"multi-batch evidence directory requires {BATCH_INDEX_NAME}")
        return
    text = visible_markdown(index.read_text(encoding="utf-8"))
    if not text.strip() or re.sub(r"\s+", "", text).lower() in {"x", "todo", "tbd"}:
        result.error(f"{BATCH_INDEX_NAME} is empty or placeholder-only")
    for report in reports:
        relative = report.relative_to(evidence_dir).as_posix()
        parts = report.relative_to(evidence_dir).parts
        if len(parts) != 3 or parts[0] not in {"workspace", "inventory"} or not re.fullmatch(
            r"[A-Za-z0-9._-]+__variant-[A-Za-z0-9._-]+__scope-[A-Za-z0-9._-]+", parts[1]
        ):
            result.error(f"invalid multi-batch report layout: {relative}")
        if relative not in text and parts[1] not in text:
            result.error(f"{BATCH_INDEX_NAME} does not reference batch report: {relative}")


def validate_evidence_dir(evidence_dir: Path) -> list[ReportResult]:
    root_report = evidence_dir / REPORT_NAME
    nested_reports = sorted(
        report for report in evidence_dir.glob(f"**/{REPORT_NAME}") if report != root_report
    )
    if root_report.is_file() and nested_reports:
        result = validate_report(root_report)
        result.error("evidence directory mixes single-batch root report with nested batch reports")
        for report in nested_reports:
            nested = validate_report(report)
            nested.error("nested report is invalid when a root single-batch report exists")
            result.findings.extend(nested.findings)
        return [result]
    if root_report.is_file():
        if (evidence_dir / BATCH_INDEX_NAME).exists():
            result = validate_report(root_report)
            result.error("single-batch evidence directory must not contain BATCH-INDEX.md")
            return [result]
        return [validate_report(root_report)]
    if not nested_reports:
        result = ReportResult(path=evidence_dir)
        result.error(f"no {REPORT_NAME} under evidence directory")
        return [result]
    index_result = ReportResult(path=evidence_dir / BATCH_INDEX_NAME)
    validate_batch_index(evidence_dir, nested_reports, index_result)
    return [index_result] + [validate_report(report) for report in nested_reports]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if bool(args.report) == bool(args.evidence_dir):
        print("provide exactly one of <report.md> or --evidence-dir", file=sys.stderr)
        return 2
    target = args.report or args.evidence_dir
    if target is None or not target.exists() or (args.evidence_dir and not target.is_dir()):
        print(f"path not found: {target}", file=sys.stderr)
        return 4
    results = [validate_report(target)] if args.report else validate_evidence_dir(target)
    payload = []
    error_count = 0
    for item in results:
        errors = item.errors
        error_count += len(errors)
        payload.append({
            "path": str(item.path),
            "errors": [finding.message for finding in errors],
            "warnings": [finding.message for finding in item.findings if finding.level == "WARN"],
        })
        if not args.json:
            print(f"## {item.path}")
            if not item.findings:
                print("OK")
            for finding in item.findings:
                print(f"{finding.level}: {finding.message}")
    if args.json:
        print(json.dumps({"results": payload, "error_count": error_count}, ensure_ascii=False, indent=2))
    return 3 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())

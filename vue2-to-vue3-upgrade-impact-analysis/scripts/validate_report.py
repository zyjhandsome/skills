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
    "behavior_parity_required": {"yes", "no"},
    "network_mode": {"online", "offline", "partial"},
}
STATUS_HEADERS = ("字段", "取值")
INVENTORY_HEADERS = ("包名", "当前版本", "Vue3 就绪度", "建议", "证据")
SUBSYSTEM_HEADERS = ("子系统", "scope_status", "风险", "就绪度", "命名配方", "说明")
QUEUE_HEADERS = ("单元", "类型", "状态", "问题", "选项")
RECORD_HEADERS = ("字段", "内容")

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
UNIT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
FENCE = re.compile(r"(?ms)^[ \t]*(```|~~~).*?^[ \t]*\1[ \t]*$")
HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")


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
    allowed_keys = set(STATUS_ENUMS) | {"report_path"}
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
    if not values.get("report_path"):
        errors.append("missing status field: report_path")
    return values, errors


def path_matches_report(value: str, report: Path) -> bool:
    normalized = value.strip().strip("`").replace("\\", "/").rstrip("/") or "."
    expected = report.parent.resolve()
    candidate = Path(normalized)
    if candidate.is_absolute():
        return candidate.resolve() == expected
    if normalized == ".":
        return True
    return expected.as_posix().rstrip("/").endswith("/" + normalized.lstrip("./"))


def parse_subsystems(block: str, result: ReportResult) -> list[dict[str, str]]:
    rows, errors = parse_table(block, SUBSYSTEM_HEADERS)
    for error in errors:
        result.error(f"§4 {error}")
    if not rows:
        result.error("§4 subsystem inventory must contain at least one data row")
    parsed: list[dict[str, str]] = []
    seen: set[str] = set()
    for cells in rows:
        sid, scope, risk, readiness, recipe, note = cells
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
        if not recipe or not note:
            result.error(f"subsystem row has blank recipe/note: {sid}")
        parsed.append({"id": sid, "scope_status": scope, "risk": risk, "readiness": readiness})
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

    baseline = sections.get("基线与假设", "")
    if "lockfile" not in baseline.lower():
        result.error("§1 must state lockfile status (e.g. path present, or 无 lockfile)")

    path_block = sections.get("推荐迁移路径", "")
    if COMPOSITION_MARKER not in path_block:
        result.error(f"§3 missing required marker: {COMPOSITION_MARKER}")
    name_marker_ok = "Name, never run" in path_block or (
        "命名配方" in path_block and "不执行" in path_block
    )
    if not name_marker_ok:
        result.error("§3 missing Name-never-run marker")

    gap_block = sections.get("未决问题与证据缺口", "")
    if MANUAL_GAP_CHECKLIST_MARKER not in gap_block:
        result.error(f"§10 missing required checklist marker: {MANUAL_GAP_CHECKLIST_MARKER}")

    subsystems = parse_subsystems(sections.get("子系统影响清单", ""), result)
    queue = parse_queue(sections.get("确认队列", ""), result)
    queue_by_unit = {row["unit"]: row for row in queue}
    path_rows = [row for row in queue if row["type"] == "path"]
    path_row = path_rows[0] if len(path_rows) == 1 else None

    mandatory_ids = {
        row["id"] for row in subsystems
        if row["scope_status"] != "not_applicable" and row["risk"] in HIGH_BLOCKER_RISKS
    }
    for sid in sorted(mandatory_ids):
        if f"subsystem:{sid}" not in queue_by_unit:
            result.error(f"high/blocker subsystem {sid!r} missing from confirmation queue")

    path_decided = bool(path_row and path_row["status"] == "decided")
    for row in queue:
        if row["type"] == "subsystem" and row["status"] == "ready" and not path_decided:
            result.error(f"subsystem {row['unit']} is ready before path is decided")

    analysis = status.get("analysis_status")
    decision = status.get("decision_status")
    gate = status.get("batch_implementation_gate")
    askable = [row for row in queue if row["status"] in {"ready", "pending"}]
    blocked_or_deferred = [row for row in queue if row["status"] in {"blocked", "deferred"}]
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
    if gate == "ready" and (not path_decided or any(
        queue_by_unit.get(f"subsystem:{sid}", {}).get("status") != "decided"
        for sid in mandatory_ids
    )):
        result.error("batch_implementation_gate=ready requires path and every High/blocker subsystem decided")

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

    if gate == "ready" and not any("实施需另授权" in line or "不改代码" in line for line in text.splitlines()):
        result.error("ready report must state that implementation needs separate authorization / this skill does not edit code")
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

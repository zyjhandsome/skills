#!/usr/bin/env python3
"""Validate a Vue2→Vue3 impact-analysis packet.

This validator checks the visible Markdown structure and cross-file decision
contract. It never proves that evidence is true or sufficient, and it never
modifies the analyzed project.

Exit codes: 0 pass, 2 usage error, 3 validation error, 4 path not found.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path



def _load_summary_validator():
    module_path = Path(__file__).with_name("validate_upgrade_summary.py")
    spec = importlib.util.spec_from_file_location(
        "vue2_to_vue3_validate_upgrade_summary", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load summary validator: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


validate_summary = _load_summary_validator()

REPORT_NAME = "vue2-to-vue3-upgrade-report.md"
BATCH_INDEX_NAME = "BATCH-INDEX.md"
DECISION_RECORDS_DIR = "decision-records"
SUMMARY_NAME = "upgrade-summary.json"
INVENTORY_NAME = "inventory.json"

ENTRY_MODES = {"upgrade", "residual-audit"}
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
# Value-checked only when present; absence means the default `upgrade` mode, so
# every packet written before residual audit existed stays valid.
SOFT_STATUS_ENUMS = {
    "entry_mode": ENTRY_MODES,
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
VALIDATION_HEADERS = ("命名配方", "实施期命令", "失败证明什么", "证据状态")
RECORD_HEADERS = ("字段", "内容")
YES_NO = {"yes", "no"}
AXIS_MARKERS = (
    ("runtime_axis:", {"compat", "direct-vue3"}),
    ("build_axis:", {"vite", "cli5-webpack5", "existing-vite"}),
    ("topology_axis:", {"single-cutover", "coexist", "host-port"}),
)
LOCKFILE_STATUSES = {"present", "absent", "unparsed"}
NODE_COMPATIBILITY_STATUSES = {
    "compatible",
    "upgrade-required",
    "conflict",
    "unknown",
}
NODE_TRANSITION_STRATEGIES = {
    "same-node",
    "upgrade-before-vue",
    "temporary-dual-node",
    "blocked",
    "undecided",
}
NODE_BASELINE_FIELDS = (
    "host_node_version",
    "current_node_contract",
    "current_node_evidence",
    "target_node_requirement",
    "target_node_sources",
    "node_compatibility_status",
    "node_transition_strategy",
)
# Always-required §1 anchor fields: the packet must bind to a repo state and
# state a browser support floor (value may be an evidenced unknown).
BASELINE_ANCHOR_FIELDS = (
    "repo_revision",
    "browser_support_floor",
)
PATH_IDS = {
    "compat-big-bang",
    "direct-vue3",
    "host-port-direct",
    "microfrontend-coexist",
    "deferred-inventory-only",
    "residual-audit",
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
    "host-port-direct": {
        "runtime_axis": "direct-vue3",
        "topology_axis": "host-port",
    },
    "microfrontend-coexist": {
        "topology_axis": "coexist",
    },
}
HOST_PORT_REQUIRED_MARKERS = (
    "source_root:",
    "implementation_target:",
    "forbid_source_mutation:",
)
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
    "分叉人工答复",
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
    # Silent Vue3 breaks: build/lint stay green while behavior degrades.
    ("component v-model model option", ("model 选项", "model:")),
    ("native/keyCode modifiers", (".native", "keyCode")),
    ("emits declaration double-fire", ("emits",)),
    (
        "global registration APIs and directive hooks",
        ("Vue.component", "Vue.directive", "Vue.mixin", "全局注册"),
    ),
    ("transition class rename", ("v-enter", "过渡类名", "transition 类名")),
    (
        "silent semantics family",
        ("v-if/v-for", "静默语义", "attr coercion"),
    ),
    # `.sync` → `v-model:<arg>` is the correct Vue3 rewrite, yet the argument is the
    # old UI kit's prop name. When the kit is replaced in the same upgrade the prop
    # must be re-resolved against the new kit, or the binding goes dead build-green.
    ("sync modifier target prop identity", (".sync", "sync 修饰符")),
    # Legacy UI kits accepted font/sprite class strings where component-based
    # targets require a Component. The residue can be silent or abort mount.
    ("UI kit icon prop class identity", ("icon prop", "sprite 字符串", "sprite-icon")),
    # Codemods rewrite the `| filter` pipe and leave object-access call sites alone.
    ("options filters object access", ("$options.filters", "过滤器对象访问")),
    # Vue 2 unwrapped a bare `<template>`; Vue 3 compiles it to a real template
    # element whose children the UA stylesheet hides, blanking a whole section
    # with no error, no warning and no codemod fingerprint.
    (
        "lone template wrapper",
        ("裸 `<template>`", "裸 <template>", "lone_template_wrapper"),
    ),
    # Vue 3 renders into the mount container instead of replacing it, so an id or
    # class shared with the root component's root element now matches twice.
    ("mount container selector collision", ("挂载容器", "mount container")),
    # Overlay chrome moves under Teleport, so CSS that suppressed it stops
    # matching and the app's own replacement control becomes a duplicate.
    (
        "teleported kit chrome suppression",
        ("overlay chrome", "kit chrome", "kit_chrome_css_suppression"),
    ),
    # Dev server and production build are two runtime faces with different module
    # resolution and entry/URL topology; one can stay green while the other breaks.
    ("dev vs build runtime lane", ("运行面", "require.context", "dev 与 build")),
    # The inverse of a silent break: code that was already wrong and was being
    # muffled. Router 3 prototype patches and `.catch` swallows hid navigation
    # rejections that Router 4 reports, and missing required params go from
    # ignored to thrown — usually on a bootstrap navigation, i.e. a blank page.
    ("router navigation silent-to-throw", ("导航静默变抛错", "Missing required param")),
    # Bare globals loaded from HTML/dynamic scripts are not Vue plugins; their
    # registration timing is only closed by a post-mount runtime round-trip.
    (
        "external global script runtime contract",
        ("外部全局脚本", "external global script", "globalThis.X"),
    ),
    # Migrating *onto* an API the target major already deprecates is invisible to
    # build and to screenshots, and shows up as per-mount console noise at the
    # scale of the call sites a codemod touched. Style/build tooling has the same
    # clock (a working `@import` that is already deprecated).
    ("target dependency deprecation surface", ("弃用告警面", "目标依赖弃用面")),
)
MARKER_PLACEHOLDERS = {"", "-", "—", "tbd", "todo", "待补", "待填", "待填写"}
# A UI kit that is replaced or majored shifts behavior contracts (mount timing,
# prop/enum identity, event payloads) that stay invisible to build and to visual diff.
UI_BEHAVIOR_READINESS = {"replace", "needs-major"}
UI_BEHAVIOR_MARKERS = (
    "mount_timing:",
    "prop_renames:",
    "enum_renames:",
    "event_contract:",
    "slot_contract:",
    # Slot *names* migrating is not the same risk as what a slot is allowed to
    # contain: trigger/reference slots in the new kit apply directives to their
    # single child, which requires an element-rooted node. A component-rooted
    # child keeps the build green and only warns at runtime.
    "slot_content_shape:",
    "required_behavior_assertions:",
)
UI_STAGING_VALUES = {"with-runtime", "after-runtime"}
# `proceed:subsystem:<id>` answers "does it come along", never the fork inside.
# Each of these picks a different package to install, and each has a wrong
# default nobody chose — a bare `npm i vue-router` resolves to v5 while a Vue2
# repo's migration guide is v3->v4. `ui` is absent on purpose: its fork is
# `ui_cutover_staging`, gated in §3.
SUBSYSTEM_FORK_MARKERS = {
    "router": ("router_major:", {"4", "5"}, "confirm:router-major"),
    "store": ("store_target:", {"vuex4", "pinia"}, "confirm:store-target"),
    "i18n-plugins": (
        "i18n_mode:",
        {"legacy", "composition"},
        "confirm:i18n-mode",
    ),
    "test": ("test_runner:", {"keep", "vitest"}, "confirm:test-runner"),
}
CONFIRM_TOKEN_RE = re.compile(
    r"confirm:[A-Za-z0-9@._/-]+(?::[A-Za-z0-9@._/-]+)*"
)
BLOCKER_ACTIONS = {"replace", "fork", "remove", "defer"}
NO_FORK_ANSWER_VALUES = {"—", "-", "n/a", "not_applicable"}
RESIDUAL_AUDIT_PATH_ID = "residual-audit"
# A residual audit inspects an already-Vue3 workspace; it proposes no cutover,
# so it is exempt from the upgrade-path machinery and carries these instead.
RESIDUAL_FINDING_MARKERS = (
    "compat_shims_present:",
    "codemod_artifacts:",
    "silent_break_residues:",
    "runtime_lane_residues:",
    "required_cleanup_assertions:",
)
# Paths that plan no cutover: no axis preset, no target-node resolution, no
# recipe/lane/console-baseline apparatus.
NON_CUTOVER_PATH_IDS = {"deferred-inventory-only", RESIDUAL_AUDIT_PATH_ID}
CHECKLIST_PLACEHOLDERS = {"", "-", "—", "todo", "待填", "待填写"}
VALIDATION_PLACEHOLDERS = CHECKLIST_PLACEHOLDERS | {"tbd", "待补", "n/a", "na"}
RECIPE_SKIP = {"name", "never", "run"}
RECIPE_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
UNIT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
FENCE = re.compile(r"(?ms)^[ \t]*(```|~~~).*?^[ \t]*\1[ \t]*$")
HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")
VISUAL_PACKAGE_TRIGGERS = (
    "element-ui",
    "element-plus",
    "ant-design-vue",
    "vuetify",
    "vant",
    "tailwindcss",
    "vxe-table",
    "vue-grid-layout",
    "vue-json-tree-view",
    "vue-ueditor-wrap",
    "quill",
    "codemirror",
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
    allowed_keys = (
        set(STATUS_ENUMS)
        | set(OPTIONAL_STATUS_ENUMS)
        | set(SOFT_STATUS_ENUMS)
        | OPTIONAL_STATUS_TEXT
        | {"report_path", "evidence_as_of"}
    )
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
    for key, allowed in SOFT_STATUS_ENUMS.items():
        value = values.get(key)
        if value and value not in allowed:
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
            continue
        if marker == "required_visual_states:" and visual_required == "yes":
            states = [item.strip() for item in match.group(1).split(",") if item.strip()]
            # Downstream visual gates hard-require at least five unique state rows;
            # fewer than five here fails only after the baseline window has closed.
            if len(set(states)) < 5:
                result.error(
                    "§5 required_visual_states needs at least 5 unique states when "
                    "visual_acceptance_required=yes"
                )


def ui_kit_changes(subsystems: list[dict[str, str]]) -> bool:
    """True when the `ui` subsystem swaps or majors its kit in this upgrade."""
    return any(
        row.get("id") == "ui"
        and row.get("scope_status") == "in_scope"
        and row.get("readiness") in UI_BEHAVIOR_READINESS
        for row in subsystems
    )


def _marker_value(block: str, marker: str) -> str | None:
    match = re.search(rf"(?im)^\s*[-*]?\s*`?{re.escape(marker)}`?\s*(.+)$", block)
    if not match:
        return None
    value = match.group(1).strip()
    return None if value.lower() in MARKER_PLACEHOLDERS else value


def validate_ui_behavior_contract(
    subsystems: list[dict[str, str]], impact_block: str, result: "ReportResult"
) -> None:
    """A kit swap shifts behavior contracts that no visual diff can see.

    Lazy-mounted overlays, renamed props, renamed enum values and changed event
    payloads all keep the build green and the screenshots comparable while the
    interaction is dead, so they need their own §5 block and their own assertions.
    """
    if not ui_kit_changes(subsystems):
        return
    if not re.search(r"(?m)^###\s+ui_behavior_contract\s*$", impact_block):
        result.error(
            "§5 UI-kit replacement/major requires ### ui_behavior_contract "
            "(behavior shifts are not covered by ui_visual_risk)"
        )
        return
    for marker in UI_BEHAVIOR_MARKERS:
        value = _marker_value(impact_block, marker)
        if value is None:
            result.error(f"§5 ui_behavior_contract missing substantive {marker}")
            continue
        if marker == "required_behavior_assertions:":
            items = {item.strip() for item in value.split(",") if item.strip()}
            if len(items) < 3:
                result.error(
                    "§5 required_behavior_assertions needs at least 3 unique "
                    "assertions; each maps to a §8 interaction-level row"
                )


def validate_ui_cutover_staging(
    subsystems: list[dict[str, str]], path_block: str, result: "ReportResult"
) -> None:
    """Whether the kit moves with the runtime or after it is the blast-radius lever."""
    if not ui_kit_changes(subsystems):
        return
    value = _marker_value(path_block, "ui_cutover_staging:")
    if value is None:
        result.error(
            "§3 UI-kit replacement/major requires ui_cutover_staging: "
            f"{sorted(UI_STAGING_VALUES)}"
        )
        return
    # Take the leading token so a trailing rationale (often in full-width
    # parentheses, with no space before it) does not become part of the value.
    token = re.match(r"[A-Za-z0-9_-]+", value.strip().lstrip("`"))
    staging = token.group(0) if token else value.strip()
    if staging not in UI_STAGING_VALUES:
        result.error(
            f"§3 invalid ui_cutover_staging {staging!r}; allowed={sorted(UI_STAGING_VALUES)}"
        )


def _inline_marker_value(text: str, marker: str) -> str | None:
    """Read a marker written inside a table cell rather than on its own line."""
    match = re.search(rf"`?{re.escape(marker)}`?\s*`?([A-Za-z0-9_.-]+)`?", text)
    if not match:
        return None
    value = match.group(1).strip().strip("`")
    return None if value.lower() in MARKER_PLACEHOLDERS else value


def validate_subsystem_forks(
    subsystems: list[dict[str, str]],
    queue: list[dict[str, str]],
    entry_mode: str,
    path_block: str,
    inventory_rows: list[list[str]],
    analysis_status: str,
    implementation_gate: str,
    result: "ReportResult",
) -> dict[str, set[str]]:
    """A scope answer must not be mistaken for an answer to the fork inside it.

    Router v4-vs-v5, Vuex-vs-Pinia, i18n legacy-vs-composition and the test
    runner each decide what actually gets installed. Left unanswered they are
    settled later by whoever runs the install, which is how a human who approved
    a scope finds the state library swapped at implementation time. A `decided`
    queue row whose §4 note carries no fork marker is indistinguishable from one
    the analyzer answered on the human's behalf. Return the exact confirm tokens
    implied by those markers so Decision Records can prove the user supplied
    them rather than merely repeating the analyzer's recommendation.
    """
    expected_tokens: dict[str, set[str]] = {}
    if entry_mode == "residual-audit":
        return expected_tokens
    notes = {row.get("id"): row.get("note", "") for row in subsystems}
    queue_by_unit = {row.get("unit"): row for row in queue}
    for row in queue:
        if row.get("type") != "subsystem" or row.get("status") != "decided":
            continue
        subsystem_id = row.get("id", "")
        spec = SUBSYSTEM_FORK_MARKERS.get(subsystem_id)
        if spec is None:
            continue
        marker, allowed, token_prefix = spec
        value = _inline_marker_value(notes.get(subsystem_id, ""), marker)
        if value is None:
            result.error(
                f"§4 {subsystem_id} is decided in §7 but its note records no "
                f"{marker} — proceed:subsystem only answers scope; "
                f"allowed={sorted(allowed)}"
            )
            continue
        if value not in allowed:
            result.error(
                f"§4 invalid {marker} {value!r} for {subsystem_id}; "
                f"allowed={sorted(allowed)}"
            )
            continue
        expected_tokens.setdefault(subsystem_id, set()).add(
            f"{token_prefix}:{value}"
        )

    ui_row = queue_by_unit.get("subsystem:ui")
    if ui_row and ui_row.get("status") == "decided":
        ui_staging = _inline_marker_value(path_block, "ui_cutover_staging:")
        if ui_staging in UI_STAGING_VALUES:
            expected_tokens.setdefault("ui", set()).add(
                f"confirm:ui-staging:{ui_staging}"
            )

    # An `unknown` package is not resolved by deciding the containing subsystem.
    # A complete packet must carry one explicit per-package action token, owned
    # by one decided subsystem. This prevents an i18n mode or generic proceed
    # answer from silently deciding replace/remove for an unrelated plugin.
    if analysis_status == "complete":
        for package, _version, readiness, _suggestion, _evidence in inventory_rows:
            if readiness != "unknown":
                continue
            token_re = re.compile(
                rf"confirm:blocker:{re.escape(package)}:"
                rf"({'|'.join(sorted(BLOCKER_ACTIONS))})(?![A-Za-z0-9@._/-])"
            )
            owners: list[tuple[str, str]] = []
            for subsystem_id, note in notes.items():
                for match in token_re.finditer(note):
                    owners.append((subsystem_id or "", match.group(0)))
            unique = set(owners)
            if not unique:
                result.error(
                    f"§2 unknown package {package!r} requires exactly one explicit "
                    f"confirm:blocker:{package}:<replace|fork|remove|defer> token "
                    "in its §4 owner note"
                )
                continue
            if len(unique) != 1:
                result.error(
                    f"§2 unknown package {package!r} has ambiguous package actions: "
                    f"{sorted(unique)!r}"
                )
                continue
            owner, token = next(iter(unique))
            owner_row = queue_by_unit.get(f"subsystem:{owner}")
            if not owner_row or owner_row.get("status") != "decided":
                result.error(
                    f"§2 unknown package {package!r} action is owned by {owner!r}, "
                    "but that subsystem is not decided in §7"
                )
                continue
            if token.endswith(":defer") and implementation_gate == "ready":
                result.error(
                    f"§2 unknown package {package!r} was explicitly deferred; "
                    "batch_implementation_gate must stay frozen"
                )
            expected_tokens.setdefault(owner, set()).add(token)

    return expected_tokens


def validate_residual_audit(
    entry_mode: str,
    recommended_path: str | None,
    impact_block: str,
    result: "ReportResult",
) -> None:
    """`residual-audit` must be a writable branch, not just a permitted word.

    An already-Vue3 workspace has no cutover to plan, so the packet swaps the
    upgrade-path apparatus for an inventory of what the previous migration left
    behind — and that inventory is only useful if it names cleanup assertions.
    """
    if entry_mode != "residual-audit":
        if recommended_path == RESIDUAL_AUDIT_PATH_ID:
            result.error(
                f"§3 推荐路径 id {RESIDUAL_AUDIT_PATH_ID!r} requires status "
                "entry_mode: residual-audit"
            )
        return
    if recommended_path and recommended_path != RESIDUAL_AUDIT_PATH_ID:
        result.error(
            f"entry_mode=residual-audit requires §3 推荐路径 id "
            f"{RESIDUAL_AUDIT_PATH_ID!r}, not {recommended_path!r} "
            "(a residual audit proposes no migration path)"
        )
    if not re.search(r"(?m)^###\s+residual_findings\s*$", impact_block):
        result.error(
            "§5 entry_mode=residual-audit requires ### residual_findings "
            "(what the previous migration left behind)"
        )
        return
    for marker in RESIDUAL_FINDING_MARKERS:
        value = _marker_value(impact_block, marker)
        if value is None:
            result.error(f"§5 residual_findings missing substantive {marker}")
            continue
        if marker == "required_cleanup_assertions:":
            items = {item.strip() for item in value.split(",") if item.strip()}
            if len(items) < 3:
                result.error(
                    "§5 required_cleanup_assertions needs at least 3 unique "
                    "assertions; each maps to a §8 row"
                )


def validate_default_path_deviation(
    axes: dict[str, str], path_block: str, result: "ReportResult"
) -> None:
    """Single-repo in-place defaults to compat; overriding it must be argued.

    `direct-vue3` in place removes the compat layer that would otherwise absorb
    the silent-failure family, so the packet has to say what it is giving up.
    """
    if axes.get("topology_axis") != "single-cutover":
        return
    if axes.get("runtime_axis") != "direct-vue3":
        return
    if _marker_value(path_block, "default_path_deviation:") is None:
        result.error(
            "§3 in-place runtime_axis=direct-vue3 deviates from the compat-big-bang "
            "default and requires a substantive default_path_deviation line "
            "(what the default would have absorbed, and why it is not needed here)"
        )


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


def parse_node_matrix(baseline: str, result: ReportResult) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in NODE_BASELINE_FIELDS:
        match = re.search(
            rf"(?im)^\s*[-*]?\s*`?{re.escape(name)}`?\s*[:：]\s*(.+?)\s*$",
            baseline,
        )
        if not match:
            result.error(f"§1 missing structured {name}:")
            continue
        value = match.group(1).strip().strip("`").strip()
        if not value or re.fullmatch(r"(?:<[^>]+>|tbd|todo|待补)", value, re.I):
            result.error(f"§1 {name} must contain a concrete value or explicit unknown")
            continue
        values[name] = value

    status = values.get("node_compatibility_status", "").lower()
    strategy = values.get("node_transition_strategy", "").lower()
    target_sources = values.get("target_node_sources", "")
    if target_sources and not HTTP_URL_RE.search(target_sources):
        result.error("§1 target_node_sources must include an official/registry http(s) URL")
    if status and status not in NODE_COMPATIBILITY_STATUSES:
        result.error(
            "§1 node_compatibility_status must be one of "
            f"{sorted(NODE_COMPATIBILITY_STATUSES)}"
        )
    if strategy and strategy not in NODE_TRANSITION_STRATEGIES:
        result.error(
            "§1 node_transition_strategy must be one of "
            f"{sorted(NODE_TRANSITION_STRATEGIES)}"
        )
    if status == "compatible" and strategy != "same-node":
        result.error(
            "§1 compatible Node matrix requires node_transition_strategy=same-node"
        )
    if status == "upgrade-required" and strategy not in {
        "upgrade-before-vue",
        "temporary-dual-node",
    }:
        result.error(
            "§1 upgrade-required Node matrix requires upgrade-before-vue or "
            "temporary-dual-node"
        )
    if status == "conflict" and strategy != "blocked":
        result.error(
            "§1 conflicting Node matrix requires node_transition_strategy=blocked"
        )
    if status == "unknown" and strategy not in {"undecided", "blocked"}:
        result.error(
            "§1 unknown Node matrix requires "
            "node_transition_strategy=undecided|blocked"
        )
    validate_selected_node_version(status, baseline, result)
    return values


def validate_selected_node_version(
    status: str, baseline: str, result: "ReportResult"
) -> None:
    """A range is not a version, and every declaration surface holds one value.

    `target_node_requirement` is an intersection like `^20.19.0 || >=22.12.0`,
    but `.nvmrc`, `engines.node`, CI setup-node, the Docker base image and the
    deploy builder each take exactly one. Leaving the pick implicit is how those
    surfaces quietly end up on different majors. Only demanded when the upgrade
    actually rewrites them: a `compatible`/`same-node` repo writes nothing.
    """
    if status != "upgrade-required":
        return
    match = re.search(
        r"(?im)^\s*[-*]?\s*`?selected_node_version`?\s*[:：]\s*(.+?)\s*$", baseline
    )
    selected = match.group(1).strip().strip("`").strip() if match else ""
    if not selected or re.fullmatch(r"(?:<[^>]+>|tbd|todo|待补|undecided)", selected, re.I):
        result.error(
            "§1 node_compatibility_status=upgrade-required requires "
            "selected_node_version: the one concrete version every declaration "
            "surface (.nvmrc / engines / CI / Docker / deploy builder) will carry"
        )
        return
    if re.search(r"\|\||[\^~><=*]|\bx\b", selected):
        result.error(
            f"§1 selected_node_version must be one concrete version, not a range: "
            f"{selected!r}"
        )


def parse_baseline_anchor_fields(baseline: str, result: ReportResult) -> dict[str, str]:
    """§1 must bind the packet to a repo revision and a browser support floor."""
    values: dict[str, str] = {}
    for name in BASELINE_ANCHOR_FIELDS:
        match = re.search(
            rf"(?im)^\s*[-*]?\s*`?{re.escape(name)}`?\s*[:：]\s*(.+?)\s*$",
            baseline,
        )
        if not match:
            result.error(f"§1 missing structured {name}:")
            continue
        value = match.group(1).strip().strip("`").strip()
        if not value or re.fullmatch(r"(?:<[^>]+>|tbd|todo|待补|待填)", value, re.I):
            result.error(
                f"§1 {name} must contain a concrete value or an evidenced unknown"
            )
            continue
        values[name] = value
    return values


def parse_named_lockfile_status(baseline: str, name: str) -> str | None:
    match = re.search(
        rf"(?im)^\s*[-*]?\s*`?{re.escape(name)}`?\s*[:：]\s*`?([A-Za-z_-]+)`?",
        baseline,
    )
    if not match:
        return None
    value = match.group(1).lower()
    return value if value in LOCKFILE_STATUSES else None


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
    if path_id in NON_CUTOVER_PATH_IDS:
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
    if axes.get("topology_axis") == "host-port" and axes.get("runtime_axis") == "compat":
        result.error(
            "topology_axis=host-port forbids runtime_axis=compat "
            "(compat is not a primary host-port path)"
        )
    if path_id == "compat-big-bang" and axes.get("topology_axis") == "host-port":
        result.error(
            "compat-big-bang cannot pair with topology_axis=host-port; "
            "use host-port-direct"
        )


def validate_host_port_baseline(
    baseline: str, path_id: str | None, axes: dict[str, str], result: ReportResult
) -> None:
    is_host_port = path_id == "host-port-direct" or axes.get("topology_axis") == "host-port"
    if not is_host_port:
        return
    for marker in HOST_PORT_REQUIRED_MARKERS:
        match = re.search(
            rf"(?im)^\s*[-*]?\s*`?{re.escape(marker)}`?\s*`?(.+?)\s*$",
            baseline,
        )
        if not match:
            result.error(f"§1 host-port requires concrete {marker} value")
            continue
        value = match.group(1).strip().strip("`")
        if not value or value.lower() in CHECKLIST_PLACEHOLDERS | {"tbd", "todo", "n/a", "待定"}:
            result.error(f"§1 host-port requires concrete {marker} value")
            continue
        if marker == "forbid_source_mutation:" and value.lower() not in {"yes", "true"}:
            result.error("§1 forbid_source_mutation must be yes for host-port")
    if re.search(r"(?i)\bvue-compat\b", baseline) and re.search(
        r"(?i)primary\s+recipe|主路径|主配方", baseline
    ):
        result.error("§1 must not name vue-compat as primary recipe for host-port")


def extract_recipe_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for token in RECIPE_ID_RE.findall(text or ""):
        lowered = token.lower()
        if lowered in RECIPE_SKIP or lowered in {"http", "https"}:
            continue
        ids.add(token)
    return ids


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
                "recipe": recipe,
                "note": note,
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


def validate_validation_matrix(
    block: str, subsystems: list[dict[str, str]], result: ReportResult
) -> None:
    rows, errors = parse_table(block, VALIDATION_HEADERS)
    for error in errors:
        result.error(f"§8 {error}")
    if not rows:
        result.error("§8 validation matrix must contain at least one data row")
        return
    covered: set[str] = set()
    for recipe, command, failure, evidence in rows:
        if any(
            not cell or cell.strip().lower() in VALIDATION_PLACEHOLDERS
            for cell in (recipe, command, failure, evidence)
        ):
            result.error(f"§8 row has blank or placeholder cells: {recipe!r}")
            continue
        covered.update(extract_recipe_ids(recipe))
    required: set[str] = set()
    for row in subsystems:
        if row.get("scope_status") != "in_scope":
            continue
        recipe = row.get("recipe", "")
        if recipe.strip() in {"—", "-", "–"}:
            continue
        required.update(extract_recipe_ids(recipe))
    missing = sorted(required - covered)
    if missing:
        result.error(
            "§8 missing implementation-stage rows for named recipes: "
            + ", ".join(missing)
        )


def parse_record(
    path: Path,
    expected_unit: str,
    expected_status: str,
    expected_fork_tokens: set[str],
    result: ReportResult,
) -> None:
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
    fork_answer = values.get("分叉人工答复", "")
    observed_fork_tokens = set(CONFIRM_TOKEN_RE.findall(fork_answer))
    if expected_status == "decided" and expected_fork_tokens:
        if observed_fork_tokens != expected_fork_tokens:
            result.error(
                f"{path.name}: 分叉人工答复 tokens {sorted(observed_fork_tokens)!r} "
                f"must equal report-derived tokens {sorted(expected_fork_tokens)!r}"
            )
    elif observed_fork_tokens:
        result.error(
            f"{path.name}: 分叉人工答复 must be '—' when no decided fork is open"
        )
    elif fork_answer and fork_answer.strip().lower() not in NO_FORK_ANSWER_VALUES:
        result.error(
            f"{path.name}: 分叉人工答复 must contain exact confirm tokens or '—'"
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
    node_matrix = parse_node_matrix(baseline, result)
    parse_baseline_anchor_fields(baseline, result)
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
    validate_host_port_baseline(baseline, recommended_path, axes, result)
    if recommended_path == "host-port-direct" and re.search(
        r"(?i)@vue/compat|vue-compat", path_block
    ) and not re.search(r"(?i)(禁|forbid|非主|not\s+primary|不作为主)", path_block):
        result.error(
            "§3 host-port-direct must not promote @vue/compat / vue-compat "
            "without an explicit non-primary ban"
        )

    gap_block = sections.get("未决问题与证据缺口", "")
    validate_manual_gap_checklist(gap_block, result)

    entry_mode = status.get("entry_mode") or "upgrade"
    validate_residual_audit(
        entry_mode, recommended_path, sections.get("分层影响分析", ""), result
    )

    subsystems = parse_subsystems(sections.get("子系统影响清单", ""), result)
    validate_ui_behavior_contract(subsystems, sections.get("分层影响分析", ""), result)
    validate_ui_cutover_staging(subsystems, path_block, result)
    if entry_mode != "residual-audit":
        validate_default_path_deviation(axes, path_block, result)
    validate_validation_matrix(sections.get("验证矩阵", ""), subsystems, result)
    queue = parse_queue(sections.get("确认队列", ""), result)
    subsystem_fork_tokens = validate_subsystem_forks(
        subsystems,
        queue,
        entry_mode,
        path_block,
        inventory_rows,
        status.get("analysis_status", ""),
        status.get("batch_implementation_gate", ""),
        result,
    )
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
    node_status = node_matrix.get("node_compatibility_status", "").lower()
    target_node_requirement = node_matrix.get("target_node_requirement", "")
    target_node_unknown = bool(
        re.search(r"(?i)\bunknown\b|未知|未定|未解析", target_node_requirement)
    )
    if (
        analysis == "complete"
        and recommended_path not in NON_CUTOVER_PATH_IDS
        and (target_node_unknown or node_status == "unknown")
    ):
        result.error(
            "complete analysis requires a resolved target_node_requirement and "
            "node_compatibility_status"
        )
    if gate == "ready" and node_status in {"conflict", "unknown"}:
        result.error(
            "batch_implementation_gate=ready forbidden for Node status conflict/unknown"
        )
    if node_status == "upgrade-required":
        build = next((row for row in subsystems if row["id"] == "build"), None)
        if (
            not build
            or build["risk"] not in HIGH_BLOCKER_RISKS
            or build["required_for_path"] != "yes"
        ):
            result.error(
                "node_compatibility_status=upgrade-required requires §4 build risk "
                "high|blocker and required_for_path=yes"
            )
    host_lock = parse_named_lockfile_status(baseline, "host_lockfile_status")
    source_lock = parse_named_lockfile_status(baseline, "source_lockfile_status")
    is_host_port = (
        recommended_path == "host-port-direct"
        or axes.get("topology_axis") == "host-port"
    )
    if is_host_port:
        if host_lock is None:
            result.error(
                "§1 host-port requires host_lockfile_status: present|absent|unparsed"
            )
        if source_lock is None:
            result.error(
                "§1 host-port requires source_lockfile_status: present|absent|unparsed"
            )
        if host_lock and lock_status and host_lock != lock_status:
            result.error(
                "§1 host-port lockfile_status must equal host_lockfile_status "
                f"(got lockfile_status={lock_status!r}, host_lockfile_status={host_lock!r})"
            )
        if gate == "ready" and (host_lock or lock_status) != "present":
            result.error(
                "batch_implementation_gate=ready requires host_lockfile_status=present "
                "(host-port uses B lock, not A)"
            )
    elif gate == "ready" and lock_status != "present":
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
            # Every unit that entered §7 needs a record. Optional medium rows are
            # not forced into the queue, but once queued their decision evidence
            # must not disappear merely because their risk is below High.
            required_units = list(queue)
            for row in required_units:
                prefix = "migration-path" if row["type"] == "path" else "subsystem"
                record_path = records_dir / f"{prefix}__{row['id']}.md"
                parse_record(
                    record_path,
                    row["unit"],
                    row["status"],
                    subsystem_fork_tokens.get(row["id"], set())
                    if row["type"] == "subsystem"
                    else set(),
                    result,
                )
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
        if len(parts) != 3 or parts[0] not in {"workspace", "inventory", "host-port"} or not re.fullmatch(
            r"[A-Za-z0-9._-]+__variant-[A-Za-z0-9._-]+__scope-[A-Za-z0-9._-]+", parts[1]
        ):
            result.error(f"invalid multi-batch report layout: {relative}")
        if relative not in text and parts[1] not in text:
            result.error(f"{BATCH_INDEX_NAME} does not reference batch report: {relative}")


def declared_file_matches(value: str, expected: Path) -> bool:
    text = str(value).strip().strip("`").replace("\\", "/")
    if not text or text in {".", "./"}:
        return False
    target = expected.resolve()
    candidate = Path(text)
    try:
        if candidate.is_absolute():
            return candidate.resolve() == target
        return (Path.cwd() / candidate).resolve() == target
    except OSError:
        return False


def validate_overlap_rows(
    summary: dict, validation_block: str, result: "ReportResult"
) -> None:
    """A declared codemod intersection needs its own §8 row.

    Two recipes that rewrite the same call sites can each be individually
    correct and jointly wrong. Either recipe's own validation row passes while
    the composed result is broken, so the pair has to be validated as a pair.
    """
    constraints = summary.get("recipe_constraints")
    if not isinstance(constraints, list):
        return
    rows, _ = parse_table(validation_block, VALIDATION_HEADERS)
    row_recipe_sets = [set(extract_recipe_ids(row[0])) for row in rows if row]
    pairs: set[tuple[str, str]] = set()
    for item in constraints:
        if not isinstance(item, dict):
            continue
        recipe_id = str(item.get("id", "")).strip()
        overlaps = item.get("overlaps_with")
        if not recipe_id or not isinstance(overlaps, list):
            continue
        for other in overlaps:
            other_id = str(other).strip()
            if other_id and other_id != recipe_id:
                pairs.add(tuple(sorted((recipe_id, other_id))))
    for left, right in sorted(pairs):
        if not any({left, right} <= ids for ids in row_recipe_sets):
            result.error(
                f"§8 missing an intersection row for overlapping recipes "
                f"{left} × {right}; each recipe's own row can pass while the "
                "composed rewrite is broken"
            )


def validate_bundle_artifacts(report: Path, result: ReportResult) -> None:
    """Validate the standalone bundle and report/summary/inventory agreement."""
    bundle_dir = report.parent
    summary_path = bundle_dir / SUMMARY_NAME
    inventory_path = bundle_dir / INVENTORY_NAME
    if not summary_path.is_file():
        result.error(f"bundle missing required {SUMMARY_NAME}")
    if not inventory_path.is_file():
        result.error(f"bundle missing required {INVENTORY_NAME}")
    if not summary_path.is_file():
        return

    raw = summary_path.read_bytes()
    try:
        summary = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        result.error(f"{SUMMARY_NAME} is not valid UTF-8 JSON: {exc}")
        return
    for error in validate_summary(summary, len(raw)):
        result.error(f"{SUMMARY_NAME}: {error}")
    if not isinstance(summary, dict):
        return

    report_text = visible_markdown(report.read_text(encoding="utf-8"))
    status, _ = parse_status(report_text)
    sections, _ = split_sections(report_text)
    path_match = RECOMMENDED_PATH_RE.search(sections.get("推荐迁移路径", ""))
    report_path_id = path_match.group(1) if path_match else None
    axis_values = {}
    path_block = sections.get("推荐迁移路径", "")
    for marker, _allowed in AXIS_MARKERS:
        match = re.search(rf"(?im)^\s*[-*]?\s*{re.escape(marker)}\s*`?([A-Za-z0-9_-]+)`?", path_block)
        if match:
            axis_values[marker[:-1]] = match.group(1)
    lock_match = re.search(
        r"(?im)^\s*[-*]?\s*`?lockfile_status`?\s*[:：]\s*`?(present|absent|unparsed)`?",
        sections.get("基线与假设", ""),
    )
    report_lock = lock_match.group(1) if lock_match else None

    comparisons = {
        "analysis_status": status.get("analysis_status"),
        "decision_status": status.get("decision_status"),
        "batch_implementation_gate": status.get("batch_implementation_gate"),
        "visual_acceptance_required": status.get("visual_acceptance_required"),
        "recommended_path": report_path_id,
        "lockfile_status": report_lock,
        "entry_mode": status.get("entry_mode"),
    }
    for field_name, report_value in comparisons.items():
        if report_value is not None and summary.get(field_name) != report_value:
            result.error(
                f"{SUMMARY_NAME} {field_name}={summary.get(field_name)!r} "
                f"does not match report {report_value!r}"
            )

    validate_overlap_rows(summary, sections.get("验证矩阵", ""), result)

    summary_axes = summary.get("axes")
    if isinstance(summary_axes, dict):
        report_axes = {
            "runtime": axis_values.get("runtime_axis"),
            "build": axis_values.get("build_axis"),
            "topology": axis_values.get("topology_axis"),
        }
        if summary_axes != report_axes:
            result.error(
                f"{SUMMARY_NAME} axes={summary_axes!r} does not match report {report_axes!r}"
            )

    subsystem_rows, _ = parse_table(
        sections.get("子系统影响清单", ""), SUBSYSTEM_HEADERS
    )
    report_recipes: set[str] = set()
    for _sid, scope, _risk, _readiness, _required, recipe, _note in subsystem_rows:
        if scope == "in_scope":
            report_recipes.update(extract_recipe_ids(recipe))
    if re.search(
        r"(?m)^###\s+ui_behavior_contract\s*$", sections.get("分层影响分析", "")
    ) and not isinstance(summary.get("ui_behavior_contract"), dict):
        result.error(
            f"report declares §5 ui_behavior_contract but {SUMMARY_NAME} carries no "
            "ui_behavior_contract.required_assertions for downstream planning"
        )

    summary_recipe_values = summary.get("named_recipes")
    if isinstance(summary_recipe_values, list) and all(
        isinstance(item, str) for item in summary_recipe_values
    ):
        summary_recipes = set(summary_recipe_values)
        if summary_recipes != report_recipes:
            result.error(
                f"{SUMMARY_NAME} named_recipes={sorted(summary_recipes)!r} "
                f"does not match report subsystem recipes={sorted(report_recipes)!r}"
            )

    if not declared_file_matches(summary.get("report_path", ""), report):
        result.error(f"{SUMMARY_NAME} report_path does not resolve to {report}")
    if inventory_path.is_file() and not declared_file_matches(
        summary.get("inventory_path", ""), inventory_path
    ):
        result.error(f"{SUMMARY_NAME} inventory_path does not resolve to {inventory_path}")
    if not declared_file_matches(status.get("summary_path", ""), summary_path):
        result.error(f"report summary_path does not resolve to {summary_path}")

    declared_records = summary.get("decision_records")
    if isinstance(declared_records, list) and all(
        isinstance(item, str) for item in declared_records
    ):
        actual_records = sorted((bundle_dir / "decision-records").glob("*.md"))
        missing_from_manifest = [
            path
            for path in actual_records
            if not any(declared_file_matches(item, path) for item in declared_records)
        ]
        unresolved_manifest = [
            item
            for item in declared_records
            if not any(declared_file_matches(item, path) for path in actual_records)
        ]
        if missing_from_manifest or unresolved_manifest:
            details = []
            if missing_from_manifest:
                details.append(
                    "unlisted=" + ",".join(path.name for path in missing_from_manifest)
                )
            if unresolved_manifest:
                details.append("missing=" + ",".join(unresolved_manifest))
            result.error(
                f"{SUMMARY_NAME} decision_records does not match decision-records/: "
                + "; ".join(details)
            )

    if inventory_path.is_file():
        try:
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            result.error(f"{INVENTORY_NAME} is not valid UTF-8 JSON: {exc}")
        else:
            if not isinstance(inventory, dict):
                result.error(f"{INVENTORY_NAME} root must be an object")
            else:
                if inventory.get("lockfile_status") not in LOCKFILE_STATUSES:
                    result.error(
                        f"{INVENTORY_NAME} lockfile_status must be one of {sorted(LOCKFILE_STATUSES)}"
                    )
                elif report_lock and inventory.get("lockfile_status") != report_lock:
                    result.error(
                        f"{INVENTORY_NAME} lockfile_status={inventory.get('lockfile_status')!r} "
                        f"does not match report {report_lock!r}"
                    )
                baseline_block = sections.get("基线与假设", "")
                revision_match = re.search(
                    r"(?im)^\s*[-*]?\s*`?repo_revision`?\s*[:：]\s*(.+?)\s*$",
                    baseline_block,
                )
                inventory_revision = inventory.get("repo_revision")
                if (
                    isinstance(inventory_revision, str)
                    and inventory_revision
                    and revision_match
                    and inventory_revision not in revision_match.group(1)
                ):
                    result.error(
                        f"{INVENTORY_NAME} repo_revision={inventory_revision!r} does not "
                        f"match report §1 repo_revision {revision_match.group(1)!r} "
                        "(stale analysis packet)"
                    )
                report_entry_mode = status.get("entry_mode") or "upgrade"
                if (
                    inventory.get("vue_major") == "3"
                    and status.get("analysis_status") == "complete"
                    and report_entry_mode != "residual-audit"
                ):
                    result.error(
                        f"{INVENTORY_NAME} vue_major=3: workspace is already on Vue 3; "
                        "a complete packet must set status entry_mode: residual-audit "
                        "or stay blocked instead of describing a Vue2 baseline"
                    )
                if (
                    report_entry_mode == "residual-audit"
                    and inventory.get("vue_major") not in (None, "", "3")
                ):
                    result.error(
                        f"entry_mode=residual-audit but {INVENTORY_NAME} "
                        f"vue_major={inventory.get('vue_major')!r}: a residual audit "
                        "only applies to an already-Vue3 workspace"
                    )


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
        result = validate_report(root_report)
        validate_bundle_artifacts(root_report, result)
        return [result]
    if not nested_reports:
        result = ReportResult(path=evidence_dir)
        result.error(f"no {REPORT_NAME} under evidence directory")
        return [result]
    index_result = ReportResult(path=evidence_dir / BATCH_INDEX_NAME)
    validate_batch_index(evidence_dir, nested_reports, index_result)
    nested_results = []
    for report in nested_reports:
        result = validate_report(report)
        validate_bundle_artifacts(report, result)
        nested_results.append(result)
    return [index_result] + nested_results


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

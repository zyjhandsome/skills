#!/usr/bin/env python3
"""Generate evidence-backed frontend dependency upgrade impact reports."""

from __future__ import annotations

import argparse
import concurrent.futures
import contextvars
import csv
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from upgrade_lockfiles import (  # noqa: E402  (sibling module; scripts/ is added above)
    LOCK_NAMES,
    DependencyGraph,
    LockSnapshot,
    build_dependency_graph,
    detect_lock,
    parse_lock,
    unquote_yaml,
)
from upgrade_alternatives import (  # noqa: E402
    ALTERNATIVE_RANK_SIGNALS,
    DISPOSITION_OPTIONS,
    REFACTOR_STAGES,
    REPLACEMENT_MAP_REVIEWED,
    RESEARCH_CRITERIA,
    curated_native_routes,
    curated_replacement_packages,
    curated_replacements,
)
from upgrade_semver import (  # noqa: E402
    VERSION_RE,
    classify_change,
    clean_version,
    compare_versions,
    preferred_version as preferred_node_version,
    range_satisfies as semver_satisfies,
    range_witnesses as node_constraint_candidates,
    semver_key,
)


DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)
SPECIAL_FIELDS = ("overrides", "resolutions", "peerDependenciesMeta")
CRITICAL_RE = re.compile(r"(?:auth|login|permission|role|payment|checkout|order|upload|token)", re.I)
SHARED_RE = re.compile(r"(?:common|shared|components?|utils?|services?|request|client|router|store)", re.I)
TEST_RE = re.compile(r"(?:^|/)(?:__tests__/|test/|tests/)|\.(?:test|spec)\.[^.]+$", re.I)
TEXT_EXTENSIONS = {
    ".astro", ".cjs", ".css", ".cts", ".html", ".js", ".json", ".jsx",
    ".less", ".mjs", ".mts", ".scss", ".sass", ".svelte", ".ts", ".tsx",
    ".vue", ".yaml", ".yml",
}
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".next", ".nuxt", ".output", ".turbo", ".vite",
    "build", "coverage", "dist", "node_modules", "out",
}
CONFIG_FILE_HINTS = (
    "babel.config", "eslint.config", "jest.config", "next.config", "nuxt.config",
    "package.json", "playwright.config", "postcss.config", "tailwind.config",
    "tsconfig", "vite.config", "vitest.config", "webpack.config",
)
TOOLCHAIN_PACKAGES = {
    "@angular-devkit/build-angular", "@angular/cli", "@babel/core", "@nestjs/cli",
    "@playwright/test", "@remix-run/dev", "@sveltejs/kit", "@swc/core",
    "@vue/cli-service", "astro", "cypress", "eslint", "esbuild", "gatsby", "gulp",
    "jest", "mocha", "next", "nuxt", "nx", "parcel", "playwright", "prettier",
    "react-scripts", "rollup", "storybook", "stylelint", "tailwindcss", "ts-node",
    "tsup", "tsx", "turbo", "typescript", "vite", "vitest", "vue-tsc", "webpack",
    "webpack-cli",
}
REPORT_SECTION_TITLES = {
    "Upgrade Summary": "升级摘要",
    "Release Notes And Changelog Evidence": "发布说明与变更日志证据",
    "Breaking Changes And Migration Notes": "破坏性变更与迁移说明",
    "Dependency Changes": "依赖变化",
    "Diff Evidence Used": "使用的差异证据",
    "Code References": "代码引用",
    "Detailed Code Modification Points": "详细代码修改候选",
    "Business Impact": "业务影响",
    "Technical Risks": "技术风险",
    "Test Scope": "测试范围",
    "Rollout And Rollback": "发布与回滚",
    "Human Confirmation Queue": "人工确认队列",
    "Conclusion": "结论",
}
REQUIRED_HEADINGS = tuple(REPORT_SECTION_TITLES)
# End-of-life dates from the official Node.js release schedule (nodejs/Release). This is a
# reviewed snapshot, not a live feed: majors outside the table stay `unknown` instead of being
# guessed, and NODE_SCHEDULE_REVIEWED is reported so a stale table is visible to the reader.
NODE_EOL_DATES = {
    12: "2022-04-30", 13: "2020-06-01", 14: "2023-04-30", 15: "2021-06-01",
    16: "2023-09-11", 17: "2022-06-01", 18: "2025-04-30", 19: "2023-06-01",
    20: "2026-04-30", 21: "2024-06-01", 22: "2027-04-30", 23: "2025-06-01",
    24: "2028-04-30", 25: "2026-06-01",
}
NODE_SCHEDULE_REVIEWED = "2026-07-25"
NODE_EOL_WARNING_WINDOW_DAYS = 90
CHANGE_SCORES = {"same": 0, "patch": 1, "minor": 3, "added": 3, "unknown": 3, "major": 5, "removed": 5}
# Blast radius of the package family, before it is weighted by how large the version change is.
DEPENDENCY_TYPE_BASE = {
    "runtime": 1, "dev-tooling": 1,
    "typescript": 2, "style": 2, "test": 2,
    "state": 4, "dom-runtime": 4,
    "framework": 5, "router": 5, "ui": 5, "request": 5, "build": 5,
}
# base blast radius -> (trivial change, moderate change, breaking change)
DEPENDENCY_TYPE_BY_CHANGE = {
    5: (1, 3, 5),
    4: (1, 3, 4),
    2: (1, 2, 2),
    1: (1, 1, 1),
}
TRIVIAL_CHANGES = frozenset({"same", "patch"})
BREAKING_CHANGES = frozenset({"major", "removed", "replacement"})
RISK_FACTORS = (
    "version_change",
    "dependency_type",
    "usage_scope",
    "business_criticality",
    "lockfile_change",
    "test_coverage_gap",
    "peer_compatibility",
)
RISK_LOW_MAX = 6
RISK_MEDIUM_MAX = 14
NODE_SUPPORT_STATUSES = ("supported", "approaching-eol", "eol", "unknown")
NODE_CONSTRAINT_KINDS = (
    "runtime-pin", "project-engine", "toolchain-engine", "dependency-engine",
    "target-package-engine", "ci-node-version", "container-node-image",
)
DECLARATION_CATEGORY = "Dependency declaration/config"
UNMAPPED_FLOW = "需要补充路由/调用方映射"
UNRATED = "待评估"
CODE_CATEGORY_TITLES = {
    DECLARATION_CATEGORY: "依赖声明/配置",
    "Direct package usage": "直接包用法",
    "Vue app entry": "Vue 应用入口",
    "Vue reactivity": "Vue 响应式",
    "React root API": "React 根节点 API",
    "State manager API": "状态管理 API",
    "Axios client API": "Axios 客户端 API",
    "Axios serialization/upload": "Axios 序列化/上传",
    "UI component usage": "UI 组件用法",
    "Build configuration": "构建配置",
}
# An open-target package is triaged into exactly one primary track. Other routes stay
# visible as alternates; the track only says which one this run's evidence points at.
PRIMARY_TRACKS = {
    "remove": "删除",
    "replace": "替换",
    "native-refactor": "原生改造",
    "handle-parent": "处置父包",
    "fix-phantom": "修复幽灵依赖",
    "pending-removal-evidence": "先补删除证据",
    "proceed-exact": "确认推进精确升级",
}
PROCEED_EXACT_TRACK = "proceed-exact"
BATCH_IMPLEMENTATION_GATES = ("frozen", "ready")
# Where the package comes from. This decides which routes are even possible: a package
# the workspace never declared cannot be "removed" from the manifest.
PROVENANCE_KINDS = {
    "direct": "直接依赖（manifest 已声明，无其他包引入）",
    "both": "直接依赖 + 被其他包引入（摘除声明后仍会以传递依赖存在）",
    "phantom": "幽灵依赖（manifest 未声明但代码在用）",
    "transitive": "传递依赖（manifest 未声明，仅由父包引入）",
    "unknown": "来源未确认",
}
PARENT_CHAIN_LIMIT = 5
NODE_BUILTINS = frozenset({
    "assert", "buffer", "child_process", "cluster", "console", "crypto", "dns", "events",
    "fs", "http", "http2", "https", "module", "net", "os", "path", "perf_hooks", "process",
    "querystring", "readline", "stream", "string_decoder", "timers", "tls", "tty", "url",
    "util", "v8", "vm", "worker_threads", "zlib",
})
CONFIRMATION_STATUSES = ("ready", "blocked", "decided")
DECISION_RECORD_STATUSES = ("confirmed", "invalidated", "unknown-package")
# Open-target disposition selected in the decision file (analysis endpoint — not implementation).
DISPOSITION_SELECTED_ACTION = "disposition-selected"
# Exact-upgrade proceed confirmation recorded (still analysis endpoint — not implementation).
PROCEED_SELECTED_ACTION = "proceed-selected"
DEFERRED_ACTION = "deferred"
PARENT_DECISION_SEPARATOR = "<-"
# Deterministic size grading for a first-party rewrite, from this run's own scan counts.
REFACTOR_SCALE_SMALL_FILES = 2
REFACTOR_SCALE_SMALL_POINTS = 5
REFACTOR_SCALE_MEDIUM_FILES = 10
REFACTOR_SCALE_MEDIUM_POINTS = 30
REFACTOR_SCALES = ("S", "M", "L")
ANALYSIS_MODES = {
    "exact-upgrade",
    "auto-assess",
    "target-discovery",
    "removal-assessment",
    "compliance-assessment",
    "replacement-discovery",
}
COMPLIANCE_STATUSES = {"eligible", "ineligible", "unknown"}
REQUIRED_ALTERNATIVE_CRITERIA = {
    "node",
    "framework",
    "peer",
    "security",
    "license",
    "maintenance",
}
SELECTION_STATUSES = {"selected", "needs_explicit_choice", "not_applicable"}
REMOVAL_STATUSES = {
    "safe_removal_candidate",
    "requires_migration",
    "not_viable",
    "uncertain",
    "not_assessed",
}
REMOVAL_COVERAGE_AREAS = {
    "business",
    "runtime",
    "dynamic",
    "build",
    "tooling",
    "peer",
    "transitive",
}
EVIDENCE_DIMENSIONS = (
    "registry",
    "repository",
    "release",
    "changelog",
    "migration",
    "compatibility",
    "security",
    "support",
    "license",
)
CHANGELOG_FILENAMES = (
    "CHANGELOG.md", "changelog.md", "CHANGELOG", "changelog",
    "CHANGES.md", "changes.md", "History.md", "HISTORY.md", "history.md",
    "CHANGELOG.en-US.md", "CHANGELOG.zh-CN.md",
)
_HTTP_MEMORY_CACHE: dict[str, str | None] = {}
_HTTP_CACHE_LOCK = threading.Lock()
_HTTP_CACHE_DIR: Path | None = None
_HTTP_CACHE_TTL_SECONDS = 21_600


@dataclass
class Upgrade:
    package: str
    from_version: str
    to_version: str
    dependency_type: str = ""
    reason: str = ""
    source: str = "explicit"
    intent: str = "exact-upgrade"


@dataclass
class VersionNote:
    version: str
    published: str = ""
    change_type: str = ""
    release_notes: str = ""
    changelog: str = ""
    sources: list[str] = field(default_factory=list)
    evidence_status: str = "partial"
    release_status: str = "missing"
    changelog_status: str = "missing"
    repository_url: str = ""
    repository_source: str = ""
    repository_validation: str = "unknown"


@dataclass
class OfficialSource:
    kind: str
    url: str
    status: str = "candidate"
    title: str = ""
    version: str = ""
    reason: str = ""


@dataclass
class ManifestPackage:
    package: str
    field: str = ""
    spec: str = ""
    # Range a `catalog:` / `catalog:<name>` protocol spec resolves to in pnpm-workspace.yaml.
    catalog_spec: str = ""
    catalog_source: str = ""


@dataclass
class ManifestSnapshot:
    path: str = ""
    package_manager: str = ""
    engines: dict[str, Any] = field(default_factory=dict)
    volta: dict[str, Any] = field(default_factory=dict)
    pnpm: dict[str, Any] = field(default_factory=dict)
    packages: dict[str, ManifestPackage] = field(default_factory=dict)
    special_entries: list[str] = field(default_factory=list)


@dataclass
class CodeModificationPoint:
    package: str
    file: str
    line: int
    category: str
    current_usage: str
    upstream_reason: str
    recommended_change: str
    validation: str
    priority: str = "P1"
    confidence: str = "medium"


@dataclass
class RiskAssessment:
    factors: dict[str, int] = field(default_factory=dict)
    total: int = 0
    automatic_level: str = "Medium"
    final_level: str = "Medium"
    rationale: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)


@dataclass
class TargetCandidate:
    package: str
    version: str
    candidate_type: str
    published: str = ""
    peer_dependencies: dict[str, str] = field(default_factory=dict)
    engines: dict[str, str] = field(default_factory=dict)
    rationale: str = ""
    compatibility: str = ""
    compliance_and_maintenance: str = ""
    migration_cost: str = ""
    validation_scope: str = ""
    rollback_difficulty: str = ""
    source: str = ""
    confidence: str = "medium"
    compliance_status: str = "unknown"
    criteria_checked: list[str] = field(default_factory=list)
    disqualifiers: list[str] = field(default_factory=list)
    evidence_urls: list[str] = field(default_factory=list)
    checked_at: str = ""


@dataclass
class AlternativeCandidate:
    package: str
    version: str
    rationale: str = ""
    compatibility: str = ""
    compliance_and_maintenance: str = ""
    migration_cost: str = ""
    validation_scope: str = ""
    rollback_difficulty: str = ""
    source: str = ""
    confidence: str = "low"
    compliance_status: str = "unknown"
    criteria_checked: list[str] = field(default_factory=list)
    disqualifiers: list[str] = field(default_factory=list)
    evidence_urls: list[str] = field(default_factory=list)
    checked_at: str = ""
    # `analysis-evidence` outranks `curated-map`: only the former carries a human verdict.
    origin: str = "analysis-evidence"
    peer_dependencies: dict[str, Any] = field(default_factory=dict)
    engines: dict[str, Any] = field(default_factory=dict)
    published: str = ""
    license: str = ""
    deprecated: bool = False
    # fits | unknown | conflicts, against the project's Node and declared peers.
    constraint_fit: str = "unknown"
    fallback_version: str = ""
    conservative_version: str = ""
    rank: int = 0
    rank_signals: list[str] = field(default_factory=list)


@dataclass
class DispositionOption:
    option: str
    title: str
    applicability: str
    required_evidence: str
    availability: str = "needs-research"
    detail: str = ""


@dataclass
class ParentEdge:
    """A package that pulls in the analysed package, and what it asks for."""

    package: str
    version: str
    requirement: str
    latest_stable: str = ""
    # still-depends | dropped | unknown — does the parent's newest stable still pull it in?
    fix_available: str = "unknown"
    fix_note: str = ""
    target_compatible_version: str = ""
    target_compatible_requirement: str = ""


@dataclass
class ProvenanceAssessment:
    """direct / both / phantom / transitive / unknown, plus the evidence behind it."""

    kind: str = "unknown"
    declared_field: str = ""
    used_in_code: bool = False
    parents: list[ParentEdge] = field(default_factory=list)
    chains: list[str] = field(default_factory=list)
    chain_total: int = 0
    override_version: str = ""
    override_breaks: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


@dataclass
class RefactorAction:
    """One call site and how it would be rewritten without the dependency."""

    file: str
    line: int
    category: str
    current_usage: str
    approach: str
    parity_risk: str
    validation: str
    confidence: str = "low"


@dataclass
class RefactorPlan:
    """First-party replacement route: used when no compliant package option exists."""

    status: str = "needs-research"  # established | needs-research
    native_routes: list[str] = field(default_factory=list)
    capabilities_to_rebuild: list[str] = field(default_factory=list)
    call_site_groups: list[str] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)
    validation_scope: str = ""
    unknowns: list[str] = field(default_factory=list)
    actions: list[RefactorAction] = field(default_factory=list)
    parity_checks: list[str] = field(default_factory=list)
    impact_surface: list[str] = field(default_factory=list)
    scale: str = ""
    scale_basis: str = ""
    rollback: str = ""


@dataclass
class ConfirmationOption:
    option_id: str
    label: str
    detail: str = ""


@dataclass
class ConfirmationQuestion:
    """One package, one question. The Agent asks these verbatim, in order."""

    package: str
    track: str
    status: str = "ready"  # ready | blocked | decided
    prompt: str = ""
    options: list[ConfirmationOption] = field(default_factory=list)
    blocked_reason: str = ""
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class HumanDecision:
    """A recorded selection. A selection is not an implementation approval."""

    package: str
    track: str = ""
    choice: str = ""
    selected_package: str = ""
    selected_version: str = ""
    rationale: str = ""
    decided_at: str = ""
    source: str = "confirmation-queue"
    status: str = "confirmed"
    invalidation_reason: str = ""


@dataclass
class RemovalAssessment:
    status: str = "not_assessed"
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    confidence: str = "low"
    coverage_checked: list[str] = field(default_factory=list)


@dataclass
class NodeConstraint:
    source: str
    requirement: str
    kind: str
    authority: str = "authoritative"
    path: str = ""


@dataclass
class NodeRuntimeAssessment:
    status: str = "unknown"
    execution_readiness: str = "blocked"
    current_host_node: str = ""
    current_host_node_path: str = ""
    project_constraints: list[NodeConstraint] = field(default_factory=list)
    observed_runtime_evidence: list[NodeConstraint] = field(default_factory=list)
    available_managers: list[str] = field(default_factory=list)
    installed_versions: dict[str, list[str]] = field(default_factory=dict)
    compatible_installed_versions: list[str] = field(default_factory=list)
    selected_project_node: str = ""
    selected_manager: str = ""
    selected_node_support: str = "unknown"
    recommended_strategy: str = "read-only-analysis"
    restoration_plan: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    installation_guidance: list[str] = field(default_factory=list)


@dataclass
class PackageReport:
    upgrade: Upgrade
    package_url: str
    repository_url: str = ""
    repository_directory: str = ""
    repository_source_version: str = ""
    repository_validation_status: str = "unknown"
    repository_lineage: dict[str, str] = field(default_factory=dict)
    homepage: str = ""
    change_type: str = "unknown"
    notes: list[VersionNote] = field(default_factory=list)
    target_peer_dependencies: dict[str, str] = field(default_factory=dict)
    target_peer_dependencies_meta: dict[str, Any] = field(default_factory=dict)
    target_engines: dict[str, str] = field(default_factory=dict)
    evidence_completeness: str = "partial"
    evidence_dimensions: dict[str, str] = field(
        default_factory=lambda: {dimension: "missing" for dimension in EVIDENCE_DIMENSIONS}
    )
    official_sources: list[OfficialSource] = field(default_factory=list)
    peer_compatibility_status: str = "unknown"
    peer_compatibility_conflicts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    manifest_field: str = ""
    manifest_spec: str = ""
    lock_kind: str = "none"
    lock_path: str = ""
    before_lock_version: str = ""
    current_lock_version: str = ""
    after_lock_version: str = ""
    before_lock_versions: list[str] = field(default_factory=list)
    current_lock_versions: list[str] = field(default_factory=list)
    after_lock_versions: list[str] = field(default_factory=list)
    observed_lock_versions: list[str] = field(default_factory=list)
    baseline_status: str = "unknown"
    risk: RiskAssessment = field(default_factory=RiskAssessment)
    analysis_mode: str = "exact-upgrade"
    decision_status: str = "not_needed"
    recommended_action: str = "upgrade"
    target_candidates: list[TargetCandidate] = field(default_factory=list)
    alternative_candidates: list[AlternativeCandidate] = field(default_factory=list)
    disposition_options: list[DispositionOption] = field(default_factory=list)
    refactor_plan: RefactorPlan = field(default_factory=RefactorPlan)
    provenance: ProvenanceAssessment = field(default_factory=ProvenanceAssessment)
    primary_track: str = "not_applicable"
    primary_track_basis: str = ""
    alternate_tracks: list[str] = field(default_factory=list)
    confirmation: ConfirmationQuestion | None = None
    # Full questions for alternate tracks (switch:<track>); Agent asks these verbatim after a switch.
    alternate_questions: list[ConfirmationQuestion] = field(default_factory=list)
    parent_questions: list[ConfirmationQuestion] = field(default_factory=list)
    decision: HumanDecision | None = None
    # available | missing — whether this run produced at least one actionable route.
    option_status: str = "not_applicable"
    # reviewed | curated-only | pending
    research_status: str = "not_applicable"
    removal: RemovalAssessment = field(default_factory=RemovalAssessment)
    decision_required: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    selection_status: str = "not_applicable"
    used_local_upstream_evidence: bool = False
    # Exact-target planning remains analysis-only: commands are emitted but never run.
    exact_upgrade_status: str = "not_applicable"
    exact_upgrade_strategy: str = ""
    target_convergence_status: str = "not_applicable"
    residual_lock_versions: list[str] = field(default_factory=list)
    implementation_commands: list[str] = field(default_factory=list)
    implementation_blockers: list[str] = field(default_factory=list)


@dataclass
class AnalysisBundle:
    title: str
    generated: str
    project_root: str
    status: str
    reports: list[PackageReport]
    code_points: list[CodeModificationPoint]
    scan_warnings: list[str]
    manifest: ManifestSnapshot
    before_lock: LockSnapshot
    current_lock: LockSnapshot
    after_lock: LockSnapshot
    diff_evidence: list[str]
    analysis_status: str = "partial"
    decision_status: str = "not_needed"
    behavior_parity_required: str = "no"
    change_dir: str = ""
    report_output_dir: str = ""
    report_paths: dict[str, str] = field(default_factory=dict)
    pending_human_decisions: list[dict[str, str]] = field(default_factory=list)
    node_runtime: NodeRuntimeAssessment = field(default_factory=NodeRuntimeAssessment)
    importer_resolution: str = "confirmed"
    decision_file: str = ""
    decision_warnings: list[str] = field(default_factory=list)
    # frozen: do not open implementation plans or execute; ready: Stage A clear for Stage B/C handoff.
    batch_implementation_gate: str = "frozen"
    batch_gate_reasons: list[str] = field(default_factory=list)


@dataclass
class FrontendWorkspaceResolution:
    status: str  # confirmed | failed
    manifest_path: str = ""
    reason: str = ""


def infer_dependency_type(package: str, declared_type: str = "") -> str:
    if declared_type and declared_type not in DEPENDENCY_FIELDS:
        return declared_type
    name = package.lower()
    groups = [
        ("dom-runtime", ("jquery", "zepto")),
        ("framework", ("react", "vue", "@angular/core", "svelte", "solid-js", "next", "nuxt")),
        ("router", ("react-router", "vue-router", "@angular/router")),
        ("state", ("redux", "@reduxjs/toolkit", "vuex", "pinia", "zustand", "mobx", "recoil")),
        ("ui", ("antd", "element-ui", "element-plus", "@mui/", "vuetify", "vant", "bootstrap", "chakra", "naive-ui")),
        ("request", ("axios", "graphql-request", "apollo", "@tanstack/query", "react-query", "swr")),
        ("build", ("vite", "webpack", "rollup", "parcel", "babel", "swc", "esbuild", "vue-loader", "@vitejs/")),
        ("typescript", ("typescript", "@types/", "ts-node", "vue-tsc")),
        ("style", ("sass", "less", "postcss", "tailwindcss", "stylus", "autoprefixer")),
        ("test", ("jest", "vitest", "playwright", "cypress", "@testing-library/", "mocha", "karma")),
    ]
    for dependency_type, needles in groups:
        if any(name == needle or needle in name for needle in needles):
            return dependency_type
    return "dev-tooling" if declared_type == "devDependencies" else "runtime"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def flatten_mapping(value: Any, prefix: str = "") -> list[str]:
    rows: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(flatten_mapping(value[key], child))
    else:
        rows.append(f"{prefix}={value}")
    return rows


def read_pnpm_catalogs(project_root: Path) -> dict[str, dict[str, str]]:
    """Read `catalog:` / `catalogs:` ranges from pnpm-workspace.yaml without a YAML dependency."""
    path = project_root / "pnpm-workspace.yaml"
    if not path.is_file():
        return {}
    catalogs: dict[str, dict[str, str]] = {}
    section = ""
    named = ""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return {}
    for raw in lines:
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            section = stripped.rstrip(":") if stripped.endswith(":") else ""
            named = ""
            continue
        if section not in {"catalog", "catalogs"}:
            continue
        if section == "catalogs" and stripped.endswith(":") and ":" not in stripped[:-1]:
            named = stripped[:-1].strip("'\"")
            continue
        key, separator, value = stripped.partition(":")
        if not separator:
            continue
        name = key.strip().strip("'\"")
        spec = unquote_yaml(value.strip())
        if not name or not spec:
            continue
        catalog_name = "default" if section == "catalog" else (named or "default")
        catalogs.setdefault(catalog_name, {})[name] = spec
    return catalogs


def resolve_catalog_spec(spec: str, package: str, catalogs: dict[str, dict[str, str]]) -> tuple[str, str]:
    if not spec.startswith("catalog:"):
        return "", ""
    name = spec.split(":", 1)[1].strip() or "default"
    entry = (catalogs.get(name) or {}).get(package, "")
    source = f"pnpm-workspace.yaml#catalog{'' if name == 'default' else 's.' + name}"
    return entry, source if entry else ""


def load_manifest(path: Path | None, project_root: Path | None = None) -> ManifestSnapshot:
    if path is None or not path.exists():
        return ManifestSnapshot(path=str(path or ""))
    data = read_json(path)
    snapshot = ManifestSnapshot(
        path=str(path.resolve()),
        package_manager=str(data.get("packageManager") or ""),
        engines=data.get("engines") or {},
        volta=data.get("volta") or {},
        pnpm=data.get("pnpm") or {},
    )
    catalogs = read_pnpm_catalogs(project_root or path.parent)
    for field_name in DEPENDENCY_FIELDS:
        for package, spec in (data.get(field_name) or {}).items():
            entry = ManifestPackage(package, field_name, str(spec))
            entry.catalog_spec, entry.catalog_source = resolve_catalog_spec(entry.spec, package, catalogs)
            snapshot.packages[package] = entry
    for field_name in SPECIAL_FIELDS:
        if field_name in data:
            snapshot.special_entries.extend(f"{field_name}.{row}" for row in flatten_mapping(data[field_name]))
    return snapshot


def resolve_frontend_workspace(project_root: Path, args: argparse.Namespace) -> FrontendWorkspaceResolution:
    candidates: list[Path] = []
    if getattr(args, "after_package_json", None):
        candidates.append(Path(args.after_package_json))
    if getattr(args, "before_package_json", None):
        candidates.append(Path(args.before_package_json))
    candidates.append(project_root / "package.json")
    for path in candidates:
        resolved = path if path.is_absolute() else (project_root / path)
        if resolved.is_file():
            return FrontendWorkspaceResolution("confirmed", str(resolved.resolve()), "")
    return FrontendWorkspaceResolution(
        "failed",
        "",
        "未找到 frontend workspace 的 package.json；请显式传入前端目录或 --after-package-json，勿对非前端仓库静默分析。",
    )


def compare_package_json(before_path: Path, after_path: Path) -> list[Upgrade]:
    before = read_json(before_path)
    after = read_json(after_path)
    upgrades: list[Upgrade] = []
    for field_name in DEPENDENCY_FIELDS:
        before_deps = before.get(field_name, {}) or {}
        after_deps = after.get(field_name, {}) or {}
        for package in sorted(set(before_deps) | set(after_deps)):
            before_value = str(before_deps.get(package, ""))
            after_value = str(after_deps.get(package, ""))
            if before_value != after_value:
                upgrades.append(Upgrade(
                    package=package,
                    from_version=clean_version(before_value),
                    to_version=clean_version(after_value),
                    dependency_type=field_name,
                    source="package-json-diff",
                ))
    return upgrades


def compare_special_fields(before_path: Path, after_path: Path) -> list[str]:
    before = read_json(before_path)
    after = read_json(after_path)
    changes: list[str] = []
    for field_name in SPECIAL_FIELDS:
        before_rows = set(flatten_mapping(before.get(field_name) or {}))
        after_rows = set(flatten_mapping(after.get(field_name) or {}))
        for row in sorted(before_rows - after_rows):
            changes.append(f"{field_name} removed/changed: {row}")
        for row in sorted(after_rows - before_rows):
            changes.append(f"{field_name} added/changed: {row}")
    return changes


def parse_upgrade_spec(spec: str) -> Upgrade:
    raw = spec.strip()
    try:
        if "->" in raw:
            package_part, to_version = raw.rsplit("->", 1)
            package, from_version = package_part.rsplit("@", 1)
        elif ".." in raw:
            package_part, versions = raw.rsplit("@", 1)
            from_version, to_version = versions.split("..", 1)
            package = package_part
        else:
            parts = raw.rsplit(":", 2)
            if len(parts) != 3:
                raise ValueError
            package, from_version, to_version = parts
    except ValueError as exc:
        raise ValueError(f"Cannot parse upgrade spec {raw!r}; use package:from:to or package@from..to") from exc
    upgrade = Upgrade(package.strip(), clean_version(from_version), clean_version(to_version), intent="exact-upgrade")
    validate_upgrade(upgrade)
    return upgrade


def validate_upgrade(upgrade: Upgrade) -> None:
    if not upgrade.package:
        raise ValueError("Upgrade package name is required")
    if upgrade.intent not in ANALYSIS_MODES:
        raise ValueError(f"Unsupported analysis intent for {upgrade.package}: {upgrade.intent}")
    if upgrade.intent == "exact-upgrade" and not upgrade.to_version and upgrade.source != "package-json-diff":
        raise ValueError(f"Exact upgrade {upgrade.package} is missing target version")


def load_upgrades_file(path: Path) -> list[Upgrade]:
    if path.suffix.lower() == ".json":
        data = read_json(path)
        rows = data.get("upgrades", []) if isinstance(data, dict) else data
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    upgrades: list[Upgrade] = []
    for row in rows:
        upgrade = Upgrade(
            package=str(row.get("package") or row.get("name") or "").strip(),
            from_version=clean_version(row.get("from") or row.get("from_version") or ""),
            to_version=clean_version(row.get("to") or row.get("to_version") or ""),
            dependency_type=str(row.get("dependency_type") or row.get("type") or ""),
            reason=str(row.get("reason") or ""),
            intent=str(row.get("intent") or row.get("mode") or ("exact-upgrade" if row.get("to") or row.get("to_version") else "auto-assess")),
        )
        validate_upgrade(upgrade)
        upgrades.append(upgrade)
    return upgrades


def collect_upgrades(args: argparse.Namespace) -> list[Upgrade]:
    upgrades = [parse_upgrade_spec(spec) for spec in args.upgrade]
    upgrades.extend(Upgrade(package=package.strip(), from_version="", to_version="", source="assess", intent="auto-assess") for package in args.assess)
    upgrades.extend(Upgrade(package=package.strip(), from_version="", to_version="", source="removal-candidate", intent="removal-assessment") for package in args.removal_candidate)
    if args.upgrades_file:
        upgrades.extend(load_upgrades_file(Path(args.upgrades_file)))
    if args.before_package_json and args.after_package_json:
        upgrades.extend(compare_package_json(Path(args.before_package_json), Path(args.after_package_json)))
    reasons: dict[str, str] = {}
    for item in args.reason:
        package, separator, reason = item.partition("=")
        if not separator or not package.strip() or not reason.strip():
            raise ValueError("--reason must use package=reason")
        reasons[package.strip()] = reason.strip()
    deduped: dict[tuple[str, str, str, str], Upgrade] = {}
    for upgrade in upgrades:
        if upgrade.package in reasons:
            upgrade.reason = reasons[upgrade.package]
        validate_upgrade(upgrade)
        deduped[(upgrade.package, upgrade.from_version, upgrade.to_version, upgrade.intent)] = upgrade
    return list(deduped.values())


def package_url(package: str, version: str = "") -> str:
    quoted = urllib.parse.quote(package, safe="@/")
    suffix = f"/v/{urllib.parse.quote(version, safe='')}" if version else ""
    return f"https://www.npmjs.com/package/{quoted}{suffix}"


def registry_url(package: str) -> str:
    return f"https://registry.npmjs.org/{urllib.parse.quote(package, safe='')}"


REGISTRY_PROBE_URL = "https://registry.npmjs.org/"
GITHUB_PROBE_URL = "https://api.github.com/"


class NetworkReachabilityError(Exception):
    """Public network unreachable; caller must confirm --offline before local readback."""

    def __init__(
        self,
        message: str,
        *,
        registry_reachable: bool,
        github_reachable: bool,
        stage: str = "preflight",
    ) -> None:
        super().__init__(message)
        self.registry_reachable = bool(registry_reachable)
        self.github_reachable = bool(github_reachable)
        self.stage = stage
        self.network_reachability = "unreachable"
        self.awaiting_offline_confirmation = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "network_reachability": self.network_reachability,
            "awaiting_offline_confirmation": self.awaiting_offline_confirmation,
            "registry_reachable": self.registry_reachable,
            "github_reachable": self.github_reachable,
            "stage": self.stage,
            "message": str(self),
        }


def probe_http_reachable(url: str, timeout: int) -> bool:
    """Direct reachability probe — bypasses the HTTP cache so a stale hit cannot fake online.

    An HTTP response (including 401/403/429) means the public path is up; only transport
    failures (DNS/timeout/connection) count as unreachable.
    """
    headers = {
        "User-Agent": "frontend-dependency-upgrade-impact-analysis/2.0",
        "Accept": "*/*",
    }
    try:
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=max(1, int(timeout))) as response:
            status = int(getattr(response, "status", 0) or 0)
            return status > 0
    except urllib.error.HTTPError as exc:
        return exc.code is not None and int(exc.code) > 0
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def assess_network_reachability(timeout: int, *, probe_github: bool | None = None) -> dict[str, Any]:
    """Two-tier public reachability: registry first; GitHub only when registry fails or forced."""
    registry_ok = probe_http_reachable(REGISTRY_PROBE_URL, timeout)
    should_probe_github = bool(probe_github) if probe_github is not None else (not registry_ok)
    github_ok: bool | None = None
    if should_probe_github:
        github_ok = probe_http_reachable(GITHUB_PROBE_URL, timeout)
    if registry_ok:
        status = "reachable"
    elif github_ok:
        status = "partial-github-only"
    elif github_ok is False:
        status = "unreachable"
    else:
        status = "unknown"
    return {
        "network_reachability": status,
        "registry_reachable": registry_ok,
        "github_reachable": github_ok,
        "awaiting_offline_confirmation": (not registry_ok) and github_ok is False,
        "registry_probe_url": REGISTRY_PROBE_URL,
        "github_probe_url": GITHUB_PROBE_URL,
    }


def ensure_network_reachability(args: argparse.Namespace) -> dict[str, Any]:
    """Generator-side double insurance. Skip when caller already confirmed --offline."""
    if bool(getattr(args, "offline", False)):
        result = {
            "network_reachability": "skipped-offline",
            "registry_reachable": None,
            "github_reachable": None,
            "awaiting_offline_confirmation": False,
            "registry_probe_url": REGISTRY_PROBE_URL,
            "github_probe_url": GITHUB_PROBE_URL,
        }
        args.network_reachability = result
        return result
    result = assess_network_reachability(int(getattr(args, "timeout", 12) or 12))
    args.network_reachability = result
    if result.get("awaiting_offline_confirmation"):
        raise NetworkReachabilityError(
            "公网不可达：registry.npmjs.org 与 api.github.com 均探测失败。"
            "请勿因 .npmrc/私有 registry/内网形态推断 offline。"
            "若确认离线，由调用方显式传入 --offline 后再跑；此前禁止回读本地 upstream-evidence。",
            registry_reachable=False,
            github_reachable=False,
            stage="preflight",
        )
    return result


def local_upstream_readback_allowed(args: argparse.Namespace) -> bool:
    """Local upstream-evidence readback is allowed only after explicit --offline."""
    return bool(getattr(args, "offline", False))


def exact_upgrade_interval_lacks_github_bodies(report: PackageReport) -> bool:
    if not report.notes or not is_exact_upgrade_target(report.upgrade):
        return False
    has_release = any(
        note.release_status in {"substantive", "substantive-linked"} for note in report.notes
    )
    has_changelog = any(note.changelog_status == "confirmed" for note in report.notes)
    return not has_release and not has_changelog


def exact_upgrade_targets_github(report: PackageReport) -> bool:
    if report.repository_url and github_slug(report.repository_url):
        return True
    return any(bool(github_slug(note.repository_url)) for note in report.notes)


def maybe_require_github_reachability_after_empty_evidence(
    report: PackageReport,
    args: argparse.Namespace,
) -> None:
    """If exact-upgrade interval has no release/changelog bodies, re-probe GitHub before asking offline."""
    if bool(getattr(args, "offline", False)):
        return
    if not exact_upgrade_interval_lacks_github_bodies(report):
        return
    if not exact_upgrade_targets_github(report):
        return
    github_ok = probe_http_reachable(GITHUB_PROBE_URL, int(getattr(args, "timeout", 12) or 12))
    reachability = dict(getattr(args, "network_reachability", None) or {})
    reachability["github_reachable"] = github_ok
    if github_ok:
        reachability["network_reachability"] = (
            "reachable" if reachability.get("registry_reachable") else "partial-github-only"
        )
        args.network_reachability = reachability
        append_unique(
            report.warnings,
            "升级区间内未取得可用的 GitHub release/changelog 正文，但 api.github.com 仍可达；"
            "保持联网模式（partial/missing），不得改标 offline，也不得擅自加 --offline。",
        )
        return
    reachability["network_reachability"] = "unreachable"
    reachability["awaiting_offline_confirmation"] = True
    args.network_reachability = reachability
    raise NetworkReachabilityError(
        "精确升级区间内 release 与 changelog 均无可用正文，且 api.github.com 可达性探测失败。"
        "请确认是否由调用方显式传入 --offline（可回读本地 upstream-evidence）；"
        "确认前禁止本地回读，也不得因私有 registry 形态推断 offline。",
        registry_reachable=bool(reachability.get("registry_reachable")),
        github_reachable=False,
        stage="exact-upgrade-github-evidence",
    )


def format_network_reachability_error(exc: NetworkReachabilityError) -> str:
    payload = json.dumps(exc.as_dict(), ensure_ascii=False)
    return f"{exc}\n{payload}"


def default_http_cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base) / "frontend-dependency-upgrade-impact-analysis" / "http"
    return Path.home() / ".cache" / "frontend-dependency-upgrade-impact-analysis" / "http"


def configure_http_cache(cache_dir: str | Path | None, ttl_seconds: int, enabled: bool = True) -> None:
    global _HTTP_CACHE_DIR, _HTTP_CACHE_TTL_SECONDS
    with _HTTP_CACHE_LOCK:
        _HTTP_MEMORY_CACHE.clear()
        _HTTP_CACHE_TTL_SECONDS = max(0, int(ttl_seconds))
        _HTTP_CACHE_DIR = Path(cache_dir).expanduser().resolve() if enabled and cache_dir else None


def http_cache_path(url: str) -> Path | None:
    if _HTTP_CACHE_DIR is None:
        return None
    return _HTTP_CACHE_DIR / f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"


def read_http_cache(url: str) -> tuple[bool, str | None]:
    with _HTTP_CACHE_LOCK:
        if url in _HTTP_MEMORY_CACHE:
            return True, _HTTP_MEMORY_CACHE[url]
        path = http_cache_path(url)
    if path is None or not path.is_file():
        return False, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if float(payload.get("expires_at") or 0) < time.time():
            return False, None
        if payload.get("found") is False:
            with _HTTP_CACHE_LOCK:
                _HTTP_MEMORY_CACHE[url] = None
            return True, None
        text = payload.get("text")
        if not isinstance(text, str):
            return False, None
        with _HTTP_CACHE_LOCK:
            _HTTP_MEMORY_CACHE[url] = text
        return True, text
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False, None


def write_http_cache(url: str, text: str | None, authenticated: bool) -> None:
    with _HTTP_CACHE_LOCK:
        _HTTP_MEMORY_CACHE[url] = text
        path = http_cache_path(url)
        ttl_seconds = _HTTP_CACHE_TTL_SECONDS
    if path is None or authenticated or ttl_seconds <= 0:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".{threading.get_ident()}.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "expires_at": time.time() + ttl_seconds,
                    "found": text is not None,
                    "text": text,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError:
        return


_FETCH_PACKAGE = contextvars.ContextVar("upstream_fetch_package", default="")
_FETCH_DIAGNOSTICS: dict[str, list[str]] = {}
_FETCH_DIAGNOSTICS_LOCK = threading.Lock()


def reset_fetch_diagnostics(package: str = "") -> None:
    key = package or "_default"
    _FETCH_PACKAGE.set(key)
    with _FETCH_DIAGNOSTICS_LOCK:
        _FETCH_DIAGNOSTICS[key] = []


def record_fetch_diagnostic(message: str) -> None:
    text = str(message or "").strip()
    if not text:
        return
    key = _FETCH_PACKAGE.get() or "_default"
    with _FETCH_DIAGNOSTICS_LOCK:
        bucket = _FETCH_DIAGNOSTICS.setdefault(key, [])
        if text not in bucket:
            bucket.append(text)


def drain_fetch_diagnostics(package: str = "", limit: int = 40) -> list[str]:
    key = package or _FETCH_PACKAGE.get() or "_default"
    with _FETCH_DIAGNOSTICS_LOCK:
        items = list(_FETCH_DIAGNOSTICS.pop(key, []))
    return items[: max(1, limit)]


def _http_error_diagnostic(url: str, exc: urllib.error.HTTPError) -> str:
    detail = f"HTTP {exc.code}"
    if exc.code in {403, 429} and "api.github.com" in url:
        remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
        reset_at = exc.headers.get("X-RateLimit-Reset") if exc.headers else None
        if remaining is not None:
            detail += f"；X-RateLimit-Remaining={remaining}"
        if reset_at:
            detail += f"；X-RateLimit-Reset={reset_at}"
        if not os.environ.get("GITHUB_TOKEN"):
            detail += "；未设置 GITHUB_TOKEN，匿名 GitHub API 极易被限流"
        detail += "（疑似限流/防滥用拦截）"
    elif exc.code in {401, 403}:
        detail += "（访问被拒绝）"
    return f"{url} → {detail}"


def request_text(url: str, timeout: int, attempts: int = 2) -> str | None:
    cache_hit, cached = read_http_cache(url)
    if cache_hit:
        return cached
    headers = {
        "User-Agent": "frontend-dependency-upgrade-impact-analysis/2.0",
        "Accept": "application/vnd.github+json, application/json, text/plain, */*",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    last_error = ""
    for attempt in range(max(1, attempts)):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                text = response.read().decode(charset, errors="replace")
                write_http_cache(url, text, authenticated=bool(headers.get("Authorization")))
                return text
        except urllib.error.HTTPError as exc:
            last_error = _http_error_diagnostic(url, exc)
            if exc.code in {404, 410}:
                write_http_cache(url, None, authenticated=bool(headers.get("Authorization")))
                # 404 is often an expected miss (no release); keep diagnostic only for non-miss probes.
                if "api.github.com" in url and "/releases" not in url and "/git/trees/" not in url:
                    record_fetch_diagnostic(last_error)
                return None
            if exc.code not in {403, 429, 500, 502, 503, 504} or attempt + 1 >= attempts:
                record_fetch_diagnostic(last_error)
                return None
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = f"{url} → 网络错误/超时：{exc}"
            if attempt + 1 >= attempts:
                record_fetch_diagnostic(last_error)
                return None
    if last_error:
        record_fetch_diagnostic(last_error)
    return None


def request_json(url: str, timeout: int) -> Any | None:
    text = request_text(url, timeout)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        record_fetch_diagnostic(f"{url} → JSON 解析失败")
        return None


_UPSTREAM_EVIDENCE_LOCK = threading.Lock()
RELEASE_NOTE_PLACEHOLDERS = frozenset({
    "离线模式：需要人工收集官方发布证据。",
    "无法获取 npm 元数据。",
    "该版本只有官方 Git tag，未找到 GitHub Release 正文。",
    "未找到可确认属于目标包的 GitHub Release 正文。",
})
CHANGELOG_NOTE_PLACEHOLDERS = frozenset({
    "离线模式：需要人工收集官方变更日志。",
    "需要人工复核上游资料。",
    "已找到 changelog 文档，但未能提取该版本章节。",
    "未找到官方 changelog 文档。",
})


def upstream_evidence_enabled(args: argparse.Namespace) -> bool:
    return not bool(getattr(args, "no_upstream_evidence", False))


def upstream_evidence_dir(output_dir: Path | str) -> Path:
    return Path(output_dir).resolve() / "upstream-evidence"


def package_dir_name(package: str) -> str:
    return package.replace("/", "__")


def is_exact_upgrade_target(upgrade: Upgrade) -> bool:
    return upgrade.intent == "exact-upgrade" and bool(clean_version(upgrade.to_version))


def is_placeholder_release_notes(text: str) -> bool:
    return not text or text.strip() in RELEASE_NOTE_PLACEHOLDERS


def is_placeholder_changelog(text: str) -> bool:
    return not text or text.strip() in CHANGELOG_NOTE_PLACEHOLDERS


def upstream_package_dir(root: Path, package: str) -> Path:
    return root / package_dir_name(package)


def upstream_version_dir(root: Path, package: str, version: str) -> Path:
    return upstream_package_dir(root, package) / clean_version(version)


def write_upstream_registry(root: Path, package: str, metadata: dict[str, Any]) -> Path:
    package_dir = upstream_package_dir(root, package)
    package_dir.mkdir(parents=True, exist_ok=True)
    path = package_dir / "registry.json"
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_upstream_registry(root: Path | None, package: str) -> dict[str, Any] | None:
    if root is None:
        return None
    path = upstream_package_dir(root, package) / "registry.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_upstream_version_evidence(
    root: Path,
    package: str,
    note: VersionNote,
    *,
    evidence_origin: str = "network",
    changelog_document: str = "",
    fetch_diagnostics: list[str] | None = None,
) -> None:
    """Always persist sources.json for exact-upgrade versions (download-first contract)."""
    version_dir = upstream_version_dir(root, package, note.version)
    version_dir.mkdir(parents=True, exist_ok=True)
    if note.release_notes and not is_placeholder_release_notes(note.release_notes):
        (version_dir / "release.md").write_text(note.release_notes, encoding="utf-8")
    if note.changelog and not is_placeholder_changelog(note.changelog):
        (version_dir / "changelog.md").write_text(note.changelog, encoding="utf-8")
    if changelog_document:
        (version_dir / "changelog-document.md").write_text(changelog_document, encoding="utf-8")
    payload = {
        "version": note.version,
        "published": note.published,
        "change_type": note.change_type,
        "release_status": note.release_status,
        "changelog_status": note.changelog_status,
        "evidence_status": note.evidence_status,
        "evidence_origin": evidence_origin,
        "repository_url": note.repository_url,
        "repository_source": note.repository_source,
        "repository_validation": note.repository_validation,
        "sources": list(note.sources),
        "has_release_body": bool(note.release_notes and not is_placeholder_release_notes(note.release_notes)),
        "has_changelog_section": bool(note.changelog and not is_placeholder_changelog(note.changelog)),
        "has_changelog_document": bool(changelog_document),
        "fetch_diagnostics": list(fetch_diagnostics or []),
    }
    (version_dir / "sources.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_upstream_fetch_failure(
    root: Path,
    package: str,
    *,
    stage: str,
    diagnostics: list[str],
    from_version: str = "",
    to_version: str = "",
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    package_dir = upstream_package_dir(root, package)
    package_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "package": package,
        "from_version": from_version,
        "to_version": to_version,
        "stage": stage,
        "failed_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "diagnostics": list(diagnostics),
    }
    (package_dir / "fetch-failure.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    update_upstream_manifest(
        root,
        package=package,
        from_version=from_version,
        to_version=to_version,
        versions=[{
            "version": to_version or from_version or "unknown",
            "status": "missing",
            "origin": "network-failed",
            "stage": stage,
            "diagnostics": list(diagnostics)[:20],
        }],
    )


def read_upstream_version_evidence(root: Path | None, package: str, version: str) -> dict[str, Any] | None:
    if root is None:
        return None
    version_dir = upstream_version_dir(root, package, version)
    sources_path = version_dir / "sources.json"
    if not version_dir.is_dir() and not sources_path.is_file():
        release_path = version_dir / "release.md"
        changelog_path = version_dir / "changelog.md"
        if not release_path.is_file() and not changelog_path.is_file():
            return None
    payload: dict[str, Any] = {}
    if sources_path.is_file():
        try:
            loaded = json.loads(sources_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass
    release_path = version_dir / "release.md"
    changelog_path = version_dir / "changelog.md"
    if release_path.is_file():
        payload["release_notes"] = release_path.read_text(encoding="utf-8")
    if changelog_path.is_file():
        payload["changelog"] = changelog_path.read_text(encoding="utf-8")
    if not payload.get("release_notes") and not payload.get("changelog") and not payload:
        return None
    payload.setdefault("version", clean_version(version))
    return payload


def merge_note_fields_from_local(
    release_text: str,
    changelog_text: str,
    release_status: str,
    changelog_status: str,
    local: dict[str, Any] | None,
) -> tuple[str, str, str, str, bool]:
    if not local:
        return release_text, changelog_text, release_status, changelog_status, False
    used = False
    local_release = str(local.get("release_notes") or "").strip()
    local_changelog = str(local.get("changelog") or "").strip()
    if is_placeholder_release_notes(release_text) and local_release:
        release_text = local_release
        release_status = str(local.get("release_status") or release_status or "substantive")
        used = True
    if is_placeholder_changelog(changelog_text) and local_changelog:
        changelog_text = local_changelog
        changelog_status = str(local.get("changelog_status") or "confirmed")
        used = True
    return release_text, changelog_text, release_status, changelog_status, used


def update_upstream_manifest(
    root: Path,
    *,
    package: str,
    from_version: str,
    to_version: str,
    versions: list[dict[str, Any]],
) -> None:
    manifest_path = root / "manifest.json"
    with _UPSTREAM_EVIDENCE_LOCK:
        root.mkdir(parents=True, exist_ok=True)
        manifest: dict[str, Any] = {"packages": {}, "root": str(root.resolve())}
        if manifest_path.is_file():
            try:
                loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    manifest.update(loaded)
            except (OSError, json.JSONDecodeError):
                pass
        packages = manifest.setdefault("packages", {})
        if not isinstance(packages, dict):
            packages = {}
            manifest["packages"] = packages
        packages[package] = {
            "package": package,
            "package_dir": package_dir_name(package),
            "from_version": from_version,
            "to_version": to_version,
            "updated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
            "versions": versions,
        }
        manifest["root"] = str(root.resolve())
        manifest["updated_at"] = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def cleanup_upstream_evidence(root: Path | None) -> bool:
    if root is None or not root.exists():
        return False
    shutil.rmtree(root)
    return True


def apply_local_upstream_note(report: PackageReport, local: dict[str, Any], fallback_change_type: str) -> VersionNote:
    release_notes = str(local.get("release_notes") or "").strip()
    changelog = str(local.get("changelog") or "").strip()
    release_status = str(local.get("release_status") or ("substantive" if release_notes else "missing"))
    changelog_status = str(local.get("changelog_status") or ("confirmed" if changelog else "missing"))
    if release_status == "ambiguous":
        evidence_status = "ambiguous"
    elif release_status in {"substantive", "substantive-linked"} and changelog_status == "confirmed":
        evidence_status = "confirmed"
    elif release_status in {"substantive", "substantive-linked", "pointer", "thin", "tag-only"} or changelog_status == "confirmed":
        evidence_status = "partial"
    else:
        evidence_status = str(local.get("evidence_status") or "partial")
    return VersionNote(
        version=str(local.get("version") or ""),
        published=str(local.get("published") or ""),
        change_type=str(local.get("change_type") or fallback_change_type),
        release_notes=release_notes or "未找到可确认属于目标包的 GitHub Release 正文。",
        changelog=changelog or "未找到官方 changelog 文档。",
        sources=list(local.get("sources") or []),
        evidence_status=evidence_status,
        release_status=release_status,
        changelog_status=changelog_status,
        repository_url=str(local.get("repository_url") or ""),
        repository_source=str(local.get("repository_source") or ""),
        repository_validation=str(local.get("repository_validation") or "unknown"),
    )


def collect_exact_upgrade_from_local_evidence(
    upgrade: Upgrade,
    args: argparse.Namespace,
    report: PackageReport,
) -> PackageReport | None:
    root = getattr(args, "upstream_evidence_root", None)
    if root is None or not is_exact_upgrade_target(upgrade):
        return None
    metadata = read_upstream_registry(root, upgrade.package)
    if not isinstance(metadata, dict):
        return None
    normalized = report.upgrade
    selected, warnings, _interval_complete = versions_in_range(metadata, normalized, args.max_versions)
    if not selected:
        return None
    report.warnings.extend(warnings)
    report.evidence_dimensions["registry"] = "candidate"
    report.repository_url, report.repository_directory, report.repository_source_version = repository_details_for_version(
        metadata, normalized.to_version or selected[-1]
    )
    report.homepage = str(metadata.get("homepage") or "")
    target_metadata = (metadata.get("versions") or {}).get(normalized.to_version, {}) or {}
    report.target_peer_dependencies = target_metadata.get("peerDependencies") or {}
    report.target_peer_dependencies_meta = target_metadata.get("peerDependenciesMeta") or {}
    report.target_engines = target_metadata.get("engines") or {}
    times = metadata.get("time") or {}
    add_official_source(report.official_sources, "registry", report.package_url, status="candidate", title="local upstream-evidence registry")
    release_confirmed = True
    changelog_confirmed = True
    local_hits = 0
    version_rows: list[dict[str, Any]] = []
    for version in selected:
        local = read_upstream_version_evidence(root, upgrade.package, version)
        if not local:
            report.notes.append(VersionNote(
                version=version,
                published=str(times.get(version) or "")[:10],
                change_type=classify_change(normalized.from_version, version),
                release_notes="未找到可确认属于目标包的 GitHub Release 正文。",
                changelog="未找到官方 changelog 文档。",
                sources=[package_url(upgrade.package, version)],
                evidence_status="missing",
            ))
            release_confirmed = False
            changelog_confirmed = False
            version_rows.append({"version": version, "status": "missing", "origin": "local"})
            continue
        local.setdefault("published", str(times.get(version) or "")[:10])
        if not local.get("sources"):
            local["sources"] = [package_url(upgrade.package, version)]
        note = apply_local_upstream_note(report, local, classify_change(normalized.from_version, version))
        report.notes.append(note)
        local_hits += 1
        release_confirmed = release_confirmed and note.release_status in {"substantive", "substantive-linked"}
        changelog_confirmed = changelog_confirmed and note.changelog_status == "confirmed"
        if note.repository_url:
            report.repository_lineage[version] = note.repository_url
        version_rows.append({
            "version": version,
            "status": note.evidence_status,
            "origin": "local",
            "release_status": note.release_status,
            "changelog_status": note.changelog_status,
        })
    if local_hits == 0:
        report.notes.clear()
        return None
    report.used_local_upstream_evidence = True
    report.evidence_dimensions["release"] = "confirmed" if release_confirmed else "candidate"
    report.evidence_dimensions["changelog"] = "confirmed" if changelog_confirmed else "candidate"
    report.evidence_dimensions["repository"] = "candidate" if report.repository_url else "missing"
    for dimension in ("migration", "security", "support", "license"):
        if report.evidence_dimensions.get(dimension) == "missing" and dimension == "migration":
            report.evidence_dimensions[dimension] = (
                "not-applicable" if report.change_type in {"patch", "same", "added", "removed"} else "missing"
            )
    report.evidence_completeness = "partial"
    report.warnings.append("离线/本地模式：已从报告旁 upstream-evidence 回读官方证据；不得标记为 complete。")
    update_upstream_manifest(
        Path(root),
        package=upgrade.package,
        from_version=normalized.from_version,
        to_version=normalized.to_version,
        versions=version_rows,
    )
    return report


def parallel_map_ordered(function: Any, items: list[Any], workers: int) -> list[Any]:
    if len(items) < 2 or workers <= 1:
        return [function(item) for item in items]
    # Preserve ContextVar (e.g. per-package fetch diagnostics) across worker threads.
    # Each worker needs its own Context copy: a single Context cannot be .run() concurrently
    # or re-entered from nested parallel_map_ordered calls.
    parent_context = contextvars.copy_context()

    def run(item: Any) -> Any:
        return parent_context.copy().run(function, item)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max(1, workers), len(items))) as executor:
        return list(executor.map(run, items))


def repository_details_from_npm(metadata: dict[str, Any]) -> tuple[str, str]:
    repository = metadata.get("repository") or {}
    if isinstance(repository, str):
        return repository, ""
    if isinstance(repository, dict):
        directory = str(repository.get("directory") or "").replace("\\", "/").strip("/")
        directory = directory.removeprefix("./")
        return str(repository.get("url") or ""), directory
    return "", ""


def repository_details_for_version(metadata: dict[str, Any], version: str) -> tuple[str, str, str]:
    """Resolve repository from version metadata first; top-level npm metadata is only a fallback."""
    version_metadata = (metadata.get("versions") or {}).get(clean_version(version), {}) or {}
    version_repository = version_metadata.get("repository")
    if version_repository:
        url, directory = repository_details_from_npm({"repository": version_repository})
        if url:
            return url, directory, "npm-version-metadata"
    url, directory = repository_details_from_npm(metadata)
    return url, directory, "npm-top-level-fallback" if url else "missing"


def github_slug(repository: str) -> str:
    repository = repository.replace("git+", "").strip()
    match = re.search(r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/#\s]+)", repository)
    if not match:
        return ""
    repo = match.group("repo").removesuffix(".git")
    return f"{match.group('owner')}/{repo}"


def canonical_version(value: str) -> str:
    match = VERSION_RE.search(value or "")
    return match.group("version") if match else ""


def package_release_tokens(package: str) -> set[str]:
    leaf = package.split("/")[-1].lower()
    return {package.lower(), leaf, package.lower().replace("/", "-"), leaf.replace("_", "-")}


def release_matches_package(row: dict[str, str], package: str) -> bool:
    haystack = f"{row.get('tag', '')} {row.get('name', '')} {row.get('body', '')[:5000]}".lower()
    return any(re.search(rf"(^|[/@_\s-]){re.escape(token)}(?=[@_\s-]|v?\d|$)", haystack) for token in package_release_tokens(package))


def release_body_kind(body: str) -> tuple[str, list[str]]:
    urls = re.findall(r"https?://[^\s<>()\]]+", body or "")
    residue = re.sub(r"https?://[^\s<>()\]]+", "", body or "")
    residue = re.sub(r"[\s*_`>#()[\]-]+", "", residue)
    if urls and len(residue) < 20:
        return "pointer", urls
    return ("substantive" if len((body or "").strip()) >= 80 else "thin"), urls


def fetch_github_releases(
    slug: str,
    package: str,
    timeout: int,
    max_pages: int,
    repository_directory: str = "",
    target_versions: Iterable[str] = (),
) -> dict[str, dict[str, str]]:
    if not slug:
        return {}
    targets = {canonical_version(version) for version in target_versions if canonical_version(version)}
    candidates: dict[str, list[dict[str, str]]] = {}
    exhausted = False
    targets_found = False
    for page in range(1, max_pages + 1):
        data = request_json(f"https://api.github.com/repos/{slug}/releases?per_page=100&page={page}", timeout)
        if not isinstance(data, list):
            break
        for release in data:
            tag = str(release.get("tag_name") or "")
            version = canonical_version(tag)
            if version:
                candidates.setdefault(version, []).append({
                    "body": str(release.get("body") or ""),
                    "url": str(release.get("html_url") or ""),
                    "published": str(release.get("published_at") or "")[:10],
                    "name": str(release.get("name") or tag),
                    "tag": tag,
                    "source_kind": "github-release",
                })
        if len(data) < 100:
            exhausted = True
            break
        if targets and targets.issubset(candidates):
            targets_found = True
            break
    token = package.split("/")[-1].lower()
    selected: dict[str, dict[str, str]] = {}
    for version, rows in candidates.items():
        package_rows = [row for row in rows if release_matches_package(row, package)]
        if package_rows:
            choice = package_rows[0]
        elif len(rows) == 1 and not repository_directory:
            choice = rows[0]
        else:
            selected[version] = {
                "body": "",
                "url": "",
                "published": "",
                "name": "",
                "tag": "",
                "source_kind": "ambiguous",
                "status": "ambiguous",
                "reason": f"同一 semver 存在 {len(rows)} 个 release，且 tag/name 未明确匹配包 {package}。",
            }
            continue
        body_kind, pointer_urls = release_body_kind(choice.get("body", ""))
        choice = dict(choice)
        choice["status"] = body_kind
        choice["pointer_urls"] = pointer_urls
        selected[version] = choice
    if not exhausted and not targets_found and max_pages > 0:
        selected["_collection"] = {
            "status": "truncated",
            "reason": f"GitHub Releases 已达到 {max_pages} 页上限，较早版本可能缺失。",
        }
    return selected


def github_default_branch(slug: str, timeout: int) -> str:
    data = request_json(f"https://api.github.com/repos/{slug}", timeout)
    return str(data.get("default_branch") or "") if isinstance(data, dict) else ""


def tag_ref_candidates(package: str, version: str) -> list[str]:
    leaf = package.split("/")[-1]
    return [
        f"v{version}", version, f"{leaf}@{version}", f"{package}@{version}",
        f"{leaf}-v{version}",
    ]


def fetch_changelog(
    slug: str,
    repository_directory: str,
    timeout: int,
    refs: Iterable[str] = (),
    default_branch: str = "",
) -> tuple[str, str]:
    if not slug:
        return "", ""
    base_directory = repository_directory.strip("/")
    directories = [base_directory] if base_directory else []
    directories.extend(
        directory for directory in (
            f"{base_directory}/docs" if base_directory else "",
            f"{base_directory}/dev" if base_directory else "",
            "dev", "docs", ".github",
        )
        if directory and directory not in directories
    )
    directories.append("")
    branches: list[str] = []
    for branch in (*refs, default_branch, "main", "master", "dev"):
        if branch and branch not in branches:
            branches.append(branch)
    allowed_names = {name.lower() for name in CHANGELOG_FILENAMES}
    for branch in branches:
        encoded_branch = urllib.parse.quote(branch, safe="")
        tree = request_json(
            f"https://api.github.com/repos/{slug}/git/trees/{encoded_branch}?recursive=1",
            timeout,
        )
        scored_paths: list[tuple[int, str]] = []
        if isinstance(tree, dict):
            for item in tree.get("tree") or []:
                path = str(item.get("path") or "")
                if item.get("type") != "blob" or not path:
                    continue
                lower_path = path.lower()
                name = Path(path).name.lower()
                if name not in allowed_names and not (
                    "changelog" in name and name.endswith((".md", ".markdown", ".txt"))
                ):
                    continue
                score = 1
                if base_directory and (lower_path == base_directory.lower() or lower_path.startswith(base_directory.lower() + "/")):
                    score += 8
                if name == "changelog.md":
                    score += 5
                if "en-us" in name:
                    score += 9
                if path.count("/") == 0:
                    score += 3
                if lower_path.startswith(("dev/", "docs/")):
                    score += 2
                score -= min(path.count("/"), 4)
                scored_paths.append((score, path))
        for _, relative in sorted(scored_paths, key=lambda row: (-row[0], row[1]))[:8]:
            url = f"https://raw.githubusercontent.com/{slug}/{encoded_branch}/{relative}"
            text = request_text(url, timeout)
            if text and len(text.strip()) > 20:
                return text, url
    # Bounded fallback for APIs that do not expose a tree (rate limit, non-GitHub
    # mirror, or tests). Rank likely locations and never perform an unbounded
    # branch × directory × filename product.
    direct_candidates: list[tuple[int, str, str]] = []
    for branch_index, branch in enumerate(branches):
        for directory in directories:
            for filename in CHANGELOG_FILENAMES:
                score = 100 - branch_index * 5
                if base_directory and directory == base_directory:
                    score += 20
                if filename.lower() == "changelog.md":
                    score += 10
                if "en-US" in filename:
                    score += 15
                if directory in {"dev", "docs"}:
                    score += 3
                relative = f"{directory}/{filename}" if directory else filename
                direct_candidates.append((score, branch, relative))
    for branch in branches:
        branch_candidates = sorted(
            (row for row in direct_candidates if row[1] == branch),
            key=lambda row: -row[0],
        )[:8]
        for _, _, relative in branch_candidates:
            url = f"https://raw.githubusercontent.com/{slug}/{urllib.parse.quote(branch, safe='')}/{relative}"
            text = request_text(url, timeout)
            if text and len(text.strip()) > 20:
                return text, url
    return "", ""


def extract_changelog_section(changelog: str, version: str, max_chars: int) -> str:
    if not changelog:
        return ""
    normalized = canonical_version(version) or clean_version(version)
    if not normalized:
        return ""
    escaped = re.escape(normalized)
    flexible_version = escaped.replace(r"\.", r"[-._]")
    atx_heading = re.compile(
        rf"^(?P<h>\#{{1,6}})[ \t]+[^\n]*?(?<![\d.])v?{flexible_version}(?![\d.])[^"
        rf"\n]*$",
        re.I | re.M,
    )
    match = atx_heading.search(changelog)
    heading_level = len(match.group("h")) if match else 0
    if not match:
        setext = re.compile(
            rf"^(?P<title>[^\n]*?(?<![\d.])v?{flexible_version}(?![\d.])[^\n]*)\n(?P<bar>=+|-+)[ \t]*$",
            re.I | re.M,
        ).search(changelog)
        if setext:
            match = setext
            heading_level = 1 if setext.group("bar").startswith("=") else 2
    if not match:
        html_heading = re.compile(
            rf"<h(?P<level>[1-6])[^>]*>[^<]*?(?<![\d.])v?{flexible_version}(?![\d.])[^<]*?</h[1-6]>",
            re.I,
        ).search(changelog)
        if html_heading:
            match = html_heading
            heading_level = int(html_heading.group("level"))
    if match:
        start = match.end()
        if start < len(changelog) and changelog[start] == "\n":
            start += 1
        next_atx = re.compile(rf"^\#{{1,{heading_level}}}[ \t]+", re.M).search(changelog, start)
        next_setext = re.compile(r"^[^\n]+\n(?:=+|-+)[ \t]*$", re.M).search(changelog, start)
        ends = [candidate.start() for candidate in (next_atx, next_setext) if candidate]
        end = min(ends) if ends else len(changelog)
        section = changelog[start:end].strip()
        return truncate(section, max_chars) if section else ""
    # Some official changelogs (notably jQuery) are release-index documents whose
    # version appears in a link/list item rather than in a Markdown heading.
    marker = re.search(rf"^.*(?<![\d.])v?{flexible_version}(?![\d.]).*$", changelog, re.I | re.M)
    if marker:
        start = changelog.rfind("\n", 0, marker.start()) + 1
        end = changelog.find("\n", marker.end())
        end = len(changelog) if end == -1 else end
        return truncate(changelog[start:end].strip(), max_chars)
    return ""


def raw_github_relative_path(url: str, slug: str) -> str:
    prefix = f"https://raw.githubusercontent.com/{slug}/"
    if not url.startswith(prefix):
        return ""
    remainder = url[len(prefix):]
    _, separator, relative = remainder.partition("/")
    return relative if separator else ""


def resolve_historical_changelog(
    slug: str,
    package: str,
    version: str,
    repository_directory: str,
    version_metadata: dict[str, Any],
    default_branch: str,
    changelog: str,
    changelog_url: str,
    timeout: int,
    max_chars: int,
) -> tuple[str, str, str]:
    section = extract_changelog_section(changelog, version, max_chars)
    if section:
        return changelog, changelog_url, section
    refs = list(dict.fromkeys(
        ref for ref in (
            str(version_metadata.get("gitHead") or ""),
            *tag_ref_candidates(package, version),
        )
        if ref
    ))
    relative_path = raw_github_relative_path(changelog_url, slug)
    if relative_path:
        for ref in refs:
            url = (
                f"https://raw.githubusercontent.com/{slug}/"
                f"{urllib.parse.quote(ref, safe='')}/{relative_path}"
            )
            historical = request_text(url, timeout)
            historical_section = extract_changelog_section(historical or "", version, max_chars)
            if historical_section:
                return historical or "", url, historical_section
    historical, historical_url = fetch_changelog(
        slug,
        repository_directory,
        timeout,
        refs,
        default_branch,
    )
    historical_section = extract_changelog_section(historical, version, max_chars)
    if historical_section:
        return historical, historical_url, historical_section
    return changelog, changelog_url, ""


def fetch_github_tag(slug: str, package: str, version: str, timeout: int) -> dict[str, str]:
    """Return tag-only evidence when a GitHub Release object does not exist."""
    for tag in tag_ref_candidates(package, version):
        encoded = urllib.parse.quote(tag, safe="")
        data = request_json(f"https://api.github.com/repos/{slug}/git/ref/tags/{encoded}", timeout)
        if isinstance(data, dict) and data.get("ref"):
            return {
                "body": "",
                "url": f"https://github.com/{slug}/tree/{urllib.parse.quote(tag, safe='@')}",
                "published": "",
                "name": tag,
                "tag": tag,
                "source_kind": "github-tag",
                "status": "tag-only",
                "reason": "该版本存在官方 Git tag，但没有 GitHub Release 正文。",
            }
    return {}


def fetch_github_release_by_tag(
    slug: str,
    package: str,
    version: str,
    timeout: int,
    repository_directory: str = "",
) -> dict[str, Any]:
    tags = tag_ref_candidates(package, version)
    if repository_directory:
        leaf = package.split("/")[-1]
        tags = [f"{leaf}@{version}", f"{package}@{version}", f"{leaf}-v{version}", f"v{version}", version]
    for tag in dict.fromkeys(tags):
        data = request_json(
            f"https://api.github.com/repos/{slug}/releases/tags/{urllib.parse.quote(tag, safe='')}",
            timeout,
        )
        if not isinstance(data, dict) or not data.get("tag_name"):
            continue
        body = str(data.get("body") or "")
        if repository_directory and tag in {f"v{version}", version}:
            package_haystack = f"{data.get('tag_name', '')} {data.get('name', '')} {body}".lower()
            if not any(token in package_haystack for token in package_release_tokens(package)):
                continue
        body_kind, pointer_urls = release_body_kind(body)
        return {
            "body": body,
            "url": str(data.get("html_url") or ""),
            "published": str(data.get("published_at") or "")[:10],
            "name": str(data.get("name") or tag),
            "tag": str(data.get("tag_name") or tag),
            "source_kind": "github-release",
            "status": body_kind,
            "pointer_urls": pointer_urls,
        }
    return {}


def validate_version_repository(
    slug: str,
    repository_directory: str,
    package: str,
    version: str,
    version_metadata: dict[str, Any],
    timeout: int,
) -> tuple[str, str, str]:
    """Validate npm's repository against the package.json stored at gitHead/tag."""
    if not slug:
        return "missing", "repository 不是可识别的 GitHub URL", repository_directory
    git_head = str(version_metadata.get("gitHead") or "")
    refs = [git_head] if git_head else tag_ref_candidates(package, version)
    relative = f"{repository_directory.strip('/')}/package.json" if repository_directory.strip("/") else "package.json"
    saw_package_json = False
    for ref in dict.fromkeys(ref for ref in refs if ref):
        url = f"https://raw.githubusercontent.com/{slug}/{urllib.parse.quote(ref, safe='')}/{relative}"
        data = request_json(url, timeout)
        if not isinstance(data, dict):
            continue
        saw_package_json = True
        found_name = str(data.get("name") or "")
        found_version = clean_version(str(data.get("version") or ""))
        if found_name == package and found_version == clean_version(version):
            resolved_directory = str(Path(relative).parent).replace("\\", "/")
            return "confirmed", f"{ref}:{relative}", "" if resolved_directory == "." else resolved_directory
        if found_name == package and not found_version:
            return "candidate", f"{ref}:{relative} 包名匹配但未声明版本", repository_directory
    if git_head and not repository_directory.strip("/"):
        tree = request_json(
            f"https://api.github.com/repos/{slug}/git/trees/{urllib.parse.quote(git_head, safe='')}?recursive=1",
            timeout,
        )
        leaf = package.split("/")[-1].lower()
        package_json_paths: list[tuple[int, str]] = []
        if isinstance(tree, dict):
            for item in tree.get("tree") or []:
                path = str(item.get("path") or "")
                if item.get("type") != "blob" or not path.lower().endswith("/package.json"):
                    continue
                lower = path.lower()
                score = (10 if f"/{leaf}/" in f"/{lower}" else 0) - min(path.count("/"), 5)
                package_json_paths.append((score, path))
        name_match_path = ""
        for _, path in sorted(package_json_paths, key=lambda row: (-row[0], row[1]))[:12]:
            data = request_json(
                f"https://raw.githubusercontent.com/{slug}/{urllib.parse.quote(git_head, safe='')}/{path}",
                timeout,
            )
            if not isinstance(data, dict):
                continue
            if str(data.get("name") or "") == package and clean_version(str(data.get("version") or "")) == clean_version(version):
                inferred = str(Path(path).parent).replace("\\", "/")
                return "confirmed", f"{git_head}:{path}（tree 推导 package directory）", inferred
            if str(data.get("name") or "") == package and not name_match_path:
                name_match_path = path
        if name_match_path:
            inferred = str(Path(name_match_path).parent).replace("\\", "/")
            return "candidate", f"{git_head}:{name_match_path} 包名匹配；仓库源码版本字段与发布包不同，需结合 release/tag", inferred
    if git_head and repository_directory.strip("/") and saw_package_json:
        return "ambiguous", "gitHead 上的 repository directory package.json 与目标包名/版本不匹配", repository_directory
    if git_head and not repository_directory.strip("/"):
        commit = request_json(f"https://api.github.com/repos/{slug}/commits/{urllib.parse.quote(git_head, safe='')}", timeout)
        if isinstance(commit, dict) and str(commit.get("sha") or "").startswith(git_head):
            return "confirmed", f"npm gitHead {git_head} 属于该 repository；package.json 未提供可比版本", repository_directory
    if saw_package_json:
        return "ambiguous", "历史 package.json 与目标包名/版本不匹配", repository_directory
    return "candidate", "无法在 gitHead/tag 上读取目标 package.json", repository_directory


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self._skip += 1
        elif not self._skip and tag in {"p", "li", "h1", "h2", "h3", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "noscript"} and self._skip:
            self._skip -= 1
        elif not self._skip and tag in {"p", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def fetch_linked_release_text(url: str, timeout: int, max_chars: int) -> str:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or host in {"localhost", "127.0.0.1", "::1"}:
        return ""
    if re.fullmatch(r"\d+(?:\.\d+){3}", host):
        return ""
    text = request_text(url, timeout)
    if not text:
        return ""
    if "<html" not in text[:1000].lower():
        return truncate(text, max_chars) if len(text.strip()) >= 80 else ""
    parser = VisibleTextParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        return ""
    visible = re.sub(r"[ \t]+", " ", "".join(parser.parts))
    visible = re.sub(r"\n{3,}", "\n\n", visible).strip()
    return truncate(visible, max_chars) if len(visible) >= 160 else ""


def extract_complete_urls(text: str) -> list[str]:
    urls = re.findall(r"\]\((https?://[^)\s]+)\)", text or "")
    urls.extend(
        match.group(1)
        for match in re.finditer(r"(?m)^\s*(https?://[^\s<>]+)\s*$", text or "")
    )
    return list(dict.fromkeys(url.rstrip(".,;:!?)]}") for url in urls if url))


def is_release_page_candidate(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    if host == "github.com" and re.search(r"/(?:issues|pull|commit|compare|discussions)/", path):
        return False
    return (
        host.startswith("blog.")
        or ".blog." in host
        or "release" in path
        or "changelog" in path
        or "migration" in path
        or "upgrade" in path
    )


def add_official_source(
    sources: list[OfficialSource],
    kind: str,
    url: str,
    *,
    status: str = "candidate",
    title: str = "",
    version: str = "",
    reason: str = "",
) -> None:
    if not url:
        return
    existing = next(
        (source for source in sources if source.kind == kind and source.url == url and source.version == version),
        None,
    )
    if existing:
        if status == "confirmed":
            existing.status = status
        existing.title = title or existing.title
        existing.reason = reason or existing.reason
        return
    sources.append(OfficialSource(kind, url, status, title, version, reason))


def known_official_sources(package: str, from_version: str, to_version: str) -> list[OfficialSource]:
    """Small, explicit profiles only for stable official entry points; never for release text."""
    sources: list[OfficialSource] = []
    target_key = semver_key(to_version or from_version)
    from_key = semver_key(from_version)
    name = package.lower()
    if name == "vue":
        if target_key and target_key[0] <= 2:
            add_official_source(sources, "documentation", "https://v2.vuejs.org/", title="Vue 2 documentation")
            add_official_source(sources, "support", "https://v2.vuejs.org/eol/", title="Vue 2 EOL")
        else:
            add_official_source(sources, "documentation", "https://vuejs.org/guide/introduction.html", title="Vue documentation")
        if from_key and target_key and from_key[0] < 3 <= target_key[0]:
            add_official_source(sources, "migration", "https://v3-migration.vuejs.org/", title="Vue 3 Migration Guide")
    elif name == "vuex":
        if target_key and target_key[0] <= 3:
            add_official_source(sources, "documentation", "https://v3.vuex.vuejs.org/", title="Vuex 3 documentation")
        else:
            add_official_source(sources, "documentation", "https://vuex.vuejs.org/", title="Vuex documentation")
        if from_key and target_key and from_key[0] < 4 <= target_key[0]:
            add_official_source(
                sources, "migration",
                "https://vuex.vuejs.org/guide/migrating-to-4-0-from-3-x",
                title="Migrating to Vuex 4",
            )
        add_official_source(sources, "support", "https://vuex.vuejs.org/", title="Vuex maintenance status")
    elif name == "jquery":
        add_official_source(sources, "migration", "https://jquery.com/upgrade-guide/", title="jQuery Upgrade Guide")
        add_official_source(sources, "release-blog-index", "https://blog.jquery.com/category/releases/", title="jQuery release blog")
    elif name == "element-plus":
        add_official_source(
            sources, "changelog",
            "https://element-plus.org/en-US/guide/changelog.html",
            title="Element Plus changelog",
        )
        add_official_source(sources, "documentation", "https://element-plus.org/en-US/", title="Element Plus documentation")
    return sources


def evidence_completeness(dimensions: dict[str, str], interval_complete: bool) -> str:
    if not interval_complete:
        return "partial"
    if any(value == "ambiguous" for value in dimensions.values()):
        return "ambiguous"
    core = ("registry", "repository", "compatibility")
    if any(dimensions.get(name) not in {"confirmed", "not-applicable"} for name in core):
        return "partial"
    if any(dimensions.get(name) not in {"confirmed", "not-applicable"} for name in ("release", "changelog")):
        return "partial"
    # Migration, security, support and license are approval evidence. A generator may
    # discover candidates, but only reviewed evidence can close these dimensions.
    approval = ("migration", "security", "support", "license")
    if any(dimensions.get(name) not in {"confirmed", "not-applicable"} for name in approval):
        return "partial"
    return "complete"


def truncate(text: str, max_chars: int) -> str:
    text = str(text or "").strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 20)].rstrip() + "\n...[truncated]"


def versions_in_range(metadata: dict[str, Any], upgrade: Upgrade, max_versions: int) -> tuple[list[str], list[str], bool]:
    warnings: list[str] = []
    versions = [version for version in (metadata.get("versions") or {}) if semver_key(version) is not None]
    versions.sort(key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))
    before, after = clean_version(upgrade.from_version), clean_version(upgrade.to_version)
    if semver_key(before) is None or semver_key(after) is None:
        return [after or before], ["版本区间不是标准 semver；仅列出可用端点。"], False
    selected = [version for version in versions if compare_versions(version, before) == 1 and compare_versions(version, after) in {-1, 0}]
    before_key, after_key = semver_key(before), semver_key(after)
    if before_key and after_key and before_key[3] == 1 and after_key[3] == 1:
        selected = [version for version in selected if (semver_key(version) or (0, 0, 0, 0, ""))[3] == 1]
    if after not in selected and after in versions:
        selected.append(after)
        selected.sort(key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))
    if not selected:
        return [after], ["npm registry 中没有版本匹配请求区间。"], False
    complete = True
    if max_versions > 0 and len(selected) > max_versions:
        warnings.append(f"版本区间包含 {len(selected)} 个版本；输出已截断为最新 {max_versions} 个，不能视为完整证据。")
        selected = selected[-max_versions:]
        complete = False
    return selected, warnings, complete


def infer_current_versions(upgrades: list[Upgrade], before_lock: LockSnapshot, current_lock: LockSnapshot) -> None:
    for upgrade in upgrades:
        if upgrade.from_version:
            continue
        inferred = before_lock.direct_versions.get(upgrade.package) or current_lock.direct_versions.get(upgrade.package)
        if not inferred:
            observed = (
                before_lock.all_versions.get(upgrade.package)
                or current_lock.all_versions.get(upgrade.package)
                or []
            )
            candidates = [version for version in observed if version != upgrade.to_version]
            if candidates:
                inferred = min(
                    candidates,
                    key=lambda value: semver_key(value) or (0, 0, 0, 0, value),
                )
        # When the current lock already equals an explicitly supplied target, it is
        # post-upgrade evidence, not proof of the historical "from" baseline.
        if inferred and inferred != upgrade.to_version:
            upgrade.from_version = inferred


def discover_target_candidates(metadata: dict[str, Any], upgrade: Upgrade) -> list[TargetCandidate]:
    versions_data = metadata.get("versions") or {}
    stable_versions = [
        version for version in versions_data
        if semver_key(version) is not None and (semver_key(version) or (0, 0, 0, 0, ""))[3] == 1
    ]
    stable_versions.sort(key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))
    current_key = semver_key(upgrade.from_version)
    newer = stable_versions
    if current_key is not None:
        newer = [version for version in stable_versions if compare_versions(version, upgrade.from_version) == 1]
    if not newer:
        return []

    selected: list[tuple[str, str, str]] = []
    if upgrade.package.lower() == "jquery" and current_key is not None and current_key[0] < 3:
        migration_major = [
            version for version in newer
            if (semver_key(version) or (0,))[0] == 3
        ]
        if migration_major:
            selected.append((
                migration_major[-1],
                "official-migration-stage",
                "jQuery 官方升级流程建议跨大版本逐段使用 Migrate；先落到最新 3.x，再评估 4.x。",
            ))
    if current_key is not None:
        same_major = [version for version in newer if (semver_key(version) or (0,))[0] == current_key[0]]
        if same_major:
            selected.append((
                same_major[-1],
                "same-major-latest",
                "同一主版本中的最新稳定候选，通常迁移面较小；仍需结合安全、license 和项目政策确认合规性。",
            ))
        higher_majors = sorted({(semver_key(version) or (0,))[0] for version in newer if (semver_key(version) or (0,))[0] > current_key[0]})
        if higher_majors and upgrade.package.lower() != "jquery":
            next_major = higher_majors[0]
            next_major_versions = [version for version in newer if (semver_key(version) or (0,))[0] == next_major]
            selected.append((
                next_major_versions[-1],
                "next-major-latest",
                "下一主版本中的最新稳定候选，可延长维护周期，但必须完整核查 breaking changes。",
            ))
    latest = newer[-1]
    selected.append((
        latest,
        "latest-stable",
        "registry 中的最新稳定候选；不是自动推荐结论，需结合兼容性、维护状态和迁移成本评审。",
    ))

    candidates: list[TargetCandidate] = []
    seen: set[str] = set()
    times = metadata.get("time") or {}
    for version, candidate_type, rationale in selected:
        if version in seen:
            continue
        seen.add(version)
        version_metadata = versions_data.get(version) or {}
        candidates.append(TargetCandidate(
            package=upgrade.package,
            version=version,
            candidate_type=candidate_type,
            published=str(times.get(version) or "")[:10],
            peer_dependencies=version_metadata.get("peerDependencies") or {},
            engines=version_metadata.get("engines") or {},
            rationale=rationale,
            compatibility="根据 peerDependencies/engines 初筛；仍需与目标 workspace 的框架、Node、浏览器和运行环境核对。",
            compliance_and_maintenance="需要 Agent 核对安全公告、license、维护状态和仓库政策。",
            migration_cost="需要结合 breaking changes、公共包装器和调用方映射评估。",
            validation_scope="需要结合依赖类型和关键业务流程确定。",
            rollback_difficulty="需要结合 manifest+lock、数据/状态兼容性和部署模型评估。",
            source=package_url(upgrade.package, version),
            confidence="medium",
        ))
        if len(candidates) >= 3:
            break
    return candidates


def is_stable_version(version: str) -> bool:
    key = semver_key(version)
    return key is not None and key[3] == 1


def latest_stable_release(metadata: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Newest non-prerelease version plus its version metadata."""
    versions_data = metadata.get("versions") or {}
    stable = [version for version in versions_data if is_stable_version(version)]
    if not stable:
        return "", {}
    stable.sort(key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))
    latest = stable[-1]
    return latest, versions_data.get(latest) or {}


def offline_alternative_candidate(hint: Any, source_package: str) -> AlternativeCandidate:
    return AlternativeCandidate(
        package=hint.package,
        version="",
        rationale=hint.reason,
        compatibility=f"能力对齐差异：{hint.parity_gap}",
        compliance_and_maintenance="离线模式未解析 registry 元数据；需要核对维护状态、弃用标记、安全公告与 license。",
        migration_cost=f"需要按 {source_package} 的实际调用点评估改造范围。",
        validation_scope="需要结合依赖类型和关键业务流程确定。",
        rollback_difficulty="需要结合 manifest+lock、数据/状态兼容性和部署模型评估。",
        source=package_url(hint.package),
        confidence="low",
        compliance_status="unknown",
        disqualifiers=["离线模式未解析精确版本"],
        origin="curated-map",
    )


def build_alternative_candidates(
    source_package: str,
    args: argparse.Namespace,
    warnings: list[str],
) -> list[AlternativeCandidate]:
    """Resolve reviewed replacement packages to exact stable versions.

    The package list is curated knowledge; the version, publish date and deprecation
    flag are read from the registry so nothing version-shaped is hardcoded. Candidates
    are always `unknown` compliance: they are decision evidence, never a selection.
    """
    hints = curated_replacement_packages(source_package)
    if not hints:
        return []
    candidates: list[AlternativeCandidate] = []
    for hint in hints[:3]:
        if args.offline:
            candidates.append(offline_alternative_candidate(hint, source_package))
            continue
        metadata = request_json(registry_url(hint.package), args.timeout)
        if not isinstance(metadata, dict):
            candidate = offline_alternative_candidate(hint, source_package)
            candidate.disqualifiers = ["未能获取 registry 元数据"]
            candidate.compliance_and_maintenance = "获取 registry 元数据失败；需要人工核对版本、维护状态与 license。"
            candidates.append(candidate)
            warnings.append(f"获取替代库 {hint.package} 的 registry 元数据失败；候选保留但缺少精确版本。")
            continue
        version, version_metadata = latest_stable_release(metadata)
        published = str((metadata.get("time") or {}).get(version) or "")[:10]
        maintenance = [f"最新稳定版发布于 {published}" if published else "registry 未提供发布日期"]
        disqualifiers: list[str] = []
        deprecated = bool(version_metadata.get("deprecated"))
        if deprecated:
            disqualifiers.append(f"registry 标记该版本已弃用：{version_metadata['deprecated']}")
        license_name = str(version_metadata.get("license") or "")
        maintenance.append(f"license={license_name or '未声明'}")
        candidates.append(AlternativeCandidate(
            package=hint.package,
            version=version,
            rationale=hint.reason,
            compatibility=f"能力对齐差异：{hint.parity_gap}",
            compliance_and_maintenance="；".join(maintenance) + "；仍需核对安全公告、license 与仓库政策。",
            migration_cost=f"需要按 {source_package} 的实际调用点评估改造范围。",
            validation_scope="需要结合依赖类型和关键业务流程确定。",
            rollback_difficulty="需要结合 manifest+lock、数据/状态兼容性和部署模型评估。",
            source=package_url(hint.package, version),
            confidence="low",
            compliance_status="unknown",
            disqualifiers=disqualifiers,
            evidence_urls=[package_url(hint.package, version)],
            origin="curated-map",
            peer_dependencies=version_metadata.get("peerDependencies") or {},
            engines=version_metadata.get("engines") or {},
            published=published,
            license=license_name,
            deprecated=deprecated,
            conservative_version=previous_major_stable(metadata, version),
        ))
    return candidates


def previous_major_stable(metadata: dict[str, Any], version: str) -> str:
    """Newest stable release of the major line below `version`.

    Offered as the conservative option: a smaller jump for teams that do not want the
    newest major's breaking changes in the same change window as the replacement.
    """
    key = semver_key(version)
    if key is None or key[0] <= 0:
        return ""
    target_major = key[0] - 1
    stable = [
        candidate for candidate in (metadata.get("versions") or {})
        if is_stable_version(candidate) and (semver_key(candidate) or (0,))[0] == target_major
    ]
    if not stable:
        return ""
    stable.sort(key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))
    return stable[-1]


def flag_alternative_runtime_conflicts(
    reports: list[PackageReport],
    runtime: NodeRuntimeAssessment,
    args: argparse.Namespace | None = None,
) -> None:
    """Mark replacement candidates that cannot run on the project's Node.

    Only judged against a concrete selected project Node; an unresolved runtime leaves
    the candidate at `unknown` fit rather than guessing. When the newest stable release
    conflicts, the newest release that does satisfy the project runtime is resolved as
    the recommended fallback so the human still has a usable version to decide on.
    """
    selected = runtime.selected_project_node
    if not selected:
        return
    for report in reports:
        for candidate in report.alternative_candidates:
            requirement = str((candidate.engines or {}).get("node") or "")
            if not requirement:
                candidate.constraint_fit = "fits"
                continue
            satisfied = semver_satisfies(selected, requirement)
            if satisfied is not False:
                if satisfied is True:
                    candidate.constraint_fit = "fits"
                continue
            candidate.constraint_fit = "conflicts"
            append_unique(
                candidate.disqualifiers,
                f"engines.node={requirement} 与所选项目 Node {selected} 不兼容；"
                "选择该候选需同时规划运行时升级",
            )
            if args is None or args.offline or candidate.fallback_version:
                continue
            metadata = request_json(registry_url(candidate.package), args.timeout)
            if not isinstance(metadata, dict):
                continue
            fallback = highest_version_satisfying_node(metadata, selected, exclude=candidate.version)
            if fallback:
                candidate.fallback_version = fallback
                append_unique(
                    candidate.disqualifiers,
                    f"若不升级运行时，可考虑的最高兼容版本为 {fallback}（需重新核对该版本的能力与破坏性变更）",
                )
            else:
                append_unique(candidate.disqualifiers, "该库无任何满足当前项目 Node 的稳定版本")


def highest_version_satisfying_node(
    metadata: dict[str, Any],
    node_version: str,
    exclude: str = "",
) -> str:
    """Newest stable release whose `engines.node` accepts `node_version`."""
    versions_data = metadata.get("versions") or {}
    stable = [version for version in versions_data if is_stable_version(version)]
    stable.sort(key=lambda value: semver_key(value) or (0, 0, 0, 0, ""), reverse=True)
    for version in stable:
        if version == exclude or (versions_data.get(version) or {}).get("deprecated"):
            continue
        requirement = str(((versions_data.get(version) or {}).get("engines") or {}).get("node") or "")
        if not requirement or semver_satisfies(node_version, requirement) is not False:
            return version
    return ""


def highest_stable_candidate_compatible_with_project(
    metadata: dict[str, Any],
    selected_node: str,
    manifest: ManifestSnapshot,
    lock: LockSnapshot,
) -> str:
    """Resolve the newest non-deprecated stable version whose Node and peers fit."""
    versions_data = metadata.get("versions") or {}
    versions = sorted(
        (version for version in versions_data if is_stable_version(version)),
        key=lambda value: semver_key(value) or (0, 0, 0, 0, ""),
        reverse=True,
    )
    for version in versions:
        row = versions_data.get(version) or {}
        if row.get("deprecated"):
            continue
        node_requirement = str((row.get("engines") or {}).get("node") or "")
        if not selected_node or (
            node_requirement and semver_satisfies(selected_node, node_requirement) is not True
        ):
            continue
        peer_ok = True
        for peer, requirement in sorted((row.get("peerDependencies") or {}).items()):
            installed = project_declared_version(peer, manifest, lock)
            if not installed or semver_satisfies(installed, str(requirement)) is not True:
                peer_ok = False
                break
        if peer_ok:
            return version
    return ""


def verify_replacement_recommendations(
    reports: list[PackageReport],
    runtime: NodeRuntimeAssessment,
    manifest: ManifestSnapshot,
    lock: LockSnapshot,
    args: argparse.Namespace,
) -> None:
    """Keep user-facing choices to reviewed latest stable compatible versions."""
    for report in reports:
        for candidate in report.alternative_candidates:
            if candidate.origin != "analysis-evidence" or candidate.compliance_status != "eligible":
                continue
            if args.offline:
                # Keep the human-reviewed version selectable; freshness is a warning, not a veto.
                append_unique(
                    report.warnings,
                    f"{candidate.package}@{candidate.version}：离线模式未向 registry 复核是否为最新稳定兼容版；"
                    "联网重跑前请人工确认版本仍适用。",
                )
                continue
            metadata = request_json(registry_url(candidate.package), args.timeout)
            if not isinstance(metadata, dict):
                candidate.constraint_fit = "unknown"
                append_unique(candidate.disqualifiers, "无法获取 registry 元数据以确认最新稳定兼容版本")
                continue
            recommended = highest_stable_candidate_compatible_with_project(
                metadata, runtime.selected_project_node, manifest, lock,
            )
            if not recommended:
                candidate.constraint_fit = "conflicts"
                append_unique(candidate.disqualifiers, "未找到同时满足当前 Node、框架与 peer 约束的稳定版本")
                continue
            if candidate.version != recommended:
                append_unique(
                    candidate.disqualifiers,
                    f"满足全部项目约束的最新稳定版是 {recommended}；"
                    f"当前复核版本 {candidate.version} 不再作为默认推荐，需按 {recommended} 重新复核安全与 license",
                )


def assess_alternative_constraint_fit(
    reports: list[PackageReport],
    manifest: ManifestSnapshot,
    lock: LockSnapshot,
) -> None:
    """Set `constraint_fit` from declared peers, leaving unverifiable peers `unknown`.

    A runtime conflict already recorded by the Node cross-check is never downgraded.
    """
    for report in reports:
        for candidate in report.alternative_candidates:
            if candidate.constraint_fit == "conflicts":
                continue
            peers = candidate.peer_dependencies or {}
            if not peers:
                # No declared peers to contradict the project: treat as fits so reviewed
                # analysis-evidence candidates can enter the replace confirmation options.
                if candidate.constraint_fit == "unknown":
                    candidate.constraint_fit = "fits"
                continue
            verified = True
            for peer, requirement in sorted(peers.items()):
                installed = project_declared_version(peer, manifest, lock)
                if not installed or not isinstance(requirement, str):
                    candidate.constraint_fit = "unknown"
                    verified = False
                    continue
                satisfied = semver_satisfies(installed, requirement)
                if satisfied is False:
                    candidate.constraint_fit = "conflicts"
                    append_unique(
                        candidate.disqualifiers,
                        f"peerDependencies.{peer}={requirement} 与项目现有 {peer}@{installed} 不兼容",
                    )
                    break
                if satisfied is not True:
                    candidate.constraint_fit = "unknown"
                    verified = False
            else:
                if verified:
                    candidate.constraint_fit = "fits"


def project_declared_version(package: str, manifest: ManifestSnapshot, lock: LockSnapshot) -> str:
    """Resolved lock version for a project dependency, falling back to the manifest range."""
    resolved = (lock.direct_versions or {}).get(package) or ""
    if resolved:
        return resolved
    declared = (manifest.packages or {}).get(package)
    spec = getattr(declared, "spec", "") if declared else ""
    return clean_version(spec) if spec else ""


def rank_alternative_candidates(reports: list[PackageReport]) -> None:
    """Order replacement candidates by machine-checkable signals only.

    Signal priority is fixed by `ALTERNATIVE_RANK_SIGNALS` so the same inputs always
    produce the same order. Ranking is presentation order plus a stated basis; it is
    not a selection and never changes `recommended_action`.
    """
    fit_score = {"fits": 2, "unknown": 1, "conflicts": 0}
    for report in reports:
        for candidate in report.alternative_candidates:
            candidate.rank_signals = [
                f"human-reviewed={'yes' if candidate.origin == 'analysis-evidence' else 'no'}",
                f"project-constraint-fit={candidate.constraint_fit}",
                f"not-deprecated={'no' if candidate.deprecated else 'yes'}",
                f"recent-release={candidate.published or 'unknown'}",
                f"declared-license={candidate.license or 'unknown'}",
            ]
        report.alternative_candidates.sort(key=lambda candidate: (
            0 if candidate.origin == "analysis-evidence" else 1,
            -fit_score.get(candidate.constraint_fit, 1),
            1 if candidate.deprecated else 0,
            invert_date_key(candidate.published),
            0 if candidate.license else 1,
            candidate.package,
        ))
        for index, candidate in enumerate(report.alternative_candidates, start=1):
            candidate.rank = index


def invert_date_key(published: str) -> str:
    """Sort key placing newer ISO dates first and unknown dates last."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published or ""):
        return "0000-00-00"
    return "".join(chr(ord("9") - int(char)) if char.isdigit() else char for char in published)


def build_disposition_options(report: PackageReport) -> list[DispositionOption]:
    """Render the full decision menu for one open-target package.

    Availability only states whether this run produced evidence for a route; it never
    ranks or selects one. Ranking stays with `recommended_action`.
    """
    package = report.upgrade.package
    natives = curated_native_routes(package)
    options: list[DispositionOption] = []
    for option, title, applicability, required_evidence in DISPOSITION_OPTIONS:
        availability = "needs-research"
        detail = ""
        if option == "handle-parent-package":
            if report.provenance.parents:
                availability = "evidence-available"
                detail = "父包：" + "、".join(
                    f"{edge.package}@{edge.version or '未解析'}" for edge in report.provenance.parents[:5]
                ) + (
                    f"；overrides 最低可行版本 {report.provenance.override_version}"
                    if report.provenance.override_version else "；overrides 可行版本待解析"
                )
            else:
                detail = "本轮未解析出父包；仅当该包由其他包引入时适用。"
        elif option == "remove-dependency":
            if report.removal.status not in {"not_assessed", "uncertain"}:
                availability = "evidence-available"
            detail = f"删除结论：{report.removal.status}"
            if report.provenance.kind == "both":
                detail += "；该包同时被其他包引入，摘除声明后仍会以传递依赖存在"
            elif report.provenance.kind in {"transitive", "phantom"}:
                availability = "not-applicable"
                detail = f"来源为 {report.provenance.kind}：manifest 未声明，没有可摘除的声明"
        elif option == "replace-with-alternative":
            eligible = eligible_alternative_candidates(report)
            if eligible:
                availability = "evidence-available"
                detail = "候选：" + "、".join(
                    f"{candidate.package}@{candidate.version or '待解析'}"
                    for candidate in eligible
                )
            else:
                detail = (
                    "尚无同时通过 Node、框架、peer、安全、license、维护状态与最新稳定版核验的候选；"
                    "需要 Agent 基于官方资料研究并回填。"
                )
        elif option == "native-platform-capability":
            if natives:
                availability = "evidence-available"
                detail = "；".join(
                    f"{hint.native_api}：{hint.reason} 差异：{hint.parity_gap}"
                    for hint in natives
                )
            else:
                detail = "未登记可直接替代的原生能力；需要按实际用法确认。"
        elif option == "in-house-reimplementation":
            if report.refactor_plan.status == "established":
                availability = "evidence-available"
                detail = (
                    f"改造范围：{'；'.join(report.refactor_plan.call_site_groups)}；"
                    f"需自建能力：{'、'.join(report.refactor_plan.capabilities_to_rebuild)}"
                )
            else:
                detail = "尚未建立代码调用证据，无法给出重构范围；需先补齐调用点扫描或知识图谱证据。"
        options.append(DispositionOption(option, title, applicability, required_evidence, availability, detail))
    return options


def build_refactor_plan(report: PackageReport, points: list[CodeModificationPoint]) -> RefactorPlan:
    """Derive the first-party replacement route from this run's own scan evidence.

    Direction comes from real call sites, not from a template: groups are the usage
    categories actually found in this repository, and the capability inventory is what
    those call sites would have to keep working without the dependency.
    """
    package = report.upgrade.package
    plan = RefactorPlan()
    natives = curated_native_routes(package)
    plan.native_routes = [
        f"{hint.native_api}：{hint.reason}（差异：{hint.parity_gap}）" for hint in natives
    ]
    grouped: dict[str, list[str]] = {}
    for point in points:
        if point.package != package:
            continue
        grouped.setdefault(point.category, [])
        append_unique(grouped[point.category], point.file)
    for category in sorted(grouped):
        files = sorted(grouped[category])
        shown = "、".join(f"`{path}`" for path in files[:5])
        suffix = f" 等 {len(files)} 个文件" if len(files) > 5 else ""
        plan.call_site_groups.append(f"{visible_code_category(category)}：{shown}{suffix}")
    declaration_only = set(grouped) <= {DECLARATION_CATEGORY}
    if grouped and not declaration_only:
        plan.status = "established"
        plan.stages = list(REFACTOR_STAGES)
        plan.validation_scope = validation_for_type(report.upgrade.dependency_type)
    usage_categories = [category for category in sorted(grouped) if category != DECLARATION_CATEGORY]
    plan.capabilities_to_rebuild = [
        f"{hint.native_api} 未覆盖的部分：{hint.parity_gap}" for hint in natives
    ] or ([
        "逐条列出该依赖在以下用法中承担的能力："
        + "、".join(visible_code_category(category) for category in usage_categories)
    ] if usage_categories else ["尚无调用点证据，无法列出需自建的能力"])
    if declaration_only and grouped:
        plan.unknowns.append("仅建立声明/配置引用证据；需确认是否存在运行时或动态用法后才能定重构范围")
    if not grouped:
        plan.unknowns.append("本轮未扫描到该包的调用点；需要知识图谱或定向调用追踪确认真实使用面")
    if not natives:
        plan.unknowns.append("未登记可直接改用的平台原生能力；自建实现的边界需由 Agent 依官方文档确认")
    plan.unknowns.append("自建实现的安全、边界条件与长期维护责任需要明确责任人")

    if plan.status != "established":
        # Without real call sites there is nothing to rewrite yet: a per-call-site table
        # and a size grade would both read as evidence that does not exist.
        return plan
    native_api = natives[0].native_api if natives else ""
    package_points = [point for point in points if point.package == package]
    for point in sorted(package_points, key=lambda value: (value.file, value.line)):
        approach, parity_risk = refactor_approach(point.category, native_api)
        plan.actions.append(RefactorAction(
            file=point.file, line=point.line, category=point.category,
            current_usage=point.current_usage, approach=approach, parity_risk=parity_risk,
            validation=plan.validation_scope or validation_for_type(report.upgrade.dependency_type),
            confidence="medium" if point.category in CODE_CATEGORY_TITLES else "low",
        ))
    plan.parity_checks = behavior_parity_checks(report.upgrade.dependency_type)
    files = sorted({point.file for point in package_points if point.category != DECLARATION_CATEGORY})
    shared_files = [path for path in files if SHARED_RE.search(path)]
    plan.scale, plan.scale_basis = refactor_scale(
        len(files),
        len([point for point in package_points if point.category != DECLARATION_CATEGORY]),
        bool(shared_files),
    )
    plan.impact_surface = [
        f"受影响文件：{'、'.join(f'`{path}`' for path in files[:8])}{f' 等 {len(files)} 个' if len(files) > 8 else ''}"
        if files else "受影响文件：未建立",
        f"公共包装器：{'、'.join(f'`{path}`' for path in shared_files) if shared_files else '未发现'}",
        "页面/流程：见「业务影响」；未映射的调用方需先补路由/调用方追踪",
        "类型/构建/测试：需核对类型声明、构建配置与受影响测试是否引用该包",
    ]
    plan.rollback = (
        "适配层保留一层间接，可按调用点分组回滚；未摘除依赖声明前保持 manifest+lock 可还原，"
        "摘除声明后回滚需恢复已复核的 manifest+lock 组合与上一份可部署产物。"
    )
    return plan


def assess_provenance(
    report: PackageReport,
    manifest: ManifestSnapshot,
    graph: DependencyGraph,
    points: list[CodeModificationPoint],
    workspace_names: set[str],
) -> ProvenanceAssessment:
    """Classify where the package comes from: manifest, code, or someone else's dependency.

    The classification decides which routes exist at all, so it stays conservative:
    anything that cannot be told apart from an alias or a sibling workspace declaration
    is reported as `unknown` with the reason rather than guessed into a track.
    """
    package = report.upgrade.package
    result = ProvenanceAssessment()
    declared = manifest.packages.get(package)
    result.declared_field = declared.field if declared else ""
    result.used_in_code = any(
        point.package == package and point.category != DECLARATION_CATEGORY for point in points
    )
    for edge in graph.parents_of(package):
        result.parents.append(ParentEdge(edge.parent, edge.parent_version, edge.requirement))
    if result.parents:
        # A single-node "chain" for a package the workspace declares itself says nothing.
        chains, total = graph.paths_to(package, limit=PARENT_CHAIN_LIMIT)
        result.chains = [" → ".join(chain) for chain in chains if len(chain) > 1]
        result.chain_total = total

    if declared:
        result.kind = "both" if result.parents else "direct"
        result.evidence.append(f"manifest 在 {declared.field} 中声明 `{package}` = `{declared.spec}`")
        if result.parents:
            result.evidence.append(
                f"同时被 {len(result.parents)} 个包依赖：摘除声明后仍会以传递依赖留在 lock 中"
            )
    elif result.used_in_code:
        result.kind = "phantom"
        result.evidence.append("代码中存在直接用法，但 manifest 未声明；依赖提升或父包碰巧安装才使其可用")
    elif result.parents:
        result.kind = "transitive"
        result.evidence.append(f"manifest 未声明，由 {len(result.parents)} 个父包引入")
    else:
        result.kind = "unknown"
        result.evidence.append("manifest 未声明、代码未见用法、lock 中也未见父包")

    if not graph.supported:
        result.unknowns.append("本轮未能解析依赖边：父包链与传递依赖判定不可用" + (
            f"（{'; '.join(graph.warnings)}）" if graph.warnings else ""
        ))
        if result.kind == "unknown" and not declared:
            result.unknowns.append("缺少依赖边证据时，无法区分“未安装”与“由父包引入”")
    if result.kind == "phantom":
        if package in NODE_BUILTINS:
            result.kind = "unknown"
            result.unknowns.append(f"`{package}` 与 Node 内置模块同名；需确认代码引用的不是内置模块")
        elif package in workspace_names:
            result.kind = "unknown"
            result.unknowns.append(f"`{package}` 是本仓库的 workspace 包名；不属于外部依赖")
        else:
            result.unknowns.append(
                "幽灵依赖判定需排除：tsconfig paths / 构建 alias、子包 manifest 声明、类型包与运行时注入"
            )
    if result.chain_total > len(result.chains):
        result.unknowns.append(
            f"父包路径共 {result.chain_total} 条，仅展示最短的 {len(result.chains)} 条"
        )
    return result


def resolve_override_version(
    report: PackageReport,
    node_requirement: str,
    args: argparse.Namespace | None,
) -> None:
    """Lowest stable version satisfying every parent range and the project's Node.

    Lowest rather than newest on purpose: an override is a forced resolution across
    packages that never agreed to it, so the smallest move that satisfies all of them is
    the one least likely to break a parent.
    """
    provenance = report.provenance
    if not provenance.parents or args is None or args.offline:
        if provenance.parents and args is not None and args.offline:
            provenance.unknowns.append("离线模式：未解析 overrides 可用版本")
        return
    metadata = request_json(registry_url(report.upgrade.package), args.timeout)
    if not isinstance(metadata, dict):
        provenance.unknowns.append("未能获取 registry 元数据：overrides 可行版本待解析")
        return
    requirements = [edge.requirement for edge in provenance.parents if edge.requirement]
    candidates = sorted(
        (version for version in (metadata.get("versions") or {}) if is_stable_version(version)),
        key=lambda value: semver_key(value) or (0, 0, 0, 0, ""),
    )
    def node_ok(version: str) -> bool:
        if not node_requirement:
            return True
        engines = ((metadata.get("versions") or {}).get(version) or {}).get("engines") or {}
        declared_node = str(engines.get("node") or "")
        return not declared_node or semver_satisfies(node_requirement, declared_node) is not False

    def unmet_ranges(version: str) -> list[str]:
        return [item for item in requirements if semver_satisfies(version, item) is False]

    for version in candidates:
        if node_ok(version) and not unmet_ranges(version):
            provenance.override_version = version
            return
    # Nothing satisfies everyone: report the lowest version that clears the Node bar and
    # name the parents whose ranges it breaks, so the trade-off is explicit.
    for version in candidates:
        unmet = unmet_ranges(version)
        if node_ok(version) and len(unmet) < len(requirements):
            provenance.override_version = version
            provenance.override_breaks = [
                f"{edge.package}@{edge.version} 要求 {edge.requirement}"
                for edge in provenance.parents
                if edge.requirement and semver_satisfies(version, edge.requirement) is False
            ]
            return
    provenance.unknowns.append("没有任何稳定版本能同时满足现有父包 range；overrides 必然破坏至少一个父包约束")


def flag_parent_fix_availability(report: PackageReport, args: argparse.Namespace | None) -> None:
    """Does each parent's newest stable release still pull this package in?"""
    if args is None or args.offline:
        for edge in report.provenance.parents:
            edge.fix_note = "离线模式：未核对父包是否已发布不再依赖该包的版本"
        return
    package = report.upgrade.package
    for edge in report.provenance.parents[:PARENT_CHAIN_LIMIT]:
        metadata = request_json(registry_url(edge.package), args.timeout)
        if not isinstance(metadata, dict):
            edge.fix_note = "未能获取该父包的 registry 元数据"
            continue
        latest, version_metadata = latest_stable_release(metadata)
        edge.latest_stable = latest
        requirement = str((version_metadata.get("dependencies") or {}).get(package) or "")
        if not requirement:
            edge.fix_available = "dropped"
            edge.fix_note = f"最新稳定版 {latest} 已不再依赖 `{package}`"
        else:
            edge.fix_available = "still-depends"
            edge.fix_note = f"最新稳定版 {latest} 仍依赖 `{package}` ({requirement})"


REMOVAL_COVERAGE_TITLES = {
    "business": "业务使用（页面/流程/调用方）",
    "runtime": "运行时直接 import/require",
    "dynamic": "动态 import、字符串加载与配置驱动加载",
    "build": "构建、脚本、样式与代码生成",
    "tooling": "工具链与 CI",
    "peer": "peerDependencies 与可选依赖",
    "transitive": "间接 consumer 与跨包使用",
}


def package_route_options(report: PackageReport) -> list[ConfirmationOption]:
    """Concrete replacement `package@version` choices.

    Same-package upgrades are not offered: a package reaches this path because something
    about the package itself has to go, and a version bump does not resolve that. Only the
    recommended version of each replacement is offered; the rest stay in the report.
    """
    options: list[ConfirmationOption] = []
    for index, candidate in enumerate(eligible_alternative_candidates(report), start=1):
        version = candidate.version or "待解析"
        detail = candidate.rationale or "替代库候选"
        if not candidate.version:
            detail += "；本轮未解析到精确版本，须联网解析后再确认"
        if candidate.constraint_fit == "conflicts":
            detail += f"；约束冲突：{'; '.join(candidate.disqualifiers) or '见候选表'}"
        options.append(ConfirmationOption(
            f"replace:{candidate.package}@{version}",
            (
                f"{candidate.package}@{version}（首选方案）"
                if index == 1 else f"{candidate.package}@{version}（备选方案 {index - 1}）"
            ),
            detail,
        ))
    return options


def assign_primary_track(report: PackageReport) -> None:
    """Triage one open target into exactly one track, mirroring the decision order.

    Provenance comes first: a package the workspace never declared cannot be removed from
    the manifest, and one nobody calls cannot be rewritten in first-party code. Only for
    packages the workspace actually owns does the remove → replace → rewrite order apply.
    """
    removal = report.removal.status
    routes = package_route_options(report)
    removable = removal == "safe_removal_candidate"
    refactorable = report.refactor_plan.status == "established"
    provenance = report.provenance.kind
    if provenance == "transitive":
        report.primary_track = "handle-parent"
        report.primary_track_basis = (
            f"manifest 未声明该包，由 {len(report.provenance.parents)} 个父包引入："
            "既删不掉也改造不了，只能动父包或用 overrides 钉版本。"
        )
        report.alternate_tracks = []
        return
    if provenance == "phantom":
        report.primary_track = "fix-phantom"
        report.primary_track_basis = (
            "代码在用但 manifest 未声明：依赖靠提升或父包碰巧安装才可用，"
            "父包一变就会断，必须先消除这种用法。"
        )
        report.alternate_tracks = ["replace"] if routes else []
        return
    if removal == "safe_removal_candidate":
        report.primary_track = "remove"
        report.primary_track_basis = "删除证据已达安全候选门槛，删除是成本最低的收敛方式。"
    elif removal in {"uncertain", "not_assessed"}:
        report.primary_track = "pending-removal-evidence"
        report.primary_track_basis = (
            f"删除结论为 {removal}：尚未确认该包是否真的被使用，先补证据再定轨；"
            "静态扫描零命中不足以判定未使用。"
        )
    elif routes:
        report.primary_track = "replace"
        report.primary_track_basis = f"已确认存在使用点且本轮有 {len(routes)} 个可选的包@版本。"
    else:
        report.primary_track = "native-refactor"
        report.primary_track_basis = "已确认存在使用点，且本轮无可选替代包，只剩原生改造。"
    available = {
        "remove": removable,
        "replace": bool(routes),
        "native-refactor": refactorable,
        "handle-parent": provenance == "both" and bool(report.provenance.parents),
    }
    report.alternate_tracks = [
        track for track, ready in available.items() if ready and track != report.primary_track
    ]


def append_other_option(question: ConfirmationQuestion) -> None:
    if any(option.option_id == "other" for option in question.options):
        return
    question.options.append(ConfirmationOption(
        "other", "其他：自行指定依赖包与版本，或改走其他处置方式",
        "自填内容会以 `source=other` 记录，并按同样的约束重新核对。",
    ))


def curated_lead_note(report: PackageReport) -> str:
    curated = [
        candidate.package for candidate in report.alternative_candidates
        if candidate.origin == "curated-map"
    ]
    if not curated or eligible_alternative_candidates(report):
        return ""
    names = "、".join(f"`{name}`" for name in curated[:5])
    return (
        f"报告中的 curated-map 线索（{names}）不可直接点选；"
        "须调研回填 `--analysis-evidence-file` 后才会出现 `replace:<包>@<版本>`。"
    )


def build_proceed_exact_question(report: PackageReport) -> ConfirmationQuestion:
    """Exact upgrades still need a human proceed/defer gate before Stage B/C."""
    package = report.upgrade.package
    target = report.upgrade.to_version
    source = report.upgrade.from_version or report.current_lock_version or "?"
    question = ConfirmationQuestion(package=package, track=PROCEED_EXACT_TRACK)
    report.primary_track = PROCEED_EXACT_TRACK
    report.primary_track_basis = "精确目标版本已明确；进入计划/实施前须确认推进或延期"
    if report.exact_upgrade_status == "blocked":
        question.status = "blocked"
        question.blocked_reason = (
            "精确升级仍有实施阻塞项；解除阻塞前不确认推进。"
            "同批任一包 blocked 时 `batch_implementation_gate=frozen`。"
        )
        question.prerequisites = list(report.implementation_blockers) or [
            "解决 Node/父依赖/lock 收敛等 implementation_blockers 后重跑"
        ]
        report.decision_status = "needs_choice"
        report.selection_status = "needs_explicit_choice"
        append_unique(
            report.decision_required,
            "精确升级阻塞未解除；解除前不得确认推进，也不得开实施计划。",
        )
        return question
    proceed_id = f"proceed:{package}@{target}"
    question.prompt = (
        f"确认按精确目标推进 `{package}` `{source}` → `{target}` 吗？"
        "所有当前 ready 包（精确升级与开放目标）可同一波确认；"
        "switch/handle-parent 后续题下一波；blocked 不问。"
    )
    question.options = [
        ConfirmationOption(
            proceed_id,
            f"确认推进到 {package}@{target}",
            f"策略：`{report.exact_upgrade_strategy or 'direct-upgrade'}`；"
            "写入决策后仅表示分析选型完成，不等于实施批准。",
        ),
        ConfirmationOption(
            "defer",
            "本轮不推进（保留分析，不进入计划/实施）",
            "记为 deferred；不阻止同批其他已确认包在闸门解冻后推进。",
        ),
    ]
    append_other_option(question)
    report.decision_status = "needs_choice"
    report.selection_status = "needs_explicit_choice"
    append_unique(
        report.decision_required,
        "精确升级目标已明确，但仍需确认推进（proceed）或延期（defer）后，方可进入计划/实施阶段。",
    )
    return question


def build_confirmation_question(
    report: PackageReport,
    track: str | None = None,
) -> ConfirmationQuestion:
    """One question per package/track, asked verbatim by the Agent.

    Pass `track` to render an alternate-track question after `switch:<track>`.
    Ready questions end with `other` (blocked questions have no options).
    """
    package = report.upgrade.package
    track = track or report.primary_track
    question = ConfirmationQuestion(package=package, track=track)
    routes = package_route_options(report)
    plan = report.refactor_plan
    if track == "pending-removal-evidence":
        question.status = "blocked"
        question.blocked_reason = "尚未确认该包是否被使用；确认使用面之前不提选型问题。"
        missing = sorted(REMOVAL_COVERAGE_AREAS - set(report.removal.coverage_checked))
        question.prerequisites = [
            REMOVAL_COVERAGE_TITLES.get(area, area) for area in missing
        ] + list(report.removal.unknowns)
        return question
    if track == "handle-parent":
        return build_parent_question(report, question)
    if track == "fix-phantom":
        question.prompt = f"`{package}` 是幽灵依赖（代码在用、manifest 未声明），怎么消除？"
        question.options = [
            ConfirmationOption(
                "remove-usage", "移除代码中的用法",
                f"用法位于：{'; '.join(sorted({action.file for action in plan.actions})[:5]) or '见代码修改候选'}",
            ),
            ConfirmationOption(
                "switch-to-declared", "改用已声明的依赖或原生能力承接该用法",
                f"可直接改用的原生能力：{'；'.join(plan.native_routes) or '未登记，需调研'}",
            ),
        ]
        question.options.extend(routes)
        question.prerequisites = list(report.provenance.unknowns)
    elif track == "remove":
        both = report.provenance.kind == "both"
        question.prompt = f"`{package}` 的删除证据已达安全候选门槛，确认删除吗？"
        question.options = [ConfirmationOption(
            "remove",
            "确认移除直接声明（包仍将作为传递依赖存在）" if both else "确认删除该依赖",
            f"证据：{'; '.join(report.removal.evidence) or '见删除评估'}"
            + (f"；仍被 {len(report.provenance.parents)} 个父包引入，摘除声明不会让它离开 lock" if both else ""),
        )]
        if both:
            question.options.append(ConfirmationOption(
                "switch:handle-parent", "同时处置父包（下一步再逐个父包确认）",
                f"父包链：{'; '.join(report.provenance.chains[:3]) or '未建立'}",
            ))
        if routes:
            question.options.append(ConfirmationOption(
                "switch:replace", "改走替换（下一步用下方「改轨问题：replace」选题）",
                "候选：" + "、".join(option.label.split("（")[0] for option in routes),
            ))
        if plan.status == "established":
            question.options.append(ConfirmationOption(
                "switch:native-refactor", "改走原生改造（下一步用下方「改轨问题：native-refactor」）",
                f"改造规模 {plan.scale}（{plan.scale_basis}）",
            ))
    elif track == "replace":
        lead = curated_lead_note(report)
        question.prompt = f"`{package}` 需要处置但未指定目标版本，选择替换成哪个包与版本？"
        if lead:
            question.prompt += f" {lead}"
        question.options = list(routes)
        if not routes:
            question.status = "blocked"
            question.blocked_reason = (
                "尚无已复核的 `replace:<包>@<版本>` 可选项。"
                + (lead or "请完成替代方案调研并回填 --analysis-evidence-file。")
            )
            question.prerequisites = [
                "按「替代方案调研任务」回填 analysis-evidence 候选",
            ]
            return question
        if report.provenance.kind == "both":
            question.options.append(ConfirmationOption(
                "switch:handle-parent", "先处置父包（该包同时被其他包引入）",
                f"父包链：{'; '.join(report.provenance.chains[:3]) or '未建立'}",
            ))
        if report.removal.status == "safe_removal_candidate":
            question.options.append(ConfirmationOption(
                "switch:remove", "改走删除（下一步用下方「改轨问题：remove」）",
                f"删除结论：{report.removal.status}",
            ))
        if plan.status == "established":
            question.options.append(ConfirmationOption(
                "switch:native-refactor", "改走原生改造（下一步用下方「改轨问题：native-refactor」）",
                f"改造规模 {plan.scale}（{plan.scale_basis}）",
            ))
    else:
        lead = curated_lead_note(report)
        if plan.status != "established":
            question.status = "blocked"
            question.blocked_reason = "改造方向尚未建立：缺少声明以外的调用点证据或替代方案调研结论。"
            question.prerequisites = list(plan.unknowns) + (
                ["完成替代方案调研并回填 --analysis-evidence-file"]
                if report.research_status != "reviewed" else []
            )
            return question
        question.prompt = f"`{package}` 本轮主轨为原生改造，确认吗？"
        if lead:
            question.prompt += f" {lead}"
        question.options = [
            ConfirmationOption(
                "native-refactor", "确认：进行原生改造（改用原生能力或自建最小实现）",
                f"规模 {plan.scale}（{plan.scale_basis}）；需自建：{'；'.join(plan.capabilities_to_rebuild)}",
            ),
        ]
        if routes:
            question.options.append(ConfirmationOption(
                "switch:replace", "改走替换（下一步用下方「改轨问题：replace」选题）",
                "候选：" + "、".join(option.label.split("（")[0] for option in routes),
            ))
        if report.removal.status == "safe_removal_candidate":
            question.options.append(ConfirmationOption(
                "switch:remove", "改走删除（下一步用下方「改轨问题：remove」）",
                f"删除结论：{report.removal.status}",
            ))
        if report.provenance.kind == "both" and report.provenance.parents:
            question.options.append(ConfirmationOption(
                "switch:handle-parent", "改走处置父包",
                f"父包链：{'; '.join(report.provenance.chains[:3]) or '未建立'}",
            ))
    append_other_option(question)
    return question


def build_alternate_track_questions(report: PackageReport) -> list[ConfirmationQuestion]:
    """Ready questions for every alternate track so switch:<track> has a verbatim follow-up."""
    questions: list[ConfirmationQuestion] = []
    for track in report.alternate_tracks:
        question = build_confirmation_question(report, track=track)
        if question.status == "ready" and question.options:
            questions.append(question)
    return questions


DECISION_FILE_NAME = "human-decisions.json"


def load_decision_record(path: Path | None) -> tuple[list[HumanDecision], list[str]]:
    """Read recorded selections. Recording a selection is not an implementation approval."""
    warnings: list[str] = []
    if path is None or not path.is_file():
        return [], warnings
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        return [], [f"读取人工决策文件失败：{path}（{error}）"]
    rows = data.get("decisions") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return [], [f"人工决策文件格式不支持：{path}；期望 {{'decisions': [...]}}"]
    decisions: list[HumanDecision] = []
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("package") or "").strip():
            warnings.append("人工决策文件包含缺少 package 的条目；已忽略。")
            continue
        choice = str(row.get("choice") or "").strip()
        package = str(row["package"]).strip()
        if choice.startswith("switch:"):
            warnings.append(
                f"{package} 的记录是路由答案 `{choice}`，不是最终选择；"
                "请改问报告中「改轨问题」对应轨道后再记录结果。"
            )
            continue
        if choice == "handle-parent":
            warnings.append(
                f"{package} 的记录 `handle-parent` 只表示进入父包追问，不是最终选择；"
                "请继续写入 `包<-父包` 追问结果，或改选 pin-override / remove-feature / other。"
            )
            continue
        if choice == "reject-native-refactor":
            warnings.append(
                f"{package} 的记录 `reject-native-refactor` 已废除；"
                "请改选 native-refactor、switch 到替换/删除，或 other。"
            )
            continue
        if choice == "pin-override":
            warnings.append(
                f"{package} 的记录 `pin-override` 缺少精确版本；请改用 pin-override:<包>@<版本>。"
            )
            continue
        decisions.append(HumanDecision(
            package=package,
            track=str(row.get("track") or "").strip(),
            choice=choice,
            selected_package=str(row.get("selected_package") or "").strip(),
            selected_version=str(row.get("selected_version") or "").strip(),
            rationale=str(row.get("rationale") or "").strip(),
            decided_at=str(row.get("decided_at") or "").strip(),
            source=str(row.get("source") or "confirmation-queue").strip(),
        ))
    return decisions, warnings


def revalidate_decision(report: PackageReport, decision: HumanDecision) -> str:
    """Reason the recorded choice no longer holds, or "" when it still does."""
    choice = decision.choice
    if choice == "remove":
        if report.removal.status == "not_viable":
            return "删除结论已变为 not_viable，原“确认删除”不再成立"
        return ""
    if choice == "native-refactor":
        if report.refactor_plan.status != "established":
            return "改造方向已不成立（缺少调用点证据），需重新确认"
        return ""
    if choice in {"remove-usage", "switch-to-declared", "remove-feature", "defer"}:
        return ""
    if choice == "proceed" or choice.startswith("proceed:"):
        if not is_exact_upgrade_target(report.upgrade):
            return "proceed 仅适用于精确升级目标"
        if report.exact_upgrade_status == "blocked":
            return "精确升级仍有实施阻塞项，不能确认推进"
        if choice.startswith("proceed:"):
            body = choice.split(":", 1)[1]
            if "@" not in body:
                return "proceed 选项缺少 包@版本"
            package, version = body.rsplit("@", 1)
            if package != report.upgrade.package:
                return f"proceed 目标包 {package} 与分析包 {report.upgrade.package} 不一致"
            if version != report.upgrade.to_version:
                return (
                    f"proceed 目标版本 {version} 与当前分析目标 "
                    f"{report.upgrade.to_version} 不一致，需重新确认"
                )
            decision.selected_package = decision.selected_package or package
            decision.selected_version = decision.selected_version or version
        else:
            decision.selected_package = decision.selected_package or report.upgrade.package
            decision.selected_version = decision.selected_version or report.upgrade.to_version
        return ""
    if choice.startswith("parent-upgrade:") or choice.startswith("parent-replace:") or choice.startswith("parent-remove:"):
        return ""
    if choice.startswith("pin-override:"):
        pinned = choice.split(":", 1)[1]
        if "@" not in pinned:
            return "pin-override 缺少 包@版本"
        name, version = pinned.rsplit("@", 1)
        if name != report.upgrade.package:
            return f"pin-override 目标包 {name} 与分析包 {report.upgrade.package} 不一致"
        if semver_key(version) is None:
            return f"pin-override 版本 {version} 不是精确 semver"
        return ""
    if choice.startswith("replace:"):
        body = choice.split(":", 1)[1]
        if "@" not in body:
            return "replace 选项缺少 包@版本"
        package, version = body.rsplit("@", 1)
        decision.selected_package = decision.selected_package or package
        decision.selected_version = decision.selected_version or version
    package = decision.selected_package
    version = decision.selected_version
    if not package or not version:
        if decision.source == "other":
            return ""
        return "记录缺少 selected_package 或 selected_version，无法核对"
    if semver_key(version) is None:
        return f"selected_version={version} 不是精确 semver"
    if package == report.upgrade.package:
        return "记录选择了同库版本；未指定目标版本的包不接受同库升级，请改用精确升级模式重跑"
    match = next((item for item in report.alternative_candidates if item.package == package), None)
    if match is None:
        if decision.source == "other":
            return ""
        return f"{package} 已不在本轮替代候选中"
    if match.deprecated:
        return f"{package}@{match.version} 已被 registry 标记弃用"
    if match.constraint_fit == "conflicts":
        return f"{package} 与项目约束冲突：{'; '.join(match.disqualifiers) or '见候选表'}"
    if match.version and version != match.version and decision.source != "other":
        return f"{package} 的推荐版本已变为 {match.version}，原记录 {version} 需重新确认"
    return ""


def mark_disposition_selected(report: PackageReport, decision: HumanDecision) -> None:
    """Record a final open-target disposition. This is the analysis endpoint, not implementation."""
    decision.status = "confirmed"
    report.decision = decision
    report.selection_status = "selected"
    report.recommended_action = DISPOSITION_SELECTED_ACTION
    report.decision_status = "not_needed"
    if report.confirmation is not None:
        report.confirmation.status = "decided"
    report.decision_required = [
        item for item in report.decision_required
        if "尚未选择目标版本" not in item and "替代方案调研尚未回填" not in item
    ]
    append_unique(
        report.decision_required,
        f"已记录分析选型：{decision.choice}；本技能到此结束，实施授权须另行取得。",
    )


def mark_proceed_selected(report: PackageReport, decision: HumanDecision) -> None:
    """Record exact-upgrade proceed/defer. Still analysis endpoint, not implementation approval."""
    decision.status = "confirmed"
    if not decision.track:
        decision.track = PROCEED_EXACT_TRACK
    report.decision = decision
    report.selection_status = "selected"
    report.decision_status = "not_needed"
    if decision.choice == "defer":
        report.recommended_action = DEFERRED_ACTION
        note = "已记录延期：本轮不进入计划/实施；需要时重新确认 proceed。"
    else:
        report.recommended_action = PROCEED_SELECTED_ACTION
        note = (
            f"已记录推进确认：{decision.choice}；"
            "仅完成 Stage A。`batch_implementation_gate=ready` 且调用方批准后才可开计划/实施。"
        )
    if report.confirmation is not None:
        report.confirmation.status = "decided"
    report.decision_required = [
        item for item in report.decision_required
        if "仍需确认推进" not in item and "阻塞未解除" not in item
    ]
    append_unique(report.decision_required, note)


def apply_decisions(reports: list[PackageReport], decisions: list[HumanDecision]) -> list[str]:
    """Attach still-valid decisions, and re-open invalidated ones with the reason."""
    warnings: list[str] = []
    by_package = {report.upgrade.package: report for report in reports}
    parent_confirmed: dict[str, set[str]] = {}
    for decision in decisions:
        package_key = decision.package
        if PARENT_DECISION_SEPARATOR in package_key:
            target_name, _parent_name = package_key.split(PARENT_DECISION_SEPARATOR, 1)
            report = by_package.get(target_name)
            if report is None:
                decision.status = "unknown-package"
                warnings.append(f"人工决策文件中的 {package_key} 不在本次分析清单内；已忽略。")
                continue
            reason = revalidate_decision(report, decision)
            if reason:
                decision.status = "invalidated"
                decision.invalidation_reason = reason
                warnings.append(f"{package_key} 的人工选择已失效：{reason}")
                continue
            decision.status = "confirmed"
            parent_confirmed.setdefault(target_name, set()).add(package_key)
            continue
        report = by_package.get(package_key)
        if report is None:
            decision.status = "unknown-package"
            warnings.append(f"人工决策文件中的 {package_key} 不在本次分析清单内；已忽略。")
            continue
        exact_proceed = (
            is_exact_upgrade_target(report.upgrade)
            or report.primary_track == PROCEED_EXACT_TRACK
        )
        if exact_proceed:
            reason = revalidate_decision(report, decision)
            report.decision = decision
            if reason:
                decision.status = "invalidated"
                decision.invalidation_reason = reason
                if report.confirmation is not None and report.confirmation.status == "ready":
                    report.confirmation.prompt = f"（原选择已失效：{reason}）" + report.confirmation.prompt
                append_unique(report.decision_required, f"原人工选择已失效并需重新确认：{reason}")
                warnings.append(f"{package_key} 的人工选择已失效：{reason}")
                continue
            if decision.choice not in {"defer", "proceed"} and not decision.choice.startswith("proceed:"):
                if decision.source == "other":
                    mark_proceed_selected(report, decision)
                    continue
                decision.status = "invalidated"
                decision.invalidation_reason = "精确升级仅接受 proceed / proceed:包@版本 / defer / other"
                warnings.append(f"{package_key} 的人工选择无效：{decision.invalidation_reason}")
                continue
            mark_proceed_selected(report, decision)
            continue
        if report.primary_track == "not_applicable":
            warnings.append(f"{package_key} 无可用确认轨，人工决策记录不适用；已忽略。")
            continue
        reason = revalidate_decision(report, decision)
        report.decision = decision
        if reason:
            decision.status = "invalidated"
            decision.invalidation_reason = reason
            if report.confirmation is not None:
                report.confirmation.prompt = f"（原选择已失效：{reason}）" + report.confirmation.prompt
            append_unique(report.decision_required, f"原人工选择已失效并需重新确认：{reason}")
            warnings.append(f"{package_key} 的人工选择已失效：{reason}")
            continue
        mark_disposition_selected(report, decision)
    for report in reports:
        target = report.upgrade.package
        expected = {question.package for question in report.parent_questions}
        got = parent_confirmed.get(target, set())
        if not expected or not expected <= got:
            continue
        if report.selection_status == "selected":
            continue
        summary = HumanDecision(
            package=target,
            track="handle-parent",
            choice="parent-followups-complete",
            rationale="全部父包追问已确认",
            source="confirmation-queue",
            status="confirmed",
        )
        mark_disposition_selected(report, summary)
    return warnings


def build_parent_question(report: PackageReport, question: ConfirmationQuestion) -> ConfirmationQuestion:
    """Transitive packages: pick the approach first, then the parents, one at a time."""
    package = report.upgrade.package
    provenance = report.provenance
    if not provenance.parents:
        question.status = "blocked"
        question.blocked_reason = "判定为传递依赖但未解析出父包；无法给出可执行选项。"
        question.prerequisites = list(provenance.unknowns) or [
            "提供可解析的 lockfile，或用包管理器输出补齐依赖边证据"
        ]
        return question
    fixed = [edge for edge in provenance.parents if edge.fix_available == "dropped"]
    question.prompt = (
        f"`{package}` 是传递依赖，只能从父包侧处置。先选处置方式："
        "若选「处置父包」，还须继续回答下方每个父包追问；`handle-parent` 本身不是最终选择。"
    )
    question.options = [
        ConfirmationOption(
            "handle-parent", "处置引入它的父包（下一步逐个父包确认；本项勿写入 decision-file）",
            f"父包 {len(provenance.parents)} 个；"
            + (f"其中 {', '.join(edge.package for edge in fixed)} 的最新稳定版已不再依赖它" if fixed
               else "本轮未发现已摆脱该依赖的父包版本"),
        ),
    ]
    if provenance.override_version:
        detail = f"最低可行版本 {provenance.override_version}：满足项目 Node 且尽量少动父包"
        if provenance.override_breaks:
            detail += f"；会破坏 {'; '.join(provenance.override_breaks)}"
        question.options.append(ConfirmationOption(
            f"pin-override:{package}@{provenance.override_version}",
            f"用 overrides/resolutions 钉到 {package}@{provenance.override_version}", detail,
        ))
    else:
        question.options.append(ConfirmationOption(
            "pin-override", "用 overrides/resolutions 钉版本（版本待解析）",
            "本轮未解析出可行版本："
            + ("；".join(provenance.unknowns) or "需联网核对父包 range 与可用版本")
            + "；解析前勿写入 decision-file",
        ))
    question.options.append(ConfirmationOption(
        "remove-feature", "移除引入该父包的功能",
        f"需确认业务方同意；受影响链路：{'; '.join(provenance.chains[:3]) or '未建立'}",
    ))
    append_other_option(question)
    return question


def build_parent_followups(report: PackageReport) -> list[ConfirmationQuestion]:
    """One follow-up question per parent, asked only after `handle-parent` is chosen."""
    questions: list[ConfirmationQuestion] = []
    for edge in report.provenance.parents[:PARENT_CHAIN_LIMIT]:
        question = ConfirmationQuestion(
            package=f"{report.upgrade.package}{PARENT_DECISION_SEPARATOR}{edge.package}",
            track="handle-parent",
            prompt=f"父包 `{edge.package}@{edge.version or '未解析'}` 怎么处置？",
        )
        target = f"{edge.package}@{edge.latest_stable}" if edge.latest_stable else edge.package
        question.options = [
            ConfirmationOption(
                f"parent-upgrade:{target}",
                f"升级父包到 {edge.latest_stable or '待解析的稳定版'}",
                edge.fix_note or "需核对该版本是否仍引入目标包",
            ),
            ConfirmationOption(f"parent-replace:{edge.package}", "替换该父包", "需另行调研父包的替代方案与迁移成本。"),
            ConfirmationOption(f"parent-remove:{edge.package}", "删除该父包", f"需确认本仓库是否仍在使用 `{edge.package}`。"),
            ConfirmationOption(
                "other", "其他：自行指定父包处置方式与版本",
                "自填内容会以 `source=other` 记录，并按同样的约束重新核对。",
            ),
        ]
        questions.append(question)
    return questions


def refactor_approach(category: str, native_api: str) -> tuple[str, str]:
    """Rewrite approach and behaviour risk for one usage category.

    Category-driven and deliberately generic about the target API: the exact replacement
    still has to be confirmed against official docs, so the text says what to preserve
    rather than pretending to know the final code.
    """
    target = native_api or "自建最小实现"
    table = {
        DECLARATION_CATEGORY: (
            "所有调用点迁移完成后再摘除声明，并同步 lock 与 overrides/resolutions。",
            "过早摘除会导致构建期失败；残留声明会让改造看起来已完成。",
        ),
        "Direct package usage": (
            f"在适配层导出与现用法同名同签名的函数，内部改为 {target}，调用点只改 import 来源。",
            "默认值、错误类型、返回结构与异步时序容易与原库不一致。",
        ),
        "Axios client API": (
            f"以 {target} 重建 client：基础 URL、请求/响应拦截、超时、取消、重试与统一错误封装逐项对齐。",
            "拦截器顺序、错误对象结构、非 2xx 是否抛错、取消语义差异最容易改变业务行为。",
        ),
        "Axios serialization/upload": (
            f"以 {target} 重建序列化与上传：表单编码、Content-Type、二进制与进度事件逐项对齐。",
            "参数序列化格式与上传进度回调在原生 API 下行为不同，易破坏后端契约与交互反馈。",
        ),
        "State manager API": (
            "先固定 store 的公开契约（state 形状、action 语义、订阅时序），再替换内部实现。",
            "订阅触发时机与批量更新语义变化会导致渲染次数与竞态行为改变。",
        ),
        "UI component usage": (
            "按组件逐个建立等价封装，保留 props、插槽/children、事件名与受控/非受控语义。",
            "无障碍属性、键盘交互与表单校验时机最易在自建组件中丢失。",
        ),
        "Build configuration": (
            "以原生或已有构建能力替换该插件职责，逐项对齐产物结构与环境变量注入。",
            "产物路径、分包与 sourcemap 变化会影响部署与线上排障。",
        ),
    }
    return table.get(category, (
        f"按该用法的实际语义建立等价实现（{target}），先保证契约一致再优化内部实现。",
        "需要 Agent 依官方文档确认等价性；未确认前不得假定行为一致。",
    ))


def behavior_parity_checks(dependency_type: str) -> list[str]:
    """What "keep the existing behaviour" concretely means for this dependency type."""
    generic = [
        "输入边界值与空值处理",
        "错误类型、错误码与错误信息结构",
        "并发与重入下的时序",
        "编码、时区与本地化",
        "日志与监控埋点仍能覆盖失败路径",
    ]
    specific = {
        "request": ["超时与重试策略", "取消语义", "非 2xx 是否抛错", "请求/响应拦截顺序", "参数与响应序列化格式", "上传下载进度与流式处理", "凭证、跨域与 XSRF 处理"],
        "state": ["初始化与持久化时机", "订阅触发次数与批量更新", "异步 action 的错误传播", "退出与清理"],
        "router": ["守卫顺序与重定向", "参数与查询解析", "历史导航与刷新", "404 与深链"],
        "ui": ["受控/非受控语义", "键盘与无障碍行为", "表单校验触发时机", "空态与加载态"],
        "framework": ["渲染时机与生命周期顺序", "SSR/hydration 一致性"],
        "build": ["产物结构与分包", "环境变量注入", "sourcemap 与调试能力"],
        "style": ["层叠顺序与主题变量", "响应式断点与暗色模式"],
        "typescript": ["生成类型与公开 API 签名", "严格模式下的可空性"],
        "test": ["runner 配置、transform 与 mock 语义"],
        "dom-runtime": ["事件委托与冒泡顺序", "选择器与集合语义", "异步回调时序"],
    }
    return specific.get(dependency_type, []) + generic


def refactor_scale(files: int, points: int, shared: bool) -> tuple[str, str]:
    """Deterministic size grade from scan counts; no effort estimate is implied."""
    basis = f"调用点 {points} 个、文件 {files} 个、{'跨公共包装器' if shared else '未跨公共包装器'}"
    if files <= REFACTOR_SCALE_SMALL_FILES and points <= REFACTOR_SCALE_SMALL_POINTS and not shared:
        return "S", basis
    if files <= REFACTOR_SCALE_MEDIUM_FILES and points <= REFACTOR_SCALE_MEDIUM_POINTS:
        return "M", basis
    return "L", basis


def build_research_task(report: PackageReport) -> list[str]:
    """Checklist the Agent must complete before this package's options are decidable."""
    usage = sorted({group.split("：", 1)[0] for group in report.refactor_plan.call_site_groups})
    lines = [
        f"能力画像：{'、'.join(usage) if usage else '本轮未建立调用点证据，需先补齐使用面'}",
        f"知识表核对日期：{REPLACEMENT_MAP_REVIEWED}"
        + ("（该包已有登记条目，仍需按本仓库用法复核）" if curated_replacements(report.upgrade.package)
           else "（该包无登记条目，候选须由本轮调研产出）"),
    ]
    lines.extend(f"筛选标准：{item}" for item in RESEARCH_CRITERIA)
    lines.append("回填方式：将复核结论写入 --analysis-evidence-file 的 alternative_candidates，禁止只按下载量或星标选型")
    return lines


def node_support_status(version: str, today: dt.date | None = None) -> tuple[str, str]:
    """Classify a Node version against the reviewed release schedule as of `today`."""
    key = semver_key(version)
    if key is None:
        return "unknown", f"无法解析 Node 版本 {version!r}；请核对官方发布计划"
    major = key[0]
    raw_date = NODE_EOL_DATES.get(major)
    if raw_date is None:
        return "unknown", (
            f"Node {major} 不在已核对的发布计划表内（表最后核对于 {NODE_SCHEDULE_REVIEWED}）；"
            "请对照 https://github.com/nodejs/Release 确认支持状态"
        )
    eol = dt.date.fromisoformat(raw_date)
    current = today or dt.date.today()
    if current >= eol:
        return "eol", (
            f"Node {major} 已于 {raw_date} 结束支持（EOL）；仅在隔离环境中用于项目验证，"
            "并规划升级到受支持主版本"
        )
    if (eol - current).days <= NODE_EOL_WARNING_WINDOW_DAYS:
        return "approaching-eol", f"Node {major} 将于 {raw_date} 进入 EOL；请在该日期前规划运行时升级"
    return "supported", f"Node {major} 官方支持至 {raw_date}"


def normalize_node_version(value: Any) -> str:
    match = VERSION_RE.search(str(value or "").strip())
    return match.group("version") if match else ""


def read_runtime_pin(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            value = line.strip()
            if value and not value.startswith("#"):
                return value
    except OSError:
        return ""
    return ""


def add_node_constraint(items: list[NodeConstraint], constraint: NodeConstraint) -> None:
    key = (constraint.source, constraint.requirement, constraint.kind, constraint.authority, constraint.path)
    if constraint.requirement and key not in {
        (item.source, item.requirement, item.kind, item.authority, item.path) for item in items
    }:
        items.append(constraint)


def scan_installed_node_versions(root: Path, layout: str) -> list[str]:
    if not root.is_dir():
        return []
    try:
        candidates: list[Path]
        if layout == "fnm":
            candidates = list((root / "node-versions").glob("v*/installation")) if (root / "node-versions").is_dir() else []
            names = [candidate.parent.name for candidate in candidates]
        elif layout == "volta":
            base = root / "tools" / "image" / "node"
            names = [candidate.name for candidate in base.iterdir()] if base.is_dir() else []
        elif layout == "asdf":
            base = root / "installs" / "nodejs"
            names = [candidate.name for candidate in base.iterdir()] if base.is_dir() else []
        elif layout == "nvm-posix":
            base = root / "versions" / "node"
            names = [candidate.name for candidate in base.iterdir()] if base.is_dir() else []
        else:
            names = [candidate.name for candidate in root.iterdir()]
    except OSError:
        return []
    return sorted(
        {version for name in names if (version := normalize_node_version(name))},
        key=lambda value: semver_key(value) or (0, 0, 0, 0, ""),
    )


def detect_node_managers() -> tuple[list[str], dict[str, list[str]]]:
    managers: list[str] = []
    installed: dict[str, list[str]] = {}
    home = Path.home()

    def register(name: str, versions: list[str], available: bool) -> None:
        if available and name not in managers:
            managers.append(name)
        if versions:
            installed[name] = versions

    nvm_home_raw = os.environ.get("NVM_HOME", "")
    nvm_home = Path(nvm_home_raw) if nvm_home_raw else Path("")
    nvm_windows_available = os.name == "nt" and bool(shutil.which("nvm") or nvm_home_raw)
    register(
        "nvm-windows",
        scan_installed_node_versions(nvm_home, "nvm-windows") if nvm_home_raw else [],
        nvm_windows_available,
    )

    nvm_dir_raw = os.environ.get("NVM_DIR", "")
    nvm_dir = Path(nvm_dir_raw) if nvm_dir_raw else home / ".nvm"
    register("nvm", scan_installed_node_versions(nvm_dir, "nvm-posix"), nvm_dir.is_dir())

    fnm_roots = [
        Path(os.environ["FNM_DIR"]) if os.environ.get("FNM_DIR") else None,
        home / ".local" / "share" / "fnm",
        Path(os.environ["APPDATA"]) / "fnm" if os.environ.get("APPDATA") else None,
    ]
    fnm_root = next((path for path in fnm_roots if path and path.is_dir()), None)
    register(
        "fnm",
        scan_installed_node_versions(fnm_root, "fnm") if fnm_root else [],
        bool(shutil.which("fnm") or fnm_root),
    )

    volta_root = Path(os.environ.get("VOLTA_HOME") or home / ".volta")
    register(
        "volta",
        scan_installed_node_versions(volta_root, "volta"),
        bool(shutil.which("volta") or volta_root.is_dir()),
    )

    asdf_root = Path(os.environ.get("ASDF_DATA_DIR") or home / ".asdf")
    register(
        "asdf",
        scan_installed_node_versions(asdf_root, "asdf"),
        bool(shutil.which("asdf") or asdf_root.is_dir()),
    )
    return managers, installed


def current_host_node_runtime() -> tuple[str, str]:
    executable = shutil.which("node") or ""
    if not executable:
        return "", ""
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "", executable
    return normalize_node_version(result.stdout or result.stderr), executable


def observed_node_runtime_evidence(project_root: Path) -> list[NodeConstraint]:
    candidates: list[Path] = []
    for relative in (".github/workflows", ".circleci"):
        directory = project_root / relative
        if directory.is_dir():
            candidates.extend(sorted(directory.glob("*.yml")))
            candidates.extend(sorted(directory.glob("*.yaml")))
    for name in (
        ".gitlab-ci.yml", "azure-pipelines.yml", "azure-pipelines.yaml",
        "netlify.toml", "vercel.json", "docker-compose.yml", "docker-compose.yaml",
        "app.json", "cloudbuild.yaml",
    ):
        path = project_root / name
        if path.is_file():
            candidates.append(path)
    candidates.extend(sorted(project_root.glob("Dockerfile*")))
    patterns = (
        ("ci-node-version", re.compile(r"node-version\s*:\s*['\"]?([^'\"#\s,\]]+)", re.I)),
        # netlify.toml `NODE_VERSION = "20"`, Dockerfile `ARG NODE_VERSION=20`,
        # workflow `env: NODE_VERSION: 20`, compose `NODE_VERSION: 20`.
        ("ci-node-version", re.compile(r"NODE_VERSION\s*[:=]\s*['\"]?([0-9][^'\"#\s,\]]*)")),
        (
            "container-node-image",
            re.compile(r"(?:FROM|image\s*:|container\s*:)\s*(?:cimg/|circleci/)?node:([0-9][^@\s]*)", re.I),
        ),
        # vercel.json / serverless `"runtime": "nodejs20.x"`.
        ("container-node-image", re.compile(r"nodejs([0-9]+(?:\.[0-9]+)?)\.x", re.I)),
    )
    evidence: list[NodeConstraint] = []
    for path in candidates[:64]:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        relative = str(path.relative_to(project_root)).replace("\\", "/")
        for kind, pattern in patterns:
            for match in pattern.finditer(text):
                raw = match.group(1).strip().split("-")[0]
                if normalize_node_version(raw) or re.fullmatch(r"v?\d+(?:\.\d+)?(?:\.x)?", raw, re.I):
                    add_node_constraint(
                        evidence,
                        NodeConstraint(relative, raw, kind, "observed", relative),
                    )
    return evidence


def declared_runtime_pins(project_root: Path) -> list[NodeConstraint]:
    """Committed runtime pins outside `.nvmrc`/`.tool-versions` that tooling actually honours."""
    pins: list[NodeConstraint] = []
    npmrc = project_root / ".npmrc"
    if npmrc.is_file():
        match = re.search(
            r"^\s*use-node-version\s*=\s*['\"]?([0-9][^'\"#\s]*)",
            npmrc.read_text(encoding="utf-8", errors="ignore"),
            re.M,
        )
        if match:
            add_node_constraint(
                pins,
                NodeConstraint(".npmrc#use-node-version", match.group(1), "runtime-pin", "authoritative", ".npmrc"),
            )
    for name in ("mise.toml", ".mise.toml", ".mise/config.toml"):
        path = project_root / name
        if not path.is_file():
            continue
        in_tools = False
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                in_tools = stripped.rstrip("]").strip("[").strip() in {"tools", "tools.node"}
                continue
            if not in_tools:
                continue
            match = re.match(r"^node(?:js)?\s*=\s*['\"]([^'\"]+)['\"]", stripped, re.I)
            if match:
                add_node_constraint(
                    pins,
                    NodeConstraint(f"{name}#tools.node", match.group(1), "runtime-pin", "authoritative", name),
                )
                break
    return pins


def lock_declared_runtime_evidence(lock: LockSnapshot | None) -> list[NodeConstraint]:
    """`engines.node` recorded by the lockfile for resolved direct versions.

    Works without `node_modules`, so it is the offline-safe way to recover a project
    Node constraint when the manifest declares none. Only whitelisted toolchain
    packages gate the runtime used for project commands; other dependencies are
    recorded as observed so a stale upper bound cannot fabricate a conflict.
    """
    if lock is None or not lock.declared_engines:
        return []
    lock_name = Path(lock.path).name if lock.path else lock.kind
    evidence: list[NodeConstraint] = []
    for package, requirement in sorted(lock.declared_engines.items()):
        if requirement.strip() in {"*", ">=0", ">=0.0.0"}:
            continue
        version = lock.direct_versions.get(package) or "unknown"
        toolchain = package in TOOLCHAIN_PACKAGES
        add_node_constraint(
            evidence,
            NodeConstraint(
                f"{package}@{version} lock engines.node",
                requirement,
                "toolchain-engine" if toolchain else "dependency-engine",
                "authoritative" if toolchain else "observed",
                lock_name,
            ),
        )
    return evidence


def installed_toolchain_runtime_evidence(
    project_root: Path,
    manifest: ManifestSnapshot,
    lock: LockSnapshot | None = None,
) -> list[NodeConstraint]:
    evidence: list[NodeConstraint] = []
    for package in sorted(set(manifest.packages) & TOOLCHAIN_PACKAGES):
        metadata_path = project_root / "node_modules"
        for part in package.split("/"):
            metadata_path /= part
        metadata_path /= "package.json"
        if not metadata_path.is_file():
            continue
        try:
            metadata = read_json(metadata_path)
        except (OSError, json.JSONDecodeError):
            continue
        requirement = str((metadata.get("engines") or {}).get("node") or "")
        if not requirement:
            continue
        version = str(metadata.get("version") or "unknown")
        locked_version = (lock.direct_versions.get(package) if lock else "") or ""
        authority = "authoritative" if locked_version and locked_version == version else "observed"
        relative = str(metadata_path.relative_to(project_root)).replace("\\", "/")
        add_node_constraint(
            evidence,
            NodeConstraint(
                (
                    f"{package}@{version} installed+lock engines.node"
                    if authority == "authoritative"
                    else f"{package}@{version} installed engines.node"
                ),
                requirement,
                "toolchain-engine",
                authority,
                relative,
            ),
        )
    return evidence


def version_satisfies_all(version: str, constraints: list[NodeConstraint]) -> bool | None:
    outcomes = [semver_satisfies(version, item.requirement) for item in constraints]
    if any(outcome is False for outcome in outcomes):
        return False
    if any(outcome is None for outcome in outcomes):
        return None
    return True


def load_node_runtime_evidence(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = read_json(path)
    runtime = data.get("node_runtime") if isinstance(data, dict) else None
    if runtime is None:
        return {}
    if not isinstance(runtime, dict):
        raise ValueError("analysis evidence node_runtime 必须是对象")
    constraints = runtime.get("additional_project_constraints") or []
    if not isinstance(constraints, list):
        raise ValueError("node_runtime.additional_project_constraints 必须是数组")
    for index, row in enumerate(constraints):
        if not isinstance(row, dict):
            raise ValueError(f"node_runtime.additional_project_constraints[{index}] 必须是对象")
        missing = [field_name for field_name in ("source", "requirement", "kind", "authority") if not row.get(field_name)]
        if missing:
            raise ValueError(
                f"node_runtime.additional_project_constraints[{index}] 缺少字段：" + ", ".join(missing)
            )
        if row["authority"] not in {"authoritative", "observed"}:
            raise ValueError(f"node_runtime.additional_project_constraints[{index}].authority 无效")
    selected = str(runtime.get("selected_project_node") or "")
    if selected and semver_key(selected) is None:
        raise ValueError("node_runtime.selected_project_node 必须是精确 semver")
    return runtime


def assess_node_runtime(
    project_root: Path,
    manifest: ManifestSnapshot,
    reports: list[PackageReport],
    evidence: dict[str, Any] | None = None,
    lock: LockSnapshot | None = None,
) -> NodeRuntimeAssessment:
    evidence = evidence or {}
    assessment = NodeRuntimeAssessment()
    assessment.current_host_node, assessment.current_host_node_path = current_host_node_runtime()
    assessment.available_managers, assessment.installed_versions = detect_node_managers()

    pins = (
        (".nvmrc", "runtime-pin"),
        (".node-version", "runtime-pin"),
    )
    for relative, kind in pins:
        path = project_root / relative
        value = read_runtime_pin(path) if path.is_file() else ""
        if value:
            add_node_constraint(
                assessment.project_constraints,
                NodeConstraint(relative, value, kind, "authoritative", relative),
            )
    for pin in declared_runtime_pins(project_root):
        add_node_constraint(assessment.project_constraints, pin)
    tool_versions = project_root / ".tool-versions"
    if tool_versions.is_file():
        for line in tool_versions.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = re.match(r"\s*nodejs\s+([^\s#]+)", line)
            if match:
                add_node_constraint(
                    assessment.project_constraints,
                    NodeConstraint(".tool-versions", match.group(1), "runtime-pin", "authoritative", ".tool-versions"),
                )
                break
    engine = str(manifest.engines.get("node") or "")
    if engine:
        add_node_constraint(
            assessment.project_constraints,
            NodeConstraint("package.json#engines.node", engine, "project-engine", "authoritative", manifest.path),
        )
    volta_node = str(manifest.volta.get("node") or "")
    if volta_node:
        add_node_constraint(
            assessment.project_constraints,
            NodeConstraint("package.json#volta.node", volta_node, "runtime-pin", "authoritative", manifest.path),
        )
    execution_env_node = str((manifest.pnpm.get("executionEnv") or {}).get("nodeVersion") or "")
    if execution_env_node:
        add_node_constraint(
            assessment.project_constraints,
            NodeConstraint(
                "package.json#pnpm.executionEnv.nodeVersion",
                execution_env_node,
                "runtime-pin",
                "authoritative",
                manifest.path,
            ),
        )
    for report in reports:
        target_engine = str(report.target_engines.get("node") or "")
        if target_engine:
            add_node_constraint(
                assessment.project_constraints,
                NodeConstraint(
                    f"{report.upgrade.package}@{report.upgrade.to_version or 'candidate'} engines.node",
                    target_engine,
                    "target-package-engine",
                    "authoritative",
                    report.package_url,
                ),
            )
    for row in evidence.get("additional_project_constraints") or []:
        constraint = NodeConstraint(
            str(row["source"]),
            str(row["requirement"]),
            str(row["kind"]),
            str(row["authority"]),
            str(row.get("path") or ""),
        )
        add_node_constraint(
            assessment.project_constraints if constraint.authority == "authoritative" else assessment.observed_runtime_evidence,
            constraint,
        )
    assessment.observed_runtime_evidence.extend(observed_node_runtime_evidence(project_root))
    derived = lock_declared_runtime_evidence(lock)
    for constraint in derived:
        add_node_constraint(
            assessment.project_constraints
            if constraint.authority == "authoritative"
            else assessment.observed_runtime_evidence,
            constraint,
        )
    lock_facts = {(item.source.rsplit("@", 1)[0], item.requirement) for item in derived}
    for constraint in installed_toolchain_runtime_evidence(project_root, manifest, lock):
        if (constraint.source.rsplit("@", 1)[0], constraint.requirement) in lock_facts:
            continue
        add_node_constraint(
            assessment.project_constraints
            if constraint.authority == "authoritative"
            else assessment.observed_runtime_evidence,
            constraint,
        )
    unknown = [
        constraint for constraint in assessment.project_constraints
        if semver_satisfies("20.0.0", constraint.requirement) is None
    ]
    if unknown:
        assessment.status = "unknown"
        assessment.blockers.extend(
            f"无法解析 Node 约束：{item.source}={item.requirement}" for item in unknown
        )
    elif not assessment.project_constraints:
        assessment.status = "unknown"
        assessment.warnings.append("未发现权威项目 Node 约束；不能仅凭当前 Node 声称兼容")
    else:
        sample_versions = node_constraint_candidates(
            [constraint.requirement for constraint in assessment.project_constraints]
        )
        if not any(version_satisfies_all(version, assessment.project_constraints) is True for version in sample_versions):
            assessment.status = "constraint-conflict"
            assessment.blockers.append("权威项目 Node 约束没有可识别交集")
        else:
            assessment.status = "pending"

    installed_to_manager: dict[str, str] = {}
    for manager, versions in assessment.installed_versions.items():
        for version in versions:
            installed_to_manager.setdefault(version, manager)
    candidate_versions = set(installed_to_manager)
    if assessment.current_host_node:
        candidate_versions.add(assessment.current_host_node)
    assessment.compatible_installed_versions = sorted(
        [
            version for version in candidate_versions
            if version_satisfies_all(version, assessment.project_constraints) is True
        ],
        key=lambda value: semver_key(value) or (0, 0, 0, 0, ""),
    )

    selected_from_evidence = str(evidence.get("selected_project_node") or "")
    exact_pins = sorted({
        normalize_node_version(item.requirement)
        for item in assessment.project_constraints
        if item.kind == "runtime-pin" and normalize_node_version(item.requirement)
    })
    if len(exact_pins) > 1:
        assessment.status = "constraint-conflict"
        assessment.blockers.append("项目精确 Node pin 不一致：" + ", ".join(exact_pins))
    if selected_from_evidence:
        if version_satisfies_all(selected_from_evidence, assessment.project_constraints) is not True:
            assessment.status = "constraint-conflict"
            assessment.blockers.append(
                f"证据指定的 Node {selected_from_evidence} 不满足全部权威项目约束"
            )
        else:
            assessment.selected_project_node = selected_from_evidence
    elif len(exact_pins) == 1:
        assessment.selected_project_node = exact_pins[0]
    elif assessment.compatible_installed_versions:
        assessment.selected_project_node = preferred_node_version(assessment.compatible_installed_versions)
    else:
        observed_versions = sorted({
            normalize_node_version(item.requirement)
            for item in assessment.observed_runtime_evidence
            if normalize_node_version(item.requirement)
            and version_satisfies_all(normalize_node_version(item.requirement), assessment.project_constraints) is True
        }, key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))
        if observed_versions:
            assessment.selected_project_node = preferred_node_version(observed_versions)

    if assessment.selected_project_node:
        assessment.selected_manager = installed_to_manager.get(assessment.selected_project_node, "")
        assessment.selected_node_support, support_note = node_support_status(assessment.selected_project_node)
        if assessment.selected_node_support != "supported":
            assessment.warnings.append(support_note)
        for observed in assessment.observed_runtime_evidence:
            if observed.kind == "toolchain-engine":
                compatible = semver_satisfies(
                    assessment.selected_project_node, observed.requirement
                )
                if compatible is False:
                    assessment.warnings.append(
                        f"所选 Node {assessment.selected_project_node} 不满足已安装工具链证据 "
                        f"{observed.source}={observed.requirement}；需先与 lock 版本复核"
                    )

    if assessment.status not in {"constraint-conflict", "unknown"}:
        current_compatible = (
            assessment.current_host_node
            and version_satisfies_all(assessment.current_host_node, assessment.project_constraints) is True
        )
        selected_installed = assessment.selected_project_node in candidate_versions
        if current_compatible:
            assessment.status = "compatible-current"
            assessment.selected_project_node = assessment.current_host_node
            assessment.selected_manager = "current"
            assessment.recommended_strategy = "current-runtime"
        elif selected_installed:
            assessment.status = "runtime-switch-required"
            assessment.recommended_strategy = "isolated-child-process"
        elif assessment.available_managers:
            assessment.status = "runtime-missing"
            assessment.blockers.append(
                f"未安装所选兼容 Node {assessment.selected_project_node or '精确版本待确认'}"
            )
        else:
            assessment.status = "manager-missing"
            assessment.blockers.append("需要切换项目 Node，但未检测到受支持的版本管理器")

    if assessment.status == "unknown" and assessment.project_constraints and not assessment.blockers:
        assessment.blockers.append("Node 兼容性尚未完成判定")

    if assessment.status == "unknown" and not assessment.project_constraints:
        evidence_selected = normalize_node_version(str(evidence.get("selected_project_node") or ""))
        if evidence_selected:
            # Human-established exact project Node when the repo has no pin/engines.
            add_node_constraint(
                assessment.project_constraints,
                NodeConstraint(
                    "analysis-evidence#selected_project_node",
                    evidence_selected,
                    "runtime-pin",
                    "authoritative",
                    "",
                ),
            )
            assessment.selected_project_node = evidence_selected
            assessment.selected_manager = installed_to_manager.get(evidence_selected, "")
            assessment.selected_node_support, support_note = node_support_status(evidence_selected)
            if assessment.selected_node_support != "supported":
                assessment.warnings.append(support_note)
            assessment.compatible_installed_versions = sorted(
                [
                    version for version in candidate_versions
                    if version_satisfies_all(version, assessment.project_constraints) is True
                ],
                key=lambda value: semver_key(value) or (0, 0, 0, 0, ""),
            )
            if assessment.current_host_node == evidence_selected:
                assessment.status = "compatible-current"
                assessment.selected_manager = "current"
                assessment.recommended_strategy = "current-runtime"
            elif evidence_selected in candidate_versions:
                assessment.status = "runtime-switch-required"
                assessment.recommended_strategy = "isolated-child-process"
            elif assessment.available_managers:
                assessment.status = "runtime-missing"
                assessment.blockers.append(f"未安装证据指定的项目 Node {evidence_selected}")
            else:
                assessment.status = "manager-missing"
                assessment.blockers.append("需要切换到证据指定的项目 Node，但未检测到受支持的版本管理器")
        else:
            assessment.compatible_installed_versions = []
            assessment.selected_project_node = ""
            assessment.selected_manager = ""
            assessment.recommended_strategy = "read-only-analysis"
            assessment.blockers.append(
                "未发现权威项目 Node 约束；项目命令硬阻断，直至补齐 pin/engines，"
                "或通过 --analysis-evidence-file 指定 selected_project_node 精确版本"
            )

    if assessment.status in {"compatible-current", "runtime-switch-required"}:
        assessment.execution_readiness = "ready-awaiting-approval"
    else:
        assessment.execution_readiness = "blocked"

    if assessment.status == "manager-missing":
        assessment.installation_guidance.append(
            "Windows：winget install CoreyButler.NVMforWindows；"
            "macOS/Linux：curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash。"
            "执行前需单独批准并复核 nvm 官方来源和当前安装版本。"
        )
    elif assessment.status == "runtime-missing" and assessment.selected_project_node:
        version = assessment.selected_project_node
        manager = assessment.available_managers[0] if assessment.available_managers else "nvm"
        commands = {
            "nvm-windows": f"nvm install {version}",
            "nvm": f"nvm install {version}",
            "fnm": f"fnm install {version}",
            "volta": f"volta install node@{version}",
            "asdf": f"asdf install nodejs {version}",
        }
        assessment.installation_guidance.append(commands.get(manager, f"安装 Node {version}"))

    assessment.restoration_plan = [
        "执行前快照 node 路径/版本、PATH、包管理器和 Node 约束文件",
        "项目命令优先在隔离子进程中运行；全局切换仅作受控回退",
        "无论成功、失败或中断都在 finally 中恢复并验证原 Node",
        "验证 .nvmrc/.node-version/.tool-versions/engines/Volta/CI 未被临时兼容处理修改",
    ]
    return assessment


def assess_peer_compatibility(
    report: PackageReport,
    manifest: ManifestSnapshot,
    before_lock: LockSnapshot,
    current_lock: LockSnapshot,
    after_lock: LockSnapshot,
) -> None:
    if not report.target_peer_dependencies:
        report.peer_compatibility_status = "not-applicable"
        report.evidence_dimensions["compatibility"] = "confirmed"
        return
    unknown = False
    for peer, requirement in sorted(report.target_peer_dependencies.items()):
        peer_meta = report.target_peer_dependencies_meta.get(peer) or {}
        optional = bool(peer_meta.get("optional")) if isinstance(peer_meta, dict) else False
        actual = (
            after_lock.direct_versions.get(peer)
            or current_lock.direct_versions.get(peer)
            or before_lock.direct_versions.get(peer)
        )
        if not actual:
            manifest_peer = manifest.packages.get(peer)
            if manifest_peer:
                actual = clean_version(manifest_peer.spec)
        if not actual or semver_key(actual) is None:
            if not optional:
                unknown = True
                report.peer_compatibility_conflicts.append(f"{peer} {requirement}：未解析到 workspace 精确版本")
            continue
        compatible = semver_satisfies(actual, str(requirement))
        if compatible is False:
            report.peer_compatibility_conflicts.append(f"{peer}@{actual} 不满足 {requirement}")
        elif compatible is None and not optional:
            unknown = True
            report.peer_compatibility_conflicts.append(f"{peer}@{actual} 与范围 {requirement} 无法自动判定")
    if any("不满足" in conflict for conflict in report.peer_compatibility_conflicts):
        report.peer_compatibility_status = "incompatible"
        report.evidence_dimensions["compatibility"] = "ambiguous"
        report.evidence_completeness = "ambiguous"
        report.warnings.append("目标 peerDependencies 与 workspace 版本冲突：" + "；".join(report.peer_compatibility_conflicts))
    elif unknown:
        report.peer_compatibility_status = "unknown"
        report.evidence_dimensions["compatibility"] = "candidate"
    else:
        report.peer_compatibility_status = "compatible"
        report.evidence_dimensions["compatibility"] = "confirmed"


def string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def exact_candidate_version(value: Any, label: str) -> str:
    version = clean_version(str(value or ""))
    if not version or semver_key(version) is None:
        raise ValueError(f"{label} 必须提供精确 semver 版本，当前为：{value!r}")
    return version


def validate_compliance_fields(
    package: str,
    version: str,
    status: str,
    criteria_checked: list[str],
    evidence_urls: list[str],
) -> None:
    if status not in COMPLIANCE_STATUSES:
        raise ValueError(f"{package}@{version} 的 compliance_status 不支持：{status}")
    if status == "eligible" and (not criteria_checked or not evidence_urls):
        raise ValueError(
            f"{package}@{version} 标记 eligible 时必须提供 criteria_checked 和 evidence_urls"
        )
    if status == "eligible":
        normalized = {str(item).strip().lower() for item in criteria_checked}
        missing = sorted(REQUIRED_ALTERNATIVE_CRITERIA - normalized)
        if missing:
            raise ValueError(
                f"{package}@{version} 标记 eligible 时缺少必核标准：{', '.join(missing)}"
            )


def eligible_alternative_candidates(report: PackageReport) -> list[AlternativeCandidate]:
    """Return only fully reviewed, compatible, non-deprecated replacement choices."""
    eligible: list[AlternativeCandidate] = []
    for candidate in report.alternative_candidates:
        criteria = {str(item).strip().lower() for item in candidate.criteria_checked}
        if (
            candidate.origin == "analysis-evidence"
            and candidate.compliance_status == "eligible"
            and semver_key(candidate.version) is not None
            and REQUIRED_ALTERNATIVE_CRITERIA <= criteria
            and bool(candidate.evidence_urls)
            and not candidate.deprecated
            and candidate.constraint_fit == "fits"
            and not candidate.disqualifiers
        ):
            eligible.append(candidate)
    return eligible[:3]


def target_candidate_from_evidence(
    owner_package: str,
    row: dict[str, Any],
    existing: TargetCandidate | None = None,
) -> TargetCandidate:
    version = exact_candidate_version(row.get("version"), f"{owner_package} 同库候选")
    base = asdict(existing) if existing else {}
    status = str(row.get("compliance_status", base.get("compliance_status", "unknown"))).strip() or "unknown"
    criteria = string_list(row.get("criteria_checked", base.get("criteria_checked", [])))
    evidence_urls = string_list(row.get("evidence_urls", base.get("evidence_urls", [])))
    source = str(row.get("source", base.get("source", ""))).strip()
    if source and source not in evidence_urls:
        evidence_urls.append(source)
    validate_compliance_fields(owner_package, version, status, criteria, evidence_urls)
    return TargetCandidate(
        package=owner_package,
        version=version,
        candidate_type=str(row.get("candidate_type", base.get("candidate_type", "agent-researched"))),
        published=str(row.get("published", base.get("published", ""))),
        peer_dependencies=row.get("peer_dependencies", row.get("peerDependencies", base.get("peer_dependencies", {}))) or {},
        engines=row.get("engines", base.get("engines", {})) or {},
        rationale=str(row.get("rationale", base.get("rationale", ""))),
        compatibility=str(row.get("compatibility", base.get("compatibility", ""))),
        compliance_and_maintenance=str(row.get("compliance_and_maintenance", base.get("compliance_and_maintenance", ""))),
        migration_cost=str(row.get("migration_cost", base.get("migration_cost", ""))),
        validation_scope=str(row.get("validation_scope", base.get("validation_scope", ""))),
        rollback_difficulty=str(row.get("rollback_difficulty", base.get("rollback_difficulty", ""))),
        source=source,
        confidence=str(row.get("confidence", base.get("confidence", "medium"))),
        compliance_status=status,
        criteria_checked=criteria,
        disqualifiers=string_list(row.get("disqualifiers", base.get("disqualifiers", []))),
        evidence_urls=evidence_urls,
        checked_at=str(row.get("checked_at", base.get("checked_at", ""))),
    )


def alternative_candidate_from_evidence(owner_package: str, row: dict[str, Any]) -> AlternativeCandidate:
    package = str(row.get("package") or "").strip()
    if not package:
        raise ValueError(f"{owner_package} 的替代库候选缺少 package")
    version = exact_candidate_version(row.get("version"), f"{owner_package} 替代库 {package}")
    status = str(row.get("compliance_status") or "unknown").strip()
    criteria = string_list(row.get("criteria_checked"))
    evidence_urls = string_list(row.get("evidence_urls"))
    source = str(row.get("source") or "").strip()
    if source and source not in evidence_urls:
        evidence_urls.append(source)
    validate_compliance_fields(package, version, status, criteria, evidence_urls)
    return AlternativeCandidate(
        package=package,
        version=version,
        rationale=str(row.get("rationale") or ""),
        compatibility=str(row.get("compatibility") or ""),
        compliance_and_maintenance=str(row.get("compliance_and_maintenance") or ""),
        migration_cost=str(row.get("migration_cost") or ""),
        validation_scope=str(row.get("validation_scope") or ""),
        rollback_difficulty=str(row.get("rollback_difficulty") or ""),
        source=source,
        confidence=str(row.get("confidence") or "low"),
        compliance_status=status,
        criteria_checked=criteria,
        disqualifiers=string_list(row.get("disqualifiers")),
        evidence_urls=evidence_urls,
        checked_at=str(row.get("checked_at") or ""),
    )


def removal_from_evidence(package: str, row: dict[str, Any]) -> RemovalAssessment:
    status = str(row.get("status") or "not_assessed").strip()
    if status not in REMOVAL_STATUSES:
        raise ValueError(f"{package} 的 removal.status 不支持：{status}")
    evidence = string_list(row.get("evidence"))
    blockers = string_list(row.get("blockers"))
    unknowns = string_list(row.get("unknowns"))
    coverage = string_list(row.get("coverage_checked"))
    if status == "safe_removal_candidate":
        missing = sorted(REMOVAL_COVERAGE_AREAS - set(coverage))
        if missing or not evidence or unknowns:
            raise ValueError(
                f"{package} 标记 safe_removal_candidate 需要完整 coverage、非空 evidence 且无 unknowns；"
                f"缺少 coverage：{', '.join(missing) or '无'}"
            )
    if status == "not_viable" and not (evidence or blockers):
        raise ValueError(f"{package} 标记 not_viable 时必须提供 evidence 或 blockers")
    return RemovalAssessment(
        status=status,
        evidence=evidence,
        blockers=blockers,
        unknowns=unknowns,
        confidence=str(row.get("confidence") or "low"),
        coverage_checked=coverage,
    )


def load_analysis_evidence(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    data = read_json(path)
    packages = data.get("packages") if isinstance(data, dict) else None
    if not isinstance(packages, dict):
        raise ValueError("analysis evidence JSON 必须包含对象字段 packages")
    result: dict[str, dict[str, Any]] = {}
    for package, row in packages.items():
        if not isinstance(row, dict):
            raise ValueError(f"analysis evidence packages.{package} 必须是对象")
        result[str(package)] = row
    return result


def apply_analysis_evidence(reports: list[PackageReport], evidence: dict[str, dict[str, Any]]) -> None:
    reports_by_package = {report.upgrade.package: report for report in reports}
    unknown_packages = sorted(set(evidence) - set(reports_by_package))
    if unknown_packages:
        raise ValueError("analysis evidence 包不在本次清单中：" + ", ".join(unknown_packages))
    for package, row in evidence.items():
        report = reports_by_package[package]
        if row.get("reason") and not report.upgrade.reason:
            report.upgrade.reason = str(row["reason"])
            report.decision_required = [
                decision for decision in report.decision_required
                if not decision.startswith("尚未建立治理或不合规依据")
            ]
        if row.get("target_candidates"):
            # Same-package versions are not a route for an open target. Ignoring instead of
            # failing keeps older evidence files usable, but the intent has to be redirected.
            append_unique(
                report.warnings,
                f"已忽略 {package}.target_candidates：未指定目标版本的包不接受同库候选；"
                "确需升级请改用 --upgrade package::<精确版本> 走精确升级模式。",
            )
        alternatives = row.get("alternative_candidates") or []
        if alternatives:
            reviewed = [
                alternative_candidate_from_evidence(package, candidate)
                for candidate in alternatives
                if isinstance(candidate, dict)
            ]
            if len(reviewed) != len(alternatives):
                raise ValueError(f"{package}.alternative_candidates 每一项必须是对象")
            # A human verdict replaces the curated suggestion for the same package;
            # unreviewed curated candidates stay visible so no route is silently dropped.
            reviewed_packages = {candidate.package for candidate in reviewed}
            report.alternative_candidates = reviewed + [
                candidate for candidate in report.alternative_candidates
                if candidate.package not in reviewed_packages
            ]
        if row.get("removal") is not None:
            if not isinstance(row["removal"], dict):
                raise ValueError(f"{package}.removal 必须是对象")
            report.removal = removal_from_evidence(package, row["removal"])
        for source_row in row.get("official_sources") or []:
            if not isinstance(source_row, dict) or not source_row.get("kind") or not source_row.get("url"):
                raise ValueError(f"{package}.official_sources 每一项必须包含 kind 和 url")
            add_official_source(
                report.official_sources,
                str(source_row["kind"]),
                str(source_row["url"]),
                status=str(source_row.get("status") or "confirmed"),
                title=str(source_row.get("title") or ""),
                version=str(source_row.get("version") or ""),
                reason=str(source_row.get("reason") or ""),
            )
        dimensions = row.get("evidence_dimensions") or {}
        if not isinstance(dimensions, dict):
            raise ValueError(f"{package}.evidence_dimensions 必须是对象")
        for dimension, status in dimensions.items():
            if dimension not in EVIDENCE_DIMENSIONS:
                raise ValueError(f"{package}.evidence_dimensions 包含未知维度：{dimension}")
            if status not in {"confirmed", "candidate", "missing", "ambiguous", "not-applicable", "offline"}:
                raise ValueError(f"{package}.{dimension} 的证据状态无效：{status}")
            report.evidence_dimensions[dimension] = str(status)
        report.evidence_completeness = evidence_completeness(report.evidence_dimensions, True)
        report.constraints.extend(string_list(row.get("constraints")))


def append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def reconcile_open_target_report(report: PackageReport) -> None:
    if report.upgrade.to_version or report.analysis_mode == "exact-upgrade":
        return
    report.decision_status = "needs_choice"
    report.selection_status = "needs_explicit_choice"
    # Curated suggestions are leads, not researched conclusions, so they never move the
    # recommendation ahead of the removal-first order.
    reviewed_alternatives = [
        candidate for candidate in report.alternative_candidates
        if candidate.origin == "analysis-evidence"
    ]
    eligible_alternatives = eligible_alternative_candidates(report)
    report.research_status = (
        "reviewed" if reviewed_alternatives
        else "curated-only" if report.alternative_candidates
        else "pending"
    )
    if report.alternative_candidates:
        append_unique(
            report.decision_required,
            "已列出替代库候选与处置方案选项；选择哪条路径由人决定，本报告不自动选型。",
        )
    if report.provenance.kind == "transitive":
        report.recommended_action = "handle-parent-packages"
        append_unique(
            report.decision_required,
            "该包是传递依赖：既不能从 manifest 删除，也无法在本仓库改造；"
            "只能处置父包或用 overrides/resolutions 钉版本。",
        )
    elif report.provenance.kind == "phantom":
        report.recommended_action = "fix-phantom-dependency"
        append_unique(
            report.decision_required,
            "该包是幽灵依赖：代码在用但 manifest 未声明，靠依赖提升才可用；"
            "需移除用法或改用已声明的依赖／原生能力，不接受“补个声明了事”。",
        )
    elif report.removal.status == "safe_removal_candidate":
        report.recommended_action = "review-removal"
        append_unique(
            report.decision_required,
            "删除证据满足安全候选门槛；删除仍需人显式选择，未获选择时继续比较替代方案。",
        )
    elif eligible_alternatives:
        report.recommended_action = "research-replacement"
        append_unique(report.decision_required, "替代库候选仍需人显式选择。")
    elif report.removal.status == "requires_migration":
        report.recommended_action = (
            "plan-native-refactor"
            if report.refactor_plan.status == "established" and report.research_status == "reviewed"
            else "research-replacement"
        )
        append_unique(
            report.decision_required,
            "已确认存在真实使用点，不能直接删除；必须先评估合格替代库，确认无可行替代后才能进入原生改造。",
        )
    elif report.refactor_plan.status == "established":
        report.recommended_action = "plan-native-refactor"
        append_unique(
            report.decision_required,
            "替代包本轮未建立可行候选；剩余可行方向是改用平台原生能力或自建最小实现。",
        )
    else:
        report.recommended_action = (
            "blocked-pending-options" if report.removal.status == "not_viable" else "review-removal"
        )
    report.disposition_options = build_disposition_options(report)
    has_option = bool(
        eligible_alternatives
        or report.refactor_plan.status == "established"
        or report.removal.status == "safe_removal_candidate"
        or (report.provenance.kind in {"transitive", "both"} and report.provenance.parents)
        or report.provenance.kind == "phantom"
    )
    # The gate is a completeness signal, not a recommendation: `recommended_action` keeps
    # naming the next step (removal review stays valid while removal is still open).
    report.option_status = "available" if has_option else "missing"
    if not has_option:
        append_unique(
            report.decision_required,
            "本轮未产出任何可执行选项（删除／替代包／原生改造／父包处置）；"
            "补齐候选研究与调用点证据前，报告不得标记为 complete。",
        )
    if report.research_status != "reviewed" and report.provenance.kind != "transitive":
        # A package the repository never calls cannot be swapped for another one; its
        # route runs through the parents, so replacement research does not apply.
        append_unique(
            report.decision_required,
            "替代方案调研尚未回填人工复核结论；见「替代方案调研任务」清单。",
        )


def collect_package_report(upgrade: Upgrade, args: argparse.Namespace) -> PackageReport:
    dependency_type = infer_dependency_type(upgrade.package, upgrade.dependency_type)
    normalized = Upgrade(
        upgrade.package,
        clean_version(upgrade.from_version),
        clean_version(upgrade.to_version),
        dependency_type,
        upgrade.reason,
        upgrade.source,
        upgrade.intent,
    )
    change_type = (
        classify_change(upgrade.from_version, upgrade.to_version)
        if upgrade.intent == "exact-upgrade"
        else ("removed" if upgrade.intent == "removal-assessment" else "unknown")
    )
    report = PackageReport(
        normalized,
        package_url(upgrade.package),
        change_type=change_type,
        analysis_mode=upgrade.intent,
        decision_status="needs_choice",
        recommended_action="upgrade" if upgrade.to_version else "assess",
        selection_status="needs_explicit_choice",
        primary_track=PROCEED_EXACT_TRACK if upgrade.to_version else "not_applicable",
    )
    if upgrade.to_version:
        report.decision_required.append(
            "精确升级目标已明确，但仍需确认推进（proceed）或延期（defer）后，方可进入计划/实施阶段。"
        )
    else:
        report.decision_required.append("未指定目标版本；需要由人在删除、替换、原生改造或父包处置之间确认方案，同库升级不在选项内。")
    if not upgrade.reason and upgrade.intent in {"auto-assess", "compliance-assessment", "target-discovery"}:
        report.decision_required.append("尚未建立治理或不合规依据；先核对仓库政策、安全、license、兼容性和维护状态。")
    endpoint = normalized.to_version or normalized.from_version or "unknown"
    evidence_root: Path | None = getattr(args, "upstream_evidence_root", None)
    persist_evidence = (
        upstream_evidence_enabled(args)
        and evidence_root is not None
        and is_exact_upgrade_target(normalized)
    )
    if args.offline:
        if persist_evidence and local_upstream_readback_allowed(args):
            local_report = collect_exact_upgrade_from_local_evidence(normalized, args, report)
            if local_report is not None:
                return local_report
        report.notes.append(VersionNote(endpoint, change_type=report.change_type, release_notes="离线模式：需要人工收集官方发布证据。", changelog="离线模式：需要人工收集官方变更日志。", sources=[package_url(upgrade.package, endpoint)], evidence_status="offline"))
        report.evidence_completeness = "offline"
        report.evidence_dimensions = {dimension: "offline" for dimension in EVIDENCE_DIMENSIONS}
        report.warnings.append("使用了离线模式（调用方显式 --offline）；报告不能标记为 complete。")
        if not normalized.to_version:
            report.alternative_candidates = build_alternative_candidates(upgrade.package, args, report.warnings)
        return report
    reset_fetch_diagnostics(upgrade.package)
    metadata = request_json(registry_url(upgrade.package), args.timeout)
    metadata_origin = "network"
    # Local upstream-evidence readback is gated on explicit --offline only. A failed
    # fetch while online must not silently look like an offline/intranet fallback.
    if (
        not isinstance(metadata, dict)
        and persist_evidence
        and local_upstream_readback_allowed(args)
    ):
        local_metadata = read_upstream_registry(evidence_root, upgrade.package)
        if isinstance(local_metadata, dict):
            metadata = local_metadata
            metadata_origin = "local"
            report.used_local_upstream_evidence = True
            report.warnings.append("获取 npm registry 元数据失败；已回读本地 upstream-evidence/registry.json。")
    if not isinstance(metadata, dict):
        diagnostics = drain_fetch_diagnostics(upgrade.package)
        report.notes.append(VersionNote(endpoint, change_type=report.change_type, release_notes="无法获取 npm 元数据。", changelog="需要人工复核上游资料。", sources=[package_url(upgrade.package, endpoint)], evidence_status="missing", release_status="missing", changelog_status="missing"))
        report.warnings.append("获取 npm registry 元数据失败。")
        for item in diagnostics:
            append_unique(report.warnings, f"上游抓取失败：{item}")
        report.evidence_dimensions["registry"] = "missing"
        report.evidence_dimensions["release"] = "missing"
        report.evidence_dimensions["changelog"] = "missing"
        report.evidence_completeness = "partial"
        if persist_evidence and evidence_root is not None:
            write_upstream_fetch_failure(
                Path(evidence_root),
                upgrade.package,
                stage="registry",
                diagnostics=diagnostics or ["npm registry 元数据不可用"],
                from_version=normalized.from_version,
                to_version=normalized.to_version,
            )
            report.warnings.append(
                f"已写入 upstream-evidence 抓取失败记录：{upstream_package_dir(Path(evidence_root), upgrade.package) / 'fetch-failure.json'}"
            )
        return report
    if persist_evidence and metadata_origin == "network":
        write_upstream_registry(evidence_root, upgrade.package, metadata)
    report.evidence_dimensions["registry"] = "confirmed" if metadata_origin == "network" else "candidate"
    report.repository_url, report.repository_directory, report.repository_source_version = repository_details_for_version(metadata, endpoint)
    report.homepage = str(metadata.get("homepage") or "")
    if normalized.to_version:
        target_metadata = (metadata.get("versions") or {}).get(normalized.to_version, {}) or {}
        report.target_peer_dependencies = target_metadata.get("peerDependencies") or {}
        report.target_peer_dependencies_meta = target_metadata.get("peerDependenciesMeta") or {}
        report.target_engines = target_metadata.get("engines") or {}
    elif upgrade.intent != "removal-assessment":
        # No same-package candidates: a package listed without a target has to go, and a
        # version bump inside the same package does not resolve why it was listed.
        report.recommended_action = "review-removal"
    if not normalized.to_version:
        report.alternative_candidates = build_alternative_candidates(upgrade.package, args, report.warnings)
    if normalized.to_version:
        selected, warnings, interval_complete = versions_in_range(metadata, normalized, args.max_versions)
    else:
        selected = [normalized.from_version] if normalized.from_version else []
        warnings = ["未形成可分析的精确目标区间；需要继续研究候选版本、替代库或删除方案。"]
        interval_complete = False
    report.warnings.extend(warnings)
    times = metadata.get("time") or {}
    for source in known_official_sources(upgrade.package, normalized.from_version, normalized.to_version):
        add_official_source(
            report.official_sources, source.kind, source.url, status=source.status,
            title=source.title, version=source.version, reason=source.reason,
        )
    add_official_source(report.official_sources, "registry", report.package_url, status="confirmed", title="npm package metadata")
    release_cache: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    changelog_cache: dict[tuple[str, str], tuple[str, str]] = {}
    release_confirmed = bool(selected)
    changelog_confirmed = bool(selected)
    source_ambiguous = False
    repository_statuses: list[str] = []
    persisted_version_rows: list[dict[str, Any]] = []
    if normalized.from_version:
        from_repository, _, _ = repository_details_for_version(metadata, normalized.from_version)
        report.repository_lineage[normalized.from_version] = from_repository or "missing"

    version_contexts: list[dict[str, Any]] = []
    for version in selected:
        version_metadata = (metadata.get("versions") or {}).get(version, {}) or {}
        repository_url, repository_directory, repository_source = repository_details_for_version(metadata, version)
        slug = github_slug(repository_url)
        report.repository_lineage[version] = repository_url or "missing"
        if repository_source == "npm-top-level-fallback":
            report.warnings.append(f"{version} 缺少版本级 repository；已使用 npm 顶层字段兜底，需校验历史归属。")
        if repository_url:
            add_official_source(
                report.official_sources, "repository", repository_url,
                status="confirmed" if repository_source == "npm-version-metadata" else "candidate",
                version=version, reason=repository_source,
            )
        version_contexts.append({
            "version": version,
            "version_metadata": version_metadata,
            "repository_url": repository_url,
            "repository_directory": repository_directory,
            "repository_source": repository_source,
            "slug": slug,
        })

    workers = max(1, int(args.network_workers))
    slugs = list(dict.fromkeys(context["slug"] for context in version_contexts if context["slug"]))
    branch_rows = parallel_map_ordered(
        lambda slug: (slug, github_default_branch(slug, args.timeout)),
        slugs,
        workers,
    )
    branch_cache = dict(branch_rows)

    def validate_context(context: dict[str, Any]) -> tuple[str, str, str]:
        if not context["slug"]:
            return "missing", "repository 不是可识别的 GitHub URL", context["repository_directory"]
        return validate_version_repository(
            context["slug"],
            context["repository_directory"],
            upgrade.package,
            context["version"],
            context["version_metadata"],
            args.timeout,
        )

    validations = parallel_map_ordered(validate_context, version_contexts, workers)
    for context, (validation, reason, validated_directory) in zip(version_contexts, validations):
        context["default_branch"] = branch_cache.get(context["slug"], "")
        context["repository_validation"] = validation
        context["repository_validation_reason"] = reason
        if validated_directory and not context["repository_directory"]:
            context["repository_directory"] = validated_directory
            if context["version"] == endpoint:
                report.repository_directory = validated_directory

    repository_groups: dict[tuple[str, str], dict[str, Any]] = {}
    for context in version_contexts:
        if not context["slug"]:
            continue
        cache_key = (context["slug"], context["repository_directory"])
        group = repository_groups.setdefault(cache_key, {
            "slug": context["slug"],
            "repository_directory": context["repository_directory"],
            "default_branch": context["default_branch"],
            "versions": [],
        })
        group["versions"].append(context["version"])

    repository_tasks: list[tuple[str, tuple[str, str], dict[str, Any]]] = []
    for cache_key, group in repository_groups.items():
        repository_tasks.append(("release", cache_key, group))
        repository_tasks.append(("changelog", cache_key, group))

    def fetch_repository_task(
        task: tuple[str, tuple[str, str], dict[str, Any]]
    ) -> tuple[str, tuple[str, str], Any]:
        kind, cache_key, group = task
        if kind == "release":
            result = fetch_github_releases(
                group["slug"],
                upgrade.package,
                args.timeout,
                args.max_github_pages,
                group["repository_directory"],
                group["versions"],
            )
        else:
            result = fetch_changelog(
                group["slug"],
                group["repository_directory"],
                args.timeout,
                [group["default_branch"]],
                group["default_branch"],
            )
        return kind, cache_key, result

    for kind, cache_key, result in parallel_map_ordered(fetch_repository_task, repository_tasks, workers):
        if kind == "release":
            release_cache[cache_key] = result
        else:
            changelog_cache[cache_key] = result

    def resolve_version_sources(context: dict[str, Any]) -> tuple[dict[str, Any], str, str, str]:
        slug = context["slug"]
        version = context["version"]
        repository_directory = context["repository_directory"]
        default_branch = context["default_branch"]
        if not slug:
            return {}, "", "", ""
        cache_key = (slug, repository_directory)
        releases = release_cache.get(cache_key, {})
        release: dict[str, Any] = releases.get(canonical_version(version), {})
        if not release or release.get("status") == "ambiguous":
            direct_release = fetch_github_release_by_tag(
                slug, upgrade.package, version, args.timeout, repository_directory
            )
            if direct_release:
                release = direct_release
        if not release or release.get("status") == "ambiguous":
            tag_evidence = fetch_github_tag(slug, upgrade.package, version, args.timeout)
            if tag_evidence:
                release = tag_evidence
        changelog, changelog_url = changelog_cache.get(cache_key, ("", ""))
        changelog, changelog_url, changelog_text = resolve_historical_changelog(
            slug,
            upgrade.package,
            version,
            repository_directory,
            context["version_metadata"],
            default_branch,
            changelog,
            changelog_url,
            args.timeout,
            args.max_note_chars,
        )
        return release, changelog, changelog_url, changelog_text

    resolved_sources = parallel_map_ordered(resolve_version_sources, version_contexts, workers)
    for context, (release, changelog, changelog_url, changelog_text) in zip(version_contexts, resolved_sources):
        version = context["version"]
        version_metadata = context["version_metadata"]
        repository_url = context["repository_url"]
        repository_directory = context["repository_directory"]
        repository_source = context["repository_source"]
        slug = context["slug"]
        default_branch = context["default_branch"]
        repository_validation = context["repository_validation"]
        repository_validation_reason = context["repository_validation_reason"]
        if slug:
            cache_key = (slug, repository_directory)
            collection = release_cache.get(cache_key, {}).get("_collection", {})
            if collection.get("status") == "truncated":
                append_unique(report.warnings, str(collection.get("reason") or "GitHub release 分页不完整。"))
            if (
                repository_validation in {"candidate", "ambiguous"}
                and repository_source == "npm-version-metadata"
                and release.get("source_kind") == "github-release"
                and release_matches_package(release, upgrade.package)
            ):
                repository_validation = "confirmed"
                repository_validation_reason = "版本级 npm repository 与 package-aware GitHub Release 相互印证"
        if not slug:
            source_ambiguous = True
            repository_validation, repository_validation_reason = "missing", "repository 不是可识别的 GitHub URL"
        if default_branch:
            if repository_validation == "confirmed":
                report.repository_validation_status = "confirmed"
                report.evidence_dimensions["repository"] = "confirmed"
            else:
                report.repository_validation_status = repository_validation
                report.evidence_dimensions["repository"] = repository_validation
                append_unique(report.warnings, f"{version} 仓库历史校验：{repository_validation_reason}")
        elif repository_url:
            report.repository_validation_status = "candidate"
            report.evidence_dimensions["repository"] = "candidate"
        else:
            report.repository_validation_status = "missing"
            report.evidence_dimensions["repository"] = "missing"
        repository_statuses.append(repository_validation)
        release_text = truncate(release.get("body", ""), args.max_note_chars)
        sources = [package_url(upgrade.package, version)]
        if release.get("url"):
            sources.append(release["url"])
            add_official_source(
                report.official_sources,
                "release" if release.get("source_kind") == "github-release" else "tag",
                str(release["url"]),
                status="confirmed" if release.get("status") == "substantive" else "candidate",
                version=version,
                reason=str(release.get("reason") or release.get("status") or ""),
            )
        pointer_urls = release.get("pointer_urls") or [] if release.get("status") == "pointer" else []
        for pointer_url in pointer_urls:
            sources.append(pointer_url)
            add_official_source(
                report.official_sources, "release-linked-page", pointer_url,
                status="candidate", version=version,
                reason="GitHub Release 正文仅提供该链接，需跟随并核验正文。",
            )
            if not release_text or release.get("status") == "pointer":
                linked_text = fetch_linked_release_text(pointer_url, args.timeout, args.max_note_chars)
                if linked_text:
                    release_text = linked_text
                    release["status"] = "substantive-linked"
                    add_official_source(
                        report.official_sources, "release-linked-page", pointer_url,
                        status="confirmed", version=version,
                        reason="已跟随 Release 指针并提取到正文。",
                    )
        if changelog_text and changelog_url:
            sources.append(changelog_url)
            add_official_source(
                report.official_sources, "changelog", changelog_url,
                status="confirmed", version=version,
            )
            full_changelog_section = extract_changelog_section(changelog, version, max(args.max_note_chars * 10, 20_000))
            for linked_url in extract_complete_urls(full_changelog_section)[:12]:
                sources.append(linked_url)
                add_official_source(
                    report.official_sources, "changelog-linked-page", linked_url,
                    status="candidate", version=version,
                    reason="版本 changelog 条目指向该官方页面。",
                )
                if not release_text and is_release_page_candidate(linked_url):
                    linked_text = fetch_linked_release_text(linked_url, args.timeout, args.max_note_chars)
                    if linked_text:
                        release_text = linked_text
                        release["status"] = "substantive-linked"
                        add_official_source(
                            report.official_sources, "changelog-linked-page", linked_url,
                            status="confirmed", version=version,
                            reason="已跟随 changelog 版本链接并提取到发布正文。",
                        )
        release_status = str(release.get("status") or "missing")
        changelog_status = "confirmed" if changelog_text else ("document-only" if changelog else "missing")
        note_release = release_text or (
            "该版本只有官方 Git tag，未找到 GitHub Release 正文。"
            if release_status == "tag-only"
            else "未找到可确认属于目标包的 GitHub Release 正文。"
        )
        note_changelog = changelog_text or (
            "已找到 changelog 文档，但未能提取该版本章节。"
            if changelog else "未找到官方 changelog 文档。"
        )
        evidence_origin = "network"
        if persist_evidence and local_upstream_readback_allowed(args):
            local_version = read_upstream_version_evidence(evidence_root, upgrade.package, version)
            note_release, note_changelog, release_status, changelog_status, used_local = merge_note_fields_from_local(
                note_release, note_changelog, release_status, changelog_status, local_version,
            )
            if used_local:
                evidence_origin = "local"
                report.used_local_upstream_evidence = True
                append_unique(report.warnings, f"{version} 部分官方证据来自本地 upstream-evidence。")
                if local_version:
                    for url in local_version.get("sources") or []:
                        if url:
                            sources.append(str(url))
                    if not repository_url and local_version.get("repository_url"):
                        repository_url = str(local_version.get("repository_url") or "")
                        repository_source = str(local_version.get("repository_source") or repository_source)
                        repository_validation = str(
                            local_version.get("repository_validation") or repository_validation
                        )
        if release_status == "ambiguous":
            status = "ambiguous"
            source_ambiguous = True
        elif release_status in {"substantive", "substantive-linked"} and changelog_status == "confirmed":
            status = "confirmed"
        elif release_status in {"substantive", "substantive-linked", "pointer", "thin", "tag-only"} or changelog_status == "confirmed":
            status = "partial"
        else:
            status = "missing"
        release_confirmed = release_confirmed and release_status in {"substantive", "substantive-linked"}
        changelog_confirmed = changelog_confirmed and changelog_status == "confirmed"
        note = VersionNote(
            version=version,
            published=str(times.get(version) or "")[:10] or str(release.get("published") or ""),
            change_type=classify_change(normalized.from_version, version),
            release_notes=note_release,
            changelog=note_changelog,
            sources=list(dict.fromkeys(sources)),
            evidence_status=status,
            release_status=release_status,
            changelog_status=changelog_status,
            repository_url=repository_url,
            repository_source=repository_source,
            repository_validation=repository_validation,
        )
        report.notes.append(note)
        if persist_evidence and evidence_root is not None:
            # Download-first: always persist per-version sources.json so the pack exists
            # even when release/changelog bodies are missing (rate-limit / 404 / parse miss).
            # Keep package-level diagnostics; attach a snapshot into sources.json.
            with _FETCH_DIAGNOSTICS_LOCK:
                version_diagnostics = list(_FETCH_DIAGNOSTICS.get(upgrade.package, []))[-12:]
            write_upstream_version_evidence(
                evidence_root,
                upgrade.package,
                note,
                evidence_origin=evidence_origin if evidence_origin == "local" else "network",
                changelog_document=changelog if changelog and not changelog_text else "",
                fetch_diagnostics=version_diagnostics,
            )
            persisted_version_rows.append({
                "version": version,
                "status": status,
                "origin": evidence_origin if evidence_origin == "local" else "network",
                "release_status": release_status,
                "changelog_status": changelog_status,
                "fetch_diagnostics": version_diagnostics[:10],
            })
    if persist_evidence and persisted_version_rows and evidence_root is not None:
        update_upstream_manifest(
            evidence_root,
            package=upgrade.package,
            from_version=normalized.from_version,
            to_version=normalized.to_version,
            versions=persisted_version_rows,
        )
        append_unique(
            report.warnings,
            "精确升级默认下载并落盘 upstream-evidence/；报告以该本地证据包为 release/changelog 依据之一。",
        )
    if "ambiguous" in repository_statuses:
        report.repository_validation_status = "ambiguous"
        report.evidence_dimensions["repository"] = "ambiguous"
    elif "missing" in repository_statuses:
        report.repository_validation_status = "missing"
        report.evidence_dimensions["repository"] = "missing"
    elif repository_statuses and all(status == "confirmed" for status in repository_statuses):
        report.repository_validation_status = "confirmed"
        report.evidence_dimensions["repository"] = "confirmed"
    else:
        report.repository_validation_status = "candidate"
        report.evidence_dimensions["repository"] = "candidate"
    if release_confirmed:
        report.evidence_dimensions["release"] = "confirmed"
    elif source_ambiguous:
        report.evidence_dimensions["release"] = "ambiguous"
    elif any(note.release_status not in {"missing"} for note in report.notes):
        report.evidence_dimensions["release"] = "candidate"
    else:
        report.evidence_dimensions["release"] = "missing"
    if changelog_confirmed:
        report.evidence_dimensions["changelog"] = "confirmed"
    elif any(note.changelog_status not in {"missing"} for note in report.notes):
        report.evidence_dimensions["changelog"] = "candidate"
    else:
        report.evidence_dimensions["changelog"] = "missing"
    migration_sources = [source for source in report.official_sources if source.kind == "migration"]
    report.evidence_dimensions["migration"] = "candidate" if migration_sources else (
        "not-applicable" if report.change_type in {"patch", "same", "added", "removed"} else "missing"
    )
    for dimension in ("security", "support", "license"):
        matching = [source for source in report.official_sources if source.kind == dimension]
        report.evidence_dimensions[dimension] = "candidate" if matching else "missing"
    if report.repository_url:
        slug = github_slug(report.repository_url)
        if slug:
            add_official_source(report.official_sources, "security", f"https://github.com/{slug}/security", title="GitHub security")
            add_official_source(report.official_sources, "license", f"https://github.com/{slug}", title="Repository license")
            report.evidence_dimensions["security"] = "candidate"
            report.evidence_dimensions["license"] = "candidate"
    if report.homepage:
        add_official_source(report.official_sources, "homepage", report.homepage, status="candidate")
    leftover_diagnostics = drain_fetch_diagnostics(upgrade.package)
    for item in leftover_diagnostics:
        append_unique(report.warnings, f"上游抓取：{item}")
    report.evidence_completeness = evidence_completeness(report.evidence_dimensions, interval_complete)
    if len(set(report.repository_lineage.values())) > 1:
        report.warnings.append("版本区间跨越不同 repository；已按版本拆分 release/changelog 取证。")
    if source_ambiguous:
        report.evidence_completeness = "ambiguous"
    maybe_require_github_reachability_after_empty_evidence(report, args)
    return report


def is_code_scan_candidate(path: Path) -> bool:
    if path.name.lower() in LOCK_NAMES:
        return False
    return path.suffix.lower() in TEXT_EXTENSIONS or any(path.name.lower().startswith(hint) for hint in CONFIG_FILE_HINTS)


def iter_code_files(project_root: Path, max_files: int, max_file_bytes: int) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    warnings: list[str] = []
    for root, dirs, names in os.walk(project_root):
        dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
        for name in sorted(names):
            path = Path(root) / name
            if not is_code_scan_candidate(path):
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            files.append(path)
            if len(files) >= max_files:
                warnings.append(f"静态扫描在 {max_files} 个文件处停止；结果可能不完整。")
                return files, warnings
    return files, warnings


def read_text_file(path: Path) -> str | None:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            return None
    return None


def package_reference_regex(package: str) -> re.Pattern[str]:
    escaped = re.escape(package)
    return re.compile(rf"(?:from\s+|import\s*\(|require\s*\(|import\s+)\s*['\"]{escaped}(?:/[^'\"]*)?['\"]|['\"]{escaped}['\"]\s*:")


def validation_for_type(dependency_type: str) -> str:
    return {
        "framework": "执行类型检查/构建、渲染、路由冒烟和核心业务流程回归。",
        "router": "验证守卫、重定向、参数、嵌套路由、深链、刷新、历史导航和 404。",
        "state": "验证初始化、持久化、订阅、异步 action、权限状态和退出清理。",
        "dom-runtime": "按官方 Upgrade Guide 分阶段验证选择器、事件、Ajax/Deferred、插件、全局加载顺序和 Migrate 警告。",
        "ui": "验证 Form/Table/Modal/Drawer/Upload/日期行为，并执行定向视觉回归。",
        "request": "验证成功、业务错误、401/403/500、超时、取消、序列化、上传和下载。",
        "build": "验证开发/生产一致性、插件、环境变量、资源、分包、sourcemap 和构建产物。",
        "typescript": "执行类型检查，并验证生成类型、JSX/模块兼容性和 CI。",
        "style": "执行样式构建、主题、响应式/暗色模式和视觉回归。",
        "test": "执行受影响测试，并验证 runner、transform、mock 和环境配置。",
    }.get(dependency_type, "执行定向类型、构建、单测、冒烟和受影响业务流程回归。")


def specific_code_patterns(report: PackageReport) -> list[tuple[re.Pattern[str], str, str]]:
    package = report.upgrade.package.lower()
    patterns: list[tuple[re.Pattern[str], str, str]] = []
    if package == "vue" or package.startswith("@vue/"):
        patterns.extend([
            (re.compile(r"\bnew\s+Vue\b|\bVue\.use\b|\bVue\.prototype\b"), "Vue 应用入口", "Vue 全局应用 API 发生变化；需对照迁移指南核验。"),
            (re.compile(r"\bVue\.(?:set|delete)\b|\$set\b|\$delete\b"), "Vue 响应式", "Vue 响应式辅助 API 发生变化；需验证基于 Proxy 的更新行为。"),
        ])
    if "vue-router" in package:
        patterns.append((re.compile(r"\bnew\s+Router\b|\bVueRouter\b|\baddRoutes\b"), "Vue Router API", "路由创建和动态路由 API 在大版本间发生变化。"))
    if package in {"react", "react-dom", "@types/react", "@types/react-dom"}:
        patterns.append((re.compile(r"\bReactDOM\.render\b|\bhydrate\b"), "React 根节点 API", "根节点渲染 API 需要按目标版本核对迁移要求。"))
    if "react-router" in package:
        patterns.append((re.compile(r"\bSwitch\b|\bRedirect\b|\bwithRouter\b|\buseHistory\b|\bcomponent=|\brender="), "React Router API", "旧版路由 API 已变化或移除。"))
    if report.upgrade.dependency_type == "state":
        patterns.append((re.compile(r"\bmapState\b|\bmapGetters\b|\bmapActions\b|\bcreateStore\b|\bdefineStore\b"), "状态管理 API", "Store 初始化和订阅行为需要按目标版本核验。"))
    if package == "axios":
        patterns.extend([
            (re.compile(r"\bCancelToken\b|\baxios\.interceptors\b|\baxios\.create\b"), "Axios 客户端 API", "Axios 大版本的请求生命周期和取消行为需要迁移核验。"),
            (re.compile(r"\bFormData\b|multipart/form-data|\bparamsSerializer\b"), "Axios 序列化/上传", "Axios 序列化和 FormData 行为需要回归覆盖。"),
        ])
    if report.upgrade.dependency_type == "ui":
        patterns.append((re.compile(r"\b(?:Table|Form|Modal|Drawer|Upload|DatePicker|Select|Pagination)\b"), "UI 组件用法", "组件属性、事件、默认值、主题和视觉行为可能发生变化。"))
    if report.upgrade.dependency_type == "build":
        patterns.append((re.compile(r"\bdefineConfig\b|\bplugins\s*:|\bloadEnv\b|\bmodule\.exports\b"), "构建配置", "必须验证构建、插件和模块格式兼容性。"))
    return patterns


def point_priority(path: str, change_type: str, category: str) -> str:
    if CRITICAL_RE.search(path) or "Build configuration" in category:
        return "P0"
    if change_type in {"major", "removed"} or SHARED_RE.search(path):
        return "P1"
    return "P2"


def upstream_reason_for(report: PackageReport, reason: str) -> str:
    source = next((url for note in report.notes for url in note.sources if "github.com" in url), report.package_url)
    return f"{reason} 证据候选：{source}"


def declaration_reason(report: PackageReport) -> str:
    if report.upgrade.to_version:
        return (
            f"依赖声明本身需要改到目标版本 {report.upgrade.to_version}；"
            "这是升级动作的落点，不是 API 适配候选。"
        )
    return "依赖声明是本次治理对象的入口；目标未选定前不改动该行。"


def declaration_recommendation(report: PackageReport) -> str:
    if not report.upgrade.to_version:
        return "保持不变，直到人工在删除、替换、原生改造或父包处置之间做出选择。"
    spec = report.manifest_spec or "当前声明"
    return (
        f"获得实施批准后，把 {spec} 更新到 {report.upgrade.to_version} 对应的声明范围，"
        "并通过包管理器同步 lock；不要手工编辑 lockfile。"
    )


def analyze_code_modification_points(project_root: Path, reports: list[PackageReport], max_points: int, max_scan_files: int, max_file_bytes: int) -> tuple[list[CodeModificationPoint], list[str], list[str]]:
    files, warnings = iter_code_files(project_root, max_scan_files, max_file_bytes)
    test_files = [str(path.relative_to(project_root)).replace("\\", "/") for path in files if TEST_RE.search(str(path).replace("\\", "/"))]
    points: list[CodeModificationPoint] = []
    seen: set[tuple[str, str, int, str]] = set()
    scanners = [
        (report, package_reference_regex(report.upgrade.package), specific_code_patterns(report))
        for report in reports
    ]
    for path in files:
        text = read_text_file(path)
        if text is None:
            continue
        relative = str(path.relative_to(project_root)).replace("\\", "/")
        is_config = any(path.name.lower().startswith(hint) for hint in CONFIG_FILE_HINTS)
        lines = text.splitlines()
        for report, package_regex, patterns in scanners:
            direct_file = bool(package_regex.search(text))
            if not direct_file:
                continue
            for line_number, raw in enumerate(lines, 1):
                line = raw.strip()
                if not line:
                    continue
                if package_regex.search(line):
                    is_declaration = is_config and path.name == "package.json"
                    category = DECLARATION_CATEGORY if is_config else "Direct package usage"
                    key = (report.upgrade.package, relative, line_number, category)
                    if key not in seen:
                        seen.add(key)
                        if is_declaration:
                            # The declaration is the edit itself, not an API adaptation candidate.
                            reason = declaration_reason(report)
                            recommendation = declaration_recommendation(report)
                            validation = "确认 lock 直接解析版本与目标一致，且 overrides/resolutions 未意外锁定旧版本。"
                            priority = "P0" if report.upgrade.to_version else "P1"
                        else:
                            reason = upstream_reason_for(
                                report,
                                f"此处直接用法必须核对 {report.upgrade.package} "
                                f"{report.upgrade.from_version}->{report.upgrade.to_version} 的完整变更区间。",
                            )
                            recommendation = "对照官方迁移证据确认 import、选项、props、类型和 peer 相关配置。"
                            validation = validation_for_type(report.upgrade.dependency_type)
                            priority = point_priority(relative, report.change_type, category)
                        points.append(CodeModificationPoint(
                            report.upgrade.package, relative, line_number, category, truncate(line, 240),
                            reason, recommendation, validation, priority, "high",
                        ))
                for pattern, category, reason in patterns:
                    if not pattern.search(line):
                        continue
                    key = (report.upgrade.package, relative, line_number, category)
                    if key in seen:
                        continue
                    seen.add(key)
                    points.append(CodeModificationPoint(
                        report.upgrade.package, relative, line_number, category, truncate(line, 240),
                        upstream_reason_for(report, reason),
                        "将该候选与准确的上游条目逐项核对；仅在文档变化确实适用时进行适配。",
                        validation_for_type(report.upgrade.dependency_type), point_priority(relative, report.change_type, category), "medium",
                    ))
                if len(points) >= max_points:
                    warnings.append(f"代码修改候选达到 {max_points} 条上限；需要继续进行定向复核。")
                    return points, warnings, test_files
    return points, warnings, test_files


def assess_removal(report: PackageReport, points: list[CodeModificationPoint]) -> None:
    if report.analysis_mode not in {"auto-assess", "removal-assessment", "compliance-assessment"}:
        return
    package_points = [point for point in points if point.package == report.upgrade.package]
    usage_points = [
        point for point in package_points
        if not (Path(point.file).name == "package.json" and point.category == DECLARATION_CATEGORY)
    ]
    declared_direct = bool(report.manifest_field)
    observed = bool(report.observed_lock_versions)
    evidence: list[str] = []
    blockers: list[str] = []
    if declared_direct:
        evidence.append(f"manifest 在 {report.manifest_field} 中声明 `{report.upgrade.package}`。")
    if observed:
        evidence.append(f"lockfile 观察到版本：{', '.join(report.observed_lock_versions)}。")
    if usage_points:
        files = sorted({point.file for point in usage_points})
        blockers.append("发现代码或配置使用：" + ", ".join(files[:12]))
        report.removal = RemovalAssessment(
            status="requires_migration",
            evidence=evidence,
            blockers=blockers,
            unknowns=[],
            confidence="high" if any(point.confidence == "high" for point in usage_points) else "medium",
            coverage_checked=["business", "runtime"],
        )
        if report.analysis_mode == "removal-assessment":
            report.recommended_action = "plan-migration-before-removal"
            report.decision_required.append("当前证据表明删除需要迁移；必须先替换或消除已确认的使用点，再由人决定是否删除。")
        else:
            report.recommended_action = "research-replacement"
            report.decision_required.append("删除需要先迁移已确认的使用点；需要研究替代库、原生改造或隔离/fork 方案。")
        return

    unknowns = [
        "需要通过代码知识图谱确认公共包装器和间接调用方。",
        "需要排除 alias、barrel export、dynamic import、运行时注册和配置驱动加载。",
        "需要检查 package scripts、构建、测试、类型、样式、代码生成和 CI 使用。",
        "需要确认 peerDependencies 和间接 consumer；静态扫描零命中不能证明可安全删除。",
    ]
    report.removal = RemovalAssessment(
        status="uncertain",
        evidence=evidence + ["有边界的静态扫描未建立确定使用点。"],
        blockers=[],
        unknowns=unknowns,
        confidence="low",
        coverage_checked=[],
    )
    report.recommended_action = "review-removal"
    report.decision_status = "needs_choice"
    report.decision_required.append("删除结论仍为 uncertain；补齐调用图和动态/构建期使用证据后，由人决定是否删除。")
    if report.analysis_mode != "removal-assessment":
        report.decision_required.append("若最终不删除，需要研究替代库或原生改造；同库升级不作为本轮选项。")


def baseline_for(report: PackageReport, manifest: ManifestSnapshot, before_lock: LockSnapshot, current_lock: LockSnapshot, after_lock: LockSnapshot) -> None:
    package = report.upgrade.package
    manifest_package = manifest.packages.get(package)
    if manifest_package:
        report.manifest_field = manifest_package.field
        report.manifest_spec = manifest_package.spec
        if manifest_package.catalog_spec:
            report.manifest_spec = f"{manifest_package.spec} → {manifest_package.catalog_spec}"
            append_unique(
                report.warnings,
                f"{package} 通过 pnpm catalog 声明；有效范围 {manifest_package.catalog_spec}"
                f"（来源 {manifest_package.catalog_source}），改动范围时需同步 catalog。",
            )
        elif manifest_package.spec.startswith("catalog:"):
            append_unique(
                report.warnings,
                f"{package} 声明为 {manifest_package.spec}，但未能在 pnpm-workspace.yaml 中解析到对应 catalog 条目；"
                "请人工确认有效范围。",
            )
    report.lock_kind = current_lock.kind if current_lock.kind != "none" else (after_lock.kind if after_lock.kind != "none" else before_lock.kind)
    report.lock_path = current_lock.path or after_lock.path or before_lock.path
    report.before_lock_version = before_lock.direct_versions.get(package, "")
    report.current_lock_version = current_lock.direct_versions.get(package, "")
    report.after_lock_version = after_lock.direct_versions.get(package, "")
    report.before_lock_versions = sorted(set(before_lock.all_versions.get(package, [])), key=lambda value: semver_key(value) or (0, 0, 0, 0, value))
    report.current_lock_versions = sorted(set(current_lock.all_versions.get(package, [])), key=lambda value: semver_key(value) or (0, 0, 0, 0, value))
    report.after_lock_versions = sorted(set(after_lock.all_versions.get(package, [])), key=lambda value: semver_key(value) or (0, 0, 0, 0, value))
    observed = report.before_lock_versions + report.current_lock_versions + report.after_lock_versions
    report.observed_lock_versions = sorted(set(observed), key=lambda value: semver_key(value) or (0, 0, 0, 0, value))
    before = report.before_lock_version
    current = report.current_lock_version
    after = report.after_lock_version
    if before:
        report.baseline_status = "matches_from" if before == report.upgrade.from_version else "mismatch"
    elif current:
        if current == report.upgrade.from_version:
            report.baseline_status = "matches_from"
        elif current == report.upgrade.to_version:
            report.baseline_status = "matches_to"
        else:
            report.baseline_status = "mismatch"
    elif after:
        report.baseline_status = "matches_to" if after == report.upgrade.to_version else "mismatch"
    elif report.upgrade.from_version and (
        report.upgrade.from_version in report.before_lock_versions
        or report.upgrade.from_version in report.current_lock_versions
    ):
        report.baseline_status = "matches_from"
    elif report.after_lock_versions:
        report.baseline_status = (
            "matches_to"
            if set(report.after_lock_versions) == {report.upgrade.to_version}
            else "mismatch"
        )
    else:
        report.baseline_status = "unknown"


def direct_upgrade_command(report: PackageReport) -> str:
    package_at_version = f"{report.upgrade.package}@{report.upgrade.to_version}"
    dev = report.manifest_field == "devDependencies"
    optional = report.manifest_field == "optionalDependencies"
    peer = report.manifest_field == "peerDependencies"
    if report.lock_kind == "pnpm":
        flag = " -D" if dev else (" -O" if optional else (" --save-peer" if peer else ""))
        return f"pnpm add {package_at_version}{flag}"
    if report.lock_kind == "yarn":
        flag = " -D" if dev else (" -O" if optional else (" -P" if peer else ""))
        return f"yarn add {package_at_version}{flag}"
    if report.lock_kind == "bun":
        flag = " -d" if dev else (" --optional" if optional else (" --peer" if peer else ""))
        return f"bun add {package_at_version}{flag}"
    flag = " --save-dev" if dev else (" --save-optional" if optional else (" --save-peer" if peer else ""))
    return f"npm install {package_at_version}{flag}"


def lock_convergence_commands(report: PackageReport, needs_override: bool) -> list[str]:
    package = report.upgrade.package
    target = report.upgrade.to_version
    if report.lock_kind == "pnpm":
        commands = (
            [f'pnpm pkg set "pnpm.overrides.{package}={target}"', "pnpm install"]
            if needs_override else [direct_upgrade_command(report), "pnpm dedupe"]
        )
        return commands + [f"pnpm why {package}"]
    if report.lock_kind == "yarn":
        commands = (
            [f'在 package.json 的 resolutions 中设置 "{package}": "{target}"', "yarn install"]
            if needs_override else [direct_upgrade_command(report), "yarn dedupe"]
        )
        return commands + [f"yarn why {package}"]
    if report.lock_kind == "bun":
        commands = (
            [f'在 package.json 的 overrides/resolutions 中设置 "{package}": "{target}"', "bun install"]
            if needs_override else [direct_upgrade_command(report), "bun install"]
        )
        return commands + ["bun pm ls --all"]
    commands = (
        [f'npm pkg set "overrides.{package}={target}"', "npm install"]
        if needs_override else [direct_upgrade_command(report), "npm dedupe"]
    )
    return commands + [f"npm ls {package} --all"]


def finalize_exact_upgrade_report(
    report: PackageReport,
    runtime: NodeRuntimeAssessment,
) -> None:
    """Produce a deterministic exact-target plan without executing any command."""
    if report.analysis_mode != "exact-upgrade" or not report.upgrade.to_version:
        return
    report.exact_upgrade_status = "ready"
    target = report.upgrade.to_version
    parents = report.provenance.parents
    needs_override = report.provenance.kind == "transitive"
    if report.provenance.kind == "transitive":
        report.exact_upgrade_strategy = "parent-first-with-override-fallback"
    elif report.provenance.kind == "both":
        report.exact_upgrade_strategy = "direct-upgrade-plus-parent-convergence"
    else:
        report.exact_upgrade_strategy = "direct-upgrade"

    if report.provenance.kind in {"unknown", "phantom"}:
        append_unique(
            report.implementation_blockers,
            f"依赖来源为 {report.provenance.kind}，无法形成安全的精确升级命令",
        )
    incompatible_parents = [
        f"{edge.package}@{edge.version} 要求 {edge.requirement or '未建立'}"
        for edge in parents
        if not edge.requirement or semver_satisfies(target, edge.requirement) is not True
    ]
    if incompatible_parents:
        append_unique(
            report.implementation_blockers,
            "目标版本不满足当前父依赖范围；必须先解析并升级/替换父依赖的精确兼容版本："
            + "；".join(incompatible_parents),
        )
    if report.peer_compatibility_status != "compatible" and report.peer_compatibility_status != "not-applicable":
        append_unique(
            report.implementation_blockers,
            "目标 peerDependencies 未确认兼容：" + (
                "；".join(report.peer_compatibility_conflicts) or report.peer_compatibility_status
            ),
        )
    if runtime.status != "compatible-current":
        append_unique(
            report.implementation_blockers,
            "当前运行环境不能直接执行该升级；先调整 Node/工具链或目标版本："
            + "；".join(runtime.blockers or [runtime.status]),
        )

    if report.after_lock_versions:
        report.residual_lock_versions = [
            version for version in report.after_lock_versions if version != target
        ]
        report.target_convergence_status = (
            "confirmed" if not report.residual_lock_versions and target in report.after_lock_versions
            else "blocked-residual-versions"
        )
        if report.residual_lock_versions:
            append_unique(
                report.implementation_blockers,
                "升级后 lock 仍残留非目标版本：" + ", ".join(report.residual_lock_versions),
            )
    else:
        report.target_convergence_status = "verification-required"

    if not incompatible_parents:
        report.implementation_commands = lock_convergence_commands(report, needs_override)
    if report.implementation_blockers:
        report.exact_upgrade_status = "blocked"
        report.recommended_action = "adjust-environment-or-target"
    else:
        report.recommended_action = "upgrade-to-exact-target"


def dependency_type_score(dependency_type: str, change_type: str) -> int:
    """Weight the package family's blast radius by how large the version change actually is."""
    base = DEPENDENCY_TYPE_BASE.get(dependency_type, 2)
    trivial, moderate, breaking = DEPENDENCY_TYPE_BY_CHANGE.get(base, (1, 2, 2))
    if change_type in TRIVIAL_CHANGES:
        return trivial
    if change_type in BREAKING_CHANGES:
        return breaking
    return moderate


def risk_score(report: PackageReport, points: list[CodeModificationPoint], test_files: list[str], business_override: str, coverage_override: str) -> RiskAssessment:
    uncertainties: list[str] = []
    package_points = [point for point in points if point.package == report.upgrade.package]
    # A dependency declaration proves the package is installed, not that code depends on it,
    # so declaration-only hits must not inflate the usage-scope factor.
    files = {point.file for point in package_points if point.category != DECLARATION_CATEGORY}
    declaration_only = bool(package_points) and not files
    if not files:
        usage = 0
        if declaration_only:
            uncertainties.append("仅发现依赖声明，未发现源码使用点；使用范围需通过知识图谱或动态加载核查后复算")
    elif len(files) == 1 and not any(SHARED_RE.search(path) for path in files):
        usage = 1
    elif len(files) <= 5 and not any(SHARED_RE.search(path) for path in files):
        usage = 3
    else:
        usage = 5
    if business_override == "high":
        business = 5
    elif business_override == "medium":
        business = 3
    elif business_override == "low":
        business = 1
    elif any(CRITICAL_RE.search(path) for path in files):
        business = 5
    elif files:
        # No critical-path evidence yet: score the uncertainty instead of assuming a main flow.
        business = 2
        uncertainties.append(
            "业务关键性按未确认计 2 分；补齐路由/调用方映射后用 --business-criticality 复算"
        )
    else:
        business = 1
    if report.baseline_status == "mismatch":
        lock = 5
    elif report.baseline_status == "unknown":
        lock = 3
    elif len(report.observed_lock_versions) > 1:
        lock = 3
    else:
        lock = 1
    if coverage_override == "adequate":
        coverage = 0
    elif coverage_override == "partial":
        coverage = 2
    elif coverage_override == "missing":
        coverage = 3
    else:
        stems = {Path(path).stem.lower() for path in files}
        related = any(any(stem and stem in Path(test).stem.lower() for stem in stems) for test in test_files)
        coverage = 0 if related and files else (2 if test_files else 3)
    peer = 5 if report.peer_compatibility_status == "incompatible" else (
        2 if report.peer_compatibility_status == "unknown" else 0
    )
    if peer == 2:
        uncertainties.append("目标 peerDependencies 或 workspace 精确版本未确认；按未知计 2 分")
    if report.change_type == "unknown":
        uncertainties.append("版本变化类型无法解析；按 minor 同级计 3 分")
    factors = dict(zip(RISK_FACTORS, (
        CHANGE_SCORES.get(report.change_type, 3),
        dependency_type_score(report.upgrade.dependency_type, report.change_type),
        usage,
        business,
        lock,
        coverage,
        peer,
    )))
    total = sum(factors.values())
    automatic = "Low" if total <= RISK_LOW_MAX else ("Medium" if total <= RISK_MEDIUM_MAX else "High")
    final = automatic
    rationale: list[str] = []
    red_line = business == 5 and report.upgrade.dependency_type in {"framework", "router", "state", "dom-runtime", "ui", "request", "build"}
    evidence_gap = report.change_type == "major" and report.evidence_completeness != "complete"
    peer_conflict = report.peer_compatibility_status == "incompatible"
    if report.baseline_status == "mismatch" or red_line or evidence_gap or peer_conflict:
        final = "High"
        if report.baseline_status == "mismatch":
            rationale.append("基线不一致属于强制高风险信号。")
        if red_line:
            rationale.append("高影响依赖触达业务关键路径。")
        if evidence_gap:
            rationale.append("大版本升级的上游证据不完整或存在歧义。")
        if peer_conflict:
            rationale.append("目标 peerDependencies 与 workspace 精确版本冲突。")
    return RiskAssessment(factors, total, automatic, final, rationale, uncertainties)


def breaking_candidates(report: PackageReport) -> list[str]:
    pattern = re.compile(r"(?:breaking|deprecated|deprecation|removed|migration|incompatible)", re.I)
    candidates: list[str] = []
    for note in report.notes:
        for source_text in (note.release_notes, note.changelog):
            for line in source_text.splitlines():
                if pattern.search(line):
                    value = truncate(re.sub(r"\s+", " ", line), 240)
                    if value and value not in candidates:
                        candidates.append(value)
                if len(candidates) >= 8:
                    return candidates
    return candidates


def business_module(path: str) -> tuple[str, str]:
    normalized = path.replace("\\", "/")
    match = re.search(r"(?:pages?|views?|routes?)/([^/]+)", normalized, re.I)
    module = match.group(1) if match else (Path(normalized).parent.name or "共享/基础设施")
    flows = [name for name in ("login", "permission", "order", "upload", "form", "table", "route", "build") if name in normalized.lower()]
    return module, ", ".join(flows) or UNMAPPED_FLOW


def overall_level(reports: list[PackageReport]) -> str:
    rank = {"Low": 0, "Medium": 1, "High": 2}
    return max((report.risk.final_level for report in reports), key=lambda value: rank.get(value, 1), default="Medium")


def md_cell(value: Any, max_chars: int = 420) -> str:
    text = truncate(re.sub(r"\s+", " ", str(value or "")).strip(), max_chars)
    # `truncate` re-introduces a newline that would split the row and break the
    # table's column count, so collapse once more after truncating.
    text = re.sub(r"\s+", " ", text).strip()
    return html.escape(text, quote=False).replace("|", "\\|") or "-"


def visible_code_category(value: str) -> str:
    return CODE_CATEGORY_TITLES.get(value, value)


def format_mapping(mapping: dict[str, Any] | None, empty: str = "未建立") -> str:
    """Render a machine mapping as readable `key=value` pairs instead of raw JSON."""
    if not mapping:
        return f"`{empty}`"
    return "；".join(
        f"`{key}`={value if isinstance(value, str) else ', '.join(map(str, value)) if isinstance(value, list) else value}"
        for key, value in sorted(mapping.items())
    )


def format_mapping_cell(mapping: dict[str, Any] | None, empty: str = "未建立") -> str:
    """Same pairs as `format_mapping`, without backticks, for use inside table cells."""
    if not mapping:
        return empty
    return "; ".join(f"{key}={value}" for key, value in sorted(mapping.items()))


def format_path_list(paths: dict[str, str] | None) -> list[str]:
    if not paths:
        return ["- 报告路径：`未建立`"]
    labels = {"markdown": "Markdown 报告", "json": "结构化 JSON", "upstream_evidence": "上游证据包"}
    return ["- 报告路径："] + [
        f"  - {labels.get(key, key)}：`{value}`" for key, value in sorted(paths.items())
    ]


def report_section(anchor: str) -> list[str]:
    return [f"<!-- section: {anchor} -->", f"## {REPORT_SECTION_TITLES[anchor]}"]


def confirmation_queue_phase(bundle: AnalysisBundle) -> str:
    """Return evidence | choice | mixed | none for confirmation gating."""
    if bundle.decision_status != "needs_choice":
        return "none"
    ready = False
    blocked = False
    for report in bundle.reports:
        question = report.confirmation
        if question is None:
            continue
        if question.status == "blocked":
            blocked = True
        elif question.status == "ready":
            ready = True
    if blocked and ready:
        return "mixed"
    if blocked:
        return "evidence"
    if ready:
        return "choice"
    return "choice"


def compute_batch_implementation_gate(
    reports: list[PackageReport],
    *,
    decision_status: str,
    importer_resolution: str,
    baseline_blockers: list[str],
    node_runtime: NodeRuntimeAssessment,
    workspace_failed: bool,
    remediation_blocked: bool,
) -> tuple[str, list[str]]:
    """Stage A must be clear and non-deferred packages must be technically ready."""
    reasons: list[str] = []
    if workspace_failed or importer_resolution == "failed":
        reasons.append("前端 workspace 未确认")
    if baseline_blockers:
        reasons.append("基线未对齐：" + "、".join(baseline_blockers))
    if decision_status == "needs_choice":
        reasons.append("人工确认未完成（开放目标选型或精确升级推进确认）")
    if node_runtime.status == "constraint-conflict":
        reasons.append("Node 约束冲突")
    if node_runtime.execution_readiness == "blocked":
        reasons.append("Node 执行就绪度为 blocked")
    for report in reports:
        package = report.upgrade.package
        if report.recommended_action == DEFERRED_ACTION:
            continue
        if report.exact_upgrade_status == "blocked":
            reasons.append(f"{package}：精确升级仍 blocked")
        if report.confirmation is not None and report.confirmation.status in {"ready", "blocked"}:
            reasons.append(f"{package}：确认队列仍为 {report.confirmation.status}")
        if (
            report.recommended_action == PROCEED_SELECTED_ACTION
            and report.exact_upgrade_status != "ready"
        ):
            reasons.append(f"{package}：已确认推进但精确升级未 ready")
    if remediation_blocked and not any("精确升级仍 blocked" in item for item in reasons):
        reasons.append("存在 remediation-blocked / exact_upgrade blocked")
    # Deduplicate while preserving order
    unique: list[str] = []
    for item in reasons:
        if item not in unique:
            unique.append(item)
    return ("frozen" if unique else "ready"), unique


def confirmation_status_banners(bundle: AnalysisBundle, location: str = "header") -> list[str]:
    phase = confirmation_queue_phase(bundle)
    lines: list[str] = []
    next_action = (
        "**下一动作=照确认队列向用户提问或补证据，不是等待放行**。"
        "禁止只贴本报告后收工或等用户说「继续」。"
    )
    if phase == "evidence":
        title = "待补证据（确认队列 blocked）" if location == "header" else "待补证据（结论闸门）"
        lines.append(
            f"> **{title}**：`decision_status=needs_choice`，但尚不能问选型/推进。"
            "请先完成删除面核验 / 替代方案调研 / 调用点证据 / 精确升级阻塞项，回填后重跑。"
            f"{next_action}"
            "生成器 exit `7`（若无更高优先级 exit）。`batch_implementation_gate=frozen`。"
        )
    elif phase == "mixed":
        title = "待补证据 + 待确认" if location == "header" else "待补证据 + 待确认（结论闸门）"
        lines.append(
            f"> **{title}**：部分包确认队列 `blocked`（先补证据），部分 `ready`。"
            "对所有当前 `ready` 包同一波原文提问（开放目标 + 精确升级）；`blocked` 不问。"
            f"{next_action}"
            "exit `7`。闸门 `frozen`。"
        )
    elif phase == "choice":
        title = "待人工确认" if location == "header" else "待人工确认（结论闸门）"
        lines.append(
            f"> **{title}**：`decision_status=needs_choice`。"
            "同一波问完所有当前 `ready` 包：开放目标照选项表原文提问（替换含精确 `包@版本` 与 `other`）；"
            "精确升级确认 `proceed:包@版本` / `defer` / `other`。"
            "`switch:<track>` / `handle-parent` 后续题下一波。"
            f"{next_action}"
            "写入决策文件、重跑并由 Agent 复核至 `analysis_status=complete` 后，本技能才完成。"
            "exit `7`。本技能不实施变更。"
        )
    if bundle.batch_implementation_gate == "frozen":
        reason_text = "；".join(bundle.batch_gate_reasons) or "见确认队列与阻塞项"
        title = "批次实施闸门 frozen" if location == "header" else "批次实施闸门 frozen（结论）"
        lines.append(
            f"> **{title}**：`batch_implementation_gate=frozen`。"
            f"原因：{reason_text}。"
            "整批不得开实施计划或执行变更；待全部策略确认且非延期包技术就绪后才为 `ready`。"
        )
    elif phase == "none" and location == "header":
        lines.append(
            "> **批次实施闸门 ready**：Stage A 已清空确认队列且无整批冻结原因。"
            "仍须调用方进入 Stage B（计划）并另给 Stage C（实施）授权；本技能不实施。"
        )
    if not lines:
        return []
    out: list[str] = []
    for body in lines:
        out.extend([body, ""])
    return out


def markdown_report(bundle: AnalysisBundle) -> str:
    exact_count = sum(1 for report in bundle.reports if report.analysis_mode == "exact-upgrade" and report.upgrade.to_version)
    pending_count = sum(1 for report in bundle.reports if report.selection_status == "needs_explicit_choice")
    if bundle.node_runtime.execution_readiness == "blocked" or bundle.node_runtime.status == "runtime-switch-required":
        pending_count += 1
    blocked_count = sum(1 for report in bundle.reports if report.baseline_status in {"mismatch", "unknown"})
    if bundle.node_runtime.execution_readiness == "blocked":
        blocked_count += 1
    lines = [
        f"# {bundle.title}", "",
        f"- 生成时间：`{bundle.generated}`",
        f"- 项目根目录：`{bundle.project_root}`",
        f"- 前端 workspace 解析：`{bundle.importer_resolution}`",
        f"- 报告状态：`{bundle.status}`",
        f"- 分析状态：`{bundle.analysis_status}`",
        f"- 决策状态：`{bundle.decision_status}`",
        f"- 行为守恒要求：`{bundle.behavior_parity_required}`",
        f"- Node 运行时状态：`{bundle.node_runtime.status}`",
        f"- 执行就绪度：`{bundle.node_runtime.execution_readiness}`",
        f"- 本机当前 Node：`{bundle.node_runtime.current_host_node or '未检测到'}`；路径：`{bundle.node_runtime.current_host_node_path or '未检测到'}`",
        f"- 项目 Node：`{bundle.node_runtime.selected_project_node or '未建立'}`；管理器：`{bundle.node_runtime.selected_manager or '未建立'}`",
        f"- 批次实施闸门：`{bundle.batch_implementation_gate}`",
        f"- 闸门原因：{('；'.join(bundle.batch_gate_reasons) if bundle.batch_gate_reasons else '无')}",
        f"- 关联 change/任务目录：`{bundle.change_dir or '未绑定'}`",
        f"- 报告目录：`{bundle.report_output_dir}`",
        *format_path_list(bundle.report_paths),
        f"- 批次：精确升级 `{exact_count}` / 待人工决策 `{pending_count}` / blocked 项 `{blocked_count}`",
        "",
    ]
    lines.extend(confirmation_status_banners(bundle))
    lines.extend([
        *report_section("Upgrade Summary"), "",
        "| 包 | 分析模式 | 治理/升级原因 | 原版本 | 目标版本 | 建议动作 | 选择状态 | 决策状态 | 约束 | 变化类型 | 依赖类型 | Manifest 声明 | Lock 直接解析 | 基线状态 | 风险分 | 风险等级 | 证据完整性 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|",
    ])
    for report in bundle.reports:
        direct = report.current_lock_version or report.before_lock_version or report.after_lock_version or "-"
        lines.append("| " + " | ".join(md_cell(value) for value in (
            report.upgrade.package, report.analysis_mode, report.upgrade.reason, report.upgrade.from_version, report.upgrade.to_version,
            report.recommended_action, report.selection_status, report.decision_status, "; ".join(report.constraints), report.change_type,
            report.upgrade.dependency_type, report.manifest_spec, direct, report.baseline_status,
            report.risk.total, report.risk.final_level, report.evidence_completeness,
        )) + " |")

    lines.extend(["", *report_section("Release Notes And Changelog Evidence"), ""])
    upstream_evidence_path = bundle.report_paths.get("upstream_evidence", "")
    if upstream_evidence_path:
        lines.append(f"- 本地上游证据包：`{upstream_evidence_path}`")
    elif any(report.used_local_upstream_evidence for report in bundle.reports):
        lines.append("- 本地上游证据包：已回读（路径见各包警告）")
    for report in bundle.reports:
        lines.extend([f"### {report.upgrade.package} `{report.upgrade.from_version} -> {report.upgrade.to_version}`", "", f"- 完整性：`{report.evidence_completeness}`", f"- 包页面：{report.package_url}"])
        if report.repository_url:
            lines.append(f"- 代码仓库：{report.repository_url}")
        if report.homepage:
            lines.append(f"- 官方主页：{report.homepage}")
        lines.append(
            f"- 仓库校验：`{report.repository_validation_status}`；"
            f"版本来源：`{report.repository_source_version or '未建立'}`"
        )
        lines.append(f"- 证据维度：{format_mapping(report.evidence_dimensions)}")
        lines.append(f"- 本地证据回读：`{'yes' if report.used_local_upstream_evidence else 'no'}`")
        if report.repository_lineage:
            lines.append(f"- 版本仓库谱系：{format_mapping(report.repository_lineage)}")
        for warning in report.warnings:
            lines.append(f"- 警告：{warning}")
        if report.official_sources:
            lines.extend([
                "", "#### 官方来源清单", "",
                "| 类型 | 状态 | 版本 | 标题/原因 | URL |",
                "|---|---|---|---|---|",
            ])
            for source in report.official_sources:
                lines.append("| " + " | ".join(md_cell(value) for value in (
                    source.kind, source.status, source.version,
                    source.title or source.reason, source.url,
                )) + " |")
        lines.extend(["", "| 版本 | 发布日期 | 变化类型 | 仓库 | 仓库来源 | 仓库校验 | Release 状态 | Changelog 状态 | 发布说明摘要 | 变更日志摘要 | 证据状态 | 来源 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"])
        for note in report.notes:
            lines.append("| " + " | ".join(md_cell(value) for value in (
                note.version, note.published, note.change_type, note.repository_url, note.repository_source, note.repository_validation,
                note.release_status, note.changelog_status, note.release_notes, note.changelog,
                note.evidence_status, "; ".join(note.sources),
            )) + " |")
        lines.append("")

    lines.extend([*report_section("Breaking Changes And Migration Notes"), "", "| 包 | 版本区间 | 变化 | 影响类型 | 必需验证 |", "|---|---|---|---|---|"])
    for report in bundle.reports:
        candidates = breaking_candidates(report) or ["需要 Agent 复核官方迁移和破坏性变更文档"]
        for candidate in candidates:
            lines.append("| " + " | ".join(md_cell(value) for value in (
                report.upgrade.package, f"{report.upgrade.from_version} -> {report.upgrade.to_version}", candidate,
                report.upgrade.dependency_type, validation_for_type(report.upgrade.dependency_type),
            )) + " |")

    lines.extend(["", *report_section("Dependency Changes"), ""])
    for report in bundle.reports:
        # Same predicate as `reconcile_open_target_report`, so what is computed and what
        # is rendered cannot drift apart.
        open_target = not report.upgrade.to_version and report.analysis_mode != "exact-upgrade"
        lines.extend([
            f"### {report.upgrade.package}", "",
            f"- Manifest：`{report.manifest_field or '未建立'}` = `{report.manifest_spec or '未建立'}`",
            f"- Lock：`{report.lock_kind}` `{report.lock_path or '未建立'}`",
            f"- 升级前/当前/升级后直接版本：`{report.before_lock_version or '-'}` / `{report.current_lock_version or '-'}` / `{report.after_lock_version or '-'}`",
            f"- 升级前观察版本：`{', '.join(report.before_lock_versions) or '未提供'}`",
            f"- 当前观察版本：`{', '.join(report.current_lock_versions) or '未检测到'}`",
            f"- 升级后观察版本：`{', '.join(report.after_lock_versions) or '未提供'}`",
            f"- 汇总观察版本：`{', '.join(report.observed_lock_versions) or '未建立'}`",
            f"- 基线状态：`{report.baseline_status}`",
            f"- 目标 peerDependencies：{format_mapping(report.target_peer_dependencies)}",
            f"- Peer 兼容性：`{report.peer_compatibility_status}`；冲突：`{'; '.join(report.peer_compatibility_conflicts) or '无'}`",
            f"- 目标 engines：{format_mapping(report.target_engines)}",
            "",
        ])
        if not open_target:
            lines.extend([
                "#### 精确目标升级结论", "",
                f"- 升级状态：`{report.exact_upgrade_status}`",
                f"- 实施策略：`{report.exact_upgrade_strategy or '未建立'}`",
                f"- 全量 lock 收敛：`{report.target_convergence_status}`；"
                f"残留版本：`{', '.join(report.residual_lock_versions) or '无'}`",
                f"- 阻塞项：{'; '.join(report.implementation_blockers) or '无'}",
                "- 实施命令（仅输出，不执行；所有阻塞项清零后方可运行）：",
                *(
                    [f"  - `{command}`" for command in report.implementation_commands]
                    if report.implementation_commands else ["  - `未建立`"]
                ),
                f"- 完成判定：升级后 lock 中 `{report.upgrade.package}` 的所有实例必须等于 "
                f"`{report.upgrade.to_version}`；任何旧版本残留都视为整改未完成。",
                "",
            ])
        lines.extend(render_provenance(report))
        if open_target:
            alternates = "、".join(
                f"`{track}`（{PRIMARY_TRACKS[track]}）" for track in report.alternate_tracks
            ) or "无"
            lines.extend([
                "#### 处置决策顺序", "",
                f"- 主轨：`{report.primary_track}`（{PRIMARY_TRACKS.get(report.primary_track, report.primary_track)}）",
                f"- 判定依据：{report.primary_track_basis or '未建立'}",
                f"- 备选轨道：{alternates}",
                "- 判定顺序：`先看依赖来源 → 是否真的被使用 → 是否有可换的包 → 都没有则原生改造`；"
                "同库升级不在选项内，主轨只表示本轮证据指向哪条路径，人可改轨。",
                "- 以下各路径的证据一并呈现，便于一次看全选择面；呈现不等于推荐，最终由人拍板。",
                "",
            ])
        if report.removal.status != "not_assessed":
            lines.extend([
                "#### 删除可行性", "",
                f"- 结论：`{report.removal.status}`；可信度：`{report.removal.confidence}`",
                f"- 支持证据：{'; '.join(report.removal.evidence) or '未建立'}",
                f"- 阻塞证据：{'; '.join(report.removal.blockers) or '未建立'}",
                f"- 未决核查：{'; '.join(report.removal.unknowns) or '无'}",
                f"- 已核查覆盖：{'; '.join(report.removal.coverage_checked) or '未建立'}",
                "",
            ])
        if report.alternative_candidates:
            lines.extend([
                "#### 替代库候选", "",
                f"- 候选来源：`analysis-evidence` 为人工复核结论；`curated-map` 为知识表线索（核对于 {REPLACEMENT_MAP_REVIEWED}），"
                "只是待评估证据，不改变推荐优先级，也不构成选型。",
                f"- 排序仅按机器可核信号，优先级依次为：{'、'.join(f'`{signal}`' for signal in ALTERNATIVE_RANK_SIGNALS)}；"
                "排序是呈现顺序与依据，不是选型结论，人可直接否决。",
                "",
                "- 每个候选最多给三个精确版本：推荐稳定版、满足项目 Node 的兼容回退版、上一个大版本的保守版；"
                "确认队列只问推荐版本，换版本走 `other`。",
                "",
                "| 排序 | 包 | 推荐版本 | 其他可选版本 | 来源 | 排序依据 | 合规状态 | 约束匹配 | 核查标准 | 排除原因 | PeerDependencies | Engines | 兼容性 | 合规/维护 | 迁移成本 | 验证范围 | 回滚难度 | 推荐理由 | 可信度 | 证据 |",
                "|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
            ])
            for candidate in report.alternative_candidates:
                lines.append("| " + " | ".join(md_cell(value) for value in (
                    candidate.rank, candidate.package, candidate.version or "待解析",
                    alternative_version_options(candidate), candidate.origin,
                    "; ".join(candidate.rank_signals), candidate.compliance_status, candidate.constraint_fit,
                    "; ".join(candidate.criteria_checked), "; ".join(candidate.disqualifiers),
                    format_mapping_cell(candidate.peer_dependencies, "-"),
                    format_mapping_cell(candidate.engines, "-"),
                    candidate.compatibility,
                    candidate.compliance_and_maintenance, candidate.migration_cost,
                    candidate.validation_scope, candidate.rollback_difficulty,
                    candidate.rationale, candidate.confidence,
                    "; ".join(candidate.evidence_urls or ([candidate.source] if candidate.source else [])),
                )) + " |")
            lines.append("")
        elif open_target:
            lines.extend([
                "#### 替代库候选", "",
                f"- 尚未建立。替代库知识表（核对于 {REPLACEMENT_MAP_REVIEWED}）没有该包条目，"
                "需要 Agent 按下方调研任务清单研究 2～3 个候选及其精确版本；不得按下载量或流行度自动选型。",
                "",
            ])
        if open_target and report.research_status != "reviewed":
            lines.extend([
                "#### 替代方案调研任务", "",
                f"- 调研状态：`{report.research_status}`。回填人工复核结论前，该包不得视为已完成分析。",
                "",
            ])
            lines.extend(f"- {item}" for item in build_research_task(report))
            lines.append("")
        if open_target:
            plan = report.refactor_plan
            lines.extend([
                "#### 原生重构方向", "",
                f"- 方案状态：`{plan.status}`（无合规替代包时的兜底路径；方向来自本轮实际调用点证据）",
                f"- 可直接改用的原生能力：{'；'.join(plan.native_routes) or '未登记'}",
                f"- 需自建的能力：{'；'.join(plan.capabilities_to_rebuild) or '未建立'}",
                f"- 按调用点分组的改造范围：{'；'.join(plan.call_site_groups) or '未建立'}",
                f"- 分阶段路径：{'；'.join(f'{index}) {stage}' for index, stage in enumerate(plan.stages, start=1)) or '证据不足，未生成'}",
                f"- 改造规模：`{plan.scale or '未建立'}`（{plan.scale_basis or '尚无调用点计数'}；仅为规模分级，不含工时估算）",
                f"- 验证范围：{plan.validation_scope or '需先建立调用点证据'}",
                f"- 回滚：{plan.rollback or '未建立'}",
                f"- 未决项：{'；'.join(plan.unknowns) or '无'}",
                "",
                "- 影响面：",
                *[f"  - {item}" for item in plan.impact_surface or ["需先建立调用点证据"]],
                "",
                "- 行为等价核对清单（“保持原有逻辑”的具体含义，逐项核对后才算改造完成）：",
                *[f"  - {item}" for item in plan.parity_checks or ["需先建立调用点证据"]],
                "",
                "| 文件 | 行号 | 类别 | 当前用法 | 等价实现思路 | 行为差异风险 | 验证点 | 可信度 |",
                "|---|---:|---|---|---|---|---|---|",
            ])
            if plan.actions:
                for action in plan.actions:
                    lines.append("| " + " | ".join(md_cell(value) for value in (
                        action.file, action.line, visible_code_category(action.category),
                        action.current_usage, action.approach, action.parity_risk,
                        action.validation, action.confidence,
                    )) + " |")
            else:
                lines.append("| 未建立 | 0 | 未建立 | 未建立 | 需先建立调用点证据 | 未建立 | 未建立 | low |")
            lines.extend(["", "> 上表为改造候选。等价实现必须结合官方文档与实际语义确认，生成器不代替该确认。", ""])
        if report.disposition_options:
            lines.extend([
                "#### 处置方案选项", "",
                "- 以下为该包的完整可选路径，供人拍板；`evidence-available` 仅表示本轮已产出该路径的证据，不代表推荐。",
                "",
                "| 处置方案 | 说明 | 证据状态 | 适用条件 | 本轮证据 | 决策所需依据 |",
                "|---|---|---|---|---|---|",
            ])
            for option in report.disposition_options:
                lines.append("| " + " | ".join(md_cell(value) for value in (
                    option.option, option.title, option.availability,
                    option.applicability, option.detail or "未建立", option.required_evidence,
                )) + " |")
            lines.append("")
    runtime = bundle.node_runtime
    lines.extend([
        "### Node 运行时兼容性", "",
        f"- 状态：`{runtime.status}`；执行就绪度：`{runtime.execution_readiness}`",
        f"- 本机当前 Node：`{runtime.current_host_node or '未检测到'}`；路径：`{runtime.current_host_node_path or '未检测到'}`",
        f"- 所选项目 Node：`{runtime.selected_project_node or '未建立'}`；管理器：`{runtime.selected_manager or '未建立'}`",
        f"- 所选 Node 支持状态：`{runtime.selected_node_support}`（发布计划表核对于 {NODE_SCHEDULE_REVIEWED}）",
        f"- 可用管理器：`{', '.join(runtime.available_managers) or '未检测到'}`",
        f"- 已安装版本：{format_mapping(runtime.installed_versions, '未检测到')}",
        f"- 兼容的已安装版本：`{', '.join(runtime.compatible_installed_versions) or '未检测到'}`",
        f"- 推荐策略：`{runtime.recommended_strategy}`",
        "",
        "| 来源 | Node 要求 | 类别 | 权威性 | 路径/URL |",
        "|---|---|---|---|---|",
    ])
    constraints = runtime.project_constraints + runtime.observed_runtime_evidence
    if constraints:
        for constraint in constraints:
            lines.append("| " + " | ".join(md_cell(value) for value in (
                constraint.source, constraint.requirement, constraint.kind,
                constraint.authority, constraint.path,
            )) + " |")
    else:
        lines.append("| 未建立 | 未建立 | 未建立 | 未建立 | 未建立 |")
    lines.extend([
        "",
        f"- 阻塞项：{'; '.join(runtime.blockers) or '无'}",
        f"- 警告：{'; '.join(runtime.warnings) or '无'}",
        f"- 一次性安装建议：{'; '.join(runtime.installation_guidance) or '无'}",
        f"- 恢复计划：{'; '.join(runtime.restoration_plan) or '未建立'}",
        "",
        "### Overrides / Resolutions / Peer 元数据",
    ])
    lines.extend([f"- `{entry}`" for entry in bundle.manifest.special_entries] or ["- 未建立"])
    lock_warnings = sorted(set(bundle.before_lock.warnings + bundle.current_lock.warnings + bundle.after_lock.warnings))
    if lock_warnings:
        lines.append("")
        lines.append("### Lockfile 解析警告")
        lines.extend(f"- {warning}" for warning in lock_warnings)

    lines.extend(["", *report_section("Diff Evidence Used"), ""])
    lines.extend([f"- {item}" for item in bundle.diff_evidence] or ["- 未建立"])
    lines.append("- 上游源码差异：默认跳过，仅在存在明确且有边界的证据缺口时使用。")

    lines.extend(["", *report_section("Code References"), ""])
    for report in bundle.reports:
        direct_files = sorted({point.file for point in bundle.code_points if point.package == report.upgrade.package and point.category in {"Direct package usage", DECLARATION_CATEGORY}})
        shared_files = sorted(path for path in direct_files if SHARED_RE.search(path))
        lines.extend([
            f"### {report.upgrade.package}", "",
            f"- 直接引用/配置文件：{', '.join(f'`{path}`' for path in direct_files) or '未建立'}",
            f"- 公共包装器候选：{', '.join(f'`{path}`' for path in shared_files) or '未建立'}",
            "- 间接调用方/页面：需要通过知识图谱或定向调用追踪补充；生成器不依据文件名推断事实。", "",
        ])
    for warning in bundle.scan_warnings:
        lines.append(f"- 扫描警告：{warning}")

    lines.extend(["", *report_section("Detailed Code Modification Points"), "", "| 包 | 文件 | 行号 | 类别 | 当前用法 | 上游依据 | 建议修改 | 必需验证 | 优先级 | 可信度 |", "|---|---|---:|---|---|---|---|---|---|---|"])
    if bundle.code_points:
        for point in sorted(bundle.code_points, key=lambda value: ({"P0": 0, "P1": 1, "P2": 2}.get(value.priority, 3), value.file, value.line)):
            lines.append("| " + " | ".join(md_cell(value) for value in (
                point.package, point.file, point.line, visible_code_category(point.category), point.current_usage,
                point.upstream_reason, point.recommended_change, point.validation, point.priority, point.confidence,
            )) + " |")
    else:
        lines.append("| - | - | - | 未建立 | 静态扫描未发现直接引用 | 需要复核调用图、别名和运行时注册 | 追踪用法并执行定向验证 | 待建立 | P1 | low |")
    lines.extend(["", "> 以上内容均为修改候选。编辑代码前必须结合准确的上游证据确认其适用性。", ""])

    lines.extend([*report_section("Business Impact"), "", "| 包 | 模块 | 页面/流程 | 风险 | 依据 |", "|---|---|---|---|---|"])
    emitted: set[tuple[str, str]] = set()
    for point in bundle.code_points:
        # A manifest declaration is not a business surface; only real usage maps to flows.
        if point.category == DECLARATION_CATEGORY:
            continue
        module, flows = business_module(point.file)
        key = (point.package, module)
        if key in emitted:
            continue
        emitted.add(key)
        report = next(report for report in bundle.reports if report.upgrade.package == point.package)
        # An unmapped flow is not an assessed impact, so it must not inherit the package risk level.
        mapped = flows != UNMAPPED_FLOW
        severity = report.risk.final_level if mapped else UNRATED
        basis = (
            f"根据 {point.file} 映射；仍需调用方追踪" if mapped
            else f"仅建立 {point.file} 引用证据；页面/流程映射完成后才可定级"
        )
        lines.append("| " + " | ".join(md_cell(value) for value in (point.package, module, flows, severity, basis)) + " |")
    if not emitted:
        lines.append(f"| - | 未建立 | {UNMAPPED_FLOW} | {UNRATED} | 尚未建立直接代码引用证据 |")

    lines.extend(["", *report_section("Technical Risks"), "", "| 包 | 风险 | 严重度 | 证据 | 缓解措施 |", "|---|---|---|---|---|"])
    for report in bundle.reports:
        factor_text = ", ".join(f"{name}={score}" for name, score in report.risk.factors.items())
        override_text = "; ".join(report.risk.rationale) or f"未覆盖自动等级（{report.risk.automatic_level}）"
        uncertainty_text = "; ".join(report.risk.uncertainties) or "无"
        lines.append("| " + " | ".join(md_cell(value) for value in (
            report.upgrade.package, "七因素升级风险", report.risk.final_level,
            f"总分 {report.risk.total}：{factor_text}；{override_text}；不确定项：{uncertainty_text}",
            validation_for_type(report.upgrade.dependency_type),
        )) + " |")
        if report.evidence_completeness != "complete":
            lines.append("| " + " | ".join(md_cell(value) for value in (report.upgrade.package, "上游证据缺口", "High" if report.change_type == "major" else "Medium", report.evidence_completeness, "批准前完成官方迁移、发布和 peer 证据复核")) + " |")
    runtime_severity = "High" if runtime.status in {"constraint-conflict", "unknown", "manager-missing", "runtime-missing"} or runtime.blockers or runtime.warnings else "Medium"
    lines.append("| " + " | ".join(md_cell(value) for value in (
        "__node_runtime__",
        "Node 运行时兼容与恢复",
        runtime_severity,
        (
            f"status={runtime.status}；host={runtime.current_host_node or 'unknown'}；"
            f"project={runtime.selected_project_node or 'unknown'}；"
            f"blockers={'; '.join(runtime.blockers) or '无'}；warnings={'; '.join(runtime.warnings) or '无'}"
        ),
        "本机/项目运行时隔离；实施前审批；优先隔离 PATH；finally 恢复并验证原本机 Node 及无临时约束残留",
    )) + " |")

    lines.extend(["", *report_section("Test Scope"), "", "### 必测"])
    for report in bundle.reports:
        lines.append(f"- `{report.upgrade.package}`: {validation_for_type(report.upgrade.dependency_type)}")
    lines.extend([
        "- 验证目标直接 lock 解析版本以及 peer/engine 兼容性。",
        f"- 所有项目命令必须在 Node `{runtime.selected_project_node or '待确认'}` 下执行并记录实际 `node --version`。",
        "- 实施前快照当前 Node/路径/PATH/包管理器及 Node 约束；实施后验证恢复一致。",
        "- 覆盖关键流程的成功、失败、中断和恢复状态。",
        "", "### 建议验证", "- 获得实施批准后，按项目实际情况运行原生 typecheck、lint、unit、build、E2E、视觉和兼容性检查。",
        "- 对比升级前后的警告、包体积、运行时错误、API 错误率和视觉基线。",
        "", "### 冒烟检查", "- 应用启动 → 鉴权/入口 → 代表性列表/详情 → 新建/编辑 → 适用时覆盖上传/下载。",
    ])

    level = overall_level(bundle.reports)
    if runtime_severity == "High":
        level = "High"
    lines.extend([
        "", *report_section("Rollout And Rollback"), "",
        f"- 发布：{'采用分阶段发布或明确的等价控制。' if level == 'High' else '发布后重点观察受影响模块。'}",
        "- 监控：运行时异常、白屏、路由失败、API 错误率/延迟、上传失败、控制台警告、视觉回归以及包体积/性能变化。",
        "- 回滚：恢复已复核的 manifest+lock 组合及上一份可部署产物；不得只修改单个依赖文件。",
        "- 运行时恢复：临时项目 Node 只用于受控子进程；若使用全局切换，无论成功或失败都恢复并验证原本机 Node。",
        "- 触发条件：核心流程失败、鉴权/权限回归、API 错误持续上升、上传失败，或视觉/构建问题超出可控范围时回滚。",
    ])
    lines.extend(render_confirmation_queue(bundle))
    lines.extend([
        "", *report_section("Conclusion"), "",
        *confirmation_status_banners(bundle, location="conclusion"),
        f"- 总体风险：`{level}`",
        f"- 报告状态：`{bundle.status}`",
        f"- 分析状态：`{bundle.analysis_status}`",
        f"- 决策状态：`{bundle.decision_status}`",
        f"- 批次实施闸门：`{bundle.batch_implementation_gate}`",
        f"- 闸门原因：{('；'.join(bundle.batch_gate_reasons) if bundle.batch_gate_reasons else '无')}",
        f"- 行为守恒要求：`{bundle.behavior_parity_required}`",
        f"- Node 运行时状态：`{runtime.status}`；执行就绪度：`{runtime.execution_readiness}`",
        f"- Node 阻塞项：{'; '.join(runtime.blockers) or '无'}",
        f"- 报告目录：`{bundle.report_output_dir}`",
        "- 最低可接受验证：确认准确 lock/peer/engine，执行受影响自动化检查，覆盖关键成功/失败/恢复流程，具备监控和已验证的回滚路径。",
        "- 剩余工作：标记为 `complete` 前，解决所有“未建立”“需要 Agent 复核”、基线不一致、证据警告、未翻译上游摘要和间接调用方映射缺口；"
        "若 `decision_status=needs_choice`，还必须完成人工确认队列"
        "（exit `7`：下一动作=照队列提问或补证据，不是等待放行；所有当前 ready 同波问完）。"
        "决策落盘并重跑后，Agent 须复核并将 `analysis_status` 升为 `complete` 才算本技能结束。"
        "`batch_implementation_gate=frozen` 时不得开实施计划或执行变更（可不阻止分析定稿）。",
    ])
    option_gaps = [report.upgrade.package for report in bundle.reports if report.option_status == "missing"]
    research_gaps = [report.upgrade.package for report in bundle.reports if report.research_status == "pending"]
    lines.append(
        "- 选项完整性闸门：未指定目标版本的包必须至少产出一个可执行选项（删除／替代包／原生改造／父包处置）。"
        + (f"未满足：`{'`, `'.join(option_gaps)}`；报告不得标记为 `complete`。" if option_gaps else "本轮全部满足。")
    )
    if research_gaps:
        lines.append(
            f"- 替代方案调研缺口：`{'`, `'.join(research_gaps)}` 尚无任何候选线索，"
            "需按「替代方案调研任务」联网调研后回填 `--analysis-evidence-file`。"
        )
    remediation_blockers = [
        f"`{report.upgrade.package}`：{blocker}"
        for report in bundle.reports
        for blocker in report.implementation_blockers
    ]
    if remediation_blockers:
        lines.extend(["", "### 整改阻塞", *[f"- {item}" for item in remediation_blockers]])
    decisions = [
        f"`{report.upgrade.package}`：{decision}"
        for report in bundle.reports
        for decision in report.decision_required
    ]
    if decisions:
        lines.extend(["", "### 需要人工决策", *[f"- {decision}" for decision in decisions]])
    if runtime.status == "runtime-switch-required":
        lines.extend(["", "### Node 实施审批", "- 项目命令需要隔离 Node；执行前必须明确批准 `runtime-switch`，安装缺失 Node 时另行批准 `node-install`。"])
    elif runtime.blockers:
        lines.extend(["", "### Node 实施阻塞", *[f"- {blocker}" for blocker in runtime.blockers]])
    return "\n".join(lines) + "\n"


def render_provenance(report: PackageReport) -> list[str]:
    """Where the package comes from, and the parent chains that pull it in."""
    provenance = report.provenance
    lines = [
        "#### 依赖来源与父包链", "",
        f"- 来源：`{provenance.kind}`（{PROVENANCE_KINDS.get(provenance.kind, provenance.kind)}）",
        f"- manifest 声明字段：`{provenance.declared_field or '未声明'}`；代码直接用法：`{'有' if provenance.used_in_code else '未发现'}`",
        f"- 判定证据：{'；'.join(provenance.evidence) or '未建立'}",
    ]
    if provenance.chains:
        shown = "；".join(f"`{chain}`" for chain in provenance.chains)
        suffix = f"（共 {provenance.chain_total} 条，仅展示最短的 {len(provenance.chains)} 条）" if provenance.chain_total > len(provenance.chains) else ""
        lines.append(f"- 父包链：{shown}{suffix}")
    if provenance.override_version:
        breaks = "；".join(provenance.override_breaks)
        lines.append(
            f"- overrides/resolutions 最低可行版本：`{provenance.override_version}`"
            + (f"；会破坏的父包约束：{breaks}" if breaks else "；满足全部现有父包 range 与项目 Node")
        )
    lines.append(f"- 未决项：{'；'.join(provenance.unknowns) or '无'}")
    lines.append("")
    if provenance.parents:
        lines.extend([
            "| 父包 | 已解析版本 | 对该包的 range | 父包最新稳定版 | 是否已摆脱该依赖 | 说明 |",
            "|---|---|---|---|---|---|",
        ])
        for edge in provenance.parents[:PARENT_CHAIN_LIMIT]:
            lines.append("| " + " | ".join(md_cell(value) for value in (
                edge.package, edge.version or "未解析", edge.requirement or "-",
                edge.latest_stable or "未解析", edge.fix_available, edge.fix_note or "-",
            )) + " |")
        if len(provenance.parents) > PARENT_CHAIN_LIMIT:
            lines.append(f"| 其余 {len(provenance.parents) - PARENT_CHAIN_LIMIT} 个父包 | - | - | - | unknown | 超出展示上限，见 JSON 输出 |")
        lines.append("")
    return lines


def alternative_version_options(candidate: AlternativeCandidate) -> str:
    """Versions beyond the recommended one, de-duplicated and labelled."""
    extras = [
        (candidate.fallback_version, "兼容项目 Node"),
        (candidate.conservative_version, "上一个大版本，保守"),
    ]
    seen = {candidate.version}
    labelled = []
    for version, note in extras:
        if version and version not in seen:
            seen.add(version)
            labelled.append(f"{version}（{note}）")
    return "; ".join(labelled) or "-"


def _render_option_table(question: ConfirmationQuestion) -> list[str]:
    lines = [
        "| 选项 ID | 选项 | 说明 |",
        "|---|---|---|",
    ]
    for option in question.options:
        lines.append("| " + " | ".join(md_cell(value) for value in (
            option.option_id, option.label, option.detail or "-",
        )) + " |")
    lines.append("")
    return lines


def render_confirmation_queue(bundle: AnalysisBundle) -> list[str]:
    """The per-package questions the Agent must ask, plus decisions already recorded."""
    lines = ["", *report_section("Human Confirmation Queue"), ""]
    questions = [report for report in bundle.reports if report.confirmation is not None]
    phase = confirmation_queue_phase(bundle)
    proceed_ready = [
        report for report in questions
        if report.confirmation is not None
        and report.confirmation.track == PROCEED_EXACT_TRACK
        and report.confirmation.status == "ready"
    ]
    lines.extend([
        f"- 决策记录文件：`{bundle.decision_file}`（生成器只读；由 Agent 在人确认后写入）",
        f"- 本轮确认阶段：`{phase}`（`evidence`=先补证据；`choice`=可确认；`mixed`=二者并存；`none`=无需）",
        f"- 批次实施闸门：`{bundle.batch_implementation_gate}`",
        "- 提问规则：所有当前 `ready` 包（开放目标 + 精确升级）同一波问完；"
        "`switch:<track>` / `handle-parent` 后续题下一波。",
        "- **下一动作**：`needs_choice` / exit `7` 时照本队列向用户提问或补证据，**不是等待放行**；禁止只贴报告收工。",
        "- `blocked` 的包先补前置证据，不得提前问选型/推进。同批任一 blocked/未确认 → 整批 `frozen`。",
        "- 替换轨必须给出精确 `replace:<包>@<版本>`（仅 `analysis-evidence` eligible）；`curated-map` 只是线索。",
        "- 精确升级选项：`proceed:<包>@<版本>` / `defer` / `other`。",
        "- 选项末位固定为 `other`。`switch:<track>` 后改问同包「改轨问题」整表，勿把 switch 写入决策文件。",
        "- `handle-parent` 本身不是最终选择；须继续写 `包<-父包` 追问，或选 pin-override / remove-feature / other。",
        "- 记录选型/推进不等于实施授权；本技能终点是决策落盘重跑后经复核的 `analysis_status=complete` 报告"
        "（`disposition-selected` / `proceed-selected` / `deferred`）。",
        "- Agent 协议：`decision_status=needs_choice` 时必须当场提问；"
        "`batch_implementation_gate=frozen` 时不得开计划/实施（可不阻止分析定稿）；"
        "见 `references/human-confirmation-gates.md`。",
        "",
    ])
    if not questions:
        lines.extend(["- 本轮确认队列为空。", ""])
        return lines
    if proceed_ready:
        lines.extend([
            "### 精确升级批量确认（可一次询问）",
            "",
            "| 包 | 原版本 | 目标版本 | 策略 | 建议选项 ID |",
            "|---|---|---|---|---|",
        ])
        for report in proceed_ready:
            question = report.confirmation
            assert question is not None
            proceed_id = next(
                (option.option_id for option in question.options if option.option_id.startswith("proceed:")),
                f"proceed:{report.upgrade.package}@{report.upgrade.to_version}",
            )
            lines.append("| " + " | ".join(md_cell(value) for value in (
                report.upgrade.package,
                report.upgrade.from_version or report.current_lock_version or "-",
                report.upgrade.to_version,
                report.exact_upgrade_strategy or "-",
                proceed_id,
            )) + " |")
        lines.extend([
            "",
            "- 对上表一次确认即可；每包将对应 `proceed:包@版本` 或统一 `defer` 写入决策文件。",
            "",
        ])
    lines.extend([
        "| 包 | 主轨 | 队列状态 | 问题 | 前置条件 |",
        "|---|---|---|---|---|",
    ])
    for report in questions:
        question = report.confirmation
        assert question is not None
        summary = (
            f"{len(question.prerequisites)} 项，见下方分节" if len(question.prerequisites) > 3
            else "; ".join(question.prerequisites) or "-"
        )
        lines.append("| " + " | ".join(md_cell(value) for value in (
            question.package, question.track, question.status,
            question.prompt or question.blocked_reason or "-",
            summary,
        )) + " |")
    lines.append("")
    for report in questions:
        question = report.confirmation
        assert question is not None
        lines.append(f"### {question.package}")
        lines.append("")
        if question.status == "blocked":
            lines.extend([
                f"- 状态：`blocked`（待补证据，勿问选型）。{question.blocked_reason}",
                "- 需先完成：",
                *[f"  - {item}" for item in question.prerequisites],
                *([] if question.prerequisites else ["  - 见删除评估与调研任务"]),
                "",
            ])
            continue
        if question.status == "decided" and report.decision is not None:
            lines.extend([
                f"- 状态：`decided`。已记录选择 `{report.decision.choice}`，本轮不再提问。",
                "",
            ])
            continue
        lines.extend([
            f"- 主轨问题（先问这个）：{question.prompt}",
            "",
            *_render_option_table(question),
        ])
        for alt in report.alternate_questions:
            lines.extend([
                f"- 改轨问题：`{alt.track}`（仅当人回答 `switch:{alt.track}` 后原文改问；勿写入 decision-file）",
                f"- 问题：{alt.prompt}",
                "",
                *_render_option_table(alt),
            ])
        for followup in report.parent_questions:
            lines.extend([
                f"- 父包追问（仅在对话中选择 `handle-parent` 后逐个提问；decision `package`=`{followup.package}`）："
                f"{followup.prompt}",
                "",
                *_render_option_table(followup),
            ])
    decided = [report for report in bundle.reports if report.decision is not None]
    if decided:
        lines.extend([
            "### 人工决策记录", "",
            "| 包 | 轨道 | 选择 | 选定包 | 选定版本 | 状态 | 来源 | 时间 | 理由/失效原因 |",
            "|---|---|---|---|---|---|---|---|---|",
        ])
        for report in decided:
            decision = report.decision
            assert decision is not None
            lines.append("| " + " | ".join(md_cell(value) for value in (
                decision.package, decision.track or report.primary_track, decision.choice or "-",
                decision.selected_package or "-", decision.selected_version or "-",
                decision.status, decision.source, decision.decided_at or "-",
                decision.invalidation_reason or decision.rationale or "-",
            )) + " |")
        lines.append("")
    if bundle.decision_warnings:
        lines.extend(["### 决策记录警告", "", *[f"- {item}" for item in bundle.decision_warnings], ""])
    return lines


def split_markdown_row(line: str) -> list[str]:
    body = line.strip().strip("|")
    return [cell.replace("\\|", "|").strip() for cell in re.split(r"(?<!\\)\|", body)]


def is_markdown_separator(line: str) -> bool:
    cells = split_markdown_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def markdown_table_errors(markdown: str) -> list[str]:
    errors: list[str] = []
    lines = markdown.splitlines()
    index = 0
    table_number = 0
    while index + 1 < len(lines):
        if lines[index].startswith("|") and is_markdown_separator(lines[index + 1]):
            table_number += 1
            expected = len(split_markdown_row(lines[index]))
            index += 2
            row_number = 0
            while index < len(lines) and lines[index].startswith("|"):
                row_number += 1
                actual = len(split_markdown_row(lines[index]))
                if actual != expected:
                    errors.append(f"Markdown 表格 {table_number} 第 {row_number} 行列数 {actual}，表头为 {expected}。")
                index += 1
            continue
        index += 1
    return errors


def validate_report_contract(markdown: str) -> list[str]:
    errors: list[str] = []
    for heading in REQUIRED_HEADINGS:
        anchor = f"<!-- section: {heading} -->"
        visible_heading = REPORT_SECTION_TITLES[heading]
        if anchor not in markdown or f"## {visible_heading}" not in markdown:
            errors.append(f"Markdown 缺少章节：{visible_heading} ({heading})")
    if "上游依据" not in markdown or "优先级" not in markdown or "可信度" not in markdown:
        errors.append("详细代码修改候选字段不完整。")
    if "选择状态" not in markdown or "约束" not in markdown or "报告路径" not in markdown:
        errors.append("升级摘要缺少选择状态、约束或报告路径。")
    if "精确目标升级结论" in markdown and (
        "实施命令（仅输出，不执行" not in markdown or "全量 lock 收敛" not in markdown
    ):
        errors.append("精确升级缺少只读实施命令或全量 lock 收敛结论。")
    has_candidate_table = "| 精确版本 | 候选类型 |" in markdown or "| 包 | 精确版本 | 合规状态 |" in markdown
    if has_candidate_table and (
        "合规状态" not in markdown or "核查标准" not in markdown or "排除原因" not in markdown
    ):
        errors.append("候选矩阵缺少结构化合规字段。")
    errors.extend(markdown_table_errors(markdown))
    return errors


def apply_behavior_parity(report: PackageReport) -> None:
    """Keep observable behaviour fixed while the human picks a route.

    For open targets parity is no longer a preference for one route: all remaining routes
    change the dependency graph. It becomes a constraint every route must satisfy, and
    the recommendation stays the next step rather than a disguised selection.
    """
    if report.analysis_mode == "exact-upgrade" and report.upgrade.to_version:
        report.constraints.append("行为守恒：仅允许为实现该精确目标所必需的适配；禁止顺手重构业务/UI。")
        report.decision_status = "needs_choice"
        report.selection_status = "needs_explicit_choice"
        append_unique(
            report.decision_required,
            "行为守恒：精确目标已定，仍须人确认推进或延期；报告不自动批准实施。",
        )
        return
    report.constraints.append(
        "行为守恒：删除／替换／原生改造／父包处置都必须保持对外可观察行为不变；"
        "同库升级不作为本轮选项，确需升级请改用精确目标版本重跑。"
    )
    append_unique(
        report.decision_required,
        "行为守恒：本轮所有路径都会改变依赖构成；由人显式选择走哪条，报告不代选。",
    )
    report.decision_status = "needs_choice"
    report.selection_status = "needs_explicit_choice"


def resolve_report_output_dir(project_root: Path, output_dir: str | None, change_dir: str | None) -> tuple[Path, str]:
    """
    Return (output_path, resolution_note).
    Default is an existing --change-dir evidence folder; --output-dir overrides when set.
    """
    if output_dir:
        path = Path(output_dir)
        if not path.is_absolute():
            path = project_root / path
        return path.resolve(), f"使用显式 --output-dir：{path}"

    if not change_dir:
        raise ValueError(
            "必须提供既有 --change-dir（写入 <change-dir>/evidence/frontend-dependency-upgrade/），"
            "或显式 --output-dir。"
        )

    selected_change = Path(change_dir)
    if not selected_change.is_absolute():
        selected_change = project_root / selected_change
    selected_change = selected_change.resolve()
    if not selected_change.is_dir():
        raise ValueError(f"--change-dir 不是目录：{selected_change}")
    path = selected_change / "evidence" / "frontend-dependency-upgrade"
    return path, f"使用 --change-dir：{selected_change}"


def resolve_decision_file(args: argparse.Namespace, output_dir: Path) -> Path | None:
    """Explicit `--decision-file`, else the conventional file beside the report."""
    raw = getattr(args, "decision_file", None)
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else (Path(args.project_root).resolve() / path).resolve()
    default = (output_dir / DECISION_FILE_NAME).resolve()
    return default if default.is_file() else None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Frontend workspace root; defaults to current directory.")
    parser.add_argument("--upgrade", action="append", default=[], help="package:from:to or package::to (infer current version); repeatable.")
    parser.add_argument("--assess", action="append", default=[], help="Package with no selected target; triaged into remove / replace / native-refactor / handle-parent. Same-package upgrades are not offered.")
    parser.add_argument("--removal-candidate", action="append", default=[], help="Package to assess for possible removal; repeatable.")
    parser.add_argument("--reason", action="append", default=[], help="Optional package=reason or compliance concern; repeatable.")
    parser.add_argument("--upgrades-file", help="JSON/CSV with package, optional from/to, intent, reason rows.")
    parser.add_argument(
        "--analysis-evidence-file",
        help="Agent-reviewed JSON with compliance candidates, alternatives, removal coverage, and constraints.",
    )
    parser.add_argument(
        "--decision-file",
        help=(
            "JSON of human selections from the confirmation queue; read only, never written by "
            f"the generator. Defaults to <output-dir>/{DECISION_FILE_NAME} when that file exists."
        ),
    )
    parser.add_argument("--before-package-json")
    parser.add_argument("--after-package-json")
    parser.add_argument("--before-lock", help="Authoritative pre-upgrade npm/pnpm/Yarn lockfile.")
    parser.add_argument("--after-lock", help="Authoritative post-upgrade npm/pnpm/Yarn lockfile.")
    parser.add_argument("--workspace-importer", default=".", help="pnpm/npm workspace importer relative to the lock root.")
    parser.add_argument("--allow-baseline-mismatch", action="store_true", help="Write the report despite an unknown or mismatched baseline; never use to pass a gate.")
    parser.add_argument("--business-criticality", choices=("auto", "low", "medium", "high"), default="auto")
    parser.add_argument("--test-coverage", choices=("auto", "adequate", "partial", "missing"), default="auto")
    parser.add_argument(
        "--change-dir",
        help=(
            "Default report location: existing caller-owned change/task directory "
            "(e.g. openspec/changes/<id>). Reports go to "
            "<change-dir>/evidence/frontend-dependency-upgrade/."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional report directory override. When set, replaces --change-dir resolution.",
    )
    parser.add_argument(
        "--allow-behavior-change",
        action="store_true",
        help="Opt out of default behavior-preserving recommendations; allow promoting removal/replacement when evidence supports it.",
    )
    parser.add_argument("--json-output", nargs="?", const="__auto__", default=None, help="Optional structured JSON path; bare flag writes beside the Markdown report.")
    parser.add_argument("--title", default="前端依赖升级与治理影响分析报告")
    parser.add_argument(
        "--offline",
        action="store_true",
        help=(
            "Caller/human-confirmed offline mode: skip network probes and allow local "
            "upstream-evidence readback. Agents must not set this from .npmrc, private "
            "registry, or intranet heuristics — probe public reachability first."
        ),
    )
    parser.add_argument(
        "--no-upstream-evidence",
        action="store_true",
        help="Disable writing/reading report-adjacent upstream-evidence/ for exact upgrades.",
    )
    parser.add_argument(
        "--cleanup-upstream-evidence",
        action="store_true",
        help="Delete output_dir/upstream-evidence after the report is written successfully.",
    )
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--network-workers", type=int, default=6, help="Maximum concurrent upstream evidence requests.")
    parser.add_argument("--http-cache-dir", help="Persistent public HTTP cache directory; defaults to the user cache directory.")
    parser.add_argument("--http-cache-ttl", type=int, default=21_600, help="Public HTTP response and stable-miss cache TTL in seconds.")
    parser.add_argument("--no-http-cache", action="store_true", help="Disable the persistent HTTP cache for this run.")
    parser.add_argument("--max-github-pages", type=int, default=5)
    parser.add_argument("--max-versions", type=int, default=0, help="0 keeps the complete interval; positive values mark evidence truncated.")
    parser.add_argument("--max-note-chars", type=int, default=1800)
    parser.add_argument("--max-code-points", type=int, default=200)
    parser.add_argument("--max-scan-files", type=int, default=8000)
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    return parser.parse_args(argv)


def missing_upgrade_message() -> str:
    return "请至少提供包名：使用 --upgrade package::target、--assess package、--removal-candidate package，或提供结构化 upgrades 文件。"


def collect_package_reports(upgrades: list[Upgrade], args: argparse.Namespace) -> list[PackageReport]:
    total_workers = max(1, int(args.network_workers))
    if bool(args.offline) or len(upgrades) < 2 or total_workers < 2:
        return [collect_package_report(upgrade, args) for upgrade in upgrades]
    package_workers = min(len(upgrades), max(1, total_workers // 2))
    workers_per_package = max(1, total_workers // package_workers)

    def collect(upgrade: Upgrade) -> PackageReport:
        package_args = argparse.Namespace(**vars(args))
        package_args.network_workers = workers_per_package
        return collect_package_report(upgrade, package_args)

    return parallel_map_ordered(collect, upgrades, package_workers)


def partition_upgrade_batches(upgrades: list[Upgrade]) -> list[tuple[str, list[Upgrade], str]]:
    """Split mixed exact/open-target batches into separate report directories.

    Returns (subdir, upgrades, label). Empty subdir means write at the batch root
    (single-mode runs keep the historical layout).
    """
    exact = [upgrade for upgrade in upgrades if is_exact_upgrade_target(upgrade)]
    open_targets = [upgrade for upgrade in upgrades if not is_exact_upgrade_target(upgrade)]
    if exact and open_targets:
        return [
            ("exact", exact, "精确升级批次（含 upstream-evidence）"),
            ("open-target", open_targets, "开放目标批次（无 upstream-evidence）"),
        ]
    if exact:
        return [("", exact, "精确升级")]
    return [("", open_targets or upgrades, "开放目标")]


EXIT_CODE_PRIORITY = (2, 8, 5, 3, 4, 6, 7, 0)


def merge_exit_codes(codes: list[int]) -> int:
    if not codes:
        return 0
    rank = {code: index for index, code in enumerate(EXIT_CODE_PRIORITY)}
    return sorted(codes, key=lambda code: rank.get(int(code), 99))[0]


def write_batch_index(parent_dir: Path, batches: list[tuple[str, Path, str]]) -> Path:
    parent_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 前端依赖升级影响分析 — 批次索引",
        "",
        "本轮同时包含精确升级与开放目标，已自动拆成两份报告：",
        "",
    ]
    for subdir, report_path, label in batches:
        relative = report_path.name if not subdir else f"{subdir}/{report_path.name}"
        lines.append(f"- **{label}**：`{relative}`")
        if subdir == "exact":
            lines.append(f"  - upstream-evidence：`{subdir}/upstream-evidence/`")
    lines.extend([
        "",
        "release/changelog 下载与落盘仅适用于精确升级批次。",
        "",
    ])
    path = parent_dir / "BATCH-INDEX.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_bundle(
    args: argparse.Namespace,
    output_dir: Path | None = None,
    output_note: str | None = None,
    upgrades: list[Upgrade] | None = None,
) -> AnalysisBundle:
    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise ValueError(f"Project root is not a directory: {project_root}")
    if output_dir is None:
        output_dir, output_note = resolve_report_output_dir(project_root, args.output_dir, args.change_dir)
    elif output_note is None:
        output_note = f"使用调用方提供的输出目录：{output_dir}"
    if upstream_evidence_enabled(args):
        args.upstream_evidence_root = upstream_evidence_dir(output_dir)
    else:
        args.upstream_evidence_root = None
    workspace = resolve_frontend_workspace(project_root, args)
    cache_dir = args.http_cache_dir or default_http_cache_dir()
    configure_http_cache(cache_dir, args.http_cache_ttl, enabled=not args.no_http_cache)
    if upgrades is None:
        upgrades = collect_upgrades(args)
    if not upgrades:
        raise ValueError(missing_upgrade_message())
    package_names = [upgrade.package for upgrade in upgrades]
    manifest_path = Path(args.after_package_json).resolve() if args.after_package_json else project_root / "package.json"
    if workspace.status == "confirmed" and workspace.manifest_path:
        manifest_path = Path(workspace.manifest_path)
    manifest = load_manifest(manifest_path if manifest_path.exists() else None, project_root)
    toolchain_names = sorted(set(manifest.packages) & TOOLCHAIN_PACKAGES)
    initial_analysis_packages = list(dict.fromkeys(package_names + toolchain_names))
    before_lock = parse_lock(
        Path(args.before_lock).resolve() if args.before_lock else None,
        initial_analysis_packages, args.workspace_importer, role="before",
    )
    after_lock = parse_lock(
        Path(args.after_lock).resolve() if args.after_lock else None,
        initial_analysis_packages, args.workspace_importer, role="after",
    )
    current_path = None if args.before_lock or args.after_lock else detect_lock(project_root)
    current_lock = parse_lock(current_path, initial_analysis_packages, args.workspace_importer, role="current")
    infer_current_versions(upgrades, before_lock, current_lock)
    reports = collect_package_reports(upgrades, args)
    peer_names = sorted({
        peer
        for report in reports
        for peer in report.target_peer_dependencies
        if peer not in package_names
    })
    if peer_names:
        analysis_packages = list(dict.fromkeys(initial_analysis_packages + peer_names))
        before_lock = parse_lock(
            Path(args.before_lock).resolve() if args.before_lock else None,
            analysis_packages, args.workspace_importer, role="before",
        )
        after_lock = parse_lock(
            Path(args.after_lock).resolve() if args.after_lock else None,
            analysis_packages, args.workspace_importer, role="after",
        )
        current_lock = parse_lock(current_path, analysis_packages, args.workspace_importer, role="current")
    for report in reports:
        baseline_for(report, manifest, before_lock, current_lock, after_lock)
        assess_peer_compatibility(report, manifest, before_lock, current_lock, after_lock)
    points, scan_warnings, test_files = analyze_code_modification_points(project_root, reports, args.max_code_points, args.max_scan_files, args.max_file_bytes)
    for report in reports:
        assess_removal(report, points)
    evidence_path: Path | None = None
    if args.analysis_evidence_file:
        evidence_path = Path(args.analysis_evidence_file)
        if not evidence_path.is_absolute():
            evidence_path = project_root / evidence_path
        evidence_path = evidence_path.resolve()
    apply_analysis_evidence(reports, load_analysis_evidence(evidence_path))
    graph_lock = current_path or (Path(args.after_lock).resolve() if args.after_lock else None)
    dependency_graph = build_dependency_graph(graph_lock, set(manifest.packages))
    workspace_names = {manifest.packages[name].package for name in manifest.packages
                       if manifest.packages[name].spec.startswith("workspace:")}
    for report in reports:
        report.provenance = assess_provenance(report, manifest, dependency_graph, points, workspace_names)
        report.refactor_plan = build_refactor_plan(report, points)
        reconcile_open_target_report(report)
        if not bool(args.allow_behavior_change):
            apply_behavior_parity(report)
        report.risk = risk_score(report, points, test_files, args.business_criticality, args.test_coverage)
    node_runtime = assess_node_runtime(
        project_root,
        manifest,
        reports,
        load_node_runtime_evidence(evidence_path),
        current_lock if current_lock.kind != "none" else after_lock if after_lock.kind != "none" else before_lock,
    )
    flag_alternative_runtime_conflicts(reports, node_runtime, args)
    assess_alternative_constraint_fit(reports, manifest, current_lock if current_lock.kind != "none" else after_lock)
    verify_replacement_recommendations(
        reports,
        node_runtime,
        manifest,
        current_lock if current_lock.kind != "none" else after_lock,
        args,
    )
    rank_alternative_candidates(reports)
    decision_path = resolve_decision_file(args, output_dir)
    decisions, decision_warnings = load_decision_record(decision_path)
    for report in reports:
        if report.upgrade.to_version or report.analysis_mode == "exact-upgrade":
            finalize_exact_upgrade_report(report, node_runtime)
            report.confirmation = build_proceed_exact_question(report)
            continue
        reconcile_open_target_report(report)
        if report.provenance.parents:
            flag_parent_fix_availability(report, args)
            resolve_override_version(report, node_runtime.selected_project_node, args)
        assign_primary_track(report)
        report.confirmation = build_confirmation_question(report)
        report.alternate_questions = build_alternate_track_questions(report)
        if report.primary_track == "handle-parent" or "handle-parent" in report.alternate_tracks:
            report.parent_questions = build_parent_followups(report)
    decision_warnings.extend(apply_decisions(reports, decisions))
    baseline_blockers = [
        report.upgrade.package for report in reports
        if report.baseline_status in {"mismatch", "unknown"}
    ]
    runtime_analysis_blocked = node_runtime.status == "constraint-conflict"
    workspace_failed = workspace.status == "failed"
    remediation_blocked = any(
        report.exact_upgrade_status == "blocked"
        or report.recommended_action == "remediation-blocked"
        for report in reports
    )
    if workspace_failed:
        for report in reports:
            if report.change_type == "added":
                report.change_type = "unknown"
            report.recommended_action = "resolve-frontend-workspace"
            if workspace.reason and workspace.reason not in report.constraints:
                report.constraints.append(workspace.reason)
            if workspace.reason and workspace.reason not in report.warnings:
                report.warnings.append(workspace.reason)
    status = "blocked" if baseline_blockers or runtime_analysis_blocked or workspace_failed or remediation_blocked else "draft"
    analysis_status = "blocked" if baseline_blockers or runtime_analysis_blocked or workspace_failed or remediation_blocked else "partial"
    decision_status = "needs_choice" if any(
        report.decision_status == "needs_choice" or report.selection_status == "needs_explicit_choice"
        for report in reports
    ) or workspace_failed else "not_needed"
    pending_human_decisions = [
        {
            "package": report.upgrade.package,
            "selection_status": report.selection_status,
            "decisions": "；".join(report.decision_required),
        }
        for report in reports
        if report.selection_status == "needs_explicit_choice" or report.decision_status == "needs_choice"
    ]
    if workspace_failed:
        pending_human_decisions.insert(0, {
            "package": "__frontend_workspace__",
            "selection_status": "failed",
            "decisions": workspace.reason,
        })
    if node_runtime.execution_readiness == "blocked" or node_runtime.status == "runtime-switch-required":
        pending_human_decisions.append({
            "package": "__node_runtime__",
            "selection_status": node_runtime.status,
            "decisions": "；".join(
                node_runtime.blockers
                or ["实施前需明确批准 runtime-switch；缺少 Node/管理器时另行批准一次性安装"]
            ),
        })
    diff_evidence = [
        f"Manifest：{manifest.path or '未建立'}",
        f"升级前 lock：{before_lock.path or '未提供'}",
        f"当前 lock：{current_lock.path or '未检测到'}",
        f"升级后 lock：{after_lock.path or '未提供'}",
        "已完成应用 import/配置静态扫描；间接调用图仍需 Agent 复核。",
        (
            f"上游取证：network_workers={max(1, int(args.network_workers))}；"
            f"HTTP cache={'disabled' if args.no_http_cache else 'enabled'}；"
            f"ttl={max(0, int(args.http_cache_ttl))}s；"
            f"upstream-evidence={'disabled' if args.no_upstream_evidence else 'enabled'}；"
            f"cleanup_upstream_evidence={'yes' if args.cleanup_upstream_evidence else 'no'}；"
            f"network_reachability="
            f"{(getattr(args, 'network_reachability', None) or {}).get('network_reachability', 'unset')}。"
        ),
        f"报告输出：{output_note}",
        (
            f"Node 运行时：status={node_runtime.status}；"
            f"execution_readiness={node_runtime.execution_readiness}；"
            f"selected={node_runtime.selected_project_node or '未建立'}。"
        ),
    ]
    if args.before_package_json and args.after_package_json:
        special_changes = compare_special_fields(Path(args.before_package_json), Path(args.after_package_json))
        diff_evidence.extend(special_changes or ["未检测到 overrides/resolutions/peerDependenciesMeta 变化。"])
    change_dir_value = ""
    if args.change_dir:
        change_path = Path(args.change_dir)
        if not change_path.is_absolute():
            change_path = project_root / change_path
        change_dir_value = str(change_path.resolve())
    elif "change-dir" in output_note:
        # Best-effort: parent of evidence/frontend-dependency-upgrade
        if output_dir.name == "frontend-dependency-upgrade" and output_dir.parent.name == "evidence":
            change_dir_value = str(output_dir.parent.parent)
    parity_on = not bool(args.allow_behavior_change)
    report_paths = {
        "markdown": str((output_dir / "frontend-dependency-upgrade-report.md").resolve()),
    }
    if args.json_output is not None:
        json_path = (
            output_dir / "frontend-dependency-upgrade-report.json"
            if args.json_output == "__auto__"
            else Path(args.json_output).resolve()
        )
        report_paths["json"] = str(json_path)
    evidence_root = getattr(args, "upstream_evidence_root", None)
    if evidence_root is not None and Path(evidence_root).is_dir():
        report_paths["upstream_evidence"] = str(Path(evidence_root).resolve())
    batch_gate, batch_reasons = compute_batch_implementation_gate(
        reports,
        decision_status=decision_status,
        importer_resolution=workspace.status,
        baseline_blockers=baseline_blockers,
        node_runtime=node_runtime,
        workspace_failed=workspace_failed,
        remediation_blocked=remediation_blocked,
    )
    return AnalysisBundle(
        args.title,
        dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        str(project_root), status, reports, points, scan_warnings, manifest,
        before_lock, current_lock, after_lock, diff_evidence, analysis_status, decision_status,
        "yes" if parity_on else "no",
        change_dir_value,
        str(output_dir),
        report_paths,
        pending_human_decisions,
        node_runtime,
        workspace.status,
        str(decision_path or (output_dir / DECISION_FILE_NAME).resolve()),
        decision_warnings,
        batch_gate,
        batch_reasons,
    )


def write_bundle(bundle: AnalysisBundle, args: argparse.Namespace, output_dir: Path | None = None) -> Path:
    target = Path(output_dir or bundle.report_output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    markdown_path = target / "frontend-dependency-upgrade-report.md"
    bundle.report_output_dir = str(target)
    bundle.report_paths["markdown"] = str(markdown_path)
    if args.json_output is not None:
        json_path = target / "frontend-dependency-upgrade-report.json" if args.json_output == "__auto__" else Path(args.json_output).resolve()
        bundle.report_paths["json"] = str(json_path)
    evidence_root = getattr(args, "upstream_evidence_root", None)
    if evidence_root is not None and Path(evidence_root).is_dir():
        bundle.report_paths["upstream_evidence"] = str(Path(evidence_root).resolve())
    markdown = markdown_report(bundle)
    errors = validate_report_contract(markdown)
    if errors:
        raise RuntimeError("Report contract validation failed:\n- " + "\n- ".join(errors))
    markdown_path.write_text(markdown, encoding="utf-8")
    if bool(getattr(args, "cleanup_upstream_evidence", False)):
        cleaned = cleanup_upstream_evidence(Path(evidence_root) if evidence_root else upstream_evidence_dir(target))
        if cleaned:
            bundle.report_paths.pop("upstream_evidence", None)
    if args.json_output is not None:
        json_path = Path(bundle.report_paths["json"])
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(asdict(bundle), ensure_ascii=False, indent=2), encoding="utf-8")
    return markdown_path


def configure_console() -> None:
    """Keep the console's own encoding but stop unencodable characters from aborting the run.

    Report files are always written as UTF-8; only the progress lines are affected here.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (OSError, ValueError):
            pass


def exit_code_for_bundle(bundle: AnalysisBundle, args: argparse.Namespace) -> int:
    if bundle.importer_resolution == "failed":
        workspace_decision = next(
            (item for item in bundle.pending_human_decisions if item.get("package") == "__frontend_workspace__"),
            None,
        )
        print(
            (workspace_decision or {}).get("decisions") or "前端 workspace 未解析",
            file=sys.stderr,
        )
        return 5
    baseline_blockers = [
        f"{report.upgrade.package}({report.baseline_status})"
        for report in bundle.reports
        if report.baseline_status in {"mismatch", "unknown"}
    ]
    if baseline_blockers and not args.allow_baseline_mismatch:
        print(f"基线未对齐：{', '.join(baseline_blockers)}。报告状态为 blocked；确认基线后才能继续。", file=sys.stderr)
        return 3
    if bundle.node_runtime.status == "constraint-conflict":
        print(
            "Node 运行时定框未通过："
            + "；".join(bundle.node_runtime.blockers or ["缺少可验证的项目 Node 约束"])
            + "。报告状态为 blocked；解决后才能进入实施。",
            file=sys.stderr,
        )
        return 4
    exact_blockers = [
        f"{report.upgrade.package}：{'; '.join(report.implementation_blockers)}"
        for report in bundle.reports
        if report.exact_upgrade_status == "blocked"
    ]
    if exact_blockers:
        print(
            "精确升级被兼容性、父依赖或 lock 收敛条件阻止："
            + "；".join(exact_blockers),
            file=sys.stderr,
        )
        return 6
    if bundle.decision_status == "needs_choice":
        pending_packages = [
            item.get("package") or "?"
            for item in bundle.pending_human_decisions
            if item.get("package") not in {"__node_runtime__"}
        ]
        phase = confirmation_queue_phase(bundle)
        phase_hint = {
            "evidence": "当前为待补证据，勿问选型/推进；下一动作=补证据后重跑，不是等待放行",
            "choice": (
                "当前为待人工确认：下一动作=照确认队列向用户提问，不是等待放行；"
                "所有当前 ready 包（开放目标+精确升级）同一波问完；"
                "switch/handle-parent 后续题下一波"
            ),
            "mixed": (
                "部分待补证据、部分可确认；对 ready 包同一波提问，blocked 先补证据；"
                "下一动作不是等待放行"
            ),
        }.get(phase, "见人工确认队列；下一动作=提问或补证据，不是等待放行")
        print(
            f"人工确认未完成（decision_status=needs_choice，phase={phase}，"
            f"batch_implementation_gate={bundle.batch_implementation_gate}）："
            + ("、".join(str(name) for name in pending_packages) or "见人工确认队列")
            + f"。{phase_hint}。报告已写出为 draft；"
            "Agent 须当场处理确认队列，写入 decision-file 并重跑、复核至 analysis_status=complete "
            "前不得宣称本技能完成，不得开计划/实施。",
            file=sys.stderr,
        )
        return 7
    if bundle.batch_implementation_gate == "frozen":
        print(
            "警告：批次实施闸门仍为 frozen（"
            + ("；".join(bundle.batch_gate_reasons) or "见报告")
            + "）。Stage A 决策可能已完成，但不得开实施计划或执行变更。",
            file=sys.stderr,
        )
    return 0


def main(argv: list[str]) -> int:
    configure_console()
    try:
        args = parse_args(argv)
        project_root = Path(args.project_root).resolve()
        output_dir, output_note = resolve_report_output_dir(project_root, args.output_dir, args.change_dir)
        upgrades = collect_upgrades(args)
        if not upgrades:
            raise ValueError(missing_upgrade_message())
        # Double insurance with Agent curl: probe before any upstream collection.
        ensure_network_reachability(args)
        batches = partition_upgrade_batches(upgrades)
        written: list[tuple[str, Path, str]] = []
        codes: list[int] = []
        for subdir, batch_upgrades, label in batches:
            batch_args = argparse.Namespace(**vars(args))
            batch_dir = output_dir / subdir if subdir else output_dir
            batch_note = output_note if not subdir else f"{output_note}；自动拆分 → {subdir}/（{label}）"
            if subdir == "open-target":
                batch_args.no_upstream_evidence = True
            # Split batches always use a per-directory decision file to avoid cross-talk.
            if subdir:
                batch_args.decision_file = str((batch_dir / DECISION_FILE_NAME).resolve())
            bundle = build_bundle(batch_args, batch_dir, batch_note, upgrades=batch_upgrades)
            markdown_path = write_bundle(bundle, batch_args, batch_dir)
            written.append((subdir, markdown_path, label))
            print(f"已写入 [{label}] {markdown_path}")
            print(f"输出解析：{batch_note}")
            codes.append(exit_code_for_bundle(bundle, batch_args))
        if len(written) > 1:
            index_path = write_batch_index(output_dir, written)
            print(f"已写入批次索引 {index_path}")
        return merge_exit_codes(codes)
    except NetworkReachabilityError as exc:
        print(format_network_reachability_error(exc), file=sys.stderr)
        return 8
    except (ValueError, OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

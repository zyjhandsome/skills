#!/usr/bin/env python3
"""Generate evidence-backed frontend dependency upgrade impact reports."""

from __future__ import annotations

import argparse
import concurrent.futures
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


DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)
SPECIAL_FIELDS = ("overrides", "resolutions", "peerDependenciesMeta")
LOCK_NAMES = ("package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock")
VERSION_RE = re.compile(r"(?P<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)")
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
    "@angular/cli", "@playwright/test", "@vue/cli-service", "cypress", "eslint",
    "esbuild", "gulp", "jest", "next", "nuxt", "parcel", "playwright",
    "react-scripts", "rollup", "typescript", "vite", "vitest", "webpack",
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
    "Conclusion": "结论",
}
REQUIRED_HEADINGS = tuple(REPORT_SECTION_TITLES)
CODE_CATEGORY_TITLES = {
    "Dependency declaration/config": "依赖声明/配置",
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
ANALYSIS_MODES = {
    "exact-upgrade",
    "auto-assess",
    "target-discovery",
    "removal-assessment",
    "compliance-assessment",
    "replacement-discovery",
}
COMPLIANCE_STATUSES = {"eligible", "ineligible", "unknown"}
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
class LockSnapshot:
    kind: str = "none"
    path: str = ""
    lockfile_version: str = ""
    importer: str = "."
    direct_versions: dict[str, str] = field(default_factory=dict)
    all_versions: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ManifestPackage:
    package: str
    field: str = ""
    spec: str = ""


@dataclass
class ManifestSnapshot:
    path: str = ""
    package_manager: str = ""
    engines: dict[str, Any] = field(default_factory=dict)
    volta: dict[str, Any] = field(default_factory=dict)
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
    removal: RemovalAssessment = field(default_factory=RemovalAssessment)
    decision_required: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    selection_status: str = "not_applicable"


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


def clean_version(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith(("workspace:", "file:", "link:", "github:", "git+", "http:" , "https:")):
        return value
    if value.startswith("npm:"):
        match = VERSION_RE.search(value)
        return match.group("version") if match else value
    value = value.split("||", 1)[0].strip()
    match = VERSION_RE.search(value.lstrip("v^~<>= "))
    return match.group("version") if match else value


def semver_key(value: str) -> tuple[int, int, int, int, str] | None:
    version = clean_version(value)
    match = VERSION_RE.fullmatch(version)
    if not match:
        return None
    base = version.split("+", 1)[0]
    main, _, prerelease = base.partition("-")
    major, minor, patch = (int(part) for part in main.split("."))
    return major, minor, patch, 1 if not prerelease else 0, prerelease


def compare_versions(left: str, right: str) -> int | None:
    left_key = semver_key(left)
    right_key = semver_key(right)
    if left_key is None or right_key is None:
        return None
    return (left_key > right_key) - (left_key < right_key)


def classify_change(from_version: str, to_version: str) -> str:
    if not from_version and to_version:
        return "added"
    if from_version and not to_version:
        return "removed"
    before = semver_key(from_version)
    after = semver_key(to_version)
    if before is None or after is None:
        return "unknown"
    if before[0] != after[0]:
        return "major"
    if before[1] != after[1]:
        return "minor"
    if before != after:
        return "patch"
    return "same"


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


def load_manifest(path: Path | None) -> ManifestSnapshot:
    if path is None or not path.exists():
        return ManifestSnapshot(path=str(path or ""))
    data = read_json(path)
    snapshot = ManifestSnapshot(
        path=str(path.resolve()),
        package_manager=str(data.get("packageManager") or ""),
        engines=data.get("engines") or {},
        volta=data.get("volta") or {},
    )
    for field_name in DEPENDENCY_FIELDS:
        for package, spec in (data.get(field_name) or {}).items():
            snapshot.packages[package] = ManifestPackage(package, field_name, str(spec))
    for field_name in SPECIAL_FIELDS:
        if field_name in data:
            snapshot.special_entries.extend(f"{field_name}.{row}" for row in flatten_mapping(data[field_name]))
    return snapshot


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


def detect_lock(project_root: Path) -> Path | None:
    for name in LOCK_NAMES:
        path = project_root / name
        if path.exists():
            return path
    return None


def add_version(mapping: dict[str, list[str]], package: str, version: str) -> None:
    version = clean_version(version)
    if semver_key(version) is None:
        return
    mapping.setdefault(package, [])
    if version not in mapping[package]:
        mapping[package].append(version)


def parse_npm_lock(path: Path, packages: list[str], importer: str) -> LockSnapshot:
    data = read_json(path)
    snapshot = LockSnapshot("npm", str(path.resolve()), str(data.get("lockfileVersion") or ""), importer)
    package_set = set(packages)
    entries = data.get("packages") or {}
    if isinstance(entries, dict) and entries:
        for key, info in entries.items():
            if not isinstance(info, dict):
                continue
            for package in package_set:
                marker = f"node_modules/{package}"
                if key.replace("\\", "/").endswith(marker) and info.get("version"):
                    add_version(snapshot.all_versions, package, str(info["version"]))
                direct_key = f"node_modules/{package}" if importer in {"", "."} else f"{importer.strip('/')}/node_modules/{package}"
                if key.replace("\\", "/") == direct_key and info.get("version"):
                    snapshot.direct_versions[package] = clean_version(info["version"])
    dependencies = data.get("dependencies") or {}

    def walk(node: dict[str, Any], depth: int = 0) -> None:
        for name, info in node.items():
            if not isinstance(info, dict):
                continue
            if name in package_set and info.get("version"):
                add_version(snapshot.all_versions, name, str(info["version"]))
                if depth == 0:
                    snapshot.direct_versions[name] = clean_version(info["version"])
            walk(info.get("dependencies") or {}, depth + 1)

    if isinstance(dependencies, dict):
        walk(dependencies)
    return snapshot


def unquote_yaml(value: str) -> str:
    return value.strip().strip("'\"")


def parse_pnpm_direct(lines: list[str], packages: set[str], importer: str) -> dict[str, str]:
    direct: dict[str, str] = {}
    in_importers = False
    current_importer = ""
    current_field = ""
    current_package = ""
    for raw in lines:
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))
        if stripped == "importers:":
            in_importers = True
            continue
        if not in_importers or not stripped or stripped.startswith("#"):
            continue
        if indent == 0 and stripped.endswith(":"):
            break
        if indent == 2 and stripped.endswith(":"):
            current_importer = unquote_yaml(stripped[:-1])
            current_field = ""
            current_package = ""
            continue
        if current_importer != importer:
            continue
        if indent == 4 and stripped.rstrip(":") in {"dependencies", "devDependencies", "optionalDependencies"}:
            current_field = stripped.rstrip(":")
            current_package = ""
            continue
        if not current_field:
            continue
        version_line = re.match(r"^\s{8}version:\s+(.+)$", raw)
        if indent == 8 and version_line and current_package in packages:
            direct[current_package] = clean_version(unquote_yaml(version_line.group(1)).split("(", 1)[0])
            continue
        scalar = re.match(r"^\s{6}([^:]+):\s+(.+)$", raw)
        if indent == 6 and scalar:
            package = unquote_yaml(scalar.group(1))
            if package in packages:
                direct[package] = clean_version(unquote_yaml(scalar.group(2)).split("(", 1)[0])
            current_package = ""
            continue
        nested = re.match(r"^\s{6}([^:]+):\s*$", raw)
        if indent == 6 and nested:
            current_package = unquote_yaml(nested.group(1))
            continue
    return direct


def parse_pnpm_lock(path: Path, packages: list[str], importer: str) -> LockSnapshot:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    version_match = re.search(r"^lockfileVersion:\s*['\"]?([^'\"\s]+)", text, re.M)
    snapshot = LockSnapshot("pnpm", str(path.resolve()), version_match.group(1) if version_match else "", importer)
    snapshot.direct_versions = parse_pnpm_direct(lines, set(packages), importer)
    for package in packages:
        escaped = re.escape(package)
        patterns = [
            rf"^[ \t]*['\"]?/?{escaped}@(?P<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)",
            rf"^[ \t]*/?{escaped}/(?P<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?):",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.M):
                add_version(snapshot.all_versions, package, match.group("version"))
        if package in snapshot.direct_versions:
            add_version(snapshot.all_versions, package, snapshot.direct_versions[package])
    if not snapshot.direct_versions:
        snapshot.warnings.append(f"未能解析 pnpm importer {importer!r} 的直接版本；请核验 workspace importer。")
    return snapshot


def parse_yarn_lock(path: Path, packages: list[str], importer: str) -> LockSnapshot:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    snapshot = LockSnapshot("yarn", str(path.resolve()), "", importer)
    current_selectors = ""
    observed: dict[str, list[str]] = {package: [] for package in packages}
    for raw in text.splitlines():
        if raw and not raw[0].isspace() and raw.rstrip().endswith(":"):
            current_selectors = raw.rstrip()[:-1].strip("'\"")
            continue
        version_match = re.match(r"^\s+version\s+['\"]?([^'\"\s]+)", raw)
        if not version_match:
            continue
        version = clean_version(version_match.group(1))
        for package in packages:
            if re.search(rf"(?:^|[,\s'\"]){re.escape(package)}@", current_selectors):
                add_version(observed, package, version)
    snapshot.all_versions = {key: value for key, value in observed.items() if value}
    for package, versions in snapshot.all_versions.items():
        if len(versions) == 1:
            snapshot.direct_versions[package] = versions[0]
        else:
            snapshot.warnings.append(f"Yarn lock 包含多个 {package} 版本；缺少包管理器输出时无法唯一确定 workspace 直接解析版本。")
    return snapshot


def parse_lock(path: Path | None, packages: list[str], importer: str = ".") -> LockSnapshot:
    if path is None or not path.exists():
        return LockSnapshot(path=str(path or ""), importer=importer, warnings=["未找到 lockfile。"])
    if path.name in {"package-lock.json", "npm-shrinkwrap.json"}:
        return parse_npm_lock(path, packages, importer)
    if path.name == "pnpm-lock.yaml":
        return parse_pnpm_lock(path, packages, importer)
    if path.name == "yarn.lock":
        return parse_yarn_lock(path, packages, importer)
    return LockSnapshot(path=str(path.resolve()), importer=importer, warnings=["不支持该 lockfile 类型。"])


def package_url(package: str, version: str = "") -> str:
    quoted = urllib.parse.quote(package, safe="@/")
    suffix = f"/v/{urllib.parse.quote(version, safe='')}" if version else ""
    return f"https://www.npmjs.com/package/{quoted}{suffix}"


def registry_url(package: str) -> str:
    return f"https://registry.npmjs.org/{urllib.parse.quote(package, safe='')}"


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
    for attempt in range(max(1, attempts)):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                text = response.read().decode(charset, errors="replace")
                write_http_cache(url, text, authenticated=bool(headers.get("Authorization")))
                return text
        except urllib.error.HTTPError as exc:
            if exc.code in {404, 410}:
                write_http_cache(url, None, authenticated=bool(headers.get("Authorization")))
                return None
            if exc.code not in {403, 429, 500, 502, 503, 504} or attempt + 1 >= attempts:
                return None
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 >= attempts:
                return None
    return None


def request_json(url: str, timeout: int) -> Any | None:
    text = request_text(url, timeout)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def parallel_map_ordered(function: Any, items: list[Any], workers: int) -> list[Any]:
    if len(items) < 2 or workers <= 1:
        return [function(item) for item in items]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max(1, workers), len(items))) as executor:
        return list(executor.map(function, items))


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


def semver_satisfies(version: str, requirement: str) -> bool | None:
    key = semver_key(version)
    if key is None:
        return None
    requirement = str(requirement or "").strip()
    if not requirement or requirement == "*":
        return True
    outcomes: list[bool] = []
    for alternative in requirement.split("||"):
        hyphen = re.fullmatch(
            r"\s*(\d+(?:\.\d+){0,2})\s+-\s+(\d+(?:\.\d+){0,2})\s*",
            alternative,
        )
        if hyphen:
            lower_parts = [int(part) for part in hyphen.group(1).split(".")]
            upper_parts = [int(part) for part in hyphen.group(2).split(".")]
            lower = ".".join(str(part) for part in (lower_parts + [0, 0])[:3])
            upper_fill = upper_parts + [999999, 999999]
            upper = ".".join(str(part) for part in upper_fill[:3])
            return (compare_versions(version, lower) or 0) >= 0 and (compare_versions(version, upper) or 0) <= 0
        tokens = [token for token in re.split(r"[\s,]+", alternative.strip()) if token and token != "-"]
        if not tokens:
            outcomes.append(True)
            continue
        valid = True
        understood = False
        for token in tokens:
            if token in {"*", "x", "X"}:
                understood = True
                continue
            wildcard = re.fullmatch(r"v?(\d+)(?:\.(\d+|x|X|\*))?(?:\.(\d+|x|X|\*))?", token)
            if wildcard and any(part in {None, "x", "X", "*"} for part in wildcard.groups()[1:]):
                understood = True
                major = int(wildcard.group(1))
                minor = wildcard.group(2)
                if key[0] != major or (minor not in {None, "x", "X", "*"} and key[1] != int(minor)):
                    valid = False
                continue
            match = re.fullmatch(r"(>=|<=|>|<|\^|~)?v?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)", token)
            partial_comparator = re.fullmatch(r"(>=|<=|>|<)v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", token)
            if not match and partial_comparator:
                operator = partial_comparator.group(1)
                raw_parts = list(partial_comparator.groups()[1:])
                provided = sum(part is not None for part in raw_parts)
                lower_parts = [int(part or 0) for part in raw_parts]
                lower = ".".join(str(part) for part in lower_parts)
                upper_parts = list(lower_parts)
                if provided == 1:
                    upper_parts = [lower_parts[0] + 1, 0, 0]
                elif provided == 2:
                    upper_parts = [lower_parts[0], lower_parts[1] + 1, 0]
                else:
                    upper_parts[2] += 1
                upper = ".".join(str(part) for part in upper_parts)
                understood = True
                lower_comparison = compare_versions(version, lower)
                upper_comparison = compare_versions(version, upper)
                if lower_comparison is None or upper_comparison is None:
                    return None
                valid = valid and {
                    ">=": lower_comparison >= 0,
                    "<=": upper_comparison < 0 if provided < 3 else lower_comparison <= 0,
                    ">": upper_comparison >= 0 if provided < 3 else lower_comparison > 0,
                    "<": lower_comparison < 0,
                }[operator]
                continue
            if not match:
                continue
            understood = True
            operator, wanted = match.groups()
            comparison = compare_versions(version, wanted)
            if comparison is None:
                return None
            wanted_key = semver_key(wanted)
            if operator == "^" and wanted_key:
                upper = (
                    f"{wanted_key[0] + 1}.0.0" if wanted_key[0] > 0
                    else (f"0.{wanted_key[1] + 1}.0" if wanted_key[1] > 0 else f"0.0.{wanted_key[2] + 1}")
                )
                valid = valid and comparison >= 0 and (compare_versions(version, upper) or 0) < 0
            elif operator == "~" and wanted_key:
                upper = f"{wanted_key[0]}.{wanted_key[1] + 1}.0"
                valid = valid and comparison >= 0 and (compare_versions(version, upper) or 0) < 0
            elif operator == ">=":
                valid = valid and comparison >= 0
            elif operator == "<=":
                valid = valid and comparison <= 0
            elif operator == ">":
                valid = valid and comparison > 0
            elif operator == "<":
                valid = valid and comparison < 0
            else:
                valid = valid and comparison == 0
        if understood and valid:
            return True
        if understood:
            outcomes.append(False)
    return False if outcomes else None


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
    github = project_root / ".github" / "workflows"
    if github.is_dir():
        candidates.extend(sorted(github.glob("*.yml")))
        candidates.extend(sorted(github.glob("*.yaml")))
    for name in (".gitlab-ci.yml", "azure-pipelines.yml", "azure-pipelines.yaml"):
        path = project_root / name
        if path.is_file():
            candidates.append(path)
    candidates.extend(sorted(project_root.glob("Dockerfile*")))
    patterns = (
        ("ci-node-version", re.compile(r"node-version\s*:\s*['\"]?([^'\"#\s,\]]+)", re.I)),
        ("container-node-image", re.compile(r"(?:FROM|image\s*:)\s*node:([0-9][^@\s]*)", re.I)),
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


def node_constraint_candidates(requirements: list[str]) -> list[str]:
    candidates: set[str] = set()
    for requirement in requirements:
        for match in re.finditer(r"\d+(?:\.\d+){0,2}", requirement):
            parts = [int(part) for part in match.group(0).split(".")]
            normalized = (parts + [0, 0])[:3]
            candidates.add(".".join(str(part) for part in normalized))
            candidates.add(f"{normalized[0]}.{normalized[1]}.99")
            candidates.add(f"{normalized[0]}.99.99")
    for major in range(0, 41):
        candidates.update({f"{major}.0.0", f"{major}.20.0", f"{major}.99.99"})
    return sorted(candidates, key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))


def version_satisfies_all(version: str, constraints: list[NodeConstraint]) -> bool | None:
    outcomes = [semver_satisfies(version, item.requirement) for item in constraints]
    if any(outcome is False for outcome in outcomes):
        return False
    if any(outcome is None for outcome in outcomes):
        return None
    return True


def preferred_node_version(versions: Iterable[str]) -> str:
    exact = [value for value in versions if semver_key(value) is not None]
    if not exact:
        return ""
    lts_candidates = [
        value for value in exact
        if (semver_key(value) or (1, 0, 0, 0, ""))[0] % 2 == 0
        and not (semver_key(value) or (0, 0, 0, 0, ""))[4]
    ]
    pool = lts_candidates or exact
    return max(pool, key=lambda value: semver_key(value) or (0, 0, 0, 0, ""))


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
    for constraint in installed_toolchain_runtime_evidence(project_root, manifest, lock):
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
        major = (semver_key(assessment.selected_project_node) or (999, 0, 0, 0, ""))[0]
        if major <= 16:
            assessment.warnings.append(
                f"Node {assessment.selected_project_node} 已处于 EOL 范围；仅在隔离环境中用于项目验证"
            )
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
        if not str(evidence.get("selected_project_node") or ""):
            assessment.compatible_installed_versions = []
            assessment.selected_project_node = ""
            assessment.selected_manager = ""
            assessment.recommended_strategy = "read-only-analysis"

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
        existing = {candidate.version: candidate for candidate in report.target_candidates}
        for candidate_row in row.get("target_candidates") or []:
            if not isinstance(candidate_row, dict):
                raise ValueError(f"{package}.target_candidates 每一项必须是对象")
            version = exact_candidate_version(candidate_row.get("version"), f"{package} 同库候选")
            existing[version] = target_candidate_from_evidence(package, candidate_row, existing.get(version))
        report.target_candidates = sorted(
            existing.values(),
            key=lambda candidate: semver_key(candidate.version) or (0, 0, 0, 0, ""),
        )
        alternatives = row.get("alternative_candidates") or []
        if alternatives:
            report.alternative_candidates = [
                alternative_candidate_from_evidence(package, candidate)
                for candidate in alternatives
                if isinstance(candidate, dict)
            ]
            if len(report.alternative_candidates) != len(alternatives):
                raise ValueError(f"{package}.alternative_candidates 每一项必须是对象")
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
    eligible_targets = [
        candidate for candidate in report.target_candidates
        if candidate.compliance_status == "eligible"
    ]
    non_ineligible_targets = [
        candidate for candidate in report.target_candidates
        if candidate.compliance_status != "ineligible"
    ]
    eligible_alternatives = [
        candidate for candidate in report.alternative_candidates
        if candidate.compliance_status == "eligible"
    ]
    if report.removal.status == "safe_removal_candidate":
        report.recommended_action = "review-removal"
        append_unique(
            report.decision_required,
            "删除证据满足安全候选门槛；删除仍需人显式选择，未获选择时继续比较同库或替代方案。",
        )
    elif eligible_targets:
        report.recommended_action = "review-same-package-candidates"
    elif non_ineligible_targets:
        report.recommended_action = "review-same-package-candidates"
        append_unique(report.decision_required, "同库候选尚未全部完成合规核验，不能直接选定目标版本。")
    elif eligible_alternatives or report.alternative_candidates:
        report.recommended_action = "research-replacement"
        append_unique(report.decision_required, "同库无合规可行候选；替代库仍需人显式选择。")
    elif report.removal.status == "requires_migration":
        report.recommended_action = "plan-migration-before-removal"
    elif report.removal.status == "not_viable":
        report.recommended_action = "retain-or-govern"
    else:
        report.recommended_action = "review-removal"


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
        decision_status="not_needed" if upgrade.to_version else "needs_choice",
        recommended_action="upgrade" if upgrade.to_version else "assess",
        selection_status="selected" if upgrade.to_version else "needs_explicit_choice",
    )
    if not upgrade.to_version:
        report.decision_required.append("尚未选择目标版本；需要由人确认升级、删除、替换或保留方案。")
    if not upgrade.reason and upgrade.intent in {"auto-assess", "compliance-assessment", "target-discovery"}:
        report.decision_required.append("尚未建立治理或不合规依据；先核对仓库政策、安全、license、兼容性和维护状态。")
    endpoint = normalized.to_version or normalized.from_version or "unknown"
    if args.offline:
        report.notes.append(VersionNote(endpoint, change_type=report.change_type, release_notes="离线模式：需要人工收集官方发布证据。", changelog="离线模式：需要人工收集官方变更日志。", sources=[package_url(upgrade.package, endpoint)], evidence_status="offline"))
        report.evidence_completeness = "offline"
        report.evidence_dimensions = {dimension: "offline" for dimension in EVIDENCE_DIMENSIONS}
        report.warnings.append("使用了离线模式；报告不能标记为 complete。")
        return report
    metadata = request_json(registry_url(upgrade.package), args.timeout)
    if not isinstance(metadata, dict):
        report.notes.append(VersionNote(endpoint, change_type=report.change_type, release_notes="无法获取 npm 元数据。", changelog="需要人工复核上游资料。", sources=[package_url(upgrade.package, endpoint)]))
        report.warnings.append("获取 npm registry 元数据失败。")
        return report
    report.evidence_dimensions["registry"] = "confirmed"
    report.repository_url, report.repository_directory, report.repository_source_version = repository_details_for_version(metadata, endpoint)
    report.homepage = str(metadata.get("homepage") or "")
    if normalized.to_version:
        target_metadata = (metadata.get("versions") or {}).get(normalized.to_version, {}) or {}
        report.target_peer_dependencies = target_metadata.get("peerDependencies") or {}
        report.target_peer_dependencies_meta = target_metadata.get("peerDependenciesMeta") or {}
        report.target_engines = target_metadata.get("engines") or {}
    elif upgrade.intent != "removal-assessment":
        report.target_candidates = discover_target_candidates(metadata, normalized)
        if report.target_candidates:
            report.recommended_action = "review-removal"
            report.warnings.append("已预取同库版本候选；它们只在删除不成立、不确定或未被选择后进入比较。")
        else:
            report.recommended_action = "review-removal"
            report.decision_required.append("同库尚未发现更高稳定版本；若删除不成立或未被选择，需要研究替代库或保留/豁免方案。")
    if normalized.to_version:
        selected, warnings, interval_complete = versions_in_range(metadata, normalized, args.max_versions)
    elif report.target_candidates:
        selected = [candidate.version for candidate in report.target_candidates]
        warnings = ["目标版本尚未由人选择；候选版本证据不能替代选型决定。"]
        interval_complete = False
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
        if release_status == "ambiguous":
            status = "ambiguous"
            source_ambiguous = True
        elif release_status in {"substantive", "substantive-linked"} and changelog_status == "confirmed":
            status = "confirmed"
        elif release_status in {"substantive", "pointer", "thin", "tag-only"} or changelog_status == "confirmed":
            status = "partial"
        else:
            status = "missing"
        release_confirmed = release_confirmed and release_status in {"substantive", "substantive-linked"}
        changelog_confirmed = changelog_confirmed and changelog_status == "confirmed"
        report.notes.append(VersionNote(
            version=version,
            published=str(times.get(version) or "")[:10] or str(release.get("published") or ""),
            change_type=classify_change(normalized.from_version, version),
            release_notes=release_text or (
                "该版本只有官方 Git tag，未找到 GitHub Release 正文。"
                if release_status == "tag-only"
                else "未找到可确认属于目标包的 GitHub Release 正文。"
            ),
            changelog=changelog_text or (
                "已找到 changelog 文档，但未能提取该版本章节。"
                if changelog else "未找到官方 changelog 文档。"
            ),
            sources=list(dict.fromkeys(sources)),
            evidence_status=status,
            release_status=release_status,
            changelog_status=changelog_status,
            repository_url=repository_url,
            repository_source=repository_source,
            repository_validation=repository_validation,
        ))
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
    report.evidence_dimensions["release"] = "confirmed" if release_confirmed else ("ambiguous" if source_ambiguous else "candidate")
    report.evidence_dimensions["changelog"] = "confirmed" if changelog_confirmed else "candidate"
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
    report.evidence_completeness = evidence_completeness(report.evidence_dimensions, interval_complete)
    if len(set(report.repository_lineage.values())) > 1:
        report.warnings.append("版本区间跨越不同 repository；已按版本拆分 release/changelog 取证。")
    if source_ambiguous:
        report.evidence_completeness = "ambiguous"
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
                    category = "Dependency declaration/config" if is_config else "Direct package usage"
                    key = (report.upgrade.package, relative, line_number, category)
                    if key not in seen:
                        seen.add(key)
                        points.append(CodeModificationPoint(
                            report.upgrade.package, relative, line_number, category, truncate(line, 240),
                            upstream_reason_for(report, f"此处直接用法必须核对 {report.upgrade.package} {report.upgrade.from_version}->{report.upgrade.to_version} 的完整变更区间。"),
                            "对照官方迁移证据确认 import、选项、props、类型和 peer 相关配置。",
                            validation_for_type(report.upgrade.dependency_type), point_priority(relative, report.change_type, category), "high",
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
        if not (Path(point.file).name == "package.json" and point.category == "Dependency declaration/config")
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
            report.recommended_action = "review-same-package-candidates" if report.target_candidates else "research-replacement"
            if report.target_candidates:
                report.decision_required.append("删除不能作为无适配操作；需要由人从已核验合规性的同库精确版本中选择，或决定迁移后删除。")
            else:
                report.decision_required.append("删除需要迁移且尚无同库可行版本；需要研究替代库、保留或治理方案。")
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
    if report.target_candidates:
        report.decision_required.append("若最终不删除，已收集的同库版本仅作为待合规核验的后续候选。")
    elif report.analysis_mode != "removal-assessment":
        report.decision_required.append("若最终不删除，需要继续研究同库合规精确版本；同库无解时再研究替代库。")


def baseline_for(report: PackageReport, manifest: ManifestSnapshot, before_lock: LockSnapshot, current_lock: LockSnapshot, after_lock: LockSnapshot) -> None:
    package = report.upgrade.package
    manifest_package = manifest.packages.get(package)
    if manifest_package:
        report.manifest_field = manifest_package.field
        report.manifest_spec = manifest_package.spec
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
    else:
        report.baseline_status = "unknown"


def risk_score(report: PackageReport, points: list[CodeModificationPoint], test_files: list[str], business_override: str, coverage_override: str) -> RiskAssessment:
    change_scores = {"same": 0, "patch": 1, "minor": 3, "added": 3, "unknown": 3, "major": 5, "removed": 5}
    type_scores = {"runtime": 1, "dev-tooling": 1, "typescript": 2, "style": 2, "test": 2, "state": 4, "dom-runtime": 4, "framework": 5, "router": 5, "ui": 5, "request": 5, "build": 5}
    package_points = [point for point in points if point.package == report.upgrade.package]
    files = {point.file for point in package_points}
    if not files:
        usage = 0
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
        business = 3
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
    factors = {
        "version_change": change_scores.get(report.change_type, 3),
        "dependency_type": type_scores.get(report.upgrade.dependency_type, 2),
        "usage_scope": usage,
        "business_criticality": business,
        "lockfile_change": lock,
        "test_coverage_gap": coverage,
        "peer_compatibility": 5 if report.peer_compatibility_status == "incompatible" else (
            2 if report.peer_compatibility_status == "unknown" else 0
        ),
    }
    total = sum(factors.values())
    automatic = "Low" if total <= 5 else ("Medium" if total <= 12 else "High")
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
    return RiskAssessment(factors, total, automatic, final, rationale)


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
    return module, ", ".join(flows) or "需要补充路由/调用方映射"


def overall_level(reports: list[PackageReport]) -> str:
    rank = {"Low": 0, "Medium": 1, "High": 2}
    return max((report.risk.final_level for report in reports), key=lambda value: rank.get(value, 1), default="Medium")


def md_cell(value: Any, max_chars: int = 420) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return html.escape(truncate(text, max_chars), quote=False).replace("|", "\\|") or "-"


def visible_code_category(value: str) -> str:
    return CODE_CATEGORY_TITLES.get(value, value)


def report_section(anchor: str) -> list[str]:
    return [f"<!-- section: {anchor} -->", f"## {REPORT_SECTION_TITLES[anchor]}"]


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
        f"- 报告状态：`{bundle.status}`",
        f"- 分析状态：`{bundle.analysis_status}`",
        f"- 决策状态：`{bundle.decision_status}`",
        f"- 行为守恒要求：`{bundle.behavior_parity_required}`",
        f"- Node 运行时状态：`{bundle.node_runtime.status}`",
        f"- 执行就绪度：`{bundle.node_runtime.execution_readiness}`",
        f"- 本机当前 Node：`{bundle.node_runtime.current_host_node or '未检测到'}`；路径：`{bundle.node_runtime.current_host_node_path or '未检测到'}`",
        f"- 项目 Node：`{bundle.node_runtime.selected_project_node or '未建立'}`；管理器：`{bundle.node_runtime.selected_manager or '未建立'}`",
        f"- 关联 change/任务目录：`{bundle.change_dir or '未绑定'}`",
        f"- 报告目录：`{bundle.report_output_dir}`",
        f"- 报告路径：`{json.dumps(bundle.report_paths, ensure_ascii=False, sort_keys=True)}`",
        f"- 批次：精确升级 `{exact_count}` / 待人工决策 `{pending_count}` / blocked 项 `{blocked_count}`",
        "",
        *report_section("Upgrade Summary"), "",
        "| 包 | 分析模式 | 治理/升级原因 | 原版本 | 目标版本 | 建议动作 | 选择状态 | 决策状态 | 约束 | 变化类型 | 依赖类型 | Manifest 声明 | Lock 直接解析 | 基线状态 | 风险分 | 风险等级 | 证据完整性 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|",
    ]
    for report in bundle.reports:
        direct = report.current_lock_version or report.before_lock_version or report.after_lock_version or "-"
        lines.append("| " + " | ".join(md_cell(value) for value in (
            report.upgrade.package, report.analysis_mode, report.upgrade.reason, report.upgrade.from_version, report.upgrade.to_version,
            report.recommended_action, report.selection_status, report.decision_status, "; ".join(report.constraints), report.change_type,
            report.upgrade.dependency_type, report.manifest_spec, direct, report.baseline_status,
            report.risk.total, report.risk.final_level, report.evidence_completeness,
        )) + " |")

    lines.extend(["", *report_section("Release Notes And Changelog Evidence"), ""])
    for report in bundle.reports:
        lines.extend([f"### {report.upgrade.package} `{report.upgrade.from_version} -> {report.upgrade.to_version}`", "", f"- 完整性：`{report.evidence_completeness}`", f"- 包页面：{report.package_url}"])
        if report.repository_url:
            lines.append(f"- 代码仓库：{report.repository_url}")
        if report.homepage:
            lines.append(f"- 官方主页：{report.homepage}")
        lines.append(f"- 仓库校验：`{report.repository_validation_status}`；版本来源：`{report.repository_source_version}`")
        lines.append(f"- 证据维度：`{json.dumps(report.evidence_dimensions, ensure_ascii=False, sort_keys=True)}`")
        if report.repository_lineage:
            lines.append(f"- 版本仓库谱系：`{json.dumps(report.repository_lineage, ensure_ascii=False, sort_keys=True)}`")
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
        open_target = report.analysis_mode in {"auto-assess", "compliance-assessment", "target-discovery"}
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
            f"- 目标 peerDependencies：`{json.dumps(report.target_peer_dependencies, ensure_ascii=False, sort_keys=True) if report.target_peer_dependencies else '未建立'}`",
            f"- Peer 兼容性：`{report.peer_compatibility_status}`；冲突：`{'; '.join(report.peer_compatibility_conflicts) or '无'}`",
            f"- 目标 engines：`{json.dumps(report.target_engines, ensure_ascii=False, sort_keys=True) if report.target_engines else '未建立'}`",
            "",
        ])
        if open_target:
            lines.extend([
                "#### 处置决策顺序", "",
                "- `删除评估 → 同库合规精确版本 → 替代库精确版本 → 保留/豁免/隔离/fork/移除功能`",
                "- 版本候选只有在删除不成立、不确定或未被选择时才进入人工比较。",
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
        if report.target_candidates:
            lines.extend([
                "#### 同库目标版本候选", "",
                "- 以下候选尚需按安全、license、维护状态和仓库政策核验；registry 版本本身不等于合规。",
                "",
                "| 精确版本 | 候选类型 | 合规状态 | 核查标准 | 排除原因 | 发布日期 | PeerDependencies | Engines | 兼容性 | 合规/维护 | 迁移成本 | 验证范围 | 回滚难度 | 推荐理由 | 可信度 | 证据 |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
            ])
            for candidate in report.target_candidates:
                lines.append("| " + " | ".join(md_cell(value) for value in (
                    candidate.version, candidate.candidate_type, candidate.compliance_status,
                    "; ".join(candidate.criteria_checked), "; ".join(candidate.disqualifiers), candidate.published,
                    json.dumps(candidate.peer_dependencies, ensure_ascii=False, sort_keys=True),
                    json.dumps(candidate.engines, ensure_ascii=False, sort_keys=True),
                    candidate.compatibility, candidate.compliance_and_maintenance,
                    candidate.migration_cost, candidate.validation_scope, candidate.rollback_difficulty,
                    candidate.rationale, candidate.confidence,
                    "; ".join(candidate.evidence_urls or ([candidate.source] if candidate.source else [])),
                )) + " |")
            lines.append("")
        elif open_target and report.removal.status != "safe_removal_candidate":
            lines.extend([
                "#### 同库目标版本候选", "",
                "- 尚未建立。删除不成立、不确定或未被选择时，需要研究 1～3 个满足治理条件的同库精确版本。",
                "",
            ])
        if report.alternative_candidates:
            lines.extend([
                "#### 替代库候选", "",
                "| 包 | 精确版本 | 合规状态 | 核查标准 | 排除原因 | 兼容性 | 合规/维护 | 迁移成本 | 验证范围 | 回滚难度 | 推荐理由 | 可信度 | 证据 |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
            ])
            for candidate in report.alternative_candidates:
                lines.append("| " + " | ".join(md_cell(value) for value in (
                    candidate.package, candidate.version, candidate.compliance_status,
                    "; ".join(candidate.criteria_checked), "; ".join(candidate.disqualifiers), candidate.compatibility,
                    candidate.compliance_and_maintenance, candidate.migration_cost,
                    candidate.validation_scope, candidate.rollback_difficulty,
                    candidate.rationale, candidate.confidence,
                    "; ".join(candidate.evidence_urls or ([candidate.source] if candidate.source else [])),
                )) + " |")
            lines.append("")
        elif open_target and report.removal.status != "safe_removal_candidate" and not report.target_candidates:
            lines.extend([
                "#### 替代库候选", "",
                "- 尚未建立。同库没有合规可行版本时，需要 Agent 基于官方资料研究 2～3 个候选及其精确版本；不得自动选型。",
                "",
            ])
    runtime = bundle.node_runtime
    lines.extend([
        "### Node 运行时兼容性", "",
        f"- 状态：`{runtime.status}`；执行就绪度：`{runtime.execution_readiness}`",
        f"- 本机当前 Node：`{runtime.current_host_node or '未检测到'}`；路径：`{runtime.current_host_node_path or '未检测到'}`",
        f"- 所选项目 Node：`{runtime.selected_project_node or '未建立'}`；管理器：`{runtime.selected_manager or '未建立'}`",
        f"- 可用管理器：`{', '.join(runtime.available_managers) or '未检测到'}`",
        f"- 已安装版本：`{json.dumps(runtime.installed_versions, ensure_ascii=False, sort_keys=True) if runtime.installed_versions else '未检测到'}`",
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
        direct_files = sorted({point.file for point in bundle.code_points if point.package == report.upgrade.package and point.category in {"Direct package usage", "Dependency declaration/config"}})
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
        module, flows = business_module(point.file)
        key = (point.package, module)
        if key in emitted:
            continue
        emitted.add(key)
        report = next(report for report in bundle.reports if report.upgrade.package == point.package)
        lines.append("| " + " | ".join(md_cell(value) for value in (point.package, module, flows, report.risk.final_level, f"根据 {point.file} 映射；仍需调用方追踪")) + " |")
    if not emitted:
        lines.append("| - | 未建立 | 需要补充路由/调用方映射 | Medium | 尚未建立直接代码引用证据 |")

    lines.extend(["", *report_section("Technical Risks"), "", "| 包 | 风险 | 严重度 | 证据 | 缓解措施 |", "|---|---|---|---|---|"])
    for report in bundle.reports:
        factor_text = ", ".join(f"{name}={score}" for name, score in report.risk.factors.items())
        lines.append("| " + " | ".join(md_cell(value) for value in (
            report.upgrade.package, "七因素升级风险", report.risk.final_level,
            f"总分 {report.risk.total}：{factor_text}；{'; '.join(report.risk.rationale) or '未覆盖自动等级'}",
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
        "", *report_section("Conclusion"), "",
        f"- 总体风险：`{level}`",
        f"- 报告状态：`{bundle.status}`",
        f"- 分析状态：`{bundle.analysis_status}`",
        f"- 决策状态：`{bundle.decision_status}`",
        f"- 行为守恒要求：`{bundle.behavior_parity_required}`",
        f"- Node 运行时状态：`{runtime.status}`；执行就绪度：`{runtime.execution_readiness}`",
        f"- Node 阻塞项：{'; '.join(runtime.blockers) or '无'}",
        f"- 报告目录：`{bundle.report_output_dir}`",
        "- 最低可接受验证：确认准确 lock/peer/engine，执行受影响自动化检查，覆盖关键成功/失败/恢复流程，具备监控和已验证的回滚路径。",
        "- 剩余工作：标记为 `complete` 前，解决所有“未建立”“需要 Agent 复核”、基线不一致、证据警告、未翻译上游摘要和间接调用方映射缺口。",
    ])
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
    has_candidate_table = "| 精确版本 | 候选类型 |" in markdown or "| 包 | 精确版本 | 合规状态 |" in markdown
    if has_candidate_table and (
        "合规状态" not in markdown or "核查标准" not in markdown or "排除原因" not in markdown
    ):
        errors.append("候选矩阵缺少结构化合规字段。")
    errors.extend(markdown_table_errors(markdown))
    return errors


def apply_behavior_parity(report: PackageReport) -> None:
    """Bias recommendations toward same-package upgrades; keep removal/replacement as human choices."""
    if report.analysis_mode == "exact-upgrade" and report.upgrade.to_version:
        report.constraints.append("行为守恒：仅允许为实现该精确目标所必需的适配；禁止顺手重构业务/UI。")
        report.selection_status = "selected"
        return
    eligible_targets = [
        candidate for candidate in report.target_candidates
        if candidate.compliance_status == "eligible"
    ]
    if report.recommended_action == "review-removal":
        if eligible_targets:
            report.recommended_action = "prefer-same-package-upgrade"
            report.decision_required.append(
                "行为守恒：删除仍为待选项；默认偏好同库合规精确升级，须由人显式选择删除或目标版本。"
            )
        elif report.target_candidates:
            report.recommended_action = "review-same-package-candidates"
            report.decision_required.append(
                "行为守恒：同库候选尚未完成合规核验；删除/换库仍须显式选择。"
            )
        else:
            report.recommended_action = "prefer-same-package-or-retain"
            report.decision_required.append(
                "行为守恒：删除结论未批准；优先继续核验同库合规版本或保留，替代库须显式选择。"
            )
    elif report.recommended_action == "research-replacement":
        report.recommended_action = "prefer-same-package-or-retain"
        report.decision_required.append("行为守恒：替代库仅作候选；默认不纳入已选定范围，须人显式选择。")
    elif report.recommended_action == "review-same-package-candidates":
        if eligible_targets:
            report.recommended_action = "prefer-same-package-upgrade"
            report.decision_required.append("行为守恒：请从同库合规精确版本中选择；删除/换库须另作显式决定。")
        else:
            report.decision_required.append("行为守恒：先完成同库候选合规核验；删除/换库须另作显式决定。")
    report.decision_status = "needs_choice"
    report.selection_status = "needs_explicit_choice"


def resolve_report_output_dir(project_root: Path, output_dir: str | None, change_dir: str | None) -> tuple[Path, str]:
    """
    Return (output_path, resolution_note).
    Prefer explicit output-dir, then an explicit existing change-dir evidence folder, else fallback.
    """
    if output_dir:
        path = Path(output_dir)
        if not path.is_absolute():
            path = project_root / path
        return path.resolve(), f"使用显式 --output-dir：{path}"

    selected_change: Path | None = None
    note = ""
    if change_dir:
        selected_change = Path(change_dir)
        if not selected_change.is_absolute():
            selected_change = project_root / selected_change
        selected_change = selected_change.resolve()
        if not selected_change.is_dir():
            raise ValueError(f"--change-dir 不是目录：{selected_change}")
        note = f"使用 --change-dir：{selected_change}"

    if selected_change is not None:
        path = selected_change / "evidence" / "frontend-dependency-upgrade"
        return path, note or f"写入 change 证据目录：{path}"

    path = (project_root / "dependency-upgrade-report").resolve()
    return path, (
        "未提供 --output-dir 或既有 --change-dir；回退到 "
        f"{path}。若需归档到某次任务，请显式提供该任务的 --change-dir。"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Frontend workspace root; defaults to current directory.")
    parser.add_argument("--upgrade", action="append", default=[], help="package:from:to or package::to (infer current version); repeatable.")
    parser.add_argument("--assess", action="append", default=[], help="Package with no selected target; assess removal first, then compliant same-package and alternative options.")
    parser.add_argument("--removal-candidate", action="append", default=[], help="Package to assess for possible removal; repeatable.")
    parser.add_argument("--reason", action="append", default=[], help="Optional package=reason or compliance concern; repeatable.")
    parser.add_argument("--upgrades-file", help="JSON/CSV with package, optional from/to, intent, reason rows.")
    parser.add_argument(
        "--analysis-evidence-file",
        help="Agent-reviewed JSON with compliance candidates, alternatives, removal coverage, and constraints.",
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
        help="Existing caller-owned change/task directory. Reports go to <change-dir>/evidence/frontend-dependency-upgrade/.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Explicit report directory. Overrides --change-dir resolution when set.",
    )
    parser.add_argument(
        "--allow-behavior-change",
        action="store_true",
        help="Opt out of default behavior-preserving recommendations; allow promoting removal/replacement when evidence supports it.",
    )
    parser.add_argument("--json-output", nargs="?", const="__auto__", default=None, help="Optional structured JSON path; bare flag writes beside the Markdown report.")
    parser.add_argument("--title", default="前端依赖升级与治理影响分析报告")
    parser.add_argument("--offline", action="store_true")
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


def build_bundle(
    args: argparse.Namespace,
    output_dir: Path | None = None,
    output_note: str | None = None,
) -> AnalysisBundle:
    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise ValueError(f"Project root is not a directory: {project_root}")
    if output_dir is None:
        output_dir, output_note = resolve_report_output_dir(project_root, args.output_dir, args.change_dir)
    elif output_note is None:
        output_note = f"使用调用方提供的输出目录：{output_dir}"
    cache_dir = args.http_cache_dir or default_http_cache_dir()
    configure_http_cache(cache_dir, args.http_cache_ttl, enabled=not args.no_http_cache)
    upgrades = collect_upgrades(args)
    if not upgrades:
        raise ValueError(missing_upgrade_message())
    package_names = [upgrade.package for upgrade in upgrades]
    manifest_path = Path(args.after_package_json).resolve() if args.after_package_json else project_root / "package.json"
    manifest = load_manifest(manifest_path if manifest_path.exists() else None)
    toolchain_names = sorted(set(manifest.packages) & TOOLCHAIN_PACKAGES)
    initial_analysis_packages = list(dict.fromkeys(package_names + toolchain_names))
    before_lock = parse_lock(Path(args.before_lock).resolve() if args.before_lock else None, initial_analysis_packages, args.workspace_importer)
    after_lock = parse_lock(Path(args.after_lock).resolve() if args.after_lock else None, initial_analysis_packages, args.workspace_importer)
    current_path = None if args.before_lock or args.after_lock else detect_lock(project_root)
    current_lock = parse_lock(current_path, initial_analysis_packages, args.workspace_importer)
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
        before_lock = parse_lock(Path(args.before_lock).resolve() if args.before_lock else None, analysis_packages, args.workspace_importer)
        after_lock = parse_lock(Path(args.after_lock).resolve() if args.after_lock else None, analysis_packages, args.workspace_importer)
        current_lock = parse_lock(current_path, analysis_packages, args.workspace_importer)
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
    for report in reports:
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
    baseline_blockers = [
        report.upgrade.package for report in reports
        if report.baseline_status in {"mismatch", "unknown"}
    ]
    runtime_analysis_blocked = node_runtime.status == "constraint-conflict"
    status = "blocked" if baseline_blockers or runtime_analysis_blocked else "draft"
    analysis_status = "blocked" if baseline_blockers or runtime_analysis_blocked else "partial"
    decision_status = "needs_choice" if any(
        report.decision_status == "needs_choice" or report.selection_status == "needs_explicit_choice"
        for report in reports
    ) else "not_needed"
    pending_human_decisions = [
        {
            "package": report.upgrade.package,
            "selection_status": report.selection_status,
            "decisions": "；".join(report.decision_required),
        }
        for report in reports
        if report.selection_status == "needs_explicit_choice" or report.decision_status == "needs_choice"
    ]
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
            f"ttl={max(0, int(args.http_cache_ttl))}s。"
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
    markdown = markdown_report(bundle)
    errors = validate_report_contract(markdown)
    if errors:
        raise RuntimeError("Report contract validation failed:\n- " + "\n- ".join(errors))
    markdown_path.write_text(markdown, encoding="utf-8")
    if args.json_output is not None:
        json_path = Path(bundle.report_paths["json"])
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(asdict(bundle), ensure_ascii=False, indent=2), encoding="utf-8")
    return markdown_path


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        project_root = Path(args.project_root).resolve()
        output_dir, output_note = resolve_report_output_dir(project_root, args.output_dir, args.change_dir)
        bundle = build_bundle(args, output_dir, output_note)
        markdown_path = write_bundle(bundle, args, output_dir)
    except (ValueError, OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"已写入 {markdown_path}")
    print(f"输出解析：{output_note}")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

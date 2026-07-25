#!/usr/bin/env python3
"""Lockfile detection and parsing for the upgrade report generator.

Each parser records the workspace importer's direct resolution separately from every
observed version, so duplicate or peer-context copies never masquerade as the baseline.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from upgrade_semver import clean_version, semver_key


LOCK_NAMES = ("package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb")
LOCK_ROLE_LABELS = {"current": "当前", "before": "升级前", "after": "升级后"}


@dataclass
class LockSnapshot:
    kind: str = "none"
    path: str = ""
    lockfile_version: str = ""
    importer: str = "."
    direct_versions: dict[str, str] = field(default_factory=dict)
    all_versions: dict[str, list[str]] = field(default_factory=dict)
    # `engines.node` recorded by the lock for the resolved direct version, keyed by package.
    # Only npm and pnpm locks carry it; Yarn v1 and Bun locks leave it empty.
    declared_engines: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LockEdge:
    """One `parent@version depends on child (range)` edge read from the lock."""

    parent: str
    parent_version: str
    child: str
    requirement: str


@dataclass
class DependencyGraph:
    """Reverse dependency edges for the whole lock, used to explain transitive packages."""

    kind: str = "none"
    supported: bool = False
    # child package -> edges that pull it in. Root/workspace edges use parent `__root__`.
    dependents: dict[str, list[LockEdge]] = field(default_factory=dict)
    roots: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)

    def add(self, edge: LockEdge) -> None:
        bucket = self.dependents.setdefault(edge.child, [])
        if edge not in bucket:
            bucket.append(edge)
        if edge.parent == ROOT_NODE:
            self.roots.add(edge.child)

    def parents_of(self, package: str) -> list[LockEdge]:
        return [edge for edge in self.dependents.get(package, []) if edge.parent != ROOT_NODE]

    def paths_to(self, package: str, limit: int = 5, max_depth: int = 12) -> tuple[list[list[str]], int]:
        """Root-to-package paths, capped. Returns the kept paths and the total found.

        Breadth-first from the package upwards so the shortest, most actionable chains
        come first; a package pulled in by dozens of parents would otherwise bury them.
        """
        found: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()
        total = 0
        budget = 20_000
        queue: list[tuple[str, list[str]]] = [(package, [package])]
        while queue and budget > 0:
            budget -= 1
            current, trail = queue.pop(0)
            if len(trail) > max_depth:
                continue
            edges = self.dependents.get(current, [])
            if not edges:
                continue
            for edge in edges:
                if edge.parent == ROOT_NODE:
                    chain = tuple(reversed(trail))
                    if chain in seen:
                        continue
                    seen.add(chain)
                    total += 1
                    if len(found) < limit:
                        found.append(list(chain))
                    continue
                if edge.parent in trail:
                    continue
                queue.append((edge.parent, trail + [edge.parent]))
        return found, total


ROOT_NODE = "__root__"
DEPENDENCY_EDGE_FIELDS = ("dependencies", "optionalDependencies", "peerDependencies")


def read_lock_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


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
    data = read_lock_json(path)
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
                    requirement = str((info.get("engines") or {}).get("node") or "")
                    if requirement:
                        snapshot.declared_engines[package] = requirement
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


def pnpm_declared_engines(lines: list[str], package: str, version: str) -> str:
    """Read `engines.node` from the pnpm `packages:` block of one resolved version."""
    header = re.compile(
        rf"^(?P<indent>[ \t]*)['\"]?/?{re.escape(package)}[@/]{re.escape(version)}"
        r"(?:\([^)]*\))?['\"]?:\s*$"
    )
    inline = re.compile(r"^[ \t]*engines:\s*\{[^}]*\bnode:\s*(?P<requirement>[^,}]+)")
    block = re.compile(r"^[ \t]*engines:\s*$")
    nested = re.compile(r"^[ \t]*node:\s*(?P<requirement>.+?)\s*$")
    for index, line in enumerate(lines):
        match = header.match(line)
        if not match:
            continue
        indent = len(match.group("indent"))
        in_engines_block = False
        for candidate in lines[index + 1:]:
            if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
                break
            if in_engines_block:
                nested_match = nested.match(candidate)
                if nested_match:
                    return unquote_yaml(nested_match.group("requirement"))
                if candidate.strip():
                    in_engines_block = False
            inline_match = inline.match(candidate)
            if inline_match:
                return unquote_yaml(inline_match.group("requirement"))
            if block.match(candidate):
                in_engines_block = True
    return ""


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
            requirement = pnpm_declared_engines(lines, package, snapshot.direct_versions[package])
            if requirement:
                snapshot.declared_engines[package] = requirement
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


def strip_jsonc(text: str) -> str:
    """Remove JSONC comments and trailing commas while leaving string literals untouched."""
    output: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == '"':
            end = index + 1
            while end < length:
                if text[end] == "\\":
                    end += 2
                    continue
                if text[end] == '"':
                    break
                end += 1
            output.append(text[index:end + 1])
            index = end + 1
            continue
        if char == "/" and index + 1 < length and text[index + 1] == "/":
            index = text.find("\n", index)
            if index == -1:
                break
            continue
        if char == "/" and index + 1 < length and text[index + 1] == "*":
            end = text.find("*/", index + 2)
            index = length if end == -1 else end + 2
            continue
        output.append(char)
        index += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(output))


def parse_bun_lock(path: Path, packages: list[str], importer: str) -> LockSnapshot:
    snapshot = LockSnapshot(kind="bun", path=str(path.resolve()), importer=importer)
    if path.name == "bun.lockb":
        snapshot.warnings.append(
            "bun.lockb 是二进制 lockfile，无法读取直接解析版本；请提交 `bun.lock`（Bun 1.2+ 文本锁）"
            "或运行 `bun install --save-text-lockfile` 后重跑分析。"
        )
        return snapshot
    try:
        data = json.loads(strip_jsonc(path.read_text(encoding="utf-8", errors="ignore")))
    except (OSError, json.JSONDecodeError) as exc:
        snapshot.warnings.append(f"bun.lock 解析失败：{exc}")
        return snapshot
    snapshot.lockfile_version = str(data.get("lockfileVersion") or "")
    workspaces = data.get("workspaces") or {}
    workspace_key = "" if importer in {".", ""} else importer
    declared = workspaces.get(workspace_key)
    if declared is None and workspace_key:
        snapshot.warnings.append(f"bun.lock 中未找到 workspace {importer!r}；请核验 --workspace-importer。")
    entries = data.get("packages") or {}
    observed: dict[str, list[str]] = {}
    for key, value in entries.items():
        identifier = value[0] if isinstance(value, list) and value else ""
        version = clean_version(str(identifier).rsplit("@", 1)[-1]) if "@" in str(identifier) else ""
        if not version:
            continue
        leaf = str(key).rsplit("/", 1)[-1]
        for package in packages:
            if leaf != package:
                continue
            add_version(observed, package, version)
            if str(key) == package:
                snapshot.direct_versions.setdefault(package, version)
    snapshot.all_versions = {key: value for key, value in observed.items() if value}
    return snapshot


def npm_entry_name(key: str) -> str:
    """Package name for an npm `packages` key such as `node_modules/a/node_modules/@b/c`."""
    normalized = key.replace("\\", "/")
    marker = "node_modules/"
    index = normalized.rfind(marker)
    return normalized[index + len(marker):] if index >= 0 else ""


def npm_graph(data: Any, graph: DependencyGraph) -> None:
    entries = data.get("packages") if isinstance(data, dict) else None
    if isinstance(entries, dict) and entries:
        for key, info in entries.items():
            if not isinstance(info, dict):
                continue
            name = npm_entry_name(str(key)) or str(info.get("name") or "")
            version = clean_version(str(info.get("version") or ""))
            parent = name or ROOT_NODE
            if str(key) in {"", "."}:
                parent, version = ROOT_NODE, ""
            for group in DEPENDENCY_EDGE_FIELDS + ("devDependencies",):
                if parent != ROOT_NODE and group == "devDependencies":
                    continue  # a dependency's own devDependencies are not installed
                for child, requirement in (info.get(group) or {}).items():
                    graph.add(LockEdge(parent, version, str(child), str(requirement)))
        graph.supported = True
        return
    legacy = data.get("dependencies") if isinstance(data, dict) else None
    if isinstance(legacy, dict):
        def walk(node: dict[str, Any], parent: str, parent_version: str) -> None:
            for name, info in node.items():
                if not isinstance(info, dict):
                    continue
                graph.add(LockEdge(parent, parent_version, str(name), str(info.get("version") or "")))
                for child, requirement in (info.get("requires") or {}).items():
                    graph.add(LockEdge(str(name), clean_version(str(info.get("version") or "")), str(child), str(requirement)))
                walk(info.get("dependencies") or {}, str(name), clean_version(str(info.get("version") or "")))

        walk(legacy, ROOT_NODE, "")
        graph.supported = True


def pnpm_graph(lines: list[str], graph: DependencyGraph) -> None:
    """Read `snapshots:`/`packages:` dependency blocks from a pnpm lock."""
    header = re.compile(r"^  ['\"]?/?(?P<name>@?[^@'\"]+(?:/[^@'\"]+)?)@(?P<version>[^'\"(:]+)")
    entry = re.compile(r"^\s{6}['\"]?(?P<name>@?[^:'\"]+)['\"]?:\s*(?P<requirement>.+)$")
    current_name = ""
    current_version = ""
    in_dependencies = False
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            current_name, current_version, in_dependencies = "", "", False
            continue
        if indent == 2:
            match = header.match(raw)
            current_name = match.group("name") if match else ""
            current_version = clean_version(match.group("version").split("(", 1)[0]) if match else ""
            in_dependencies = False
            continue
        if indent == 4:
            in_dependencies = stripped.rstrip(":") in {"dependencies", "optionalDependencies", "peerDependencies"}
            continue
        if indent == 6 and in_dependencies and current_name:
            match = entry.match(raw)
            if match:
                graph.add(LockEdge(
                    current_name, current_version, unquote_yaml(match.group("name")),
                    unquote_yaml(match.group("requirement")),
                ))
    graph.supported = bool(graph.dependents)


def yarn_graph(text: str, graph: DependencyGraph) -> None:
    current_names: list[str] = []
    current_version = ""
    in_dependencies = False
    entry = re.compile(r"^\s{4}['\"]?(?P<name>@?[^\s'\"]+?)['\"]?\s+['\"]?(?P<requirement>[^'\"]+)['\"]?\s*$")
    for raw in text.splitlines():
        if raw and not raw[0].isspace() and raw.rstrip().endswith(":"):
            selectors = raw.rstrip()[:-1]
            current_names = []
            for selector in selectors.split(","):
                cleaned = selector.strip().strip("'\"")
                name = cleaned[: cleaned.rindex("@")] if "@" in cleaned[1:] else cleaned
                if name and name not in current_names:
                    current_names.append(name)
            current_version = ""
            in_dependencies = False
            continue
        stripped = raw.strip()
        version_match = re.match(r"^\s+version\s+['\"]?([^'\"\s]+)", raw)
        if version_match:
            current_version = clean_version(version_match.group(1))
            continue
        if stripped in {"dependencies:", "optionalDependencies:"}:
            in_dependencies = True
            continue
        if raw and not raw.startswith("    "):
            in_dependencies = False
            continue
        if in_dependencies and current_names:
            match = entry.match(raw)
            if match:
                for name in current_names:
                    graph.add(LockEdge(name, current_version, match.group("name"), match.group("requirement")))
    graph.supported = bool(graph.dependents)


def bun_graph(data: Any, graph: DependencyGraph) -> None:
    entries = data.get("packages") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        return
    for key, value in entries.items():
        if not isinstance(value, list):
            continue
        identifier = str(value[0]) if value else ""
        version = clean_version(identifier.rsplit("@", 1)[-1]) if "@" in identifier else ""
        name = str(key).rsplit("/", 1)[-1]
        info = next((item for item in value if isinstance(item, dict)), {})
        for group in DEPENDENCY_EDGE_FIELDS:
            for child, requirement in (info.get(group) or {}).items():
                graph.add(LockEdge(name, version, str(child), str(requirement)))
    graph.supported = bool(graph.dependents)


def build_dependency_graph(path: Path | None, root_packages: Iterable[str]) -> DependencyGraph:
    """Reverse dependency edges plus the workspace's own declarations as root edges.

    Root edges come from the manifest rather than the lock: Yarn v1 and Bun locks do not
    mark which entries the workspace declares, and the manifest is authoritative anyway.
    """
    graph = DependencyGraph()
    for package in root_packages:
        graph.add(LockEdge(ROOT_NODE, "", package, "manifest"))
    if path is None or not path.exists():
        graph.warnings.append("缺少 lockfile：无法判定传递依赖的父包链，来源判定降级为 unknown。")
        return graph
    graph.kind = path.name
    try:
        if path.name in {"package-lock.json", "npm-shrinkwrap.json"}:
            npm_graph(read_lock_json(path), graph)
        elif path.name == "pnpm-lock.yaml":
            pnpm_graph(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), graph)
        elif path.name == "yarn.lock":
            yarn_graph(path.read_text(encoding="utf-8-sig", errors="replace"), graph)
        elif path.name == "bun.lock":
            bun_graph(json.loads(strip_jsonc(path.read_text(encoding="utf-8", errors="ignore"))), graph)
        elif path.name == "bun.lockb":
            graph.warnings.append("bun.lockb 是二进制 lockfile，无法构建父包链；请提交 bun.lock 文本锁。")
        else:
            graph.warnings.append(f"lock 类型 {path.name} 不支持父包链解析。")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        graph.warnings.append(f"解析父包链失败：{path.name}（{error}）")
    if not graph.supported and not graph.warnings:
        graph.warnings.append(f"未能从 {path.name} 解析出依赖边；父包链不可用。")
    return graph


def parse_lock(path: Path | None, packages: list[str], importer: str = ".", role: str = "current") -> LockSnapshot:
    label = LOCK_ROLE_LABELS.get(role, role)
    if path is None:
        # Missing before/after locks are the normal pre-upgrade state, not a finding.
        warnings = [] if role != "current" else [
            "未在项目根目录找到受支持的 lockfile（" + " / ".join(LOCK_NAMES) + "）；直接解析版本无法确认。"
        ]
        return LockSnapshot(path="", importer=importer, warnings=warnings)
    if not path.exists():
        return LockSnapshot(path=str(path), importer=importer, warnings=[f"{label} lock 路径不存在：{path}"])
    if path.name in {"package-lock.json", "npm-shrinkwrap.json"}:
        return parse_npm_lock(path, packages, importer)
    if path.name == "pnpm-lock.yaml":
        return parse_pnpm_lock(path, packages, importer)
    if path.name == "yarn.lock":
        return parse_yarn_lock(path, packages, importer)
    if path.name in {"bun.lock", "bun.lockb"}:
        return parse_bun_lock(path, packages, importer)
    return LockSnapshot(
        path=str(path.resolve()),
        importer=importer,
        warnings=[f"{label} lock 类型不受支持：{path.name}；受支持类型为 " + " / ".join(LOCK_NAMES) + "。"],
    )

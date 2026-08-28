#!/usr/bin/env python3
"""Generate hosted AngularJS/JSP/jQuery to Vue3 migration evidence artifacts."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Iterable


EXCLUDED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".cache",
    "node_modules",
    "dist",
    "build",
    "target",
    "coverage",
    "covers",
    "docs",
    "doc",
    "reports",
    "report",
    "evidence",
    "openspec",
    "test",
    "tests",
    "e2e",
    "e2e-tests",
    "__tests__",
    "vendor",
    "vendors",
    "lib",
    "libs",
    "locale",
    "locales",
}

DEPENDENCY_NOISE_DIRS = {
    "node_modules",
    "dist",
    "build",
    "target",
    "coverage",
    "vendor",
    "vendors",
    ".cache",
}

LOCKFILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
}

MINIFIED_RE = re.compile(r"\.min\.(js|css)$", re.I)
TEST_FILE_RE = re.compile(r"(\.|-)(spec|test|e2e)\.(js|jsx|ts|tsx|vue)$", re.I)
ARTIFACT_HTML_RE = re.compile(r"(evidence|report|coverage|openspec|handoff|verification).*\.html?$", re.I)
SOURCE_PAGE_EXTS = {".jsp", ".jspx", ".html", ".htm", ".ftl", ".vm"}
HOST_PAGE_EXTS = {".vue", ".html", ".htm", ".jsx", ".tsx"}
SOURCE_CODE_EXTS = {".java", ".kt", ".groovy", ".xml", ".properties", ".yml", ".yaml", ".json", ".js", ".ts"}
HOST_CODE_EXTS = {".js", ".ts", ".vue", ".json", ".mjs", ".cjs", ".html", ".htm"}

SOURCE_SIGNALS = {
    "angularjs": r"ng-app|ng-controller|ng-repeat|ng-model|ng-src|ng-href|ng-if|ng-show|ng-hide|ng-class|ng-click|ng-change|angular\.module|\.controller\(|\.component\(|\.directive\(",
    "jquery": r"\$\(document\)\.ready|\$\(function|\.on\(|\.click\(|\.change\(|\.submit\(|\$\.ajax\(",
    "server-template": r"<%@|<jsp:|th:(?:text|if|each|href|src|class|object|field|value|action|replace|insert|fragment|with|unless|switch|case|include|attr)\b|layout:|session\.|request\.",
    "ajax": r"\$http|\$resource|\$\.ajax\(|\$\.get\(|\$\.post\(|axios\.|fetch\(",
    "dom": r"\.val\(|\.html\(|\.text\(|\.append\(|\.show\(|\.hide\(|\.addClass\(|\.removeClass\(",
    "plugin": r"DataTables|dataTable|jqGrid|bootstrapTable|datepicker|zTree|modal\(|upload|select2|chosen|validate\(",
}

HOST_SIGNAL_PATTERNS = {
    "router": r"createRouter|vue-router|routes\s*[:=]|beforeEach",
    "pinia": r"defineStore|createPinia|pinia",
    "vuex": r"createStore|mapState|vuex",
    "axios": r"axios\.|create\(\{|interceptors",
    "i18n": r"createI18n|vue-i18n|\$t\(",
    "proxy": r"proxy\s*:",
    "permission": r"permission|auth|beforeEach|roles|menus?",
    "jquery": r"jquery|\$\(",
    "mpa": r"getPages|pagesDir|src/pages|entry\s*:",
}

FLOW_CONTRACT_HEADERS = [
    "FLOW-ID",
    "Step",
    "Entry/Trigger",
    "Condition",
    "Input",
    "Processing",
    "Output",
    "Call Target",
    "Side Effect",
    "Business Meaning",
    "Evidence",
    "Confidence",
    "Related CHAIN-ID",
]

VARIABLE_CHAIN_HEADERS = [
    "CHAIN-ID",
    "Step",
    "VAR-ID",
    "Normalized Path",
    "Operation",
    "Scope/Function",
    "Upstream",
    "Downstream",
    "Condition",
    "Business Meaning",
    "Evidence",
    "Confidence",
    "Vue3 Host Target",
]

GATE_ROWS = [
    ["behavior", "inputs, validation, branches, success/error/empty/loading states", "pending evidence"],
    ["permission", "menu, route, button hide/disable, server-side rejection", "pending evidence"],
    ["url", "old deep link, query/hash, redirects, back/forward, external links", "pending evidence"],
    ["api", "endpoint, method, params/body, response codes, failure handling", "pending evidence"],
    ["visual", "screenshot or measurement evidence; otherwise manual-only", "manual-only until measured"],
    ["runtime", "host Node, lockfile, existing lint/build/test commands", "pending host command run"],
    ["git hygiene", "no dependency/cache/build directory in intended commit; distinguish business clean from repo clean", "pending git status review"],
    ["rollback", "switch, scope, owner, restore condition, data compatibility", "pending design"],
    ["completion authority", "domain verify is evidence only; completion requires Delivery verified + domain verify + current host revision", "pending both gates"],
]

DESIGN_READY_ROWS = [
    ["page closure", "source templates/fragments/scripts/controllers/services/APIs/assets identified", "not-ready: empty-contract"],
    ["core flows", "at least 1-2 material business FLOW rows filled for the selected unit", "not-ready: empty-contract"],
    ["variable/API chains", "material request/response/state/DOM chains filled or unresolved with runtime checks", "not-ready: empty-contract"],
    ["host decisions", "reuse/change/create decisions for host entry/router/API/store/components/i18n/style", "not-ready: empty-contract"],
    ["URL mapping", "old source URL to new host entry backed by Java/menu/MPA evidence", "not-ready: empty-contract"],
    ["permission/API/rollback", "permission/session/API parity and rollback condition drafted", "not-ready: empty-contract"],
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        parts = {part.lower() for part in rel.parts[:-1]}
        if parts & EXCLUDED_DIRS:
            continue
        rel_text = str(rel).replace("\\", "/")
        if TEST_FILE_RE.search(path.name) or ARTIFACT_HTML_RE.search(rel_text):
            continue
        if MINIFIED_RE.search(path.name):
            continue
        if path.suffix.lower() in {".map", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf"}:
            continue
        yield path


def git_revision(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def is_git_repo(root: Path) -> bool:
    try:
        subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except Exception:
        return False


def git_status_paths(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return []

    paths = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.replace("\\", "/"))
    return paths


def is_dependency_noise(path: str) -> bool:
    parts = {part for part in re.split(r"[/\\]+", path) if part}
    return bool(parts & DEPENDENCY_NOISE_DIRS)


def is_lockfile(path: str) -> bool:
    return Path(path).name in LOCKFILES


def repo_acquisition_rows(args, source: Path, host: Path) -> list[dict[str, str]]:
    warnings = {
        "source": args.source_acquisition_warning or "",
        "host": args.host_acquisition_warning or "",
    }
    rows = []
    for role, repo in (("source", source), ("host", host)):
        git_repo = is_git_repo(repo)
        status_paths = git_status_paths(repo) if git_repo else []
        status = "existing-git-repo" if git_repo else "path-exists-not-git"
        if warnings[role] and git_repo:
            status = "clone-warning-existing-git-repo"
        rows.append(
            {
                "repo_role": role,
                "repo_path": str(repo),
                "acquisition_status": status,
                "acquisition_warning": warnings[role],
                "revision": git_revision(repo),
                "revision_source": "git rev-parse --short HEAD" if git_repo else "unavailable",
                "dirty_entries": str(len(status_paths)),
                "usable_for_stage": "yes" if git_repo and git_revision(repo) != "unknown" else "no",
                "notes": "existing repository reused; record clone warnings separately" if warnings[role] else "",
            }
        )
    return rows


def git_hygiene_rows(source: Path, host: Path) -> list[dict[str, str]]:
    rows = []
    for role, repo in (("source", source), ("host", host)):
        paths = git_status_paths(repo) if is_git_repo(repo) else []
        dependency_noise = [path for path in paths if is_dependency_noise(path)]
        lockfiles = [path for path in paths if is_lockfile(path)]
        business_changes = [
            path for path in paths
            if not is_dependency_noise(path) and not is_lockfile(path)
        ]
        src_changes = [
            path for path in business_changes
            if path.startswith("src/") or "/src/" in path or path.startswith("webapp/") or "/webapp/" in path
        ]
        if not paths:
            stage_status = "clean"
        elif dependency_noise:
            stage_status = "blocked-by-dependency-noise"
        elif role == "source" and business_changes:
            stage_status = "source-dirty-review-required"
        else:
            stage_status = "review-required"
        rows.append(
            {
                "repo_role": role,
                "status_entries": str(len(paths)),
                "business_changes": str(len(business_changes)),
                "src_or_webapp_changes": str(len(src_changes)),
                "lockfile_changes": str(len(lockfiles)),
                "dependency_noise": str(len(dependency_noise)),
                "stage_status": stage_status,
                "notes": "src clean is not repo clean; dependency/cache/build noise must not enter commits" if paths else "clean worktree",
            }
        )
    return rows


def load_package_json(root: Path) -> dict:
    package_path = root / "package.json"
    if not package_path.exists():
        return {}
    try:
        return json.loads(read_text(package_path))
    except json.JSONDecodeError:
        return {}


def package_versions(package: dict) -> dict[str, str]:
    merged = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        value = package.get(key)
        if isinstance(value, dict):
            merged.update(value)
    return merged


def detect_lockfile(root: Path) -> str:
    for filename in ("pnpm-lock.yaml", "yarn.lock", "package-lock.json", "bun.lockb"):
        if (root / filename).exists():
            return filename
    return "not found"


def detect_node(root: Path, package: dict) -> str:
    engines = package.get("engines") if isinstance(package, dict) else None
    if isinstance(engines, dict) and engines.get("node"):
        return str(engines["node"])
    volta = package.get("volta") if isinstance(package, dict) else None
    if isinstance(volta, dict) and volta.get("node"):
        return f"volta {volta['node']}"
    for filename in (".nvmrc", ".node-version"):
        path = root / filename
        if path.exists():
            return read_text(path).strip()
    return "not declared"


def search_host_signal(root: Path, pattern: str) -> int:
    regex = re.compile(pattern, re.I)
    count = 0
    for path in iter_files(root):
        if path.suffix.lower() not in {".js", ".ts", ".vue", ".json", ".mjs", ".cjs"}:
            continue
        count += len(regex.findall(read_text(path)))
    return count


def detect_host_stack(host: Path) -> list[dict[str, str]]:
    package = load_package_json(host)
    versions = package_versions(package)
    scripts = package.get("scripts", {}) if isinstance(package.get("scripts"), dict) else {}

    ui_libs = [
        name
        for name in (
            "element-plus",
            "ant-design-vue",
            "naive-ui",
            "vant",
            "vuetify",
            "@arco-design/web-vue",
            "tdesign-vue-next",
            "@opentiny/vue",
        )
        if name in versions
    ]

    build_tool = "unknown"
    if "vite" in versions or (host / "vite.config.ts").exists() or (host / "vite.config.js").exists():
        build_tool = "Vite"
    elif "@vue/cli-service" in versions or (host / "vue.config.js").exists():
        build_tool = "Vue CLI"
    elif "webpack" in versions or (host / "webpack.config.js").exists():
        build_tool = "Webpack"

    rows = [
        {"area": "revision", "value": git_revision(host), "evidence": "git rev-parse --short HEAD"},
        {"area": "build tool", "value": build_tool, "evidence": "package.json/config files"},
        {"area": "lockfile", "value": detect_lockfile(host), "evidence": "repository root"},
        {"area": "node", "value": detect_node(host, package), "evidence": "package engines/.nvmrc"},
        {"area": "vue", "value": versions.get("vue", "not declared"), "evidence": "package.json"},
        {"area": "router", "value": versions.get("vue-router", signal_value(host, "router")), "evidence": "package.json/source scan"},
        {"area": "state", "value": detect_state(versions, host), "evidence": "package.json/source scan"},
        {"area": "api client", "value": "axios" if "axios" in versions or search_host_signal(host, HOST_SIGNAL_PATTERNS["axios"]) else "not detected", "evidence": "package.json/source scan"},
        {"area": "jquery", "value": versions.get("jquery", signal_value(host, "jquery")), "evidence": "package.json/source scan"},
        {"area": "ui library", "value": ", ".join(ui_libs) if ui_libs else "not detected", "evidence": "package.json"},
        {"area": "i18n", "value": versions.get("vue-i18n", signal_value(host, "i18n")), "evidence": "package.json/source scan"},
        {"area": "proxy", "value": signal_value(host, "proxy"), "evidence": "vite/vue/webpack config scan"},
        {"area": "mpa", "value": detect_mpa(host), "evidence": "scripts/getpage.js and src/pages/*/*.ts scan"},
        {"area": "permission/auth", "value": signal_value(host, "permission"), "evidence": "source scan"},
        {"area": "scripts", "value": ", ".join(sorted(scripts)) if scripts else "not declared", "evidence": "package.json"},
    ]
    return rows


def detect_mpa(host: Path) -> str:
    markers = []
    if (host / "scripts" / "getpage.js").exists():
        markers.append("scripts/getpage.js")
    page_entries = list((host / "src" / "pages").glob("*/*.ts")) if (host / "src" / "pages").exists() else []
    if page_entries:
        markers.append(f"src/pages/*/*.ts ({len(page_entries)})")
    signal_count = search_host_signal(host, HOST_SIGNAL_PATTERNS["mpa"])
    if signal_count:
        markers.append(f"source signals ({signal_count})")
    return ", ".join(markers) if markers else "not detected"


def detect_state(versions: dict[str, str], host: Path) -> str:
    if "pinia" in versions:
        return f"pinia {versions['pinia']}"
    if "vuex" in versions:
        return f"vuex {versions['vuex']}"
    if search_host_signal(host, HOST_SIGNAL_PATTERNS["pinia"]):
        return "pinia signal"
    if search_host_signal(host, HOST_SIGNAL_PATTERNS["vuex"]):
        return "vuex signal"
    return "not detected"


def signal_value(root: Path, signal: str) -> str:
    count = search_host_signal(root, HOST_SIGNAL_PATTERNS[signal])
    return f"detected ({count} matches)" if count else "not detected"


def normalize_key(rel: Path) -> str:
    parts = [p.lower() for p in rel.with_suffix("").parts]
    ignored = {
        "src",
        "main",
        "webapp",
        "web-inf",
        "templates",
        "template",
        "views",
        "view",
        "pages",
        "page",
        "components",
        "component",
        "modules",
        "module",
        "router",
        "routes",
    }
    parts = [re.sub(r"[^a-z0-9]+", "-", p).strip("-") for p in parts if p not in ignored]
    parts = [p for p in parts if p and p not in {"index", "main", "app"}]
    return "/".join(parts[-2:]) if parts else rel.stem.lower()


def token_key(value: str) -> str:
    value = value.replace("\\", "/")
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    tokens = [token.lower() for token in re.split(r"[^A-Za-z0-9]+", value) if token]
    aliases = {"management": "manage", "bench": "bench", "work": "work", "phones": "phone"}
    normalized = [aliases.get(token, token) for token in tokens]
    return "-".join(normalized)


def last_token_set(value: str) -> set[str]:
    key = token_key(value)
    aliases = {
        "management": "manage",
        "managed": "manage",
        "manager": "manage",
        "bench": "bench",
        "workbench": "work bench",
        "taskmanage": "task manage",
        "taskmanagement": "task manage",
        "projectprogress": "project progress",
        "phones": "phone",
    }
    expanded = []
    for token in key.split("-"):
        expanded.extend(aliases.get(token, token).split())
    return {token for token in expanded if token and token not in {"src", "main", "webapp", "views", "pages", "page", "components", "component", "index", "html", "htm", "vue", "js", "ts"}}


def page_kind(root: Path, rel: Path, source: bool) -> str:
    parts = [part.lower() for part in rel.parts]
    if source:
        return "source-page"
    rel_text = str(rel).replace("\\", "/")
    if rel.suffix.lower() in {".html", ".htm"} and re.match(r"src/pages/[^/]+/[^/]+\.html?$", rel_text):
        return "host-html-entry"
    if rel.suffix.lower() in {".html", ".htm"} and rel.name.lower() in {"index.html", "index.htm"}:
        return "host-shell"
    if rel.suffix.lower() in {".html", ".htm"}:
        return "host-html-fragment"
    if "pages" in parts:
        if rel.suffix.lower() == ".vue":
            return "host-page-component"
        if rel.suffix.lower() in {".ts", ".js", ".tsx", ".jsx"}:
            return "host-entry-script"
    if "views" in parts:
        return "host-view-candidate"
    return "host-component-candidate"


def is_host_landing_candidate(row: dict[str, str]) -> bool:
    return row.get("kind") in {"host-html-entry", "host-page-component", "host-entry-script", "host-view-candidate"}


def is_shell_candidate(row: dict[str, str]) -> bool:
    return row.get("kind") == "host-shell" or row.get("key") in {"index", "main", "app"} or row.get("path", "").lower() in {"index.html", "public/index.html"}


def url_guess(rel: Path) -> str:
    rel_no_ext = rel.with_suffix("")
    parts = [p for p in rel_no_ext.parts if p.lower() not in {"webapp", "templates", "views", "pages"}]
    if parts and parts[-1].lower() in {"index", "main"}:
        parts = parts[:-1]
    return "/" + "/".join(parts).replace("\\", "/")


def signal_summary(text: str, signals: dict[str, str]) -> dict[str, int]:
    return {name: len(re.findall(pattern, text, re.I)) for name, pattern in signals.items()}


def discover_pages(root: Path, exts: set[str], source: bool) -> list[dict[str, str]]:
    rows = []
    for path in iter_files(root):
        if path.suffix.lower() not in exts:
            continue
        rel = path.relative_to(root)
        kind = page_kind(root, rel, source)
        if not source and kind == "host-html-fragment":
            continue
        text = read_text(path)
        signals = signal_summary(text, SOURCE_SIGNALS if source else HOST_SIGNAL_PATTERNS)
        rows.append(
            {
                "key": normalize_key(rel),
                "tokens": " ".join(sorted(last_token_set(str(rel)))),
                "kind": kind,
                "path": str(rel).replace("\\", "/"),
                "url_guess": url_guess(rel),
                "signals": ", ".join(f"{k}:{v}" for k, v in signals.items() if v) or "none",
                "line_count": str(text.count("\n") + 1 if text else 0),
            }
        )
    return sorted(rows, key=lambda row: row["path"])


def score_page_match(source: dict[str, str], host: dict[str, str]) -> tuple[int, list[str]]:
    score = 0
    basis = []
    source_key = token_key(source["key"])
    host_key = token_key(host["key"])
    source_tokens = set(source.get("tokens", "").split())
    host_tokens = set(host.get("tokens", "").split())
    if source_key and source_key == host_key:
        score += 60
        basis.append("normalized-key")
    overlap = source_tokens & host_tokens
    if overlap:
        score += min(30, len(overlap) * 10)
        basis.append("token-overlap:" + "+".join(sorted(overlap)))
        if len(overlap) >= 2:
            score += 30
            basis.append("multi-token-overlap")
    if source_key and host_key and (source_key in host_key or host_key in source_key):
        score += 15
        basis.append("substring-key")
    if is_shell_candidate(host):
        score -= 40
        basis.append("host-shell-candidate")
    if not is_host_landing_candidate(host):
        score -= 25
        basis.append("host-component-candidate")
    return score, basis


def compare_pages(source_pages: list[dict[str, str]], host_pages: list[dict[str, str]]) -> list[dict[str, str]]:
    matched_host_paths = set()
    rows = []
    for source in source_pages:
        scored = []
        for host in host_pages:
            score, basis = score_page_match(source, host)
            if score > 0:
                scored.append((score, basis, host))
        scored.sort(key=lambda item: item[0], reverse=True)
        if scored and scored[0][0] >= 45:
            score, basis, host = scored[0]
            matched_host_paths.add(host["path"])
            status = "partial-overlap"
            confidence = "medium" if score >= 60 else "low"
            next_action = "human-correct mapping; trace URL/API/permission/behavior before marking migrated"
        else:
            host = None
            score = 0
            basis = []
            status = "unmigrated"
            confidence = "medium"
            next_action = "identify host landing point"
        rows.append(
            {
                "status": status,
                "match_basis": ", ".join(basis) if basis else "none",
                "candidate_score": str(score),
                "needs_human_correction": "yes",
                "source_key": source["key"],
                "source_path": source["path"],
                "source_url": source["url_guess"],
                "host_path": host["path"] if host else "",
                "host_entry": host["url_guess"] if host else "",
                "confidence": confidence,
                "next_action": next_action,
            }
        )

    for host in host_pages:
        if host["path"] in matched_host_paths:
            continue
        if not is_host_landing_candidate(host):
            if is_shell_candidate(host):
                next_action = "ignore for business-page matching unless router/menu evidence points here"
                status = "host-shell"
            else:
                next_action = "ignore unless referenced by a matched host page closure"
                status = "host-component"
        else:
            next_action = "confirm whether this replaces or is unrelated to source"
            status = "host-page-only"
        rows.append(
            {
                "status": status,
                "match_basis": "none",
                "candidate_score": "0",
                "needs_human_correction": "yes" if status == "host-page-only" else "no",
                "source_key": host["key"],
                "source_path": "",
                "source_url": "",
                "host_path": host["path"],
                "host_entry": host["url_guess"],
                "confidence": "medium",
                "next_action": next_action,
            }
        )
    return rows


def extract_java_routes(source: Path) -> list[dict[str, str]]:
    rows = []
    route_re = re.compile(r"@(RequestMapping|GetMapping|PostMapping)\s*(?:\(\s*)?(?:value\s*=\s*)?[{\"']([^}\"']+)[}\"']")
    return_re = re.compile(r"return\s+[\"']([^\"']+)[\"']")
    for path in iter_files(source):
        if path.suffix.lower() != ".java":
            continue
        text = read_text(path)
        class_match = re.search(r"@RequestMapping\s*(?:\(\s*)?(?:value\s*=\s*)?[{\"']([^}\"']+)[}\"']", text)
        class_route = class_match.group(1) if class_match else ""
        class_file = str(path.relative_to(source)).replace("\\", "/")
        matches = list(route_re.finditer(text))
        for index, match in enumerate(matches):
            if class_match and match.start() == class_match.start():
                continue
            route = match.group(2)
            next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[match.start():next_start]
            returns = return_re.findall(block)
            full_route = "/".join(part.strip("/") for part in (class_route, route) if part).replace("//", "/")
            rows.append(
                {
                    "source_url": "/" + full_route.strip("/"),
                    "source_route_evidence": f"{class_file}:{text[:match.start()].count(chr(10)) + 1}",
                    "source_template": returns[0] if returns else "",
                    "server_controller": class_file,
                }
            )
    return rows


def extract_angular_routes(source: Path) -> list[dict[str, str]]:
    rows = []
    component_templates = extract_angular_component_templates(source)
    when_re = re.compile(
        r"\.\s*when\(\s*[\"']([^\"']+)[\"']\s*,\s*\{(?P<body>.*?)\}\s*\)",
        re.I | re.S,
    )
    state_re = re.compile(
        r"\.\s*state\(\s*[\"']([^\"']+)[\"']\s*,\s*\{(?P<body>.*?)\}\s*\)",
        re.I | re.S,
    )
    url_re = re.compile(r"\burl\s*:\s*[\"']([^\"']+)[\"']", re.I)
    template_re = re.compile(r"\btemplateUrl\s*:\s*[\"']([^\"']+)[\"']", re.I)
    inline_template_re = re.compile(r"\btemplate\s*:\s*[\"']([^\"']+)[\"']", re.I | re.S)
    for path in iter_files(source):
        if path.suffix.lower() not in {".js", ".ts"}:
            continue
        text = read_text(path)
        source_file = str(path.relative_to(source)).replace("\\", "/")
        for match in when_re.finditer(text):
            template = template_re.search(match.group("body"))
            inline_template = inline_template_re.search(match.group("body"))
            template_value = template.group(1) if template else template_from_inline(inline_template.group(1), component_templates) if inline_template else ""
            rows.append(
                {
                    "source_url": "#!" + match.group(1),
                    "source_route_evidence": f"{source_file}:{text[:match.start()].count(chr(10)) + 1}",
                    "source_template": template_value,
                    "server_controller": source_file,
                }
            )
        for match in state_re.finditer(text):
            body = match.group("body")
            url = url_re.search(body)
            template = template_re.search(body)
            inline_template = inline_template_re.search(body)
            if url:
                template_value = template.group(1) if template else template_from_inline(inline_template.group(1), component_templates) if inline_template else ""
                rows.append(
                    {
                        "source_url": "#!" + url.group(1),
                        "source_route_evidence": f"{source_file}:{text[:match.start()].count(chr(10)) + 1}",
                        "source_template": template_value,
                        "server_controller": source_file,
                    }
                )
    return rows


def component_to_tag(name: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name).lower()


def extract_angular_component_templates(source: Path) -> dict[str, str]:
    templates = {}
    component_re = re.compile(r"\.\s*component\(\s*[\"']([^\"']+)[\"']", re.I)
    template_re = re.compile(r"\btemplateUrl\s*:\s*[\"']([^\"']+)[\"']", re.I)
    for path in iter_files(source):
        if path.suffix.lower() not in {".js", ".ts"}:
            continue
        text = read_text(path)
        matches = list(component_re.finditer(text))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[match.start():end]
            template = template_re.search(block)
            if template:
                templates[component_to_tag(match.group(1))] = template.group(1)
    return templates


def template_from_inline(template: str, component_templates: dict[str, str]) -> str:
    tag_match = re.search(r"<\s*([a-z][a-z0-9-]*)\b", template, re.I)
    if not tag_match:
        return ""
    return component_templates.get(tag_match.group(1).lower(), "")


def discover_host_entries(host: Path) -> list[dict[str, str]]:
    entries = []
    for path in iter_files(host):
        rel = path.relative_to(host)
        rel_text = str(rel).replace("\\", "/")
        if rel_text == "scripts/getpage.js":
            entries.append({
                "host_entry_html": "",
                "host_entry_ts": rel_text,
                "host_menu_or_route": "MPA getPages helper",
                "host_entry_evidence": rel_text,
            })
        if re.match(r"src/pages/[^/]+/[^/]+\.(ts|js|tsx|jsx)$", rel_text):
            entries.append({
                "host_entry_html": "",
                "host_entry_ts": rel_text,
                "host_menu_or_route": "src/pages MPA entry",
                "host_entry_evidence": rel_text,
            })
        if re.match(r"src/pages/[^/]+/[^/]+\.html?$", rel_text):
            entries.append({
                "host_entry_html": rel_text,
                "host_entry_ts": "",
                "host_menu_or_route": "HTML entry candidate",
                "host_entry_evidence": rel_text,
            })
    return entries


def build_url_entry_mapping(source: Path, host: Path, source_pages: list[dict[str, str]], host_pages: list[dict[str, str]]) -> list[dict[str, str]]:
    java_routes = extract_java_routes(source)
    angular_routes = extract_angular_routes(source)
    source_routes = java_routes + angular_routes
    host_entries = discover_host_entries(host)
    rows = []

    for page in source_pages:
        page_tokens = last_token_set(page["path"])
        route = best_route_for_page(page, page_tokens, source_routes)
        entry = best_host_entry_for_page(page, page_tokens, host_entries)
        rows.append({
            "source_url": route.get("source_url", page["url_guess"]),
            "source_route_evidence": route.get("source_route_evidence", "url_guess only"),
            "source_template": route.get("source_template", page["path"]),
            "server_controller": route.get("server_controller", ""),
            "host_entry_html": entry.get("host_entry_html", ""),
            "host_entry_ts": entry.get("host_entry_ts", ""),
            "host_menu_or_route": entry.get("host_menu_or_route", ""),
            "mapping_status": "candidate" if route or entry else "unresolved",
            "confidence": "medium" if route and entry else "low",
            "unresolved": "" if route and entry else "requires Java/menu/MPA evidence",
        })

    for entry in host_entries:
        if any(row["host_entry_ts"] == entry["host_entry_ts"] and row["host_entry_html"] == entry["host_entry_html"] for row in rows):
            continue
        rows.append({
            "source_url": "",
            "source_route_evidence": "",
            "source_template": "",
            "server_controller": "",
            "host_entry_html": entry.get("host_entry_html", ""),
            "host_entry_ts": entry.get("host_entry_ts", ""),
            "host_menu_or_route": entry.get("host_menu_or_route", ""),
            "mapping_status": "host-page-only-candidate",
            "confidence": "low",
            "unresolved": "confirm source counterpart",
        })
    return rows


def best_route_for_page(page: dict[str, str], page_tokens: set[str], source_routes: list[dict[str, str]]) -> dict[str, str]:
    scored = []
    page_path = page["path"].lower()
    for route in source_routes:
        route_text = route["source_url"] + "/" + route["source_template"]
        route_tokens = last_token_set(route_text)
        overlap = page_tokens & route_tokens
        score = len(overlap) * 10
        template = route.get("source_template", "").lower()
        if template and (page_path.endswith(template) or template in page_path):
            score += 100
        if page.get("source_url") and route.get("source_url") == page.get("source_url"):
            score += 80
        if score:
            scored.append((score, route))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored else {}


def best_host_entry_for_page(page: dict[str, str], page_tokens: set[str], host_entries: list[dict[str, str]]) -> dict[str, str]:
    scored = []
    page_path = page["path"].lower()
    for entry in host_entries:
        entry_text = entry["host_entry_html"] + "/" + entry["host_entry_ts"]
        entry_tokens = last_token_set(entry_text)
        overlap = page_tokens & entry_tokens
        score = len(overlap) * 10
        if entry_text and any(piece and piece in entry_text.lower() for piece in page_path.split("/")):
            score += 25
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored else {}


def coupling_counts(root: Path, patterns: dict[str, str]) -> list[dict[str, str]]:
    totals = Counter()
    files = Counter()
    for path in iter_files(root):
        if path.suffix.lower() not in {".js", ".ts", ".vue", ".html", ".htm", ".jsp", ".jspx", ".ftl", ".vm"}:
            continue
        text = read_text(path)
        for name, pattern in patterns.items():
            hits = len(re.findall(pattern, text, re.I))
            if hits:
                totals[name] += hits
                files[name] += 1
    return [
        {"signal": name, "matches": str(totals[name]), "files": str(files[name])}
        for name in sorted(totals)
    ]


def source_shellish(row: dict[str, str]) -> bool:
    source_path = row.get("source_path", "").lower()
    source_key = row.get("source_key", "").lower()
    return source_key in {"index", "main", "app"} or source_path in {"index.html", "index.htm"} or row.get("source_url") == "/"


def route_mapping_strength(row: dict[str, str], url_mapping: list[dict[str, str]]) -> tuple[int, str]:
    source_path = row.get("source_path", "")
    source_key = row.get("source_key", "")
    best = 0
    notes = []
    for mapping in url_mapping:
        haystack = " ".join([
            mapping.get("source_template", ""),
            mapping.get("source_url", ""),
            mapping.get("host_entry_html", ""),
            mapping.get("host_entry_ts", ""),
        ]).lower()
        if source_path and source_path.lower() in haystack:
            best += 25
            notes.append("source-template")
        if source_key and set(last_token_set(source_key)) & set(last_token_set(haystack)):
            best += 15
            notes.append("token-route")
        if mapping.get("source_route_evidence") and mapping.get("source_route_evidence") != "url_guess only":
            best += 25
            notes.append("source-route")
        if mapping.get("host_entry_html") or mapping.get("host_entry_ts"):
            best += 20
            notes.append("host-entry")
    return best, "+".join(sorted(set(notes))) if notes else "path-order"


def recommended_units(comparison: list[dict[str, str]], url_mapping: list[dict[str, str]]) -> list[dict[str, str]]:
    candidates = [row for row in comparison if row["status"] in {"unmigrated", "partial-overlap"}]
    scored = []
    for index, row in enumerate(candidates):
        score = 10 if row["status"] == "unmigrated" else 0
        route_score, route_reason = route_mapping_strength(row, url_mapping)
        score += route_score
        if source_shellish(row):
            score -= 50
            route_reason = f"{route_reason}; shell/index downgraded"
        scored.append((score, index, route_reason, row))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {
            "priority": f"P{index + 1}",
            "unit": row["source_key"],
            "source_path": row["source_path"],
            "reason": f"page-level switchable candidate; {route_reason}; requires host landing and parity closure",
            "status": row["status"],
        }
        for index, (_score, _original_index, route_reason, row) in enumerate(scored[:10])
    ]


def table(headers: list[str], rows: Iterable[Iterable[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def dict_table(rows: list[dict[str, str]], headers: list[str]) -> str:
    return table(headers, ([row.get(header, "") for header in headers] for row in rows))


def build_markdown(args, data: dict) -> str:
    mode = args.mode
    lines = [
        f"# {args.project_name} Hosted AngularJS To Vue3 Migration {mode.title()}",
        "",
        "This artifact is an evidence baseline. Review source and host code before treating any row as implementation design.",
        "",
        "## Revisions",
        table(["repo", "path", "revision"], [
            ["source", str(data["source_repo"]), data["source_revision"]],
            ["host", str(data["host_repo"]), data["host_revision"]],
        ]),
        "",
        "## Repo Acquisition",
        "A failed clone may be a warning rather than a blocker when an existing git repo is present and its revision is readable.",
        dict_table(data["repo_acquisition"], ["repo_role", "repo_path", "acquisition_status", "acquisition_warning", "revision", "revision_source", "dirty_entries", "usable_for_stage", "notes"]),
        "",
        "## Git Hygiene",
        "Dependency/cache/build directory noise blocks commit readiness. `src/` clean is useful but does not prove the whole repo is clean.",
        dict_table(data["git_hygiene"], ["repo_role", "status_entries", "business_changes", "src_or_webapp_changes", "lockfile_changes", "dependency_noise", "stage_status", "notes"]),
        "",
        "## Host Stack",
        dict_table(data["host_stack"], ["area", "value", "evidence"]),
        "",
        "## Source Page Inventory",
        dict_table(data["source_pages"], ["key", "kind", "tokens", "path", "url_guess", "signals", "line_count"]),
        "",
        "## Host Page Inventory",
        dict_table(data["host_pages"], ["key", "kind", "tokens", "path", "url_guess", "signals", "line_count"]),
        "",
        "## A/B Page Comparison",
        "This table is a candidate map, not a gap truth table. `already-migrated` requires behavior evidence or human confirmation and is never inferred from filename matching alone.",
        dict_table(data["comparison"], ["status", "match_basis", "candidate_score", "needs_human_correction", "source_key", "source_path", "source_url", "host_path", "host_entry", "confidence", "next_action"]),
        "",
        "## URL / Entry Mapping",
        "File-derived URL guesses are low-confidence until backed by Java route, menu, or MPA entry evidence.",
        dict_table(data["url_entry_mapping"], ["source_url", "source_route_evidence", "source_template", "server_controller", "host_entry_html", "host_entry_ts", "host_menu_or_route", "mapping_status", "confidence", "unresolved"]),
        "",
        "## Coupling Counts",
        "Source counts exclude vendor/lib/locale/build artifacts.",
        dict_table(data["source_couplings"], ["signal", "matches", "files"]),
        "",
        "## Suggested First Migration Units",
        dict_table(data["recommended_units"], ["priority", "unit", "source_path", "status", "reason"]),
        "",
        "## Validation Gates",
        table(["gate", "check", "status"], GATE_ROWS),
        "",
        "## Completion Authority",
        "Do not announce a page migration complete from this domain artifact alone. Completion requires Delivery verified evidence, domain verify evidence, current host revision binding, and no blocking residuals.",
    ]

    if mode in {"design", "verify"}:
        unit = args.unit or "[required migration unit missing]"
        lines.extend([
            "",
            f"## {mode.title()} Unit",
            f"- unit: `{unit}`",
            "- scope: one independently switchable page or user behavior",
            "- rule: reuse host shell/auth/API/state/components; do not copy source layout",
            "",
            "## Page Closure Contract",
            table(["item", "evidence"], [
                ["source templates/fragments", "fill from source code"],
                ["source AngularJS/jQuery/server variables", "fill from source code"],
                ["source APIs and response codes", "fill from source code"],
                ["host landing files", "fill from host code"],
                ["reuse/change/create decisions", "fill after host review"],
                ["old URL -> new entry", "fill with route evidence"],
                ["rollback switch and condition", "fill before implementation"],
            ]),
            "",
            "## Design Ready Gate",
            "Script-generated header-only contracts are `not-ready: empty-contract`. Do not enter Delivery Frame until an agent fills these rows with evidence or marks unresolved edges with a non-blocking reason.",
            table(["gate", "minimum evidence", "status"], DESIGN_READY_ROWS),
        ])

    if mode == "design" and args.unit:
        lines.extend([
            "",
            "## Scoped FLOW/CHAIN Contracts",
            "These tables are intentionally scoped to the selected unit. Do not fill them with whole-repo placeholders.",
            "",
            "### Business Flow",
            table(FLOW_CONTRACT_HEADERS, []),
            "",
            "### Variable Reference Chain",
            table(VARIABLE_CHAIN_HEADERS, []),
        ])

    return "\n".join(lines) + "\n"


def write_csv(path: Path, headers: list[str], rows: Iterable[Iterable[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        writer.writerows(rows)


def write_dict_csv(path: Path, rows: list[dict[str, str]], headers: list[str]) -> None:
    write_csv(path, headers, ([row.get(header, "") for header in headers] for row in rows))


def write_html(path: Path, markdown_text: str) -> None:
    escaped = html.escape(markdown_text)
    body = escaped.replace("\n", "<br>\n")
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Hosted AngularJS To Vue3 Migration</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 1180px; margin: 32px auto; padding: 0 24px; line-height: 1.55; color: #1f2937; }}
    h1, h2, h3 {{ color: #111827; }}
    code {{ background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>{body}</body>
</html>
""",
        encoding="utf-8",
    )


def collect_data(args) -> dict:
    source = Path(args.source_repo).resolve()
    host = Path(args.host_repo).resolve()
    if not source.exists():
        raise SystemExit(f"source repo not found: {source}")
    if not host.exists():
        raise SystemExit(f"host repo not found: {host}")

    source_pages = discover_pages(source, SOURCE_PAGE_EXTS, source=True)
    host_pages = discover_pages(host, HOST_PAGE_EXTS, source=False)
    comparison = compare_pages(source_pages, host_pages)
    url_entry_mapping = build_url_entry_mapping(source, host, source_pages, host_pages)
    return {
        "source_repo": source,
        "host_repo": host,
        "source_revision": git_revision(source),
        "host_revision": git_revision(host),
        "repo_acquisition": repo_acquisition_rows(args, source, host),
        "git_hygiene": git_hygiene_rows(source, host),
        "host_stack": detect_host_stack(host),
        "source_pages": source_pages,
        "host_pages": host_pages,
        "comparison": comparison,
        "url_entry_mapping": url_entry_mapping,
        "source_couplings": coupling_counts(source, SOURCE_SIGNALS),
        "recommended_units": recommended_units(comparison, url_entry_mapping),
    }


def write_outputs(args, data: dict) -> None:
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    markdown_text = build_markdown(args, data)

    if args.format in {"markdown", "all"}:
        path = out / f"{args.mode}-evidence.md"
        path.write_text(markdown_text, encoding="utf-8")
        print(f"Wrote {path}")

    if args.format in {"html", "all"}:
        path = out / f"{args.mode}-evidence.html"
        write_html(path, markdown_text)
        print(f"Wrote {path}")

    if args.format in {"csv", "all"}:
        csv_dir = out / "csv"
        write_dict_csv(csv_dir / "01-repo-acquisition.csv", data["repo_acquisition"], ["repo_role", "repo_path", "acquisition_status", "acquisition_warning", "revision", "revision_source", "dirty_entries", "usable_for_stage", "notes"])
        write_dict_csv(csv_dir / "02-git-hygiene.csv", data["git_hygiene"], ["repo_role", "status_entries", "business_changes", "src_or_webapp_changes", "lockfile_changes", "dependency_noise", "stage_status", "notes"])
        write_dict_csv(csv_dir / "03-host-stack.csv", data["host_stack"], ["area", "value", "evidence"])
        write_dict_csv(csv_dir / "04-source-pages.csv", data["source_pages"], ["key", "kind", "tokens", "path", "url_guess", "signals", "line_count"])
        write_dict_csv(csv_dir / "05-host-pages.csv", data["host_pages"], ["key", "kind", "tokens", "path", "url_guess", "signals", "line_count"])
        write_dict_csv(csv_dir / "06-page-comparison.csv", data["comparison"], ["status", "match_basis", "candidate_score", "needs_human_correction", "source_key", "source_path", "source_url", "host_path", "host_entry", "confidence", "next_action"])
        write_dict_csv(csv_dir / "07-url-entry-mapping.csv", data["url_entry_mapping"], ["source_url", "source_route_evidence", "source_template", "server_controller", "host_entry_html", "host_entry_ts", "host_menu_or_route", "mapping_status", "confidence", "unresolved"])
        write_dict_csv(csv_dir / "08-source-couplings.csv", data["source_couplings"], ["signal", "matches", "files"])
        write_dict_csv(csv_dir / "09-recommended-units.csv", data["recommended_units"], ["priority", "unit", "source_path", "status", "reason"])
        write_csv(csv_dir / "10-validation-gates.csv", ["gate", "check", "status"], GATE_ROWS)
        if args.mode == "design" and args.unit:
            write_csv(csv_dir / "11-design-ready-gate.csv", ["gate", "minimum evidence", "status"], DESIGN_READY_ROWS)
            write_csv(csv_dir / "12-business-flow-contract.csv", FLOW_CONTRACT_HEADERS, [])
            write_csv(csv_dir / "13-variable-chain-contract.csv", VARIABLE_CHAIN_HEADERS, [])
        print(f"Wrote CSV files under {csv_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate hosted AngularJS/JSP/jQuery to Vue3 migration evidence artifacts.")
    parser.add_argument("mode", nargs="?", choices=["assess", "design", "verify"], default="assess")
    parser.add_argument("--project-name", default="hosted-angularjs-to-vue3")
    parser.add_argument("--source-repo", required=True, help="Legacy source repo A")
    parser.add_argument("--host-repo", required=True, help="Existing Vue3 host repo B")
    parser.add_argument("--unit", help="Page, route, menu item, URL, or user behavior for design/verify")
    parser.add_argument("--output-dir", default="reports/angularjs-vue3-migration")
    parser.add_argument("--format", choices=["markdown", "html", "csv", "all"], default="all")
    parser.add_argument("--source-acquisition-warning", default="", help="Optional warning from source repo clone/fetch, recorded as evidence.")
    parser.add_argument("--host-acquisition-warning", default="", help="Optional warning from host repo clone/fetch, recorded as evidence.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.mode in {"design", "verify"} and not args.unit:
        print(f"Warning: {args.mode} mode is most useful with --unit.", flush=True)
    data = collect_data(args)
    write_outputs(args, data)


if __name__ == "__main__":
    main()

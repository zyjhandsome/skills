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
}

RESOURCE_CLOSURE_DIRS = {
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
CSS_I18N_EXTS = {".css", ".scss", ".less", ".sass", ".json", ".properties"}

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

MODE_LABELS = {
    "assess": "评估",
    "design": "设计",
    "verify": "复核",
}

FLOW_CONTRACT_HEADERS = [
    "FLOW-ID",
    "步骤",
    "入口/触发",
    "条件",
    "输入",
    "处理",
    "输出",
    "调用目标",
    "副作用",
    "业务含义",
    "证据",
    "置信度",
    "关联 CHAIN-ID",
]

VARIABLE_CHAIN_HEADERS = [
    "CHAIN-ID",
    "步骤",
    "VAR-ID",
    "规范化路径",
    "操作",
    "作用域/函数",
    "上游",
    "下游",
    "条件",
    "业务含义",
    "证据",
    "置信度",
    "Vue3 Host 落点",
]

GATE_ROWS = [
    ["behavior", "输入、校验、分支、成功/失败/空态/加载态", "待补证据"],
    ["permission", "菜单、路由、按钮隐藏/禁用、服务端拒绝", "待补证据"],
    ["url", "旧深链、query/hash、重定向、前进后退、外链", "待补证据"],
    ["source contract gates", "导航落地、比较/身份、共享弹窗、命中层、选择器-DOM、测试加载方式", "待补证据"],
    ["api", "端点、方法、参数/body、响应码、失败处理", "待补证据"],
    ["visual", "截图或测量证据；否则标 manual-only", "未测量前仅人工核对"],
    ["runtime", "宿主 Node、lockfile、既有 lint/build/test 命令", "待跑宿主命令"],
    ["git hygiene", "拟提交内容无依赖/缓存/构建目录；区分业务干净与整仓干净", "待复核 git status"],
    ["rollback", "开关、范围、责任人、恢复条件、数据兼容", "待设计"],
    ["completion authority", "领域复核只是证据；完成需要 Delivery verified + 领域复核 + 当前宿主修订", "待两边门禁"],
]

DESIGN_READY_ROWS = [
    ["page closure", "已识别源仓模板/片段/脚本/controller/service/API/资产", "not-ready: empty-contract"],
    ["display-contract matrix", "每个源区域有稳定 DISP 行，partial-overlap 已填 B 现状", "not-ready: empty-contract"],
    ["matrix region split", "矩阵已按源区域拆行；仅有整页 (skeleton) 行即不合格", "not-ready: skeleton-only-matrix"],
    ["host baseline gap", "宿主全局基线缺口表已填 A 侧依赖，host-missing/partial 项在本页有落地方式", "not-ready: empty-contract"],
    ["page-init", "run/controller init/定时器/首屏请求/默认筛选值已列出", "not-ready: empty-contract"],
    ["source i18n text", "源 zh/en 或模板文案原文已逐项记录，偏离有批准", "not-ready: empty-contract"],
    ["CSS closure", "页级 CSS、common/sprite/plugin/工具类依赖及 B 落地方式已列出", "not-ready: empty-contract"],
    ["core flows", "选定单元至少填实 1-2 条核心业务 FLOW", "not-ready: empty-contract"],
    ["variable/API chains", "已填实请求/响应/状态/DOM 链，或标未决并给出运行时检查", "not-ready: empty-contract"],
    ["source contract gates", "导航落地、比较/身份、共享弹窗模式、命中层、选择器-DOM、测试加载方式已处理", "not-ready: empty-contract"],
    ["entry-wiring", "切片完成判据写到入口挂载、API 调用、用户可达", "not-ready: empty-contract"],
    ["host decisions", "已给出宿主入口/路由/API/store/组件/i18n/样式的复用/改动/新建决策", "not-ready: empty-contract"],
    ["URL mapping", "旧源 URL 到新宿主入口有 Java/菜单/MPA/Vue Router 证据", "not-ready: empty-contract"],
    ["permission/API/rollback", "已起草权限/会话/API 对等与回退条件", "not-ready: empty-contract"],
]

MATRIX_CLOSED_STATUSES = {"verified", "manual-verified", "approved-deviation"}

HOST_BASELINE_HEADERS = [
    "基线类别",
    "A 假定的全局依赖",
    "A 证据",
    "B 是否提供",
    "B 落地方式",
    "状态",
]

DESIGN_SCOPE_HEADERS = [
    "source_key",
    "source_path",
    "status",
    "host_entry",
    "host_entry_evidence",
    "design_scope",
    "reason",
]

MAX_BATCH_UNITS = 5

BATCH_ADMISSION_HEADERS = [
    "unit",
    "matched_source_pages",
    "comparison_status",
    "design_scope",
    "admission",
    "reason",
]

BATCH_SHARED_SURFACE_HEADERS = [
    "surface",
    "host_path",
    "shared_by",
    "owner",
    "sequencing",
]

DISPLAY_CONTRACT_HEADERS = [
    "DISP-ID",
    "迁移单元",
    "源区域",
    "可见文案（源 i18n 原文）",
    "控件形态",
    "API + 字段/公式",
    "默认值/校验",
    "依赖 CSS（页级 + common + sprite）",
    "启动副作用",
    "B 现状",
    "证据",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def iter_files(root: Path, include_resource_closure_dirs: bool = False) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        parts = {part.lower() for part in rel.parts[:-1]}
        excluded = set(EXCLUDED_DIRS)
        if not include_resource_closure_dirs:
            excluded |= RESOURCE_CLOSURE_DIRS
        if parts & excluded:
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


def repo_acquisition_rows(args, source: Path, host: Path | None) -> list[dict[str, str]]:
    warnings = {
        "source": args.source_acquisition_warning or "",
        "host": args.host_acquisition_warning or "",
    }
    rows = []
    repos: list[tuple[str, Path | None]] = [("source", source), ("host", host)]
    for role, repo in repos:
        if repo is None:
            rows.append(
                {
                    "repo_role": role,
                    "repo_path": "",
                    "acquisition_status": "not-provided",
                    "acquisition_warning": warnings[role],
                    "revision": "source-only",
                    "revision_source": "unavailable",
                    "dirty_entries": "0",
                    "usable_for_stage": "no",
                    "notes": "source-only assess; host landing design cannot be completed",
                }
            )
            continue
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
                "notes": "复用已有仓库；克隆警告单独记录" if warnings[role] else "",
            }
        )
    return rows


def git_hygiene_rows(source: Path, host: Path | None) -> list[dict[str, str]]:
    rows = []
    repos: list[tuple[str, Path | None]] = [("source", source), ("host", host)]
    for role, repo in repos:
        if repo is None:
            rows.append(
                {
                    "repo_role": role,
                    "status_entries": "0",
                    "business_changes": "0",
                    "src_or_webapp_changes": "0",
                    "lockfile_changes": "0",
                    "dependency_noise": "0",
                    "stage_status": "source-only",
                    "notes": "host repo not provided; host hygiene unavailable",
                }
            )
            continue
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
                "notes": "src 干净不等于整仓干净；依赖/缓存/构建噪声不得进入提交" if paths else "工作区干净",
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


def actual_node_version() -> str:
    try:
        result = subprocess.run(["node", "-v"], check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return "not measured"


def detect_lint_on_save(root: Path) -> str:
    findings = []
    for filename in ("vue.config.js", "vue.config.cjs", "vue.config.mjs", "vue.config.ts"):
        text = read_text(root / filename)
        if not text:
            continue
        match = re.search(r"\blintOnSave\s*:\s*([^,\n}]+)", text)
        if match:
            findings.append(f"lintOnSave={match.group(1).strip()} ({filename})")

    # A Vite host has no lintOnSave, but an ESLint/checker plugin produces the same blocking overlay.
    for filename in ("vite.config.ts", "vite.config.js", "vite.config.mts", "vite.config.mjs", "vite.config.cjs"):
        text = read_text(root / filename)
        if not text:
            continue
        plugins = [
            name
            for name in ("vite-plugin-eslint", "vite-plugin-checker", "@vitejs/plugin-legacy", "unplugin-eslint")
            if name in text
        ]
        if plugins:
            findings.append(f"vite overlay plugins: {', '.join(plugins)} ({filename})")
        overlay = re.search(r"\boverlay\s*:\s*(true|false)", text)
        if overlay:
            findings.append(f"server.hmr overlay={overlay.group(1)} ({filename})")

    package = load_package_json(root)
    versions = package_versions(package)
    dep_plugins = [
        name
        for name in ("vite-plugin-eslint", "vite-plugin-checker", "eslint-webpack-plugin", "fork-ts-checker-webpack-plugin")
        if name in versions
    ]
    if dep_plugins:
        findings.append(f"declared overlay tooling: {', '.join(dep_plugins)} (package.json)")

    return "; ".join(findings) if findings else "not detected"


def detect_ts_strict(root: Path) -> str:
    path = root / "tsconfig.json"
    if not path.exists():
        return "tsconfig not found"
    try:
        config = json.loads(read_text(path))
    except json.JSONDecodeError:
        return "tsconfig unreadable"
    options = config.get("compilerOptions", {}) if isinstance(config, dict) else {}
    strict = options.get("strict", "not set") if isinstance(options, dict) else "not set"
    no_implicit_any = options.get("noImplicitAny", "not set") if isinstance(options, dict) else "not set"
    return f"strict={strict}; noImplicitAny={no_implicit_any}"


def detect_formatter_config(root: Path) -> str:
    found = [
        filename
        for filename in (
            ".prettierrc",
            ".prettierrc.json",
            ".prettierrc.js",
            ".prettierrc.cjs",
            "prettier.config.js",
            "prettier.config.cjs",
            ".editorconfig",
        )
        if (root / filename).exists()
    ]
    return ", ".join(found) if found else "not detected"


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
        {"area": "node actual", "value": actual_node_version(), "evidence": "node -v"},
        {"area": "vue", "value": versions.get("vue", "not declared"), "evidence": "package.json"},
        {"area": "router", "value": versions.get("vue-router", signal_value(host, "router")), "evidence": "package.json/source scan"},
        {"area": "state", "value": detect_state(versions, host), "evidence": "package.json/source scan"},
        {"area": "api client", "value": "axios" if "axios" in versions or search_host_signal(host, HOST_SIGNAL_PATTERNS["axios"]) else "not detected", "evidence": "package.json/source scan"},
        {"area": "jquery", "value": versions.get("jquery", signal_value(host, "jquery")), "evidence": "package.json/source scan"},
        {"area": "ui library", "value": ", ".join(ui_libs) if ui_libs else "not detected", "evidence": "package.json"},
        {"area": "i18n", "value": versions.get("vue-i18n", signal_value(host, "i18n")), "evidence": "package.json/source scan"},
        {"area": "proxy", "value": signal_value(host, "proxy"), "evidence": "vite/vue/webpack config scan"},
        {"area": "mpa", "value": detect_mpa(host), "evidence": "scripts/getpage.js and src/pages/*/*.ts scan"},
        {"area": "lintOnSave / dev overlay", "value": detect_lint_on_save(host), "evidence": "vue.config.*/vite.config.*/package.json scan"},
        {"area": "ts strict", "value": detect_ts_strict(host), "evidence": "tsconfig.json compilerOptions"},
        {"area": "formatter", "value": detect_formatter_config(host), "evidence": "Prettier/EditorConfig files"},
        {"area": "permission/auth", "value": signal_value(host, "permission"), "evidence": "source scan"},
        {"area": "scripts", "value": ", ".join(sorted(scripts)) if scripts else "not declared", "evidence": "package.json"},
    ]
    return rows


HOST_BASELINE_CATEGORIES = [
    ("css reset/base", ("normalize.css", "reset.css", "sanitize.css", "@unocss/reset"), r"(normalize|reset|sanitize)\.(css|scss|less)|font-size\s*:\s*0"),
    ("bootstrap/utility sheet", ("bootstrap", "bootstrap-vue", "tailwindcss", "@unocss/core"), r"\bbootstrap(\.min)?\.(css|js)\b|\bpull-(left|right)\b|\bcol-(xs|sm|md|lg)-\d"),
    ("sprite/icon assets", ("@element-plus/icons-vue", "@ant-design/icons-vue", "vite-plugin-svg-icons"), r"sprite|icon-?font|background-position\s*:|\.svg#"),
    ("jquery + plugins", ("jquery", "jquery-ui", "bootstrap-datepicker", "select2", "layer"), r"\$\(|jquery"),
    ("global js libs", ("moment", "dayjs", "lodash", "echarts", "chart.js", "tinymce", "@tinymce/tinymce-vue"), r"\b(moment|dayjs|lodash|echarts|tinymce)\b"),
    ("server-rendered globals", (), r"window\.[A-Za-z_$][\w$]*\s*="),
]


def host_baseline_gap_rows(host: Path | None) -> list[dict[str, str]]:
    """Emit the host baseline gap table skeleton. Detection covers B only; the A column stays human-filled."""
    rows = []
    if host is None:
        for category, _packages, _pattern in HOST_BASELINE_CATEGORIES:
            rows.append({
                "基线类别": category,
                "A 假定的全局依赖": "[从源模板填写]",
                "A 证据": "[file:line]",
                "B 是否提供": "[not provided] host repo 未提供",
                "B 落地方式": "[待宿主分析]",
                "状态": "unknown",
            })
        return rows

    versions = package_versions(load_package_json(host))
    for category, packages, pattern in HOST_BASELINE_CATEGORIES:
        declared = [name for name in packages if name in versions]
        signal_hits = search_host_signal(host, pattern) if pattern else 0
        if declared:
            provided = f"declared: {', '.join(declared)}"
            status = "host-provides"
        elif signal_hits:
            provided = f"source signals only ({signal_hits})"
            status = "host-partial"
        else:
            provided = "not detected"
            status = "host-missing"
        rows.append({
            "基线类别": category,
            "A 假定的全局依赖": "[从源模板填写]",
            "A 证据": "[file:line]",
            "B 是否提供": provided,
            "B 落地方式": "[待填：页级 scoped 落地或宿主 token]",
            "状态": status,
        })
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
            next_action = "人工校正映射；在标 already-migrated 前先追 URL/API/权限/行为"
        else:
            host = None
            score = 0
            basis = []
            status = "unmigrated"
            confidence = "medium"
            next_action = "识别宿主落点"
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
                next_action = "除非路由/菜单证据指向此处，否则不参与业务页匹配"
                status = "host-shell"
            else:
                next_action = "除非被已匹配页面闭包引用，否则忽略"
                status = "host-component"
        else:
            next_action = "确认是替换源页还是无关页面"
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


def resolve_import_path(root: Path, from_file: Path, import_value: str) -> str:
    if not import_value.startswith("."):
        return import_value
    candidate = (from_file.parent / import_value).resolve()
    suffixes = ["", ".vue", ".ts", ".js", ".tsx", ".jsx", "/index.vue", "/index.ts", "/index.js"]
    for suffix in suffixes:
        path = Path(str(candidate) + suffix)
        if path.exists() and root in path.parents:
            return str(path.relative_to(root)).replace("\\", "/")
    if root in candidate.parents:
        return str(candidate.relative_to(root)).replace("\\", "/")
    return import_value


def enclosing_object_literal(text: str, index: int) -> tuple[int, int]:
    """Return the [start, end) span of the object literal that directly contains index."""
    depth = 0
    start = -1
    for i in range(index, -1, -1):
        char = text[i]
        if char == "}":
            depth += 1
        elif char == "{":
            if depth == 0:
                start = i
                break
            depth -= 1
    if start < 0:
        return (-1, -1)
    depth = 0
    for i in range(start, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return (start, i + 1)
    return (start, len(text))


def own_level_text(object_text: str) -> str:
    """Strip nested objects/arrays so key lookups only see this object's own properties."""
    body = object_text[1:-1] if len(object_text) >= 2 else object_text
    out = []
    depth = 0
    for char in body:
        if char in "{[":
            depth += 1
            continue
        if char in "}]":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            out.append(char)
    return "".join(out)


def normalize_route_path(value: str) -> str:
    path = value.strip().lower()
    for prefix in ("#!", "#"):
        if path.startswith(prefix):
            path = path[len(prefix):]
    path = path.split("?")[0]
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def route_path_shape(value: str) -> tuple[int, int]:
    """Return (segment count, dynamic segment count) so /phones and /phones/:id cannot match."""
    path = normalize_route_path(value)
    segments = [segment for segment in path.split("/") if segment]
    dynamic = sum(1 for segment in segments if segment.startswith(":") or segment.startswith("*"))
    return (len(segments), dynamic)


def extract_vue_router_entries(host: Path) -> list[dict[str, str]]:
    entries = []
    route_path_re = re.compile(r"\bpath\s*:\s*[\"']([^\"']*)[\"']", re.I)
    component_ident_re = re.compile(r"\bcomponent\s*:\s*([A-Za-z_$][\w$]*)", re.I)
    component_import_re = re.compile(r"\bcomponent\s*:\s*\(?\s*\)\s*=>\s*import\(\s*[\"']([^\"']+)[\"']\s*\)", re.I | re.S)
    redirect_re = re.compile(r"\bredirect\s*:", re.I)
    import_re = re.compile(r"import\s+([A-Za-z_$][\w$]*)\s+from\s+[\"']([^\"']+)[\"']", re.I)

    for path in iter_files(host):
        rel = path.relative_to(host)
        rel_text = str(rel).replace("\\", "/")
        if path.suffix.lower() not in {".js", ".ts", ".mjs", ".cjs"}:
            continue
        text = read_text(path)
        if "vue-router" not in text and "createRouter" not in text and "routes" not in text:
            continue
        imports = {
            match.group(1): resolve_import_path(host, path, match.group(2))
            for match in import_re.finditer(text)
        }
        for match in route_path_re.finditer(text):
            start, end = enclosing_object_literal(text, match.start())
            if start < 0:
                continue
            own = own_level_text(text[start:end])
            if not route_path_re.search(own):
                continue
            route_path = match.group(1)
            component_path = ""
            dynamic = component_import_re.search(own)
            if dynamic:
                component_path = resolve_import_path(host, path, dynamic.group(1))
            else:
                ident = component_ident_re.search(own)
                if ident:
                    component_path = imports.get(ident.group(1), ident.group(1))
            if not component_path and redirect_re.search(own):
                # A redirect record is a hop, not a landing point. Never let it borrow the next route's component.
                continue
            entries.append({
                "host_entry_html": "",
                "host_entry_ts": component_path or rel_text,
                "host_route_path": route_path,
                "host_menu_or_route": f"Vue Router {route_path} ({rel_text}:{text[:match.start()].count(chr(10)) + 1})",
                "host_entry_evidence": rel_text,
            })
    return entries


def discover_host_entries(host: Path) -> list[dict[str, str]]:
    entries = []
    for path in iter_files(host):
        rel = path.relative_to(host)
        rel_text = str(rel).replace("\\", "/")
        if rel_text == "scripts/getpage.js":
            entries.append({
                "host_entry_html": "",
                "host_entry_ts": rel_text,
                "host_route_path": "",
                "host_menu_or_route": "MPA getPages helper",
                "host_entry_evidence": rel_text,
            })
        if re.match(r"src/pages/[^/]+/[^/]+\.(ts|js|tsx|jsx)$", rel_text):
            entries.append({
                "host_entry_html": "",
                "host_entry_ts": rel_text,
                "host_route_path": "",
                "host_menu_or_route": "src/pages MPA entry",
                "host_entry_evidence": rel_text,
            })
        if re.match(r"src/pages/[^/]+/[^/]+\.html?$", rel_text):
            entries.append({
                "host_entry_html": rel_text,
                "host_entry_ts": "",
                "host_route_path": "",
                "host_menu_or_route": "HTML entry candidate",
                "host_entry_evidence": rel_text,
            })
    seen = set()
    unique_entries = []
    for entry in entries + extract_vue_router_entries(host):
        key = (entry.get("host_entry_html", ""), entry.get("host_entry_ts", ""), entry.get("host_menu_or_route", ""))
        if key in seen:
            continue
        seen.add(key)
        unique_entries.append(entry)
    return unique_entries


def build_url_entry_mapping(source: Path, host: Path | None, source_pages: list[dict[str, str]], host_pages: list[dict[str, str]]) -> list[dict[str, str]]:
    java_routes = extract_java_routes(source)
    angular_routes = extract_angular_routes(source)
    source_routes = java_routes + angular_routes
    host_entries = discover_host_entries(host) if host else []
    rows = []

    for page in source_pages:
        page_tokens = last_token_set(page["path"])
        route = best_route_for_page(page, page_tokens, source_routes)
        entry = best_host_entry_for_page(
            page,
            page_tokens,
            host_entries,
            route.get("source_url", ""),
        )
        rows.append({
            "source_page_path": page["path"],
            "source_url": route.get("source_url", page["url_guess"]),
            "source_route_evidence": route.get("source_route_evidence", "url_guess only"),
            "source_template": route.get("source_template", page["path"]),
            "server_controller": route.get("server_controller", ""),
            "host_entry_html": entry.get("host_entry_html", ""),
            "host_entry_ts": entry.get("host_entry_ts", ""),
            "host_route_path": entry.get("host_route_path", ""),
            "host_menu_or_route": entry.get("host_menu_or_route", ""),
            "mapping_status": "candidate" if route or entry else "unresolved",
            "confidence": "medium" if route and entry else "low",
            "unresolved": "" if route and entry else "需要 Java/菜单/MPA/Vue Router 证据",
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
            "host_route_path": entry.get("host_route_path", ""),
            "host_menu_or_route": entry.get("host_menu_or_route", ""),
            "mapping_status": "host-page-only-candidate",
            "confidence": "low",
            "unresolved": "确认源仓对应页",
        })
    return rows


def reconcile_comparison_entries(comparison: list[dict[str, str]], url_entry_mapping: list[dict[str, str]]) -> None:
    """Write the proven router/MPA entry back into the comparison table instead of leaving a filename guess."""
    by_source_path = {
        row.get("source_page_path", ""): row
        for row in url_entry_mapping
        if row.get("source_page_path")
    }
    for row in comparison:
        mapping = by_source_path.get(row.get("source_path", ""))
        if not mapping:
            continue
        route = mapping.get("host_menu_or_route", "")
        entry = mapping.get("host_entry_ts", "") or mapping.get("host_entry_html", "")
        if route:
            row["host_entry"] = route
            row["host_entry_evidence"] = "route/menu/MPA evidence"
        elif entry:
            row["host_entry"] = entry
            row["host_entry_evidence"] = "host entry file evidence"
        else:
            row["host_entry_evidence"] = "filename guess only"
            row["needs_human_correction"] = "yes"
        if row.get("status") == "partial-overlap" and not route:
            row["next_action"] = "入口证据不足：仅文件名相似，不得据此给 design-scope=repair"


def repair_scope_gate(comparison: list[dict[str, str]]) -> list[dict[str, str]]:
    """Decide design-scope per source page so an unmigrated page cannot inherit a nearby Vue file's entry."""
    rows = []
    for row in comparison:
        if not row.get("source_path"):
            continue
        status = row.get("status", "")
        has_route_evidence = row.get("host_entry_evidence", "") == "route/menu/MPA evidence"
        if status == "partial-overlap" and has_route_evidence:
            scope = "repair"
            reason = "partial-overlap 且宿主入口有 route/menu/MPA 证据"
        elif status == "partial-overlap":
            scope = "new-landing"
            reason = "partial-overlap 但入口只有文件名猜测，不足以判定 B 已有入口"
        else:
            scope = "new-landing"
            reason = f"对照状态为 {status or 'unknown'}，不满足 repair 准入"
        rows.append({
            "source_key": row.get("source_key", ""),
            "source_path": row.get("source_path", ""),
            "status": status,
            "host_entry": row.get("host_entry", ""),
            "host_entry_evidence": row.get("host_entry_evidence", ""),
            "design_scope": scope,
            "reason": reason,
        })
    return rows


def batch_admission_rows(
    units: list[str],
    comparison: list[dict[str, str]],
    design_scope_gate: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Decide whether the requested units can run as one batch, before any approval is asked."""
    if not units:
        return []
    scope_by_path = {row["source_path"]: row for row in design_scope_gate}
    resolved = []
    for unit in units:
        matches = [row for row in comparison if row.get("source_path") and unit_matches_row(unit, row)]
        scopes = sorted({scope_by_path[row["source_path"]]["design_scope"] for row in matches if row["source_path"] in scope_by_path})
        resolved.append((unit, matches, scopes))

    all_scopes = sorted({scope for _unit, _matches, scopes in resolved for scope in scopes})
    mixed_scope = len(all_scopes) > 1

    rows = []
    for unit, matches, scopes in resolved:
        status = ", ".join(sorted({row.get("status", "") for row in matches})) or "none"
        scope = ", ".join(scopes) or "unknown"
        if not matches:
            admission, reason = "rejected", "该 unit 在 A/B 对照表里没有源页行，先校正 unit 名或补 assess"
        elif len(matches) > 1:
            admission, reason = "needs-human", f"unit 匹配到 {len(matches)} 个源页，范围不唯一，先收紧 unit 名"
        elif mixed_scope:
            admission, reason = "rejected", f"批次内 design-scope 不一致（{', '.join(all_scopes)}），按 scope 拆成两个批次"
        else:
            admission, reason = "admitted", f"唯一源页、design-scope={scope}，可与本批其他 unit 同批"
        rows.append({
            "unit": unit,
            "matched_source_pages": ", ".join(row.get("source_path", "") for row in matches) or "none",
            "comparison_status": status,
            "design_scope": scope,
            "admission": admission,
            "reason": reason,
        })
    return rows


HOST_SHARED_SURFACES = [
    ("router registration", r"^src/router/|(^|/)routes?\.(ts|js)$"),
    ("menu / navigation", r"(^|/)(menu|nav|sidebar|navigation)[^/]*\.(ts|js|json|vue)$"),
    ("shared i18n catalog", r"(^|/)(locale|locales|i18n|lang)/"),
    ("global stylesheet", r"(^|/)(common|global|base|reset|variables|theme)[^/]*\.(css|scss|less)$"),
    ("global store", r"^src/(store|stores)/"),
]


def batch_shared_surface_rows(
    host: Path | None,
    admission: list[dict[str, str]],
    comparison: list[dict[str, str]],
) -> list[dict[str, str]]:
    """List host surfaces more than one batch unit will touch, so Plan can assign a single owner."""
    admitted = [row["unit"] for row in admission if row["admission"] in {"admitted", "needs-human"}]
    if len(admitted) < 2:
        return []

    rows = []
    if host is not None:
        for surface, pattern in HOST_SHARED_SURFACES:
            regex = re.compile(pattern, re.I)
            for path in iter_files(host, include_resource_closure_dirs=True):
                rel = str(path.relative_to(host)).replace("\\", "/")
                if not regex.search(rel):
                    continue
                rows.append({
                    "surface": surface,
                    "host_path": rel,
                    "shared_by": "批次默认全体",
                    "owner": "[未分配：Plan 必须指定唯一任务组]",
                    "sequencing": "作为前置任务组先落地，其余 unit 只读依赖",
                })

    # Real overlap: two admitted units resolving to the same host page or entry.
    by_host: dict[str, list[str]] = {}
    for unit in admitted:
        for row in comparison:
            if not unit_matches_row(unit, row):
                continue
            key = row.get("host_path") or row.get("host_entry")
            if key:
                by_host.setdefault(key, [])
                if unit not in by_host[key]:
                    by_host[key].append(unit)
    for key, owners in sorted(by_host.items()):
        if len(owners) < 2:
            continue
        rows.append({
            "surface": "同一宿主落点",
            "host_path": key,
            "shared_by": ", ".join(owners),
            "owner": "[未分配：同落点的 unit 不得并行实施]",
            "sequencing": "串行，或合并成一个 unit",
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


def best_host_entry_for_page(
    page: dict[str, str],
    page_tokens: set[str],
    host_entries: list[dict[str, str]],
    source_route_path: str = "",
) -> dict[str, str]:
    scored = []
    page_path = page["path"].lower()
    source_shape = route_path_shape(source_route_path) if source_route_path else None
    for entry in host_entries:
        entry_text = entry["host_entry_html"] + "/" + entry["host_entry_ts"] + "/" + entry.get("host_menu_or_route", "")
        entry_tokens = last_token_set(entry_text)
        overlap = page_tokens & entry_tokens
        score = len(overlap) * 10
        if entry_text and any(piece and piece in entry_text.lower() for piece in page_path.split("/")):
            score += 25
        host_route = entry.get("host_route_path", "")
        if source_shape and host_route:
            # Route-path alignment outranks filename tokens: /phones and /phones/:phoneId are different pages.
            if normalize_route_path(source_route_path) == normalize_route_path(host_route):
                score += 120
            elif route_path_shape(host_route)[1] != source_shape[1]:
                score -= 60
            elif route_path_shape(host_route)[0] != source_shape[0]:
                score -= 20
        if score > 0:
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


def closure_resource_rows(root: Path) -> list[dict[str, str]]:
    rows = []
    for path in iter_files(root, include_resource_closure_dirs=True):
        if path.suffix.lower() not in CSS_I18N_EXTS:
            continue
        rel = path.relative_to(root)
        rel_text = str(rel).replace("\\", "/")
        parts = {part.lower() for part in rel.parts[:-1]}
        if not (parts & RESOURCE_CLOSURE_DIRS):
            continue
        kind = "i18n" if path.suffix.lower() in {".json", ".properties"} else "css"
        rows.append(
            {
                "resource_type": kind,
                "path": rel_text,
                "closure_status": "scan-required",
                "notes": "not a page candidate; include when a selected unit references this CSS/i18n resource",
            }
        )
    return rows


def slugify(value: str) -> str:
    slug = token_key(value)
    return slug or "unit"


def unit_matches_row(unit: str, row: dict[str, str]) -> bool:
    if not unit:
        return False
    unit_tokens = set(last_token_set(unit))
    row_text = " ".join(
        [
            row.get("source_key", ""),
            row.get("source_path", ""),
            row.get("source_url", ""),
            row.get("host_path", ""),
            row.get("host_entry", ""),
        ]
    )
    if unit.lower() in row_text.lower():
        return True
    row_tokens = set(last_token_set(row_text))
    if len(unit_tokens) > 1:
        return unit_tokens <= row_tokens
    return bool(unit_tokens & row_tokens)


def matching_units(units: list[str], row: dict[str, str]) -> list[str]:
    return [unit for unit in units if unit_matches_row(unit, row)]


def display_contract_rows(comparison: list[dict[str, str]], units: list[str] | None = None) -> list[dict[str, str]]:
    selected = units or []
    rows = []
    for row in comparison:
        if row.get("status") != "partial-overlap":
            continue
        owners = matching_units(selected, row) if selected else []
        if selected and not owners:
            continue
        unit_slug = slugify(row.get("source_key", "") or (owners[0] if owners else "unit"))
        rows.append(
            {
                "DISP-ID": f"DISP-{unit_slug}-region-1 (skeleton)",
                "迁移单元": "|".join(owners) if owners else "[未选定]",
                "源区域": f"{row.get('source_key', '')}（整页骨架行，必须按源区域拆分后才算合同）",
                "可见文案（源 i18n 原文）": "从源码填写",
                "控件形态": "从源码填写",
                "API + 字段/公式": "从源码填写",
                "默认值/校验": "从源码填写",
                "依赖 CSS（页级 + common + sprite）": "从源码填写",
                "启动副作用": "从源码填写",
                "B 现状": "wired-unverified",
                "证据": f"{row.get('source_path', '')} -> {row.get('host_path', '')}",
            }
        )
    return rows


def verify_one_unit(unit: str, comparison: list[dict[str, str]]) -> dict[str, str]:
    matches = [row for row in comparison if unit_matches_row(unit, row)]
    if not matches:
        return {"unit": unit, "status": "fail", "reason": "selected unit has no source/host comparison row"}
    if any(row.get("status") == "unmigrated" for row in matches):
        return {"unit": unit, "status": "fail", "reason": "selected unit is unmigrated"}
    matrix_rows = display_contract_rows(comparison, [unit])
    if not matrix_rows:
        return {"unit": unit, "status": "fail", "reason": "selected unit has no display-contract matrix rows"}
    if any("(skeleton)" in row["DISP-ID"] for row in matrix_rows):
        return {
            "unit": unit,
            "status": "fail",
            "reason": "display-contract matrix is still a whole-page skeleton row; split it by source region first",
        }
    if any(row["B 现状"] not in MATRIX_CLOSED_STATUSES for row in matrix_rows):
        return {"unit": unit, "status": "fail", "reason": "display-contract matrix is not verified"}
    return {
        "unit": unit,
        "status": "pass",
        "reason": "display-contract rows are verified, manual-verified, or approved-deviation",
    }


def verification_unit_results(args, data: dict) -> list[dict[str, str]]:
    if args.mode != "verify":
        return []
    return [verify_one_unit(unit, data["comparison"]) for unit in args.units]


def verification_result(args, data: dict) -> dict[str, str]:
    if args.mode != "verify":
        return {"status": "not-applicable", "reason": "only emitted in verify mode"}
    if not args.units:
        return {"status": "fail", "reason": "verify requires --unit to bind evidence"}
    per_unit = data["verification_units"]
    failed = [result["unit"] for result in per_unit if result["status"] != "pass"]
    if failed:
        # One failing unit fails the batch. A batch never averages its units.
        return {"status": "fail", "reason": f"units not verified: {', '.join(failed)}"}
    return {
        "status": "pass",
        "reason": f"all {len(per_unit)} unit(s) verified, manual-verified, or approved-deviation",
    }


def source_shellish(row: dict[str, str]) -> bool:
    source_path = row.get("source_path", "").lower()
    source_key = row.get("source_key", "").lower()
    return source_key in {"index", "main", "app"} or source_path in {"index.html", "index.htm"} or row.get("source_url") == "/"


def route_mapping_strength(row: dict[str, str], url_mapping: list[dict[str, str]]) -> tuple[int, str]:
    source_path = row.get("source_path", "")
    source_key = row.get("source_key", "")
    source_url = row.get("source_url", "")
    row_tokens = set(last_token_set(" ".join([source_key, source_path, source_url])))
    best = 0
    best_notes: list[str] = []
    for mapping in url_mapping:
        haystack = " ".join([
            mapping.get("source_template", ""),
            mapping.get("source_url", ""),
            mapping.get("host_entry_html", ""),
            mapping.get("host_entry_ts", ""),
            mapping.get("host_menu_or_route", ""),
        ]).lower()
        mapping_tokens = set(last_token_set(haystack))
        has_relation = False
        score = 0
        notes = []
        if source_path and source_path.lower() in haystack:
            has_relation = True
            score += 25
            notes.append("source-template")
        if source_url and source_url.lower() and source_url.lower() in haystack:
            has_relation = True
            score += 25
            notes.append("source-url")
        if row_tokens & mapping_tokens:
            has_relation = True
            score += 15
            notes.append("token-route")
        if has_relation and mapping.get("source_route_evidence") and mapping.get("source_route_evidence") != "url_guess only":
            score += 25
            notes.append("source-route")
        if has_relation and (mapping.get("host_entry_html") or mapping.get("host_entry_ts")):
            score += 20
            notes.append("host-entry")
        if score > best:
            best = score
            best_notes = notes
    return best, "+".join(sorted(set(best_notes))) if best else "path-order"


def recommended_units(comparison: list[dict[str, str]], url_mapping: list[dict[str, str]]) -> list[dict[str, str]]:
    candidates = [
        row
        for row in comparison
        if row["status"] in {"unmigrated", "partial-overlap"} and not source_shellish(row)
    ]
    scored = []
    for index, row in enumerate(candidates):
        score = 10 if row["status"] == "unmigrated" else 0
        route_score, route_reason = route_mapping_strength(row, url_mapping)
        score += route_score
        scored.append((score, index, route_reason, row))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {
            "priority": f"P{index + 1}",
            "unit": row["source_key"],
            "source_path": row["source_path"],
            "reason": f"可独立切换的页面候选；{route_reason}；需要宿主落点与对等闭包",
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


def labeled_table(rows: list[dict[str, str]], columns: list[tuple[str, str]]) -> str:
    return table(
        [label for _key, label in columns],
        ([row.get(key, "") for key, _label in columns] for row in rows),
    )


def build_markdown(args, data: dict) -> str:
    mode = args.mode
    mode_label = MODE_LABELS.get(mode, mode)
    lines = [
        f"# {args.project_name} AngularJS 迁入 Vue3 Host — {mode_label}",
        "",
        "本文件是证据基线。对照源仓与宿主代码复核之前，任何一行都不得当作实施设计。",
        "",
        "> 状态枚举、路径、命令、URL、CSV 字段名保持英文原文；章节标题、表头与说明默认简体中文。",
        "",
        "## 修订绑定",
        table(["仓库", "路径", "修订"], [
            ["source", str(data["source_repo"]), data["source_revision"]],
            ["host", str(data["host_repo"]) if data["host_repo"] else "[not provided]", data["host_revision"]],
        ]),
        "",
        "## 仓库获取",
        "克隆失败在已有 git 仓且 HEAD 可读时，记为警告而非阻断。",
        labeled_table(data["repo_acquisition"], [
            ("repo_role", "角色"),
            ("repo_path", "路径"),
            ("acquisition_status", "获取状态"),
            ("acquisition_warning", "获取警告"),
            ("revision", "修订"),
            ("revision_source", "修订来源"),
            ("dirty_entries", "脏文件数"),
            ("usable_for_stage", "本阶段可用"),
            ("notes", "备注"),
        ]),
        "",
        "## Git 卫生",
        "依赖/缓存/构建目录噪声会阻断提交就绪。`src/` 干净有参考价值，但不能证明整仓干净。",
        labeled_table(data["git_hygiene"], [
            ("repo_role", "角色"),
            ("status_entries", "状态条目数"),
            ("business_changes", "业务变更"),
            ("src_or_webapp_changes", "src/webapp 变更"),
            ("lockfile_changes", "lockfile 变更"),
            ("dependency_noise", "依赖噪声"),
            ("stage_status", "阶段状态"),
            ("notes", "备注"),
        ]),
        "",
        "## Host 栈",
        labeled_table(data["host_stack"], [
            ("area", "领域"),
            ("value", "取值"),
            ("evidence", "证据"),
        ]),
        "",
        "## Host 全局基线缺口",
        "源页假定这些全局依赖存在。B 侧为脚本探测，A 侧必须按源模板人工填写；`host-missing` / `host-partial` 是后续每一页的长期约束。",
        labeled_table(data["host_baseline_gap"], [(header, header) for header in HOST_BASELINE_HEADERS]),
        "",
        "## 源仓页面清单",
        labeled_table(data["source_pages"], [
            ("key", "标识"),
            ("kind", "类型"),
            ("tokens", "分词"),
            ("path", "路径"),
            ("url_guess", "URL 猜测"),
            ("signals", "信号"),
            ("line_count", "行数"),
        ]),
        "",
        "## Host 页面清单",
        labeled_table(data["host_pages"], [
            ("key", "标识"),
            ("kind", "类型"),
            ("tokens", "分词"),
            ("path", "路径"),
            ("url_guess", "URL 猜测"),
            ("signals", "信号"),
            ("line_count", "行数"),
        ]),
        "",
        "## A/B 页面对照",
        "本表是候选映射，不是缺口真相表。`already-migrated` 需要行为证据或人工确认，不得仅凭文件名匹配判定。",
        labeled_table(data["comparison"], [
            ("status", "状态"),
            ("match_basis", "匹配依据"),
            ("candidate_score", "候选分"),
            ("needs_human_correction", "需人工校正"),
            ("source_key", "源标识"),
            ("source_path", "源路径"),
            ("source_url", "源 URL"),
            ("host_path", "宿主路径"),
            ("host_entry", "宿主入口"),
            ("confidence", "置信度"),
            ("next_action", "下一步"),
        ]),
        "",
        "## URL / 入口映射",
        "由文件路径猜出的 URL 在有 Java 路由、菜单、MPA 或 Vue Router 入口证据前，置信度为低。",
        labeled_table(data["url_entry_mapping"], [
            ("source_url", "源 URL"),
            ("source_route_evidence", "源路由证据"),
            ("source_template", "源模板"),
            ("server_controller", "服务端 Controller"),
            ("host_entry_html", "宿主 HTML 入口"),
            ("host_entry_ts", "宿主 TS 入口"),
            ("host_menu_or_route", "宿主菜单/路由"),
            ("mapping_status", "映射状态"),
            ("confidence", "置信度"),
            ("unresolved", "未决"),
        ]),
        "",
        "## design-scope 选路判定",
        "`repair` 只在对照状态为 `partial-overlap` 且宿主入口有 route/menu/MPA 证据时给出。仅文件名相似不足以判定 B 已有入口。",
        labeled_table(data["design_scope_gate"], [
            ("source_key", "源页"),
            ("source_path", "源路径"),
            ("status", "对照状态"),
            ("host_entry", "宿主入口"),
            ("host_entry_evidence", "入口证据"),
            ("design_scope", "design-scope"),
            ("reason", "依据"),
        ]),
        "",
        "## 耦合计数",
        "源仓计数已排除 vendor/构建产物；lib/locale 不进页面对照，但可进入 CSS/i18n 闭包扫描。",
        labeled_table(data["source_couplings"], [
            ("signal", "信号"),
            ("matches", "命中数"),
            ("files", "文件数"),
        ]),
        "",
        "## CSS / i18n 闭包资源候选",
        "这些资源不是页面候选；只有被选定 UNIT 引用时才进入页面闭包。",
        labeled_table(data["source_closure_resources"], [
            ("resource_type", "类型"),
            ("path", "路径"),
            ("closure_status", "闭包状态"),
            ("notes", "说明"),
        ]),
        "",
        "## 建议优先迁移单元",
        labeled_table(data["recommended_units"], [
            ("priority", "优先级"),
            ("unit", "单元"),
            ("source_path", "源路径"),
            ("status", "状态"),
            ("reason", "理由"),
        ]),
        "",
        "## 校验门禁",
        table(["门禁", "检查项", "状态"], GATE_ROWS),
        "",
        "## 完成判定权",
        "不得仅凭本领域工件宣布页面迁移完成。完成需要 Delivery verified 证据、领域复核证据、当前宿主修订绑定，以及无阻断残留。",
    ]

    if mode in {"design", "verify"}:
        units = args.units or ["[缺少必填迁移单元]"]
        unit_label = "、".join(f"`{unit}`" for unit in units)
        profile_note = f"- Profile：`{args.profile}`（只读合同/切片计划，不执行 B 修改）" if args.profile else ""
        lines.extend([
            "",
            f"## {mode_label}单元",
            f"- 单元（{len(units)} 个，上限 {MAX_BATCH_UNITS}）：{unit_label}",
            profile_note,
            "- 范围：每个单元都是一个可独立切换的页面或用户行为",
            "- 规则：复用宿主 shell/鉴权/API/状态/组件；不要复制源仓布局",
            "",
            "## 批次准入",
            "批次内 design-scope 必须一致；`rejected` 或 `needs-human` 未清空前不得进入 Frame。",
            labeled_table(data["batch_admission"], [(header, header) for header in BATCH_ADMISSION_HEADERS]),
            "",
            "## 共享宿主面 ownership",
            "多个 unit 会碰的宿主面必须由唯一任务组独占修改，并作为前置组先落地；其余 unit 只读依赖。",
            labeled_table(data["batch_shared_surface"], [(header, header) for header in BATCH_SHARED_SURFACE_HEADERS]),
            "",
            "## 页面闭包合同",
            table(["项", "证据"], [
                ["源仓模板/片段", "从源码填写"],
                ["源仓 AngularJS/jQuery/服务端变量", "从源码填写"],
                ["源仓 API 与响应码", "从源码填写"],
                ["Host 落点文件", "从宿主代码填写"],
                ["复用/改动/新建决策", "复核宿主后填写"],
                ["旧 URL → 新入口", "用路由证据填写"],
                ["回退开关与条件", "实施前填写"],
            ]),
            "",
            "## 设计就绪门禁",
            "脚本生成的仅表头合同为 `not-ready: empty-contract`。在用证据填实这些行、或把未决边标为非阻断原因之前，不得进入 Delivery Frame。",
            "批次模式下每条门禁按 unit 逐个判定：任一 unit 未就绪，整批不得进入 Frame。",
            table(["门禁", "最低证据", "状态"], DESIGN_READY_ROWS),
            "",
            "## Display Contract Matrix 基线",
            "脚本只生成 partial-overlap 的矩阵骨架。每行仍需按源代码和运行时证据填实；`wired-unverified` 不能作为通过证据。",
            dict_table(data["display_contract"], DISPLAY_CONTRACT_HEADERS),
        ])

    if mode == "assess" and data["display_contract"]:
        lines.extend([
            "",
            "## Partial-Overlap Display Contract Matrix 基线",
            "脚本只生成矩阵骨架，防止壳页被误判为已迁完；设计前必须填实源文案、控件形态、字段公式、默认值、CSS 和启动副作用。",
            dict_table(data["display_contract"], DISPLAY_CONTRACT_HEADERS),
        ])

    if mode == "verify":
        result = data["verification_result"]
        lines.extend([
            "",
            "## 领域复核结论",
            "批次结论不取平均：任一 unit 未结清，整批为 fail。",
            table(["状态", "原因"], [[result["status"], result["reason"]]]),
            "",
            "### 逐单元结论",
            labeled_table(data["verification_units"], [
                ("unit", "单元"),
                ("status", "状态"),
                ("reason", "原因"),
            ]),
        ])

    if mode == "design" and args.units:
        lines.extend([
            "",
            "## 限定范围的 FLOW/CHAIN 合同",
            "这些表仅覆盖选定单元。不要用整仓占位行填表。",
            "",
            "### 业务流",
            table(FLOW_CONTRACT_HEADERS, []),
            "",
            "### 变量引用链",
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
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>AngularJS 迁入 Vue3 Host 迁移证据</title>
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
    host = Path(args.host_repo).resolve() if args.host_repo else None
    if not source.exists():
        raise SystemExit(f"source repo not found: {source}")
    if host and not host.exists():
        raise SystemExit(f"host repo not found: {host}")

    source_pages = discover_pages(source, SOURCE_PAGE_EXTS, source=True)
    host_pages = discover_pages(host, HOST_PAGE_EXTS, source=False) if host else []
    comparison = compare_pages(source_pages, host_pages)
    url_entry_mapping = build_url_entry_mapping(source, host, source_pages, host_pages)
    reconcile_comparison_entries(comparison, url_entry_mapping)
    data = {
        "source_repo": source,
        "host_repo": host,
        "source_revision": git_revision(source),
        "host_revision": git_revision(host) if host else "source-only",
        "repo_acquisition": repo_acquisition_rows(args, source, host),
        "git_hygiene": git_hygiene_rows(source, host),
        "host_stack": detect_host_stack(host) if host else [{"area": "source-only", "value": "host repo not provided", "evidence": "CLI --host-repo omitted"}],
        "source_pages": source_pages,
        "host_pages": host_pages,
        "comparison": comparison,
        "url_entry_mapping": url_entry_mapping,
        "source_couplings": coupling_counts(source, SOURCE_SIGNALS),
        "source_closure_resources": closure_resource_rows(source),
        "recommended_units": recommended_units(comparison, url_entry_mapping),
        "host_baseline_gap": host_baseline_gap_rows(host),
        "design_scope_gate": repair_scope_gate(comparison),
    }
    data["batch_admission"] = batch_admission_rows(args.units, comparison, data["design_scope_gate"])
    data["batch_shared_surface"] = batch_shared_surface_rows(host, data["batch_admission"], comparison)
    data["display_contract"] = display_contract_rows(comparison, args.units)
    data["verification_units"] = verification_unit_results(args, data)
    data["verification_result"] = verification_result(args, data)
    return data


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
        write_dict_csv(csv_dir / "03b-host-baseline-gap.csv", data["host_baseline_gap"], HOST_BASELINE_HEADERS)
        write_dict_csv(csv_dir / "04-source-pages.csv", data["source_pages"], ["key", "kind", "tokens", "path", "url_guess", "signals", "line_count"])
        write_dict_csv(csv_dir / "05-host-pages.csv", data["host_pages"], ["key", "kind", "tokens", "path", "url_guess", "signals", "line_count"])
        write_dict_csv(csv_dir / "06-page-comparison.csv", data["comparison"], ["status", "match_basis", "candidate_score", "needs_human_correction", "source_key", "source_path", "source_url", "host_path", "host_entry", "host_entry_evidence", "confidence", "next_action"])
        write_dict_csv(csv_dir / "07-url-entry-mapping.csv", data["url_entry_mapping"], ["source_page_path", "source_url", "source_route_evidence", "source_template", "server_controller", "host_entry_html", "host_entry_ts", "host_route_path", "host_menu_or_route", "mapping_status", "confidence", "unresolved"])
        write_dict_csv(csv_dir / "07b-design-scope-gate.csv", data["design_scope_gate"], DESIGN_SCOPE_HEADERS)
        write_dict_csv(csv_dir / "08-source-couplings.csv", data["source_couplings"], ["signal", "matches", "files"])
        write_dict_csv(csv_dir / "09-recommended-units.csv", data["recommended_units"], ["priority", "unit", "source_path", "status", "reason"])
        write_csv(csv_dir / "10-validation-gates.csv", ["gate", "check", "status"], GATE_ROWS)
        write_dict_csv(csv_dir / "14-source-closure-resources.csv", data["source_closure_resources"], ["resource_type", "path", "closure_status", "notes"])
        write_dict_csv(csv_dir / "15-display-contract.csv", data["display_contract"], DISPLAY_CONTRACT_HEADERS)
        if args.units:
            write_dict_csv(csv_dir / "17-batch-admission.csv", data["batch_admission"], BATCH_ADMISSION_HEADERS)
            write_dict_csv(csv_dir / "18-batch-shared-surface.csv", data["batch_shared_surface"], BATCH_SHARED_SURFACE_HEADERS)
        if args.mode == "verify":
            write_dict_csv(csv_dir / "16-verify-result.csv", [data["verification_result"]], ["status", "reason"])
            write_dict_csv(csv_dir / "16b-verify-units.csv", data["verification_units"], ["unit", "status", "reason"])
        if args.mode == "design" and args.units:
            write_csv(csv_dir / "11-design-ready-gate.csv", ["gate", "minimum evidence", "status"], DESIGN_READY_ROWS)
            write_csv(csv_dir / "12-business-flow-contract.csv", FLOW_CONTRACT_HEADERS, [])
            write_csv(csv_dir / "13-variable-chain-contract.csv", VARIABLE_CHAIN_HEADERS, [])
        print(f"Wrote CSV files under {csv_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate hosted AngularJS/JSP/jQuery to Vue3 migration evidence artifacts.")
    parser.add_argument("mode", nargs="?", choices=["assess", "design", "verify"], default="assess")
    parser.add_argument("--project-name", default="hosted-angularjs-to-vue3")
    parser.add_argument("--source-repo", required=True, help="Legacy source repo A")
    parser.add_argument("--host-repo", help="Existing Vue3 host repo B. Optional only for source-only assess.")
    parser.add_argument(
        "--unit",
        action="append",
        default=[],
        help=(
            "Page, route, menu item, URL, or user behavior for design/verify. "
            f"Repeat or comma-separate to run a batch of at most {MAX_BATCH_UNITS} units."
        ),
    )
    parser.add_argument("--profile", choices=["repair"], help="Optional read-only design profile for shell-page repair contracts.")
    parser.add_argument("--output-dir", default="reports/angularjs-vue3-migration")
    parser.add_argument("--format", choices=["markdown", "html", "csv", "all"], default="all")
    parser.add_argument("--source-acquisition-warning", default="", help="Optional warning from source repo clone/fetch, recorded as evidence.")
    parser.add_argument("--host-acquisition-warning", default="", help="Optional warning from host repo clone/fetch, recorded as evidence.")
    return parser


def parse_units(raw_units: list[str]) -> list[str]:
    units = []
    for value in raw_units:
        for piece in value.split(","):
            unit = piece.strip()
            if unit and unit not in units:
                units.append(unit)
    return units


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.units = parse_units(args.unit)
    if args.mode in {"design", "verify"} and not args.units:
        parser.error(f"{args.mode} mode requires --unit")
    if len(args.units) > MAX_BATCH_UNITS:
        parser.error(
            f"batch of {len(args.units)} units exceeds the cap of {MAX_BATCH_UNITS}; "
            "split it so the High cost/risk/rollback summary stays reviewable"
        )
    if args.mode in {"design", "verify"} and not args.host_repo:
        parser.error(f"{args.mode} mode requires --host-repo")
    data = collect_data(args)
    write_outputs(args, data)


if __name__ == "__main__":
    main()

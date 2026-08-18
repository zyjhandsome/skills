#!/usr/bin/env python3
"""Create a bounded, read-only Vue workspace impact profile.

The script reads manifests, lock metadata and source text. It never installs,
upgrades, executes project scripts, or edits the analyzed workspace.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

RELATED_NAMES = {
    "vue", "@vue/compat", "vue-router", "vuex", "pinia", "element-ui",
    "element-plus", "ant-design-vue", "vuetify", "vue-i18n",
    "vant",
    "@vue/test-utils", "@vue/composition-api", "@vue/cli-service",
    "@vue/compiler-sfc", "vue-template-compiler", "vite",
    "@vitejs/plugin-vue", "vite-plugin-vue2", "eslint-plugin-vue",
    "vuedraggable", "vue-draggable-next", "vue-class-component",
    "vue-property-decorator", "sass", "sass-loader", "webpack",
    # Non vue-* packages that commonly block Vue3 cutover or visual parity
    "tui-editor", "@toast-ui/editor", "@toast-ui/vue-editor",
    "vue2-editor", "quill", "mavon-editor", "wangeditor",
    # High-impact non-vue-* deps often missed by name heuristics
    "echarts", "xlsx", "normalize.css", "sortablejs", "file-saver",
    "jszip", "codemirror", "dropzone", "driver.js", "nprogress",
}

# Always surface these as replace/unknown even when not matching vue-* prefix rules.
REPLACE_ON_SIGHT = {
    "element-ui", "vite-plugin-vue2", "@vue/composition-api", "vue-template-compiler",
    "tui-editor", "@toast-ui/vue-editor", "vue2-editor", "mavon-editor",
}

LOCK_NAMES = ("pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb", "package-lock.json")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "coverage", ".idea", ".vscode"}
SOURCE_SUFFIXES = {".vue", ".js", ".jsx", ".ts", ".tsx"}
SOURCE_PATTERNS = {
    "new_vue": re.compile(r"\bnew\s+Vue\s*\("),
    "vue_use": re.compile(r"\bVue\.use\s*\("),
    "listeners_removed": re.compile(r"\$listeners\b"),
    "scoped_slots_changed": re.compile(r"\$scopedSlots\b"),
    "children_removed": re.compile(r"\$children\b"),
    "set_delete_removed": re.compile(r"\b(?:Vue|this)\.\$(?:set|delete)\s*\("),
    "sync_modifier": re.compile(r"\.sync\b"),
    "destroy_lifecycle": re.compile(r"\b(?:beforeDestroy|destroyed)\b"),
    "filters_option": re.compile(r"\bfilters\s*:"),
    "vue_filter_register": re.compile(r"\bVue\.filter\s*\("),
    "slot_scope": re.compile(r"\bslot-scope\b"),
    "slot_attr_legacy": re.compile(r"""(?:^|\s)slot\s*=\s*['"][^'"]+['"]"""),
    "functional_component": re.compile(r"\bfunctional\s*:\s*true\b"),
    "router_add_routes": re.compile(r"\.addRoutes\s*\("),
    "router_wildcard": re.compile(r"path\s*:\s*['\"]\*['\"]"),
    "event_bus": re.compile(r"\.\$(?:on|off|once)\s*\("),
    "vue_prototype_assignment": re.compile(
        r"\bVue\.prototype(?:\.\$[A-Za-z_$][\w$]*|\[\s*['\"]\$[A-Za-z_$][\w$]*['\"]\s*\])\s*="
    ),
    "vue_prototype_define_property": re.compile(
        r"\bObject\.defineProperty\s*\(\s*Vue\.prototype\s*,\s*['\"]\$[A-Za-z_$][\w$]*['\"]"
    ),
    "global_properties_assignment": re.compile(
        r"\b[A-Za-z_$][\w$]*\.config\.globalProperties(?:\.\$[A-Za-z_$][\w$]*|\[\s*['\"]\$[A-Za-z_$][\w$]*['\"]\s*\])\s*="
    ),
}
SCRIPT_SETUP_ATTR = re.compile(r"<script\b[^>]*\bsetup\b", re.I)
# Vue Options/Composition setup(props|context) — not editor callbacks like setup(editor)
VUE_SETUP_FN = re.compile(
    r"(?:^|[,\n{])\s*setup\s*\(\s*(?:props|context|ctx)?\s*[,)]",
    re.M,
)
EDITOR_SETUP_FN = re.compile(r"\bsetup\s*\(\s*editor\b", re.I)
PACKAGE_HINT = re.compile(
    r"(?:^|[-_/])(vue2?|plugin|editor|grid|tree|table|widget|component|ui)(?:$|[-_/])",
    re.I,
)
IMPORT_DEFAULT = re.compile(
    r"\bimport\s+(?:type\s+)?([A-Za-z_$][\w$]*)\s+from\s+['\"]([^'\"]+)['\"]"
)
IMPORT_NAMESPACE = re.compile(
    r"\bimport\s+\*\s+as\s+([A-Za-z_$][\w$]*)\s+from\s+['\"]([^'\"]+)['\"]"
)
REQUIRE_BINDING = re.compile(
    r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*require\(\s*['\"]([^'\"]+)['\"]\s*\)"
)
GLOBAL_MOUNT_CONSUMER = re.compile(r"\bthis\.(\$[A-Za-z_$][\w$]*)\b")
NODE_DECLARATION_PATTERN = re.compile(
    r"(?:node-version|NODE_VERSION|FROM\s+node:|setup-node|nodejs_version)",
    re.I,
)
VUE_BUILTIN_INSTANCE_PROPERTIES = {
    "$attrs", "$children", "$data", "$delete", "$destroy", "$el", "$emit",
    "$forceUpdate", "$listeners", "$mount", "$nextTick", "$off", "$on", "$once",
    "$options", "$parent", "$refs", "$root", "$scopedSlots", "$set", "$slots",
    "$watch",
}


def is_related(name: str) -> bool:
    return name in RELATED_NAMES or name.startswith("@vue/") or name.startswith("vue-")


def load_package_json(root: Path) -> dict:
    path = root / "package.json"
    if not path.is_file():
        raise FileNotFoundError(f"package.json not found under {root}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("package.json root must be an object")
    return data


def deps_map(pkg: dict) -> dict[str, str]:
    merged: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        block = pkg.get(key) or {}
        if isinstance(block, dict):
            merged.update({str(name): str(version) for name, version in block.items()})
    return merged


def node_contract_evidence(root: Path, pkg: dict) -> dict:
    """Collect bounded Node declarations without treating them as build proof."""
    candidates = [
        root / "Dockerfile",
        root / "docker-compose.yml",
        root / "docker-compose.yaml",
        root / ".gitlab-ci.yml",
        root / "azure-pipelines.yml",
        root / "netlify.toml",
        root / "vercel.json",
    ]
    for directory in (root / ".github" / "workflows", root / ".devcontainer"):
        if directory.is_dir():
            candidates.extend(path for path in directory.rglob("*") if path.is_file())
    declarations: list[dict[str, object]] = []
    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            if path.stat().st_size > 512_000:
                continue
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, 1):
            if NODE_DECLARATION_PATTERN.search(line):
                declarations.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "line": line_number,
                        "text": line.strip()[:300],
                    }
                )
                if len(declarations) >= 50:
                    break
        if len(declarations) >= 50:
            break
    volta = pkg.get("volta") if isinstance(pkg.get("volta"), dict) else {}
    engines = pkg.get("engines") if isinstance(pkg.get("engines"), dict) else {}
    return {
        "package_json_engines_node": engines.get("node"),
        "package_json_volta_node": volta.get("node"),
        "config_declarations": declarations,
        "known_green_baseline": None,
        "note": "declarations are contract signals; they do not prove a green build",
    }


def major_from_spec(spec: str) -> int | None:
    """Extract a numeric major without lexicographic version comparisons."""
    match = re.search(r"(?<!\d)(\d+)(?:\.\d+)?", spec)
    return int(match.group(1)) if match else None


def _string_vue_major(major: int | None) -> str | None:
    return str(major) if major is not None else None


def classify_vue3_readiness(name: str, spec: str) -> str:
    major = major_from_spec(spec)
    if name in REPLACE_ON_SIGHT:
        return "replace"
    if name in {
        "@toast-ui/editor", "quill", "wangeditor",
        "echarts", "xlsx", "normalize.css", "sortablejs", "file-saver",
        "jszip", "codemirror", "dropzone", "driver.js", "nprogress",
    }:
        # Framework-agnostic or CSS/reset utilities: still surface for regression.
        return "unknown"
    minimum_majors = {
        "vue": 3,
        "vue-router": 4,
        "vuex": 4,
        "pinia": 2,
        "element-plus": 1,
        "ant-design-vue": 2,
        "vuetify": 3,
        "vant": 3,
        "vue-i18n": 9,
        "@vue/test-utils": 2,
        "@vue/compiler-sfc": 3,
        "@vue/compat": 3,
        "@vue/cli-service": 5,
        "@vitejs/plugin-vue": 1,
        "vite": 2,
        "eslint-plugin-vue": 7,
        "vuedraggable": 4,
        "vue-draggable-next": 2,
    }
    minimum = minimum_majors.get(name)
    if minimum is None or major is None:
        return "unknown"
    return "ready" if major >= minimum else "needs-major"


def count_composition_setup(text: str, relative: str) -> int:
    """Count likely Vue Composition/Options setup usage; skip editor callbacks."""
    count = 0
    if relative.endswith(".vue") and SCRIPT_SETUP_ATTR.search(text):
        count += 1
    for match in VUE_SETUP_FN.finditer(text):
        window = text[match.start() : match.start() + 48]
        if EDITOR_SETUP_FN.search(window):
            continue
        # TinyMCE / toast-ui paths often use setup(editor); already skipped above.
        if "tinymce" in relative.lower() and "props" not in window and "context" not in window:
            continue
        count += 1
    return count


def find_lockfiles(root: Path) -> list[str]:
    """Find workspace and nearest parent lockfiles without leaving the project drive."""
    found: list[str] = []
    current = root
    for _ in range(4):
        for name in LOCK_NAMES:
            candidate = current / name
            if candidate.is_file():
                found.append(str(candidate.resolve()))
        if current.parent == current or current.parent.drive != root.drive:
            break
        current = current.parent
    return sorted(set(found))


def package_lock_versions(lockfiles: list[str], package_names: set[str]) -> dict[str, str]:
    lock = next((Path(item) for item in lockfiles if Path(item).name == "package-lock.json"), None)
    if not lock:
        return {}
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    versions: dict[str, str] = {}
    packages = data.get("packages") if isinstance(data, dict) else None
    if isinstance(packages, dict):
        for name in package_names:
            meta = packages.get(f"node_modules/{name}")
            if isinstance(meta, dict) and meta.get("version"):
                versions[name] = str(meta["version"])
    dependencies = data.get("dependencies") if isinstance(data, dict) else None
    if isinstance(dependencies, dict):
        for name in package_names:
            meta = dependencies.get(name)
            if name not in versions and isinstance(meta, dict) and meta.get("version"):
                versions[name] = str(meta["version"])
    return versions


def assess_lockfiles(lockfiles: list[str]) -> dict:
    """Return a conservative, machine-readable lockfile state."""
    if not lockfiles:
        return {"status": "absent", "errors": []}
    errors: list[str] = []
    for item in lockfiles:
        path = Path(item)
        try:
            if path.stat().st_size == 0:
                errors.append(f"empty:{path}")
                continue
            if path.name == "package-lock.json":
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    errors.append(f"invalid-root:{path}")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"unparsed:{path}:{type(exc).__name__}")
    return {"status": "unparsed" if errors else "present", "errors": errors}


def package_peer_vue_specs(
    root: Path, lockfiles: list[str], package_names: set[str]
) -> dict[str, str]:
    """Read Vue peer ranges from package-lock metadata or installed packages."""
    specs: dict[str, str] = {}
    lock = next((Path(item) for item in lockfiles if Path(item).name == "package-lock.json"), None)
    if lock:
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            data = {}
        packages = data.get("packages") if isinstance(data, dict) else None
        if isinstance(packages, dict):
            for name in package_names:
                meta = packages.get(f"node_modules/{name}")
                peers = meta.get("peerDependencies") if isinstance(meta, dict) else None
                if isinstance(peers, dict) and peers.get("vue"):
                    specs[name] = str(peers["vue"])
    modules_root = root / "node_modules"
    for name in package_names - specs.keys():
        manifest = modules_root.joinpath(*name.split("/"), "package.json")
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        peers = meta.get("peerDependencies") if isinstance(meta, dict) else None
        if isinstance(peers, dict) and peers.get("vue"):
            specs[name] = str(peers["vue"])
    return specs


def package_name_from_specifier(specifier: str) -> str | None:
    if not specifier or specifier.startswith((".", "/", "#")):
        return None
    parts = specifier.split("/")
    if specifier.startswith("@"):
        return "/".join(parts[:2]) if len(parts) >= 2 else None
    return parts[0]


def _append_sample(target: dict[str, list[str]], key: str, relative: str) -> None:
    bucket = target.setdefault(key, [])
    if relative not in bucket and len(bucket) < 5:
        bucket.append(relative)


def discover_source_roots(root: Path) -> list[Path]:
    """Discover bounded sibling source roots used by multi-page Vue workspaces.

    Vue CLI projects commonly keep additional entries in top-level directories
    such as ``src.mobile``. Scanning only ``src`` silently drops an entire build
    surface, while recursively scanning the repository pulls in vendored assets.
    Restrict discovery to conventional top-level ``src`` variants.
    """
    candidates = []
    try:
        children = sorted(root.iterdir(), key=lambda item: item.name.lower())
    except OSError:
        return candidates
    for child in children:
        if not child.is_dir():
            continue
        name = child.name
        if name == "src" or name.startswith(("src.", "src-", "src_")):
            candidates.append(child)
    return candidates


def scan_source(
    root: Path,
    source_roots: list[Path] | None = None,
    max_files: int = 5000,
    max_bytes: int = 1_000_000,
) -> dict:
    signal_keys = list(SOURCE_PATTERNS) + ["composition_setup"]
    counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = {key: [] for key in signal_keys}
    scanned_files = 0
    skipped_large = 0
    truncated = False
    plugin_packages: dict[str, list[str]] = {}
    legacy_definitions: dict[str, list[str]] = {}
    vue3_definitions: dict[str, list[str]] = {}
    consumers: dict[str, list[str]] = {}
    roots = source_roots if source_roots is not None else discover_source_roots(root)
    if not roots:
        return {"scanned_files": 0, "skipped_large_files": 0, "truncated": False,
                "signals": {}, "samples": {}, "vue_plugin_packages": {},
                "global_mounts": {}}
    paths = (path for source_root in roots for path in source_root.rglob("*"))
    for path in paths:
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if scanned_files >= max_files:
            truncated = True
            break
        try:
            if path.stat().st_size > max_bytes:
                skipped_large += 1
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned_files += 1
        relative = path.relative_to(root).as_posix()
        bindings: dict[str, str] = {}
        for pattern in (IMPORT_DEFAULT, IMPORT_NAMESPACE, REQUIRE_BINDING):
            for match in pattern.finditer(text):
                package = package_name_from_specifier(match.group(2))
                if package:
                    bindings[match.group(1)] = package
        vue_bindings = {"Vue"}
        vue_bindings.update(binding for binding, package in bindings.items() if package == "vue")
        for vue_binding in vue_bindings:
            for match in re.finditer(
                rf"\b{re.escape(vue_binding)}\.use\s*\(\s*([A-Za-z_$][\w$]*)",
                text,
            ):
                package = bindings.get(match.group(1))
                if package and package != "vue":
                    _append_sample(plugin_packages, package, relative)
            definition_patterns = (
                re.compile(
                    rf"\b{re.escape(vue_binding)}\.prototype\.(\$[A-Za-z_$][\w$]*)\s*="
                ),
                re.compile(
                    rf"\b{re.escape(vue_binding)}\.prototype\[\s*['\"](\$[A-Za-z_$][\w$]*)['\"]\s*\]\s*="
                ),
                re.compile(
                    rf"\bObject\.defineProperty\s*\(\s*{re.escape(vue_binding)}\.prototype\s*,\s*['\"](\$[A-Za-z_$][\w$]*)['\"]"
                ),
            )
            for pattern in definition_patterns:
                for match in pattern.finditer(text):
                    _append_sample(legacy_definitions, match.group(1), relative)
        for match in re.finditer(
            r"\b[A-Za-z_$][\w$]*\.config\.globalProperties\.(\$[A-Za-z_$][\w$]*)\s*=",
            text,
        ):
            _append_sample(vue3_definitions, match.group(1), relative)
        for match in GLOBAL_MOUNT_CONSUMER.finditer(text):
            name = match.group(1)
            if name not in VUE_BUILTIN_INSTANCE_PROPERTIES:
                _append_sample(consumers, name, relative)
        for key, pattern in SOURCE_PATTERNS.items():
            matches = list(pattern.finditer(text))
            if matches:
                counts[key] += len(matches)
                if len(samples[key]) < 5:
                    samples[key].append(relative)
        setup_hits = count_composition_setup(text, relative)
        if setup_hits:
            counts["composition_setup"] += setup_hits
            if len(samples["composition_setup"]) < 5:
                samples["composition_setup"].append(relative)
    mount_names = sorted(set(legacy_definitions) | set(vue3_definitions) | set(consumers))
    global_mounts = {
        name: {
            "legacy_definition_samples": legacy_definitions.get(name, []),
            "vue3_definition_samples": vue3_definitions.get(name, []),
            "consumer_samples": consumers.get(name, []),
            "unresolved_consumer": bool(consumers.get(name))
            and not bool(legacy_definitions.get(name) or vue3_definitions.get(name)),
        }
        for name in mount_names
    }
    return {
        "scanned_files": scanned_files,
        "skipped_large_files": skipped_large,
        "truncated": truncated,
        "signals": dict(sorted(counts.items())),
        "samples": {key: value for key, value in samples.items() if value},
        "vue_plugin_packages": dict(sorted(plugin_packages.items())),
        "global_mounts": global_mounts,
    }


def profile(root: Path) -> dict:
    pkg = load_package_json(root)
    deps = deps_map(pkg)
    lockfiles = find_lockfiles(root)
    lockfile_state = assess_lockfiles(lockfiles)
    resolved = package_lock_versions(lockfiles, set(deps))
    peer_vue_specs = package_peer_vue_specs(root, lockfiles, set(deps))
    source_roots = discover_source_roots(root)
    source_impact = scan_source(root, source_roots)
    related = {}
    for name, spec in sorted(deps.items()):
        candidate_reasons: list[str] = []
        if is_related(name):
            candidate_reasons.append("known-vue-package")
        if PACKAGE_HINT.search(name):
            candidate_reasons.append("package-name-heuristic")
        if name in peer_vue_specs:
            candidate_reasons.append(f"peerDependencies.vue={peer_vue_specs[name]}")
        if name in source_impact["vue_plugin_packages"]:
            candidate_reasons.append("registered-via-Vue.use")
        if not candidate_reasons:
            continue
        effective = resolved.get(name, spec)
        related[name] = {
            "declared_version": spec,
            "resolved_version": resolved.get(name),
            "readiness": classify_vue3_readiness(name, effective),
            "candidate_reasons": candidate_reasons,
            "classification_basis": (
                "minimum-compatible-major; verify selected target version from official sources"
                if is_related(name)
                else "candidate-only; verify Vue3 support, maintenance status, and replacement"
            ),
        }
    vue_spec = deps.get("vue", "")
    scripts = json.dumps(pkg.get("scripts") or {})
    if "vite" in deps or re.search(r"\bvite\b", scripts):
        builder = "vite-vue2" if "vite-plugin-vue2" in deps else "vite"
    elif "@vue/cli-service" in deps or "vue-cli-service" in scripts:
        builder = "vue-cli"
    elif "webpack" in deps:
        builder = "webpack-custom"
    else:
        builder = "unknown"
    package_manager = pkg.get("packageManager")
    volta = pkg.get("volta") if isinstance(pkg.get("volta"), dict) else {}
    ui_stacks = [
        name
        for name in ("element-ui", "element-plus", "ant-design-vue", "vuetify", "vant")
        if name in deps
    ]
    return {
        "project_root": str(root.resolve()),
        "profile_as_of": date.today().isoformat(),
        "package_name": pkg.get("name"),
        "package_manager_pin": package_manager,
        "node_pins": {
            "engines": (pkg.get("engines") or {}).get("node"),
            "volta": volta.get("node"),
            ".nvmrc": (root / ".nvmrc").read_text(encoding="utf-8").strip() if (root / ".nvmrc").is_file() else None,
            ".node-version": (root / ".node-version").read_text(encoding="utf-8").strip() if (root / ".node-version").is_file() else None,
        },
        "node_contract_evidence": node_contract_evidence(root, pkg),
        "vue_version_spec": vue_spec or None,
        # Contract: string major ("2" / "3"), never int — matches dual-entry schema.
        "vue_major": _string_vue_major(
            major_from_spec(resolved.get("vue", vue_spec)) if vue_spec else None
        ),
        "builder": builder,
        "has_typescript": bool(deps.get("typescript") or (root / "tsconfig.json").is_file()),
        "store": "both" if "vuex" in deps and "pinia" in deps else "vuex" if "vuex" in deps else "pinia" if "pinia" in deps else "none",
        "ui_stack": ui_stacks[0] if ui_stacks else "none",
        "ui_stacks": ui_stacks,
        "source_roots": [path.relative_to(root).as_posix() for path in source_roots],
        "composition_bridge": "@vue/composition-api" in deps,
        "lockfiles": lockfiles,
        "lockfile_status": lockfile_state["status"],
        "lockfile_errors": lockfile_state["errors"],
        "related_packages": related,
        "source_impact_signals": source_impact,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        help="explicit UTF-8 JSON artifact path; omitted means no filesystem writes",
    )
    args = parser.parse_args()
    root = args.project_root.resolve()
    try:
        data = profile(root)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"invalid package.json: {exc}", file=sys.stderr)
        return 3
    rendered = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if args.json:
        print(rendered)
    else:
        print(f"workspace: {data['package_name']} @ {data['project_root']}")
        print(f"vue: {data['vue_version_spec']} (major={data['vue_major']})")
        print(f"builder: {data['builder']} store: {data['store']} ui: {data['ui_stack']}")
        print(
            f"locks: {len(data['lockfiles'])} ({data['lockfile_status']}) "
            f"source files: {data['source_impact_signals']['scanned_files']}"
        )
        for name, meta in data["related_packages"].items():
            shown = meta["resolved_version"] or meta["declared_version"]
            print(f"  - {name}@{shown} [{meta['readiness']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

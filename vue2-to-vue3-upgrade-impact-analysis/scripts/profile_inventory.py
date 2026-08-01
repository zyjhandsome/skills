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
    "@vue/test-utils", "@vue/composition-api", "@vue/cli-service",
    "@vue/compiler-sfc", "vue-template-compiler", "vite",
    "@vitejs/plugin-vue", "vite-plugin-vue2", "eslint-plugin-vue",
    "vuedraggable", "vue-draggable-next", "vue-class-component",
    "vue-property-decorator", "sass", "sass-loader", "webpack",
    # Non vue-* packages that commonly block Vue3 cutover
    "tui-editor", "@toast-ui/editor", "@toast-ui/vue-editor",
    "vue2-editor", "quill", "mavon-editor", "wangeditor",
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
}
SCRIPT_SETUP_ATTR = re.compile(r"<script\b[^>]*\bsetup\b", re.I)
# Vue Options/Composition setup(props|context) — not editor callbacks like setup(editor)
VUE_SETUP_FN = re.compile(
    r"(?:^|[,\n{])\s*setup\s*\(\s*(?:props|context|ctx)?\s*[,)]",
    re.M,
)
EDITOR_SETUP_FN = re.compile(r"\bsetup\s*\(\s*editor\b", re.I)


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
    if name in {"@toast-ui/editor", "quill", "wangeditor"}:
        # Not Vue-bound by name; still flag for residual/blocker review.
        return "unknown"
    minimum_majors = {
        "vue": 3,
        "vue-router": 4,
        "vuex": 4,
        "pinia": 2,
        "element-plus": 1,
        "ant-design-vue": 2,
        "vuetify": 3,
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


def scan_source(root: Path, max_files: int = 5000, max_bytes: int = 1_000_000) -> dict:
    signal_keys = list(SOURCE_PATTERNS) + ["composition_setup"]
    counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = {key: [] for key in signal_keys}
    scanned_files = 0
    skipped_large = 0
    truncated = False
    source_root = root / "src"
    if not source_root.is_dir():
        return {"scanned_files": 0, "skipped_large_files": 0, "truncated": False,
                "signals": {}, "samples": {}}
    for path in source_root.rglob("*"):
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
    return {
        "scanned_files": scanned_files,
        "skipped_large_files": skipped_large,
        "truncated": truncated,
        "signals": dict(sorted(counts.items())),
        "samples": {key: value for key, value in samples.items() if value},
    }


def profile(root: Path) -> dict:
    pkg = load_package_json(root)
    deps = deps_map(pkg)
    lockfiles = find_lockfiles(root)
    resolved = package_lock_versions(lockfiles, set(deps))
    related = {}
    for name, spec in sorted(deps.items()):
        if not is_related(name):
            continue
        effective = resolved.get(name, spec)
        related[name] = {
            "declared_version": spec,
            "resolved_version": resolved.get(name),
            "readiness": classify_vue3_readiness(name, effective),
            "classification_basis": "minimum-compatible-major; verify selected target version from official sources",
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
        "vue_version_spec": vue_spec or None,
        # Contract: string major ("2" / "3"), never int — matches dual-entry schema.
        "vue_major": _string_vue_major(
            major_from_spec(resolved.get("vue", vue_spec)) if vue_spec else None
        ),
        "builder": builder,
        "has_typescript": bool(deps.get("typescript") or (root / "tsconfig.json").is_file()),
        "store": "both" if "vuex" in deps and "pinia" in deps else "vuex" if "vuex" in deps else "pinia" if "pinia" in deps else "none",
        "ui_stack": "element-ui" if "element-ui" in deps else "element-plus" if "element-plus" in deps else "ant-design-vue" if "ant-design-vue" in deps else "vuetify" if "vuetify" in deps else "none",
        "composition_bridge": "@vue/composition-api" in deps,
        "lockfiles": lockfiles,
        "related_packages": related,
        "source_impact_signals": scan_source(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
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
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"workspace: {data['package_name']} @ {data['project_root']}")
        print(f"vue: {data['vue_version_spec']} (major={data['vue_major']})")
        print(f"builder: {data['builder']} store: {data['store']} ui: {data['ui_stack']}")
        print(f"locks: {len(data['lockfiles'])} source files: {data['source_impact_signals']['scanned_files']}")
        for name, meta in data["related_packages"].items():
            shown = meta["resolved_version"] or meta["declared_version"]
            print(f"  - {name}@{shown} [{meta['readiness']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

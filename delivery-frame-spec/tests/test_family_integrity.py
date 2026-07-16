#!/usr/bin/env python3
"""Family integrity self-check: run before shipping the delivery-* skills to other users.

1. Every relative path referenced in the four SKILL.md files and shared references
   (references/*.md, scripts/*.py, tests/*) resolves to an existing file/dir.
2. family_version strings outside the authoritative family-contract.md match its value.
3. All four skills plus the shared contract/template/adapter files exist (atomic install).

Standard library only. Exit 0 = consistent, 1 = broken reference or version drift.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILLS_ROOT = TESTS_DIR.parent.parent
FAMILY = ("delivery-explore", "delivery-frame-spec", "delivery-plan-tasks", "delivery-execute-verify")
REQUIRED_SHARED = (
    "delivery-frame-spec/references/family-contract.md",
    "delivery-frame-spec/references/handoff-contract.md",
    "delivery-frame-spec/references/handoff-template.md",
    "delivery-frame-spec/references/batch-clarification.md",
    "delivery-frame-spec/references/openspec-adapter.md",
    "delivery-frame-spec/scripts/validate_handoff.py",
    "delivery-frame-spec/scripts/hash_change_artifacts.py",
    "delivery-frame-spec/scripts/delivery_scaffold.py",
    "delivery-execute-verify/scripts/validate_delivery_change.py",
)
# Backtick-quoted relative paths that live in the repo, including cross-skill references
# like `../delivery-frame-spec/references/family-contract.md`. Skip templates/placeholders.
PATH_RE = re.compile(
    r"`((?:\.\./)?(?:delivery-[a-z-]+/)?(?:references|scripts|tests)/[A-Za-z0-9_./-]+)`"
)
VERSION_RE = re.compile(r"delivery-family/(\d+\.\d+)")
AUTHORITY = SKILLS_ROOT / "delivery-frame-spec" / "references" / "family-contract.md"


def scan_files() -> list[Path]:
    files: list[Path] = []
    for skill in FAMILY:
        root = SKILLS_ROOT / skill
        files.append(root / "SKILL.md")
        files.extend((root / "references").glob("*.md"))
    return [f for f in files if f.is_file()]


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_SHARED:
        if not (SKILLS_ROOT / rel).is_file():
            errors.append(f"atomic-install: required shared file missing: {rel}")
    for skill in FAMILY:
        if not (SKILLS_ROOT / skill / "SKILL.md").is_file():
            errors.append(f"atomic-install: {skill}/SKILL.md missing")

    for doc in scan_files():
        base = doc.parent
        for match in PATH_RE.finditer(doc.read_text(encoding="utf-8")):
            ref = match.group(1)
            if "<" in ref or ref.endswith("/"):
                continue
            target = (base / ref).resolve()
            if not target.exists() and ref.startswith("../delivery-"):
                # Cross-skill form documented for consumption from another skill's root
                # (e.g. the authoritative-path line in batch-clarification.md).
                target = (SKILLS_ROOT / ref.removeprefix("../")).resolve()
            if not target.exists():
                errors.append(f"broken reference in {doc.relative_to(SKILLS_ROOT)}: `{ref}`")

    authoritative = VERSION_RE.search(AUTHORITY.read_text(encoding="utf-8"))
    if not authoritative:
        errors.append("family-contract.md declares no family_version")
    else:
        current = authoritative.group(1)
        for skill in FAMILY:
            for path in (SKILLS_ROOT / skill).rglob("*"):
                if path.suffix not in {".md", ".py", ".json"} or not path.is_file():
                    continue
                if path == AUTHORITY or "tests" in path.parts:
                    continue  # tests may pin historical versions with banners
                for version in VERSION_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
                    if version.split(".")[0] != current.split(".")[0]:
                        errors.append(
                            f"family_version major drift in {path.relative_to(SKILLS_ROOT)}: "
                            f"{version} vs authoritative {current}"
                        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: family references, atomic-install set, and version majors are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

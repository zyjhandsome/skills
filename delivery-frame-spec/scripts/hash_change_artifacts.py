#!/usr/bin/env python3
"""Compute artifact_revision for an OpenSpec change directory.

Hashes authoritative planning/execution files (proposal, design, tasks, specs/**,
verification when present). Ignores _test_harness and dotfiles.

Usage:
  python hash_change_artifacts.py path/to/openspec/changes/<id>
  python hash_change_artifacts.py path/to/openspec/changes/<id> --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

INCLUDE_NAMES = {
    "proposal.md",
    "design.md",
    "tasks.md",
    "verification.md",
}
INCLUDE_GLOBS = ("specs/**/*.md",)


def iter_artifact_files(change_dir: Path) -> list[Path]:
    files: list[Path] = []
    for name in INCLUDE_NAMES:
        path = change_dir / name
        if path.is_file():
            files.append(path)
    for pattern in INCLUDE_GLOBS:
        files.extend(p for p in change_dir.glob(pattern) if p.is_file())
    # Stable order by relative posix path
    return sorted({p.resolve() for p in files}, key=lambda p: p.relative_to(change_dir.resolve()).as_posix())


def hash_change(change_dir: Path) -> tuple[str, list[dict[str, str]]]:
    root = change_dir.resolve()
    entries: list[dict[str, str]] = []
    h = hashlib.sha256()
    for path in iter_artifact_files(change_dir):
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        file_digest = hashlib.sha256(data).hexdigest()
        entries.append({"path": rel, "sha256": file_digest})
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(data)
        h.update(b"\0")
    return h.hexdigest(), entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("change_dir", type=Path, help="OpenSpec change directory")
    parser.add_argument("--json", action="store_true", help="Print JSON with per-file digests")
    args = parser.parse_args()
    change_dir = args.change_dir
    if not change_dir.is_dir():
        print(f"ERROR: not a directory: {change_dir}", file=sys.stderr)
        return 2
    digest, entries = hash_change(change_dir)
    if not entries:
        print("ERROR: no authoritative artifacts found", file=sys.stderr)
        return 1
    if args.json:
        print(
            json.dumps(
                {"artifact_revision": digest, "files": entries},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

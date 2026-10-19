#!/usr/bin/env python3
"""Convert Obsidian same-doc block refs [[#heading]] to Markdown [text](#slug)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from heading_slug import heading_to_slug  # noqa: E402

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
WIKILINK_RE = re.compile(r"\[\[#([^\]|]+)(?:\|([^\]]+))?\]\]")


def build_slug_map(text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for match in HEADING_RE.finditer(text):
        title = match.group(2).strip()
        mapping[title] = heading_to_slug(title)
    return mapping


def fix_wikilink_anchors(text: str) -> tuple[str, int]:
    slug_map = build_slug_map(text)
    replacements = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal replacements
        title = match.group(1).strip()
        alias = match.group(2)
        slug = slug_map.get(title)
        if slug is None:
            slug = heading_to_slug(title)
        label = alias.strip() if alias else title
        replacements += 1
        return f"[{label}](#{slug})"

    return WIKILINK_RE.sub(repl, text), replacements


def process_file(path: Path, dry_run: bool = False) -> int:
    original = path.read_text(encoding="utf-8")
    updated, count = fix_wikilink_anchors(original)
    if count and not dry_run:
        path.write_text(updated, encoding="utf-8")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Markdown files or directories (default: cwd)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    args = parser.parse_args()

    targets: list[Path] = []
    roots = args.paths or [Path.cwd()]
    for root in roots:
        if root.is_dir():
            targets.extend(sorted(root.rglob("*.md")))
        elif root.is_file():
            targets.append(root)

    total = 0
    for path in targets:
        count = process_file(path, dry_run=args.dry_run)
        if count:
            action = "would fix" if args.dry_run else "fixed"
            print(f"{action} {count} wikilink(s): {path}")
            total += count

    print(f"Done. {'Would fix' if args.dry_run else 'Fixed'} {total} wikilink anchor(s) in {len(targets)} file(s).")


if __name__ == "__main__":
    main()

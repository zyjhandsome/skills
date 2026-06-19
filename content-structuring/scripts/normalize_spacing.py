#!/usr/bin/env python3
"""Normalize content-structuring output Markdown spacing (spec v5.24/v5.25).

Fixes:
- Remove --- between body ## sections (keep only structural ---)
- Collapse 3+ consecutive blank lines to one
- Ensure exactly one blank line between ## and first ###

Usage:
  python normalize_spacing.py path/to/doc.md          # fix in place
  python normalize_spacing.py path/to/doc.md --check  # exit 1 if violations
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STRUCTURAL_AFTER = frozenset(
    {
        "核心导读",
        "目录",
    }
)
STRUCTURAL_BEFORE = frozenset(
    {
        "延伸术语表",
        "自检报告",
    }
)

MAX_HR = 5


def _section_title(line: str) -> str | None:
    m = re.match(r"^## ([^#].*)$", line)
    return m.group(1).strip() if m else None


def _is_body_section(title: str) -> bool:
    skip = {"文章元数据", "核心导读", "目录", "延伸术语表", "自检报告"}
    return title not in skip and not title.startswith("延伸术语表") and not title.startswith("自检报告")


def check(text: str) -> list[str]:
    issues: list[str] = []
    lines = text.splitlines()
    hr_lines = [i + 1 for i, ln in enumerate(lines) if ln.strip() == "---"]
    if len(hr_lines) > MAX_HR:
        issues.append(f"--- count {len(hr_lines)} > {MAX_HR} (lines {hr_lines})")

    triples = [m.start() for m in re.finditer(r"\n\n\n+", text)]
    if triples:
        issues.append(f"triple+ blank lines: {len(triples)} block(s)")

    for i, line in enumerate(lines):
        title = _section_title(line)
        if not title or not _is_body_section(title):
            continue
        blanks = 0
        j = i + 1
        while j < len(lines) and lines[j].strip() == "":
            blanks += 1
            j += 1
        if blanks != 1:
            issues.append(f"L{i + 1} ## {title[:40]}: {blanks} blank line(s) before next content (want 1)")

    # body --- between sections (after 目录, before 延伸术语表)
    past_toc = False
    for i, line in enumerate(lines):
        title = _section_title(line)
        if title == "目录":
            past_toc = True
            continue
        if not past_toc:
            continue
        if title and (title.startswith("延伸术语表") or title.startswith("自检报告")):
            break
        if line.strip() != "---":
            continue
        nxt_title = _section_title(lines[i + 1]) if i + 1 < len(lines) else None
        if nxt_title and _is_body_section(nxt_title):
            issues.append(f"L{i + 1}: --- between body sections (before ## {nxt_title[:40]})")

    return issues


def normalize(text: str) -> str:
    lines = text.splitlines()

    # Split into ## sections
    blocks: list[list[str]] = []
    current: list[str] = []
    preamble: list[str] = []

    started = False
    for line in lines:
        if re.match(r"^## [^#]", line):
            started = True
            if current:
                blocks.append(current)
            current = [line]
        elif not started:
            preamble.append(line)
        else:
            current.append(line)
    if current:
        blocks.append(current)

    def strip_block(block: list[str]) -> list[str]:
        heading = block[0]
        rest = block[1:]
        while rest and rest[0].strip() == "":
            rest.pop(0)
        while rest and rest[-1].strip() == "":
            rest.pop()
        while rest and rest[-1].strip() == "---":
            rest.pop()
            while rest and rest[-1].strip() == "":
                rest.pop()
        return [heading, ""] + rest

    normalized_blocks = [strip_block(b) for b in blocks]

    result: list[str] = []
    if preamble:
        while preamble and preamble[-1].strip() == "":
            preamble.pop()
        result.extend(preamble)
        result.append("")

    for i, block in enumerate(normalized_blocks):
        title = _section_title(block[0]) or ""

        if title == "核心导读":
            if result and result[-1] != "---":
                result.extend(["", "---"] if result[-1] != "" else ["---"])
            result.append("")
        elif title == "目录":
            result.extend(["", "---", ""])
        elif _is_body_section(title) and i > 0:
            # first body section after 目录 needs --- only if 目录 block didn't add it
            prev_title = _section_title(normalized_blocks[i - 1][0]) if i > 0 else None
            if prev_title == "目录" and (not result or result[-1] != "---"):
                result.extend(["", "---", ""])
        elif title.startswith("延伸术语表"):
            result.extend(["", "---", ""])
        elif title.startswith("自检报告"):
            result.extend(["", "---", ""])

        result.extend(block)
        if i < len(normalized_blocks) - 1:
            if result[-1] != "":
                result.append("")

    out = "\n".join(result)
    out = re.sub(r"\n{3,}", "\n\n", out)
    # metadata block: ensure --- after 人物背景 block if first structural
    if "---" not in out.split("## 核心导读")[0]:
        out = out.replace("\n\n## 核心导读", "\n\n---\n\n## 核心导读", 1)
    out = out.rstrip() + "\n"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize content-structuring Markdown spacing")
    parser.add_argument("path", type=Path)
    parser.add_argument("--check", action="store_true", help="Report violations only, do not write")
    args = parser.parse_args()

    text = args.path.read_text(encoding="utf-8")
    issues = check(text)
    if args.check:
        if issues:
            for issue in issues:
                print(issue)
            return 1
        print("OK: 4d spacing gate passed")
        return 0

    fixed = normalize(text)
    post_issues = check(fixed)
    args.path.write_text(fixed, encoding="utf-8", newline="\n")
    if post_issues:
        print("Normalized with remaining issues:")
        for issue in post_issues:
            print(" ", issue)
        return 1
    print(f"Normalized: {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""4e readability gate for content-structuring drafts.

Checks that humans reliably miss:
  4e-1 解析/实录重合度  — the analysis layer retelling the dialogue
  4e-2 解析篇幅        — analysis longer than half of its section's dialogue
  4e-3 单节总长        — grab-bag sections
  4e-4 长段落          — paragraphs over the mobile-readable limit
  4e-5 事实边界密度    — a boundary block in nearly every section

Only body sections (## with a ### 深度解析 / ### 语境与释义 child) are scanned.
Findings are warnings: the row prints ⚠️ with reasons; judgment stays human.

Usage:
  python check_readability.py path/to/doc.md
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

NGRAM = 8
OVERLAP_WARN = 0.20
ANALYSIS_RATIO_WARN = 0.5
ANALYSIS_FLOOR = 450
SECTION_WARN = 3500
PARAGRAPH_WARN = 300
BOUNDARY_MAX_SHARE = 0.6

ANALYSIS_HEADINGS = ("### 深度解析", "### 语境与释义")
DIALOGUE_HEADINGS = ("### 对谈实录", "### 原声交锋")
STOP_SECTIONS = ("## 延伸术语表", "## 自检报告", "## 关键语录与交锋时刻")
_STRIP = re.compile(r"[\s，。：；、？！「」『』（）()《》*>\-|]")


@dataclass
class Section:
    title: str
    text: str
    analysis: str = ""
    dialogue: str = ""
    issues: list[str] = field(default_factory=list)


def _cut(text: str, starts: tuple[str, ...], ends: tuple[str, ...]) -> str:
    for start in starts:
        if start in text:
            rest = text.split(start, 1)[1]
            for end in ends:
                if end in rest:
                    rest = rest.split(end, 1)[0]
            return rest
    return ""


def _grams(text: str) -> set[str]:
    s = _STRIP.sub("", text)
    return {s[i : i + NGRAM] for i in range(max(0, len(s) - NGRAM + 1))}


def split_sections(text: str) -> list[Section]:
    for stop in STOP_SECTIONS:
        if stop in text:
            text = text.split(stop, 1)[0]
    sections = []
    for chunk in re.split(r"\n(?=## )", text):
        if not chunk.startswith("## "):
            continue
        if not any(h in chunk for h in ANALYSIS_HEADINGS):
            continue
        sec = Section(title=chunk.splitlines()[0][3:].strip(), text=chunk)
        sec.analysis = _cut(chunk, ANALYSIS_HEADINGS, DIALOGUE_HEADINGS + ("### 未决问题",))
        sec.dialogue = _cut(chunk, DIALOGUE_HEADINGS, ("### 未决问题",))
        sections.append(sec)
    return sections


def _chars(text: str) -> int:
    return len(_STRIP.sub("", text))


def check(text: str) -> tuple[list[Section], list[str]]:
    sections = split_sections(text)
    global_issues: list[str] = []
    for sec in sections:
        a_len, d_len = _chars(sec.analysis), _chars(sec.dialogue)
        if sec.dialogue:
            gd = _grams(sec.dialogue)
            if gd:
                overlap = len(_grams(sec.analysis) & gd) / len(gd)
                if overlap > OVERLAP_WARN:
                    sec.issues.append(f"4e-1 解析与实录重合 {overlap:.0%}")
            if a_len > max(ANALYSIS_FLOOR, d_len * ANALYSIS_RATIO_WARN):
                sec.issues.append(f"4e-2 解析 {a_len} 字，超过实录 {d_len} 字的一半")
        total = _chars(sec.text)
        if total > SECTION_WARN:
            sec.issues.append(f"4e-3 单节 {total} 字")
        long_paras = [
            p for p in sec.text.split("\n\n") if _chars(p) > PARAGRAPH_WARN
        ]
        if long_paras:
            sec.issues.append(f"4e-4 {len(long_paras)} 段超过 {PARAGRAPH_WARN} 字")
    with_boundary = sum(1 for s in sections if "**事实边界**" in s.text)
    if sections and with_boundary / len(sections) > BOUNDARY_MAX_SHARE:
        global_issues.append(
            f"4e-5 事实边界 {with_boundary}/{len(sections)} 节，只标易误读处"
        )
    return sections, global_issues


def format_row(sections: list[Section], global_issues: list[str]) -> str:
    flagged = [s for s in sections if s.issues]
    status = "✅" if not flagged and not global_issues else "⚠️"
    if status == "✅":
        note = f"4e 通过（{len(sections)} 节）"
    else:
        parts = [f"{s.title[:12]}：{'；'.join(s.issues)}" for s in flagged[:4]]
        parts += global_issues
        more = f"；另 {len(flagged) - 4} 节" if len(flagged) > 4 else ""
        note = f"4e 待改 {len(flagged)}/{len(sections)} 节。" + " | ".join(parts) + more
    return f"| 可读性机检 | {status} | {note} |"


def main() -> int:
    parser = argparse.ArgumentParser(description="4e readability gate")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    sections, global_issues = check(args.path.read_text(encoding="utf-8"))
    print(format_row(sections, global_issues))
    for sec in sections:
        for issue in sec.issues:
            print(f"  {sec.title[:20]}: {issue}")
    for issue in global_issues:
        print(f"  {issue}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

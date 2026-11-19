#!/usr/bin/env python3
"""4e readability gate for content-structuring drafts.

Scans both layer orders: 对谈三层 (解析 → 实录) and 争辩型 (交锋 → 释义).

Checks that humans reliably miss:
  4e-1 解析/实录重合度  — the analysis layer retelling the dialogue (when d_len > 0)
  4e-2 解析篇幅        — longer than max(450, half the section's dialogue) (when d_len > 0)
  4e-3 单节总长        — grab-bag sections
  4e-4 长段落          — prose paragraphs over the mobile-readable limit
  4e-5 事实边界密度    — a boundary block in nearly every section
  + 核心洞察 >50 字、空壳实录标题、实录层内嵌图/视频/Mermaid 提示与原声占比机算参考值

Media URLs, standalone figure lines, HTML media tags, fenced code / Mermaid blocks,
and GFM table separators are stripped before character / overlap accounting so
source figures never cause false 4e-1 / 4e-2 / 4e-4 warnings.
"""

from __future__ import annotations

import argparse
import math
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
INSIGHT_WARN = 50
BOUNDARY_MAX_SHARE = 0.6

INSIGHT_HEADING = "### 核心洞察"
ANALYSIS_HEADINGS = ("### 深度解析", "### 语境与释义")
DIALOGUE_HEADINGS = ("### 对谈实录", "### 原声交锋")
ALL_SUBHEADINGS = (INSIGHT_HEADING, *ANALYSIS_HEADINGS, *DIALOGUE_HEADINGS, "### 未决问题")
STOP_SECTIONS = ("## 延伸术语表", "## 自检报告", "## 关键语录与交锋时刻")

_STRIP = re.compile(r"[\s，。：；、？！「」『』（）()《》*>\-|]")
_BALANCED_PARENS = r"\((?:[^()\n]|\([^()\n]*\))*\)"
_STANDALONE_IMAGE_RE = re.compile(rf"^\s*!\[[^\]\n]*\]{_BALANCED_PARENS}\s*$", flags=re.M)
_HTML_MEDIA_RE = re.compile(
    r"</?(?:img|video|source|figure|figcaption)\b[^>]*>",
    flags=re.IGNORECASE,
)
_FIGURE_CAPTION_RE = re.compile(
    r"^\s*\*(?:原文图|图\s*\d+|关键帧|[（(]据原片)[^*\n]*\*\s*$",
    flags=re.M,
)
_LINK_DEST_RE = re.compile(rf"(?<=\]){_BALANCED_PARENS}")
_RAW_URL_RE = re.compile(r"https?://\S+")
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s\-:|]+\|\s*$", flags=re.M)
_DIALOGUE_MEDIA_RE = re.compile(
    rf"!\[[^\]\n]*\]{_BALANCED_PARENS}|<(?:img|video)\b|^\s*(?:`{{3,}}|~{{3,}})\s*mermaid\b",
    flags=re.IGNORECASE | re.M,
)


@dataclass
class Section:
    title: str
    text: str
    insight: str = ""
    analysis: str = ""
    dialogue: str = ""
    has_dialogue_heading: bool = False
    issues: list[str] = field(default_factory=list)


def _strip_fences(text: str) -> str:
    """Remove fenced code / Mermaid blocks while preserving surrounding structure."""
    out: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        if fence is not None:
            closer = rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$"
            if re.match(closer, line):
                fence = None
            continue
        m = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence = m.group(1)
            continue
        out.append(line)
    return "\n".join(out)


def _strip_media_and_blocks(text: str) -> str:
    """Strip non-prose syntax (fences, figure lines, URLs, HTML media, table rules)."""
    out = _strip_fences(text)
    out = _STANDALONE_IMAGE_RE.sub("", out)
    out = _FIGURE_CAPTION_RE.sub("", out)
    out = _HTML_MEDIA_RE.sub("", out)
    out = _LINK_DEST_RE.sub("", out)
    out = _RAW_URL_RE.sub("", out)
    out = _TABLE_SEP_RE.sub("", out)
    return out


def _is_gfm_table_block(block: str) -> bool:
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    return lines[0].startswith("|") and bool(re.fullmatch(r"\|?[\s:\-|]+\|?", lines[1]))


def _prose_paragraphs(text: str) -> list[str]:
    """Extract reader-facing prose paragraphs, excluding fences, tables, and media blocks."""
    cleaned = _strip_fences(text)
    paras: list[str] = []
    for block in cleaned.split("\n\n"):
        s = block.strip()
        if not s:
            continue
        if _is_gfm_table_block(s):
            continue
        if _STANDALONE_IMAGE_RE.fullmatch(s) or _FIGURE_CAPTION_RE.fullmatch(s):
            continue
        if re.fullmatch(r"(?:<(?:img|video|source|figure|figcaption)\b[^>]*>\s*|</(?:video|figure|figcaption)>\s*)+", s, flags=re.I):
            continue
        paras.append(s)
    return paras


def _extract_subsections(chunk: str) -> dict[str, list[str]]:
    """Split a ## section chunk into ### subsection bodies in a fence-aware pass."""
    subs: dict[str, list[str]] = {}
    current: str | None = None
    fence: str | None = None
    for line in chunk.splitlines()[1:]:
        if fence is not None:
            closer = rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$"
            if re.match(closer, line):
                fence = None
            if current is not None:
                subs[current].append(line)
            continue
        m = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence = m.group(1)
            if current is not None:
                subs[current].append(line)
            continue
        if line.startswith("### "):
            current = line.strip()
            subs.setdefault(current, [])
            continue
        if current is not None:
            subs[current].append(line)
    return subs


def _grams(text: str) -> set[str]:
    s = _STRIP.sub("", _strip_media_and_blocks(text))
    return {s[i : i + NGRAM] for i in range(max(0, len(s) - NGRAM + 1))}


def split_sections(text: str) -> list[Section]:
    lines = text.splitlines()
    chunks: list[list[str]] = []
    cur: list[str] | None = None
    fence: str | None = None
    for line in lines:
        if fence is not None:
            closer = rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$"
            if re.match(closer, line):
                fence = None
            if cur is not None:
                cur.append(line)
            continue
        m = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence = m.group(1)
            if cur is not None:
                cur.append(line)
            continue
        if line.startswith("## "):
            if any(line.startswith(stop) for stop in STOP_SECTIONS):
                break
            if cur is not None:
                chunks.append(cur)
            cur = [line]
            continue
        if cur is not None:
            cur.append(line)
    if cur is not None:
        chunks.append(cur)

    sections: list[Section] = []
    for raw_lines in chunks:
        chunk = "\n".join(raw_lines)
        subs = _extract_subsections(chunk)
        if not any(h in subs for h in ANALYSIS_HEADINGS):
            continue
        sec = Section(title=raw_lines[0][3:].strip(), text=chunk)
        sec.insight = "\n".join(subs.get(INSIGHT_HEADING, []))
        sec.analysis = "\n".join(
            "\n".join(subs[h]) for h in ANALYSIS_HEADINGS if h in subs
        )
        sec.has_dialogue_heading = any(h in subs for h in DIALOGUE_HEADINGS)
        sec.dialogue = "\n".join(
            "\n".join(subs[h]) for h in DIALOGUE_HEADINGS if h in subs
        )
        sections.append(sec)
    return sections


def _chars(text: str) -> int:
    return len(_STRIP.sub("", _strip_media_and_blocks(text)))


def voice_share(sections: list[Section]) -> float | None:
    """Estimate voice share per language-and-gates.md: (dialogue + analysis quotes) / total."""
    d_total = sum(_chars(s.dialogue) for s in sections)
    a_total = sum(_chars(s.analysis) for s in sections)
    if d_total + a_total == 0:
        return None
    a_quotes = sum(
        _chars(q)
        for s in sections
        for q in re.findall(r"「([^」]+)」", _strip_media_and_blocks(s.analysis))
    )
    return min(1.0, (d_total + a_quotes) / (d_total + a_total))


def check(text: str) -> tuple[list[Section], list[str]]:
    sections = split_sections(text)
    global_issues: list[str] = []
    for sec in sections:
        i_len = _chars(sec.insight)
        a_len, d_len = _chars(sec.analysis), _chars(sec.dialogue)
        if i_len > INSIGHT_WARN:
            sec.issues.append(f"核心洞察 {i_len} 字，超过 {INSIGHT_WARN} 字上限")
        if sec.has_dialogue_heading and d_len == 0:
            sec.issues.append("空壳实录标题（无内容须整块省略 ### 对谈实录 / 原声交锋）")
        if sec.dialogue and _DIALOGUE_MEDIA_RE.search(sec.dialogue):
            sec.issues.append("实录层内嵌了图片/视频/Mermaid（须移至深度解析或语境与释义层）")
        if d_len > 0:
            gd = _grams(sec.dialogue)
            if gd:
                overlap = len(_grams(sec.analysis) & gd) / len(gd)
                if overlap > OVERLAP_WARN:
                    sec.issues.append(f"4e-1 解析与实录重合 {overlap:.0%}")
            half_i = math.floor(d_len * ANALYSIS_RATIO_WARN)
            ceiling_i = max(ANALYSIS_FLOOR, half_i)
            if a_len > ceiling_i:
                sec.issues.append(
                    f"4e-2 解析 {a_len} 字，超过上限 {ceiling_i} 字"
                    f"（实录一半 {half_i} 字，保底 {ANALYSIS_FLOOR} 字）"
                )
        total = _chars(sec.text)
        if total > SECTION_WARN:
            sec.issues.append(f"4e-3 单节 {total} 字")
        long_paras = [
            p for p in _prose_paragraphs(sec.text) if _chars(p) > PARAGRAPH_WARN
        ]
        if long_paras:
            sec.issues.append(f"4e-4 {len(long_paras)} 段超过 {PARAGRAPH_WARN} 字")
    with_boundary = sum(1 for s in sections if "**事实边界**" in _strip_fences(s.text))
    if sections and with_boundary / len(sections) > BOUNDARY_MAX_SHARE:
        global_issues.append(
            f"4e-5 事实边界 {with_boundary}/{len(sections)} 节，只标易误读处"
        )
    return sections, global_issues


def format_row(sections: list[Section], global_issues: list[str]) -> str:
    flagged = [s for s in sections if s.issues]
    status = "✅" if not flagged and not global_issues else "⚠️"
    share = voice_share(sections)
    share_note = f"；原声参考约 {share:.0%}" if share is not None else ""
    if status == "✅":
        note = f"4e 通过（{len(sections)} 节{share_note}）"
    else:
        parts = [f"{s.title[:12]}：{'；'.join(s.issues)}" for s in flagged[:4]]
        parts += global_issues
        more = f"；另 {len(flagged) - 4} 节" if len(flagged) > 4 else ""
        note = (
            f"4e 待改 {len(flagged)}/{len(sections)} 节{share_note}。"
            + " | ".join(parts)
            + more
        )
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

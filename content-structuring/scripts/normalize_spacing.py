#!/usr/bin/env python3
"""Normalize and validate content-structuring output Markdown spacing & structure (4d).

Checks & fixes:
- Remove --- between body ## sections (keep only structural ---)
- Collapse 3+ consecutive newlines outside code fences / <figure> blocks
- Ensure exactly one blank line between ## and next content
- Protect fenced code blocks (``` / ~~~) and <figure>...</figure> blocks verbatim
- Flag body ## section numbering prefixes (`## 1. …` / `## 1．…`), explicit `{#slug}`
  heading anchors, missing `### 核心洞察` first-child in 对谈三层 sections, and
  whitespace inside Markdown image URLs (which breaks downstream HTML rendering)

Usage:
  python normalize_spacing.py path/to/doc.md          # fix spacing in place
  python normalize_spacing.py path/to/doc.md --check  # exit 1 if violations
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Closing structural blocks: a --- immediately before these is legal (spec 4d-1).
STRUCTURAL_BEFORE_PREFIXES = (
    "关键语录",
    "延伸术语表",
    "自检报告",
)

MAX_HR = 6
SECTION_INDEX_RE = re.compile(r"^\d{1,2}[.．]\s+")
EXPLICIT_ANCHOR_RE = re.compile(r"\{#[^}\n]+\}\s*$")
IMAGE_SPACE_URL_RE = re.compile(r"!\[[^\]\n]*\]\(([^)\n]*\s+[^)\n]*)\)")
INLINE_CODE_RE = re.compile(r"`+[^`\n]+`+")


def _section_title(line: str) -> str | None:
    m = re.match(r"^## ([^#].*)$", line)
    return m.group(1).strip() if m else None


def _is_body_section(title: str) -> bool:
    skip = {"文章元数据", "核心导读", "目录"}
    return title not in skip and not title.startswith(STRUCTURAL_BEFORE_PREFIXES)


def _protected_mask(lines: list[str]) -> list[bool]:
    """Mark lines inside fenced code blocks (``` / ~~~) or <figure>...</figure>."""
    mask = [False] * len(lines)
    fence: str | None = None
    in_figure = False
    for i, line in enumerate(lines):
        if fence is not None:
            mask[i] = True
            closer = rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$"
            if re.match(closer, line):
                fence = None
            continue
        m_fence = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if m_fence and not (m_fence.group(1)[0] == "`" and "`" in m_fence.group(2)):
            fence = m_fence.group(1)
            mask[i] = True
            continue
        if in_figure:
            mask[i] = True
            if re.search(r"</figure\s*>", line, flags=re.IGNORECASE):
                in_figure = False
            continue
        if re.search(r"<figure\b", line, flags=re.IGNORECASE):
            mask[i] = True
            if not re.search(r"</figure\s*>", line, flags=re.IGNORECASE):
                in_figure = True
    return mask


def _is_strict_three_layer_doc(lines: list[str], protected: list[bool]) -> bool:
    """True when metadata declares 对谈三层 (excluding 多源合并 / 纯粹对话 / 专栏 overrides)."""
    for i, line in enumerate(lines):
        if protected[i]:
            continue
        if re.match(r"^\|\s*\*?\*?文稿结构\*?\*?\s*\|", line):
            if "对谈三层" in line and not any(
                k in line for k in ("多源合并", "纯粹对话", "专栏", "通用")
            ):
                return True
    return False


def _is_generic_or_multisource_doc(lines: list[str], protected: list[bool]) -> bool:
    for i, line in enumerate(lines):
        if protected[i]:
            continue
        if re.match(r"^\|\s*\*?\*?(?:文稿结构|内容来源)\*?\*?\s*\|", line):
            if any(k in line for k in ("通用模板", "多源合并", "专栏", "纯粹对话")):
                return True
    return False


def check(text: str) -> list[str]:
    issues: list[str] = []
    lines = text.splitlines()
    protected = _protected_mask(lines)

    hr_lines = [
        i + 1
        for i, ln in enumerate(lines)
        if not protected[i] and ln.strip() == "---"
    ]
    if len(hr_lines) > MAX_HR:
        issues.append(f"--- count {len(hr_lines)} > {MAX_HR} (lines {hr_lines})")

    masked_for_blanks = "\n".join(
        "__PROTECTED__" if protected[i] else ln for i, ln in enumerate(lines)
    )
    triples = [m.start() for m in re.finditer(r"\n\n\n+", masked_for_blanks)]
    if triples:
        issues.append(f"triple+ blank lines: {len(triples)} block(s)")

    strict_three_layer = _is_strict_three_layer_doc(lines, protected)
    generic_or_multi = _is_generic_or_multisource_doc(lines, protected)

    for i, line in enumerate(lines):
        if protected[i]:
            continue
        if re.match(r"^#{1,6}\s+", line) and EXPLICIT_ANCHOR_RE.search(line):
            issues.append(f"L{i + 1}: 标题禁带显式锚点标签 {{#...}}: {line.strip()[:50]}")

        no_code = INLINE_CODE_RE.sub("", line)
        m_img_space = IMAGE_SPACE_URL_RE.search(no_code)
        if m_img_space:
            issues.append(
                f"L{i + 1}: 图片地址含空白字符（会导致下游讲稿页断图）: {m_img_space.group(1)[:50]}"
            )

        title = _section_title(line)
        if not title or not _is_body_section(title):
            continue
        if SECTION_INDEX_RE.match(title):
            issues.append(
                f"L{i + 1} ## {title[:40]}: 正文节标题禁写序号前缀（顺序只写在目录）"
            )
        blanks = 0
        j = i + 1
        while j < len(lines) and not protected[j] and lines[j].strip() == "":
            blanks += 1
            j += 1
        if blanks != 1:
            issues.append(
                f"L{i + 1} ## {title[:40]}: {blanks} blank line(s) before next content (want 1)"
            )

        # Find end of this ## section to inspect its subsections
        sec_end = j
        while sec_end < len(lines):
            if not protected[sec_end] and _section_title(lines[sec_end]) is not None:
                break
            sec_end += 1
        sec_unprotected = [
            lines[k].strip() for k in range(i + 1, sec_end) if not protected[k]
        ]
        has_insight = "### 核心洞察" in sec_unprotected
        has_dialogue = "### 对谈实录" in sec_unprotected
        must_open_with_insight = strict_three_layer or (
            has_insight and has_dialogue and not generic_or_multi
        ) or (has_insight and not generic_or_multi and j < sec_end and not lines[j].strip().startswith("### "))
        if must_open_with_insight and j < sec_end:
            first_content = lines[j].strip()
            if first_content != "### 核心洞察":
                issues.append(
                    f"L{i + 1} ## {title[:40]}: 对谈三层节标题下首个内容须为 ### 核心洞察（禁写过渡段）"
                )

    # body --- between body sections only (after 目录's structural --- is allowed)
    past_toc = False
    seen_body = False
    for i, line in enumerate(lines):
        if protected[i]:
            continue
        title = _section_title(line)
        if title == "目录":
            past_toc = True
            seen_body = False
            continue
        if not past_toc:
            continue
        if title and title.startswith(STRUCTURAL_BEFORE_PREFIXES):
            break
        if title and _is_body_section(title):
            seen_body = True
            continue
        if line.strip() != "---":
            continue
        j = i + 1
        while j < len(lines) and (not protected[j]) and lines[j].strip() == "":
            j += 1
        nxt_title = (
            _section_title(lines[j])
            if j < len(lines) and not protected[j]
            else None
        )
        if seen_body and nxt_title and _is_body_section(nxt_title):
            issues.append(
                f"L{i + 1}: --- between body sections (before ## {nxt_title[:40]})"
            )

    return issues


def _protect_fences_and_figures(text: str) -> tuple[str, list[str]]:
    """Replace fenced code / multiline <figure> blocks with placeholders during blank-line collapse."""
    lines = text.splitlines()
    protected = _protected_mask(lines)
    saved: list[str] = []
    out_lines: list[str] = []
    i = 0
    while i < len(lines):
        if not protected[i]:
            out_lines.append(lines[i])
            i += 1
            continue
        j = i + 1
        while j < len(lines) and protected[j]:
            j += 1
        token = f"\x00PROTECTED_BLOCK_{len(saved)}\x00"
        saved.append("\n".join(lines[i:j]))
        out_lines.append(token)
        i = j
    return "\n".join(out_lines), saved


def normalize(text: str) -> str:
    lines = text.splitlines()
    protected = _protected_mask(lines)

    # Split into top-level ## sections (ignoring ## inside code fences / <figure>)
    blocks: list[list[str]] = []
    current: list[str] = []
    preamble: list[str] = []

    started = False
    for i, line in enumerate(lines):
        if not protected[i] and re.match(r"^## [^#]", line):
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
        rest_prot = _protected_mask(rest)
        while rest and not rest_prot[0] and rest[0].strip() == "":
            rest.pop(0)
            rest_prot.pop(0)
        while rest and not rest_prot[-1] and rest[-1].strip() == "":
            rest.pop()
            rest_prot.pop()
        while rest and not rest_prot[-1] and rest[-1].strip() == "---":
            rest.pop()
            rest_prot.pop()
            while rest and not rest_prot[-1] and rest[-1].strip() == "":
                rest.pop()
                rest_prot.pop()
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
            prev_title = _section_title(normalized_blocks[i - 1][0]) if i > 0 else None
            if prev_title == "目录" and (not result or result[-1] != "---"):
                result.extend(["", "---", ""])
        elif title.startswith(STRUCTURAL_BEFORE_PREFIXES):
            result.extend(["", "---", ""])

        result.extend(block)
        if i < len(normalized_blocks) - 1:
            if result[-1] != "":
                result.append("")

    out, saved = _protect_fences_and_figures("\n".join(result))
    out = re.sub(r"\n{3,}", "\n\n", out)
    if "## 核心导读" in out and "---" not in out.split("## 核心导读")[0]:
        out = out.replace("\n\n## 核心导读", "\n\n---\n\n## 核心导读", 1)
    for idx, block_str in enumerate(saved):
        out = out.replace(f"\x00PROTECTED_BLOCK_{idx}\x00", block_str)
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

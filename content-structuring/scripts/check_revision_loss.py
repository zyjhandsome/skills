#!/usr/bin/env python3
"""4f revision-loss check: compare a draft before and after an edit.

4e pushes the analysis layer shorter. Shortening is only safe when the removed
material already lives in the dialogue layer. This script lists what the new
draft no longer contains, so every item is either restored (usually into
对谈实录) or consciously dropped with a reason in 自检.

  4f-1 数字与专名     — numbers / Latin proper nouns present before, absent after
  4f-2 句级内容       — body sentences whose wording no longer appears anywhere
  4f-3 括注完整       — unclosed editor notes (stack-matched), orphan brackets, 「]」 as speech
  4f-4 括注被抬进实录  — with a before draft: note sentences reused as dialogue
  4f-5 媒体链接保真   — remote/local image or video URLs present before, absent after

Code fences (``` / ~~~) are excluded from bracket/dialogue checks so JSON or
code arrays never trigger false 4f-3 failures. Speaker turns support optional
timestamp / role parentheticals such as `**全名**（14:20）：「…」`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

NGRAM = 6
SENTENCE_COVERAGE = 0.5
MIN_SENTENCE = 14
RARE_PAIR = 3
MIN_DISTINCTIVE = 3

_BALANCED_PARENS = r"\((?:[^()\n]|\([^()\n]*\))*\)"
_STRIP = re.compile(r"[\s，。：；、？！「」『』（）()《》*>\-|—［］\[\]]")
_NUM = re.compile(r"\d[\d,\.]*\s*(?:万|亿|%|个|分钟|小时|年|月|人|倍|周|美元|天)?")
_NAME = re.compile(r"[A-Z][A-Za-z0-9\.\-]+(?: [A-Z0-9][A-Za-z0-9\.\-]+)*")
_SKIP_LINE = re.compile(r"^\s*(>\s*\*\*事实边界\*\*|###|##|\|[\s\-:|]+\|\s*$)")
_NOTE_OPEN = re.compile(r"[\[［]\s*编者注(?:[：:]|\s*)")
_SPEAKER_PREFIX = r"^\*\*[^*]+\*\*(?:\s*[（(][^）)\n]*[）)])?\s*[：:]"
_DIALOGUE = re.compile(rf"{_SPEAKER_PREFIX}\s*[「\"](.*)[」\"]\s*$")
_ORPHAN_CLOSE = re.compile(r"^\s*[\]］]+\s*$")
_FAKE_CLOSE_QUOTE = re.compile(rf"{_SPEAKER_PREFIX}\s*[「\"]\s*[\]］]+\s*[」\"]\s*$")
_MD_IMAGE_RE = re.compile(r"!\[[^\]\n]*\]\(\s*((?:[^()\s\n]|\([^()\n]*\))+)")
_HTML_MEDIA_SRC_RE = re.compile(
    r"<(?:img|video|source)\b[^>]*\bsrc=([\"'])([^\"']+)\1",
    flags=re.IGNORECASE,
)
_LINK_DEST_RE = re.compile(rf"(?<=\]){_BALANCED_PARENS}")


def _strip_fences(text: str) -> str:
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


def body_lines(text: str) -> list[tuple[int, str]]:
    """Unfenced body lines as (1-based file line number, text), after 目录 and before back matter."""
    lines = text.splitlines()
    fence_mask = [False] * len(lines)
    fence: str | None = None
    for idx, line in enumerate(lines):
        if fence is not None:
            fence_mask[idx] = True
            closer = rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$"
            if re.match(closer, line):
                fence = None
            continue
        m = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence = m.group(1)
            fence_mask[idx] = True

    start = 0
    end = len(lines)
    for i, line in enumerate(lines):
        if fence_mask[i]:
            continue
        if line.startswith("## 目录"):
            start = i + 1
        if line.startswith("## 延伸术语表") or line.startswith("## 自检报告"):
            end = min(end, i)
    return [(i + 1, lines[i]) for i in range(start, end) if not fence_mask[i]]


def body(text: str) -> str:
    lines = [line for _, line in body_lines(text)]
    if lines:
        return "\n".join(lines)
    raw = _strip_fences(text)
    raw = raw.split("## 延伸术语表")[0].split("## 自检报告")[0]
    return raw.split("## 目录", 1)[1] if "## 目录" in raw else raw


def media_urls(text: str) -> set[str]:
    """Extract all Markdown image and HTML media URLs/paths in the body."""
    b = body(text)
    urls = {m.group(1).strip() for m in _MD_IMAGE_RE.finditer(b)}
    urls |= {m.group(2).strip() for m in _HTML_MEDIA_SRC_RE.finditer(b)}
    return {u for u in urls if u}


def lost_media(before: str, after: str) -> list[str]:
    """4f-5. Media URLs present before an edit that disappeared afterwards."""
    return sorted(media_urls(before) - media_urls(after))


def facts(text: str) -> set[str]:
    b = _LINK_DEST_RE.sub("", body(text))
    found = {m.strip() for m in _NUM.findall(b)} | set(_NAME.findall(b))
    return {f for f in found if len(f) > 1}


def grams(text: str) -> set[str]:
    s = _STRIP.sub("", text)
    return {s[i : i + NGRAM] for i in range(max(0, len(s) - NGRAM + 1))}


def sentences(text: str) -> list[str]:
    out: list[str] = []
    cleaned_body = _LINK_DEST_RE.sub("", body(text))
    for line in cleaned_body.splitlines():
        if _SKIP_LINE.match(line):
            continue
        line = re.sub(_SPEAKER_PREFIX, "", line.strip())
        for s in re.split(r"[。！？]", line):
            s = s.strip(" 「」")
            if len(_STRIP.sub("", s)) >= MIN_SENTENCE:
                out.append(s)
    return out


def _bigrams(text: str) -> list[str]:
    s = _STRIP.sub("", text)
    return [s[i : i + 2] for i in range(max(0, len(s) - 1))]


def _scan_notes_in_para(para_text: str) -> tuple[list[str], bool]:
    """Stack-parse `[编者注：…]` inside a paragraph, accounting for nested links/images."""
    closed_spans: list[str] = []
    has_unclosed = False
    for m in _NOTE_OPEN.finditer(para_text):
        depth = 0
        idx = m.start()
        in_code = False
        closed_at: int | None = None
        while idx < len(para_text):
            ch = para_text[idx]
            if ch == "`":
                in_code = not in_code
                idx += 1
                continue
            if not in_code:
                if ch in "[［":
                    depth += 1
                elif ch in "]］":
                    depth -= 1
                    if depth == 0:
                        closed_at = idx
                        break
            idx += 1
        if closed_at is None:
            has_unclosed = True
        else:
            closed_spans.append(para_text[m.end() : closed_at].strip())
    return closed_spans, has_unclosed


def bracket_issues(text: str) -> list[str]:
    """4f-3. Editor notes are atomic: closed in the same paragraph, never spoken."""
    issues: list[str] = []
    rows = body_lines(text)
    for lineno, line in rows:
        if _FAKE_CLOSE_QUOTE.match(line.strip()) or _ORPHAN_CLOSE.match(line):
            issues.append(f"L{lineno} 收口括号被写成独立行或发言: {line.strip()[:60]}")

    i = 0
    while i < len(rows):
        lineno, line = rows[i]
        if not line.strip():
            i += 1
            continue
        para_lines = [(lineno, line)]
        j = i + 1
        while (
            j < len(rows)
            and rows[j][0] == rows[j - 1][0] + 1
            and rows[j][1].strip()
        ):
            para_lines.append(rows[j])
            j += 1
        para_text = "\n".join(text_line for _, text_line in para_lines)
        if _NOTE_OPEN.search(para_text):
            _, unclosed = _scan_notes_in_para(para_text)
            if unclosed:
                note_lineno, note_line = next(
                    (ln, tx) for ln, tx in para_lines if _NOTE_OPEN.search(tx)
                )
                issues.append(
                    f"L{note_lineno} 编者注未在同一段收口: {note_line.strip()[:60]}"
                )
        i = j
    return issues


def note_sentences(text: str) -> list[str]:
    out: list[str] = []
    for para in body(text).split("\n\n"):
        if not _NOTE_OPEN.search(para):
            continue
        spans, _ = _scan_notes_in_para(para)
        for span in spans:
            cleaned = _LINK_DEST_RE.sub("", span)
            for sentence in re.split(r"[。！？；，]", cleaned):
                sentence = sentence.strip(" 「」『』")
                if len(_STRIP.sub("", sentence)) >= 8:
                    out.append(sentence)
    return out


def lifted_notes(before: str, after: str) -> list[str]:
    """4f-4. Sentences that lived inside an editor note, then appear as dialogue."""
    spoken = []
    for _, line in body_lines(after):
        match = _DIALOGUE.match(line.strip())
        if match:
            spoken.append(_STRIP.sub("", match.group(1)))
    blob = "\n".join(spoken)
    hits: list[str] = []
    for sentence in note_sentences(before):
        key = _STRIP.sub("", sentence)
        if key and key in blob:
            hits.append(sentence)
    return hits


def compare(before: str, after: str) -> tuple[list[str], list[str]]:
    """Return (lost_facts, lost_sentences) between before and after drafts."""
    lost_facts = sorted(facts(before) - facts(after))
    before_body = _LINK_DEST_RE.sub("", body(before))
    after_body = _LINK_DEST_RE.sub("", body(after))
    before_pairs = _bigrams(before_body)
    freq: dict[str, int] = {}
    for p in before_pairs:
        freq[p] = freq.get(p, 0) + 1
    after_pairs = set(_bigrams(after_body))
    scored: list[tuple[float, str]] = []
    seen: set[str] = set()
    for s in sentences(before):
        distinctive = {p for p in _bigrams(s) if freq.get(p, 0) <= RARE_PAIR}
        if len(distinctive) < MIN_DISTINCTIVE:
            continue
        kept = len(distinctive & after_pairs) / len(distinctive)
        if kept < SENTENCE_COVERAGE:
            key = _STRIP.sub("", s)[:20]
            if key not in seen:
                seen.add(key)
                scored.append((kept, s))
    scored.sort(key=lambda item: item[0])
    return lost_facts, [s for _, s in scored]


def main() -> int:
    parser = argparse.ArgumentParser(description="4f revision-loss check")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()
    before = args.before.read_text(encoding="utf-8")
    after = args.after.read_text(encoding="utf-8")
    lost_facts, lost = compare(before, after)
    brackets = bracket_issues(after)
    lifted = lifted_notes(before, after)
    media_lost = lost_media(before, after)
    status = (
        "✅"
        if not lost_facts and not lost and not brackets and not lifted and not media_lost
        else "⚠️"
    )
    print(
        f"| 修订完整性 | {status} | 4f-1 缺失数字/专名 {len(lost_facts)} 项；"
        f"4f-2 找不到对应表述的句子 {len(lost)} 句；"
        f"4f-3 括注破损 {len(brackets)} 处；"
        f"4f-4 编者注被写成发言 {len(lifted)} 句；"
        f"4f-5 缺失媒体链接 {len(media_lost)} 处 |"
    )
    if lost_facts:
        print("\n4f-1 LOST_FACTS:", "、".join(lost_facts))
    if lost:
        print("\n4f-2 LOST_SENTENCES:")
        for s in lost[: args.limit]:
            print(f"  - {s[:100]}")
        if len(lost) > args.limit:
            print(f"  … 另 {len(lost) - args.limit} 句")
    if brackets:
        print("\n4f-3 BROKEN_NOTES:")
        for item in brackets:
            print(f"  - {item}")
    if lifted:
        print("\n4f-4 NOTE_AS_SPEECH:")
        for s in lifted[: args.limit]:
            print(f"  - {s[:100]}")
    if media_lost:
        print("\n4f-5 LOST_MEDIA:")
        for m in media_lost[: args.limit]:
            print(f"  - {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

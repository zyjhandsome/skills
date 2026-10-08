#!/usr/bin/env python3
"""4f revision-loss check: compare a draft before and after an edit.

4e pushes the analysis layer shorter. Shortening is only safe when the removed
material already lives in the dialogue layer. This script lists what the new
draft no longer contains, so every item is either restored (usually into
对谈实录) or consciously dropped with a reason in 自检.

  4f-1 数字与专名  — numbers / Latin proper nouns present before, absent after
  4f-2 句级内容    — body sentences whose wording no longer appears anywhere
  4f-3 括注完整    — unclosed editor notes, orphan brackets, 「]」 as speech
  4f-4 括注被抬进实录 — with a before draft: note sentences reused as dialogue

Only the body is compared (after 目录, before 延伸术语表). Matching is literal,
so paraphrases still show up. The list is sorted by how much of each sentence
survived, lowest first: the top of the list is where real losses sit. Treat it
as a triage queue — read from the top until items are clearly just rephrased.

Usage:
  python check_revision_loss.py before.md after.md
  python check_revision_loss.py before.md after.md --limit 80
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
_STRIP = re.compile(r"[\s，。：；、？！「」『』（）()《》*>\-|—［］\[\]]")
_NUM = re.compile(r"\d[\d,\.]*\s*(?:万|亿|%|个|分钟|小时|年|月|人|倍|周|美元|天)?")
_NAME = re.compile(r"[A-Z][A-Za-z0-9\.\-]+(?: [A-Z0-9][A-Za-z0-9\.\-]+)*")
_SKIP_LINE = re.compile(r"^\s*(>\s*\*\*事实边界\*\*|###|##|\|)")
_NOTE_OPEN = re.compile(r"[\[［]\s*编者注")
_NOTE_SPAN = re.compile(r"[\[［]\s*编者注[：:](.*?)[\]］]", re.S)
_DIALOGUE = re.compile(r"^\*\*[^*]+\*\*：「(.*)」\s*$")
_ORPHAN_CLOSE = re.compile(r"^\s*[\]］]+\s*$")
_FAKE_CLOSE_QUOTE = re.compile(r"^\*\*[^*]+\*\*：「\s*[\]］]+\s*」\s*$")


def body_lines(text: str) -> list[tuple[int, str]]:
    """Body lines as (1-based file line number, text), after 目录 and before back matter."""
    lines = text.splitlines()
    start = 0
    end = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("## 目录"):
            start = i + 1
        if line.startswith("## 延伸术语表") or line.startswith("## 自检报告"):
            end = min(end, i)
    return [(i + 1, lines[i]) for i in range(start, end)]


def body(text: str) -> str:
    text = text.split("## 延伸术语表")[0].split("## 自检报告")[0]
    return text.split("## 目录", 1)[1] if "## 目录" in text else text


def facts(text: str) -> set[str]:
    b = body(text)
    found = {m.strip() for m in _NUM.findall(b)} | set(_NAME.findall(b))
    return {f for f in found if len(f) > 1}


def grams(text: str) -> set[str]:
    s = _STRIP.sub("", text)
    return {s[i : i + NGRAM] for i in range(max(0, len(s) - NGRAM + 1))}


def sentences(text: str) -> list[str]:
    out: list[str] = []
    for line in body(text).splitlines():
        if _SKIP_LINE.match(line):
            continue
        line = re.sub(r"^\*\*[^*]+\*\*：", "", line.strip())
        for s in re.split(r"[。！？]", line):
            s = s.strip(" 「」")
            if len(_STRIP.sub("", s)) >= MIN_SENTENCE:
                out.append(s)
    return out


def _bigrams(text: str) -> list[str]:
    s = _STRIP.sub("", text)
    return [s[i : i + 2] for i in range(max(0, len(s) - 1))]


def bracket_issues(text: str) -> list[str]:
    """4f-3. Editor notes are atomic: closed in the same paragraph, never spoken."""
    issues: list[str] = []
    rows = body_lines(text)
    i = 0
    while i < len(rows):
        lineno, line = rows[i]
        if _FAKE_CLOSE_QUOTE.match(line.strip()) or _ORPHAN_CLOSE.match(line):
            issues.append(f"L{lineno} 收口括号被写成独立行或发言: {line.strip()[:60]}")
        if _NOTE_OPEN.search(line):
            para = [line]
            j = i + 1
            while j < len(rows) and rows[j][1].strip():
                para.append(rows[j][1])
                j += 1
            if not re.search(r"[\]］]", "\n".join(para)):
                issues.append(f"L{lineno} 编者注未在同一段收口: {line.strip()[:60]}")
        i += 1
    return issues


def note_sentences(text: str) -> list[str]:
    out: list[str] = []
    for match in _NOTE_SPAN.finditer(body(text)):
        for sentence in re.split(r"[。！？]", match.group(1)):
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
    """A sentence counts as lost when most of its *distinctive* character pairs
    (rare in the before-draft, so not filler) are gone from the after-draft.
    Paraphrases and the analysis/dialogue duplicates that a 4e edit removes on
    purpose keep their distinctive pairs, so they do not show up."""
    lost_facts = sorted(facts(before) - facts(after))
    before_pairs = _bigrams(body(before))
    freq: dict[str, int] = {}
    for p in before_pairs:
        freq[p] = freq.get(p, 0) + 1
    after_pairs = set(_bigrams(body(after)))
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
    status = "✅" if not lost_facts and not lost and not brackets and not lifted else "⚠️"
    print(
        f"| 修订完整性 | {status} | 4f-1 缺失数字/专名 {len(lost_facts)} 项；"
        f"4f-2 找不到对应表述的句子 {len(lost)} 句；"
        f"4f-3 括注破损 {len(brackets)} 处；4f-4 编者注被写成发言 {len(lifted)} 句。"
        f"真丢失补回讲者原话；括注收口或改成事实边界，不要写进实录 |"
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
    return 0


if __name__ == "__main__":
    sys.exit(main())

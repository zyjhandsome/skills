#!/usr/bin/env python3
"""4c lexicon + consecutive-English scan for content-structuring outputs.

- Loads the FULL unified lexicon from references/lexicon.txt (single source);
  the spec reference set keeps no word-list copy
- 4c-1: greps blocking / contextual patterns against narrative-ish Markdown
- 4c-2: open-set scan for ≥2 consecutive lowercase-bearing English words inside
  Chinese sentences (catches code-switching that no word list can enumerate)
- Ignores metadata「原标题」cells, glossary + self-check sections, code fences,
  inline code, ordinary Markdown links, bilingual「原文：…」notes, ASR markers,
  and HTML media tag attributes (<img/video/source/figure/figcaption>)
- Masks image destination URLs (including one level of balanced parentheses)
  while keeping Chinese image alt descriptions inside ![alt](url) in scope
- Ignores first-occurrence parentheticals: 中文（English） / （English）
- Ignores allowlisted proper-noun phrases (Skill Creator, Claude Code, ...)
- Reports likely Chinese over-translation of AI/DevTools labels for human review
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LEXICON_PATH = Path(__file__).resolve().parents[1] / "references" / "lexicon.txt"


def _wrap_word_boundaries(pattern: str) -> str:
    """Add \\b guards when the pattern starts/ends with word characters."""
    prefix = r"\b" if re.match(r"\w", pattern) else ""
    suffix = r"\b" if re.search(r"\w$", pattern) else ""
    return f"{prefix}(?:{pattern}){suffix}"


def _load_lexicon(path: Path = LEXICON_PATH) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " #" in line:
            line = line.split(" #", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return sections


_SECTIONS = _load_lexicon()

# Bare narrative English: actionable 4c-1 failures.
LEXICON = [_wrap_word_boundaries(p) for p in _SECTIONS.get("blocking", [])]

# Ambiguous community terms (case-insensitive) + case-sensitive industry acronyms.
CONTEXTUAL_ENGLISH_REVIEW = [
    _wrap_word_boundaries(p) for p in _SECTIONS.get("contextual", [])
]
CONTEXTUAL_CS_REVIEW = [
    _wrap_word_boundaries(p)
    for p in _SECTIONS.get("contextual-case-sensitive", [])
]

# Likely cases where an English AI/DevTools label may have been translated away.
# Avoid matching ordinary Chinese figure references such as「如上图，图 2」or「架构图、工作流」.
OVER_TRANSLATION_REVIEW = [
    r"(?:代理|智能体)\s*(?:循环|图)",
    r"先是\s*(?:代理|智能体).{0,24}?循环.{0,24}?图",
    r"循环[、，,]\s*(?:图(?!\s*[0-9一二三四五六七八九十])|工作流)",
    r"(?<![\u4e00-\u9fff])图[、，,]\s*工作流",
    r"(?:技能创建者|电脑使用|计算机使用|子代理)",
    r"爱的是\s*(?:\*\*)?(?:建造|构建)(?:\*\*)?",
    r"(?:认同|身份).{0,12}?(?:建造者|构建者)",
]

# Proper-noun / product spans: if hit is inside these, ignore.
ALLOW_PHRASES = [_wrap_word_boundaries(p) for p in _SECTIONS.get("allow", [])]

# Official names whose capitalization matters. Lowercase generic uses remain actionable.
CASE_SENSITIVE_ALLOW_PHRASES = [
    _wrap_word_boundaries(p) for p in _SECTIONS.get("allow-case-sensitive", [])
]

_BALANCED_PARENS = r"\((?:[^()\n]|\([^()\n]*\))*\)"
# Strip parenthetical Latin/ASCII terms: （dogfooding） or (dogfooding)
PAREN_EN = re.compile(
    r"[（(]\s*[A-Za-z][A-Za-z0-9_./+#&-]*(?:\s+[A-Za-z][A-Za-z0-9_./+#&-]*)*\s*[）)]"
)
# Destination part of ![alt](url) or [label](url), supporting balanced parentheses.
MARKDOWN_LINK_DEST = re.compile(rf"(?<=\]){_BALANCED_PARENS}")
RAW_URL = re.compile(r"https?://\S+")
# Whole ordinary markdown links (NOT images): English article titles in 引用/图注原链 are archive layer.
MARKDOWN_LINK = re.compile(rf"(?<!!)\[[^\]\n]*\]{_BALANCED_PARENS}")
INLINE_CODE = re.compile(r"`+[^`\n]+`+")
# Archive layer inside a body line: bilingual 原文/原片标题 side notes, ASR/blind-spot markers, HTML media tags.
BILINGUAL_SIDE = re.compile(r"[（(]\s*(?:原文|原片标题)[：:][^）)\n]*[）)]")
ASR_MARKER = re.compile(r"[\[［]\s*(?:ASR|说话人待核|视觉盲区)[^\]］\n]*[\]］]")
HTML_MEDIA_TAG = re.compile(
    r"</?(?:img|video|source|figure|figcaption)\b[^>]*>",
    flags=re.IGNORECASE,
)


def _blank_preserve_newlines(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def _mask_archive_spans(text: str) -> str:
    """Blank spans that legitimately keep English BEFORE link-dest masking."""
    out = text
    for pat in (INLINE_CODE, BILINGUAL_SIDE, ASR_MARKER, HTML_MEDIA_TAG, MARKDOWN_LINK):
        out = pat.sub(_blank_preserve_newlines, out)
    return out


def _mask_allowed(text: str) -> str:
    out = text
    out = MARKDOWN_LINK_DEST.sub(_blank_preserve_newlines, out)
    out = RAW_URL.sub(_blank_preserve_newlines, out)
    for pat in CASE_SENSITIVE_ALLOW_PHRASES:
        out = re.sub(pat, _blank_preserve_newlines, out)
    for pat in ALLOW_PHRASES:
        out = re.sub(pat, _blank_preserve_newlines, out, flags=re.IGNORECASE)
    out = PAREN_EN.sub(_blank_preserve_newlines, out)
    return out


def _strip_excluded_regions(text: str) -> str:
    """Drop archive/meta regions outside 4c scope while keeping 1-based line numbers."""
    lines = text.splitlines()
    kept: list[str] = []
    skipping = False
    fence: str | None = None
    for line in lines:
        if fence is not None:
            closer = rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$"
            if re.match(closer, line):
                fence = None
            kept.append("")
            continue
        m_fence = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if m_fence and not (m_fence.group(1)[0] == "`" and "`" in m_fence.group(2)):
            fence = m_fence.group(1)
            kept.append("")
            continue
        title_m = re.match(r"^##\s+(.+)$", line)
        if title_m:
            title = title_m.group(1).strip()
            skipping = title.startswith("延伸术语表") or title.startswith("自检报告")
            kept.append("" if skipping else line)
            continue
        if skipping:
            kept.append("")
            continue
        if re.match(r"^##\s+文章元数据", line):
            kept.append(line)
            continue
        # Drop 原标题 row content (archive layer)
        if re.match(r"^\|\s*\*?\*?原标题\*?\*?\s*\|", line):
            kept.append("")
            continue
        kept.append(line)
    return "\n".join(kept)


def _prepare_body(text: str) -> str:
    return _mask_allowed(_mask_archive_spans(_strip_excluded_regions(text)))


def scan(text: str) -> list[dict]:
    body = _prepare_body(text)
    hits: list[dict] = []
    for pat in LEXICON:
        for m in re.finditer(pat, body, flags=re.IGNORECASE):
            line_no = body.count("\n", 0, m.start()) + 1
            hits.append(
                {
                    "pattern": pat,
                    "match": m.group(0),
                    "line": line_no,
                }
            )
    return hits


def scan_contextual_english(text: str) -> list[dict]:
    """Return non-blocking English terms whose treatment depends on source intent."""
    body = _prepare_body(text)
    hints: list[dict] = []
    for pat in CONTEXTUAL_ENGLISH_REVIEW:
        for m in re.finditer(pat, body, flags=re.IGNORECASE):
            hints.append(
                {
                    "pattern": pat,
                    "match": m.group(0),
                    "line": body.count("\n", 0, m.start()) + 1,
                }
            )
    for pat in CONTEXTUAL_CS_REVIEW:
        for m in re.finditer(pat, body):
            hints.append(
                {
                    "pattern": pat,
                    "match": m.group(0),
                    "line": body.count("\n", 0, m.start()) + 1,
                }
            )
    return hints


CJK = re.compile(r"[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]")
_EN_WORD = r"[A-Za-z][A-Za-z0-9'’&./+-]*"
CONSECUTIVE_EN = re.compile(rf"{_EN_WORD}(?:[ \t]+{_EN_WORD})+")


def scan_consecutive_english(text: str) -> list[dict]:
    """4c-2 open-set scan: ≥2 consecutive English words inside a Chinese sentence.

    Title-Case / ALL-CAPS spans are skipped as proper-noun chains (person names,
    programme names, product names). A span is reported only when at least one word
    is lowercase — that is the shape ordinary code-switching takes (`go to market
    motion`, `still hesitant`). Reported for review, not auto-failed.
    """
    body = _prepare_body(text)
    hits: list[dict] = []
    for line_no, line in enumerate(body.splitlines(), start=1):
        if not CJK.search(line):
            continue
        for m in CONSECUTIVE_EN.finditer(line):
            words = m.group(0).split()
            if all(w[:1].isupper() for w in words):
                continue
            hits.append({"match": m.group(0), "line": line_no, "words": len(words)})
    return hits


def scan_over_translation(text: str) -> list[dict]:
    """Return non-blocking hints for Chinese text that may hide field-native labels."""
    body = _strip_excluded_regions(text)
    hints: list[dict] = []
    english_label = re.compile(
        r"\b(?:Builder|Agent(?:ic)? Loop|Agent Graph|Loop|Graph|Workflow|"
        r"Skill Creator|Computer Use|Subagent)\b",
        flags=re.IGNORECASE,
    )
    for pat in OVER_TRANSLATION_REVIEW:
        for m in re.finditer(pat, body, flags=re.IGNORECASE):
            line_start = body.rfind("\n", 0, m.start()) + 1
            line_end = body.find("\n", m.end())
            if line_end < 0:
                line_end = len(body)
            line = body[line_start:line_end]
            if english_label.search(line):
                continue
            hints.append(
                {
                    "pattern": pat,
                    "match": m.group(0),
                    "line": body.count("\n", 0, m.start()) + 1,
                }
            )
    return hints


def main() -> int:
    parser = argparse.ArgumentParser(description="4c lexicon + consecutive-English scan")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--fail-on-consecutive",
        action="store_true",
        help="exit 1 when 4c-2 candidates remain (default: report only)",
    )
    args = parser.parse_args()
    text = args.path.read_text(encoding="utf-8")
    hits = scan(text)
    contextual = scan_contextual_english(text)
    consecutive = scan_consecutive_english(text)
    review = scan_over_translation(text)
    if args.json:
        print(
            json.dumps(
                {
                    "hits": hits,
                    "count": len(hits),
                    "consecutive_english": consecutive,
                    "consecutive_count": len(consecutive),
                    "contextual_english_review": contextual,
                    "contextual_review_count": len(contextual),
                    "over_translation_review": review,
                    "review_count": len(review),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if not hits:
            print("OK: no actionable 4c-1 lexicon hits (parentheticals/allowlist excluded)")
        else:
            print(f"ACTIONABLE_HITS: {len(hits)}")
            for h in hits:
                print(f"  L{h['line']}: {h['match']}  (pattern {h['pattern']})")
        if consecutive:
            print(
                f"CONSECUTIVE_ENGLISH_4C2: {len(consecutive)} "
                "(translate, or promote to proper-noun layer / lexicon [allow])"
            )
            for h in consecutive:
                print(f"  L{h['line']}: {h['match']}")
        else:
            print("OK: no 4c-2 consecutive-English candidates (Title-Case spans excluded)")
        if review:
            print(f"OVER_TRANSLATION_REVIEW: {len(review)} (non-blocking; compare with source)")
            for h in review:
                print(f"  L{h['line']}: {h['match']}  (pattern {h['pattern']})")
        if contextual:
            print(f"CONTEXTUAL_ENGLISH_REVIEW: {len(contextual)} (non-blocking; judge term role)")
            for h in contextual:
                print(f"  L{h['line']}: {h['match']}  (pattern {h['pattern']})")
        print(
            "Note: Title-Case spans are assumed proper nouns, so the concept-label pass "
            "still needs eyes; see references/over-translation-guard.md."
        )
    if hits:
        return 1
    if consecutive and args.fail_on_consecutive:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

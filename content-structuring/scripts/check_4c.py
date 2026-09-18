#!/usr/bin/env python3
"""4c unified-lexicon scan for content-structuring outputs (spec v5.33).

- Loads the FULL unified lexicon from references/lexicon.txt (single source);
  the spec reference set (see references/language-and-gates.md) keeps no word-list copy
- Greps blocking / contextual patterns against narrative-ish Markdown
- Ignores metadata「原标题」cells, glossary proper-noun column heuristically
- Ignores first-occurrence parentheticals: 中文（English） / （English）
- Ignores allowlisted proper-noun phrases (Skill Creator, Claude Code, ...)
- Reports likely Chinese over-translation of AI/DevTools labels for human review

Usage:
  python check_4c.py path/to/doc.md
  python check_4c.py path/to/doc.md --json

Exit 0 if no *actionable* hits; 1 if bare lexicon hits remain.
Does NOT replace 4c-2 human pass for ≥2 consecutive English words or term intent.
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

# Ambiguous community terms: they may be unwanted English residue or intentional
# technical labels. Report them for source-aware review; never auto-fail on the word.
CONTEXTUAL_ENGLISH_REVIEW = [
    _wrap_word_boundaries(p) for p in _SECTIONS.get("contextual", [])
]

# Likely cases where an English AI/DevTools label may have been translated away.
# These are review hints, not automatic failures: Chinese wording can be correct in
# ordinary prose, while the source may instead be naming a taxonomy or identity.
OVER_TRANSLATION_REVIEW = [
    r"(?:代理|智能体)\s*(?:循环|图)",
    r"先是\s*(?:代理|智能体).{0,24}?循环.{0,24}?图",
    r"(?:循环|图)[、，,]\s*(?:图|工作流)",
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

# Strip parenthetical Latin/ASCII terms: （dogfooding） or (dogfooding)
PAREN_EN = re.compile(
    r"[（(]\s*[A-Za-z][A-Za-z0-9_./+#&-]*(?:\s+[A-Za-z][A-Za-z0-9_./+#&-]*)*\s*[）)]"
)
MARKDOWN_LINK_DEST = re.compile(r"(?<=\])\([^\n)]*\)")
RAW_URL = re.compile(r"https?://\S+")


def _mask_allowed(text: str) -> str:
    out = text
    out = MARKDOWN_LINK_DEST.sub(lambda m: " " * len(m.group(0)), out)
    out = RAW_URL.sub(lambda m: " " * len(m.group(0)), out)
    for pat in CASE_SENSITIVE_ALLOW_PHRASES:
        out = re.sub(pat, lambda m: " " * len(m.group(0)), out)
    for pat in ALLOW_PHRASES:
        out = re.sub(pat, lambda m: " " * len(m.group(0)), out, flags=re.IGNORECASE)
    out = PAREN_EN.sub(lambda m: " " * len(m.group(0)), out)
    return out


def _strip_excluded_regions(text: str) -> str:
    """Drop archive/meta regions outside 4c scope (language-and-gates.md「4c 检索范围」)."""
    lines = text.splitlines()
    kept: list[str] = []
    skipping = False
    in_fence = False
    for line in lines:
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            kept.append("")
            continue
        if in_fence:
            kept.append("")
            continue
        title_m = re.match(r"^##\s+(.+)$", line)
        if title_m:
            title = title_m.group(1).strip()
            # 原标题 row handled below; skip whole glossary + self-check (备注常提及词库词)
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


def scan(text: str) -> list[dict]:
    body = _mask_allowed(_strip_excluded_regions(text))
    hits: list[dict] = []
    for pat in LEXICON:
        for m in re.finditer(pat, body, flags=re.IGNORECASE):
            # line number in original is approximate after masks; report span text
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
    body = _mask_allowed(_strip_excluded_regions(text))
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
    return hints


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
            # A same-line English label means the Chinese is probably an explanation.
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
    parser = argparse.ArgumentParser(description="4c lexicon helper scan")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    text = args.path.read_text(encoding="utf-8")
    hits = scan(text)
    contextual = scan_contextual_english(text)
    review = scan_over_translation(text)
    if args.json:
        print(
            json.dumps(
                {
                    "hits": hits,
                    "count": len(hits),
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
            print("OK: no actionable 4c lexicon hits (parentheticals/allowlist excluded)")
        else:
            print(f"ACTIONABLE_HITS: {len(hits)}")
            for h in hits:
                print(f"  L{h['line']}: {h['match']}  (pattern {h['pattern']})")
        if review:
            print(f"OVER_TRANSLATION_REVIEW: {len(review)} (non-blocking; compare with source)")
            for h in review:
                print(f"  L{h['line']}: {h['match']}  (pattern {h['pattern']})")
        if contextual:
            print(f"CONTEXTUAL_ENGLISH_REVIEW: {len(contextual)} (non-blocking; judge term role)")
            for h in contextual:
                print(f"  L{h['line']}: {h['match']}  (pattern {h['pattern']})")
        print(
            "Note: 4c-2 consecutive-English and concept-label passes are still required; "
            "see references/over-translation-guard.md."
        )
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Lightweight 4c lexicon scan for content-structuring outputs (spec v5.29).

- Greps the unified lexicon against narrative-ish Markdown
- Ignores metadata「原标题」cells, glossary proper-noun column heuristically
- Ignores first-occurrence parentheticals: 中文（English） / （English）
- Ignores allowlisted proper-noun phrases (Skill Creator, Claude Code, ...)

Usage:
  python check_4c.py path/to/doc.md
  python check_4c.py path/to/doc.md --json

Exit 0 if no *actionable* hits; 1 if bare lexicon hits remain.
Does NOT replace 4c-2 human pass for ≥2 consecutive English words.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Keep in sync with high-signal terms in spec「英文源素材高频夹写词」+ AI/DevTools 簇.
# Full alternation list is large; this script focuses on high-FP / high-value stems.
LEXICON = [
    r"super bullish",
    r"operationalize",
    r"dogfooding?",
    r"oneshot",
    r"one-shot",
    r"flaky",
    r"\bbuilder\b",
    r"\brefine\b",
    r"\bholistic\b",
    r"\bcontext\b",
    r"\bfeature\b",
    r"\bship\b",
    r"\bdemo\b",
    r"\bonboarding\b",
    r"\broadmap\b",
    r"\bhook\b",
    r"\bcheckout\b",
    r"\bspawn\b",
    r"\bsubprocess\b",
    r"\bwrapper\b",
    r"\bstandup\b",
    r"\bharness\b",
    r"\bsandbox\b",
    r"\bvibe\b",
    r"\bcraft\b",
    r"mass unemployment",
]

# Proper-noun / product spans: if hit is inside these, ignore.
ALLOW_PHRASES = [
    r"Skill Creator",
    r"Agent Skills?",
    r"\bSkills?\b",  # Cursor/Claude Skill package name (see over-translation-guard)
    r"Claude Code",
    r"Computer Use",
    r"Model Context Protocol",
    r"\bMCP\b",
    r"\bHooks\b",
    r"feature flag",
    r"context window",
    r"git checkout",
    r"Demo Day",
    r"Custom GPTs?",
    r"\bComposer\b",
    r"\bCanvas\b",
    r"\bSubagents?\b",
    r"\bRAG\b",  # allowed abbreviation; first-use Chinese expansion is a separate manual gate
]

# Official names whose capitalization matters. Lowercase generic uses remain actionable.
CASE_SENSITIVE_ALLOW_PHRASES = [
    r"\bHarness\b",
    r"\bCraft Conference\b",
    r"\bBehind the Craft\b",
    r"\bCraft Ventures\b",
    r"\bBeyond Vibe Coding\b",
    r"\bHow to build your own harness\b",
    r"\b(?:Uber|OpenAI) Agent Builder\b",
]

# Strip parenthetical Latin/ASCII terms: （dogfooding） or (dogfooding)
PAREN_EN = re.compile(
    r"[（(]\s*[A-Za-z][A-Za-z0-9_./+#-]*(?:\s+[A-Za-z][A-Za-z0-9_./+#-]*)*\s*[）)]"
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
    """Drop archive/meta regions outside 4c narrative scope (spec 4c 检索范围)."""
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


def main() -> int:
    parser = argparse.ArgumentParser(description="4c lexicon helper scan")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    text = args.path.read_text(encoding="utf-8")
    hits = scan(text)
    if args.json:
        print(json.dumps({"hits": hits, "count": len(hits)}, ensure_ascii=False, indent=2))
    else:
        if not hits:
            print("OK: no actionable 4c lexicon hits (parentheticals/allowlist excluded)")
            return 0
        print(f"ACTIONABLE_HITS: {len(hits)}")
        for h in hits:
            print(f"  L{h['line']}: {h['match']}  (pattern {h['pattern']})")
        print(
            "Note: 4c-2 consecutive-English pass still required; "
            "see references/over-translation-guard.md for Skill/Creator etc."
        )
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())

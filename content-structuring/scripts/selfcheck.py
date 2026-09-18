#!/usr/bin/env python3
"""Machine-fill 4c/4d rows for a content-structuring draft (spec v5.34).

Prints Markdown table rows the agent can paste into「自检报告」. Judgment rows
(语义保真 / 声纹 / 事实状态 / 信息覆盖抽样) stay human-written.

Usage:
  python selfcheck.py path/to/doc.md
  python selfcheck.py path/to/doc.md --json

Exit 1 if 4c-1 actionable hits remain or 4d fails. 4c-2 consecutive hits are
listed for review and do not fail the process by themselves.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import check_4c  # noqa: E402
import normalize_spacing  # noqa: E402


def collect(text: str) -> dict:
    hits = check_4c.scan(text)
    consecutive = check_4c.scan_consecutive_english(text)
    contextual = check_4c.scan_contextual_english(text)
    over = check_4c.scan_over_translation(text)
    spacing = normalize_spacing.check(text)
    return {
        "actionable": hits,
        "actionable_count": len(hits),
        "consecutive": consecutive,
        "consecutive_count": len(consecutive),
        "contextual": contextual,
        "contextual_count": len(contextual),
        "over_translation": over,
        "over_translation_count": len(over),
        "spacing": spacing,
        "spacing_count": len(spacing),
    }


def _sample_matches(items: list[dict], key: str = "match", limit: int = 3) -> str:
    seen: list[str] = []
    for item in items:
        value = str(item.get(key, "")).strip()
        if value and value not in seen:
            seen.append(value)
        if len(seen) >= limit:
            break
    return "、".join(seen) if seen else "无"


def format_rows(report: dict) -> str:
    actionable_n = report["actionable_count"]
    c4_status = "✅" if actionable_n == 0 and report["consecutive_count"] == 0 else "⚠️"
    d4_status = "✅" if report["spacing_count"] == 0 else "⚠️"
    samples = _sample_matches(report["actionable"])
    consec = _sample_matches(report["consecutive"])
    spacing_note = (
        "4d 通过"
        if report["spacing_count"] == 0
        else "；".join(report["spacing"][:3])
    )
    narrative = (
        f"4c-1 actionable={actionable_n}"
        f"（样例：{samples}）；"
        f"4c-2 consecutive={report['consecutive_count']}"
        f"（样例：{consec}）；"
        f"contextual={report['contextual_count']}；"
        f"over-translation={report['over_translation_count']}。"
        "4c-2/多义/过译须对照来源核实后才能把本行标 ✅。"
    )
    return (
        f"| 正文中文叙事 | {c4_status} | {narrative} |\n"
        f"| 纯净排版 | {d4_status} | {spacing_note} |"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fill 4c/4d self-check rows from scripts")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    text = args.path.read_text(encoding="utf-8")
    report = collect(text)
    if args.json:
        print(
            json.dumps(
                {
                    "actionable_count": report["actionable_count"],
                    "consecutive_count": report["consecutive_count"],
                    "contextual_count": report["contextual_count"],
                    "over_translation_count": report["over_translation_count"],
                    "spacing": report["spacing"],
                    "rows": format_rows(report),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(format_rows(report))
        if report["actionable"]:
            print("\n4c-1 ACTIONABLE_HITS:")
            for hit in report["actionable"][:8]:
                print(f"  L{hit['line']}: {hit['match']}")
        if report["consecutive"]:
            print("\n4c-2 CONSECUTIVE_ENGLISH:")
            for hit in report["consecutive"][:8]:
                print(f"  L{hit['line']}: {hit['match']}")
        if report["spacing"]:
            print("\n4d issues:")
            for issue in report["spacing"]:
                print(f"  {issue}")
    if report["actionable_count"] or report["spacing_count"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

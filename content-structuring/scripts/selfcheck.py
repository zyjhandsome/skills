#!/usr/bin/env python3
"""Machine-fill 4c/4d/4e/4f-3/判断行证据 rows for a content-structuring draft.

Prints contiguous Markdown table rows at the top so the agent can paste them
directly into「自检报告」, followed by diagnostic details. Judgment rows
(语义保真 / 人物声纹 / 信息覆盖抽样 / 原文图) stay human-written and are
validated by check_judgment.py once marked ✅.

Usage:
  python selfcheck.py path/to/doc.md
  python selfcheck.py path/to/doc.md --before before.md
  python selfcheck.py path/to/doc.md --json

Exit 1 if 4c-1 actionable hits remain, 4d fails, a bracket is unclosed, or
「判断行证据」finds a rubber-stamped ✅ / adversarial false consensus.
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
import check_judgment  # noqa: E402
import check_readability  # noqa: E402
import check_revision_loss  # noqa: E402
import normalize_spacing  # noqa: E402


def collect(text: str) -> dict:
    hits = check_4c.scan(text)
    consecutive = check_4c.scan_consecutive_english(text)
    contextual = check_4c.scan_contextual_english(text)
    over = check_4c.scan_over_translation(text)
    spacing = normalize_spacing.check(text)
    sections, readability_global = check_readability.check(text)
    share = check_readability.voice_share(sections)
    body, _ = check_judgment._split_self_check(text)
    media_count, uncaptioned = check_judgment.count_body_media(body)
    return {
        "readability_row": check_readability.format_row(sections, readability_global),
        "readability_issues": [
            f"{s.title[:20]}: {i}" for s in sections for i in s.issues
        ] + readability_global,
        "voice_share_estimate": round(share, 4) if share is not None else None,
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
        "media_count": media_count,
        "uncaptioned_media_count": uncaptioned,
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
        f"| 纯净排版 | {d4_status} | {spacing_note} |\n"
        f"{report['readability_row']}"
    )


def _format_bracket_row(brackets: list[str]) -> str:
    status = "✅" if not brackets else "⚠️"
    return f"| 括注完整 | {status} | 4f-3 未收口或被写成发言的括注 {len(brackets)} 处 |"


def _format_revision_row(
    lost_facts: list[str],
    lost_sents: list[str],
    brackets: list[str],
    lifted: list[str],
    media_lost: list[str],
) -> str:
    status = (
        "✅"
        if not lost_facts and not lost_sents and not brackets and not lifted and not media_lost
        else "⚠️"
    )
    return (
        f"| 修订完整性 | {status} | 4f-1 缺失数字/专名 {len(lost_facts)} 项；"
        f"4f-2 找不到对应表述的句子 {len(lost_sents)} 句；"
        f"4f-4 编者注被写成发言 {len(lifted)} 句；"
        f"4f-5 缺失媒体链接 {len(media_lost)} 处 |"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fill 4c/4d/4e/4f self-check rows from scripts")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--before",
        type=Path,
        help="修订前的稿子；给出时追加 4f 修订完整性比对",
    )
    args = parser.parse_args()
    text = args.path.read_text(encoding="utf-8")
    report = collect(text)
    judgment = check_judgment.issues(text)
    brackets = check_revision_loss.bracket_issues(text)

    table_lines = [
        format_rows(report),
        check_judgment.format_row(judgment),
        _format_bracket_row(brackets),
    ]

    revision_payload: dict | None = None
    if args.before:
        before_text = args.before.read_text(encoding="utf-8")
        lost_facts, lost_sents = check_revision_loss.compare(before_text, text)
        lifted = check_revision_loss.lifted_notes(before_text, text)
        media_lost = check_revision_loss.lost_media(before_text, text)
        table_lines.append(
            _format_revision_row(lost_facts, lost_sents, brackets, lifted, media_lost)
        )
        revision_payload = {
            "lost_facts": lost_facts,
            "lost_sentences": lost_sents,
            "lifted_notes": lifted,
            "lost_media": media_lost,
        }

    all_rows = "\n".join(table_lines)

    if args.json:
        payload = {
            "actionable_count": report["actionable_count"],
            "consecutive_count": report["consecutive_count"],
            "contextual_count": report["contextual_count"],
            "over_translation_count": report["over_translation_count"],
            "spacing": report["spacing"],
            "readability_issues": report["readability_issues"],
            "voice_share_estimate": report["voice_share_estimate"],
            "media_count": report["media_count"],
            "uncaptioned_media_count": report["uncaptioned_media_count"],
            "judgment": judgment,
            "brackets": brackets,
            "rows": all_rows,
        }
        if revision_payload is not None:
            payload["revision"] = revision_payload
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(all_rows)
        for item in judgment:
            print(f"  - {item}")
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
        if report["readability_issues"]:
            print("\n4e READABILITY:")
            for issue in report["readability_issues"]:
                print(f"  {issue}")
        for item in brackets:
            print(f"  - {item}")
        if revision_payload is not None:
            if revision_payload["lost_facts"]:
                print("4f-1 LOST_FACTS:", "、".join(revision_payload["lost_facts"]))
            for s in revision_payload["lost_sentences"][:40]:
                print(f"  - {s[:100]}")
            for s in revision_payload["lifted_notes"][:40]:
                print(f"  NOTE_AS_SPEECH: {s[:100]}")
            for m in revision_payload["lost_media"][:40]:
                print(f"  LOST_MEDIA: {m}")

    if (
        report["actionable_count"]
        or report["spacing_count"]
        or brackets
        or judgment
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

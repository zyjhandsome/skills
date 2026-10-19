#!/usr/bin/env python3
"""Catch judgment rows marked pass without the evidence the skill requires.

Machine rows (4c/4d/4e) can be green while 声纹, 遮名 and 信息覆盖抽样 are
rubber-stamped ✅. This check only fires when a row claims ✅, or when the
body states a consensus the adversarial mode forbids. Missing rows stay a
human checklist item.

Usage:
  python check_judgment.py path/to/doc.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FALSE_CONSENSUS = re.compile(r"共识点|达成共识|双方一致|全文共识")
NEGATION = re.compile(r"没有|未|不写|并非|不要|未决")
QUOTE = re.compile(r"「([^」]+)」")
NUMBERED = re.compile(r"^\s*\d+\.\s+\S")
SEPARATOR = re.compile(r"^:?-{3,}:?$")


def _split_self_check(text: str) -> tuple[str, str]:
    marker = "## 自检报告"
    if marker not in text:
        return text, ""
    body, section = text.split(marker, 1)
    return body, section


def _outside_quotes(text: str) -> str:
    return re.sub(r"「[^」]*」", "", text)


def _consensus_hits(text: str) -> list[str]:
    hits: list[str] = []
    cleaned = _outside_quotes(text)
    for sent in re.split(r"[。！？\n；;]", cleaned):
        snippet = sent.strip()
        if snippet and FALSE_CONSENSUS.search(snippet) and not NEGATION.search(snippet):
            hits.append(snippet[:40])
    return hits


def _table_rows(section: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    started = False
    for line in section.splitlines():
        if not line.startswith("|"):
            if started:
                break
            continue
        started = True
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in {"检查项", "a"} or SEPARATOR.match(cells[0]):
            continue
        note = cells[2] if len(cells) > 2 else ""
        rows.append((cells[0], cells[1], note))
    return rows


def _passed(result: str) -> bool:
    return "✅" in result and "不适用" not in result


def _subsection(section: str, heading: str) -> str:
    match = re.search(rf"###[^\n]*{re.escape(heading)}[^\n]*\n", section)
    if not match:
        return ""
    rest = section[match.end() :]
    nxt = re.search(r"\n### ", rest)
    return rest if nxt is None else rest[: nxt.start()]


def _quotes_missing_from_body(block: str, body: str) -> list[str]:
    missing: list[str] = []
    for quote in QUOTE.findall(block):
        if quote and quote not in body:
            missing.append(quote[:24])
    return missing


def issues(text: str) -> list[str]:
    body, section = _split_self_check(text)
    found: list[str] = []
    for snippet in _consensus_hits(body):
        found.append(f"正文写出假共识「{snippet}」")
    if not section:
        return found

    rows = _table_rows(section)
    voice_passed = any(_passed(result) and "声纹" in name for name, result, _ in rows)
    blind_passed = any(_passed(result) and "遮名" in name for name, result, _ in rows)
    coverage_passed = any(_passed(result) and "覆盖抽样" in name for name, result, _ in rows)
    for name, result, note in rows:
        if not _passed(result):
            continue
        for snippet in _consensus_hits(f"{name} {note}"):
            found.append(f"自检通过项写出假共识「{snippet}」")

    if voice_passed:
        block = _subsection(section, "人物声纹")
        quotes = QUOTE.findall(block)
        if not quotes:
            found.append("人物声纹标了通过，但没有「成稿原句」")
        else:
            missing = _quotes_missing_from_body(block, body)
            if missing:
                found.append("人物声纹的原句不在正文：" + "、".join(missing))
    if voice_passed or blind_passed:
        block = _subsection(section, "遮名检验")
        lines = [line for line in block.splitlines() if "「" in line and "→" in line]
        if len(lines) < 3:
            found.append(
                f"遮名检验只有 {len(lines)} 句（声纹或遮名已标通过，需要前/中/后 3 句）"
            )
        else:
            missing = _quotes_missing_from_body(block, body)
            if missing:
                found.append("遮名原句不在正文：" + "、".join(missing))
    if coverage_passed:
        block = _subsection(section, "信息覆盖抽样")
        anchors = [line for line in block.splitlines() if NUMBERED.match(line)]
        if len(anchors) < 3:
            found.append(f"信息覆盖抽样标了通过，但只有 {len(anchors)} 个锚点")
    return found


def format_row(found: list[str]) -> str:
    if not found:
        return "| 判断行证据 | ✅ | 声纹、遮名、覆盖抽样的通过标记有证据；正文无假共识 |"
    return "| 判断行证据 | ⚠️ | " + "；".join(found) + " |"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check rubber-stamped judgment rows")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    found = issues(args.path.read_text(encoding="utf-8"))
    print(format_row(found))
    for item in found:
        print(f"  - {item}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())

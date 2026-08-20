#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate WeChat HTML (+ optional 2.35:1 cover) against md2wechat policy."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RATIO = 2.35
RATIO_TOL = 0.02
SOURCE_OMIT_H2 = {"文章元数据", "核心导读", "目录", "延伸术语表", "自检报告"}
AUDIT_DECISIONS = {"保留", "合并", "删减", "删除"}

FORBIDDEN_IN_ARTICLE = [
    (r"<script\b", "script tag inside article"),
    (r"<link\b", "link tag inside article"),
    (r"fonts\.googleapis", "Google Fonts in article"),
    (r"class=\"mermaid\"", "raw Mermaid block"),
    (r">目录<", "TOC heading should be omitted"),
    (r">延伸术语表<", "glossary heading should be omitted"),
    (r">自检报告<", "self-check section should be omitted"),
    (r"完整整理版｜微信排版", "redundant subtitle"),
    (r"用户提供完整字幕", "pipeline note leaked (字幕来源)"),
    (r"次要核对", "pipeline note leaked (次要核对)"),
    (r"浏览器 MCP", "pipeline note leaked (MCP)"),
    (r"已降级", "pipeline note leaked (抓取降级)"),
    (r"页面口径", "pipeline note leaked (日期口径对照)"),
    (r"元数据抓取", "pipeline note leaked (抓取时间)"),
    (r"\[编者注", "editor note leaked into reader copy"),
    (r">&gt;\s", "leftover Markdown blockquote marker"),
]

COMMON_REQUIRED_IN_ARTICLE = [
    (r'id="wechat-article"', "wechat-article container"),
    (r">来源与说明<", "source footer"),
    (r"style=", "inline styles"),
]

# 对谈实录 required unless keynote/anthology mode (关键语录 section present)
REQUIRED_DIALOGUE_OR_ANTHOLOGY = [
    (r">对谈实录<", "对谈实录 labels"),
    (r">关键语录", "关键语录（单人主题演讲可替代对谈实录）"),
]


def extract_article(html: str) -> str:
    m = re.search(
        r'<section[^>]*id="wechat-article"[^>]*>(.*)</section>',
        html,
        flags=re.S | re.I,
    )
    return m.group(1) if m else html


def detect_profile(article: str) -> str:
    return "full" if re.search(r">核心洞察<", article) else "editorial"


def validate_html(path: Path, profile: str = "auto") -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    article = extract_article(text)
    resolved_profile = detect_profile(article) if profile == "auto" else profile

    for pat, msg in COMMON_REQUIRED_IN_ARTICLE:
        if not re.search(pat, article if "wechat-article" not in pat else text):
            # wechat-article id is on the section tag itself
            if pat == r'id="wechat-article"' and re.search(pat, text):
                continue
            if not re.search(pat, text):
                errors.append(f"MISSING: {msg}")

    for pat, msg in FORBIDDEN_IN_ARTICLE:
        if re.search(pat, article, flags=re.I):
            errors.append(f"FORBIDDEN: {msg}")

    # leftover GFM table pipes dumped as paragraphs (body tables must be converted)
    if re.search(r"<p[^>]*>\s*\|[^<]*\|", article):
        errors.append("FORBIDDEN: leftover Markdown table pipes in paragraphs")
    if re.search(r"<p[^>]*>\|[\s\-:|]+\|", article):
        errors.append("FORBIDDEN: leftover Markdown table separator row")

    # metadata table smell: 原标题 row as meta_row pattern densely
    if article.count("元数据抓取时间") or article.count(">文章元数据<"):
        errors.append("FORBIDDEN: 文章元数据 table/section leaked")

    # Source footer may include a concise "edited, non-verbatim" disclosure.
    footer = ""
    fm = re.search(r">来源与说明<.*$", article, flags=re.S)
    if fm:
        footer = fm.group(0)
        if "不代表" in footer or "非官方中文完整整理" in footer:
            errors.append("FORBIDDEN: long disclaimer in source footer")

    if resolved_profile == "full":
        has_dialogue = bool(re.search(r">对谈实录<", article))
        has_anthology = bool(re.search(r">关键语录", article))
        if not has_dialogue and not has_anthology:
            errors.append(
                "MISSING: 对谈实录 labels（或单人主题演讲的关键语录节）"
            )

        # Full mode keeps the source's three-layer reading hierarchy.
        n_insight = len(re.findall(r">核心洞察<", article))
        n_analysis = len(re.findall(r">深度解析<", article))
        n_dialogue = len(re.findall(r">对谈实录<", article))
        if n_insight < 1 or n_analysis < 1:
            errors.append(
                f"WEAK structure: 核心洞察={n_insight} 深度解析={n_analysis} 对谈实录={n_dialogue}"
            )
        elif n_insight != n_analysis:
            errors.append(
                f"UNBALANCED layers: 核心洞察={n_insight} 深度解析={n_analysis} 对谈实录={n_dialogue}"
            )
        elif n_dialogue == 0 and not has_anthology:
            errors.append(
                f"WEAK structure: 核心洞察={n_insight} 深度解析={n_analysis} 对谈实录={n_dialogue}"
            )
    else:
        h2_count = len(re.findall(r"<h2\b", article, flags=re.I))
        if h2_count < 3:
            errors.append(f"WEAK editorial structure: only {h2_count} section headings")
        if re.search(r"<table\b", article, flags=re.I):
            errors.append("FORBIDDEN: editorial body contains a table; rewrite it for listening")

    return errors


def source_sections(path: Path) -> list[str]:
    sections: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m and m.group(1) not in SOURCE_OMIT_H2:
            sections.append(m.group(1))
    return sections


def audit_rows(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not (line.strip().startswith("|") and line.strip().endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in {"源稿主题", "---"}:
            continue
        if re.fullmatch(r"[-: ]+", cells[0]):
            continue
        rows.append((cells[0].strip("`"), cells[1].strip("`")))
    return rows


def validate_coverage(source: Path, audit: Path, profile: str) -> list[str]:
    errors: list[str] = []
    if not source.is_file():
        return [f"coverage source not found: {source}"]
    if not audit.is_file():
        return [f"coverage audit not found: {audit}"]

    src_text = source.read_text(encoding="utf-8")
    audit_text = audit.read_text(encoding="utf-8")
    sections = source_sections(source)
    rows = audit_rows(audit)

    for required in ("标题承诺", "显式问题", "事实与观点", "来源披露", "重要删除"):
        if required not in audit_text:
            errors.append(f"AUDIT MISSING: {required}")

    row_map: dict[str, list[str]] = {}
    for heading, decision in rows:
        row_map.setdefault(heading, []).append(decision)

    for heading in sections:
        decisions = row_map.get(heading, [])
        if not decisions:
            errors.append(f"AUDIT MISSING SOURCE SECTION: {heading}")
            continue
        if len(decisions) > 1:
            errors.append(f"AUDIT DUPLICATE SOURCE SECTION: {heading}")
        for decision in decisions:
            if decision not in AUDIT_DECISIONS:
                errors.append(f"AUDIT INVALID DECISION: {heading} -> {decision}")
            if profile == "full" and decision in {"删减", "删除"}:
                errors.append(f"FULL MODE CANNOT {decision}: {heading}")

    extra = sorted(set(row_map) - set(sections))
    for heading in extra:
        errors.append(f"AUDIT UNKNOWN SOURCE SECTION: {heading}")

    mode_match = re.search(r"模式[：:]\s*`?(editorial|full)`?", audit_text)
    if mode_match and mode_match.group(1) != profile:
        errors.append(
            f"AUDIT PROFILE MISMATCH: audit={mode_match.group(1)} validator={profile}"
        )

    if profile == "editorial" and ("对谈人物" in src_text or "演讲" in src_text):
        # The edited article should disclose that quotations and sequencing are not verbatim.
        if "非逐字稿" not in audit_text:
            errors.append("AUDIT MISSING: non-verbatim editorial disclosure")

    return errors


def article_metrics(path: Path, profile: str = "auto") -> tuple[str, int, float]:
    text = path.read_text(encoding="utf-8")
    article = extract_article(text)
    resolved_profile = detect_profile(article) if profile == "auto" else profile
    plain = re.sub(r"<[^>]+>", "", article)
    plain = re.sub(r"\s+", "", plain)
    han_chars = len(re.findall(r"[\u4e00-\u9fff]", plain))
    # WeChat TTS speed varies; 260 Han characters/minute is a useful planning estimate.
    return resolved_profile, han_chars, han_chars / 260 if han_chars else 0.0


def validate_cover(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        from PIL import Image
    except ImportError:
        errors.append("Pillow not installed; cannot validate cover ratio")
        return errors
    im = Image.open(path)
    w, h = im.size
    if h == 0:
        errors.append("cover height is 0")
        return errors
    r = w / h
    if abs(r - RATIO) > RATIO_TOL:
        errors.append(f"cover ratio {r:.3f} != 2.35 (±{RATIO_TOL})")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html", type=Path)
    ap.add_argument("--cover", type=Path, default=None)
    ap.add_argument("--source", type=Path, default=None, help="Source *_整理文档.md")
    ap.add_argument("--audit", type=Path, default=None, help="Content coverage audit Markdown")
    ap.add_argument(
        "--profile",
        choices=("auto", "editorial", "full"),
        default="auto",
    )
    args = ap.parse_args(argv)

    errors: list[str] = []
    if not args.html.is_file():
        print(f"ERROR: HTML not found: {args.html}")
        return 2
    errors.extend(validate_html(args.html, profile=args.profile))

    resolved_profile, han_chars, minutes = article_metrics(args.html, profile=args.profile)
    if (args.source is None) != (args.audit is None):
        errors.append("coverage validation requires both --source and --audit")
    elif args.source is not None and args.audit is not None:
        errors.extend(validate_coverage(args.source, args.audit, resolved_profile))
        if resolved_profile == "editorial":
            article = extract_article(args.html.read_text(encoding="utf-8"))
            source_text = args.source.read_text(encoding="utf-8")
            if ("对谈人物" in source_text or "演讲" in source_text) and "非逐字稿" not in article:
                errors.append("MISSING: reader-facing non-verbatim editorial disclosure")

    if args.cover:
        if not args.cover.is_file():
            errors.append(f"cover not found: {args.cover}")
        else:
            errors.extend(validate_cover(args.cover))

    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("OK")
    print(
        f"PROFILE {resolved_profile} | Han chars {han_chars} | "
        f"estimated voice {minutes:.1f} min @ 260 chars/min"
    )
    print(
        "COVERAGE checked against source+audit"
        if args.source is not None and args.audit is not None
        else "COVERAGE not checked (pass --source and --audit)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

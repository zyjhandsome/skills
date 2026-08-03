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

FORBIDDEN_IN_ARTICLE = [
    (r"<script\b", "script tag inside article"),
    (r"<link\b", "link tag inside article"),
    (r"fonts\.googleapis", "Google Fonts in article"),
    (r"class=\"mermaid\"", "raw Mermaid block"),
    (r">目录<", "TOC heading should be omitted"),
    (r">延伸术语表<", "glossary heading should be omitted"),
    (r">自检报告<", "self-check section should be omitted"),
    (r"完整整理版｜微信排版", "redundant subtitle"),
]

REQUIRED_IN_ARTICLE = [
    (r'id="wechat-article"', "wechat-article container"),
    (r">核心洞察<", "核心洞察 labels"),
    (r">深度解析<", "深度解析 labels"),
    (r">对谈实录<", "对谈实录 labels"),
    (r">来源与说明<", "source footer"),
    (r"style=", "inline styles"),
]


def extract_article(html: str) -> str:
    m = re.search(
        r'<section[^>]*id="wechat-article"[^>]*>(.*)</section>',
        html,
        flags=re.S | re.I,
    )
    return m.group(1) if m else html


def validate_html(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    article = extract_article(text)

    for pat, msg in REQUIRED_IN_ARTICLE:
        if not re.search(pat, article if "wechat-article" not in pat else text):
            # wechat-article id is on the section tag itself
            if pat == r'id="wechat-article"' and re.search(pat, text):
                continue
            if not re.search(pat, text):
                errors.append(f"MISSING: {msg}")

    for pat, msg in FORBIDDEN_IN_ARTICLE:
        if re.search(pat, article, flags=re.I):
            errors.append(f"FORBIDDEN: {msg}")

    # metadata table smell: 原标题 row as meta_row pattern densely
    if article.count("元数据抓取时间") or article.count(">文章元数据<"):
        errors.append("FORBIDDEN: 文章元数据 table/section leaked")

    # source footer should not include long disclaimer / 文字稿 third line after 视频
    footer = ""
    fm = re.search(r">来源与说明<.*$", article, flags=re.S)
    if fm:
        footer = fm.group(0)
        if "文字稿" in footer:
            errors.append("FORBIDDEN: source footer has more than first two items (文字稿)")
        if "不代表" in footer or "非官方中文完整整理" in footer:
            errors.append("FORBIDDEN: long disclaimer in source footer")

    # count layer labels roughly balanced
    n_insight = len(re.findall(r">核心洞察<", article))
    n_analysis = len(re.findall(r">深度解析<", article))
    n_dialogue = len(re.findall(r">对谈实录<", article))
    if n_insight < 1 or n_analysis < 1 or n_dialogue < 1:
        errors.append(
            f"WEAK structure: 核心洞察={n_insight} 深度解析={n_analysis} 对谈实录={n_dialogue}"
        )
    elif min(n_insight, n_analysis, n_dialogue) != max(n_insight, n_analysis, n_dialogue):
        # warn only via stderr-style error soft? treat as warn-error for skill strictness
        errors.append(
            f"UNBALANCED layers: 核心洞察={n_insight} 深度解析={n_analysis} 对谈实录={n_dialogue}"
        )

    return errors


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
    args = ap.parse_args(argv)

    errors: list[str] = []
    if not args.html.is_file():
        print(f"ERROR: HTML not found: {args.html}")
        return 2
    errors.extend(validate_html(args.html))

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

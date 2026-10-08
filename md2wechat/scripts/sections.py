#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared H2 vocabulary for builder and validator.

Both must agree on which source sections are production noise, otherwise a
section the skill forbids can still survive into the pasted article.

Upstream content-structuring templates spell some headings with a suffix
(`## 延伸术语表（可选）`). Every membership test here goes through
``normalize_h2`` so that suffix, stray whitespace, or a half-width variant
cannot smuggle a noise section past the builder or the validator.
"""
from __future__ import annotations

import re

# Trailing qualifiers the upstream template appends to a canonical heading.
_H2_SUFFIX = re.compile(r"\s*[（(]\s*(?:可选|optional|按需)\s*[）)]\s*$", re.I)


def normalize_h2(text: str) -> str:
    """Canonical form for H2 membership tests: strip markup, inner whitespace,
    and an upstream `（可选）`-style suffix."""
    s = re.sub(r"<[^>]+>", "", text or "")
    s = s.replace("**", "").strip()
    s = _H2_SUFFIX.sub("", s)
    return re.sub(r"\s+", "", s)


# Regex fragment matching the optional upstream suffix after a heading name.
H2_SUFFIX_RE = r"(?:\s*[（(]\s*(?:可选|optional|按需)\s*[）)])?"

# Production noise: never reaches the pasted article, in either mode.
NOISE_H2 = frozenset(
    {
        "目录",
        "延伸术语表",
        "自检报告",
        "关键语录与交锋时刻",
        "编者注",
        "编辑说明",
        "免责声明",
    }
)

# Consumed into 副标题 / 人物背景 / 页脚; never rendered as an H2.
META_H2 = frozenset({"文章元数据"})

# Written by this skill, so it may appear without being a source body section.
STRUCTURAL_H2 = frozenset({"核心导读"})

# Builder: drop the whole section.
BUILDER_OMIT_H2 = NOISE_H2

# Builder: this one truncates the rest of the document instead of one section.
TRUNCATE_H2 = "自检报告"

# Validator: source H2s that need not appear in the article.
SOURCE_OMIT_H2 = NOISE_H2 | META_H2 | STRUCTURAL_H2

# Validator: H2s allowed in the article beyond the source's reader-facing ones.
ALLOWED_EXTRA_H2 = STRUCTURAL_H2


def is_noise_h2(text: str) -> bool:
    return normalize_h2(text) in NOISE_H2


def is_source_omitted_h2(text: str) -> bool:
    return normalize_h2(text) in SOURCE_OMIT_H2


def forbidden_article_h2_patterns() -> list[tuple[str, str]]:
    """(regex, message) pairs asserting noise headings never reach the article."""
    pairs = [
        (rf">\s*{re.escape(name)}{H2_SUFFIX_RE}\s*<", f"{name} section should be omitted")
        for name in sorted(NOISE_H2)
    ]
    # 关键语录与交锋时刻 is sometimes shortened in drafts.
    pairs.append((r">关键语录", "quotes anthology should be omitted"))
    return pairs

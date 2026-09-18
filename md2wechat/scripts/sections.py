#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared H2 vocabulary for builder and validator.

Both must agree on which source sections are production noise, otherwise a
section the skill forbids can still survive into the pasted article.
"""
from __future__ import annotations

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


def forbidden_article_h2_patterns() -> list[tuple[str, str]]:
    """(regex, message) pairs asserting noise headings never reach the article."""
    pairs = [
        (rf">{name}<", f"{name} section should be omitted")
        for name in sorted(NOISE_H2)
    ]
    # 关键语录与交锋时刻 is sometimes shortened in drafts.
    pairs.append((r">关键语录", "quotes anthology should be omitted"))
    return pairs

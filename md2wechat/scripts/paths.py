#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deliverable naming: keep the source filename, append 公众号文章 / 公众号封面."""
from __future__ import annotations

import re
from pathlib import Path

_DELIVERABLE_RE = re.compile(
    r"^(?P<stem>.+)_(?P<kind>公众号文章|公众号封面)\.(?P<ext>html|png)$"
)


def source_stem(src: Path) -> str:
    """Original filename without .md/.html, so suffixes can be appended."""
    name = src.name
    lower = name.lower()
    for suffix in (".markdown", ".md", ".html"):
        if lower.endswith(suffix):
            return name[: -len(suffix)]
    return src.stem


def article_html_name(src: Path) -> str:
    return f"{source_stem(src)}_公众号文章.html"


def cover_png_name(src: Path) -> str:
    return f"{source_stem(src)}_公众号封面.png"


def pair_stem(path: Path) -> tuple[str, str] | None:
    m = _DELIVERABLE_RE.match(path.name)
    if not m:
        return None
    return m.group("stem"), m.group("kind")

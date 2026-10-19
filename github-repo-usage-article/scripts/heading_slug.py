"""本系列文章共用的标题 slug。validate.py 与 fix-wikilink-anchors.py 都从这里导入。"""

from __future__ import annotations

import re


def heading_to_slug(title: str) -> str:
    """系列内部锚点。两处脚本必须用同一实现,避免各写一份后漂移。"""
    slug = title.strip().lower()
    slug = slug.replace(" · ", "--").replace(" + ", "--").replace("&", "--")
    for ch in "（）()·:：,，":
        slug = slug.replace(ch, "")
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-{3,}", "--", slug)
    return slug.strip("-")

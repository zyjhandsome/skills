# -*- coding: utf-8 -*-
"""CLI contract: coverage audit is required unless --html-only."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from validate_wechat_bundle import main, validate_footer_date, validate_html  # noqa: E402


HTML = """<!DOCTYPE html>
<html lang="zh-CN"><body>
<section id="wechat-article" style="color:#111">
<h1>反馈循环越短，判断越可靠</h1>
<h2>核心导读</h2>
<h2>短循环不是快，而是可验证</h2>
<h2>组织里为什么循环会变长</h2>
<h2>落地时先看哪三件事</h2>
<p style="color:#111">公开分享里的判断。</p>
<section><p>来源与说明</p><p>原文：Short Loops</p></section>
</section>
</body></html>
"""

SOURCE = """# 反馈循环越短，判断越可靠

## 文章元数据
| 原标题 | Short Loops |

## 核心导读
论点。

## 短循环不是快，而是可验证
正文。
"""


class ValidateCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.html = self.tmp / "反馈循环_整理文档_公众号文章.html"
        self.source = self.tmp / "反馈循环_整理文档.md"
        self.html.write_text(HTML, encoding="utf-8")
        self.source.write_text(SOURCE, encoding="utf-8")

    def test_source_without_audit_fails(self):
        code = main([str(self.html), "--source", str(self.source)])
        self.assertEqual(code, 1)

    def test_html_only_skips_coverage(self):
        code = main([str(self.html), "--html-only"])
        self.assertEqual(code, 0)

    def test_truncated_footer_title_fails(self):
        """原标题 with a GFM `\\|` split naively leaves `… Work \\` in the footer."""
        broken = HTML.replace("原文：Short Loops", "原文：How to Stay Valuable as AI Changes Work \\")
        self.html.write_text(broken, encoding="utf-8")
        errors = validate_html(self.html)
        self.assertTrue(any("TRUNCATED 原文" in e for e in errors), errors)

    def test_restored_pipe_title_passes(self):
        intact = HTML.replace("原文：Short Loops", "原文：How to Stay Valuable | Daron Acemoglu")
        self.html.write_text(intact, encoding="utf-8")
        errors = validate_html(self.html)
        self.assertFalse(any("TRUNCATED 原文" in e for e in errors), errors)

    def test_iso_publish_line_passes(self):
        dated = HTML.replace(
            "<p>原文：Short Loops</p>",
            "<p>原文：Short Loops</p><p>发布：2026-10-07</p>",
        )
        self.html.write_text(dated, encoding="utf-8")
        errors = validate_html(self.html)
        self.assertFalse(any("发布" in e for e in errors), errors)

    def test_annotated_publish_line_fails(self):
        dated = HTML.replace(
            "<p>原文：Short Loops</p>",
            "<p>原文：Short Loops</p><p>发布：2026-10-07（用户所记）</p>",
        )
        self.html.write_text(dated, encoding="utf-8")
        errors = validate_html(self.html)
        self.assertTrue(any("ISO dates only" in e for e in errors), errors)

    def test_footer_date_must_match_source(self):
        article = HTML.replace(
            "<p>原文：Short Loops</p>",
            "<p>原文：Short Loops</p><p>发布：2026-10-02</p>",
        )
        source = SOURCE.replace(
            "| 原标题 | Short Loops |",
            "| 原标题 | Short Loops |\n| 发布时间 | 2026-10-07（用户所记；页面显示为 1 天前） |",
        )
        errors = validate_footer_date(article, source)
        self.assertTrue(any("FOOTER DATE" in e and "2026-10-07" in e for e in errors), errors)
        matched = article.replace("发布：2026-10-02", "发布：2026-10-07")
        self.assertEqual(validate_footer_date(matched, source), [])


if __name__ == "__main__":
    unittest.main()

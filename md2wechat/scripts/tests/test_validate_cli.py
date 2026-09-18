# -*- coding: utf-8 -*-
"""CLI contract: coverage audit is required unless --html-only."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from validate_wechat_bundle import main  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

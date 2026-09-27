# -*- coding: utf-8 -*-
"""Process-note leaks, long paragraphs, trailing disclaimers, stale source."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from build_wechat_html import main as build_main  # noqa: E402
from validate_wechat_bundle import (  # noqa: E402
    article_warnings,
    validate_html,
    validate_source_fingerprint,
)

SOURCE = """# 标题

## 文章元数据
| 项目 | 内容 |
|---|---|
| 原标题 | Original |
| 对谈人物 | **甲**（主持人）× **乙**（嘉宾） |

## 核心导读
> **全文论点**：论点。

## 第一节标题
正文。

## 第二节标题
正文。

## 第三节标题
正文。
"""


def article(body: str) -> str:
    return (
        '<section id="wechat-article" style="color:#111">'
        '<h1><span>标题</span></h1>' + body +
        '<section><p><span>来源与说明</span></p><p><span>原文：Original</span></p></section>'
        "</section>"
    )


class ReadabilityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def _html(self, body: str) -> Path:
        path = self.tmp / "x_整理文档_公众号文章.html"
        path.write_text("<html><body>" + article(body) + "</body></html>", encoding="utf-8")
        return path

    def test_process_notes_fail(self):
        for leak in ("口播里的名字听成 Joe Lehman", "两个人都没有姓", "这场没有核对身份", "字幕作 Abalene", "［ASR］"):
            errs = validate_html(self._html("<h2>a</h2><h2>b</h2><h2>c</h2><p><span>%s</span></p>" % leak))
            self.assertTrue(any("process note" in e for e in errs), (leak, errs))

    def test_reader_attribution_passes(self):
        errs = validate_html(self._html(
            "<h2>a</h2><h2>b</h2><h2>c</h2><p><span>他估计大约两成到五成。据他回忆，这是 2025 年。</span></p>"
        ))
        self.assertFalse(any("process note" in e for e in errs), errs)

    def test_long_paragraph_and_disclaimers_warn(self):
        long_p = "字" * 230
        warns = article_warnings(article(
            "<h2><span>一节</span></h2><p><span>%s</span></p>"
            "<p><span>这是他的判断，不是一份就业统计。</span></p><p><span>这场没有点名。</span></p>" % long_p
        ))
        self.assertTrue(any(w.startswith("LONG PARAGRAPH 230") for w in warns), warns)
        self.assertTrue(any("TRAILING DISCLAIMERS" in w for w in warns), warns)

    def test_build_fingerprints_source_and_validator_flags_stale(self):
        src = self.tmp / "稿_整理文档.md"
        src.write_text(SOURCE, encoding="utf-8")
        draft = self.tmp / "draft.md"
        draft.write_text(SOURCE, encoding="utf-8")
        out = self.tmp / "稿_整理文档_公众号文章.html"
        self.assertEqual(build_main([str(draft), "--mode", "editorial", "--out", str(out), "--source", str(src)]), 0)
        html = out.read_text(encoding="utf-8")
        self.assertIn("md2wechat-source: 稿_整理文档.md sha256:", html)
        self.assertIn("第 1 节", html)
        self.assertIn("第 3 节", html)
        self.assertNotIn("第 4 节", html)                 # 核心导读 is not numbered
        self.assertEqual(validate_source_fingerprint(html, src), [])
        src.write_text(SOURCE + "\n补一句。\n", encoding="utf-8")
        self.assertTrue(validate_source_fingerprint(html, src)[0].startswith("STALE"))


if __name__ == "__main__":
    unittest.main()

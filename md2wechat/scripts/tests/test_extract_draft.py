# -*- coding: utf-8 -*-
"""extract_draft_from_html.py must round-trip an editorial article.

build(draft) → extract → build(draft') must produce the same pasted article,
so a deleted 成稿 can be reconstructed from the published HTML for revision.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from build_wechat_html import parse_md, wrap  # noqa: E402
from extract_draft_from_html import build_draft  # noqa: E402
from validate_wechat_bundle import extract_article  # noqa: E402


DRAFT = r"""# 诺奖经济学家：AI 改变工作时如何保持价值

## 文章元数据

| 项目 | 内容 |
|---|---|
| 原标题 | Nobel Economist: How to Stay Valuable \| Daron Acemoglu |
| 对谈人物 | **Marina Mogilko**（主持人） × **Daron Acemoglu**（经济学家） |
| 内容来源 | Silicon Valley Girl Podcast |

> **人物背景**：**Marina Mogilko** 是主持人。**Daron Acemoglu** 是 2024 年诺贝尔经济学奖得主。

## 核心导读

> **全文论点**：AI 被用于自动化，同时也用 AI 去创造新东西。

开场一段，带 ==荧光笔== 和 **加粗**，还有 `代码` 与 [链接](https://example.com/x)。

## 任务份额比当年高一点

> 他当场只把任务份额说得再高一点。

**Daron Acemoglu**：「AI 像一头大象。每个人摸到的是不同的部位。」

正文第二段，A & B < C。

## 护士、教师和电工

第二节正文。==**两种未来**==：人更有生产力，或者失去有意义的工作。
"""


def build(md: str) -> str:
    title, parts, mode = parse_md(md, mode="editorial")
    return wrap(title, parts, mode)


class ExtractDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.html = self.tmp / "x_整理文档_公众号文章.html"
        self.html.write_text(build(DRAFT), encoding="utf-8")

    def test_round_trip_without_source(self):
        draft2, warnings = build_draft(self.html, None)
        self.assertIn("# 诺奖经济学家：AI 改变工作时如何保持价值", draft2)
        self.assertIn(r"| 原标题 | Nobel Economist: How to Stay Valuable \| Daron Acemoglu |", draft2)
        self.assertIn("> **全文论点**：AI 被用于自动化", draft2)
        self.assertIn("**Daron Acemoglu**：「AI 像一头大象。每个人摸到的是不同的部位。」", draft2)
        self.assertIn("==荧光笔==", draft2)
        self.assertIn("==**两种未来**==", draft2)
        self.assertIn("[链接](https://example.com/x)", draft2)
        self.assertIn("A & B < C", draft2)
        self.assertNotIn("第 1 节", draft2)
        self.assertTrue(any("metadata table rebuilt" in w for w in warnings), warnings)

    def test_round_trip_with_source_is_identical(self):
        source = self.tmp / "x_整理文档.md"
        source.write_text(DRAFT, encoding="utf-8")
        draft2, warnings = build_draft(self.html, source)
        self.assertEqual([w for w in warnings if "dropped" in w], [])
        a1 = extract_article(build(DRAFT))
        a2 = extract_article(build(draft2))
        self.assertEqual(a1, a2)

    def test_rejects_foreign_html(self):
        foreign = self.tmp / "other.html"
        foreign.write_text("<html><body><h1>x</h1></body></html>", encoding="utf-8")
        with self.assertRaises(SystemExit):
            build_draft(foreign, None)


if __name__ == "__main__":
    unittest.main()

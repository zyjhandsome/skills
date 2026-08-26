# -*- coding: utf-8 -*-
"""Heading fidelity: WeChat H1/H2 must match the 整理文档 unless rewrite is allowed."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from validate_wechat_bundle import (  # noqa: E402
    validate_coverage,
    validate_heading_fidelity,
)


SOURCE = """# 乐趣即速度：当所有人同时让模型自己煮

## 文章元数据
| 原标题 | Fun Is Velocity |

## 核心导读
论点。

## 恼怒是灵感：厨房里长出 WhatsApp 中继
正文。

## Discord 通宵：Ctrl+C 杀不掉启动守护进程
正文。

## 关键语录与交锋时刻
金句。

## 延伸术语表
| 术语 | 解释 |

## 自检报告
ok
"""

FAITHFUL = """
<section id="wechat-article">
<h1>乐趣即速度：当所有人同时让模型自己煮</h1>
<h2>核心导读</h2>
<h2>恼怒是灵感：厨房里长出 WhatsApp 中继</h2>
<h2>Discord 通宵：Ctrl+C 杀不掉启动守护进程</h2>
</section>
"""

REWRITTEN = """
<section id="wechat-article">
<h1>乐趣即速度：当所有人同时让模型自己煮</h1>
<h2>核心导读</h2>
<h2>最好的产品，从一件没法继续做饭的小事长出来</h2>
<h2>人们是在 Discord 里，才终于摸到那种魔法</h2>
</section>
"""


class HeadingFidelityTests(unittest.TestCase):
    def _source(self) -> Path:
        tmp = Path(tempfile.mkdtemp()) / "整理文档.md"
        tmp.write_text(SOURCE, encoding="utf-8")
        return tmp

    def test_accepts_source_headings(self):
        errors = validate_heading_fidelity(self._source(), FAITHFUL, "editorial")
        self.assertEqual(errors, [])

    def test_rejects_rewritten_h2s(self):
        errors = validate_heading_fidelity(self._source(), REWRITTEN, "editorial")
        blob = "\n".join(errors)
        self.assertTrue(any("MISSING SOURCE H2" in e for e in errors), errors)
        self.assertTrue(any("REWRITTEN OR EXTRA H2" in e for e in errors), errors)
        self.assertIn("恼怒是灵感", blob)

    def test_allow_rewrite_skips_check(self):
        errors = validate_heading_fidelity(
            self._source(), REWRITTEN, "editorial", allow_rewrite=True
        )
        self.assertEqual(errors, [])

    def test_rejects_editorial_merge_across_h2(self):
        src = self._source()
        audit = src.with_name("审计.md")
        audit.write_text(
            """# 公众号内容审计

## 闭环检查
- 标题承诺：沿用源稿
- 显式问题：无
- 事实与观点：口播
- 来源披露：公开演讲；非逐字稿
- 重要删除：无

## 运营规范
- 发布结论：可发布
- 风险清单：无

## 覆盖矩阵
| 源稿主题 | 处理 | 成稿位置 | 核心保留与删减理由 |
|---|---|---|---|
| 恼怒是灵感：厨房里长出 WhatsApp 中继 | 合并 | 最好的产品 | 改成更好听的标题 |
| Discord 通宵：Ctrl+C 杀不掉启动守护进程 | 保留 | Discord 通宵：Ctrl+C 杀不掉启动守护进程 | 节内去掉三层 |
""",
            encoding="utf-8",
        )
        errors = validate_coverage(src, audit, "editorial")
        self.assertTrue(
            any("EDITORIAL CANNOT 合并 ACROSS H2" in e for e in errors), errors
        )

    def test_rejects_quotes_anthology_h2(self):
        html = """
<section id="wechat-article">
<h1>乐趣即速度：当所有人同时让模型自己煮</h1>
<h2>核心导读</h2>
<h2>恼怒是灵感：厨房里长出 WhatsApp 中继</h2>
<h2>Discord 通宵：Ctrl+C 杀不掉启动守护进程</h2>
<h2>关键语录与交锋时刻</h2>
</section>
"""
        errors = validate_heading_fidelity(self._source(), html, "editorial")
        self.assertTrue(any("REWRITTEN OR EXTRA H2" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""Cross-skill contract: md2wechat must accept what content-structuring emits.

The upstream templates spell the glossary heading `## 延伸术语表（可选）` and
end with `## 自检报告`. Neither may reach the pasted article, and the
validator must not demand coverage rows for them. These tests build the
upstream fixtures end to end (scan → build → validate) when the sibling skill
is installed, and always run an inline copy of the suffixed heading shape.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from build_wechat_html import parse_md, source_fingerprint, wrap  # noqa: E402
from sections import is_noise_h2, normalize_h2  # noqa: E402
from validate_wechat_bundle import (  # noqa: E402
    extract_article,
    main as validate_main,
    source_sections,
    validate_html,
)
from wechat_policy import scan_source_risks  # noqa: E402

UPSTREAM_FIXTURES = SCRIPTS.parents[1] / "content-structuring" / "fixtures"

INLINE_SOURCE = """# 测试标题

## 文章元数据

| 项目 | 内容 |
|------|------|
| **原标题** | Fixture Title |
| **对谈人物** | **甲**（主持人） × **乙**（嘉宾） |

> **人物背景**：乙讲解。

---

## 核心导读

> **全文论点**：论点。

---

## 目录

1. [第一节](#第一节)

---

## 第一节

### 核心洞察

> 洞察。

### 深度解析

解析。

### 对谈实录

**甲**：「问？」

**乙**：「答。」

## 第二节

### 核心洞察

> 洞察二。

### 深度解析

解析二。

---

## 延伸术语表（可选）

| 术语 | 全称/解释 |
|------|-----------|
| Skill | 不该出现在正文 |

---

## 自检报告

| 检查项 | 结果 | 备注 |
|--------|------|------|
| 纯净排版 | ✅ | 不该出现在正文 |
"""


def _audit_for(source: Path, mode: str) -> str:
    rows = "\n".join(
        f"| {h} | 保留 | {h} | 节内结构保留 |" for h in source_sections(source)
    )
    return f"""# 公众号内容审计

## 文件与模式
- 模式：{mode}
- 源稿：{source.name}
- 成稿：临时

## 覆盖矩阵
| 源稿主题 | 处理 | 成稿位置 | 核心保留与删减理由 |
|---|---|---|---|
{rows}

## 闭环检查
- 标题承诺：沿用源稿 H1
- 显式问题：无
- 事实与观点：口播归于讲者
- 来源披露：公开场次；非逐字稿
- 重要删除：无

## 运营规范
- 官方页：微信公众平台运营规范（发送内容规范 + 当地法律监管）
- 扫描：无
- 处理：无
- 发布结论：可发布
"""


class NormalizeTests(unittest.TestCase):
    def test_suffix_variants_are_noise(self):
        for h in ("延伸术语表", "延伸术语表（可选）", "延伸术语表 (optional)", "**自检报告**"):
            self.assertTrue(is_noise_h2(h), h)

    def test_reader_heading_untouched(self):
        self.assertEqual(normalize_h2("恼怒是灵感：厨房里长出 WhatsApp 中继"), "恼怒是灵感：厨房里长出WhatsApp中继")


class InlineSuffixedSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "inline_整理文档.md"
        self.src.write_text(INLINE_SOURCE, encoding="utf-8")

    def test_builder_drops_suffixed_glossary_and_selfcheck(self):
        title, parts, mode = parse_md(INLINE_SOURCE, mode="auto")
        self.assertEqual(mode, "full")
        article = "".join(parts)
        self.assertNotIn("延伸术语表", article)
        self.assertNotIn("自检报告", article)
        self.assertNotIn("不该出现在正文", article)

    def test_validator_does_not_demand_glossary_coverage(self):
        self.assertEqual(source_sections(self.src), ["第一节", "第二节"])

    def test_full_pipeline_passes_with_template_audit(self):
        title, parts, mode = parse_md(INLINE_SOURCE, mode="auto")
        html = self.tmp / "inline_整理文档_公众号文章.html"
        html.write_text(
            wrap(title, parts, mode=mode, fingerprint=source_fingerprint(self.src)),
            encoding="utf-8",
        )
        audit = self.tmp / "audit.md"
        audit.write_text(_audit_for(self.src, mode), encoding="utf-8")
        code = validate_main([str(html), "--source", str(self.src), "--audit", str(audit)])
        self.assertEqual(code, 0)


@unittest.skipUnless(UPSTREAM_FIXTURES.is_dir(), "content-structuring fixtures not installed")
class UpstreamFixtureTests(unittest.TestCase):
    """Every content-structuring golden sample must convert without leaking noise."""

    def _fixtures(self) -> list[Path]:
        return sorted(
            p
            for p in UPSTREAM_FIXTURES.glob("*.md")
            if p.name != "README.md" and "## 文章元数据" in p.read_text(encoding="utf-8")
        )

    def test_fixtures_exist(self):
        self.assertTrue(self._fixtures())

    def test_no_noise_section_reaches_article(self):
        for fx in self._fixtures():
            with self.subTest(fixture=fx.name):
                _, parts, _ = parse_md(fx.read_text(encoding="utf-8"), mode="auto")
                article = "".join(parts)
                for noise in ("延伸术语表", "自检报告", "关键语录与交锋时刻", ">目录<"):
                    self.assertNotIn(noise, article, f"{noise} leaked from {fx.name}")

    def test_html_lint_passes(self):
        for fx in self._fixtures():
            with self.subTest(fixture=fx.name):
                title, parts, mode = parse_md(fx.read_text(encoding="utf-8"), mode="auto")
                tmp = Path(tempfile.mkdtemp())
                html = tmp / f"{fx.stem}_公众号文章.html"
                html.write_text(wrap(title, parts, mode=mode), encoding="utf-8")
                errors = validate_html(html)
                self.assertEqual(errors, [], f"{fx.name}: {errors}")

    def test_editorial_draft_from_generic_fixture_passes_full_validation(self):
        """Editorial flow: draft copies the fixture's H1 and reader H2s, the
        audit follows the content-integrity.md skeleton, validator exits 0."""
        fx = UPSTREAM_FIXTURES / "longform-generic.md"
        if not fx.is_file():
            self.skipTest("longform fixture missing")
        tmp = Path(tempfile.mkdtemp())
        src = tmp / "20260522 测试_整理文档.md"
        src.write_text(fx.read_text(encoding="utf-8"), encoding="utf-8")
        headings = source_sections(src)
        self.assertGreaterEqual(len(headings), 3, "fixture must carry ≥3 reader H2s")
        h1 = next(l for l in src.read_text(encoding="utf-8").splitlines() if l.startswith("# "))
        draft = h1 + "\n\n" + "\n\n".join(
            f"## {h}\n\n这一节保留源稿的结论与机制，去掉三层标签后改成可播报叙述。" for h in headings
        ) + "\n"
        title, parts, mode = parse_md(draft, mode="editorial")
        self.assertEqual(mode, "editorial")
        html = tmp / "20260522 测试_整理文档_公众号文章.html"
        html.write_text(
            wrap(title, parts, mode=mode, fingerprint=source_fingerprint(src)),
            encoding="utf-8",
        )
        audit = tmp / "audit.md"
        audit.write_text(_audit_for(src, mode), encoding="utf-8")
        code = validate_main([str(html), "--source", str(src), "--audit", str(audit)])
        self.assertEqual(code, 0)

    def test_policy_scan_is_clean_on_golden_samples(self):
        for fx in self._fixtures():
            with self.subTest(fixture=fx.name):
                self.assertEqual(scan_source_risks(fx.read_text(encoding="utf-8")), [])

    def test_dialogue_fixture_full_pipeline(self):
        fx = UPSTREAM_FIXTURES / "dialogue-three-layer.md"
        if not fx.is_file():
            self.skipTest("dialogue fixture missing")
        tmp = Path(tempfile.mkdtemp())
        src = tmp / "20260715 测试_整理文档.md"
        src.write_text(fx.read_text(encoding="utf-8"), encoding="utf-8")
        title, parts, mode = parse_md(src.read_text(encoding="utf-8"), mode="auto")
        html = tmp / "20260715 测试_整理文档_公众号文章.html"
        html.write_text(
            wrap(title, parts, mode=mode, fingerprint=source_fingerprint(src)),
            encoding="utf-8",
        )
        audit = tmp / "audit.md"
        audit.write_text(_audit_for(src, mode), encoding="utf-8")
        code = validate_main([str(html), "--source", str(src), "--audit", str(audit)])
        self.assertEqual(code, 0)
        self.assertNotIn("延伸术语表", extract_article(html.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()

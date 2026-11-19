#!/usr/bin/env python3
"""Gate regression tests for content-structuring scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_4c  # noqa: E402
import check_judgment  # noqa: E402
import check_readability  # noqa: E402
import check_revision_loss  # noqa: E402
import normalize_spacing  # noqa: E402

NORM = SCRIPTS / "normalize_spacing.py"
CHECK4C = SCRIPTS / "check_4c.py"
SELFCHECK = SCRIPTS / "selfcheck.py"
FIX = ROOT / "fixtures"


def run(cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
    full_cmd = list(cmd)
    if full_cmd and full_cmd[0] == sys.executable and "-B" not in full_cmd[1:3]:
        full_cmd.insert(1, "-B")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(full_cmd, capture_output=True, env=env)


def _layered(analysis: str, dialogue: str) -> str:
    return f"# T\n\n## 节\n\n### 深度解析\n\n{analysis}\n\n### 对谈实录\n\n{dialogue}\n"


class GateRegressionTest(unittest.TestCase):
    def _with_temp_md(self, text: str):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        f.write(text)
        f.close()
        path = Path(f.name)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    # --- Original regression suite ---

    def test_4d_detects_hr_with_blank_line(self) -> None:
        text = """# T

## 文章元数据

| 项目 | 内容 |
|------|------|
| **原标题** | X |

---

## 核心导读

> **全文论点**：A

---

## 目录

1. [一](#1)

---

## 第一节

### 核心洞察

> 一

### 深度解析

内容

---

## 第二节

### 核心洞察

> 二

### 深度解析

内容二

---

## 自检报告

| a | b |
|---|---|
| x | y |
"""
        path = self._with_temp_md(text)
        cp = run([sys.executable, str(NORM), str(path), "--check"])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        self.assertNotEqual(cp.returncode, 0, out + err)
        self.assertIn("between body sections", out)

    def test_fixture_dialogue_4d_ok(self) -> None:
        cp = run([sys.executable, str(NORM), str(FIX / "dialogue-three-layer.md"), "--check"])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)

    def test_fixture_adversarial_4d_ok(self) -> None:
        cp = run([sys.executable, str(NORM), str(FIX / "adversarial-interview.md"), "--check"])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)

    def test_fixture_longform_4d_ok(self) -> None:
        cp = run([sys.executable, str(NORM), str(FIX / "longform-generic.md"), "--check"])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)

    def test_fixture_multisource_4d_ok(self) -> None:
        cp = run([sys.executable, str(NORM), str(FIX / "multisource-conflict.md"), "--check"])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)

    def test_fixture_visual_lecture_4d_ok(self) -> None:
        cp = run([sys.executable, str(NORM), str(FIX / "visual-lecture-voice.md"), "--check"])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)

    def test_fixture_longform_4c_ok(self) -> None:
        cp = run([sys.executable, str(CHECK4C), str(FIX / "longform-generic.md")])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)

    def test_fixture_multisource_4c_ok(self) -> None:
        cp = run([sys.executable, str(CHECK4C), str(FIX / "multisource-conflict.md")])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)

    def test_fixture_dialogue_4c_ok(self) -> None:
        cp = run([sys.executable, str(CHECK4C), str(FIX / "dialogue-three-layer.md")])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)

    def test_fixture_visual_lecture_4c_ok(self) -> None:
        cp = run([sys.executable, str(CHECK4C), str(FIX / "visual-lecture-voice.md")])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)

    def test_all_positive_fixtures_pass_selfcheck(self) -> None:
        positives = (
            "dialogue-three-layer.md",
            "adversarial-interview.md",
            "longform-generic.md",
            "multisource-conflict.md",
            "visual-lecture-voice.md",
        )
        for name in positives:
            with self.subTest(fixture=name):
                cp = run([sys.executable, str(SELFCHECK), str(FIX / name)])
                out = (cp.stdout or b"").decode("utf-8", errors="replace")
                err = (cp.stderr or b"").decode("utf-8", errors="replace")
                self.assertEqual(cp.returncode, 0, f"{name}:\n{out}{err}")
                self.assertIn("| 判断行证据 | ✅ |", out)
                self.assertIn("| 括注完整 | ✅ |", out)

    def test_4c_inline_lexicon_comments_do_not_break_patterns(self) -> None:
        path = self._with_temp_md("# T\n\n## 第一节\n\n灰度 rollout 之后再看 PIP。\n")
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)
        self.assertIn("CONTEXTUAL_ENGLISH_REVIEW", out)
        self.assertTrue("rollout" in out.lower() or "PIP" in out)

    def test_4c_full_lexicon_loaded_from_file(self) -> None:
        path = self._with_temp_md(
            "# T\n\n## 第一节\n\n这家公司的 flywheel 很强，incumbent 压力大，团队仍在 pontificate。\n"
        )
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertNotEqual(cp.returncode, 0, out)
        self.assertTrue("flywheel" in out and "incumbent" in out and "pontificate" in out)

    def test_fixture_stock_4c_hits(self) -> None:
        cp = run([sys.executable, str(CHECK4C), str(FIX / "stock-english-mix.md")])
        out = (cp.stdout or b"").decode("utf-8", errors="replace").lower()
        self.assertNotEqual(cp.returncode, 0, out)
        self.assertTrue("super bullish" in out or "operationalize" in out or "refine" in out)

    def test_4c_allows_rag_and_technical_harness(self) -> None:
        path = self._with_temp_md(
            "# T\n\n## 第一节\n\n检索增强生成（RAG）用于召回。Harness 是产品名，harness 也是常见技术层标签。\n"
        )
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)
        self.assertNotIn("RAG", out)

    def test_4c_allows_field_native_concept_labels(self) -> None:
        path = self._with_temp_md(
            "# T\n\n## 第一节\n\n他把自己定义为 Builder。技术演化线是 Agent → Loop → Graph，核心是 Agent Loop。\n"
        )
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)
        self.assertNotIn("ACTIONABLE_HITS", out)

    def test_4c_reports_likely_over_translation_without_failing(self) -> None:
        path = self._with_temp_md(
            "# T\n\n## 第一节\n\n现场先问：先是代理，然后循环，然后图。讲者说自己爱的是建造，编程只是手段。\n"
        )
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)
        self.assertIn("OVER_TRANSLATION_REVIEW", out)

    def test_4c_consecutive_english_is_review_not_fail(self) -> None:
        path = self._with_temp_md(
            "# T\n\n## 第一节\n\n这套 go to market motion 很强，团队靠 land and expand 打开客户。\n"
            "真正的瓶颈是 organizational readiness，而不是 technical debt；管理层 still hesitant。\n"
        )
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)
        self.assertIn("CONSECUTIVE_ENGLISH_4C2", out)
        self.assertNotIn("ACTIONABLE_HITS", out)

    def test_4c_lowercase_generic_labels_not_masked(self) -> None:
        path = self._with_temp_md(
            "# T\n\n## 第一节\n\n正文把 agent loop 当普通夹写留下，后又写 workflow change。\n"
        )
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)
        self.assertIn("CONSECUTIVE_ENGLISH_4C2", out)

    def test_selfcheck_emits_machine_rows(self) -> None:
        text = """# T

## 文章元数据

| 项目 | 内容 |
|------|------|
| **原标题** | X |

---

## 核心导读

> **全文论点**：A

---

## 目录

1. [一](#1)

---

## 第一节

### 核心洞察

> 一

### 深度解析

团队对路线图仍然 super bullish，并靠 land and expand 扩张。

---

## 第二节

### 核心洞察

> 二

### 深度解析

内容二

---

## 自检报告

| a | b |
|---|---|
| x | y |
"""
        path = self._with_temp_md(text)
        cp = run([sys.executable, str(SELFCHECK), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertNotEqual(cp.returncode, 0, out)
        self.assertIn("正文中文叙事", out)
        self.assertIn("纯净排版", out)
        self.assertIn("4c-1", out)
        self.assertIn("4c-2", out)

    def test_selfcheck_warns_when_only_4c2_remains(self) -> None:
        path = self._with_temp_md("# T\n\n## 第一节\n\n这套 go to market motion 很强。\n")
        cp = run([sys.executable, str(SELFCHECK), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)
        self.assertIn("| 正文中文叙事 | ⚠️ |", out)
        self.assertIn("go to market", out.lower())

    def test_4c_ignores_code_fences_links_and_urls(self) -> None:
        text = """# T

延伸阅读见 [Towards infinite context windows](https://example.com/context)。

```text
tokens of context and super bullish flywheel
```

正文已中文化，调用 `deprecate` 与 `prompt caching` 接口（原文："We are super bullish on this flywheel"）。
"""
        path = self._with_temp_md(text)
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)
        self.assertEqual(check_4c.scan(text), [])
        self.assertEqual(check_4c.scan_consecutive_english(text), [])

    def test_readability_adversarial_order_does_not_self_overlap(self) -> None:
        sections, _ = check_readability.check(
            (FIX / "adversarial-interview.md").read_text(encoding="utf-8")
        )
        self.assertTrue(sections)
        for sec in sections:
            self.assertNotIn("### 语境与释义", sec.dialogue)
            self.assertFalse(any(i.startswith("4e-1") for i in sec.issues))

    def test_4e2_reports_floor_when_it_binds(self) -> None:
        over, _ = check_readability.check(_layered("乙" * 460, "丙" * 200))
        issues = [i for sec in over for i in sec.issues if i.startswith("4e-2")]
        self.assertEqual(len(issues), 1)
        self.assertIn("上限 450", issues[0])
        self.assertIn("保底 450", issues[0])
        under, _ = check_readability.check(_layered("乙" * 450, "丙" * 200))
        self.assertFalse(any(i.startswith("4e-2") for sec in under for i in sec.issues))

    def test_4e2_reports_half_when_dialogue_is_long(self) -> None:
        over, _ = check_readability.check(_layered("乙" * 1001, "丙" * 2000))
        issues = [i for sec in over for i in sec.issues if i.startswith("4e-2")]
        self.assertEqual(len(issues), 1)
        self.assertIn("上限 1000", issues[0])
        under, _ = check_readability.check(_layered("乙" * 1000, "丙" * 2000))
        self.assertFalse(any(i.startswith("4e-2") for sec in under for i in sec.issues))

    def test_adversarial_judgment_evidence_passes(self) -> None:
        found = check_judgment.issues(
            (FIX / "adversarial-interview.md").read_text(encoding="utf-8")
        )
        self.assertEqual(found, [])

    def test_quoted_consensus_is_not_a_false_consensus(self) -> None:
        text = "# T\n\n### 原声交锋\n\n**林青**：「你们这是达成共识吗？」\n\n双方没有达成共识。\n"
        self.assertEqual(check_judgment.issues(text), [])

    def test_rubber_stamp_fixture_fails_judgment_only(self) -> None:
        cp = run([sys.executable, str(SELFCHECK), str(FIX / "judgment-rubber-stamp.md")])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 1, out)
        self.assertIn("4c-1 actionable=0", out)
        self.assertIn("| 纯净排版 | ✅ |", out)
        self.assertTrue("假共识" in out and "人物声纹" in out and "锚点" in out)

    def test_skill_entry_does_not_keep_a_second_length_threshold(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        gates = (ROOT / "references" / "language-and-gates.md").read_text(encoding="utf-8")
        self.assertNotIn("200–400", skill)
        self.assertNotIn("200-400", skill)
        self.assertIn("max(450, floor(同节实录字数的一半))", gates)

    def test_fixture_adversarial_readability_ok(self) -> None:
        sections, global_issues = check_readability.check(
            (FIX / "adversarial-interview.md").read_text(encoding="utf-8")
        )
        row = check_readability.format_row(sections, global_issues)
        self.assertTrue(row.startswith("| 可读性机检 | ✅ |"), row)

    # --- New media & contract regression tests ---

    def test_4c_masks_html_media_and_balanced_paren_image_urls(self) -> None:
        doc = """# T

## 第一节

![示意图](https://example.com/chart-(2026)-margin-flywheel.png)

<figure class="source-figure"><img src="https://example.com/margin-flywheel.png" alt="利润率飞轮"><figcaption>图 1：利润率对比</figcaption></figure>
"""
        self.assertEqual(check_4c.scan(doc), [])
        self.assertEqual(check_4c.scan_consecutive_english(doc), [])
        # Bare narrative English inside image alt text is still caught
        bad_alt = "## 第一节\n\n![原文图 1：live demo 界面](https://example.com/fig.png)\n"
        self.assertTrue(any(h["match"] == "live demo" for h in check_4c.scan(bad_alt)))

    def test_4c_over_translation_ignores_chinese_figure_references(self) -> None:
        prose = "## 节\n\n如上图，图 2 展示了拓扑；原图，图 8 为动图；架构图、工作流拆解如下。\n"
        self.assertEqual(check_4c.scan_over_translation(prose), [])
        over = "## 节\n\n他的演化链是循环、图、工作流。\n"
        self.assertTrue(check_4c.scan_over_translation(over))

    def test_4c_catches_brand_typos_and_cs_acronyms(self) -> None:
        typos = "## 节\n\n团队对比了 Grock、open ai、chat gpt 与 cloudcode。\n"
        hits = {h["match"].lower() for h in check_4c.scan(typos)}
        self.assertEqual(hits, {"grock", "open ai", "chat gpt", "cloudcode"})

        acronyms = "## 节\n\n两位 IC 与 MTS 讨论了 ASL 与 GTM，而 logic 与 platform 不应误报。\n"
        ctx = {h["match"] for h in check_4c.scan_contextual_english(acronyms)}
        self.assertTrue({"IC", "MTS", "ASL", "GTM"}.issubset(ctx))
        self.assertNotIn("ic", {m.lower() for m in ctx - {"IC"}})

    def test_readability_strips_media_urls_mermaid_and_tables(self) -> None:
        cdn = (
            "https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/"
            "https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F"
        )
        u1 = cdn + "11111111-aaaa-bbbb-cccc-000000000001_2400x1350.png"
        u2 = cdn + "22222222-dddd-eeee-ffff-999999999999_2400x1350.png"
        doc = f"""# T

## 第一节

### 核心洞察

> 简短结论。

### 深度解析

这里只有二十五个汉字的背景衔接说明。

![原文图 1：统计分布]({u1})

*原文图 1：统计分布（[原图地址]({u1})）*

![原文图 2：趋势变化]({u2})

*原文图 2：趋势变化（[原图地址]({u2})）*

```mermaid
flowchart LR
  A["模块一"] --> B["模块二"] --> C["模块三"]
```

### 对谈实录

**甲**：「请问明年的海外市场按席位阶梯定价是否取消免费层？」
"""
        sections, glob = check_readability.check(doc)
        self.assertEqual(glob, [])
        self.assertEqual(sections[0].issues, [])
        self.assertIsNotNone(check_readability.voice_share(sections))

    def test_readability_warns_empty_dialogue_shell_and_embedded_dialogue_media(self) -> None:
        empty_shell = "# T\n\n## 节一\n\n### 深度解析\n\n" + ("甲" * 600) + "\n\n### 对谈实录\n\n"
        secs, _ = check_readability.check(empty_shell)
        self.assertTrue(any("空壳实录" in i for i in secs[0].issues))
        self.assertFalse(any(i.startswith("4e-2") for i in secs[0].issues))

        no_dialogue = (
            "# T\n\n## 节一\n\n### 深度解析\n\n"
            + "\n\n".join(["甲" * 200] * 3)
            + "\n"
        )
        secs_no_d, _ = check_readability.check(no_dialogue)
        self.assertEqual(secs_no_d[0].issues, [])

        media_in_d = _layered("解析。", "**甲**：「看图。」\n\n![图](https://example.com/a.png)\n")
        secs_m, _ = check_readability.check(media_in_d)
        self.assertTrue(any("实录层内嵌了图片" in i for i in secs_m[0].issues))

    def test_4d_protects_code_fences_and_catches_heading_and_url_violations(self) -> None:
        fenced_doc = """# T

## 目录

1. [第一节](#第一节)

---

## 第一节

```markdown
## 代码块里的示例标题
### 子标题


---
```

---

## 自检报告
"""
        self.assertEqual(normalize_spacing.check(fenced_doc), [])
        normalized = normalize_spacing.normalize(fenced_doc)
        self.assertIn("## 代码块里的示例标题\n### 子标题\n\n\n---", normalized)

        bad_4d = """# T

## 文章元数据

| 项目 | 内容 |
|---|---|
| **文稿结构** | 对谈三层节结构 |

---

## 目录

1. [一](#一)

---

## 1. 带序号标题 {#explicit-anchor}

过渡段违规写在核心洞察之前。

### 核心洞察

> 洞察。

### 深度解析

![断图](https://example.com/bad space.png)
"""
        issues = normalize_spacing.check(bad_4d)
        self.assertTrue(any("序号前缀" in x for x in issues), issues)
        self.assertTrue(any("显式锚点" in x for x in issues), issues)
        self.assertTrue(any("核心洞察" in x for x in issues), issues)
        self.assertTrue(any("空白字符" in x for x in issues), issues)

    def test_judgment_scoping_bold_quotes_dedup_and_media_row(self) -> None:
        # Non-adversarial consensus is allowed
        normal = "# T\n\n## 第一节\n\n两位创始人在开源协议选型上达成共识。\n\n## 自检报告\n"
        self.assertEqual(check_judgment.issues(normal), [])

        # Bolded body quote matches plain self-check quote; duplicate/reused blind quotes fail
        bold_ok = """# T
## 目录
## 第一节
### 对谈实录
**甲**：「这是 **Agent Skill** 的核心。」
**乙**：「第一句独立原话。」
**甲**：「第二句独立原话。」
**乙**：「第三句独立原话。」
## 自检报告
| 检查项 | 结果 | 备注 |
|---|---|---|
| 人物声纹 | ✅ | 见下 |
| 原文图 | ✅ | 源页正文 0 张，稿内 0 张 |
### 人物声纹（附证据）
**甲**
1. 明确 — 「这是 Agent Skill 的核心。」
### 遮名检验
1. 「第一句独立原话。」→ 乙
2. 「第二句独立原话。」→ 甲
3. 「第三句独立原话。」→ 乙
"""
        self.assertEqual(check_judgment.issues(bold_ok), [])

        reused_blind = bold_ok.replace("「第一句独立原话。」", "「这是 Agent Skill 的核心。」")
        self.assertTrue(any("复用" in x for x in check_judgment.issues(reused_blind)))

        bad_media = bold_ok.replace("源页正文 0 张，稿内 0 张", "无统计图")
        self.assertTrue(any("无统计图" in x for x in check_judgment.issues(bad_media)))

        mismatch_media = bold_ok.replace("源页正文 0 张，稿内 0 张", "源页正文 2 张，稿内 2 张")
        self.assertTrue(any("实际检出 0 处" in x for x in check_judgment.issues(mismatch_media)))

    def test_selfcheck_json_includes_revision_and_lost_media(self) -> None:
        before = """# T

## 目录

## 第一节

### 深度解析

保留的分析句子长度已经超过十四个汉字。

![原文图 1：架构图](https://example.com/fig1.png)

*原文图 1：架构图（[原图地址](https://example.com/fig1.png)）*

## 自检报告
"""
        after = """# T

## 目录

## 第一节

### 深度解析

保留的分析句子长度已经超过十四个汉字。

## 自检报告
"""
        p_before = self._with_temp_md(before)
        p_after = self._with_temp_md(after)
        cp = run([sys.executable, str(SELFCHECK), str(p_after), "--before", str(p_before), "--json"])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        self.assertEqual(cp.returncode, 0, out)
        data = json.loads(out)
        self.assertIn("revision", data)
        self.assertEqual(data["revision"]["lost_media"], ["https://example.com/fig1.png"])
        self.assertIn("修订完整性 | ⚠️", data["rows"])


if __name__ == "__main__":
    unittest.main()

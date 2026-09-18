# -*- coding: utf-8 -*-
"""Regression tests for md2html-lecture converters.

Focus: no silent content drops (preamble / unknown subsections / multi-line
quotes), block-level markdown support, generic speaker tagging,
batch-upgrade diagram preservation, and 争辩型 layers (核心冲突 / 原声交锋 /
未决问题 / optional 实录 / extra metadata tables).

Run:  python -m pytest scripts/tests/ -q   (from the skill root)
"""
import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_html = _load("build_html")
batch = _load("batch_upgrade_dir")


SAMPLE_MD = """# 测试标题

## 文章元数据

| 项目 | 内容 |
|------|------|
| 原标题 | Test Show with Host — Guest on AI |
| 发布时间 | 2026-09-01 |
| 内容链接 | https://youtu.be/abc123 |

> **人物背景**：张三是某公司创始人，写过 *一本书*。

## 核心导读

> **全文论点**：这是核心论点；后半句。

导读段落一。

## 目录

- 忽略

## 普通小节A

### 核心洞察

> 一句话洞察。

### 深度解析

解析段落，含**重点**、*斜体* 和 `代码`。

> 这是解析中的引用行。

1. 有序一
2. 有序二

```python
print("hello")
```

### 对谈实录

**主持人**：「你好」

**嘉宾**：「回答，
跨行的后半句」

### 自定义子节

这个子节名字不在白名单里。

## 关键语录与交锋时刻

**主持人**：「金句一」

这里还有一段没有任何三级标题的正文。

## 延伸术语表

| 术语 | 解释 |
|------|------|
| AI | 人工智能 |

## 自检报告

| 项 | 结果 |
|----|------|
| 完整性 | OK |
"""


def _build(tmp_path, source=SAMPLE_MD, name="sample_整理文档"):
    md = tmp_path / ("%s.md" % name)
    out = tmp_path / ("%s.html" % name)
    md.write_text(source, encoding="utf-8")
    build_html.build(str(md), str(out))
    return out.read_text(encoding="utf-8")


DEBATE_MD = """# 争辩标题

## 文章元数据

| 项目 | 内容 |
|------|------|
| 原标题 | Debate Show |
| 发布时间 | 2026-09-02 |
| 内容链接 | https://youtu.be/debate1 |
| 文稿结构 | 争辩型访谈 |

### 官方章节索引

| 时间 | 章节 |
|------|------|
| 00:12 | 开场 |

> **讲者背景**：李四是对谈嘉宾。

## 核心导读

> **核心冲突**：双方对监管是否该提前介入无法达成共识。

导读说明分歧本身就是论点。

## 交锋小节

### 核心洞察

> 冲突没有收束。

### 深度解析

解析双方框架。

### 原声交锋

**甲**：「应该先立法。」

**乙**：「那会扼杀实验。」

### 语境与释义

甲要的是事前规则，乙要的是事后追责。

### 未决问题

现场没有给出可执行的折中。

## 无实录小节

### 核心洞察

> 这节没有值得摘的对话。

### 深度解析

只有分析，没有对谈实录层。

## 延伸术语表

| 术语 | 解释 |
|------|------|
| 监管 | 事前或事后规则 |

## 自检报告

| 项 | 结果 |
|----|------|
| 完整性 | OK |
"""


# ---- no silent drops --------------------------------------------------------

def test_unknown_subsection_rendered(tmp_path):
    html = _build(tmp_path)
    assert "自定义子节" in html
    assert "这个子节名字不在白名单里" in html


def test_section_without_subsections_rendered(tmp_path):
    html = _build(tmp_path)
    assert "金句一" in html
    assert "这里还有一段没有任何三级标题的正文" in html


def test_multiline_quote_joined_into_one_step(tmp_path):
    html = _build(tmp_path)
    assert "跨行的后半句" in html
    # joined into the same <p> as the first half, not dropped or split
    assert "回答， 跨行的后半句」" in html


def test_known_layers_still_render(tmp_path):
    html = _build(tmp_path)
    assert "section-insight" in html          # 核心洞察 callout
    assert "layer-analysis" in html           # 深度解析 heading
    assert 'class="timeline"' in html         # 对谈实录 timeline
    assert "一句话洞察" in html


# ---- block-level markdown ---------------------------------------------------

def test_ordered_list(tmp_path):
    html = _build(tmp_path)
    assert "<ol><li>有序一</li><li>有序二</li></ol>" in html


def test_blockquote_in_analysis(tmp_path):
    html = _build(tmp_path)
    assert "<blockquote><p>这是解析中的引用行。</p></blockquote>" in html


def test_fenced_code(tmp_path):
    html = _build(tmp_path)
    assert "<pre><code>print(&quot;hello&quot;)</code></pre>" in html


def test_italics(tmp_path):
    html = _build(tmp_path)
    assert "<em>斜体</em>" in html
    assert "<em>一本书</em>" in html          # bio italics handled natively


# ---- template ---------------------------------------------------------------

def test_speaker_tagging_is_generic(tmp_path):
    html = _build(tmp_path)
    assert "Harrison" not in html             # no hardcoded speaker names
    assert "names.includes" in html           # generic tagSpeakers present


def test_meta_and_selfcheck_panels(tmp_path):
    html = _build(tmp_path)
    assert 'id="文章元数据"' in html
    assert 'id="自检报告" hidden' in html
    assert 'id="延伸术语表"' in html


# ---- batch upgrade: diagram preservation ------------------------------------

FIG = '<figure class="diagram"><pre class="mermaid">flowchart LR\nA --> B</pre></figure>'
FIG2 = '<figure class="diagram"><pre class="mermaid">flowchart TD\nC --> D</pre></figure>'


def test_extract_and_inject_multiple_diagrams():
    old = '<h2 id="sec-a">A</h2>\n%s\n%s\n<p>x</p>' % (FIG, FIG2)
    diagrams = batch.extract_diagrams(old)
    assert batch.count_figures(diagrams) == 2

    rebuilt = '<h2 id="sec-a">A</h2>\n<p>x</p>'
    added, out = batch.inject_diagrams(rebuilt, diagrams)
    assert added == 2
    assert out.count('<figure class="diagram">') == 2
    # both figures sit between the h2 and the paragraph
    assert out.index("sec-a") < out.index("flowchart LR") < out.index("flowchart TD") < out.index("<p>x</p>")


def test_inject_skips_when_diagram_already_present():
    diagrams = {"sec-a": FIG}
    html_with_fig = '<h2 id="sec-a">A</h2>\n%s\n<p>x</p>' % FIG
    added, out = batch.inject_diagrams(html_with_fig, diagrams)
    assert added == 0
    assert out.count('<figure class="diagram">') == 1


# ---- debate variant / optional layers / extra meta tables -------------------

def test_core_conflict_uses_conflict_highlight(tmp_path):
    html = _build(tmp_path, DEBATE_MD, "debate_整理文档")
    assert "highlight-conflict" in html
    assert "双方对监管是否该提前介入无法达成共识" in html
    assert "highlight highlight-conflict" in html


def test_debate_layers_render(tmp_path):
    html = _build(tmp_path, DEBATE_MD, "debate_整理文档")
    assert "layer-clash" in html
    assert "应该先立法" in html
    assert "那会扼杀实验" in html
    assert "layer-context" in html
    assert "甲要的是事前规则" in html
    assert "section-open" in html
    assert "callout-warn" in html
    assert "现场没有给出可执行的折中" in html


def test_missing_dialogue_does_not_invent_timeline(tmp_path):
    html = _build(tmp_path, DEBATE_MD, "debate_整理文档")
    # 交锋小节 has 原声交锋 → one timeline; 无实录小节 must not add an empty one
    assert html.count('class="timeline"') == 1
    assert "只有分析，没有对谈实录层" in html
    assert "这节没有值得摘的对话" in html


def test_extra_metadata_table_keeps_heading(tmp_path):
    html = _build(tmp_path, DEBATE_MD, "debate_整理文档")
    assert "官方章节索引" in html
    assert "00:12" in html
    assert "开场" in html


def test_speaker_bio_opens_before_thesis(tmp_path):
    html = _build(tmp_path, DEBATE_MD, "debate_整理文档")
    bio_at = html.index('class="callout callout-info speaker-bio"')
    thesis_at = html.index('<h2 id="核心导读">')
    assert bio_at < thesis_at
    assert "李四是对谈嘉宾" in html

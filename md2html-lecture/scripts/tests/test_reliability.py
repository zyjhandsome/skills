"""Observable parsing and upgrade invariants, including failed rebuilds."""
import html
import json
import re
from html.parser import HTMLParser

import pytest

from test_build_html import FIG, SAMPLE_MD, SCRIPTS, _build, batch, build_html


@pytest.mark.parametrize("fence", ["```", "~~~~", "````"])
def test_fenced_headings_remain_literal_code(tmp_path, fence):
    code = "# CODE_TITLE\n## CODE_SECTION\n### CODE_LAYER\n[编者注：代码示例"
    source = SAMPLE_MD.replace('print("hello")', code).replace("```python", fence + "markdown").replace("\n```\n", "\n" + fence + "\n")
    output = _build(tmp_path, source)
    assert "<title>测试标题</title>" in output
    assert "<pre><code>%s</code></pre>" % html.escape(code) in output
    assert output.count('class="sec">') == 2
    _, sections = build_html.split_sections(source)
    assert not build_html.source_warnings(sections, [])


def test_shorter_fence_and_fence_with_trailing_text_do_not_close_code():
    lines = ["````markdown", "```", "## literal heading", "```` still code", "````", "after"]
    output = "\n".join(build_html.render_blocks(lines))
    assert "<pre><code>```\n## literal heading\n```` still code</code></pre>" in output
    assert "<p>after</p>" in output


@pytest.mark.parametrize("source,expected", [
    ("`**literal** [text](https://example.com)`", "<code>**literal** [text](https://example.com)</code>"),
    ("``a `tick` and *literal*``", "<code>a `tick` and *literal*</code>"),
    ("**重点 `*code*`**", "<strong>重点 <code>*code*</code></strong>"),
    ("[含 `**代码**` 的链接](https://example.com)", '<a href="https://example.com">含 <code>**代码**</code> 的链接</a>'),
])
def test_inline_code_is_not_reparsed(source, expected):
    assert build_html.inline(source) == expected


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


def test_link_attributes_are_escaped_and_executable_schemes_are_not_links():
    url = 'https://example.com/a"quoted?a=1&b=2'
    parser = LinkCollector()
    parser.feed(build_html.inline("[链接](%s)" % url))
    assert parser.links == [{"href": url}]
    for url in ("javascript:alert", "jAvAsCrIpT:alert", "javascript&#58;alert", "data:text/html,test"):
        parser = LinkCollector()
        parser.feed(build_html.inline("[保留文字](%s)" % url))
        assert not parser.links
    parser = LinkCollector()
    parser.feed(build_html.render_cell('https://example.com/a"quoted'))
    assert parser.links == [{"href": 'https://example.com/a"quoted'}]


def test_literal_template_tokens_are_not_replaced_in_content(tmp_path):
    output = _build(tmp_path, SAMPLE_MD.replace('print("hello")', "{{SOURCE_FILE}} {{HEADER_DEFAULTS}}"))
    assert "<pre><code>{{SOURCE_FILE}} {{HEADER_DEFAULTS}}</code></pre>" in output
    defaults = json.loads(batch.HEADER_DEFAULTS_RE.search(output).group(1))
    assert defaults["doc-title"] == "测试标题"


def test_duplicate_and_reserved_anchors_remain_unique(tmp_path):
    source = SAMPLE_MD + "\n## 普通小节A\n重复正文。\n## 普通小节A-analysis\n另一节。\n## main\n保留正文。\n"
    output = _build(tmp_path, source)
    parser = batch.PageStructure()
    parser.feed(output)
    assert not parser.duplicates
    assert "普通小节a" in parser.ids and "普通小节a-2" in parser.ids
    assert "main-2" in parser.ids
    assert set(parser.links) <= parser.ids
    assert parser.sections == 5


def test_heading_quotes_do_not_add_attributes(tmp_path):
    output = _build(tmp_path, SAMPLE_MD.replace("## 普通小节A", '## 标题"data-test="值'))
    parser = batch.PageStructure()
    parser.feed(output)
    assert '标题"data-test="值' in parser.ids
    assert 'id="标题&quot;data-test=&quot;值"' in output


def prepare_upgrade(tmp_path, source=SAMPLE_MD):
    output = _build(tmp_path, source)
    md = tmp_path / "sample_整理文档.md"
    target = md.with_suffix(".html")
    return md, target, output


def insert_figure(output, figure=FIG):
    return output.replace('class="sec">普通小节A</h2>', 'class="sec">普通小节A</h2>\n' + figure, 1)


def test_successful_upgrade_preserves_diagram_and_only_edited_header(tmp_path):
    md, target, output = prepare_upgrade(tmp_path)
    output = insert_figure(output).replace('<h1 class="doc-title">测试标题</h1>', '<h1 class="doc-title">手工标题</h1>')
    target.write_text(output, encoding="utf-8")
    md.write_text(SAMPLE_MD.replace("# 测试标题", "# 新源标题").replace("2026-09-01", "2026-10-09"), encoding="utf-8")
    result = batch.process_one(md, tmp_path, SCRIPTS / "build_html.py")
    assert result["ok"], result
    upgraded = target.read_text(encoding="utf-8")
    assert result["diagrams_restored"] == result["diagrams_saved"] == 1
    assert result["header_preserved"] == 1
    assert '<h1 class="doc-title">手工标题</h1>' in upgraded
    assert "<title>新源标题</title>" in upgraded
    assert batch.HEADER_PATTERNS["meta-date"].search(upgraded).group(2).strip() == "2026-10-09"
    assert upgraded.count(FIG) == 1
    assert upgraded.index("一句话洞察") < upgraded.index(FIG) < upgraded.index('id="普通小节a-analysis"')
    # Running it again preserves the same edit and does not duplicate figures.
    again = batch.process_one(md, tmp_path, SCRIPTS / "build_html.py")
    assert again["ok"], again
    assert target.read_text(encoding="utf-8") == upgraded
    assert not list(tmp_path.glob(".lecture-upgrade-*"))


def test_legacy_header_is_preserved_and_refresh_header_is_explicit(tmp_path):
    md, target, output = prepare_upgrade(tmp_path)
    output = batch.HEADER_DEFAULTS_RE.sub("", output).replace("测试标题", "旧页面人工标题")
    target.write_text(output, encoding="utf-8")
    result = batch.process_one(md, tmp_path, SCRIPTS / "build_html.py")
    assert result["ok"], result
    assert '<h1 class="doc-title">旧页面人工标题</h1>' in target.read_text(encoding="utf-8")
    result = batch.process_one(md, tmp_path, SCRIPTS / "build_html.py", refresh_header=True)
    assert result["ok"], result
    assert '<h1 class="doc-title">测试标题</h1>' in target.read_text(encoding="utf-8")


def test_renamed_section_does_not_replace_or_drop_old_diagrams(tmp_path):
    md, target, output = prepare_upgrade(tmp_path)
    target.write_text(insert_figure(output), encoding="utf-8")
    original = target.read_bytes()
    md.write_text(SAMPLE_MD.replace("## 普通小节A", "## 改名后的章节"), encoding="utf-8")
    result = batch.process_one(md, tmp_path, SCRIPTS / "build_html.py")
    assert not result["ok"]
    assert "diagram restoration incomplete: 0/1" in result["error"]
    assert target.read_bytes() == original
    assert not list(tmp_path.glob(".lecture-upgrade-*"))


def test_warning_is_reported_and_old_page_is_kept(tmp_path, capsys):
    md, target, _ = prepare_upgrade(tmp_path)
    original = target.read_bytes()
    md.write_text(SAMPLE_MD.replace("https://youtu.be/abc123", "未提供"), encoding="utf-8")
    assert batch.main([str(tmp_path)]) == 1
    stdout = capsys.readouterr().out
    assert "FAIL" in stdout and "WARN: no source URL" in stdout
    assert "old HTML kept" in stdout
    assert target.read_bytes() == original
    assert not list(tmp_path.glob(".lecture-upgrade-*"))


@pytest.mark.parametrize("body", [
    "from pathlib import Path\nimport sys\nPath(sys.argv[2]).write_text('partial', encoding='utf-8')\nraise SystemExit(1)\n",
    "from pathlib import Path\nimport sys\nPath(sys.argv[2]).write_text('partial', encoding='utf-8')\nprint('sections=2')\n",
])
def test_failed_or_incomplete_converter_cannot_overwrite_existing_page(tmp_path, body):
    md, target, _ = prepare_upgrade(tmp_path)
    original = target.read_bytes()
    converter = tmp_path / "broken.py"
    converter.write_text(body, encoding="utf-8")
    result = batch.process_one(md, tmp_path, converter)
    assert not result["ok"]
    assert target.read_bytes() == original
    assert not list(tmp_path.glob(".lecture-upgrade-*"))


def test_changed_page_is_not_overwritten_during_upgrade(tmp_path):
    md, target, _ = prepare_upgrade(tmp_path)
    converter = tmp_path / "concurrent.py"
    converter.write_text(
        "import runpy, sys\nfrom pathlib import Path\n"
        "source = Path(sys.argv[1])\n"
        "source.with_suffix('.html').write_text('concurrent edit', encoding='utf-8')\n"
        "sys.argv[0] = %r\nrunpy.run_path(sys.argv[0], run_name='__main__')\n" % str(SCRIPTS / "build_html.py"),
        encoding="utf-8",
    )
    result = batch.process_one(md, tmp_path, converter)
    assert not result["ok"]
    assert "changed during conversion" in result["error"]
    assert target.read_text(encoding="utf-8") == "concurrent edit"


def test_diagram_with_attributes_and_multiple_figures_survives(tmp_path):
    md, target, output = prepare_upgrade(tmp_path)
    custom = FIG.replace('class="diagram"', 'id="custom-figure" class="diagram annotated"')
    target.write_text(insert_figure(output, custom + "\n" + FIG), encoding="utf-8")
    result = batch.process_one(md, tmp_path, SCRIPTS / "build_html.py")
    assert result["ok"], result
    assert result["diagrams_restored"] == 2
    assert custom in target.read_text(encoding="utf-8")


def test_unassigned_diagram_is_not_silently_removed(tmp_path):
    md, target, output = prepare_upgrade(tmp_path)
    target.write_text(output.replace("<!-- CONTENT_START -->", "<!-- CONTENT_START -->\n" + FIG), encoding="utf-8")
    original = target.read_bytes()
    result = batch.process_one(md, tmp_path, SCRIPTS / "build_html.py")
    assert not result["ok"]
    assert "unassigned diagrams" in result["error"]
    assert target.read_bytes() == original


def test_legacy_duplicate_sections_cannot_receive_the_wrong_diagram(tmp_path):
    md, target, output = prepare_upgrade(tmp_path)
    duplicate = '<h2 id="普通小节a" class="sec">另一个旧章节</h2>\n' + FIG
    target.write_text(output.replace("<!-- CONTENT_END -->", duplicate + "\n<!-- CONTENT_END -->"), encoding="utf-8")
    original = target.read_bytes()
    result = batch.process_one(md, tmp_path, SCRIPTS / "build_html.py")
    assert not result["ok"]
    assert "ambiguous section ids" in result["error"]
    assert target.read_bytes() == original


def test_corrupt_header_snapshot_keeps_old_page(tmp_path):
    md, target, output = prepare_upgrade(tmp_path)
    target.write_text(batch.HEADER_DEFAULTS_RE.sub('<script type="application/json" id="lecture-header-defaults">broken</script>', output), encoding="utf-8")
    original = target.read_bytes()
    result = batch.process_one(md, tmp_path, SCRIPTS / "build_html.py")
    assert not result["ok"]
    assert target.read_bytes() == original


def test_batch_skips_unrelated_html_and_runs_nested_pairs(tmp_path):
    nested = tmp_path / "讲义 样例"
    nested.mkdir()
    md, target, _ = prepare_upgrade(nested)
    unrelated = tmp_path / "other.html"
    unrelated.write_text("<p>untouched</p>", encoding="utf-8")
    unrelated.with_suffix(".md").write_text("# unrelated", encoding="utf-8")
    assert batch.main([str(tmp_path)]) == 0
    assert target.exists()
    assert unrelated.read_text(encoding="utf-8") == "<p>untouched</p>"


def test_missing_intro_has_no_dead_toc_link(tmp_path, capsys):
    source = re.sub(r"## 核心导读.*?(?=## 目录)", "", SAMPLE_MD, flags=re.DOTALL)
    output = _build(tmp_path, source)
    assert '<a href="#核心导读"' not in output
    assert "WARN: missing required section「核心导读」" in capsys.readouterr().out

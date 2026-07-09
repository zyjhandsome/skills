#!/usr/bin/env python3
"""Convert a content-structuring "_整理文档.md" into the styled HTML format.

Usage:
    python build_html.py input.md [output.html]

The script performs the deterministic structural transform only. It does NOT
invent Mermaid diagrams — add those by hand after running (see SKILL.md).
"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")


# --------------------------------------------------------------------------
# Inline + helpers
# --------------------------------------------------------------------------
def inline(s):
    """Render markdown inline syntax to HTML (bold / code / links)."""
    out = html.escape(s, quote=False)
    out = re.sub(r"`([^`]+?)`", lambda m: "<code>%s</code>" % m.group(1), out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\[([^\]]+?)\]\(([^)]+?)\)", r'<a href="\2">\1</a>', out)
    return out.strip()


def strip_md(s):
    """Plain text: drop bold markers and inline code ticks."""
    return re.sub(r"[*`]", "", s).strip()


def slugify(title):
    s = strip_md(title).strip().lower()
    s = s.replace(".", "")
    s = re.sub(r"[\s：:、，,。；;/()（）【】\[\]—–·]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def split_row(row):
    """Split a markdown table row on unescaped pipes."""
    cells = re.split(r"(?<!\\)\|", row.strip())
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.replace("\\|", "|").strip() for c in cells]


def render_cell(cell):
    if re.match(r"^https?://\S+$", cell):
        text = "YouTube 原视频" if "youtu" in cell else "原文链接"
        return '<a href="%s">%s</a>' % (cell, text)
    return inline(cell)


def render_table(lines):
    """lines: markdown table lines (header, separator, body...)."""
    rows = [split_row(l) for l in lines if l.strip().startswith("|")]
    if len(rows) < 2:
        return ""
    header, body = rows[0], rows[2:]
    th = "".join("<th>%s</th>" % inline(c) for c in header)
    out = ["<table><thead><tr>%s</tr></thead><tbody>" % th]
    for r in body:
        tds = "".join("<td>%s</td>" % render_cell(c) for c in r)
        out.append("<tr>%s</tr>" % tds)
    out.append("</tbody></table>")
    return "".join(out)


def paragraphs(lines):
    """Group consecutive non-blank lines into <p> blocks."""
    blocks, cur = [], []
    for l in lines:
        if l.strip() == "" or re.fullmatch(r"-{3,}|\*{3,}|_{3,}", l.strip()):
            if cur:
                blocks.append(" ".join(cur))
                cur = []
        else:
            cur.append(l.strip())
    if cur:
        blocks.append(" ".join(cur))
    return ["<p>%s</p>" % inline(b) for b in blocks]


def _is_table_separator(line):
    s = line.strip()
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", s)) and "-" in s and "|" in s


def render_blocks(lines):
    """Render a body into <p>, markdown tables, and bullet lists.

    Blocks are separated by blank lines / horizontal rules. Each block is
    classified: a pipe row followed by a separator row → table; lines all
    starting with '- '/'* ' → unordered list; otherwise a paragraph.
    """
    out, block = [], []

    def flush():
        if not block:
            return
        if len(block) >= 2 and block[0].strip().startswith("|") and _is_table_separator(block[1]):
            out.append('<div class="table-wrap">%s</div>' % render_table(block))
        elif all(re.match(r"^\s*[-*]\s+\S", l) for l in block):
            items = "".join(
                "<li>%s</li>" % inline(re.sub(r"^\s*[-*]\s+", "", l).strip())
                for l in block
            )
            out.append("<ul>%s</ul>" % items)
        else:
            out.append("<p>%s</p>" % inline(" ".join(l.strip() for l in block)))

    for l in lines:
        if l.strip() == "" or re.fullmatch(r"-{3,}|\*{3,}|_{3,}", l.strip()):
            flush()
            block = []
        else:
            block.append(l)
    flush()
    return out


def blockquote_text(lines, strip_label=False):
    """Join consecutive '> ' lines; optionally drop a leading '**label**：'."""
    qs = [re.sub(r"^>\s?", "", l) for l in lines if l.strip().startswith(">")]
    text = " ".join(q.strip() for q in qs)
    if strip_label:
        text = re.sub(r"^\*\*[^*]+\*\*[：:]\s*", "", text)
    return text


def count_cjk(text):
    return len(re.findall(r"[\u4e00-\u9fff]", text))


# --------------------------------------------------------------------------
# Section model
# --------------------------------------------------------------------------
def split_sections(md):
    """Return (title, [(h2_title, [body_lines]), ...])."""
    lines = md.splitlines()
    title = ""
    sections = []
    cur_title, cur_body = None, []
    for l in lines:
        if l.startswith("# ") and not l.startswith("## "):
            title = strip_md(l[2:])
            continue
        if l.startswith("## "):
            if cur_title is not None:
                sections.append((cur_title, cur_body))
            cur_title, cur_body = l[3:].strip(), []
        elif cur_title is not None:
            cur_body.append(l)
    if cur_title is not None:
        sections.append((cur_title, cur_body))
    return title, sections


def split_subsections(body):
    """Split a content section body by '### ' headings -> {name: [lines]}."""
    subs, cur = {}, None
    for l in body:
        if l.startswith("### "):
            cur = l[4:].strip()
            subs[cur] = []
        elif cur is not None:
            subs[cur].append(l)
    return subs


def render_steps(lines):
    steps, n = [], 0
    for l in lines:
        if l.strip() == "":
            continue
        m = re.match(r"^\*\*(.+?)\*\*[：:]\s*(.*)$", l.strip())
        if not m:
            continue
        n += 1
        name, quote = m.group(1).strip(), m.group(2).strip()
        steps.append(
            "  <article class=\"step\">\n"
            "    <div class=\"step-num\">%d</div>\n"
            "    <div class=\"step-body\">\n"
            "      <h3>%s</h3>\n"
            "      <p>%s</p>\n"
            "    </div>\n"
            "  </article>" % (n, inline(name), inline(quote))
        )
    return steps


def render_content_section(title, body):
    sid = slugify(title)
    subs = split_subsections(body)
    out = ['<h2 id="%s">%s</h2>\n' % (sid, inline(title))]

    if "核心洞察" in subs:
        insight = blockquote_text(subs["核心洞察"])
        out.append(
            '<h3 id="%s-insight" class="layer-heading layer-insight">核心洞察</h3>\n'
            '<div class="callout callout-tip section-insight">\n'
            '  <svg class="callout-icon" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-tip"/></svg>\n'
            '  <div class="callout-body"><p>%s</p></div>\n'
            "</div>" % (sid, inline(insight))
        )
    if "深度解析" in subs:
        out.append(
            '<h3 id="%s-analysis" class="layer-heading layer-analysis">深度解析</h3>' % sid
        )
        out.append("\n".join(render_blocks(subs["深度解析"])))
    if "对谈实录" in subs:
        out.append(
            '<h3 id="%s-dialogue" class="layer-heading layer-dialogue">对谈实录</h3>' % sid
        )
        steps = render_steps(subs["对谈实录"])
        out.append('<div class="timeline">\n%s\n</div>' % "\n".join(steps))
    return "\n".join(out), sid, count_cjk(" ".join(body))


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
SKIP_TITLES = {"目录"}


def build(md_path, out_path):
    md = open(md_path, encoding="utf-8").read()
    doc_title, sections = split_sections(md)

    meta = {}            # metadata table key -> raw value
    bio_label = ""       # 人物背景 / 讲者背景 (from blockquote label)
    bio_body = ""        # bio text with label stripped
    source_url = ""
    intro_html = ""
    subtitle = ""
    glossary_html = ""
    selfcheck_html = ""
    content_sections = []   # (html, sid, title)
    cjk_total = 0

    for title, body in sections:
        if title in SKIP_TITLES:
            continue
        if title == "文章元数据":
            tbl_lines = [l for l in body if l.strip().startswith("|")]
            for r in [split_row(l) for l in tbl_lines][2:]:
                if len(r) >= 2:
                    meta[strip_md(r[0])] = r[1]
            for v in meta.values():
                m = re.search(r"https?://\S+", v)
                if m and not source_url:
                    source_url = m.group(0)
            q = [l for l in body if l.strip().startswith(">")]
            if q:
                raw = blockquote_text(q)
                lm = re.match(r"^\*\*([^*]+)\*\*[：:]\s*", raw)
                bio_label = lm.group(1).strip() if lm else "人物背景"
                bio_body = blockquote_text(q, strip_label=True)
            continue
        if title == "核心导读":
            quote = blockquote_text(body, strip_label=True)
            rest = [l for l in body if not l.strip().startswith(">")]
            paras = paragraphs(rest)
            intro_html = (
                '<h2 id="核心导读">核心导读</h2>\n\n'
                '<div class="highlight">\n  <p>%s</p>\n</div>\n\n%s'
                % (inline(quote), "\n\n".join(paras))
            )
            subtitle = strip_md(re.split(r"[；。]", quote)[0]).strip()
            if subtitle and not subtitle.endswith("。"):
                subtitle += "。"
            cjk_total += count_cjk(quote + " ".join(rest))
            continue
        if title == "延伸术语表":
            glossary_html = (
                '<details class="collapsible meta-panel" id="延伸术语表">\n'
                "  <summary>延伸术语表</summary>\n"
                '  <div class="collapsible-body">\n'
                '<div class="table-wrap">%s</div>\n'
                "  </div>\n</details>" % render_table(body)
            )
            continue
        if title == "自检报告":
            selfcheck_html = (
                '<h2 id="自检报告" hidden>自检报告</h2>\n\n'
                '<details class="collapsible">\n'
                "  <summary>展开自检报告详情</summary>\n"
                '  <div class="collapsible-body">\n'
                '    <div class="table-wrap">\n    %s\n    </div>\n'
                "  </div>\n</details>" % render_table(body)
            )
            continue
        # regular content section
        sec_html, sid, n = render_content_section(title, body)
        content_sections.append((sec_html, sid, title))
        cjk_total += n

    # ---- speaker / people bio (opens the article, before 核心导读) ----
    bio_html = ""
    if bio_body:
        bio_html = (
            '<aside class="callout callout-info speaker-bio" id="人物背景" '
            'aria-label="%s">\n'
            '  <svg class="callout-icon" viewBox="0 0 24 24" aria-hidden="true">'
            '<use href="#i-info"/></svg>\n'
            '  <div class="callout-body">\n'
            '    <p class="callout-title">%s</p>\n'
            "    <p>%s</p>\n"
            "  </div>\n"
            "</aside>"
            % (html.escape(bio_label, quote=True), inline(bio_label), inline(bio_body))
        )
        cjk_total += count_cjk(bio_body)

    # ---- metadata collapsible (table only; bio already at top) ----
    meta_lines = []
    for title, body in sections:
        if title == "文章元数据":
            meta_lines = [l for l in body if l.strip().startswith("|")]
            break
    metadata_html = ""
    if meta_lines:
        metadata_html = (
            '<details class="collapsible meta-panel" id="文章元数据">\n'
            "  <summary>文章元数据与来源</summary>\n"
            '  <div class="collapsible-body">\n'
            '<div class="table-wrap">%s</div>\n'
            "  </div>\n</details>" % render_table(meta_lines)
        )

    # ---- assemble content ----
    # Order: bio (who) → 核心导读 (thesis) → sections → glossary / meta / selfcheck
    parts = []
    if bio_html:
        parts.append(bio_html)
    if intro_html:
        parts.append(intro_html)
    parts += [s[0] for s in content_sections]
    if glossary_html:
        parts.append(glossary_html)
    if metadata_html:
        parts.append(metadata_html)
    if selfcheck_html:
        parts.append(selfcheck_html)
    content = "\n\n".join(p for p in parts if p)

    # ---- TOC (lvl-2 only) ----
    toc = []
    if bio_html:
        toc.append(
            '        <a href="#人物背景" class="lvl-2">%s</a>' % inline(bio_label or "人物背景")
        )
    toc.append('        <a href="#核心导读" class="lvl-2">核心导读</a>')
    for _, sid, t in content_sections:
        toc.append('        <a href="#%s" class="lvl-2">%s</a>' % (sid, inline(t)))
    if glossary_html:
        toc.append('        <a href="#延伸术语表" class="lvl-2">延伸术语表</a>')
    if metadata_html:
        toc.append('        <a href="#文章元数据" class="lvl-2 toc-meta-link">来源与元数据</a>')
    toc_html = "\n".join(toc)

    # ---- header fields ----
    activity = strip_md(meta.get("活动", "") or meta.get("节目", ""))
    activity_short = re.split(r"——|—|--", activity)[0].strip()
    # Prefer 核心人物; fall back to 对谈人物 / 讲者 (common in podcast notes)
    people_raw = (
        meta.get("核心人物", "")
        or meta.get("对谈人物", "")
        or meta.get("讲者", "")
    )
    people = []
    for p in re.split(r"[；;]|×", strip_md(people_raw)):
        name = re.split(r"[（(]", p)[0].strip()
        if name:
            people.append(name)
    people_str = " × ".join(people)
    if not activity_short:
        # Derive a short show name from 原标题 when 活动 is absent
        # e.g. "On Purpose with Jay Shetty — Lucy Guo on ..." → "On Purpose"
        orig = strip_md(meta.get("原标题", ""))
        head = re.split(r"\s*[—–]\s*", orig)[0].strip() if orig else ""
        if re.search(r"\s+with\s+", head, re.I):
            activity_short = re.split(r"\s+with\s+", head, flags=re.I)[0].strip()
        else:
            activity_short = head
    if activity_short and people_str:
        meta_source = "%s · %s" % (activity_short, people_str)
    elif people_str:
        meta_source = people_str
    else:
        meta_source = strip_md(meta.get("原标题", "")) or doc_title

    meta_date = strip_md(meta.get("发布时间", ""))
    read_min = max(1, round(cjk_total / 300))
    read_time = "~%d 分钟阅读" % read_min

    struct = meta.get("文稿结构", "")
    eyebrow = "对谈笔记" if ("对谈" in struct or "访谈" in struct or len(people) >= 2) else "整理笔记"

    # ---- render template ----
    tpl = open(TEMPLATE, encoding="utf-8").read()
    repl = {
        "{{TITLE}}": html.escape(doc_title, quote=False),
        "{{EYEBROW}}": html.escape(eyebrow, quote=False),
        "{{SUBTITLE}}": html.escape(subtitle, quote=False),
        "{{META_SOURCE}}": html.escape(meta_source, quote=False),
        "{{META_DATE}}": html.escape(meta_date, quote=False),
        "{{META_READTIME}}": html.escape(read_time, quote=False),
        "{{TOC}}": toc_html,
        "{{CONTENT}}": content,
        "{{SOURCE_URL}}": source_url or "#",
        "{{SOURCE_FILE}}": html.escape(os.path.basename(md_path), quote=False),
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)

    open(out_path, "w", encoding="utf-8").write(tpl)
    print("Wrote %s" % out_path)
    print("  sections=%d  cjk=%d  read=%s" % (len(content_sections), cjk_total, read_time))
    if not source_url:
        print("  WARN: no source URL found in 文章元数据")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    md_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(md_path)[0] + ".html"
    build(md_path, out_path)


if __name__ == "__main__":
    main()

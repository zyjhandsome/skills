# -*- coding: utf-8 -*-
"""Rebuild an editorial 成稿 Markdown from a published `*_公众号文章.html`.

Use this when a WeChat article must be revised after its temporary 成稿 was
deleted (the normal end of a delivery). It walks the pasted `#wechat-article`
block that `build_wechat_html.py --mode editorial` emitted and writes the
Markdown that would regenerate the same article:

    # H1
    ## 文章元数据          (copied from --source if given; else 原标题 from the footer)
    | 原标题 | … |
    > **人物背景**：…
    ## 核心导读
    > **全文论点**：…
    ## 读者向 H2 …         (section kickers「第 N 节」are dropped; the builder re-adds them)
    > 洞察卡 → blockquote, 对话卡 → **全名**：「…」, ==荧光笔==, **加粗**, `code`, [链接](url)

It is a reconstruction aid, not a second content source: edit the draft,
rebuild with `--source <整理文档.md>`, re-validate, then delete the draft.
Only HTML produced by this skill is supported; anything else is rejected.
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_wechat_html import C  # noqa: E402

FOOTER_LABEL = "来源与说明"
BIO_LABEL = "人物背景"
THESIS_LABEL = "全文论点"
KICKER_RE = re.compile(r"^第 \d+ 节$")


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: dict[str, str], parent: "Node | None"):
        self.tag = tag
        self.attrs = attrs
        self.children: list["Node | str"] = []
        self.parent = parent

    @property
    def style(self) -> str:
        return self.attrs.get("style", "")

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def find_all(self, tag: str) -> list["Node"]:
        out: list[Node] = []
        for c in self.children:
            if isinstance(c, Node):
                if c.tag == tag:
                    out.append(c)
                out.extend(c.find_all(tag))
        return out


class TreeBuilder(HTMLParser):
    VOID = {"br", "img", "hr", "meta", "link", "input"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(node)
        if tag not in self.VOID:
            self.cur = node

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(html: str) -> Node:
    tb = TreeBuilder()
    tb.feed(html)
    return tb.root


def find_article(root: Node) -> Node:
    for sec in root.find_all("section"):
        if sec.attrs.get("id") == "wechat-article":
            return sec
    raise SystemExit("not a md2wechat article: missing <section id=\"wechat-article\">")


# ---------------------------------------------------------------- inline


def inline_md(node: Node) -> str:
    """Element → Markdown inline text (**bold**, ==mark==, `code`, [a](url))."""
    parts: list[str] = []
    for c in node.children:
        if isinstance(c, str):
            parts.append(c)
            continue
        if c.tag == "strong":
            parts.append(f"**{inline_md(c)}**")
        elif c.tag == "code":
            parts.append(f"`{c.text()}`")
        elif c.tag == "a":
            parts.append(f"[{inline_md(c)}]({c.attrs.get('href', '')})")
        elif c.tag == "span" and f"background:{C['accent_soft']}" in c.style and "padding:0 4px" in c.style:
            parts.append(f"=={inline_md(c)}==")
        elif c.tag == "br":
            parts.append("\n")
        else:
            parts.append(inline_md(c))
    return "".join(parts)


def para_md(p: Node) -> str:
    return re.sub(r"[ \t]+", " ", inline_md(p)).strip()


# ---------------------------------------------------------------- blocks


def classify_section(sec: Node) -> tuple[str, list[str]]:
    """Return (kind, payload) for a <section> card inside the article."""
    ps = [c for c in sec.children if isinstance(c, Node) and c.tag == "p"]
    texts = [para_md(p) for p in ps]
    first_plain = ps[0].text().strip() if ps else ""
    if first_plain == FOOTER_LABEL:
        title = ""
        for t in texts[1:]:
            m = re.match(r"原文：(.*)$", t)
            if m:
                title = m.group(1).strip()
        return "footer", [title]
    if first_plain == BIO_LABEL:
        return "bio", texts[1:]
    if first_plain == THESIS_LABEL:
        return "thesis", texts[1:]
    if len(ps) == 2 and any(
        isinstance(s, Node) and "padding:0 8px" in s.style for s in ps[0].find_all("span")
    ):
        return "dialogue", [ps[0].text().strip(), texts[1]]
    if len(ps) == 1:
        return "insight", texts
    return "unknown", texts


def table_md(tbl: Node) -> list[str]:
    rows: list[list[str]] = []
    for tr in tbl.find_all("tr"):
        cells = [
            para_md(td).replace("|", "\\|")
            for td in tr.children
            if isinstance(td, Node) and td.tag in ("td", "th")
        ]
        if cells:
            rows.append(cells)
    if not rows:
        return []
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return out


def article_to_md(article: Node) -> tuple[str, list[str], str, list[str], list[str]]:
    """→ (h1, body_lines, 原标题, bio_paragraphs, warnings)."""
    h1 = ""
    body: list[str] = []
    bio: list[str] = []
    source_title = ""
    warnings: list[str] = []
    seen_h1 = False

    for node in article.children:
        if isinstance(node, str):
            continue
        tag = node.tag
        if tag == "h1":
            h1 = node.text().strip()
            seen_h1 = True
            continue
        if tag == "h2":
            body += ["", f"## {node.text().strip()}", ""]
            continue
        if tag == "h3":
            body += ["", f"### {node.text().strip()}", ""]
            continue
        if tag == "p":
            txt = para_md(node)
            if not txt:
                continue
            if KICKER_RE.match(node.text().strip()):
                continue  # builder re-adds「第 N 节」
            if seen_h1 and not body and "text-align:center" in node.style:
                continue  # byline derived from metadata
            body.append(txt)
            body.append("")
            continue
        if tag == "section":
            kind, payload = classify_section(node)
            if kind == "footer":
                source_title = payload[0]
                break
            if kind == "bio":
                bio = payload
            elif kind == "thesis":
                body += [f"> **{THESIS_LABEL}**：{' '.join(payload)}", ""]
            elif kind == "insight":
                body += [f"> {payload[0]}", ""]
            elif kind == "dialogue":
                body += [f"**{payload[0]}**：「{payload[1]}」", ""]
            else:
                warnings.append(f"unrecognised card dropped: {' / '.join(payload)[:60]}")
            continue
        if tag == "table":
            body += table_md(node) + [""]
            continue
        warnings.append(f"unhandled <{tag}> dropped: {node.text().strip()[:60]}")

    if not h1:
        raise SystemExit("not a md2wechat article: no <h1> inside #wechat-article")
    # collapse runs of blank lines
    out: list[str] = []
    for line in body:
        if line == "" and out and out[-1] == "":
            continue
        out.append(line)
    return h1, out, source_title, bio, warnings


def meta_table_from_source(source: Path) -> list[str]:
    lines = source.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    grab = False
    for line in lines:
        if line.startswith("## "):
            if grab:
                break
            grab = line[3:].strip() == "文章元数据"
            continue
        if grab and line.startswith("|"):
            out.append(line)
    return out


def build_draft(html_path: Path, source: Path | None) -> tuple[str, list[str]]:
    article = find_article(parse(html_path.read_text(encoding="utf-8")))
    h1, body, source_title, bio, warnings = article_to_md(article)

    meta: list[str]
    if source is not None:
        meta = meta_table_from_source(source)
        if not meta:
            warnings.append(f"--source has no 文章元数据 table: {source.name}")
    else:
        meta = []
    if not meta:
        esc_title = source_title.replace("|", "\\|")
        meta = ["| 项目 | 内容 |", "|---|---|", f"| 原标题 | {esc_title} |"]
        warnings.append(
            "metadata table rebuilt from the footer only (no 讲者/内容来源 → no byline); "
            "pass --source <整理文档.md> to copy the real table"
        )

    draft = [f"# {h1}", "", "## 文章元数据", "", *meta, ""]
    if bio:
        draft.append(f"> **{BIO_LABEL}**：{' '.join(bio)}")
        draft.append("")
    draft += body
    text = "\n".join(draft).rstrip() + "\n"
    return text, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path, help="*_公众号文章.html produced by build_wechat_html.py")
    ap.add_argument("--out", type=Path, required=True, help="where to write the reconstructed 成稿 .md (use a temp dir)")
    ap.add_argument("--source", type=Path, help="整理文档.md; its 文章元数据 table is copied verbatim")
    args = ap.parse_args(argv)

    text, warnings = build_draft(args.html, args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    n_h2 = sum(1 for line in text.splitlines() if line.startswith("## "))
    print(f"wrote {args.out} | H2 {n_h2} | {len(text)} chars")
    for w in warnings:
        print("WARN", w)
    print("NOTE reconstruction only: edit, rebuild with --source, validate, then delete the draft")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

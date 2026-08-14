#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build WeChat Official Account paste-ready HTML from 整理文档 Markdown."""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

C = {
    "bg": "#FAFAF7",
    "text": "#1A1A1A",
    "muted": "#4A4A45",
    "subtle": "#6B6B66",
    "accent": "#D97757",
    "accent_soft": "#FBEEE6",
    "accent_border": "#F0D5C4",
    "accent_strong": "#A85533",
    "surface": "#FFFFFF",
    "border": "#E5E4DC",
    "code_bg": "#F5F2EC",
}

FONT = (
    "-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB',"
    "'Microsoft YaHei','Noto Sans CJK SC',sans-serif"
)

OMIT_H2 = {"延伸术语表", "目录", "自检报告"}

# 整理文档「内容来源」常把抓取流水账写进同一格；公众号只留读者能看懂的场次/平台。
_PROCESS_MARKERS = (
    "用户提供",
    "次要核对",
    "字幕转写",
    "逐字稿",
    "WebFetch",
    "WebSearch",
    "浏览器 MCP",
    "MCP 不可用",
    "已降级",
    "页面抓取",
    "页面口径",
    "自动生成字幕",
    "YouTube 描述",
    "元数据抓取",
    "自检",
    "主源",
    "次要：",
    "核对：",
)

_PROCESS_PAREN = re.compile(
    r"[（(][^）)]*(?:口径|标注|抓取|用户提供|推算|WebFetch|MCP|次要|字幕|快照)[^）)]*[）)]"
)
_EDITOR_NOTE = re.compile(r"\[编者注：[^\]]*\]|（编者注：[^）]*）")


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def _inline_no_link(text: str) -> str:
    s = esc(text)

    def bold(m: re.Match) -> str:
        return (
            f'<strong style="font-weight:700;color:{C["text"]};">'
            f"{m.group(1)}</strong>"
        )

    s = re.sub(r"\*\*(.+?)\*\*", bold, s)

    def code(m: re.Match) -> str:
        return (
            f'<code style="padding:1px 5px;background:{C["code_bg"]};'
            f'border-radius:3px;font-size:13px;color:#2A2A2A;">'
            f"{m.group(1)}</code>"
        )

    return re.sub(r"`([^`]+)`", code, s)


def inline_md_raw(text: str) -> str:
    parts: list[str] = []
    pos = 0
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        parts.append(_inline_no_link(text[pos : m.start()]))
        label = _inline_no_link(m.group(1))
        url = esc(m.group(2))
        parts.append(
            f'<a href="{url}" style="color:{C["accent_strong"]};'
            f'text-decoration:underline;">{label}</a>'
        )
        pos = m.end()
    parts.append(_inline_no_link(text[pos:]))
    return "".join(parts)


def p(text: str, size: str = "15px", color: str | None = None, mb: str = "12px") -> str:
    color = color or C["text"]
    text = strip_editor_notes(text)
    if text.startswith(">"):
        text = strip_bq(text)
    if not text:
        return ""
    return (
        f'<p style="margin:0 0 {mb};padding:0;font-size:{size};'
        f'line-height:1.75;color:{color};">{inline_md_raw(text)}</p>'
    )


def h1(text: str) -> str:
    return (
        f'<h1 style="margin:0 0 12px;padding:0;font-size:22px;font-weight:700;'
        f'line-height:1.45;color:{C["text"]};text-align:center;">'
        f"{esc(text)}</h1>"
    )


def h2(text: str) -> str:
    return (
        f'<h2 style="margin:28px 0 14px;padding:10px 0 8px;font-size:18px;'
        f'font-weight:700;line-height:1.4;color:{C["text"]};'
        f'border-bottom:2px solid {C["accent_border"]};">{esc(text)}</h2>'
    )


def h3(text: str) -> str:
    return (
        f'<h3 style="margin:16px 0 10px;padding:0;font-size:15px;font-weight:700;'
        f'color:{C["accent_strong"]};">{esc(text)}</h3>'
    )


def insight_card(quote: str) -> str:
    return (
        f'<section style="margin:0 0 14px;padding:12px 14px;background:{C["surface"]};'
        f'border:1px solid {C["accent_border"]};border-radius:8px;">'
        f'<p style="margin:0;padding:0;font-size:15px;line-height:1.65;'
        f'color:{C["text"]};">{inline_md_raw(quote)}</p></section>'
    )


def thesis_card(label: str, body: str) -> str:
    return (
        f'<section style="margin:0 0 18px;padding:16px 16px 14px;'
        f'background:{C["accent_soft"]};border-left:4px solid {C["accent"]};'
        f'border-radius:0 8px 8px 0;">'
        f'<p style="margin:0 0 8px;padding:0;font-size:12px;font-weight:600;'
        f'color:{C["accent_strong"]};letter-spacing:0.08em;">{esc(label)}</p>'
        f'<p style="margin:0;padding:0;font-size:15px;line-height:1.7;'
        f'color:{C["text"]};">{inline_md_raw(body)}</p></section>'
    )


def bio_card(text: str) -> str:
    return (
        f'<section style="margin:0 0 20px;padding:14px 16px;background:{C["surface"]};'
        f'border:1px solid {C["border"]};border-radius:8px;">'
        f'<p style="margin:0 0 6px;padding:0;font-size:12px;font-weight:600;'
        f'color:{C["accent_strong"]};">人物背景</p>'
        f'<p style="margin:0;padding:0;font-size:14px;line-height:1.7;'
        f'color:{C["muted"]};">{inline_md_raw(text)}</p></section>'
    )


def dialogue_card(speaker: str, quote: str) -> str:
    return (
        f'<section style="margin:0 0 8px;padding:12px 14px;background:{C["surface"]};'
        f'border-radius:8px;border:1px solid {C["border"]};">'
        f'<p style="margin:0;padding:0;font-size:14px;line-height:1.7;'
        f'color:{C["muted"]};">'
        f'<span style="display:inline-block;margin-right:6px;padding:1px 8px;'
        f'background:{C["accent_soft"]};color:{C["accent_strong"]};font-size:12px;'
        f'border-radius:4px;font-weight:600;">{esc(speaker)}</span>'
        f"{inline_md_raw(quote)}</p></section>"
    )


def strip_bq(line: str) -> str:
    return re.sub(r"^>\s?", "", line).strip()


_SPEAKER_QUOTE = re.compile(
    r"^\*\*([^*]+)\*\*[：:]\s*[「\"](.+)[」\"]\s*$"
)


def render_body_line(line: str, *, size: str = "15px", color: str | None = None) -> str:
    raw = strip_bq(line.strip()) if line.strip().startswith(">") else line.strip()
    m = _SPEAKER_QUOTE.match(raw)
    if m:
        return dialogue_card(m.group(1), m.group(2))
    return p(raw, size=size, color=color)


def bare(s: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", s).strip()


_SEP_ROW = re.compile(r"^\|[\s\-:|]+\|$")


def is_pipe_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def is_sep_row(line: str) -> bool:
    return bool(_SEP_ROW.match(line.strip()))


def split_cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _td(text: str, *, header: bool = False, first_col: bool = False) -> str:
    """WeChat paste keeps td+inline styles more reliably than th / CSS classes."""
    bg = C["accent_soft"] if header else C["surface"]
    color = C["accent_strong"] if header else C["text"]
    weight = "700" if header or first_col else "400"
    size = "13px" if header else "14px"
    border = C["accent_border"] if header else C["border"]
    return (
        f'<td style="padding:8px 10px;background:{bg};color:{color};'
        f'font-size:{size};font-weight:{weight};line-height:1.55;'
        f'text-align:left;vertical-align:top;border:1px solid {border};'
        f'word-break:break-word;">{inline_md_raw(text)}</td>'
    )


def render_table_cards(header: list[str], rows: list[list[str]]) -> str:
    """Wide tables (≥5 cols) → stacked cards; native tables overflow on phone."""
    parts: list[str] = []
    for row in rows:
        inner: list[str] = []
        for j, cell in enumerate(row):
            label = header[j] if j < len(header) else ""
            if j == 0:
                inner.append(
                    f'<p style="margin:0 0 6px;padding:0;font-size:15px;'
                    f'font-weight:700;color:{C["text"]};">{inline_md_raw(cell)}</p>'
                )
            else:
                inner.append(
                    f'<p style="margin:0 0 4px;padding:0;font-size:13px;'
                    f'line-height:1.65;color:{C["muted"]};">'
                    f'<span style="color:{C["accent_strong"]};font-weight:600;">'
                    f"{inline_md_raw(label)}</span>　{inline_md_raw(cell)}</p>"
                )
        parts.append(
            f'<section style="margin:0 0 10px;padding:12px 14px;'
            f'background:{C["surface"]};border:1px solid {C["border"]};'
            f'border-radius:8px;">{"".join(inner)}</section>'
        )
    return "".join(parts)


def render_wechat_table(header: list[str], rows: list[list[str]]) -> str:
    ncols = max(len(header), 1)
    if ncols >= 5:
        return render_table_cards(header, rows)
    trs = ["<tr>" + "".join(_td(h, header=True) for h in header) + "</tr>"]
    for row in rows:
        padded = row + [""] * (ncols - len(row))
        cells = "".join(
            _td(c, first_col=(j == 0)) for j, c in enumerate(padded[:ncols])
        )
        trs.append(f"<tr>{cells}</tr>")
    return (
        f'<section style="margin:0 0 16px;padding:0;overflow:hidden;'
        f'border-radius:8px;">'
        f'<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;'
        f'width:100%;margin:0;font-size:14px;font-family:{FONT};">'
        f"{''.join(trs)}</table></section>"
    )


def try_parse_gfm_table(lines: list[str], start: int) -> tuple[str | None, int]:
    """Consume a GFM table. Returns (html, next_index) or (None, start)."""
    if start >= len(lines) or not is_pipe_row(lines[start]):
        return None, start
    raw: list[str] = []
    i = start
    while i < len(lines) and is_pipe_row(lines[i]):
        raw.append(lines[i])
        i += 1
    if len(raw) < 2:
        return None, start
    cells_list: list[list[str]] = []
    for row in raw:
        if is_sep_row(row):
            continue
        cells_list.append(split_cells(row))
    if not cells_list:
        return None, start
    header = cells_list[0]
    body = cells_list[1:]
    ncols = len(header)
    norm = []
    for r in body:
        if len(r) < ncols:
            r = r + [""] * (ncols - len(r))
        norm.append(r[:ncols])
    return render_wechat_table(header, norm), i


def parse_meta_table(lines: list[str], start: int) -> tuple[dict[str, str], int]:
    meta: dict[str, str] = {}
    i = start
    while i < len(lines) and lines[i].startswith("|"):
        row = lines[i]
        i += 1
        if re.match(r"^\|[\s\-:|]+\|$", row.strip()):
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 2 and bare(cells[0]) not in ("项目",):
            meta[bare(cells[0])] = cells[1]
    return meta, i


def public_source_line(src: str) -> str:
    """Keep venue/platform; drop pipeline notes (字幕核对 / MCP 降级 etc.)."""
    if not src:
        return ""
    src = _EDITOR_NOTE.sub("", src)
    parts = re.split(r"[；;]", src)
    keep: list[str] = []
    for part in parts:
        chunk = part.strip().strip("。")
        if not chunk:
            continue
        if any(m in chunk for m in _PROCESS_MARKERS):
            continue
        keep.append(chunk)
    line = "；".join(keep)
    line = re.sub(r"\s+", " ", line).strip(" ；;、")
    return line[:80]


def public_date(date: str) -> str:
    """ISO/public date only; drop 页面口径 vs 文稿标注 parentheticals."""
    if not date:
        return ""
    s = _PROCESS_PAREN.sub("", date)
    s = re.sub(r"\s+", " ", s).strip(" ；;、")
    return s


def strip_editor_notes(text: str) -> str:
    s = _EDITOR_NOTE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def source_footer(meta: dict[str, str]) -> str:
    """Keep only first two source lines: 原文 + 视频/内容链接."""
    title = bare(meta.get("原标题", "") or meta.get("标题", ""))
    date = public_date(bare(meta.get("发布时间", "")))
    link = bare(meta.get("内容链接", "") or meta.get("视频链接", "") or meta.get("链接", ""))
    line1 = "原文：" + (title if title else "（见正文来源）")
    if date:
        line1 += f"（{date}）"
    line2 = "视频：" + (link if link else "（未提供链接）")
    return (
        f'<section style="margin:28px 0 0;padding:16px 0 0;border-top:1px solid {C["border"]};">'
        f'<p style="margin:0 0 8px;padding:0;font-size:13px;font-weight:600;'
        f'color:{C["muted"]};">来源与说明</p>'
        f'<p style="margin:0 0 6px;padding:0;font-size:13px;line-height:1.65;'
        f'color:{C["subtle"]};">{esc(line1)}</p>'
        f'<p style="margin:0;padding:0;font-size:13px;line-height:1.65;'
        f'color:{C["subtle"]};">{esc(line2)}</p>'
        f"</section>"
    )


def subtitle_from_meta(meta: dict[str, str]) -> str:
    people = bare(
        meta.get("对谈人物", "")
        or meta.get("人物", "")
        or meta.get("讲者", "")
    )
    people = re.sub(r"<[^>]+>", "", people).strip()
    venue = public_source_line(bare(meta.get("内容来源", "") or meta.get("来源", "")))

    if people and ("×" in people or "、" in people or len(people) > 48):
        return people
    if people:
        name = re.split(r"[（(]", people)[0].strip()
        if venue:
            return f"{name} · {venue}" if name else venue
        return people
    return venue


def parse_md(md: str) -> tuple[str, list[str]]:
    lines = md.splitlines()
    out: list[str] = []
    meta: dict[str, str] = {}
    i = 0
    n = len(lines)

    while i < n and not lines[i].startswith("# "):
        i += 1
    if i >= n:
        raise ValueError("No H1 title found")
    title = lines[i][2:].strip()
    i += 1
    out.append(h1(title))

    def skip_blank() -> None:
        nonlocal i
        while i < n and lines[i].strip() == "":
            i += 1

    skip_blank()
    subtitle_placeholder_idx = len(out)
    out.append("")  # fill after meta

    while i < n:
        line = lines[i]
        if line.strip() == "---":
            i += 1
            skip_blank()
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            i += 1
            skip_blank()

            if heading == "自检报告":
                while i < n:
                    i += 1
                break

            if heading == "文章元数据":
                meta, i = parse_meta_table(lines, i)
                skip_blank()
                if i < n and lines[i].startswith(">"):
                    bio_lines = []
                    while i < n and lines[i].startswith(">"):
                        bio_lines.append(strip_bq(lines[i]))
                        i += 1
                    bio = " ".join(bio_lines)
                    bio = re.sub(r"^\*\*人物背景\*\*[：:]\s*", "", bio)
                    out.append(bio_card(bio))
                skip_blank()
                continue

            if heading in OMIT_H2:
                while i < n and not lines[i].startswith("## "):
                    i += 1
                skip_blank()
                continue

            out.append(h2(heading))

            if heading == "核心导读":
                if i < n and lines[i].startswith(">"):
                    q = []
                    while i < n and lines[i].startswith(">"):
                        q.append(strip_bq(lines[i]))
                        i += 1
                    thesis = " ".join(q)
                    thesis = re.sub(r"^\*\*全文论点\*\*[：:]\s*", "", thesis)
                    out.append(thesis_card("全文论点", thesis))
                skip_blank()
                while i < n and not lines[i].startswith("## ") and lines[i].strip() != "---":
                    if lines[i].strip() == "":
                        i += 1
                        continue
                    tbl, ni = try_parse_gfm_table(lines, i)
                    if tbl is not None:
                        out.append(tbl)
                        i = ni
                        continue
                    out.append(p(lines[i].strip()))
                    i += 1
                skip_blank()
                continue

            while i < n and not lines[i].startswith("## "):
                if lines[i].strip() == "---":
                    i += 1
                    break
                if lines[i].startswith("### "):
                    sub = lines[i][4:].strip()
                    i += 1
                    skip_blank()
                    out.append(h3(sub))

                    if sub == "核心洞察":
                        q = []
                        while i < n and lines[i].startswith(">"):
                            q.append(strip_bq(lines[i]))
                            i += 1
                        out.append(insight_card(" ".join(q)))
                        skip_blank()
                        continue

                    if sub == "对谈实录":
                        while i < n and not lines[i].startswith("## ") and not lines[i].startswith("### "):
                            if lines[i].strip() in ("", "---"):
                                if lines[i].strip() == "---":
                                    break
                                i += 1
                                continue
                            m = re.match(
                                r"^\*\*([^*]+)\*\*[：:]\s*[「\"](.+)[」\"]\s*$",
                                lines[i].strip(),
                            )
                            if m:
                                out.append(dialogue_card(m.group(1), m.group(2)))
                                i += 1
                                continue
                            tbl, ni = try_parse_gfm_table(lines, i)
                            if tbl is not None:
                                out.append(tbl)
                                i = ni
                                continue
                            out.append(p(lines[i].strip(), size="14px", color=C["muted"]))
                            i += 1
                        skip_blank()
                        continue

                    if sub == "深度解析":
                        while i < n and not lines[i].startswith("## ") and not lines[i].startswith("### "):
                            if lines[i].strip() in ("", "---"):
                                if lines[i].strip() == "---":
                                    break
                                i += 1
                                continue
                            tbl, ni = try_parse_gfm_table(lines, i)
                            if tbl is not None:
                                out.append(tbl)
                                i = ni
                                continue
                            mnum = re.match(r"^(\d+)\.\s+(.+)$", lines[i].strip())
                            if mnum:
                                out.append(p(f"{mnum.group(1)}. {mnum.group(2)}", mb="8px"))
                                i += 1
                                continue
                            out.append(p(lines[i].strip()))
                            i += 1
                        skip_blank()
                        continue

                    while i < n and not lines[i].startswith("## ") and not lines[i].startswith("### "):
                        if lines[i].strip() == "":
                            i += 1
                            continue
                        tbl, ni = try_parse_gfm_table(lines, i)
                        if tbl is not None:
                            out.append(tbl)
                            i = ni
                            continue
                        out.append(render_body_line(lines[i]))
                        i += 1
                    continue

                if lines[i].strip() == "":
                    i += 1
                    continue
                tbl, ni = try_parse_gfm_table(lines, i)
                if tbl is not None:
                    out.append(tbl)
                    i = ni
                    continue
                out.append(render_body_line(lines[i]))
                i += 1
            continue

        if lines[i].startswith("*文档生成时间"):
            i += 1
            continue
        i += 1

    sub = subtitle_from_meta(meta)
    out[subtitle_placeholder_idx] = (
        f'<p style="margin:0 0 20px;padding:0;font-size:13px;line-height:1.6;'
        f'color:{C["subtle"]};text-align:center;">{esc(sub)}</p>'
        if sub
        else ""
    )
    out.append(source_footer(meta))
    return title, [x for x in out if x]


def wrap(title: str, body_parts: list[str]) -> str:
    article = "\n".join(body_parts)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)}｜公众号完整版</title>
  <style>
    body {{ margin: 0; background: #efeee8; font-family: {FONT}; color: #1a1a1a; }}
    .howto {{ max-width: 720px; margin: 0 auto; padding: 20px 16px 8px; font-size: 14px; line-height: 1.6; color: #4a4a45; }}
    .howto strong {{ color: #a85533; }}
    .stage {{ max-width: 720px; margin: 0 auto 40px; padding: 0 12px 40px; }}
    .copy-hint {{ text-align: center; font-size: 13px; color: #6b6b66; margin: 8px 0 16px; }}
  </style>
</head>
<body>
  <div class="howto">
    <p><strong>使用方法：</strong>浏览器打开 → 选中下方米色卡片内<strong>全部正文</strong> → 复制 → 粘贴到微信公众号编辑器 → 手机预览。</p>
  </div>
  <p class="copy-hint">↓ 从这里开始复制到微信 ↓</p>
  <div class="stage">
  <section id="wechat-article" style="max-width:677px;margin:0 auto;padding:24px 18px 32px;background:{C["bg"]};color:{C["text"]};font-family:{FONT};font-size:16px;line-height:1.75;letter-spacing:0.02em;word-break:break-word;">
{article}
  </section>
  </div>
  <p class="copy-hint">↑ 复制到此结束 ↑</p>
</body>
</html>
"""


def default_out_path(src: Path) -> Path:
    stem = src.name
    for suffix in ("_整理文档.md", ".md"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    else:
        stem = src.stem
    return src.with_name(f"{stem}_公众号完整版.html")


def _self_test() -> None:
    dirty = (
        "Y Combinator · Startup School 2026；用户提供完整字幕转写 + YouTube 描述；"
        "次要核对：YC Root Access 官方逐字稿（WebFetch）。浏览器 MCP 不可用，已降级 WebFetch/WebSearch。"
    )
    assert public_source_line(dirty) == "Y Combinator · Startup School 2026", public_source_line(dirty)
    assert public_date("2026-08-07（YouTube 页面口径；YC Root Access 文稿页标注 Aug 06, 2026）") == "2026-08-07"
    sub = subtitle_from_meta(
        {
            "讲者": "**Garry Tan**（Y Combinator 总裁兼 CEO）",
            "内容来源": dirty,
        }
    )
    assert "用户提供" not in sub and "次要核对" not in sub
    assert "Garry Tan" in sub and "Startup School" in sub
    foot = source_footer(
        {
            "原标题": "Garry Tan: Own Your Intelligence",
            "发布时间": "2026-08-07（YouTube 页面口径；YC Root Access 文稿页标注 Aug 06, 2026）",
            "内容链接": "https://www.youtube.com/watch?v=eRrc1pUY5oU",
        }
    )
    assert "页面口径" not in foot and "用户提供" not in foot
    print("self-test OK")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("markdown", type=Path, nargs="?", help="Path to *_整理文档.md")
    ap.add_argument("--out", type=Path, default=None, help="Output HTML path")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        _self_test()
        return 0
    if args.markdown is None:
        ap.error("markdown path required (unless --self-test)")

    src = args.markdown
    if not src.is_file():
        print(f"ERROR: not found: {src}", file=sys.stderr)
        return 2

    title, parts = parse_md(src.read_text(encoding="utf-8"))
    html_out = wrap(title, parts)
    out = args.out or default_out_path(src)
    out.write_text(html_out, encoding="utf-8")
    print(f"Wrote {out} ({len(html_out)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

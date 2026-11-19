#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build WeChat Official Account paste-ready HTML from 整理文档 Markdown."""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

from paths import article_html_name
from sections import (
    BUILDER_OMIT_H2,
    STRUCTURAL_H2,
    TRUNCATE_H2,
    is_source_omitted_h2,
    normalize_h2,
)

C = {
    "bg": "#FAFAF7",
    "text": "#1A1A1A",
    "muted": "#4A4A45",
    "subtle": "#6B6B66",
    "accent": "#D97757",
    "accent_soft": "#FBEEE6",
    "mark": "#F0D5C4",
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

# Phone reading: body blocks need a gap larger than a tight 12px, or the
# column turns into one gray texture. Cards and labels stay tighter.
BODY_MB = "20px"
SECTION_GAP = "48px"
# A long interview needs a one-line rest under each H2. Shorter pieces do not.
LEDE_MIN_H2 = 12

OMIT_H2 = BUILDER_OMIT_H2

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

_PAREN = re.compile(r"（[^（）]*）|\([^()]*\)")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_EDITOR_NOTE = re.compile(r"\[编者注：[^\]]*\]|（编者注：[^）]*）")
_IMAGE_LINE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)\s*$")
_VIDEO_LINE = re.compile(
    r"""^<video\b[^>]*\bsrc=(["'])([^"']+)\1[^>]*>.*?(?:</video>)?\s*$""",
    re.I,
)
_ITALIC_LINE = re.compile(r"^\*(?!\*)(.+?)(?<!\*)\*\s*$")
_TIMESTAMP_PAREN = re.compile(
    r"\s*[（(]\s*\d{1,2}:\d{2}(?::\d{2})?"
    r"(?:\s*[,，、–—-]\s*\d{1,2}:\d{2}(?::\d{2})?)*"
    r"(?:\s*合并)?\s*[）)]"
)
_POINTER_LINK = re.compile(
    r"\[(?:原图地址|原图链接|原视频地址|原视频链接|查看原图|查看原视频|直达原片[^\]]*)\]\([^)]+\)"
)


def _fence_open(line: str) -> tuple[str, str] | None:
    m = re.match(r"^\s*(`{3,}|~{3,})([^\n]*)$", line)
    if not m:
        return None
    marker, rest = m.group(1), m.group(2).strip()
    if marker[0] == "`" and "`" in rest:
        return None
    lang = rest.split()[0].lower() if rest else ""
    return marker, lang


def _is_fence_close(line: str, marker: str) -> bool:
    return bool(re.match(rf"^\s*{re.escape(marker[0])}{{{len(marker)},}}\s*$", line))


def _safe_media_url(url: str) -> str:
    url = url.strip()
    checked = html.unescape(url)
    if not checked or re.search(r"[\x00-\x20\x7f]", checked):
        return ""
    try:
        parsed = urlsplit(checked)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in ("", "http", "https"):
        return ""
    return url


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def lh(size: str, ratio: float) -> str:
    """Pixel line-height strictly taller than font-size.

    Unitless values are read as raw px by the WeChat paste checker
    (1.75 → 1.75px), which is always shorter than the font.
    """
    px = int(str(size).removesuffix("px"))
    value = int(px * ratio + 0.5)
    if value <= px:
        value = px + 2
    return f"{value}px"


def shield(inner: str, color: str, align: str = "left") -> str:
    """Keep block elements free of direct text nodes.

    The paste checker treats each inline box as its own line. Bold and
    highlight then look like overlapping lines. A single wrapper span
    moves the text off the block, and an explicit text-align stops the
    browser from serializing the initial value `start`.
    """
    return f'<span style="color:{color};text-align:{align};">{inner}</span>'


def _inline_no_link(text: str) -> str:
    s = esc(text)

    def bold(m: re.Match) -> str:
        return (
            f'<strong style="font-weight:700;color:{C["text"]};text-align:left;">'
            f"{m.group(1)}</strong>"
        )

    def highlight(m: re.Match) -> str:
        inner = re.sub(r"\*\*(.+?)\*\*", bold, m.group(1))
        return (
            f'<span style="background:{C["mark"]};color:{C["text"]};'
            f'text-align:left;padding:0 4px;border-radius:3px;">'
            f"{inner}</span>"
        )

    # ==荧光笔== first so ==**词**== still bolds inside the mark.
    s = re.sub(r"==(.+?)==", highlight, s)
    s = re.sub(r"\*\*(.+?)\*\*", bold, s)

    def code(m: re.Match) -> str:
        return (
            f'<code style="padding:0 5px;background:{C["code_bg"]};'
            f'border-radius:3px;font-size:13px;line-height:{lh("13px", 1.6)};'
            f'color:#2A2A2A;text-align:left;">'
            f"{m.group(1)}</code>"
        )

    s = re.sub(r"`([^`]+)`", code, s)
    return re.sub(r"(?<!\*)\*(?=\S)([^*\n]+?)(?<=\S)\*(?!\*)", r"\1", s)


def inline_md_raw(text: str) -> str:
    # Inline images inside a sentence cannot use <img> without triggering the
    # WeChat paste line-overlap detector; render them as readable bracketed alt
    # text and never let them fall through as `!<a href=...>`.
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f"（图：{m.group(1).strip()}）" if m.group(1).strip() else "",
        text,
    )
    parts: list[str] = []
    pos = 0
    for m in re.finditer(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", text):
        parts.append(_inline_no_link(text[pos : m.start()]))
        label = _inline_no_link(m.group(1))
        url = esc(m.group(2))
        parts.append(
            f'<a href="{url}" style="color:{C["accent_strong"]};'
            f'text-align:left;text-decoration:underline;">{label}</a>'
        )
        pos = m.end()
    parts.append(_inline_no_link(text[pos:]))
    return "".join(parts)


def p(
    text: str,
    size: str = "15px",
    color: str | None = None,
    mb: str = "12px",
    *,
    strip_timestamps: bool = False,
) -> str:
    color = color or C["text"]
    text = strip_editor_notes(text)
    if strip_timestamps:
        text = _TIMESTAMP_PAREN.sub("", text).strip()
    if text.startswith(">"):
        text = strip_bq(text)
    if not text:
        return ""
    return (
        f'<p style="margin:0 0 {mb};padding:0;font-size:{size};'
        f'line-height:{lh(size, 1.75)};color:{color};text-align:left;">'
        f'{shield(inline_md_raw(text), color)}</p>'
    )


def h1(text: str) -> str:
    color = C["text"]
    return (
        f'<h1 style="margin:0 0 12px;padding:0;font-size:22px;font-weight:700;'
        f'line-height:{lh("22px", 1.45)};color:{color};text-align:center;">'
        f'{shield(esc(text), color, "center")}</h1>'
    )


def h2(text: str) -> str:
    color = C["text"]
    return (
        f'<h2 style="margin:28px 0 14px;padding:10px 0 8px;font-size:18px;'
        f'font-weight:700;line-height:{lh("18px", 1.45)};color:{color};'
        f'text-align:left;border-bottom:2px solid {C["accent_border"]};">'
        f'{shield(esc(text), color)}</h2>'
    )


def section_kicker(n: int) -> str:
    """Small「第 N 节」line above a reader-facing H2.

    Separate from the H2 so heading fidelity is untouched; spelled out so the
    WeChat 听全文 voice reads「第一节」rather than「零一」.
    """
    color = C["accent_strong"]
    return (
        f'<p style="margin:{SECTION_GAP} 0 0;padding:0;font-size:13px;font-weight:700;'
        f'line-height:{lh("13px", 1.6)};color:{color};letter-spacing:0.08em;text-align:left;">'
        f'{shield(esc("第 %d 节" % n), color)}</p>'
    )


def number_sections(parts: list[str]) -> list[str]:
    """Prefix every source H2 (not 核心导读) with a section kicker."""
    out, n = [], 0
    for part in parts:
        m = re.match(r"<h2\b[^>]*>(.*?)</h2>", part, flags=re.S)
        if m and normalize_h2(m.group(1)) not in STRUCTURAL_H2:
            n += 1
            out.append(section_kicker(n))
            part = part.replace("margin:28px 0 14px", "margin:6px 0 14px", 1)
        out.append(part)
    return out


def reader_h2_titles(md: str) -> list[str]:
    titles: list[str] = []
    fence: str | None = None
    for line in md.splitlines():
        if fence is not None:
            if _is_fence_close(line, fence):
                fence = None
            continue
        opened = _fence_open(line)
        if opened is not None:
            fence = opened[0]
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            if not is_source_omitted_h2(title):
                titles.append(title)
    return titles


def insight_ledes(md: str) -> dict[str, str]:
    """First sentence of each reader H2's 核心洞察, keyed by normalize_h2."""
    lines = md.splitlines()
    found: dict[str, str] = {}
    heading = ""
    fence: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if fence is not None:
            if _is_fence_close(line, fence):
                fence = None
            i += 1
            continue
        opened = _fence_open(line)
        if opened is not None:
            fence = opened[0]
            i += 1
            continue
        if line.startswith("## "):
            heading = line[3:].strip()
            i += 1
            continue
        if heading and not is_source_omitted_h2(heading) and line.strip() == "### 核心洞察":
            i += 1
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            quote: list[str] = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(strip_bq(lines[i]))
                i += 1
            text = "".join(quote)
            text = re.split(r"\*\*事实边界\*\*", text)[0]
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text).strip()
            end = re.search(r"[。！？]", text)
            sentence = text[: end.end()].strip() if end else text
            if sentence:
                found[normalize_h2(heading)] = sentence
            continue
        i += 1
    return found


def inject_section_ledes(parts: list[str], ledes: dict[str, str]) -> list[str]:
    """Put the source insight's first sentence under each reader H2.

    Skip when the draft already has a 本节 line, or the next paragraph
    already opens with that same sentence.
    """
    out: list[str] = []
    for i, part in enumerate(parts):
        out.append(part)
        m = re.match(r"<h2\b[^>]*>(.*?)</h2>", part, flags=re.S)
        if not m:
            continue
        key = normalize_h2(html.unescape(m.group(1)))
        sentence = ledes.get(key)
        if not sentence:
            continue
        nxt = parts[i + 1] if i + 1 < len(parts) else ""
        if "data-wechat-lede=" in nxt:
            continue
        nxt_plain = re.sub(r"<[^>]+>", "", html.unescape(nxt))
        if sentence in nxt_plain:
            continue
        out.append(section_lede(sentence))
    return out


def source_fingerprint(src: Path) -> str:
    """HTML comment tying the article to the exact 整理文档 it was written from."""
    digest = hashlib.sha256(src.read_bytes()).hexdigest()[:16]
    return f"<!-- md2wechat-source: {src.name} sha256:{digest} -->"


def h3(text: str) -> str:
    color = C["accent_strong"]
    return (
        f'<h3 style="margin:16px 0 10px;padding:0;font-size:15px;font-weight:700;'
        f'line-height:{lh("15px", 1.6)};color:{color};text-align:left;">'
        f'{shield(esc(text), color)}</h3>'
    )


def insight_card(quote: str) -> str:
    color = C["text"]
    return (
        f'<section style="margin:0 0 14px;padding:12px 14px;background:{C["surface"]};'
        f'border:1px solid {C["accent_border"]};border-radius:8px;text-align:left;">'
        f'<p style="margin:0;padding:0;font-size:15px;line-height:{lh("15px", 1.65)};'
        f'color:{color};text-align:left;">{shield(inline_md_raw(quote), color)}</p></section>'
    )


def thesis_card(label: str, body: str) -> str:
    label_color = C["accent_strong"]
    body_color = C["text"]
    return (
        f'<section style="margin:0 0 18px;padding:16px 16px 14px;'
        f'background:{C["accent_soft"]};border-left:4px solid {C["accent"]};'
        f'border-radius:0 8px 8px 0;text-align:left;">'
        f'<p style="margin:0 0 8px;padding:0;font-size:12px;font-weight:600;'
        f'line-height:{lh("12px", 1.6)};color:{label_color};letter-spacing:0.08em;'
        f'text-align:left;">{shield(esc(label), label_color)}</p>'
        f'<p style="margin:0;padding:0;font-size:15px;line-height:{lh("15px", 1.7)};'
        f'color:{body_color};text-align:left;">'
        f'{shield(inline_md_raw(body), body_color)}</p></section>'
    )


def bio_card(text: str) -> str:
    label_color = C["accent_strong"]
    body_color = C["muted"]
    return (
        f'<section style="margin:0 0 20px;padding:14px 16px;background:{C["surface"]};'
        f'border:1px solid {C["border"]};border-radius:8px;text-align:left;">'
        f'<p style="margin:0 0 6px;padding:0;font-size:12px;font-weight:600;'
        f'line-height:{lh("12px", 1.6)};color:{label_color};text-align:left;">'
        f'{shield("人物背景", label_color)}</p>'
        f'<p style="margin:0;padding:0;font-size:14px;line-height:{lh("14px", 1.7)};'
        f'color:{body_color};text-align:left;">'
        f'{shield(inline_md_raw(text), body_color)}</p></section>'
    )


def dialogue_card(speaker: str, quote: str) -> str:
    """Keep the speaker off the quote line.

    An inline-block badge with vertical padding shares the quote's line box.
    The paste checker measures that as overlapping lines once the quote wraps.
    The name sits in its own single-line paragraph; the quote paragraph has
    only text inside the wrapper span. Padding is horizontal only.
    """
    color = C["muted"]
    label_color = C["accent_strong"]
    badge = (
        f'<span style="padding:0 8px;background:{C["accent_soft"]};'
        f'color:{label_color};font-size:12px;line-height:{lh("12px", 1.6)};'
        f'border-radius:4px;font-weight:600;text-align:left;">'
        f"{esc(speaker)}</span>"
    )
    return (
        f'<section style="margin:0 0 8px;padding:12px 14px;background:{C["surface"]};'
        f'border-radius:8px;border:1px solid {C["border"]};text-align:left;">'
        f'<p style="margin:0 0 6px;padding:0;font-size:12px;'
        f'line-height:{lh("12px", 1.6)};color:{label_color};text-align:left;">'
        f"{shield(badge, label_color)}</p>"
        f'<p style="margin:0;padding:0;font-size:14px;line-height:{lh("14px", 1.7)};'
        f'color:{color};text-align:left;">'
        f"{shield(inline_md_raw(quote), color)}</p></section>"
    )


def strip_bq(line: str) -> str:
    return re.sub(r"^>\s?", "", line).strip()


_SPEAKER_QUOTE = re.compile(
    r"^\*\*([^*]+)\*\*(?:\s*([（(][^）)\n]*[）)]))?\s*[：:]\s*[「\"](.+)[」\"]\s*$"
)


_SECTION_LEDE = re.compile(r"^\*\*本节\*\*[：:]\s*(.+)$")


def _clean_wechat_caption(raw: str, *, mode: str = "full") -> str:
    """Strip external URLs and source-pointer links from figure captions."""
    s = strip_editor_notes(raw)
    s = _POINTER_LINK.sub("", s)
    s = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", r"\1", s)
    s = re.sub(r"https?://\S+", "", s)
    if mode == "editorial":
        s = re.sub(r"[（(]\s*原片定位[：:][^）)]*[）)]", "", s)
        s = re.sub(r"[·；;，,]\s*原片定位[：:][^）)\n]*", "", s)
        s = _TIMESTAMP_PAREN.sub("", s)
    s = re.sub(r"([（(])\s*[·；;，,。]+\s*", r"\1", s)
    s = re.sub(r"\s*[·；;，,]+\s*([）)])", r"\1", s)
    s = re.sub(r"[（(]\s*[）)]", "", s)
    s = re.sub(r"\s*[·]\s*$", "", s)
    s = re.sub(r"[ \t]{2,}", " ", s).strip()
    if s in ("。", "·", "；", ";"):
        return ""
    return s


def image_figure(alt: str, url: str, caption: str = "", *, mode: str = "full") -> str:
    safe = _safe_media_url(url)
    if not safe:
        return ""
    esc_url = html.escape(safe, quote=True)
    esc_alt = html.escape(strip_editor_notes(alt), quote=True)
    clean_cap = _clean_wechat_caption(caption, mode=mode) if caption else ""
    cap_html = ""
    if clean_cap:
        cap_color = C["subtle"]
        cap_html = (
            f'<p style="margin:8px 0 0;padding:0;font-size:13px;'
            f'line-height:{lh("13px", 1.65)};color:{cap_color};text-align:center;">'
            f'{shield(_inline_no_link(clean_cap), cap_color, "center")}</p>'
        )
    return (
        f'<section data-wechat-figure="1" style="margin:0 0 {BODY_MB};padding:0;text-align:left;">'
        f'<img src="{esc_url}" alt="{esc_alt}" referrerpolicy="no-referrer" '
        f'style="max-width:100%;height:auto;border-radius:6px;'
        f'border:1px solid {C["border"]};display:block;margin:0 auto;" />'
        f"{cap_html}</section>"
    )


def video_fallback_card(caption: str = "") -> str:
    clean_cap = _clean_wechat_caption(caption, mode="full") if caption else ""
    text = f"【原片动态画面：{clean_cap}】" if clean_cap else "【原片动态画面：详见原文视频演示】"
    color = C["subtle"]
    return (
        f'<section data-wechat-video="1" style="margin:0 0 16px;padding:10px 14px;'
        f'background:{C["code_bg"]};border:1px solid {C["border"]};border-radius:8px;text-align:left;">'
        f'<p style="margin:0;padding:0;font-size:13px;line-height:{lh("13px", 1.65)};'
        f'color:{color};text-align:left;">{shield(_inline_no_link(text), color)}</p></section>'
    )


def _parse_mermaid_steps(code_lines: list[str]) -> list[str]:
    node_re = re.compile(r'([A-Za-z0-9_]+)\s*(?:\[\s*"?([^\]"]+)"?\s*\]|\(\s*"?([^)"]+)"?\s*\)|\{\s*"?([^}"]+)"?\s*\})')
    labels: dict[str, str] = {}
    for raw in code_lines:
        for m in node_re.finditer(raw):
            nid = m.group(1)
            lbl = (m.group(2) or m.group(3) or m.group(4) or "").replace("<br/>", " ").replace("<br>", " ").strip()
            if lbl:
                labels[nid] = lbl
    edge_re = re.compile(
        r"([A-Za-z0-9_]+)(?:\s*[\[\(\{][^\]\)\}]*[\]\)\}])?\s*"
        r"(?:--\s*([^-.\n>]+?)\s*-->|-->\s*(?:\|([^|]+)\|)?|-\.\s*([^.\n>]*?)\s*\.->|-\.->)\s*"
        r"([A-Za-z0-9_]+)"
    )
    steps: list[str] = []
    for raw in code_lines:
        s = raw.strip()
        if not s or s.startswith(("%%", "flowchart", "graph", "subgraph", "end", "style", "classDef", "class ")):
            continue
        for m in edge_re.finditer(s):
            src, l1, l2, dotted_lbl, dst = m.groups()
            a = labels.get(src, src)
            b = labels.get(dst, dst)
            is_dotted = "-." in m.group(0)
            note = (l1 or l2 or dotted_lbl or "").strip().strip('"')
            arrow = "⇢" if is_dotted else "→"
            step = f"{a} {arrow}（{note}）{b}" if note else f"{a} {arrow} {b}"
            if step not in steps:
                steps.append(step)
    return steps


def mermaid_fallback_card(code_lines: list[str], caption: str = "") -> str:
    steps = _parse_mermaid_steps(code_lines)
    clean_cap = _clean_wechat_caption(caption, mode="full") if caption else ""
    label_color = C["accent_strong"]
    body_color = C["muted"]
    inner = [
        f'<p style="margin:0 0 6px;padding:0;font-size:12px;font-weight:600;'
        f'line-height:{lh("12px", 1.6)};color:{label_color};text-align:left;">'
        f'{shield("流程示意", label_color)}</p>'
    ]
    if steps:
        for idx, chunk in enumerate(steps[:8]):
            mb = "0" if idx == min(len(steps), 8) - 1 and not clean_cap else "4px"
            inner.append(
                f'<p style="margin:0 0 {mb};padding:0;font-size:14px;'
                f'line-height:{lh("14px", 1.7)};color:{body_color};text-align:left;">'
                f"{shield(esc(chunk), body_color)}</p>"
            )
    else:
        mb = "0" if not clean_cap else "4px"
        inner.append(
            f'<p style="margin:0 0 {mb};padding:0;font-size:14px;'
            f'line-height:{lh("14px", 1.7)};color:{body_color};text-align:left;">'
            f'{shield("详见原文结构示意图", body_color)}</p>'
        )
    if clean_cap:
        inner.append(
            f'<p style="margin:4px 0 0;padding:0;font-size:12px;'
            f'line-height:{lh("12px", 1.6)};color:{C["subtle"]};text-align:left;">'
            f'{shield(_inline_no_link(clean_cap), C["subtle"])}</p>'
        )
    return (
        f'<section data-wechat-diagram="1" style="margin:0 0 16px;padding:12px 14px;'
        f'background:{C["code_bg"]};border:1px solid {C["border"]};border-radius:8px;text-align:left;">'
        f'{"".join(inner)}</section>'
    )


def code_block_card(code_lines: list[str]) -> str:
    trimmed = list(code_lines)
    while trimmed and trimmed[0].strip() == "":
        trimmed.pop(0)
    while trimmed and trimmed[-1].strip() == "":
        trimmed.pop()
    if not trimmed:
        return ""
    rows: list[str] = []
    for idx, raw in enumerate(trimmed):
        mb = "0" if idx == len(trimmed) - 1 else "4px"
        content = esc(raw) if raw else "&nbsp;"
        rows.append(
            f'<p style="margin:0 0 {mb};padding:0;font-family:Consolas,Menlo,monospace;'
            f'font-size:13px;line-height:{lh("13px", 1.6)};color:#2A2A2A;'
            f'text-align:left;white-space:pre-wrap;word-break:break-all;">'
            f'{shield(content, "#2A2A2A")}</p>'
        )
    return (
        f'<section data-wechat-code="1" style="margin:0 0 16px;padding:12px 14px;'
        f'background:{C["code_bg"]};border:1px solid {C["border"]};border-radius:8px;text-align:left;">'
        f'{"".join(rows)}</section>'
    )


def section_lede(text: str) -> str:
    """One gray sentence under an H2. Not a heading and not a highlight."""
    color = C["muted"]
    size = "14px"
    return (
        f'<p data-wechat-lede="1" style="margin:0 0 18px;padding:0;font-size:{size};'
        f'line-height:{lh(size, 1.75)};color:{color};text-align:left;">'
        f"{shield(inline_md_raw(text), color)}</p>"
    )


def _format_speaker(name: str, note: str | None, mode: str) -> str:
    base = _TIMESTAMP_PAREN.sub("", name).strip() if mode == "editorial" else name.strip()
    extra = (note or "").strip()
    if mode == "editorial" or not extra:
        return base
    return f"{base}{extra}"


def render_body_line(
    line: str,
    *,
    size: str = "15px",
    color: str | None = None,
    mb: str = BODY_MB,
    mode: str = "full",
) -> str:
    if line.strip().startswith(">"):
        raw = strip_bq(line.strip())
        lede = _SECTION_LEDE.match(raw)
        if lede:
            return section_lede(lede.group(1).strip())
        if mode == "editorial":
            raw = _TIMESTAMP_PAREN.sub("", raw).strip()
        return insight_card(raw)
    raw = line.strip()
    m = _SPEAKER_QUOTE.match(raw)
    if m:
        speaker = _format_speaker(m.group(1), m.group(2), mode)
        quote = _TIMESTAMP_PAREN.sub("", m.group(3)).strip() if mode == "editorial" else m.group(3)
        return dialogue_card(speaker, quote)
    return p(raw, size=size, color=color, mb=mb, strip_timestamps=(mode == "editorial"))


def bare(s: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", s).strip()


_SEP_ROW = re.compile(r"^\|[\s\-:|]+\|$")


def is_pipe_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def is_sep_row(line: str) -> bool:
    return bool(_SEP_ROW.match(line.strip()))


_ESC_PIPE = "\x00PIPE\x00"


def split_cells(row: str) -> list[str]:
    """Split a GFM table row on `|`, honouring the `\\|` escape.

    Titles like `… Changes Work \\| Daron Acemoglu` must survive as one cell;
    a naive split truncated them to `… Work \\` in the footer.
    """
    s = row.strip().replace("\\|", _ESC_PIPE).strip("|")
    return [c.replace(_ESC_PIPE, "|").strip() for c in s.split("|")]


def _td(text: str, *, header: bool = False, first_col: bool = False) -> str:
    """WeChat paste keeps td+inline styles more reliably than th / CSS classes."""
    bg = C["accent_soft"] if header else C["surface"]
    color = C["accent_strong"] if header else C["text"]
    weight = "700" if header or first_col else "400"
    size = "13px" if header else "14px"
    border = C["accent_border"] if header else C["border"]
    return (
        f'<td style="padding:8px 10px;background:{bg};color:{color};'
        f'font-size:{size};font-weight:{weight};line-height:{lh(size, 1.6)};'
        f'text-align:left;vertical-align:top;border:1px solid {border};'
        f'word-break:break-word;">{shield(inline_md_raw(text), color)}</td>'
    )


def render_table_cards(header: list[str], rows: list[list[str]]) -> str:
    """Wide tables (≥5 cols) → stacked cards; native tables overflow on phone."""
    parts: list[str] = []
    for row in rows:
        inner: list[str] = []
        for j, cell in enumerate(row):
            label = header[j] if j < len(header) else ""
            if j == 0:
                title_color = C["text"]
                inner.append(
                    f'<p style="margin:0 0 6px;padding:0;font-size:15px;'
                    f'font-weight:700;line-height:{lh("15px", 1.6)};'
                    f'color:{title_color};text-align:left;">'
                    f'{shield(inline_md_raw(cell), title_color)}</p>'
                )
            else:
                muted = C["muted"]
                label_html = (
                    f'<span style="color:{C["accent_strong"]};font-weight:600;'
                    f'text-align:left;">{inline_md_raw(label)}</span>'
                    f"　{inline_md_raw(cell)}"
                )
                inner.append(
                    f'<p style="margin:0 0 4px;padding:0;font-size:13px;'
                    f'line-height:{lh("13px", 1.65)};color:{muted};text-align:left;">'
                    f"{shield(label_html, muted)}</p>"
                )
        parts.append(
            f'<section style="margin:0 0 10px;padding:12px 14px;'
            f'background:{C["surface"]};border:1px solid {C["border"]};'
            f'border-radius:8px;text-align:left;">{"".join(inner)}</section>'
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
        f'border-radius:8px;text-align:left;">'
        f'<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;'
        f'width:100%;margin:0;font-size:14px;line-height:{lh("14px", 1.6)};'
        f'font-family:{FONT};text-align:left;">'
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
        cells = split_cells(row)
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
    """Committed publish dates only, joined with 、.

    A segment counts when it starts with YYYY-MM-DD after parenthetical
    notes are removed. Event days, crawl days, and a conflicting upload
    day written inside parentheses stay in the 整理文档.
    """
    if not date:
        return ""
    s = date
    while True:
        nxt = _PAREN.sub("", s)
        if nxt == s:
            break
        s = nxt
    found: list[str] = []
    for part in re.split(r"[；;、。]", s):
        m = _ISO_DATE.match(part.strip())
        if m and m.group(0) not in found:
            found.append(m.group(0))
    return "、".join(found)


def strip_editor_notes(text: str) -> str:
    s = _EDITOR_NOTE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def source_footer(meta: dict[str, str]) -> str:
    """来源与说明 keeps 原文 and, when a committed date exists, one 发布 line."""
    title = bare(meta.get("原标题", "") or meta.get("标题", ""))
    line1 = "原文：" + (title if title else "（见正文来源）")
    date = public_date(bare(meta.get("发布时间", "")))
    date_html = ""
    if date:
        date_html = (
            f'<p style="margin:6px 0 0;padding:0;font-size:13px;line-height:{lh("13px", 1.65)};'
            f'color:{C["subtle"]};text-align:left;">'
            f'{shield(esc("发布：" + date), C["subtle"])}</p>'
        )
    return (
        f'<section style="margin:28px 0 0;padding:16px 0 0;border-top:1px solid {C["border"]};'
        f'text-align:left;">'
        f'<p style="margin:0 0 8px;padding:0;font-size:13px;font-weight:600;'
        f'line-height:{lh("13px", 1.6)};color:{C["muted"]};text-align:left;">'
        f'{shield("来源与说明", C["muted"])}</p>'
        f'<p style="margin:0;padding:0;font-size:13px;line-height:{lh("13px", 1.65)};'
        f'color:{C["subtle"]};text-align:left;">'
        f'{shield(esc(line1), C["subtle"])}</p>'
        f"{date_html}"
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
        # Byline is names only; roles already live in the 人物背景 card.
        names = [re.split(r"[（(]", x)[0].strip() for x in re.split(r"\s*×\s*", people)]
        return " × ".join(n for n in names if n) if "×" in people else people
    if people:
        name = re.split(r"[（(]", people)[0].strip()
        if venue:
            return f"{name} · {venue}" if name else venue
        return people
    return venue


def _peek_adjacent_caption(lines: list[str], next_idx: int) -> tuple[str, int]:
    """Consume a standalone `*caption*` block immediately following media/diagram."""
    n = len(lines)
    j = next_idx
    while j < n and lines[j].strip() == "":
        j += 1
    if j < n:
        m = _ITALIC_LINE.match(lines[j].strip())
        if m:
            return m.group(1).strip(), j + 1
    return "", next_idx


def try_consume_special_block(
    lines: list[str], start: int, mode: str
) -> tuple[str | None, int]:
    """Consume fenced code / mermaid, standalone image, video, or italic trace line."""
    n = len(lines)
    if start >= n:
        return None, start
    raw_line = lines[start]
    stripped = raw_line.strip()

    opened = _fence_open(raw_line)
    if opened is not None:
        marker, lang = opened
        i = start + 1
        code_lines: list[str] = []
        while i < n and not _is_fence_close(lines[i], marker):
            code_lines.append(lines[i])
            i += 1
        if i < n:
            i += 1
        if lang == "mermaid":
            cap, after_cap = _peek_adjacent_caption(lines, i)
            if cap and re.search(r"原片|示意图|流程图|口播整理|画面", cap):
                i = after_cap
            else:
                cap = ""
            if mode == "editorial":
                return "", i
            return mermaid_fallback_card(code_lines, cap), i
        return code_block_card(code_lines), i

    img_m = _IMAGE_LINE.match(stripped)
    if img_m:
        cap, next_i = _peek_adjacent_caption(lines, start + 1)
        return image_figure(img_m.group(1), img_m.group(2), cap, mode=mode), next_i

    vid_m = _VIDEO_LINE.match(stripped)
    if vid_m:
        cap, next_i = _peek_adjacent_caption(lines, start + 1)
        if mode == "editorial":
            return "", next_i
        return video_fallback_card(cap), next_i

    it_m = _ITALIC_LINE.match(stripped)
    if it_m and not stripped.startswith("*文档生成时间"):
        inner = it_m.group(1).strip()
        if mode == "editorial" and re.search(
            r"据原片.*(?:画面|口播)整理|原图地址|原图链接|原视频地址", inner
        ):
            return "", start + 1
        cleaned = _clean_wechat_caption(inner, mode=mode)
        if not cleaned:
            return "", start + 1
        return p(cleaned, size="13px", color=C["subtle"], mb="14px", strip_timestamps=(mode == "editorial")), start + 1

    return None, start


def parse_md(md: str, mode: str = "auto") -> tuple[str, list[str], str]:
    if mode == "auto":
        mode = "full" if re.search(r"^### 核心洞察\s*$", md, flags=re.M) else "editorial"
    if mode not in {"full", "editorial"}:
        raise ValueError(f"Unknown mode: {mode}")
    body_size = "16px" if mode == "editorial" else "15px"
    lines = md.splitlines()
    out: list[str] = []
    meta: dict[str, str] = {}
    i = 0
    n = len(lines)

    fence: str | None = None
    while i < n:
        if fence is not None:
            if _is_fence_close(lines[i], fence):
                fence = None
            i += 1
            continue
        opened = _fence_open(lines[i])
        if opened is not None:
            fence = opened[0]
            i += 1
            continue
        if lines[i].startswith("# "):
            break
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
            key = normalize_h2(heading)
            i += 1
            skip_blank()

            if key == TRUNCATE_H2:
                while i < n:
                    i += 1
                break

            if key == "文章元数据":
                meta, i = parse_meta_table(lines, i)
                bio_paragraphs: list[str] = []
                cur_bio: list[str] = []
                meta_fence: str | None = None
                while i < n and not (meta_fence is None and lines[i].startswith("## ")):
                    cur_line = lines[i]
                    if meta_fence is not None:
                        if _is_fence_close(cur_line, meta_fence):
                            meta_fence = None
                        i += 1
                        continue
                    op = _fence_open(cur_line)
                    if op is not None:
                        meta_fence = op[0]
                        i += 1
                        continue
                    if cur_line.strip() == "---":
                        i += 1
                        break
                    if cur_line.startswith(">"):
                        stripped_bq = strip_bq(cur_line)
                        if stripped_bq:
                            cur_bio.append(stripped_bq)
                        elif cur_bio:
                            bio_paragraphs.append(" ".join(cur_bio))
                            cur_bio = []
                    elif cur_bio:
                        bio_paragraphs.append(" ".join(cur_bio))
                        cur_bio = []
                    i += 1
                if cur_bio:
                    bio_paragraphs.append(" ".join(cur_bio))
                if bio_paragraphs:
                    bio = " ".join(bio_paragraphs)
                    bio = re.sub(
                        r"^\*\*(?:人物背景|讲者背景)(?:（[^）]*）)?\*\*[：:]\s*",
                        "",
                        bio,
                    )
                    if bio:
                        out.append(bio_card(bio))
                skip_blank()
                continue

            if key in OMIT_H2:
                omit_fence: str | None = None
                while i < n:
                    if omit_fence is not None:
                        if _is_fence_close(lines[i], omit_fence):
                            omit_fence = None
                        i += 1
                        continue
                    op = _fence_open(lines[i])
                    if op is not None:
                        omit_fence = op[0]
                        i += 1
                        continue
                    if lines[i].startswith("## "):
                        break
                    i += 1
                skip_blank()
                continue

            out.append(h2(heading))

            if key == "核心导读":
                if i < n and lines[i].startswith(">"):
                    q = []
                    while i < n and lines[i].startswith(">"):
                        q.append(strip_bq(lines[i]))
                        i += 1
                    raw_thesis = " ".join(q)
                    card_label = (
                        "核心冲突"
                        if re.match(r"^\*\*核心冲突\*\*[：:]", raw_thesis)
                        else "全文论点"
                    )
                    thesis = re.sub(r"^\*\*(?:全文论点|核心冲突)\*\*[：:]\s*", "", raw_thesis)
                    out.append(thesis_card(card_label, thesis))
                skip_blank()
                while i < n and not lines[i].startswith("## ") and lines[i].strip() != "---":
                    if lines[i].strip() == "":
                        i += 1
                        continue
                    special, ni = try_consume_special_block(lines, i, mode)
                    if special is not None:
                        if special:
                            out.append(special)
                        i = ni
                        continue
                    tbl, ni = try_parse_gfm_table(lines, i)
                    if tbl is not None:
                        out.append(tbl)
                        i = ni
                        continue
                    out.append(p(lines[i].strip(), size=body_size, mb=BODY_MB, strip_timestamps=(mode == "editorial")))
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
                            special, ni = try_consume_special_block(lines, i, mode)
                            if special is not None:
                                if special:
                                    out.append(special)
                                i = ni
                                continue
                            m = _SPEAKER_QUOTE.match(lines[i].strip())
                            if m:
                                speaker = _format_speaker(m.group(1), m.group(2), mode)
                                quote = (
                                    _TIMESTAMP_PAREN.sub("", m.group(3)).strip()
                                    if mode == "editorial"
                                    else m.group(3)
                                )
                                out.append(dialogue_card(speaker, quote))
                                i += 1
                                continue
                            tbl, ni = try_parse_gfm_table(lines, i)
                            if tbl is not None:
                                out.append(tbl)
                                i = ni
                                continue
                            out.append(p(lines[i].strip(), size="14px", color=C["muted"], strip_timestamps=(mode == "editorial")))
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
                            special, ni = try_consume_special_block(lines, i, mode)
                            if special is not None:
                                if special:
                                    out.append(special)
                                i = ni
                                continue
                            tbl, ni = try_parse_gfm_table(lines, i)
                            if tbl is not None:
                                out.append(tbl)
                                i = ni
                                continue
                            mnum = re.match(r"^(\d+)\.\s+(.+)$", lines[i].strip())
                            if mnum:
                                out.append(p(f"{mnum.group(1)}. {mnum.group(2)}", size=body_size, mb="8px", strip_timestamps=(mode == "editorial")))
                                i += 1
                                continue
                            out.append(p(lines[i].strip(), size=body_size, mb=BODY_MB, strip_timestamps=(mode == "editorial")))
                            i += 1
                        skip_blank()
                        continue

                    while i < n and not lines[i].startswith("## ") and not lines[i].startswith("### "):
                        if lines[i].strip() == "":
                            i += 1
                            continue
                        if lines[i].strip() == "---":
                            break
                        special, ni = try_consume_special_block(lines, i, mode)
                        if special is not None:
                            if special:
                                out.append(special)
                            i = ni
                            continue
                        tbl, ni = try_parse_gfm_table(lines, i)
                        if tbl is not None:
                            out.append(tbl)
                            i = ni
                            continue
                        out.append(render_body_line(lines[i], size=body_size, mode=mode))
                        i += 1
                    continue

                if lines[i].strip() == "":
                    i += 1
                    continue
                special, ni = try_consume_special_block(lines, i, mode)
                if special is not None:
                    if special:
                        out.append(special)
                    i = ni
                    continue
                tbl, ni = try_parse_gfm_table(lines, i)
                if tbl is not None:
                    out.append(tbl)
                    i = ni
                    continue
                out.append(render_body_line(lines[i], size=body_size, mode=mode))
                i += 1
            continue

        if lines[i].startswith("*文档生成时间"):
            i += 1
            continue
        i += 1

    sub = subtitle_from_meta(meta)
    out[subtitle_placeholder_idx] = (
        f'<p style="margin:0 0 20px;padding:0;font-size:13px;line-height:{lh("13px", 1.6)};'
        f'color:{C["subtle"]};text-align:center;">'
        f'{shield(esc(sub), C["subtle"], "center")}</p>'
        if sub
        else ""
    )
    out.append(source_footer(meta))
    return title, number_sections([x for x in out if x]), mode


def wrap(title: str, body_parts: list[str], mode: str = "full", fingerprint: str = "") -> str:
    article = "\n".join(body_parts)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)}｜公众号文章</title>
  {fingerprint}
  <style>
    body {{ margin: 0; background: #efeee8; font-family: {FONT}; color: #1a1a1a; }}
    .howto {{ max-width: 720px; margin: 0 auto; padding: 20px 16px 8px; font-size: 14px; line-height: 1.6; color: #4a4a45; }}
    .howto strong {{ color: #a85533; }}
    .stage {{ max-width: 720px; margin: 0 auto 40px; padding: 0 12px 40px; }}
    body.phone .stage {{ max-width: 399px; }}
    .copy-hint {{ text-align: center; font-size: 13px; color: #6b6b66; margin: 8px 0 16px; }}
    .width-toggle {{ margin-left: 8px; padding: 2px 10px; font: inherit; font-size: 13px; border: 1px solid #cdcdc4; border-radius: 6px; background: #fff; color: #4a4a45; cursor: pointer; }}
  </style>
</head>
<body>
  <div class="howto">
    <p><strong>使用方法：</strong>浏览器打开 → 选中下方米色卡片内<strong>全部正文</strong> → 复制 → 粘贴到微信公众号编辑器 → 手机预览。<button class="width-toggle" type="button" onclick="this.textContent=document.body.classList.toggle('phone')?'切回电脑宽度':'按手机宽度预览'">按手机宽度预览</button></p>
  </div>
  <p class="copy-hint">↓ 从这里开始复制到微信 ↓</p>
  <div class="stage">
  <section id="wechat-article" style="max-width:677px;margin:0 auto;padding:24px 18px 32px;background:{C["bg"]};color:{C["text"]};font-family:{FONT};font-size:16px;line-height:28px;letter-spacing:0.02em;word-break:break-word;text-align:left;">
{article}
  </section>
  </div>
  <p class="copy-hint">↑ 复制到此结束 ↑</p>
</body>
</html>
"""


def default_out_path(src: Path) -> Path:
    return src.with_name(article_html_name(src))


def _self_test() -> None:
    dirty = (
        "Y Combinator · Startup School 2026；用户提供完整字幕转写 + YouTube 描述；"
        "次要核对：YC Root Access 官方逐字稿（WebFetch）。浏览器 MCP 不可用，已降级 WebFetch/WebSearch。"
    )
    assert public_source_line(dirty) == "Y Combinator · Startup School 2026", public_source_line(dirty)
    assert public_date("2026-08-07（YouTube 页面口径；YC Root Access 文稿页标注 Aug 06, 2026）") == "2026-08-07"
    assert public_date(
        "2026-09-20（CBS）、2026-09-23（The Ezra Klein Show）、2026-09-29（CNBC）。文件名取最晚一场"
    ) == "2026-09-20、2026-09-23、2026-09-29"
    assert public_date(
        "2026-07-08（用户页面口径）；YouTube 页面元数据为 2026-07-07 10:28 PDT；"
        "Axios 精编首发 2026-06-25；录制 2026-06-23"
    ) == "2026-07-08"
    assert public_date(
        "2026-09-25（现场为 2026-09-10，旧金山）。文件名取这一天"
    ) == "2026-09-25"
    assert public_date("") == ""
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
            "编辑说明": "本文根据公开对谈编辑整理，非逐字稿；观点归属对谈嘉宾。",
        }
    )
    assert "原文：Garry Tan: Own Your Intelligence" in foot
    assert "发布：2026-08-07" in foot
    assert "视频" not in foot and "非逐字稿" not in foot
    assert "http" not in foot and "页面口径" not in foot
    assert "发布：" not in source_footer({"原标题": "Only Title"})
    # escaped pipe inside a metadata cell (原标题 with a `|` separator)
    assert split_cells(r"| 原标题 | How to Stay Valuable \| Daron Acemoglu |") == [
        "原标题",
        "How to Stay Valuable | Daron Acemoglu",
    ]
    piped_meta, _ = parse_meta_table(
        [
            "| 项目 | 内容 |",
            "|---|---|",
            r"| 原标题 | Nobel Economist: How to Stay Valuable \| Daron Acemoglu |",
        ],
        0,
    )
    assert piped_meta["原标题"] == "Nobel Economist: How to Stay Valuable | Daron Acemoglu", piped_meta
    assert "原文：Nobel Economist: How to Stay Valuable | Daron Acemoglu" in source_footer(piped_meta)
    assert default_out_path(Path("20260803 刘润×吴军_整理文档.md")).name == (
        "20260803 刘润×吴军_整理文档_公众号文章.html"
    )
    editorial = """# Test\n\n## 开场\n\n> 一句话。\n\n正文。\n"""
    _, editorial_parts, detected = parse_md(editorial, mode="auto")
    assert detected == "editorial"
    assert any("border:1px solid" in part for part in editorial_parts)
    marked = _inline_no_link("差异化来自==该让什么存在==。")
    assert C["mark"] in marked and "该让什么存在" in marked
    assert C["accent_soft"] not in marked
    assert "==" not in marked
    assert "margin:48px 0 0" in section_kicker(1)
    _, spaced, _ = parse_md("# T\n\n## 开场\n\n一段正文。\n", mode="editorial")
    assert any("margin:0 0 20px" in part for part in spaced), spaced
    lede_src = "\n".join(
        ["# T", "## 文章元数据"]
        + [f"## 第{n}节\n\n### 核心洞察\n\n> 第{n}节的判断。还有第二句。\n" for n in range(LEDE_MIN_H2)]
    )
    assert len(reader_h2_titles(lede_src)) == LEDE_MIN_H2
    lede_map = insight_ledes(lede_src)
    assert lede_map[normalize_h2("第0节")] == "第0节的判断。"
    drafted = """# T\n\n## 开场\n\n> **本节**：成稿自己的一句。\n\n正文。\n"""
    _, drafted_parts, _ = parse_md(drafted, mode="editorial")
    assert any("data-wechat-lede=" in part for part in drafted_parts)
    injected = inject_section_ledes(drafted_parts, {normalize_h2("开场"): "不该再注入。"})
    assert sum("data-wechat-lede=" in part for part in injected) == 1
    bare = inject_section_ledes([h2("第0节"), p("另一句。")], lede_map)
    assert any("第0节的判断。" in part and "data-wechat-lede=" in part for part in bare)
    noisy = (
        "# T\n\n## 开场\n\n正文。\n\n## 编辑说明\n\n不要出现。\n\n"
        "## 免责声明\n\n也不要。\n"
    )
    _, noisy_parts, _ = parse_md(noisy, mode="editorial")
    noisy_html = "".join(noisy_parts)
    assert "编辑说明" not in noisy_html and "免责声明" not in noisy_html
    # upstream content-structuring spells the glossary with a suffix
    suffixed = (
        "# T\n\n## 开场\n\n正文。\n\n## 延伸术语表（可选）\n\n| 术语 | 解释 |\n|---|---|\n"
        "| Skill | 不该出现 |\n\n## 自检报告\n\n| a | b |\n"
    )
    _, suffixed_parts, _ = parse_md(suffixed, mode="editorial")
    suffixed_html = "".join(suffixed_parts)
    assert "延伸术语表" not in suffixed_html and "不该出现" not in suffixed_html, suffixed_html
    sample = wrap(
        "标题",
        [
            h1("标题"),
            h2("核心导读"),
            p("正文有==重点==和**人名**。", size="16px"),
            thesis_card("全文论点", "到 2035 年仍在增长。"),
        ],
    )
    start = sample.find('<section id="wechat-article"')
    article = sample[start : sample.rfind("</section>")]
    assert not re.search(r"line-height:\d+(?:\.\d+)?(?!\d)(?!px)", article), article
    assert "text-align:start" not in article and "text-align:end" not in article
    assert "text-align:left" in article and "text-align:center" in article
    assert re.search(r"<p style=\"[^\"]*line-height:28px[^\"]*\">", article)
    assert re.search(r"<h2 style=\"[^\"]*line-height:26px[^\"]*\">", article)
    assert "<p style=\"" in article and "><span style=\"color:" in article
    assert not re.search(r"<(?:p|h1|h2|h3|td)\b[^>]*>[^<\s]", article)
    card = dialogue_card("Zanny Minton Beddoes", "十年后，如果这些都做成，世界会是什么样？")
    assert "padding:1px" not in card and "display:inline-block" not in card
    assert "padding:0 8px" in card and card.count("<p ") == 2
    quote_p = card.rsplit("<p ", 1)[-1]
    assert "Zanny" not in quote_p
    byline = subtitle_from_meta({"对谈人物": "**甲某**（某节目主持人）× **乙某**（某公司创始人）"})
    assert byline == "甲某 × 乙某", byline
    numbered = number_sections([h2("核心导读"), p("论点"), h2("第一个话题"), h2("第二个话题")])
    joined = "".join(numbered)
    assert "第 1 节" in joined and "第 2 节" in joined and "第 3 节" not in joined
    assert joined.index("第 1 节") < joined.index("第一个话题")
    assert not re.search(r"<(?:p|h1|h2|h3|td)\b[^>]*>[^<\s]", joined)
    media_md = """# 图文测试

## 文章元数据

| 项目 | 内容 |
|---|---|
| 原标题 | Media Test |
| 对谈人物 | **甲**（主持人） × **乙**（嘉宾） |

### 官方章节索引

| 时间 | 章节 |
|---|---|
| 00:10 | 开场 |

> **讲者背景**：乙展示架构与曲线。

## 核心导读

> **全文论点**：保留关键视觉信息。

## 第一节

### 核心洞察

> 成本陡降。

### 深度解析

```mermaid
flowchart LR
  A["提示词"] --> B["执行闭环"]
  B -. 待补 .-> C["回归评测"]
```

如图 1 所示，单次成本下降 90%。内联 ![小图](https://cdn.example/inline.png) 与 [普通链接](https://cdn.example/doc)。

![原文图 1：推理成本下降曲线](https://pbs.twimg.com/media/abc?format=jpg&name=large)

*原文图 1：推理成本下降曲线（[原图地址](https://pbs.twimg.com/media/abc?format=jpg&name=large) · 原片定位：[14:20](https://youtu.be/x?t=860)）*

<video src="https://cdn.example/demo.mp4" controls playsinline preload="metadata"></video>

*原文图 8，是视频不是静图。[原视频地址](https://cdn.example/demo.mp4)*

```python
## 代码里的井号不是章节标题
x = [1, 2]
```

### 对谈实录

**甲**（14:20）：「这张图说明什么？」

**乙**（14:25, 58:10 合并）：「说明趋势已经成立。」
"""
    _, full_parts, full_mode = parse_md(media_md, mode="auto")
    assert full_mode == "full"
    full_article = "\n".join(full_parts)
    assert 'data-wechat-figure="1"' in full_article
    assert '<img src="https://pbs.twimg.com/media/abc?format=jpg&amp;name=large"' in full_article
    assert 'referrerpolicy="no-referrer"' in full_article
    assert "!<a " not in full_article
    assert "原图地址" not in full_article
    assert "原片定位：14:20" in full_article
    assert "data-wechat-diagram=\"1\"" in full_article
    assert "提示词 → 执行闭环" in full_article
    assert "flowchart LR" not in full_article
    assert "data-wechat-video=\"1\"" in full_article
    assert "&lt;video" not in full_article and "<video" not in full_article
    assert "代码里的井号不是章节标题" in full_article
    assert "<h2><span" not in full_article.split("代码里的井号不是章节标题")[0][-80:]
    assert "甲（14:20）" in full_article
    assert "乙（14:25, 58:10 合并）" in full_article
    assert "乙展示架构与曲线" in full_article
    assert not re.search(r"line-height:\d+(?:\.\d+)?(?!\d)(?!px)", full_article), full_article
    assert not re.search(r"<(?:p|h1|h2|h3|td)\b[^>]*>[^<\s]", full_article), full_article

    _, ed_parts, ed_mode = parse_md(media_md, mode="editorial")
    assert ed_mode == "editorial"
    ed_article = "\n".join(ed_parts)
    assert 'data-wechat-figure="1"' in ed_article
    assert "data-wechat-diagram=" not in ed_article
    assert "data-wechat-video=" not in ed_article
    assert "是视频不是静图" not in ed_article
    assert "14:20" not in ed_article and "58:10" not in ed_article
    print("self-test OK")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("markdown", type=Path, nargs="?", help="Path to *_整理文档.md")
    ap.add_argument("--out", type=Path, default=None, help="Output HTML path")
    ap.add_argument(
        "--mode",
        choices=("auto", "editorial", "full"),
        default="auto",
        help="editorial article or complete three-layer conversion",
    )
    ap.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Original *_整理文档.md when building from a temp editorial draft "
        "(fingerprinted so the validator can flag a stale article; default: the input)",
    )
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

    title, parts, mode = parse_md(src.read_text(encoding="utf-8"), mode=args.mode)
    if mode == "editorial" and any("<table" in part for part in parts):
        print(
            "WARNING: editorial mode emitted native <table>; "
            "rewrite comparisons as sentences and rebuild.",
            file=sys.stderr,
        )
    origin = args.source or src
    if not origin.is_file():
        print(f"ERROR: --source not found: {origin}", file=sys.stderr)
        return 2
    if mode == "editorial":
        source_text = origin.read_text(encoding="utf-8")
        if len(reader_h2_titles(source_text)) >= LEDE_MIN_H2:
            parts = inject_section_ledes(parts, insight_ledes(source_text))
    html_out = wrap(title, parts, mode=mode, fingerprint=source_fingerprint(origin))
    out = args.out or default_out_path(src)
    out.write_text(html_out, encoding="utf-8")
    print(f"Wrote {out} ({len(html_out)} chars, mode={mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

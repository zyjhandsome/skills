#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Embed cover title and speakers in the image center.

Typography follows the editorial WeChat cover (serif title, terracotta,
tracked letters, hairline, muted people line). No white plate, capsule,
or baked-in GenerateImage text.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Title = accent-strong; people = muted terracotta (not near-black YaHei).
TITLE_FILL = (168, 85, 51)       # #A85533
PEOPLE_FILL = (176, 148, 128)    # #B09480
HAIRLINE_FILL = (212, 168, 148)  # #D4A894
HAIRLINE_W = 56
HAIRLINE_H = 2

# Quiet band the type must sit in (fraction of canvas width / height).
MAX_WIDTH_RATIO = 0.78
TITLE_TRACK = 0.10          # em
PEOPLE_TRACK = 0.14         # em
TITLE_MAX = 62
TITLE_MIN = 30
PEOPLE_RATIO = 0.36
PEOPLE_MIN = 16
LINE_GAP_RATIO = 0.22       # gap between two title lines, relative to size
STACK_GAP = 22              # title block → hairline
PEOPLE_GAP = 16             # hairline → people


def _font(path: str, size: int, index: int = 0):
    from PIL import ImageFont

    return ImageFont.truetype(path, size, index=index)


def _first_existing(candidates: list[tuple[str, int]]) -> tuple[str, int] | None:
    for path, index in candidates:
        if Path(path).is_file():
            return path, index
    return None


def _title_font_spec() -> tuple[str, int]:
    found = _first_existing([
        (r"C:\Windows\Fonts\STZHONGS.TTF", 0),      # 华文中宋
        (r"C:\Windows\Fonts\NotoSerifSC-VF.ttf", 0),
        (r"C:\Windows\Fonts\STSONG.TTF", 0),
        (r"C:\Windows\Fonts\simsun.ttc", 0),
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),
        ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc", 0),
    ])
    if found:
        return found
    raise SystemExit("No Chinese serif font found (tried 华文中宋 / Noto Serif SC / 宋体).")


def _people_font_spec() -> tuple[str, int]:
    found = _first_existing([
        (r"C:\Windows\Fonts\HarmonyOS_Sans_SC_Regular.ttf", 0),
        (r"C:\Windows\Fonts\Deng.ttf", 0),
        (r"C:\Windows\Fonts\msyh.ttc", 0),
        ("/System/Library/Fonts/PingFang.ttc", 0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ])
    if found:
        return found
    raise SystemExit("No people-line sans font found.")


def _split_title(title: str) -> list[str]:
    title = (title or "").strip()
    if not title:
        return []
    for sep in ("：", ":"):
        if sep in title:
            a, b = title.split(sep, 1)
            parts = [p.strip() for p in (a, b) if p.strip()]
            if parts:
                return parts
    return [title]


def _advance(font, ch: str) -> float:
    if hasattr(font, "getlength"):
        return float(font.getlength(ch))
    box = font.getbbox(ch)
    return float(box[2] - box[0])


def _tracked_width(text: str, font, tracking_em: float) -> float:
    if not text:
        return 0.0
    size = getattr(font, "size", 16)
    extra = tracking_em * size
    widths = [_advance(font, ch) for ch in text]
    return sum(widths) + extra * max(len(text) - 1, 0)


def _line_height(font) -> int:
    """Use the em box, not ink bbox — ink height under-counts 宋体 and
    parks the hairline on the last title line like an underline."""
    try:
        ascent, descent = font.getmetrics()
        return int(ascent + descent)
    except (AttributeError, OSError):
        return int(getattr(font, "size", 16) * 1.25)


def _draw_tracked(draw, text: str, x: float, y: float, font, fill, tracking_em: float) -> None:
    size = getattr(font, "size", 16)
    extra = tracking_em * size
    cursor = x
    for i, ch in enumerate(text):
        draw.text((cursor, y), ch, font=font, fill=fill)
        cursor += _advance(font, ch)
        if i < len(text) - 1:
            cursor += extra


def _fit_title_font(lines: list[str], max_w: float) -> tuple[object, int]:
    path, index = _title_font_spec()
    for size in range(TITLE_MAX, TITLE_MIN - 1, -1):
        font = _font(path, size, index)
        if all(_tracked_width(line, font, TITLE_TRACK) <= max_w for line in lines):
            return font, size
    return _font(path, TITLE_MIN, index), TITLE_MIN


def _wrap_if_needed(lines: list[str], max_w: float) -> list[str]:
    """If a single leftover line is still too wide at TITLE_MIN, split it."""
    path, index = _title_font_spec()
    min_font = _font(path, TITLE_MIN, index)
    out: list[str] = []
    for line in lines:
        if _tracked_width(line, min_font, TITLE_TRACK) <= max_w or len(line) < 8:
            out.append(line)
            continue
        mid = max(4, len(line) // 2)
        # Prefer a punctuation / space cut near the midpoint.
        cut = mid
        for i in range(mid, 3, -1):
            if line[i - 1] in "，、；。 !！?？—- ":
                cut = i
                break
        out.extend([line[:cut].strip(), line[cut:].strip()])
    return [p for p in out if p]


def overlay(path: Path, title: str, people: str) -> None:
    from PIL import Image, ImageDraw

    im = Image.open(path).convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im)
    max_w = w * MAX_WIDTH_RATIO

    lines = _wrap_if_needed(_split_title(title), max_w)
    people = (people or "").strip()
    title_font, title_size = _fit_title_font(lines, max_w) if lines else (None, TITLE_MIN)

    people_path, people_index = _people_font_spec()
    people_size = max(PEOPLE_MIN, int(title_size * PEOPLE_RATIO))
    people_font = _font(people_path, people_size, people_index)
    while people and _tracked_width(people, people_font, PEOPLE_TRACK) > max_w and people_size > PEOPLE_MIN:
        people_size -= 1
        people_font = _font(people_path, people_size, people_index)

    blocks: list[tuple[str, object, tuple[int, int, int], float, float]] = []
    people_h = _line_height(people_font)
    line_gap = int(title_size * LINE_GAP_RATIO)

    for i, line in enumerate(lines):
        gap = line_gap if i < len(lines) - 1 else 0
        blocks.append((line, title_font, TITLE_FILL, TITLE_TRACK, gap))

    hairline = bool(lines and people)
    total_h = 0.0
    for text, font, _fill, _tr, gap in blocks:
        total_h += _line_height(font) + gap
    if hairline:
        total_h += STACK_GAP + HAIRLINE_H + PEOPLE_GAP
    if people:
        total_h += people_h

    y = (h - total_h) / 2
    for text, font, fill, tracking, gap in blocks:
        tw = _tracked_width(text, font, tracking)
        th = _line_height(font)
        _draw_tracked(draw, text, (w - tw) / 2, y, font, fill, tracking)
        y += th + gap

    if hairline:
        y += STACK_GAP
        x0 = (w - HAIRLINE_W) / 2
        draw.rectangle((x0, y, x0 + HAIRLINE_W, y + HAIRLINE_H), fill=HAIRLINE_FILL)
        y += HAIRLINE_H + PEOPLE_GAP

    if people:
        tw = _tracked_width(people, people_font, PEOPLE_TRACK)
        _draw_tracked(draw, people, (w - tw) / 2, y, people_font, PEOPLE_FILL, PEOPLE_TRACK)

    im.save(path, format="PNG", optimize=True)
    print(f"Overlaid text on {path} size={im.size} title_px={title_size}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=Path)
    ap.add_argument("--title", default="", help="Article H1")
    ap.add_argument("--people", default="", help="Speakers, shown under the title")
    args = ap.parse_args(argv)
    if not args.image.is_file():
        print(f"ERROR: not found: {args.image}", file=sys.stderr)
        return 2
    overlay(args.image, args.title, args.people)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

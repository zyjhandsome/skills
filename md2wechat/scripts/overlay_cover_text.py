#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Embed cover title and speakers in the image center. No white plate."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TITLE_FILL = (26, 26, 26)
PEOPLE_FILL = (168, 85, 51)


def _font(path: str, size: int):
    from PIL import ImageFont

    return ImageFont.truetype(path, size)


def _pick_fonts(title_size: int, people_size: int):
    candidates = [
        (r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc"),
        ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/PingFang.ttc"),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    last_err: Exception | None = None
    for bold, regular in candidates:
        try:
            if Path(bold).is_file() and Path(regular).is_file():
                return _font(bold, title_size), _font(regular, people_size)
        except OSError as e:
            last_err = e
    raise SystemExit(
        "No Chinese font found (tried Microsoft YaHei / PingFang / Noto Sans CJK)."
        + (f"\n{last_err}" if last_err else "")
    )


def _split_title(title: str) -> list[str]:
    title = (title or "").strip()
    if not title:
        return []
    if "：" in title:
        a, b = title.split("：", 1)
        return [a, b] if b else [a]
    if ":" in title:
        a, b = title.split(":", 1)
        return [a, b] if b else [a]
    return [title]


def _size(draw, text: str, font) -> tuple[int, int]:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1]


def overlay(path: Path, title: str, people: str) -> None:
    from PIL import Image, ImageDraw

    im = Image.open(path).convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im)
    title_font, people_font = _pick_fonts(title_size=40, people_size=20)
    lines = _split_title(title)
    people = (people or "").strip()

    blocks: list[tuple[str, object, tuple[int, int, int], int]] = []
    for line in lines:
        blocks.append((line, title_font, TITLE_FILL, 10))
    if people:
        if blocks:
            # extra gap between title block and speakers
            last = blocks[-1]
            blocks[-1] = (last[0], last[1], last[2], 18)
        blocks.append((people, people_font, PEOPLE_FILL, 0))
    if not blocks:
        raise SystemExit("Need --title and/or --people")

    sizes = [_size(draw, t, f) for t, f, _, _ in blocks]
    total_h = sum(s[1] for s in sizes) + sum(gap for *_, gap in blocks[:-1])
    y = (h - total_h) / 2
    for (text, font, fill, gap), (tw, th) in zip(blocks, sizes):
        draw.text(((w - tw) / 2, y), text, font=font, fill=fill)
        y += th + gap

    im.save(path, format="PNG", optimize=True)
    print(f"Overlaid text on {path} size={im.size}")


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

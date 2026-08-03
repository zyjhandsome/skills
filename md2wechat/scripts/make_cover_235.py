#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Center-crop / resize an image to exact WeChat cover ratio 2.35:1."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RATIO = 2.35
DEFAULT_SIZE = (1175, 500)


def convert(src: Path, out: Path, width: int, height: int) -> None:
    try:
        from PIL import Image
    except ImportError as e:
        raise SystemExit(
            "Pillow required: python -m pip install pillow\n" + str(e)
        ) from e

    im = Image.open(src).convert("RGB")
    w, h = im.size
    target_h = int(round(w / RATIO))
    if target_h <= h:
        top = (h - target_h) // 2
        im = im.crop((0, top, w, top + target_h))
    else:
        target_w = int(round(h * RATIO))
        left = max(0, (w - target_w) // 2)
        im = im.crop((left, 0, left + min(target_w, w), h))

    im_out = im.resize((width, height), Image.Resampling.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    im_out.save(out, format="PNG", optimize=True)
    print(f"Wrote {out} size={im_out.size} ratio={width/height:.3f}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--width", type=int, default=DEFAULT_SIZE[0])
    ap.add_argument("--height", type=int, default=DEFAULT_SIZE[1])
    args = ap.parse_args(argv)

    if abs(args.width / args.height - RATIO) > 0.01:
        print(
            f"WARN: {args.width}x{args.height} is not ~2.35:1 "
            f"(got {args.width/args.height:.3f})",
            file=sys.stderr,
        )
    if not args.image.is_file():
        print(f"ERROR: not found: {args.image}", file=sys.stderr)
        return 2
    convert(args.image, args.out, args.width, args.height)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

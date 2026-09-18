# -*- coding: utf-8 -*-
"""Cover overlay writes tEXt and refuses a second pass."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

from overlay_cover_text import COVER_TITLE_KEY, overlay  # noqa: E402
from validate_wechat_bundle import validate_cover  # noqa: E402


@unittest.skipIf(Image is None, "Pillow not installed")
class OverlayCoverTests(unittest.TestCase):
    def _blank(self) -> Path:
        path = Path(tempfile.mkdtemp()) / "scene.png"
        Image.new("RGB", (1175, 500), (250, 250, 247)).save(path)
        return path

    def test_writes_title_text_chunk(self):
        src = self._blank()
        out = src.with_name("cover.png")
        overlay(src, "反馈循环越短，判断越可靠", "甲 × 乙", out=out)
        with Image.open(out) as im:
            stored = im.info.get(COVER_TITLE_KEY)
        self.assertEqual(stored, "反馈循环越短，判断越可靠")
        errors = validate_cover(out, expected_title="反馈循环越短，判断越可靠")
        self.assertEqual(errors, [])

    def test_refuses_second_overlay(self):
        src = self._blank()
        overlay(src, "标题一次", "甲")
        with self.assertRaises(SystemExit):
            overlay(src, "标题二次", "乙")


if __name__ == "__main__":
    unittest.main()

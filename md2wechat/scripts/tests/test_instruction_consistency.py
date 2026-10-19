# -*- coding: utf-8 -*-
"""The prose contract matches the validator and the cover prompt.

These three sentences used to disagree with the code an agent is told to run:
audit verb 合并 meant "flatten layers" in one file and "join two H2s" in the
validator; paragraph length was both 150 and a 200-character cap; the cover
prompt said "about half empty" next to a 70% empty rule.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


class InstructionConsistencyTests(unittest.TestCase):
    def test_merge_verb_is_not_layer_flattening(self):
        integrity = _text("references/content-integrity.md")
        skill = _text("SKILL.md")
        self.assertNotIn("only for layers", integrity)
        self.assertIn("EDITORIAL CANNOT 合并 ACROSS H2", integrity)
        self.assertIn("Layer flattening stays `保留`", integrity)
        self.assertIn("节内把三层合成叙述仍标 `保留`", skill)
        self.assertNotIn("完成覆盖判断（`保留 / 合并 / 删减 / 删除`）", skill)

    def test_paragraph_numbers_have_one_job_each(self):
        skill = _text("SKILL.md")
        editorial = _text("references/editorial-and-audio.md")
        self.assertIn("一段大约 150 字", skill)
        self.assertIn("超过 200 字时 WARN", skill)
        self.assertNotIn("控制在约 200 字以内", skill)
        self.assertIn("Split a paragraph at about 150 汉字", editorial)
        self.assertIn("warns above 200 汉字", editorial)
        self.assertIn("Neither number is a ceiling", editorial)

    def test_eye_comfort_is_the_same_in_skill_and_builder(self):
        skill = _text("SKILL.md")
        editorial = _text("references/editorial-and-audio.md")
        constraints = _text("references/wechat-constraints.md")
        self.assertIn("段后距是 20px", skill)
        self.assertIn("`#F0D5C4`", skill)
        self.assertIn("达到 12 节", skill)
        self.assertIn("about 40 汉字 or less", editorial)
        self.assertIn("at least 12 reader-facing H2s", editorial)
        self.assertIn("| mark | `#F0D5C4` |", constraints)
        self.assertIn("margin:0 0 20px", constraints)

    def test_cover_prompt_uses_the_seventy_percent_field(self):
        skill = _text("SKILL.md")
        examples = _text("examples.md")
        self.assertIn("中间 70% 的宽度完全空着，主体只放在左右最外 15%", skill)
        self.assertNotIn("正中约一半宽度", skill)
        self.assertIn("middle 70%", examples)
        self.assertIn("about half the width", examples)
        self.assertIn("outer 15%", examples)


if __name__ == "__main__":
    unittest.main()

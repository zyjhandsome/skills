"""4f-3 / 4f-4: editor notes stay atomic and are not spoken as dialogue."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_revision_loss as rev

CLOSED = """
## 目录

正文。[编者注：创业公司和载体都是上台段子。没有收成可核实的公司事实。]

**Jason Calacanis**：「听起来像真的。」

## 自检报告
"""

BROKEN = """
## 目录

[编者注：创业公司和载体都是上台段子。

**Jason Calacanis**：「没有收成可核实的公司事实。」

**Jason Calacanis**：「]」

]

## 自检报告
"""


class BracketIntegrityTest(unittest.TestCase):
    def test_closed_note_is_clean(self) -> None:
        self.assertEqual(rev.bracket_issues(CLOSED), [])

    def test_split_note_is_flagged(self) -> None:
        issues = rev.bracket_issues(BROKEN)
        self.assertTrue(any("未在同一段收口" in item for item in issues))
        self.assertTrue(any("收口括号" in item for item in issues))

    def test_note_sentence_lifted_into_dialogue(self) -> None:
        lifted = rev.lifted_notes(CLOSED, BROKEN)
        self.assertTrue(any("没有收成可核实的公司事实" in item for item in lifted))

    def test_closed_note_is_not_lifted(self) -> None:
        self.assertEqual(rev.lifted_notes(CLOSED, CLOSED), [])


if __name__ == "__main__":
    unittest.main()

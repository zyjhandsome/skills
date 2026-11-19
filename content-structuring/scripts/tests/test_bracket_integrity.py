"""4f-3 / 4f-4 / 4f-5: editor notes, code fences, speaker timestamps, and media loss."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_revision_loss as rev  # noqa: E402

CLOSED = """
## 目录

正文。[编者注：创业公司和载体都是上台段子。没有收成可核实的公司事实。]

**Jason Calacanis**（14:20）：「听起来像真的。」

## 自检报告
"""

BROKEN = """
## 目录

[编者注：创业公司和载体都是上台段子。

**Jason Calacanis**（14:20）：「没有收成可核实的公司事实。」

**Jason Calacanis**：「]」

]

## 自检报告
"""

CODE_FENCE_ARRAY = """
## 目录

```json
[
  "Agent",
  "Loop"
]
```

## 自检报告
"""

UNCLOSED_NOTE_WITH_IMAGE = """
## 目录

[编者注：参见 ![原文图 1](https://example.com/fig1.png)，此处口播未给具体数值

## 自检报告
"""

CLOSED_NOTE_WITH_LINK = """
## 目录

[编者注：参见 [原图地址](https://example.com/fig1.png)，此处属于编者口径推断而非原话。]

## 自检报告
"""


class BracketIntegrityTest(unittest.TestCase):
    def test_closed_note_is_clean(self) -> None:
        self.assertEqual(rev.bracket_issues(CLOSED), [])

    def test_split_note_is_flagged(self) -> None:
        issues = rev.bracket_issues(BROKEN)
        self.assertTrue(any("未在同一段收口" in item for item in issues))
        self.assertTrue(any("收口括号" in item for item in issues))

    def test_note_sentence_lifted_into_timestamped_dialogue(self) -> None:
        lifted = rev.lifted_notes(CLOSED, BROKEN)
        self.assertTrue(any("没有收成可核实的公司事实" in item for item in lifted))

    def test_closed_note_is_not_lifted(self) -> None:
        self.assertEqual(rev.lifted_notes(CLOSED, CLOSED), [])

    def test_code_fence_closing_bracket_is_ignored(self) -> None:
        self.assertEqual(rev.bracket_issues(CODE_FENCE_ARRAY), [])

    def test_nested_image_bracket_does_not_mask_unclosed_note(self) -> None:
        issues = rev.bracket_issues(UNCLOSED_NOTE_WITH_IMAGE)
        self.assertTrue(any("未在同一段收口" in item for item in issues), issues)
        self.assertEqual(rev.bracket_issues(CLOSED_NOTE_WITH_LINK), [])
        # Sentences after nested link inside closed editor note are still extracted for 4f-4
        after_lifted = """
## 目录

**甲**（05:10）：「此处属于编者口径推断而非原话。」

## 自检报告
"""
        self.assertTrue(rev.lifted_notes(CLOSED_NOTE_WITH_LINK, after_lifted))

    def test_lost_media_detects_deleted_image_and_video_urls(self) -> None:
        before = """
## 目录

![图1](https://example.com/a.png)

<video src="https://example.com/b.mp4" controls preload="metadata"></video>

## 自检报告
"""
        after = """
## 目录

![图1](https://example.com/a.png)

## 自检报告
"""
        self.assertEqual(rev.lost_media(before, after), ["https://example.com/b.mp4"])


if __name__ == "__main__":
    unittest.main()

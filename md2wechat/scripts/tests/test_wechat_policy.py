# -*- coding: utf-8 -*-
"""Tests for the WeChat 运营规范 gate.

These encode the production failure: a leaked closed-door investor talk
plus unverified financing news was converted into a paste-ready WeChat
article and later deleted for 法律法规和政策.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from wechat_policy import (  # noqa: E402
    scan_source_risks,
    title_policy_errors,
    validate_policy_audit,
    validate_source_against_audit,
)


LEAK_SOURCE = """
# 梁文锋4小时讲话外泄(全文)，DeepSeek突然暂停第二轮融资

主源：外泄投资人交流转写。主持人要求数字和卡量不要外传、不要录屏。
彭博社知情人士称第二轮融资被口头暂停，尚未核实。
亚洲金融称梁文锋与落马的方星海、易会满关系密切。
"""

PUBLIC_TALK_SOURCE = """
# 吴军谈工程师成长：把反馈循环做短

这是一场公开技术分享。吴军说，成长靠的是可验证的反馈，而不是口号。
"""


class ScanSourceTests(unittest.TestCase):
    def test_flags_unauthorized_leak_and_unverified_finance(self):
        findings = scan_source_risks(LEAK_SOURCE)
        codes = {f.code for f in findings}
        self.assertIn("leak_closed_door", codes)
        self.assertIn("unverified_finance", codes)
        self.assertIn("political_public_event", codes)
        self.assertTrue(any(f.severity == "stop" for f in findings))

    def test_keeps_ordinary_public_talk_publishable(self):
        self.assertEqual(scan_source_risks(PUBLIC_TALK_SOURCE), [])


class TitleTests(unittest.TestCase):
    def test_rejects_leak_and_breaking_finance_news(self):
        errors = title_policy_errors(
            "梁文锋4小时讲话外泄(全文)，DeepSeek突然暂停第二轮融资"
        )
        blob = "\n".join(errors).lower()
        self.assertGreaterEqual(len(errors), 2, errors)
        self.assertIn("leak", blob)
        self.assertIn("financ", blob)

    def test_allows_public_talk_judgment(self):
        self.assertEqual(
            title_policy_errors("克制才能做成：公开分享里的开源定价"),
            [],
        )


class AuditTests(unittest.TestCase):
    def test_requires_policy_conclusion(self):
        errors = validate_policy_audit("# 公众号内容审计\n\n## 覆盖矩阵\n")
        self.assertTrue(any("运营规范" in e for e in errors))
        self.assertTrue(any("发布结论" in e for e in errors))

    def test_accepts_publishable_conclusions(self):
        for conclusion in ("可发布", "改写后可发布"):
            text = (
                "# 公众号内容审计\n\n"
                "## 运营规范\n"
                f"- 发布结论：{conclusion}\n"
                "- 风险清单：无\n"
            )
            self.assertEqual(validate_policy_audit(text), [])

    def test_unpublished_is_valid_without_html(self):
        text = "# 公众号内容审计\n\n## 运营规范\n- 发布结论：不可发布\n"
        self.assertEqual(validate_policy_audit(text, html_delivered=False), [])

    def test_unpublished_cannot_pair_with_html(self):
        text = "# 公众号内容审计\n\n## 运营规范\n- 发布结论：不可发布\n"
        errors = validate_policy_audit(text, html_delivered=True)
        self.assertTrue(any("不可发布" in e and "HTML" in e for e in errors))

    def test_source_stop_risks_cannot_be_marked_publishable(self):
        audit = "# 审计\n\n## 运营规范\n- 发布结论：可发布\n"
        errors = validate_source_against_audit(
            LEAK_SOURCE, audit, html_delivered=True
        )
        self.assertTrue(any("可发布" in e for e in errors))

    def test_public_talk_does_not_require_audit(self):
        self.assertEqual(
            validate_source_against_audit(
                PUBLIC_TALK_SOURCE, None, html_delivered=True
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()

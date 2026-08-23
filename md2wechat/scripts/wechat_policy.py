#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WeChat 公众平台运营规范 gate for md2wechat article sources and H1s.

Mechanical scanner only. It cannot certify legality. A stop finding means
do not deliver paste-ready HTML until the claim is cut or the job is halted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

POLICY_CONCLUSIONS = frozenset({"可发布", "改写后可发布", "不可发布"})
POLICY_OFFICIAL_URL = (
    "https://mp.weixin.qq.com/cgi-bin/readtemplate"
    "?t=business/faq_operation_tmpl&type=info&lang=zh_CN&token="
)

_LEAK_PATTERNS = (
    r"外泄",
    r"泄密",
    r"闭门.{0,12}(会|交流|投资)",
    r"不要外传",
    r"勿外传",
    r"不要录屏",
    r"内部录音",
    r"讲话外泄",
)
_FINANCE_PATTERNS = (
    r"知情人士",
    r"尚未核实",
    r"突然.{0,12}融资",
    r"据报.{0,12}融资",
    r"暂停.{0,16}融资",
)
_POLITICAL_PATTERNS = (
    r"落马",
    r"卷入政治",
)
_TITLE_FAIL = (
    (r"外泄", "H1 frames an unauthorized leak as the story (运营规范 4.1/4.12)"),
    (r"泄密", "H1 frames leaked confidential material as the story"),
    (r"(讲话|录音|闭门).{0,8}全文", "H1 promises a leaked or unauthorized full text"),
    (r"突然.{0,12}融资", "H1 treats unverified financing as breaking news (4.9/4.11)"),
    (r"震惊|心虚|爆料", "H1 uses 误导类/标题党 wording (4.11)"),
)


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    detail: str


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(p, text) for p in patterns)


def scan_source_risks(text: str) -> list[Finding]:
    """Scan a 整理文档 (or draft) for publish-blocking 运营规范 risks."""
    findings: list[Finding] = []
    if _has_any(text, _LEAK_PATTERNS):
        findings.append(
            Finding(
                "leak_closed_door",
                "stop",
                "Source is or reprints an unauthorized closed-door leak "
                "(运营规范 4.1 侵权/商业秘密, 4.12 违法违规). "
                "Editorial rewrite does not authorize publishing the leak.",
            )
        )
    if _has_any(text, _FINANCE_PATTERNS):
        findings.append(
            Finding(
                "unverified_finance",
                "stop",
                "Unverified financing/valuation rumor (知情人士/突然/尚未核实). "
                "运营规范 4.9 谣言类, 4.11 误导类. Attribution is not enough.",
            )
        )
    if _has_any(text, _POLITICAL_PATTERNS):
        findings.append(
            Finding(
                "political_public_event",
                "stop",
                "Political/public-event association (落马等). "
                "运营规范『遵守当地法律监管』: do not pull the account into "
                "政治和公共事件.",
            )
        )
    return findings


def title_policy_errors(h1: str) -> list[str]:
    errors: list[str] = []
    for pat, msg in _TITLE_FAIL:
        if re.search(pat, h1):
            errors.append(f"POLICY TITLE: {msg}")
    return errors


def extract_policy_conclusion(audit_text: str) -> str | None:
    m = re.search(r"发布结论[：:]\s*(可发布|改写后可发布|不可发布)", audit_text)
    return m.group(1) if m else None


def validate_policy_audit(audit_text: str, html_delivered: bool = False) -> list[str]:
    errors: list[str] = []
    if "运营规范" not in audit_text:
        errors.append("AUDIT MISSING: 运营规范")
    conclusion = extract_policy_conclusion(audit_text)
    if conclusion is None:
        errors.append("AUDIT MISSING: 发布结论")
        return errors
    if conclusion not in POLICY_CONCLUSIONS:
        errors.append(f"AUDIT INVALID: 发布结论 {conclusion}")
    if conclusion == "不可发布" and html_delivered:
        errors.append("POLICY: 发布结论是不可发布, but HTML was delivered")
    return errors


def validate_source_against_audit(
    source_text: str,
    audit_text: str | None,
    html_delivered: bool,
) -> list[str]:
    errors: list[str] = []
    findings = scan_source_risks(source_text)
    stop = [f for f in findings if f.severity == "stop"]
    if not stop:
        return errors
    if not audit_text:
        errors.append(
            "POLICY: source has 运营规范 stop risks; pass --audit with 发布结论"
        )
        return errors
    conclusion = extract_policy_conclusion(audit_text)
    if conclusion == "可发布":
        codes = ", ".join(sorted({f.code for f in stop}))
        errors.append(
            f"POLICY: cannot mark 可发布 while stop risks remain ({codes})"
        )
    elif conclusion == "不可发布" and html_delivered:
        errors.append("POLICY: 发布结论是不可发布, but HTML was delivered")
    elif conclusion is None:
        errors.append("AUDIT MISSING: 发布结论")
    return errors


def format_scan_report(findings: list[Finding]) -> str:
    if not findings:
        return "POLICY OK: no mechanical 运营规范 stop signals"
    lines = ["POLICY RISK"]
    for f in findings:
        lines.append(f" - [{f.severity}] {f.code}: {f.detail}")
    lines.append(f"Official: {POLICY_OFFICIAL_URL}")
    return "\n".join(lines)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan a 整理文档 or draft H1 for 微信公众平台运营规范 stop risks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from wechat_policy import (
    format_scan_report,
    scan_source_risks,
    title_policy_errors,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path, help="整理文档.md or editorial draft")
    ap.add_argument("--title", default="", help="Optional draft H1 to check")
    args = ap.parse_args(argv)

    if not args.source.is_file():
        print(f"ERROR: source not found: {args.source}")
        return 2

    text = args.source.read_text(encoding="utf-8")
    findings = scan_source_risks(text)
    print(format_scan_report(findings))

    title_errors = title_policy_errors(args.title) if args.title else []
    for e in title_errors:
        print(f" - {e}")

    if findings or title_errors:
        print(
            "STOP or rewrite before writing HTML. "
            "Read references/wechat-operation-policy.md. "
            "Do not use full mode to reprint blocked claims."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

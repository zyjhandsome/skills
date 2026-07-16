#!/usr/bin/env python3
"""One-command delivery-family self-check. Run before shipping the four delivery-* skills.

Runs, in order:
  1. test_family_integrity.py          — references resolve, atomic set present, version majors
  2. ../../delivery-execute-verify/tests/test_template_anchor_consistency.py
                                       — machine anchors + limited synonym lock
  3. run_fixture_tests.py              — 12 pass/neg handoff fixtures (hard profile)
  4. test_single_chain.py              — Standard 4-stage chain + cascade + High slice

Exit 0 only when every suite passes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SUITES = (
    TESTS_DIR / "test_family_integrity.py",
    TESTS_DIR.parent.parent / "delivery-execute-verify" / "tests" / "test_template_anchor_consistency.py",
    TESTS_DIR / "run_fixture_tests.py",
    TESTS_DIR / "test_single_chain.py",
)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    failed = []
    for suite in SUITES:
        print(f"\n=== {suite.name} ===", flush=True)
        result = subprocess.run([sys.executable, str(suite)])
        if result.returncode != 0:
            failed.append(suite.name)
    if failed:
        print(f"\nSELF-CHECK FAILED: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"\nSELF-CHECK PASSED: all {len(SUITES)} suites green — family is shippable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

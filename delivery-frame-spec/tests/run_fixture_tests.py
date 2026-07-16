#!/usr/bin/env python3
"""P0-1 regression lock: run validate_handoff (hard profile) against the fixture set.

Fixture naming convention:
  fixtures/pass-*.json  -> must validate PASS
  fixtures/neg-*.json   -> must validate FAIL (the R2/R3 negative probes)

If a neg-* fixture starts passing, a guardrail was weakened: either restore it or add a
documented replacement control plus a new probe before merging.

Standard library only. Exit 0 = all expectations hold, 1 = regression.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent / "scripts"))

from validate_handoff import validate  # noqa: E402

FIXTURES = TESTS_DIR / "fixtures"


def main() -> int:
    fixtures = sorted(FIXTURES.glob("*.json"))
    if not fixtures:
        print(f"ERROR: no fixtures found in {FIXTURES}", file=sys.stderr)
        return 1

    regressions = 0
    for path in fixtures:
        expect_pass = path.name.startswith("pass-")
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate(data, profile="hard")
        passed = not errors
        ok = passed == expect_pass
        print(f"[{'OK ' if ok else 'REGRESSION'}] {path.name}: {'PASS' if passed else 'FAIL'}"
              f" (expected {'PASS' if expect_pass else 'FAIL'})")
        if not ok:
            regressions += 1
            for error in errors:
                print(f"        - {error}")

    if regressions:
        print(f"\nRESULT: {regressions} regression(s) — do not merge", file=sys.stderr)
        return 1
    print(f"\nRESULT: all {len(fixtures)} fixture expectations hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

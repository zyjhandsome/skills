from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_visual_report", ROOT / "scripts" / "validate_visual_report.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidateVisualReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid = (ROOT / "fixtures" / "valid-report.md").read_text(encoding="utf-8")

    def test_valid_independent_report(self) -> None:
        self.assertEqual([], MODULE.validate(self.valid))

    def test_rejects_strict_parity_without_baseline(self) -> None:
        text = self.valid.replace("git:before-upgrade/screenshots", "TBD")
        self.assertIn("strict_parity requires a traceable baseline_source", MODULE.validate(text))

    def test_rejects_completed_remediation_without_go(self) -> None:
        text = self.valid.replace(
            "Phase B go：go:visual-fix / user / 2026-08-04T10:00:00+08:00 / r2",
            "Phase B go：未批准",
        )
        self.assertTrue(any("Phase B go" in error for error in MODULE.validate(text)))

    def test_rejects_placeholder_source_snapshot(self) -> None:
        text = self.valid.replace(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", "TBD"
        )
        self.assertTrue(any("source_snapshot" in error for error in MODULE.validate(text)))

    def test_cross_repo_fixture_ok(self) -> None:
        text = (ROOT / "fixtures" / "valid-report-cross-repo.md").read_text(encoding="utf-8")
        self.assertEqual([], MODULE.validate(text))

    def test_cross_repo_requires_roots(self) -> None:
        text = (ROOT / "fixtures" / "valid-report-cross-repo.md").read_text(encoding="utf-8")
        text = text.replace("- baseline_root：`/repo/vue2-source`\n", "")
        errors = MODULE.validate(text)
        self.assertTrue(any("baseline_root" in e for e in errors), errors)

    def test_rejects_failed_required_row(self) -> None:
        text = self.valid.replace("| P4 | pass |", "| P4 | fail |")
        self.assertIn("complete report requires P4=pass", MODULE.validate(text))


if __name__ == "__main__":
    unittest.main()

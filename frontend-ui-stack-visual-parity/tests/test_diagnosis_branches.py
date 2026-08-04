from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DiagnosisBranchTests(unittest.TestCase):
    def test_diagnosis_workflow_documents_no_tailwind_branch(self) -> None:
        text = (ROOT / "references" / "diagnosis-workflow.md").read_text(encoding="utf-8")
        self.assertIn("no-tailwind", text)
        self.assertIn("with-tailwind", text)
        self.assertIn("Do **not** run Preflight contrast experiments on a `no-tailwind` project.", text)
        self.assertIn("Global reset", text)
        self.assertIn("Teleport", text)

    def test_baseline_capture_runbook_exists_and_forbids_install(self) -> None:
        path = ROOT / "references" / "baseline-capture-runbook.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("**not** authorize `npm install`", text)
        self.assertIn("1440x900", text)
        self.assertIn("search-default", text)

    def test_strategy_options_gate_preflight_to_tailwind(self) -> None:
        text = (ROOT / "references" / "strategy-options.md").read_text(encoding="utf-8")
        self.assertIn("with-tailwind", text)
        self.assertIn("Do not select A ids when `tailwind.present=no`", text)


if __name__ == "__main__":
    unittest.main()

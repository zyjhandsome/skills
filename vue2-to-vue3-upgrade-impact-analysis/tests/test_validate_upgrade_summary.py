from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_upgrade_summary", ROOT / "scripts" / "validate_upgrade_summary.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidateUpgradeSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        raw = (ROOT / "fixtures" / "upgrade-summary.json").read_bytes()
        self.data = json.loads(raw)
        self.raw_size = len(raw)

    def test_valid_summary(self) -> None:
        self.assertEqual([], MODULE.validate(self.data, self.raw_size))

    def test_rejects_skill_dependency_field(self) -> None:
        self.data["required_skill"] = "other-skill"
        self.assertTrue(any("another Skill" in e for e in MODULE.validate(self.data, self.raw_size)))

    def test_rejects_context_bloat(self) -> None:
        self.assertTrue(any("exceeds" in e for e in MODULE.validate(self.data, MODULE.MAX_BYTES + 1)))

    def test_host_port_summary_ok(self) -> None:
        raw = (ROOT / "fixtures" / "upgrade-summary-host-port.json").read_bytes()
        data = json.loads(raw)
        self.assertEqual([], MODULE.validate(data, len(raw)))
        self.assertEqual(data["recommended_path"], "host-port-direct")
        self.assertEqual(data["axes"]["topology"], "host-port")

    def test_complete_requires_named_recipes(self) -> None:
        self.data["named_recipes"] = []
        self.data["named_validations"] = ["vite build"]
        errors = MODULE.validate(self.data, self.raw_size)
        self.assertTrue(any("named_recipes" in e for e in errors))

    def test_needs_choice_rejects_analysis_complete(self) -> None:
        self.data["analysis_status"] = "partial"
        self.data["decision_status"] = "needs_choice"
        self.data["batch_implementation_gate"] = "frozen"
        self.data["next_action"] = "analysis_complete"
        errors = MODULE.validate(self.data, self.raw_size)
        self.assertTrue(any("needs_choice" in e for e in errors))

    def test_ready_requires_lockfile_present(self) -> None:
        self.data["lockfile_status"] = "absent"
        errors = MODULE.validate(self.data, self.raw_size)
        self.assertTrue(any("lockfile_status" in e for e in errors))


if __name__ == "__main__":
    unittest.main()

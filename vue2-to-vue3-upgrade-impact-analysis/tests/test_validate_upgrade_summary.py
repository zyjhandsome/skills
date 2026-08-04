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


if __name__ == "__main__":
    unittest.main()

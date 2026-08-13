from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_visual_summary", ROOT / "scripts" / "validate_visual_summary.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidateVisualSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        raw = (ROOT / "fixtures" / "valid-summary.json").read_bytes()
        self.data = json.loads(raw)
        self.raw_size = len(raw)

    def test_valid_summary(self) -> None:
        self.assertEqual([], MODULE.validate(self.data, self.raw_size))

    def test_rejects_embedded_image(self) -> None:
        self.data["artifact_index"]["capture_manifest"] = "data:image/png;base64,abc"
        self.assertTrue(any("never embed" in e for e in MODULE.validate(self.data, self.raw_size)))

    def test_rejects_context_bloat(self) -> None:
        self.assertTrue(any("exceeds" in e for e in MODULE.validate(self.data, MODULE.MAX_BYTES + 1)))

    def test_cross_repo_summary_ok(self) -> None:
        raw = (ROOT / "fixtures" / "valid-summary-cross-repo.json").read_bytes()
        data = json.loads(raw)
        self.assertEqual([], MODULE.validate(data, len(raw)))

    def test_cross_repo_summary_requires_roots(self) -> None:
        raw = (ROOT / "fixtures" / "valid-summary-cross-repo.json").read_bytes()
        data = json.loads(raw)
        del data["baseline_root"]
        self.assertTrue(
            any("baseline_root" in e for e in MODULE.validate(data, len(raw))),
        )


if __name__ == "__main__":
    unittest.main()

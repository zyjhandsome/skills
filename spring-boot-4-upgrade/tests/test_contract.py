"""Synthetic evidence tests: these do not claim to have run Spring Boot."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_contract.py"
SPEC = importlib.util.spec_from_file_location("contract", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        artifact = self.root / "synthetic-test.xml"
        raw = b'<testsuite tests="2" failures="0" errors="0" skipped="0"/>'
        artifact.write_bytes(raw)
        check = {"status": "passed", "exit_code": 0, "snapshot": "fixture-snapshot",
                 "command": "synthetic fixture, not an executed Java command", "cwd": str(self.root),
                 "environment": "unit-test-only", "artifacts": [{"path": artifact.name,
                 "sha256": hashlib.sha256(raw).hexdigest()}]}
        stage = {"resolved_boot": "3.5.16", "snapshot": "fixture-snapshot",
                 "checks": {k: copy.deepcopy(check) for k in MODULE.BASE_CHECKS}}
        stage["checks"]["tests"].update(executed=2, failures=0, errors=0, skipped=0)
        final = copy.deepcopy(stage)
        final.update(resolved_boot="4.0.8", properties_migrator_present=False,
                     temporary_rewrite_present=False, bridges=[])
        self.data = {"schema_version": 1, "mode": "migrate", "source_boot": "3.4.0", "target_boot": "4.0.8",
                     "scope": {"included": ["synthetic fixture"], "excluded": [],
                               "required_checks": sorted(MODULE.BASE_CHECKS)},
                     "baseline35": stage, "final": final}

    def check(self, gate="boot4", snapshot="fixture-snapshot"):
        return MODULE.check_contract(self.data, self.root, gate, snapshot)

    def test_complete_stage_and_final(self):
        self.assertEqual(self.check(), [])
        self.assertEqual(self.check("verified"), [])

    def test_assess_never_passes_mutation_gate(self):
        self.data["mode"] = "assess"
        self.assertTrue(self.check())

    def test_missing_or_failed_35(self):
        for value in (None, {"resolved_boot": "3.4.0"}):
            with self.subTest(value=value):
                self.data["baseline35"] = value
                self.assertTrue(self.check())

    def test_unavailable_required_check(self):
        self.data["baseline35"]["checks"]["runtime"]["status"] = "unavailable"
        self.assertTrue(self.check())

    def test_old_code_snapshot(self):
        self.assertTrue(self.check(snapshot="edited-after-tests"))

    def test_evidence_file_removed_or_tampered(self):
        path = self.root / "synthetic-test.xml"
        path.write_text("different evidence")
        self.assertTrue(self.check())
        path.unlink()
        self.assertTrue(self.check())

    def test_no_tests_or_failure(self):
        for key, value in (("executed", 0), ("failures", 1), ("errors", 1), ("executed", True)):
            with self.subTest(key=key):
                tests = self.data["final"]["checks"]["tests"]
                previous = tests[key]
                tests[key] = value
                self.assertTrue(self.check("verified"))
                tests[key] = previous

    def test_unexplained_skips(self):
        self.data["final"]["checks"]["tests"]["skipped"] = 1
        self.assertTrue(self.check("verified"))

    def test_required_security_cannot_disappear(self):
        self.data["scope"]["required_checks"].append("security")
        self.assertTrue(self.check("verified"))

    def test_health_alone_is_not_verification(self):
        runtime = self.data["final"]["checks"]["runtime"]
        self.data["final"]["checks"] = {"runtime": runtime}
        self.assertTrue(self.check("verified"))

    def test_migrator_and_temporary_plugin(self):
        for key in ("properties_migrator_present", "temporary_rewrite_present"):
            with self.subTest(key=key):
                self.data["final"][key] = True
                self.assertTrue(self.check("verified"))
                self.data["final"][key] = False

    def test_bridges_change_verdict(self):
        self.data["final"]["bridges"] = [{"component": "jackson2", "reason": "blocked SDK", "exit_condition": "SDK migrated"}]
        self.assertTrue(self.check("verified"))
        self.assertEqual(self.check("verified-with-bridges"), [])

    def test_4x_patch_does_not_need_35_or_major_recipe(self):
        self.data["source_boot"] = "4.0.7"
        self.data["baseline35"] = None
        self.assertTrue(self.check())
        self.assertEqual(self.check("verified"), [])

    def test_reject_wrong_target_and_downgrade(self):
        for target in ("4.0.x", "4.0.8-SNAPSHOT", "3.5.16"):
            self.data["target_boot"] = target
            self.assertTrue(self.check("verified"))
        self.data.update(source_boot="4.1.1", target_boot="4.0.8")
        self.assertTrue(self.check("verified"))

    def test_reject_2x(self):
        self.data["source_boot"] = "2.7.18"
        self.assertTrue(self.check())

    def test_cli_is_read_only_and_has_nonzero_failure_exit(self):
        path = self.root / "contract.json"
        path.write_text(json.dumps(self.data), encoding="utf-8")
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = subprocess.run([sys.executable, str(SCRIPT), str(path), "--gate", "boot4", "--snapshot", "changed"], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["consistent"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_invalid_json_input(self):
        path = self.root / "invalid.json"
        path.write_text("{", encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), str(path), "--gate", "verified", "--snapshot", "fixture"], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["consistent"])


if __name__ == "__main__":
    unittest.main()

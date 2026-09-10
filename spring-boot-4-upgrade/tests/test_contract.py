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
        for label, entry in (("baseline35", stage), ("final", final)):
            tree = {"groupId": "example", "artifactId": "app", "version": "1.0", "children": [
                {"groupId": "org.springframework.boot", "artifactId": artifact, "version": entry["resolved_boot"],
                 "type": "jar", "scope": "compile"}
                for artifact in ("spring-boot", "spring-boot-autoconfigure", "spring-boot-starter-webmvc")]}
            entry["resolution"] = {"units": [{"id": "app@default", "module": "example:app", "format": "maven-json",
                "core_artifacts": {k: entry["resolved_boot"] for k in MODULE.CORE},
                "tree": self.save_tree(label, tree)}]}
        self.data = {"schema_version": 2, "mode": "migrate", "source_boot": "3.4.0", "target_boot": "4.0.8",
                     "scope": {"included": ["synthetic fixture"], "excluded": [],
                               "resolution_units": ["app@default"],
                               "required_checks": sorted(MODULE.BASE_CHECKS)},
                     "baseline35": stage, "final": final}

    def check(self, gate="boot4", snapshot="fixture-snapshot"):
        return MODULE.check_contract(self.data, self.root, gate, snapshot)

    def save_tree(self, label, tree):
        raw = json.dumps(tree).encode("utf-8")
        path = self.root / (label + "-tree.json")
        path.write_bytes(raw)
        return {"path": path.name, "sha256": hashlib.sha256(raw).hexdigest()}

    def mutate_final_tree(self, change):
        unit = self.data["final"]["resolution"]["units"][0]
        tree = json.loads((self.root / unit["tree"]["path"]).read_text())
        change(tree)
        unit["tree"] = self.save_tree("final", tree)

    def test_new_starter_does_not_prove_core_and_cannot_be_a_bridge(self):
        self.mutate_final_tree(lambda t: t["children"][0].update(version="3.5.14"))
        self.assertTrue(self.check("verified"))
        self.data["final"]["bridges"] = [{"component": "parent", "reason": "old owner", "exit_condition": "later"}]
        errors = self.check("verified-with-bridges")
        self.assertTrue(any("spring-boot:3.5.14" in e for e in errors), errors)

    def test_old_actuator_rejected_even_when_core_matches(self):
        self.mutate_final_tree(lambda t: t["children"].append({"groupId": "org.springframework.boot",
            "artifactId": "spring-boot-actuator", "version": "3.5.14", "scope": "runtime", "type": "jar"}))
        self.assertTrue(self.check("verified"))

    def test_only_bom_or_starter_is_insufficient(self):
        self.mutate_final_tree(lambda t: t.update(children=t["children"][2:]))
        self.assertTrue(self.check("verified"))

    def test_core_pom_is_not_core_jar(self):
        self.mutate_final_tree(lambda t: t["children"][0].update(type="pom"))
        self.assertTrue(self.check("verified"))

    def test_missing_raw_tree_or_wrong_module(self):
        unit = self.data["final"]["resolution"]["units"][0]
        unit["module"] = "example:another-app"
        self.assertTrue(self.check("verified"))
        unit.pop("tree")
        self.assertTrue(self.check("verified"))

    def test_missing_second_application(self):
        self.data["scope"]["resolution_units"].append("second-app@default")
        self.assertTrue(self.check("verified"))

    def test_gradle_selected_version_not_requested_or_constraint(self):
        unit = {"format": "gradle-text", "configuration": "runtimeClasspath"}
        text = "runtimeClasspath - Runtime\n+--- org.springframework.boot:spring-boot:3.5.14 -> 4.0.8\n+--- org.springframework.boot:spring-boot:3.5.14 (c)\n"
        self.assertEqual(MODULE.resolved_boot_nodes(text, unit), [("org.springframework.boot:spring-boot", "4.0.8", True)])
        with self.assertRaises(ValueError):
            MODULE.resolved_boot_nodes(text + "+--- example:lib:1 FAILED\n", unit)

    def test_gradle_bom_managed_dependency_without_requested_version(self):
        text = "runtimeClasspath - Runtime\n+--- org.springframework.boot:spring-boot -> 4.0.8\n(n) - Cannot be resolved legend\n"
        self.assertEqual(MODULE.resolved_boot_nodes(text, {"format": "gradle-text", "configuration": "runtimeClasspath"}),
                         [("org.springframework.boot:spring-boot", "4.0.8", True)])

    def test_v1_no_longer_passes(self):
        self.data["schema_version"] = 1
        self.assertTrue(self.check("verified"))

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

    def test_partial_startup_cannot_pass_either_verified_gate(self):
        runtime = self.data["final"]["checks"]["runtime"]
        runtime["environment"] = "synthetic: context initialized; baseline and target DB unreachable"
        for gate in ("verified", "verified-with-bridges"):
            self.data["final"]["bridges"] = [] if gate == "verified" else [
                {"component": "jackson2", "reason": "legacy serializer", "exit_condition": "migrate serializer"}]
            for status, exit_code in (("failed", 1), ("unavailable", 0), ("passed", 1)):
                with self.subTest(gate=gate, status=status, exit_code=exit_code):
                    runtime.update(status=status, exit_code=exit_code)
                    self.assertIn("runtime: required check did not pass", self.check(gate))

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

    def test_dependency_security_cannot_be_removed_from_scope(self):
        self.data["scope"]["required_checks"].remove("dependency_security")
        for gate in ("boot4", "verified", "verified-with-bridges"):
            with self.subTest(gate=gate):
                errors = self.check(gate)
                self.assertTrue(any("required_checks must include" in e and "dependency_security" in e
                                    for e in errors), errors)

    def test_dependency_security_missing_or_failed_rejected_at_each_stage(self):
        for gate in ("boot4", "verified", "verified-with-bridges"):
            self.data["final"]["bridges"] = [] if gate != "verified-with-bridges" else [
                {"component": "legacy-sdk", "reason": "temporary adapter", "exit_condition": "compatible SDK"}]
            checks = self.data["baseline35" if gate == "boot4" else "final"]["checks"]
            original = checks.pop("dependency_security")
            with self.subTest(gate=gate, status="missing"):
                self.assertIn("missing required check: dependency_security", self.check(gate))
            checks["dependency_security"] = copy.deepcopy(original)
            for status, exit_code in (("failed", 0), ("failed", 1), ("unavailable", 0), ("passed", 1)):
                with self.subTest(gate=gate, status=status, exit_code=exit_code):
                    checks["dependency_security"].update(status=status, exit_code=exit_code)
                    self.assertIn("dependency_security: required check did not pass", self.check(gate))
            checks["dependency_security"] = original
            self.assertEqual(self.check(gate), [])

    def test_dependency_security_evidence_must_exist_and_match(self):
        evidence = self.root / "synthetic-security-review.json"
        raw = b'{"fixture": true, "note": "synthetic evidence; no vulnerability scan executed"}'
        evidence.write_bytes(raw)
        record = self.data["final"]["checks"]["dependency_security"]
        record["artifacts"] = [{"path": evidence.name, "sha256": hashlib.sha256(raw).hexdigest()}]
        self.assertEqual(self.check("verified"), [])
        evidence.write_bytes(b"changed security evidence")
        self.assertTrue(self.check("verified"))
        evidence.unlink()
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

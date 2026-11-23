from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_preflight():
    path = ROOT / "scripts" / "preflight.py"
    spec = importlib.util.spec_from_file_location("preflight", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


preflight = load_preflight()


class PreflightUnitTests(unittest.TestCase):
    def test_detect_dual_build_needs_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            (root / "build.gradle").write_text("plugins {}", encoding="utf-8")
            tool, detected, needs = preflight.detect_build_tool(root, "auto")
            self.assertIsNone(tool)
            self.assertEqual(detected, ["maven", "gradle"])
            self.assertTrue(needs)

    def test_detect_single_maven(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            tool, detected, needs = preflight.detect_build_tool(root, "auto")
            self.assertEqual(tool, "maven")
            self.assertEqual(detected, ["maven"])
            self.assertFalse(needs)

    def test_network_ok_requires_under_400(self) -> None:
        with mock.patch.object(preflight.urllib.request, "urlopen") as urlopen:
            response = mock.MagicMock()
            response.status = 404
            response.__enter__.return_value = response
            response.__exit__.return_value = False
            urlopen.return_value = response
            result = preflight.network_probe("https://api.github.com/", 5)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], 404)

    def test_python_probe_prefers_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = str(root / "python.exe") if sys.platform == "win32" else str(root / "python")
            with mock.patch.object(preflight.shutil, "which", side_effect=lambda name: fake if name == "python" else None):
                with mock.patch.object(
                    preflight,
                    "run_probe",
                    return_value={
                        "command": [fake, "--version"],
                        "exit_code": 0,
                        "ok": True,
                        "stdout": "Python 3.12.0",
                        "stderr": "",
                    },
                ):
                    result = preflight.python_probe(root, 5, {})
            self.assertTrue(result["ok"])
            self.assertEqual(result["source"], "path")
            self.assertEqual(result["executable"], fake)

    def test_python_probe_falls_back_to_current_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(preflight.shutil, "which", return_value=None):
                result = preflight.python_probe(root, 5, {})
            self.assertTrue(result["ok"])
            self.assertEqual(result["source"], "current-interpreter")
            self.assertEqual(result["executable"], sys.executable)

    def test_settings_file_is_a_gradle_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.gradle.kts").write_text('include("app")', encoding="utf-8")
            tool, detected, needs = preflight.detect_build_tool(root, "auto")
            self.assertEqual(tool, "gradle")
            self.assertEqual(detected, ["gradle"])
            self.assertFalse(needs)

    def test_wrapper_is_found_in_a_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrapper = root / "mvnw.cmd"
            wrapper.write_text("@echo off\r\n", encoding="ascii")
            module = root / "service"
            module.mkdir()
            self.assertEqual(preflight.find_wrapper(module, "maven"), wrapper)

    def test_failing_system_maven_falls_back_to_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrapper = root / ("mvnw.cmd" if sys.platform == "win32" else "mvnw")
            wrapper.write_text("", encoding="ascii")
            calls: list[str] = []

            def fake_run(command, cwd, timeout, env):
                calls.append(command[0])
                ok = Path(command[0]).name.startswith("mvnw")
                return {
                    "command": command,
                    "exit_code": 0 if ok else 1,
                    "ok": ok,
                    "stdout": "ok" if ok else "",
                    "stderr": "" if ok else "bad stub",
                }

            with mock.patch.object(preflight.shutil, "which", return_value="C:/bad/mvn.cmd"):
                with mock.patch.object(preflight, "run_probe", side_effect=fake_run):
                    result = preflight.build_probe(root, "maven", 5, {})
            self.assertTrue(result["ok"])
            self.assertEqual(result["source"], "wrapper")
            self.assertEqual(len(calls), 2)

    def test_gradle_prefers_wrapper_when_both_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrapper = root / ("gradlew.bat" if sys.platform == "win32" else "gradlew")
            wrapper.write_text("", encoding="ascii")
            seen: list[str] = []

            def fake_run(command, cwd, timeout, env):
                seen.append(Path(command[0]).name)
                return {
                    "command": command,
                    "exit_code": 0,
                    "ok": True,
                    "stdout": "Gradle 8",
                    "stderr": "",
                }

            with mock.patch.object(preflight.shutil, "which", return_value="C:/gradle/bin/gradle"):
                with mock.patch.object(preflight, "run_probe", side_effect=fake_run):
                    result = preflight.build_probe(root, "gradle", 5, {})
            self.assertEqual(result["source"], "wrapper")
            self.assertTrue(seen[0].startswith("gradlew"))

    def test_timeout_kills_the_child_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if sys.platform == "win32":
                script = root / "slow.bat"
                script.write_text(
                    f'@echo off\r\n"{sys.executable}" -c "import time; time.sleep(30)"\r\n',
                    encoding="ascii",
                )
                command = [str(script)]
            else:
                command = [sys.executable, "-c", "import time; time.sleep(30)"]
            started = time.monotonic()
            result = preflight.run_probe(command, root, 2, {})
            self.assertLess(time.monotonic() - started, 8)
            self.assertFalse(result["ok"])
            self.assertIn("TimeoutExpired", result["stderr"])

    def test_parse_java_version_reads_major_vendor_and_ea(self) -> None:
        parsed = preflight.parse_java_version(
            'openjdk version "21-ea+35"\nOpenJDK Runtime Environment Temurin'
        )
        self.assertEqual(parsed["major"], 21)
        self.assertEqual(parsed["vendor"], "temurin")
        self.assertTrue(parsed["is_ea"])
        classic = preflight.parse_java_version('java version "1.8.0_392"')
        self.assertEqual(classic["major"], 8)
        self.assertFalse(classic["is_ea"])

    def test_discovered_jdk_prefers_the_declared_major(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<java.version>17</java.version>", encoding="utf-8")
            older = root / "jdk-11" / "bin" / "java"
            wanted = root / "jdk-17" / "bin" / "java"
            older.parent.mkdir(parents=True)
            wanted.parent.mkdir(parents=True)
            older.write_text("", encoding="ascii")
            wanted.write_text("", encoding="ascii")

            def fake_run(command, cwd, timeout, env):
                version = "17.0.1" if "jdk-17" in command[0] else "11.0.2"
                return {
                    "command": command,
                    "exit_code": 0,
                    "ok": True,
                    "stdout": "",
                    "stderr": f'openjdk version "{version}"',
                }

            with mock.patch.object(preflight, "run_probe", side_effect=fake_run):
                ranked = preflight.rank_java_candidates([older, wanted], 17, root, 5, {})
            self.assertEqual(ranked[0], wanted)

    def test_skip_network_does_not_open_a_socket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            with mock.patch.object(preflight.urllib.request, "urlopen") as urlopen:
                code = preflight.main([str(root), "--json", "--skip-network", "--build-tool", "maven"])
            urlopen.assert_not_called()
            self.assertIn(code, (0, 5))


class PreflightCliTests(unittest.TestCase):
    def test_dual_build_exits_6(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            (root / "build.gradle").write_text("plugins {}", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts" / "preflight.py"),
                    str(root),
                    "--json",
                    "--skip-network",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 6)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["needs_build_tool_selection"])
            self.assertFalse(payload["hard_gates_passed"])
            self.assertEqual(payload["network"][1]["url"], "https://api.github.com/")


if __name__ == "__main__":
    unittest.main()

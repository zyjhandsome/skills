from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
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


class PreflightCliTests(unittest.TestCase):
    def test_dual_build_exits_6(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            (root / "build.gradle").write_text("plugins {}", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "preflight.py"), str(root), "--json"],
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

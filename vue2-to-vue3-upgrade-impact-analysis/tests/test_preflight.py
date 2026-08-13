from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "scripts" / "preflight.py"


class PreflightTests(unittest.TestCase):
    def test_preflight_json_on_temp_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                json.dumps({"name": "demo", "dependencies": {"vue": "2.7.16"}}),
                encoding="utf-8",
            )
            (root / "package-lock.json").write_text("{}", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PREFLIGHT),
                    "--project-root",
                    str(root),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertIn(result.returncode, (0, 5), result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("hard_gates_ok", payload)
            self.assertIn("node", payload)
            self.assertIn("package_manager", payload)


if __name__ == "__main__":
    unittest.main()

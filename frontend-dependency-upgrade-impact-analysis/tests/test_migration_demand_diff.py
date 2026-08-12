from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_migration_demand_diff.py"


class MigrationDemandDiffTests(unittest.TestCase):
    def _write_pair(self, tmp_path: Path, a_deps: dict, b_deps: dict) -> tuple[Path, Path]:
        a = tmp_path / "A"
        b = tmp_path / "B"
        a.mkdir()
        b.mkdir()
        (a / "package.json").write_text(json.dumps({"dependencies": a_deps}), encoding="utf-8")
        (b / "package.json").write_text(json.dumps({"dependencies": b_deps}), encoding="utf-8")
        (b / "package-lock.json").write_text(
            json.dumps(
                {
                    "lockfileVersion": 3,
                    "packages": {
                        "": {"dependencies": {k: v.lstrip("^~") for k, v in b_deps.items()}},
                        **{
                            f"node_modules/{k}": {"version": v.lstrip("^~")}
                            for k, v in b_deps.items()
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        return a, b

    def test_diff_classifies_element_ui_and_reuses_shared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            a, b = self._write_pair(
                tmp_path,
                {
                    "vue": "2.6.10",
                    "element-ui": "2.13.2",
                    "axios": "0.18.1",
                    "left-pad": "1.3.0",
                },
                {"vue": "3.4.0", "axios": "1.6.0", "element-plus": "2.5.0"},
            )
            out = tmp_path / "out"
            closure = tmp_path / "closure.txt"
            closure.write_text("vue\nelement-ui\naxios\nleft-pad\n", encoding="utf-8")
            stack = tmp_path / "stack.json"
            stack.write_text(json.dumps({"element-ui": "element-plus"}), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--source-root",
                    str(a),
                    "--implementation-target",
                    str(b),
                    "--output-dir",
                    str(out),
                    "--closure-packages",
                    str(closure),
                    "--stack-map",
                    str(stack),
                ],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
            by_name = {
                row["package"]: row
                for row in json.loads((out / "demand-diff.json").read_text(encoding="utf-8"))[
                    "packages"
                ]
            }
            self.assertEqual(by_name["axios"]["disposition"], "reuse-B-major-review")
            self.assertEqual(by_name["element-ui"]["disposition"], "replace-as-B-stack")
            self.assertEqual(by_name["left-pad"]["disposition"], "add-to-B")
            self.assertEqual(by_name["vue"]["disposition"], "reuse-B")
            summary = json.loads((out / "dependency-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["analysis_mode"], "migration-demand-diff")
            self.assertEqual(summary["visual_strategy_hint"], "needs_choice")
            self.assertIn("element-ui", summary["ui_replace_packages"])
            self.assertIn("NEEDS_CHOICE", result.stderr)

    def test_host_ui_heuristic_prefers_element_plus_without_stack_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            a, b = self._write_pair(
                tmp_path,
                {"element-ui": "2.13.2", "vue": "2.6.10"},
                {"vue": "3.4.0", "element-plus": "2.5.0"},
            )
            out = tmp_path / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--source-root",
                    str(a),
                    "--implementation-target",
                    str(b),
                    "--output-dir",
                    str(out),
                ],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
            by_name = {
                row["package"]: row
                for row in json.loads((out / "demand-diff.json").read_text(encoding="utf-8"))[
                    "packages"
                ]
            }
            self.assertIn("element-plus", by_name["element-ui"]["note"])

    def test_decision_file_clears_queue_to_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            a, b = self._write_pair(
                tmp_path,
                {"left-pad": "1.3.0", "vue": "2.6.10"},
                {"vue": "3.4.0"},
            )
            out = tmp_path / "out"
            decisions = tmp_path / "decisions.json"
            decisions.write_text(
                json.dumps(
                    {"left-pad": "proceed:demand:left-pad:add-to-B"}
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--source-root",
                    str(a),
                    "--implementation-target",
                    str(b),
                    "--output-dir",
                    str(out),
                    "--decision-file",
                    str(decisions),
                ],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((out / "dependency-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["decision_status"], "decided")
            self.assertEqual(summary["batch_implementation_gate"], "ready")

    def test_blanket_natural_language_does_not_clear_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            a, b = self._write_pair(
                tmp_path,
                {"left-pad": "1.3.0", "vue": "2.6.10"},
                {"vue": "3.4.0"},
            )
            out = tmp_path / "out"
            decisions = tmp_path / "decisions.json"
            decisions.write_text(json.dumps({"left-pad": "全部放行"}), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--source-root",
                    str(a),
                    "--implementation-target",
                    str(b),
                    "--output-dir",
                    str(out),
                    "--decision-file",
                    str(decisions),
                ],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

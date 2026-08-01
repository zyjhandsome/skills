from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "scripts" / "profile_inventory.py"


class ProfileInventoryTests(unittest.TestCase):
    def _run_profile(self, root: Path) -> dict:
        result = subprocess.run(
            [
                sys.executable,
                str(PROFILE),
                "--project-root",
                str(root),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_profiles_vue2_element_cli_project(self) -> None:
        pkg = {
            "name": "admin-web",
            "dependencies": {
                "vue": "^2.7.16",
                "vue-router": "^3.6.5",
                "vuex": "^3.6.2",
                "element-ui": "^2.15.14",
                "tui-editor": "1.3.3",
            },
            "devDependencies": {
                "@vue/cli-service": "^5.0.8",
            },
            "scripts": {"serve": "vue-cli-service serve"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                json.dumps(pkg), encoding="utf-8"
            )
            data = self._run_profile(root)
            self.assertEqual(data["vue_major"], "2")
            self.assertIsInstance(data["vue_major"], str)
            self.assertEqual(data["builder"], "vue-cli")
            self.assertEqual(data["ui_stack"], "element-ui")
            self.assertEqual(data["store"], "vuex")
            self.assertEqual(
                data["related_packages"]["element-ui"]["readiness"], "replace"
            )
            self.assertEqual(
                data["related_packages"]["tui-editor"]["readiness"], "replace"
            )

    def test_source_signals_slot_scope_and_filter(self) -> None:
        pkg = {
            "name": "signal-web",
            "dependencies": {"vue": "2.6.10"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
            src = root / "src"
            src.mkdir()
            (src / "main.js").write_text(
                "import Vue from 'vue'\nVue.filter('x', v => v)\n",
                encoding="utf-8",
            )
            (src / "Table.vue").write_text(
                '<template><div><span slot-scope="row">{{ row }}</span>'
                '<div slot="footer">f</div></div></template>\n'
                "<script>\nexport default {\n  setup(props) { return {} }\n}\n"
                "</script>\n",
                encoding="utf-8",
            )
            (src / "Tinymce" / "index.vue").parent.mkdir(parents=True)
            (src / "Tinymce" / "index.vue").write_text(
                "<template><div /></template>\n"
                "<script>\nexport default {\n  mounted() {\n"
                "    const editor = {}; editor.setup(editor => {});\n"
                "    setup(editor) { return editor }\n"
                "  }\n}\n</script>\n",
                encoding="utf-8",
            )
            data = self._run_profile(root)
            signals = data["source_impact_signals"]["signals"]
            self.assertGreaterEqual(signals.get("slot_scope", 0), 1)
            self.assertGreaterEqual(signals.get("vue_filter_register", 0), 1)
            self.assertGreaterEqual(signals.get("slot_attr_legacy", 0), 1)
            self.assertGreaterEqual(signals.get("composition_setup", 0), 1)
            samples = data["source_impact_signals"]["samples"]
            self.assertNotIn("src/Tinymce/index.vue", samples.get("composition_setup", []))


if __name__ == "__main__":
    unittest.main()

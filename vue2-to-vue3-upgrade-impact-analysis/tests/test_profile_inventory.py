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
                "echarts": "4.2.1",
                "xlsx": "0.14.1",
                "normalize.css": "7.0.0",
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
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "ci.yml").write_text(
                "steps:\n  - uses: actions/setup-node@v4\n    with:\n      node-version: 18\n",
                encoding="utf-8",
            )
            (root / "Dockerfile").write_text("FROM node:18-alpine\n", encoding="utf-8")
            data = self._run_profile(root)
            self.assertEqual(data["vue_major"], "2")
            self.assertIsInstance(data["vue_major"], str)
            self.assertEqual(data["builder"], "vue-cli")
            self.assertEqual(data["ui_stack"], "element-ui")
            self.assertEqual(data["store"], "vuex")
            self.assertEqual(data["lockfile_status"], "absent")
            node_declarations = data["node_contract_evidence"]["config_declarations"]
            self.assertTrue(
                any(item["path"] == ".github/workflows/ci.yml" for item in node_declarations)
            )
            self.assertTrue(any(item["path"] == "Dockerfile" for item in node_declarations))
            self.assertIsNone(data["node_contract_evidence"]["known_green_baseline"])
            self.assertEqual(
                data["related_packages"]["element-ui"]["readiness"], "replace"
            )
            self.assertEqual(
                data["related_packages"]["tui-editor"]["readiness"], "replace"
            )
            self.assertEqual(
                data["related_packages"]["echarts"]["readiness"], "unknown"
            )
            self.assertEqual(
                data["related_packages"]["xlsx"]["readiness"], "unknown"
            )
            self.assertEqual(
                data["related_packages"]["normalize.css"]["readiness"], "unknown"
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

    def test_discovers_opaque_plugins_and_global_prototype_mounts(self) -> None:
        pkg = {
            "name": "legacy-plugin-web",
            "dependencies": {
                "vue": "2.6.14",
                "legacy-tree-grid-pro": "1.2.3",
                "acme-rich-editor": "4.5.6",
                "@corp/legacy-kit": "2.0.0",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
            src = root / "src"
            src.mkdir()
            (src / "main.js").write_text(
                "import VueAlias from 'vue'\n"
                "import LegacyKit from '@corp/legacy-kit'\n"
                "VueAlias.use(LegacyKit)\n"
                "VueAlias.prototype.$http = client\n",
                encoding="utf-8",
            )
            (src / "Feature.vue").write_text(
                "<script>export default { mounted() { this.$http('/health') } }</script>",
                encoding="utf-8",
            )
            data = self._run_profile(root)
            related = data["related_packages"]
            for name in (
                "legacy-tree-grid-pro",
                "acme-rich-editor",
                "@corp/legacy-kit",
            ):
                self.assertIn(name, related)
                self.assertEqual(related[name]["readiness"], "unknown")
            self.assertIn(
                "registered-via-Vue.use",
                related["@corp/legacy-kit"]["candidate_reasons"],
            )
            mounts = data["source_impact_signals"]["global_mounts"]
            self.assertEqual(mounts["$http"]["legacy_definition_samples"], ["src/main.js"])
            self.assertEqual(mounts["$http"]["consumer_samples"], ["src/Feature.vue"])
            self.assertFalse(mounts["$http"]["unresolved_consumer"])

    def test_detects_silent_vue3_break_signals_and_repo_anchor(self) -> None:
        pkg = {"name": "silent-web", "dependencies": {"vue": "2.7.16"}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
            (root / ".browserslistrc").write_text("> 1%\nnot ie 11\n", encoding="utf-8")
            git_refs = root / ".git" / "refs" / "heads"
            git_refs.mkdir(parents=True)
            (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (git_refs / "main").write_text("3f2a1b7c9d0e\n", encoding="utf-8")
            deployment = root / "deployment"
            deployment.mkdir()
            (deployment / "Dockerfile").write_text("FROM node:10.23.1\n", encoding="utf-8")
            src = root / "src"
            src.mkdir()
            (src / "FilterBox.vue").write_text(
                "<template>\n"
                '<div><el-input @keyup.enter.native="go" @keyup.13="go" />\n'
                '<li v-for="item in list" v-if="item.ok">{{ item }}</li>\n'
                "<transition name=\"fade\"><div /></transition></div>\n"
                "</template>\n"
                "<script>\n"
                "export default {\n"
                "  model: { prop: 'value', event: 'update:model' },\n"
                "}\n"
                "Vue.component('x-box', {})\n"
                "Vue.directive('focus', {})\n"
                "Vue.mixin({})\n"
                "const Lazy = resolve => require(['./Lazy.vue'], resolve)\n"
                "</script>\n",
                encoding="utf-8",
            )
            data = self._run_profile(root)
            signals = data["source_impact_signals"]["signals"]
            for key in (
                "native_modifier",
                "keycode_modifier",
                "model_option",
                "global_component_register",
                "global_directive_register",
                "global_mixin_register",
                "transition_component",
                "async_component_legacy",
                "v_for_with_v_if",
            ):
                self.assertGreaterEqual(signals.get(key, 0), 1, key)
            self.assertEqual(data["repo_revision"], "3f2a1b7c9d0e")
            self.assertEqual(data["browserslist"], ["> 1%", "not ie 11"])
            self.assertEqual(data["browserslist_source"], ".browserslistrc")
            node_paths = [
                item["path"]
                for item in data["node_contract_evidence"]["config_declarations"]
            ]
            self.assertIn("deployment/Dockerfile", node_paths)

    def test_marks_malformed_package_lock_unparsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                json.dumps({"name": "bad-lock", "dependencies": {"vue": "2.6.14"}}),
                encoding="utf-8",
            )
            (root / "package-lock.json").write_text("{broken", encoding="utf-8")
            data = self._run_profile(root)
            self.assertEqual(data["lockfile_status"], "unparsed")
            self.assertTrue(data["lockfile_errors"])
            digest = data["lockfile_digests"]["package-lock.json"]
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_profiles_multiple_source_roots_and_vant_ui(self) -> None:
        pkg = {
            "name": "multi-page-vue2",
            "dependencies": {
                "vue": "2.7.14",
                "element-ui": "2.15.14",
                "vant": "2.12.54",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
            desktop = root / "src"
            mobile = root / "src.mobile"
            desktop.mkdir()
            mobile.mkdir()
            (desktop / "main.js").write_text(
                "import Vue from 'vue'\nnew Vue({})\n", encoding="utf-8"
            )
            (mobile / "main.js").write_text(
                "import Vue from 'vue'\nimport Vant from 'vant'\n"
                "Vue.use(Vant)\nnew Vue({})\n",
                encoding="utf-8",
            )

            data = self._run_profile(root)

            self.assertEqual(data["source_roots"], ["src", "src.mobile"])
            self.assertEqual(data["source_impact_signals"]["scanned_files"], 2)
            self.assertEqual(data["source_impact_signals"]["signals"]["new_vue"], 2)
            self.assertIn("vant", data["related_packages"])
            self.assertEqual(data["related_packages"]["vant"]["readiness"], "needs-major")
            self.assertEqual(data["ui_stacks"], ["element-ui", "vant"])

    def test_explicit_output_writes_reproducible_inventory(self) -> None:
        pkg = {"name": "output-case", "dependencies": {"vue": "2.7.14"}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
            output = Path(tmp) / "evidence" / "inventory.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(PROFILE),
                    "--project-root",
                    str(root),
                    "--json",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["package_name"], "output-case")
            self.assertEqual(json.loads(result.stdout)["package_name"], "output-case")


if __name__ == "__main__":
    unittest.main()

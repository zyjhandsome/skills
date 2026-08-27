from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = SKILL_ROOT / "scripts" / "generate_migration_plan.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test User"], check=True)
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "fixture"], check=True, capture_output=True, text=True)


class HostedGeneratorContractTest(unittest.TestCase):
    def create_fixture(self, root: Path) -> tuple[Path, Path]:
        source = root / "hiapm"
        host = root / "apmweb3"

        write(
            source / "src/main/webapp/views/taskManage.jsp",
            """
<%@ page session="true" %>
<div ng-app="legacyTask" ng-controller="TaskController">
  <button id="queryBtn">Query</button>
</div>
<script>
$(function () {
  $("#queryBtn").click(function () {
    $.ajax({ url: "/api/tasks", method: "POST" });
  });
});
angular.module("legacyTask", []).controller("TaskController", function ($scope) {});
</script>
""",
        )
        write(
            source / "src/main/webapp/libs/angular-1.6.6/angular.js",
            "angular.module('vendor').controller('Noise', function ($scope) {});",
        )
        write(source / "src/main/webapp/views/projectProgress.jsp", "<div th:text=\"${name}\"></div>")

        write(
            host / "package.json",
            json.dumps(
                {
                    "scripts": {"build": "vite build", "lint": "eslint ."},
                    "dependencies": {
                        "vue": "^3.5.0",
                        "vue-router": "^4.5.0",
                        "pinia": "^3.0.0",
                        "axios": "^1.0.0",
                        "element-plus": "^2.0.0",
                    },
                    "devDependencies": {"vite": "^7.0.0"},
                    "engines": {"node": ">=20"},
                }
            ),
        )
        write(host / "package-lock.json", "{}")
        write(host / "src/views/taskManage.vue", "<template><TaskTable /></template>")
        write(host / "src/router/index.ts", "createRouter({ routes: [] }); router.beforeEach(authGuard);")
        write(host / "vite.config.ts", "export default { server: { proxy: { '/api': 'http://localhost' } } }")
        init_git_repo(source)
        init_git_repo(host)
        write(host / "node_modules/vue/noise.js", "module.exports = {};")
        return source, host

    def run_generator(self, output_dir: Path, source: Path, host: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                *extra,
                "--project-name",
                "hiapm-to-apmweb3",
                "--source-repo",
                str(source),
                "--host-repo",
                str(host),
                "--output-dir",
                str(output_dir),
                "--format",
                "all",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def read_csv(self, path: Path) -> list[list[str]]:
        with path.open(encoding="utf-8-sig", newline="") as csv_file:
            return list(csv.reader(csv_file))

    def test_assess_generates_dual_repo_evidence_and_excludes_vendor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, host = self.create_fixture(root)
            output_dir = root / "reports"
            self.run_generator(
                output_dir,
                source,
                host,
                "--source-acquisition-warning",
                "clone exited 128; existing repo reused",
            )

            markdown = (output_dir / "assess-evidence.md").read_text(encoding="utf-8")
            self.assertIn("Hosted AngularJS To Vue3 Migration Assess", markdown)
            self.assertIn("Host Stack", markdown)
            self.assertIn("Repo Acquisition", markdown)
            self.assertIn("Git Hygiene", markdown)
            self.assertIn("Completion Authority", markdown)
            self.assertIn("A/B Page Comparison", markdown)
            self.assertNotIn("Vue 3 工程骨架", markdown)

            acquisition = self.read_csv(output_dir / "csv" / "01-repo-acquisition.csv")
            acquisition_text = "\n".join(",".join(row) for row in acquisition)
            self.assertIn("clone-warning-existing-git-repo", acquisition_text)
            self.assertIn("clone exited 128", acquisition_text)

            hygiene = self.read_csv(output_dir / "csv" / "02-git-hygiene.csv")
            hygiene_text = "\n".join(",".join(row) for row in hygiene)
            self.assertIn("blocked-by-dependency-noise", hygiene_text)
            self.assertIn("src clean is not repo clean", hygiene_text)

            host_stack = self.read_csv(output_dir / "csv" / "03-host-stack.csv")
            self.assertIn(["build tool", "Vite", "package.json/config files"], host_stack)
            self.assertTrue(any(row[0] == "state" and "pinia" in row[1] for row in host_stack))
            self.assertTrue(any(row[0] == "ui library" and "element-plus" in row[1] for row in host_stack))

            comparison = self.read_csv(output_dir / "csv" / "06-page-comparison.csv")
            comparison_text = "\n".join(",".join(row) for row in comparison)
            self.assertIn("partial-overlap", comparison_text)
            self.assertIn("unmigrated", comparison_text)
            self.assertIn("taskmanage", comparison_text.lower())

            couplings = self.read_csv(output_dir / "csv" / "07-source-couplings.csv")
            coupling_text = "\n".join(",".join(row) for row in couplings)
            self.assertIn("angularjs", coupling_text)
            self.assertIn("jquery", coupling_text)
            self.assertNotIn("vendor", coupling_text)

    def test_design_mode_emits_scoped_flow_contract_only_for_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, host = self.create_fixture(root)
            output_dir = root / "reports"
            self.run_generator(output_dir, source, host, "design", "--unit", "taskManage")

            markdown = (output_dir / "design-evidence.md").read_text(encoding="utf-8")
            self.assertIn("unit: `taskManage`", markdown)
            self.assertIn("Scoped FLOW/CHAIN Contracts", markdown)
            self.assertIn("Business Flow", markdown)
            self.assertNotIn("FLOW-001", markdown)

            business_flow = self.read_csv(output_dir / "csv" / "10-business-flow-contract.csv")
            variable_chain = self.read_csv(output_dir / "csv" / "11-variable-chain-contract.csv")
            self.assertEqual([business_flow[0]], business_flow)
            self.assertEqual([variable_chain[0]], variable_chain)


if __name__ == "__main__":
    unittest.main()

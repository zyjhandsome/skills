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
        write(source / "src/main/webapp/lib/common.css", ".mg0{margin:0}.open{display:block}")
        write(source / "src/main/webapp/locale/zh.json", "{\"query\":\"查询\"}")
        write(source / "src/main/webapp/views/projectProgress.jsp", "<div th:text=\"${name}\"></div>")
        write(
            source / "src/main/resources/templates/thymeleaf/workBench/index.html",
            "<section ng-controller=\"WorkBenchController\"><script>$(function(){ initWorkBench(); })</script></section>",
        )
        write(
            source / "app/phone-list.template.html",
            """
<ul>
  <li ng-repeat="phone in $ctrl.phones">
    <a ng-href="#!/phones/{{phone.id}}">{{phone.name}}</a>
    <img ng-src="{{phone.imageUrl}}">
    <input ng-model="$ctrl.query">
  </li>
</ul>
""",
        )
        write(
            source / "app/phone-detail.template.html",
            """
<section>
  <h1>{{$ctrl.phone.name}}</h1>
  <p>{{$ctrl.phone.description}}</p>
</section>
""",
        )
        write(
            source / "app/app.config.js",
            """
angular.module('phonecatApp').config(function($routeProvider) {
  $routeProvider.when('/phones', {
    templateUrl: 'app/phone-list.template.html',
    controller: 'PhoneListController'
  }).when('/phones/:phoneId', {
    templateUrl: 'app/phone-detail.template.html',
    controller: 'PhoneDetailController'
  });
});
""",
        )
        write(
            source / "e2e-tests/phone-list.spec.js",
            "browser.get('/'); element(by.css('a')).click(); element(by.css('x')).click();",
        )
        write(
            source / "src/main/java/com/example/PageController.java",
            """
package com.example;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/hiapm")
public class PageController {
  @GetMapping("/workBench")
  public String workBench() {
    return "thymeleaf/workBench/index";
  }

  @RequestMapping("/taskManage")
  public String taskManage() {
    return "views/taskManage";
  }
}
""",
        )

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
                        "@opentiny/vue": "^3.0.0",
                        "jquery": "^3.7.0",
                    },
                    "devDependencies": {"vite": "^7.0.0"},
                    "volta": {"node": "16.20.2"},
                }
            ),
        )
        write(host / "package-lock.json", "{}")
        write(host / "index.html", "<div id=\"app\"></div>")
        write(host / "scripts/getpage.js", "export function getPages() { return ['workbench', 'taskManagement']; }")
        write(host / "src/pages/workbench/workbench.ts", "import './workbench.html';")
        write(host / "src/pages/workbench/workbench.html", "<div id=\"workbench\"></div>")
        write(host / "src/pages/taskManagement/taskManagement.ts", "import './taskManagement.html';")
        write(host / "src/pages/taskManagement/taskManagement.html", "<div id=\"task-management\"></div>")
        write(host / "src/views/PhoneList.vue", "<template><ul><li v-for=\"phone in phones\" :key=\"phone.id\">{{ phone.name }}</li></ul></template>")
        write(host / "src/components/TaskTable.vue", "<template><table /></template>")
        write(
            host / "openspec/changes/migrate-phone-detail-to-vue3-host/evidence/angularjs-hosted-vue3-migration/assess/assess-evidence.html",
            "<html><body>phone detail evidence report</body></html>",
        )
        write(
            host / "src/router/index.ts",
            """
import { createRouter } from 'vue-router';
import PhoneList from '../views/PhoneList.vue';

const router = createRouter({
  routes: [
    { path: '/phones', component: PhoneList },
  ],
});
router.beforeEach(authGuard);
""",
        )
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
            self.assertIn("AngularJS 迁入 Vue3 Host — 评估", markdown)
            self.assertIn("Host 栈", markdown)
            self.assertIn("仓库获取", markdown)
            self.assertIn("Git 卫生", markdown)
            self.assertIn("完成判定权", markdown)
            self.assertIn("A/B 页面对照", markdown)
            self.assertIn("状态枚举、路径、命令、URL、CSV 字段名保持英文原文", markdown)
            self.assertNotIn("Vue 3 工程骨架", markdown)
            html_text = (output_dir / "assess-evidence.html").read_text(encoding="utf-8")
            self.assertIn('lang="zh-CN"', html_text)

            acquisition = self.read_csv(output_dir / "csv" / "01-repo-acquisition.csv")
            acquisition_text = "\n".join(",".join(row) for row in acquisition)
            self.assertIn("clone-warning-existing-git-repo", acquisition_text)
            self.assertIn("clone exited 128", acquisition_text)

            hygiene = self.read_csv(output_dir / "csv" / "02-git-hygiene.csv")
            hygiene_text = "\n".join(",".join(row) for row in hygiene)
            self.assertIn("blocked-by-dependency-noise", hygiene_text)
            self.assertIn("src 干净不等于整仓干净", hygiene_text)

            host_stack = self.read_csv(output_dir / "csv" / "03-host-stack.csv")
            self.assertIn(["build tool", "Vite", "package.json/config files"], host_stack)
            self.assertTrue(any(row[0] == "state" and "pinia" in row[1] for row in host_stack))
            self.assertTrue(any(row[0] == "ui library" and "element-plus" in row[1] for row in host_stack))
            self.assertTrue(any(row[0] == "ui library" and "@opentiny/vue" in row[1] for row in host_stack))
            self.assertTrue(any(row[0] == "node" and "16.20.2" in row[1] for row in host_stack))
            self.assertTrue(any(row[0] == "mpa" and "scripts/getpage.js" in row[1] for row in host_stack))
            self.assertTrue(any(row[0] == "jquery" and "^3.7.0" in row[1] for row in host_stack))

            comparison = self.read_csv(output_dir / "csv" / "06-page-comparison.csv")
            comparison_text = "\n".join(",".join(row) for row in comparison)
            self.assertIn("partial-overlap", comparison_text)
            self.assertIn("unmigrated", comparison_text)
            self.assertIn("taskmanage", comparison_text.lower())
            self.assertIn("token-overlap", comparison_text)
            self.assertIn("人工校正映射", comparison_text)
            self.assertIn("host-component", comparison_text)
            self.assertIn("host-shell", comparison_text)
            self.assertIn("src/views/PhoneList.vue", comparison_text)
            self.assertNotIn("assess-evidence.html", comparison_text)

            url_mapping = self.read_csv(output_dir / "csv" / "07-url-entry-mapping.csv")
            url_mapping_text = "\n".join(",".join(row) for row in url_mapping)
            self.assertIn("/hiapm/workBench", url_mapping_text)
            self.assertIn("#!/phones", url_mapping_text)
            self.assertIn("app/phone-list.template.html", url_mapping_text)
            self.assertIn("Vue Router /phones", url_mapping_text)
            self.assertIn("src/views/PhoneList.vue", url_mapping_text)
            self.assertIn("src/pages/workbench/workbench.ts", url_mapping_text)
            self.assertIn("PageController.java", url_mapping_text)
            self.assertNotIn("assess-evidence.html", url_mapping_text)

            couplings = self.read_csv(output_dir / "csv" / "08-source-couplings.csv")
            coupling_text = "\n".join(",".join(row) for row in couplings)
            self.assertIn("angularjs", coupling_text)
            self.assertIn("jquery", coupling_text)
            self.assertNotIn("vendor", coupling_text)
            jquery_row = next(row for row in couplings if row[0] == "jquery")
            self.assertEqual("2", jquery_row[2])

            source_pages = self.read_csv(output_dir / "csv" / "04-source-pages.csv")
            source_pages_text = "\n".join(",".join(row) for row in source_pages)
            self.assertIn("app/phone-list.template.html", source_pages_text)
            self.assertIn("angularjs", source_pages_text)

            host_pages = self.read_csv(output_dir / "csv" / "05-host-pages.csv")
            host_pages_text = "\n".join(",".join(row) for row in host_pages)
            self.assertIn("host-shell", host_pages_text)
            self.assertNotIn("assess-evidence.html", host_pages_text)

            display_contract = self.read_csv(output_dir / "csv" / "15-display-contract.csv")
            display_contract_text = "\n".join(",".join(row) for row in display_contract)
            self.assertIn("DISP-", display_contract_text)
            self.assertIn("wired-unverified", display_contract_text)

            closure_resources = self.read_csv(output_dir / "csv" / "14-source-closure-resources.csv")
            closure_resources_text = "\n".join(",".join(row) for row in closure_resources)
            self.assertIn("src/main/webapp/lib/common.css", closure_resources_text)
            self.assertIn("src/main/webapp/locale/zh.json", closure_resources_text)

            recommended = self.read_csv(output_dir / "csv" / "09-recommended-units.csv")
            self.assertNotEqual("index", recommended[1][1])

    def test_design_mode_emits_scoped_flow_contract_only_for_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, host = self.create_fixture(root)
            output_dir = root / "reports"
            self.run_generator(output_dir, source, host, "design", "--unit", "taskManage")

            markdown = (output_dir / "design-evidence.md").read_text(encoding="utf-8")
            self.assertIn("单元：`taskManage`", markdown)
            self.assertIn("限定范围的 FLOW/CHAIN 合同", markdown)
            self.assertIn("设计就绪门禁", markdown)
            self.assertIn("业务流", markdown)
            self.assertIn("| FLOW-ID | 步骤 | 入口/触发 |", markdown)
            self.assertNotIn("FLOW-001", markdown)

            design_gate = self.read_csv(output_dir / "csv" / "11-design-ready-gate.csv")
            business_flow = self.read_csv(output_dir / "csv" / "12-business-flow-contract.csv")
            variable_chain = self.read_csv(output_dir / "csv" / "13-variable-chain-contract.csv")
            design_gate_text = "\n".join(",".join(row) for row in design_gate)
            self.assertIn("core flows", design_gate_text)
            self.assertIn("display-contract matrix", design_gate_text)
            self.assertIn("CSS closure", design_gate_text)
            self.assertIn("source contract gates", design_gate_text)
            self.assertIn("not-ready: empty-contract", design_gate_text)
            self.assertEqual([business_flow[0]], business_flow)
            self.assertEqual([variable_chain[0]], variable_chain)

    def test_source_only_assess_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _host = self.create_fixture(root)
            output_dir = root / "reports"

            subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--project-name",
                    "source-only",
                    "--source-repo",
                    str(source),
                    "--output-dir",
                    str(output_dir),
                    "--format",
                    "all",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            markdown = (output_dir / "assess-evidence.md").read_text(encoding="utf-8")
            self.assertIn("[not provided]", markdown)
            acquisition = self.read_csv(output_dir / "csv" / "01-repo-acquisition.csv")
            acquisition_text = "\n".join(",".join(row) for row in acquisition)
            self.assertIn("not-provided", acquisition_text)
            self.assertIn("source-only assess", acquisition_text)

    def test_verify_unmigrated_unit_outputs_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, host = self.create_fixture(root)
            output_dir = root / "reports"
            self.run_generator(output_dir, source, host, "verify", "--unit", "phone-detail")

            markdown = (output_dir / "verify-evidence.md").read_text(encoding="utf-8")
            self.assertIn("领域复核结论", markdown)
            self.assertIn("| fail | selected unit is unmigrated |", markdown)
            verify_result = self.read_csv(output_dir / "csv" / "16-verify-result.csv")
            self.assertIn(["fail", "selected unit is unmigrated"], verify_result)

    def test_design_requires_unit_and_accepts_read_only_repair_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, host = self.create_fixture(root)
            output_dir = root / "reports"

            missing_unit = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "design",
                    "--source-repo",
                    str(source),
                    "--host-repo",
                    str(host),
                    "--output-dir",
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, missing_unit.returncode)
            self.assertIn("design mode requires --unit", missing_unit.stderr)

            self.run_generator(output_dir, source, host, "design", "--unit", "PhoneList", "--profile", "repair")
            markdown = (output_dir / "design-evidence.md").read_text(encoding="utf-8")
            self.assertIn("Profile：`repair`", markdown)
            self.assertIn("只读合同/切片计划", markdown)


if __name__ == "__main__":
    unittest.main()

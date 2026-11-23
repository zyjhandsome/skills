from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_migration_plan", SKILL_ROOT / "scripts" / "generate_migration_plan.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gen = load_generator()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def method_text() -> str:
    """Hosted method as one string, whether it is one file or split by topic (Task 16)."""
    return "\n".join(
        p.read_text(encoding="utf-8") for p in sorted((SKILL_ROOT / "references").glob("hosted-*.md"))
    )


PARTIAL = [{
    "status": "partial-overlap", "source_key": "taskmanage", "source_path": "views/taskManage.jsp",
    "source_url": "/views/taskManage", "host_path": "src/views/TaskManage.vue", "host_entry": "/src/views/TaskManage",
}]
MD_HEADER = (
    "| DISP-ID | 迁移单元 | 源区域 | API + 字段/公式 | B 现状 | row_lifecycle |\n"
    "|---|---|---|---|---|---|\n"
)


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class VerifyLedgerTest(TempDirCase):
    def verify_md(self, body: str):
        write(self.tmp / "m.md", MD_HEADER + body)
        return gen.verify_one_unit("taskManage", PARTIAL, gen.load_persisted_matrix(str(self.tmp / "m.md")))

    def test_unescaped_pipe_row_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            self.verify_md(
                "| DISP-taskmanage-a-1 | taskManage | a | total | verified | active |\n"
                "| DISP-taskmanage-b-1 | taskManage | b | val || 0 | missing | active |\n"
            )
        self.assertIn("matrix-row-column-mismatch", str(ctx.exception))
        self.assertIn("m.md:4", str(ctx.exception))

    def test_stale_row_blocks_verify(self):
        result = self.verify_md(
            "| DISP-taskmanage-a-1 | taskManage | a | total | verified | active |\n"
            "| DISP-taskmanage-b-1 | taskManage | b | sum | mismatched | stale |\n"
        )
        self.assertEqual("fail", result["status"])
        self.assertIn("stale matrix rows must be refreshed: DISP-taskmanage-b-1", result["reason"])

    def test_zero_verified_rows_do_not_pass(self):
        result = self.verify_md("| DISP-taskmanage-a-1 | taskManage | a | total | approved-deviation | active |\n")
        self.assertEqual("fail", result["status"])
        self.assertIn("no verified or manual-verified row", result["reason"])

    def test_retired_rows_stay_excluded(self):
        result = self.verify_md(
            "| DISP-taskmanage-a-1 | taskManage | a | total | verified | active |\n"
            "| DISP-taskmanage-b-1 | taskManage | b | sum | mismatched | retired |\n"
        )
        self.assertEqual("pass", result["status"])

    def test_unknown_lifecycle_value_fails(self):
        result = self.verify_md("| DISP-taskmanage-a-1 | taskManage | a | total | verified | archived |\n")
        self.assertEqual("fail", result["status"])
        self.assertIn("matrix-row-lifecycle-invalid", result["reason"])

    def test_csv_ledger_with_bom_and_padded_headers_is_read(self):
        (self.tmp / "m.csv").write_bytes(
            "\ufeffDISP-ID , 迁移单元 ,B 现状\nDISP-taskmanage-a-1,taskManage,verified\n".encode("utf-8")
        )
        result = gen.verify_one_unit("taskManage", PARTIAL, gen.load_persisted_matrix(str(self.tmp / "m.csv")))
        self.assertEqual("pass", result["status"])


class LedgerHeaderTest(TempDirCase):
    def test_method_doc_header_equals_script_header(self):
        line = next(l for l in method_text().splitlines() if l.startswith("| DISP-ID |"))
        self.assertEqual(gen.DISPLAY_CONTRACT_HEADERS, gen.split_markdown_table_row(line))
        self.assertEqual(12, len(gen.DISPLAY_CONTRACT_HEADERS))

    def test_skeleton_rows_carry_active_lifecycle(self):
        rows = gen.display_contract_rows(PARTIAL, ["taskManage"])
        self.assertEqual(["active"], [row["row_lifecycle"] for row in rows])
        self.assertEqual("wired-unverified", rows[0]["B 现状"])

    def test_selected_unmigrated_unit_gets_missing_skeleton(self):
        unmigrated = [dict(PARTIAL[0], status="unmigrated", host_path="", host_entry="")]
        rows = gen.display_contract_rows(unmigrated, ["taskManage"])
        self.assertEqual(1, len(rows))
        self.assertIn("(skeleton)", rows[0]["DISP-ID"])
        self.assertEqual("missing", rows[0]["B 现状"])
        self.assertEqual([], gen.display_contract_rows(unmigrated, None))

    def test_legacy_ledger_without_row_lifecycle_reads_as_active(self):
        write(self.tmp / "m.csv", "DISP-ID,迁移单元,B 现状\nDISP-taskmanage-a-1,taskManage,verified\n")
        result = gen.verify_one_unit("taskManage", PARTIAL, gen.load_persisted_matrix(str(self.tmp / "m.csv")))
        self.assertEqual("pass", result["status"])


class DiscoveryExclusionTest(TempDirCase):
    def discovered(self, root: Path, files: list[str]) -> set[str]:
        for rel in files:
            write(root / rel, "<div ng-controller='X'></div>")
        return {row["path"] for row in gen.discover_pages(root, gen.SOURCE_PAGE_EXTS, True)}

    def test_business_report_and_doc_templates_are_discovered(self):
        business = [
            "src/main/webapp/views/report/taskReport.jsp",
            "app/views/report/report-list.html",
            "app/login/verification-code.html",
            "app/evidenceUpload/evidence-upload.html",
            "src/main/webapp/views/doc/docList.jsp",
            "report/src/main/webapp/list.jsp",
        ]
        self.assertEqual(set(business), self.discovered(self.tmp / "src", business))

    def test_root_artifacts_and_package_dirs_are_excluded(self):
        noise = [
            "reports/migration/assess-evidence.html",
            "openspec/changes/a/evidence/b/assess-evidence.html",
            "docs/guide.html",
            "bower_components/angular/index.html",
            "web/out/design-evidence.html",
        ]
        self.assertEqual(set(), self.discovered(self.tmp / "src", noise))

    def test_repo_root_named_report_is_not_excluded(self):
        found = self.discovered(self.tmp / "report" / "web", ["views/list.jsp"])
        self.assertEqual({"views/list.jsp"}, found)


class JavaRouteTest(TempDirCase):
    def routes(self, java: str) -> dict[str, str]:
        write(self.tmp / "src/main/java/C.java", java)
        return {row["source_url"]: row["source_template"] for row in gen.extract_java_routes(self.tmp)}

    def test_methods_without_class_mapping_keep_their_own_routes(self):
        routes = self.routes('''
@Controller
public class TaskController {
  @RequestMapping("/task/list.do")
  public String list() { return "views/taskList"; }
  @RequestMapping("/task/detail.do")
  public String detail() { return "views/taskDetail"; }
  @RequestMapping(value = {"/task/a.do", "/task/b.do"})
  public String multi() { return "views/taskMulti"; }
  @RequestMapping(method = RequestMethod.GET, path = "/task/c.do")
  public String named() { return "views/taskNamed"; }
}''')
        self.assertEqual(
            {"/task/list.do", "/task/detail.do", "/task/a.do", "/task/b.do", "/task/c.do"}, set(routes)
        )
        self.assertEqual("views/taskList", routes["/task/list.do"])
        self.assertEqual("views/taskMulti", routes["/task/b.do"])

    def test_class_mapping_prefixes_method_routes(self):
        routes = self.routes('''
@Controller
@RequestMapping("/hiapm")
public class PageController {
  @GetMapping("/workBench")
  public String workBench() { return "thymeleaf/workBench/index"; }
}''')
        self.assertEqual({"/hiapm/workBench": "thymeleaf/workBench/index"}, routes)

    def test_redirect_is_not_a_template_and_model_and_view_is(self):
        routes = self.routes('''
public class HomeController {
  @GetMapping("/home")
  public String home() { if (x) return "redirect:/login"; return "views/home"; }
  @GetMapping("/mv")
  public ModelAndView mv() { return new ModelAndView("views/mv"); }
}''')
        self.assertEqual({"/home": "views/home", "/mv": "views/mv"}, routes)

    def test_multiline_mapping_annotation(self):
        routes = self.routes('''
public class X {
  @RequestMapping(
      value = "/multi/line.do",
      method = RequestMethod.POST)
  public String m() { return "views/m"; }
}''')
        self.assertEqual({"/multi/line.do": "views/m"}, routes)


class EntryEvidenceTest(TempDirCase):
    def gate(self, source_files: dict[str, str], host_files: dict[str, str]) -> dict[str, dict[str, str]]:
        src, host = self.tmp / "a", self.tmp / "b"
        for rel, text in source_files.items():
            write(src / rel, text)
        for rel, text in host_files.items():
            write(host / rel, text)
        source_pages = gen.discover_pages(src, gen.SOURCE_PAGE_EXTS, True)
        host_pages = gen.discover_pages(host, gen.HOST_PAGE_EXTS, False)
        comparison = gen.compare_pages(source_pages, host_pages)
        mapping = gen.build_url_entry_mapping(src, host, source_pages, host_pages)
        gen.reconcile_comparison_entries(comparison, mapping)
        return {row["source_path"]: row for row in gen.repair_scope_gate(comparison)}

    def test_unrelated_mpa_entry_is_not_route_evidence(self):
        rows = self.gate(
            {"views/taskManage.jsp": "<div ng-controller='T'></div>"},
            {
                "src/views/TaskManage.vue": "<template><div/></template>",
                "src/pages/taskCenter/taskCenter.ts": "import './taskCenter.html'",
                "src/pages/taskCenter/taskCenter.html": "<div id='app'></div>",
            },
        )
        row = rows["views/taskManage.jsp"]
        self.assertEqual("filename guess only", row["host_entry_evidence"])
        self.assertEqual("new-landing", row["design_scope"])

    def test_entry_in_the_matched_mpa_page_dir_keeps_repair(self):
        rows = self.gate(
            {"views/workBench.jsp": "<div ng-controller='W'></div>"},
            {
                "src/pages/workbench/workbench.ts": "import './workbench.html'",
                "src/pages/workbench/workbench.html": "<div id='app'></div>",
            },
        )
        row = rows["views/workBench.jsp"]
        self.assertEqual("route/menu/MPA evidence", row["host_entry_evidence"])
        self.assertEqual("repair", row["design_scope"])

    def test_equal_route_path_keeps_repair(self):
        rows = self.gate(
            {
                "app/phone-list.template.html": "<ul><li ng-repeat='p in $ctrl.phones'></li></ul>",
                "app/app.config.js": "$routeProvider.when('/phones', { templateUrl: 'app/phone-list.template.html' });",
            },
            {
                "src/views/PhoneList.vue": "<template><ul/></template>",
                "src/router/index.ts": (
                    "import { createRouter } from 'vue-router';\n"
                    "import PhoneList from '../views/PhoneList.vue';\n"
                    "export default createRouter({ routes: [{ path: '/phones', component: PhoneList }] });\n"
                ),
            },
        )
        self.assertEqual("repair", rows["app/phone-list.template.html"]["design_scope"])


CLOSED = [{"DISP-ID": "DISP-taskmanage-a-1", "迁移单元": "taskManage", "B 现状": "verified"}]


def comparison_row(status: str, source_path: str = "", host_path: str = "") -> dict[str, str]:
    key = Path(source_path or host_path).stem.lower()
    return {"status": status, "source_key": key, "source_path": source_path,
            "source_url": "", "host_path": host_path, "host_entry": ""}


class UnitResolutionTest(unittest.TestCase):
    def test_exact_stem_wins_over_longer_sibling(self):
        comparison = [
            comparison_row("partial-overlap", "views/taskManage.jsp", "src/views/TaskManage.vue"),
            comparison_row("unmigrated", "views/taskManageDetail.jsp"),
            comparison_row("host-component", host_path="src/components/TaskManageTable.vue"),
        ]
        self.assertEqual(["views/taskManage.jsp"],
                         [r["source_path"] for r in gen.resolve_unit_rows("taskManage", comparison)])
        self.assertEqual("pass", gen.verify_one_unit("taskManage", comparison, CLOSED)["status"])

    def test_index_page_resolves_by_parent_directory(self):
        comparison = [comparison_row("partial-overlap", "templates/workBench/index.html", "src/pages/workbench/workbench.html")]
        comparison[0]["source_key"] = "workbench"
        self.assertEqual(1, len(gen.resolve_unit_rows("workBench", comparison)))

    def test_ambiguous_unit_fails_and_names_candidates(self):
        comparison = [
            comparison_row("partial-overlap", "views/taskManage.jsp", "src/views/TaskManage.vue"),
            comparison_row("partial-overlap", "views/taskReport.jsp", "src/views/TaskReport.vue"),
        ]
        result = gen.verify_one_unit("task", comparison, CLOSED)
        self.assertEqual("fail", result["status"])
        self.assertIn("matches 2 source pages", result["reason"])
        self.assertIn("views/taskReport.jsp", result["reason"])

    def test_parse_units_accepts_fullwidth_comma(self):
        self.assertEqual(["taskManage", "workBench"], gen.parse_units(["taskManage，workBench"]))


class EncodingTest(TempDirCase):
    def test_bom_package_json_is_parsed(self):
        (self.tmp / "package.json").write_bytes(b"\xef\xbb\xbf" + b'{"dependencies": {"vue": "^3.4.0"}}')
        self.assertEqual({"vue": "^3.4.0"}, gen.load_package_json(self.tmp)["dependencies"])

    def test_gbk_template_keeps_chinese_copy(self):
        (self.tmp / "a.jsp").write_bytes('<button title="查询">任务管理</button>'.encode("gbk"))
        self.assertEqual('<button title="查询">任务管理</button>', gen.read_text(self.tmp / "a.jsp"))

    def test_undecodable_bytes_do_not_raise(self):
        (self.tmp / "b.jsp").write_bytes(b"<a ng-click='x()'>\xff\xfe\x00</a>")
        self.assertIn("ng-click", gen.read_text(self.tmp / "b.jsp"))

    def test_tsconfig_with_comments_and_app_config_reports_strict(self):
        write(self.tmp / "tsconfig.json", '{\n  // root\n  "files": [],\n  "references": [{ "path": "./tsconfig.app.json" },],\n}')
        write(self.tmp / "tsconfig.app.json", '{ "compilerOptions": { "strict": true /* on */ } }')
        self.assertEqual("strict=True; noImplicitAny=not set", gen.detect_ts_strict(self.tmp))


class NeutralWordingTest(unittest.TestCase):
    def test_no_pipeline_private_terms(self):
        texts = {
            "SKILL.md": (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8"),
            "hosted method": method_text(),
            "generator": (SKILL_ROOT / "scripts/generate_migration_plan.py").read_text(encoding="utf-8"),
        }
        for name, text in texts.items():
            for term in ["T16", "Delivery Frame", "Delivery framing", "DOMAIN_ROOT", "producing wave",
                         "Frame and Plan", "High migration work", "High cost/risk"]:
                self.assertNotIn(term, text, f"{name}: {term}")

    def test_completion_semantics_are_kept(self):
        method = method_text()
        self.assertIn("implementation authority record", method)
        self.assertIn("necessary but not sufficient", method)
        self.assertIn("two approval records", method)


class SkillDedupeTest(unittest.TestCase):
    def setUp(self):
        self.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.method = method_text()

    def test_duplicated_sections_are_gone(self):
        self.assertNotIn("## Host Compile And Diagnostic Overlay", self.skill)
        self.assertNotIn("`dest-built-unwired`, `wired-hidden`, `develop-native`, `orphan-mpa`, `deprecated-removed`", self.skill)
        self.assertNotIn("A renamed header is a `matrix-header-mismatch` ledger/tooling repair", self.skill)

    def test_removed_rules_still_exist_in_the_method(self):
        for phrase in ["matrix-header-mismatch", "font-size: 0", "lintOnSave", "noImplicitAny",
                       "matrix-not-written-back", "manual-only", "(skeleton)"]:
            self.assertIn(phrase, self.method)

    def test_red_flags_and_hard_stops_remain(self):
        self.assertIn("## Red Flags", self.skill)
        self.assertIn("## Hosted Migration Rules", self.skill)
        self.assertIn("matrix-not-written-back", self.skill)


class ScanCommandLintTest(unittest.TestCase):
    FILES = [
        "SKILL.md",
        "references/jquery-vue3-business-logic-analysis.md",
        "references/angularjs-vue3-migration-method.md",
    ]

    def test_rg_commands_are_single_quoted_and_use_recursive_excludes(self):
        for rel in self.FILES:
            for line in (SKILL_ROOT / rel).read_text(encoding="utf-8").splitlines():
                if not line.startswith("rg "):
                    continue
                self.assertNotIn('"', line, f"{rel}: {line}")
                self.assertTrue("<EXCL>" in line or "-g '!**/" in line, f"{rel}: {line}")
                if "-g '*." in line:
                    self.assertLess(line.index("-g '*."), line.index("<EXCL>"), f"{rel}: {line}")

    def test_skill_defines_excl_once_with_recursive_dirs(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(1, text.count("EXCL = "))
        self.assertIn("-g '!**/{node_modules,bower_components,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales,test,tests,e2e-tests}/**'", text)
        self.assertIn('python -B "<skill-dir>/scripts/generate_migration_plan.py" verify', text)


class ConstructMappingTest(unittest.TestCase):
    def test_mapping_file_exists_and_is_routed(self):
        mapping = (SKILL_ROOT / "references/angularjs-construct-mapping.md").read_text(encoding="utf-8")
        for token in ["transclude", "require:", "$compile", "ngModelController", "defineModel", "3.4"]:
            self.assertIn(token, mapping)
        self.assertIn("references/angularjs-construct-mapping.md", (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8"))

    def test_no_author_machine_paths_or_conflicting_override(self):
        for path in (SKILL_ROOT / "references").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("D:\\projects", text, path.name)
        greenfield = (SKILL_ROOT / "references/angularjs-vue3-migration-method.md").read_text(encoding="utf-8")
        self.assertNotIn("## Hosted Migration Override", greenfield)
        self.assertNotIn("...props.user", greenfield)


class GateAlignmentTest(unittest.TestCase):
    def test_script_gates_cover_the_method(self):
        gates = {row[0] for row in gen.GATE_ROWS}
        self.assertTrue({"page-init", "display-contract", "entry-wiring", "archive gate"} <= gates)
        ready = {row[0] for row in gen.DESIGN_READY_ROWS}
        self.assertTrue({"field formulas", "host chrome ledger"} <= ready)

    def test_method_lists_chrome_ledger_and_script_enums(self):
        method = method_text()
        gate = method.split("## Design-Ready Gate")[1].split("\n## ")[0]
        self.assertIn("host chrome ledger", gate)
        for token in ["host-page-only-candidate", "path-exists-not-git", "not-provided"]:
            self.assertIn(token, method)
        self.assertIn("Content-Type", method)
        self.assertIn("CSRF", method)

    def test_cardinality_wording_matches_the_method(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("means a wrong source", skill)
        self.assertNotIn("treat a cardinality gap as a wrong source", skill)

    def test_design_markdown_tables_use_chinese_headers(self):
        self.assertEqual("对照状态", dict(gen.UNIT_DECISION_LABELS)["comparison_status"])
        self.assertEqual("身份上下文", dict(gen.COMPARISON_SURFACE_LABELS)["identity_context"])


if __name__ == "__main__":
    unittest.main()

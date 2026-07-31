from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillStructureTests(unittest.TestCase):
    def test_skill_frontmatter_and_size(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        self.assertIn("name: java-dependency-upgrade-impact-analysis", content)
        self.assertIn("Analyze, never implement", content)
        self.assertLess(len(content.splitlines()), 200)
        self.assertNotIn("delivery-explore", content)
        self.assertNotIn("delivery-frame-spec", content)
        # Stage A may name recipes; it must never instruct running them.
        self.assertIn("Name, never run, migration recipes", content)
        self.assertNotIn("fortify", content.lower())

    def test_migration_recipes_named_not_executed(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        patterns = (ROOT / "references" / "common-upgrade-patterns.md").read_text(
            encoding="utf-8"
        )
        impact = (ROOT / "references" / "impact-and-validation.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("OpenRewrite", patterns)
        self.assertIn("OpenRewrite", impact)
        self.assertIn("verified catalog/source URL", patterns)
        self.assertIn("never runs it", impact)
        self.assertIn("Name, never run, migration recipes", skill)

    def test_referenced_markdown_files_exist(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        refs = set(re.findall(r"`references/([^`]+\.md)`", content))
        templates = set(re.findall(r"`templates/([^`]+\.md)`", content))
        self.assertTrue(refs)
        self.assertTrue(templates)
        for relative in refs:
            self.assertTrue((ROOT / "references" / relative).is_file(), relative)
        for relative in templates:
            self.assertTrue((ROOT / "templates" / relative).is_file(), relative)

    def test_required_reference_topics_present(self) -> None:
        required = {
            "owner-and-resolution.md",
            "dual-entry-and-batching.md",
            "reachability-and-upstream.md",
            "impact-and-validation.md",
            "human-confirmation-gates.md",
            "report-contract.md",
            "decision-record-schema.md",
            "common-gav-repos.md",
            "common-upgrade-patterns.md",
            "treatment-ladder.md",
            "environment-preflight.md",
            "next-action-choice-menus.md",
        }
        for name in required:
            text = (ROOT / "references" / name).read_text(encoding="utf-8")
            self.assertGreater(len(text), 200, name)

    def test_report_contract_enums(self) -> None:
        text = (ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        for token in (
            "analysis_status",
            "decision_status",
            "batch_implementation_gate",
            "needs_choice",
            "java-dependency-upgrade-report.md",
            "确认队列",
            "当前解析版本",
            "evidence/java-dependency-upgrade",
            "report_path",
        ):
            self.assertIn(token, text)

    def test_templates_default_to_chinese_headers(self) -> None:
        packet = (ROOT / "templates" / "decision-packet.md").read_text(encoding="utf-8")
        record = (ROOT / "templates" / "decision-record.md").read_text(encoding="utf-8")
        self.assertIn("依赖清单与解析路径", packet)
        self.assertIn("当前解析版本", packet)
        self.assertIn("确认队列", packet)
        self.assertIn("环境前置", packet)
        self.assertIn("主机 JDK", packet)
        self.assertIn("决策记录", record)
        self.assertIn("有效 Owner", record)
        self.assertNotIn("| Component | Module |", packet)
        self.assertNotIn("| Field | Value |", record)

    def test_owner_first_and_effective_resolution(self) -> None:
        owner = (ROOT / "references" / "owner-and-resolution.md").read_text(encoding="utf-8")
        self.assertIn("Owner-first", owner)
        self.assertIn("dependency:tree", owner)
        self.assertIn("dependencyInsight", owner)

    def test_confirmation_protocol(self) -> None:
        gates = (ROOT / "references" / "human-confirmation-gates.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("proceed:", gates)
        self.assertIn("ready", gates)
        self.assertIn("blocked", gates)
        self.assertIn("继续/放行", gates)
        self.assertIn("Decision unit", gates)
        self.assertIn("全部 proceed", gates)
        self.assertIn("remove", gates)
        self.assertIn("exclude", gates)
        self.assertIn("decided", gates)
        self.assertIn("Status transition", gates)

    def test_treatment_ladder_documented(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        ladder = (ROOT / "references" / "treatment-ladder.md").read_text(
            encoding="utf-8"
        )
        packet = (ROOT / "templates" / "decision-packet.md").read_text(encoding="utf-8")
        batching = (ROOT / "references" / "dual-entry-and-batching.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("treatment-ladder.md", skill)
        self.assertIn("recommended_treatment", ladder)
        self.assertIn("no-viable-path", ladder)
        self.assertIn("GA-only", ladder)
        self.assertIn("建议处置", packet)
        self.assertNotIn("| `defer` | 暂无可行处置", ladder)
        self.assertIn("build_variant × bounded batch_scope", ladder)
        self.assertIn("Same GAV, different GA version", batching)
        self.assertIn("Different coordinates", batching)

    def test_openai_metadata(self) -> None:
        content = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$java-dependency-upgrade-impact-analysis", content)
        match = re.search(r'short_description:\s+"([^"]+)"', content)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertGreaterEqual(len(match.group(1)), 25)
        self.assertLessEqual(len(match.group(1)), 64)
        self.assertIn("Always load SKILL.md first", content)
        self.assertNotIn("ask every ready proceed/defer", content.lower())

    def test_no_auxiliary_readme(self) -> None:
        self.assertFalse((ROOT / "README.md").exists())

    def test_common_upgrade_patterns(self) -> None:
        text = (ROOT / "references" / "common-upgrade-patterns.md").read_text(
            encoding="utf-8"
        )
        for needle in (
            "downgrade",
            "Netty",
            "commons-lang",
            "jackson",
            "Family expansion",
            "Pending baseline",
            "next-action-choice-menus.md",
        ):
            self.assertIn(needle, text)

    def test_next_action_choice_menus(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        menus = (ROOT / "references" / "next-action-choice-menus.md").read_text(
            encoding="utf-8"
        )
        gates = (ROOT / "references" / "human-confirmation-gates.md").read_text(
            encoding="utf-8"
        )
        ladder = (ROOT / "references" / "treatment-ladder.md").read_text(
            encoding="utf-8"
        )
        record = (ROOT / "templates" / "decision-record.md").read_text(encoding="utf-8")
        self.assertIn("next-action-choice-menus.md", skill)
        self.assertIn("Pending baseline ≠ downgrade block", skill)
        self.assertIn("queue-`pending`", skill)
        self.assertIn("path menu", skill.lower())
        for needle in (
            "pending-tooling",
            "move-introducer",
            "force-align",
            "原生改造",
            "可行",
            "dependency:tree",
            "队列 **`pending`**",
        ):
            self.assertIn(needle, menus)
        self.assertIn("Feasible but pending baseline", gates)
        self.assertIn("queue status **`pending`**", gates)
        self.assertIn("Missing Maven/tree", gates)
        self.assertIn("路径选项菜单", ladder)
        self.assertIn("baseline_evidence_status", record)
        self.assertIn("路径选项菜单", record)

    def test_target_existence_gate(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        batching = (ROOT / "references" / "dual-entry-and-batching.md").read_text(
            encoding="utf-8"
        )
        contract = (ROOT / "references" / "report-contract.md").read_text(
            encoding="utf-8"
        )
        packet = (ROOT / "templates" / "decision-packet.md").read_text(encoding="utf-8")
        for text in (skill, batching, contract):
            self.assertIn("target_artifact_exists", text)
        self.assertIn("Target existence precheck", batching)
        self.assertIn("maven-metadata.xml", batching)
        self.assertIn("目标存在性", packet)
        # precheck must run before owner classification
        self.assertLess(
            skill.index("Target existence precheck"),
            skill.index("Classify effective owner"),
        )

    def test_eureka_groupid_mapping(self) -> None:
        text = (ROOT / "references" / "common-gav-repos.md").read_text(encoding="utf-8")
        self.assertIn("com.netflix.eureka", text)
        self.assertIn("spring-cloud-starter-netflix-eureka-client", text)
        self.assertNotIn("org.springframework.cloud.netflix |", text)

    def test_batch_report_layout_is_deterministic(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "report-contract.md").read_text(
            encoding="utf-8"
        )
        delivery = (
            ROOT.parents[0]
            / "docs"
            / "java-dependency-upgrade-delivery-usage.md"
        ).read_text(encoding="utf-8")
        full_layout = (
            "__variant-<build-variant>__scope-<batch-scope>"
        )
        for text in (skill, contract, delivery):
            self.assertIn("BATCH-INDEX.md", text)
            self.assertIn("<authority-layer>__<boot-line>", text)
            self.assertIn(full_layout, text)
            self.assertIn("no-boot", text)
        self.assertIn("decision-domain", skill)
        self.assertIn("decision-domain", contract)
        self.assertIn("boot_line=3.2.x", delivery)

    def test_validator_wired_in(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "report-contract.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue((ROOT / "scripts" / "validate_report.py").is_file())
        self.assertTrue((ROOT / "fixtures" / "valid-report.md").is_file())
        self.assertTrue((ROOT / "fixtures" / "valid-report-complete.md").is_file())
        for text in (skill, contract):
            self.assertIn("scripts/validate_report.py", text)
        self.assertIn("--evidence-dir", skill)
        # a structural pass must never be sold as sufficient evidence
        self.assertIn("never that", skill)

    def test_owner_internal_adjustment_ladder(self) -> None:
        owner = (ROOT / "references" / "owner-and-resolution.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("netty.version", owner)
        self.assertIn("jackson-bom.version", owner)
        self.assertIn("not fully accurate", owner)

    def test_jvm_specific_traps_and_api_diff(self) -> None:
        impact = (ROOT / "references" / "impact-and-validation.md").read_text(
            encoding="utf-8"
        )
        for needle in (
            "shade",
            "META-INF/services",
            "module-info",
            "Multi-Release",
            "japicmp",
            "revapi",
            "animal-sniffer",
        ):
            self.assertIn(needle, impact)

    def test_decision_record_covers_jvm_fields(self) -> None:
        schema = (ROOT / "references" / "decision-record-schema.md").read_text(
            encoding="utf-8"
        )
        record = (ROOT / "templates" / "decision-record.md").read_text(encoding="utf-8")
        for text in (schema, record):
            self.assertIn("目标存在性", text)
            self.assertIn("请求目标", text)
            self.assertIn("推荐替代目标", text)
            self.assertIn("Owner 阶梯", text)
            self.assertIn("scope", text)
            self.assertIn("建议处置", text)
        self.assertIn("2-property-override", schema)
        self.assertIn("迁移路径选项", record)
        self.assertIn("classifier", schema)
        self.assertIn("upgrade-introducer", record)
        self.assertIn("确认队列状态", record)
        self.assertIn("ready / pending / blocked / decided / deferred", record)
        self.assertNotIn("proceed-selected", record)
        self.assertIn("upgrade / downgrade / same / unknown", record)
        self.assertIn("状态枚举映射", schema)
        self.assertNotIn("`remove` / `replace`", schema.split("方向")[1].split("\n")[0])

    def test_analysis_status_blocked_documented(self) -> None:
        gates = (ROOT / "references" / "human-confirmation-gates.md").read_text(
            encoding="utf-8"
        )
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Packet `analysis_status=blocked`", gates)
        self.assertIn("batch-wide", gates)
        self.assertIn("Never set `analysis_status=blocked`", skill)
        self.assertIn("restate a reachable", gates)
        self.assertIn("Existence-404 row can be deferred", gates)
        self.assertIn("If no fix version is findable", gates)
        self.assertIn("**never** offer `defer`", gates)

    def test_unused_with_to_prefers_remove(self) -> None:
        ladder = (ROOT / "references" / "treatment-ladder.md").read_text(
            encoding="utf-8"
        )
        patterns = (ROOT / "references" / "common-upgrade-patterns.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("表里写了", ladder)
        self.assertIn("Even if the pasted table supplies a `to`", patterns)

    def test_complete_fixture_does_not_suggest_defer_on_blocked(self) -> None:
        complete = (ROOT / "fixtures" / "valid-report-complete.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("整行 `deferred`", complete)
        self.assertIn("对存在性 `blocked` 行直接答 `defer`", complete)
        self.assertIn("no-viable-path", complete)

    def test_decision_records_layout_documented(self) -> None:
        contract = (ROOT / "references" / "report-contract.md").read_text(
            encoding="utf-8"
        )
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("decision-records/", contract)
        self.assertIn("__", contract)
        self.assertIn("decision-records/", skill)
        self.assertTrue(
            (ROOT / "fixtures" / "decision-records" / "io.netty__netty-ALL.md").is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "examples"
                / "sample-evidence-multi"
                / "BATCH-INDEX.md"
            ).is_file()
        )

    def test_extra_fixtures_exist(self) -> None:
        for name in (
            "valid-report-remove.md",
            "valid-report-replace.md",
            "valid-report-open-target.md",
            "valid-report-choose-alternative.md",
            "valid-report-pending-baseline.md",
        ):
            self.assertTrue((ROOT / "fixtures" / name).is_file(), name)
        self.assertTrue(
            (
                ROOT
                / "fixtures"
                / "decision-records"
                / "com.netflix.eureka__eureka-client.md"
            ).is_file()
        )
    def test_candidate_schema_jvm_fields(self) -> None:
        batching = (ROOT / "references" / "dual-entry-and-batching.md").read_text(
            encoding="utf-8"
        )
        for field in (
            "`scope`",
            "`classifier`",
            "`optional`",
            "`exclusions_present`",
            "`recommended_treatment`",
            "`usage_status`",
            "`introducer_gav`",
            "`target_channel`",
            "`requested_gav`",
            "`recommended_gav`",
            "`recommended_target_exists`",
            "`decision_domain`",
        ):
            self.assertIn(field, batching)

    def test_target_existence_covers_classifier(self) -> None:
        batching = (ROOT / "references" / "dual-entry-and-batching.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("per classifier", batching)
        self.assertIn("-<classifier>.jar", batching)

    def test_minimal_caller_input_documented(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Minimal caller input", content)
        self.assertIn("short prompt", content.lower())

    def test_environment_preflight_documented(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        preflight = (ROOT / "references" / "environment-preflight.md").read_text(
            encoding="utf-8"
        )
        gates = (ROOT / "references" / "human-confirmation-gates.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Environment preflight", skill)
        self.assertIn("environment-preflight.md", skill)
        self.assertIn("Run environment preflight", skill)
        self.assertIn("wrapper-only is a graded pass", skill.lower())
        self.assertIn("do not write", skill.lower())
        for needle in (
            "java -version",
            "mvn -v",
            "gradle -v",
            "python",
            "graded pass",
            "wrapper",
        ):
            self.assertIn(needle, preflight)
        self.assertIn("do not write", preflight.lower())

    def test_executable_preflight_and_lifecycle_safety(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        preflight = (ROOT / "references" / "environment-preflight.md").read_text(
            encoding="utf-8"
        )
        gates = (ROOT / "references" / "human-confirmation-gates.md").read_text(
            encoding="utf-8"
        )
        script = (ROOT / "scripts" / "preflight.py").read_text(encoding="utf-8")
        self.assertIn("scripts/preflight.py", preflight)
        self.assertIn("| `0` |", preflight)
        self.assertIn("| `5` |", preflight)
        self.assertIn("| `6` |", preflight)
        self.assertIn("dependency:analyze-only", skill)
        self.assertIn("Never run bare `dependency:analyze`", skill)
        self.assertNotIn("`dependency:analyze`);", skill)
        self.assertIn("hard_gates_passed", script)
        self.assertIn("needs_build_tool_selection", script)
        self.assertIn("return 6", script)
        self.assertIn("api.github.com", script)
        self.assertIn("current-interpreter", script)
        self.assertIn("for name in (\"python\", \"python3\")", script)
        self.assertIn("shutil.which(name)", script)
        self.assertIn("TimeoutExpired", script)
        self.assertIn("exit `6`", preflight)
        self.assertIn("environment preflight failed", gates)
        self.assertIn("no report write", gates)
        self.assertIn("Environment preflight passed", skill)
        contract = (ROOT / "references" / "report-contract.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("环境前置", contract)
        self.assertIn("不要对 `fixtures/` 根直接 `--evidence-dir`", contract)
        # preflight must run before target existence / owner work
        self.assertLess(
            skill.index("Run environment preflight"),
            skill.index("Target existence precheck"),
        )

    def test_report_path_resolution_documented(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        for text in (skill, contract):
            self.assertIn("evidence/java-dependency-upgrade", text)
            self.assertIn("openspec/changes", text)
        self.assertIn("report_path", contract)
        self.assertIn("--output-dir", skill)
        self.assertNotIn(
            "If (4) is missing, ask once for change-dir",
            skill,
        )

    def test_batching_allows_ready_plus_blocked_same_layer(self) -> None:
        batching = (ROOT / "references" / "dual-entry-and-batching.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("ready + blocked may coexist", batching)

    def test_description_is_trigger_only(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        # Frontmatter description should not summarize the workflow (SDO).
        front = content.split("---", 2)[1]
        self.assertNotIn("treatment ladder then owner-first", front)
        self.assertNotIn("analysis_status=complete", front)
        self.assertIn("Analyze, never implement", front)


if __name__ == "__main__":
    unittest.main()

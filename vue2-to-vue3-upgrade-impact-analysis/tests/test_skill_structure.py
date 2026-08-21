from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SkillStructureTests(unittest.TestCase):
    def test_skill_frontmatter_and_size(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        self.assertIn("name: vue2-to-vue3-upgrade-impact-analysis", content)
        self.assertIn("Analyze, never implement", content)
        self.assertLess(len(content.splitlines()), 200)
        self.assertNotIn("delivery-", content.lower())
        self.assertNotIn("frontend-ui-stack-visual-parity", content)
        self.assertNotIn("upgrade-evidence/v1", content)
        self.assertIn("upgrade-summary.json", content)
        self.assertIn("when every other Skill folder is absent", content)
        self.assertIn("Name, never run, migration recipes", content)
        self.assertIn("Composition API", content)
        self.assertIn(".vue2-to-vue3-upgrade-analysis", content)
        self.assertIn("Minimum load (every run)", content)
        self.assertIn("python -m unittest discover -s tests", content)

    def test_runtime_resources_have_no_sibling_contract_dependency(self) -> None:
        files = [ROOT / "SKILL.md", ROOT / "agents" / "openai.yaml"]
        for folder in ["references", "templates", "scripts"]:
            files.extend(
                path
                for path in (ROOT / folder).rglob("*")
                if path.is_file() and path.suffix in {".md", ".yaml", ".json", ".py"}
            )
        forbidden = [
            "delivery-frame-spec",
            "delivery-execute-verify",
            "upgrade-evidence/v1",
            "frontend-ui-stack-visual-parity",
            "openspec/changes",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path.relative_to(ROOT)} couples to {token}")

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
            "environment-preflight.md",
            "dual-entry-and-batching.md",
            "migration-path-ladder.md",
            "subsystem-inventory.md",
            "impact-and-validation.md",
            "official-docs-index.md",
            "named-migration-recipes.md",
            "common-upgrade-patterns.md",
            "human-confirmation-gates.md",
            "next-action-choice-menus.md",
            "report-contract.md",
            "decision-record-schema.md",
            "sibling-skill-drift-checklist.md",
        }
        for name in required:
            text = (ROOT / "references" / name).read_text(encoding="utf-8")
            self.assertGreater(len(text), 200, name)

    def test_official_docs_index_canonical_urls(self) -> None:
        text = (ROOT / "references" / "official-docs-index.md").read_text(
            encoding="utf-8"
        )
        for token in (
            "https://v3-migration.vuejs.org/",
            "https://v3-migration.vuejs.org/breaking-changes/",
            "https://v3-migration.vuejs.org/migration-build",
            "https://router.vuejs.org/guide/migration/",
            "https://test-utils.vuejs.org/migration/",
            "do not invent",
            "vue_filter_register",
            "listeners_removed",
            "2023-12-31",
            "compatConfig",
            "Two-layer modification-point model",
            "https://vite.dev/guide/",
            "v4-to-v5",
        ):
            self.assertIn(token, text)

    def test_recipes_named_not_executed(self) -> None:
        recipes = (ROOT / "references" / "named-migration-recipes.md").read_text(
            encoding="utf-8"
        )
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("@vue/compat", recipes)
        self.assertIn("gogocode", recipes)
        self.assertIn("vue-upgrade-tool", recipes)
        self.assertIn("manual-cli5-webpack5", recipes)
        self.assertIn("never runs", recipes.lower() + skill.lower())
        self.assertIn("Name, never run", skill)
        self.assertIn("Typical globs", recipes)
        self.assertIn("Implementation-stage command shape", recipes)

    def test_report_contract_enums(self) -> None:
        text = (ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        for token in (
            "analysis_status",
            "decision_status",
            "batch_implementation_gate",
            "implementation_readiness",
            "required_for_path",
            "runtime_axis:",
            "vue2-to-vue3-upgrade-report.md",
            "确认队列",
            "Composition API 全仓重写：另立项，本次不评估工作量",
            "upgrade-summary.json",
            "路径未 `decided` 前",
            "人工补搜检查",
            "lockfile",
            "lockfile_status",
            "Vue.prototype",
            "globalProperties",
            ".vue2-to-vue3-upgrade-analysis",
            "无 lockfile",
            "禁止单独",
            "默认子系统全集",
            "推荐路径 id",
            "evidence_as_of",
            "named_recipes",
            "失败证明什么",
        ):
            self.assertIn(token, text)

    def test_gates_reject_blanket_natural_language(self) -> None:
        text = (ROOT / "references" / "human-confirmation-gates.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Natural-language answers", text)
        self.assertIn("全部放行", text)
        self.assertIn("Not** a proceed token", text)
        self.assertIn("required_for_path=yes", text)
        self.assertIn("handoff only", text.lower())

    def test_blockers_dedupe_documented(self) -> None:
        text = (ROOT / "references" / "subsystem-inventory.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("dedupe", text.lower())
        self.assertIn("queue_eligible=no", text)

    def test_same_repo_host_is_host_port(self) -> None:
        text = (ROOT / "references" / "dual-entry-and-batching.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("not automatically in-place", text)
        self.assertIn("implementation_target", text)

    def test_agents_yaml_exists(self) -> None:
        text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("vue2-to-vue3-upgrade-impact-analysis", text)

    def test_decision_packet_template_matches_visual_and_manual_contract(self) -> None:
        text = (ROOT / "templates" / "decision-packet.md").read_text(encoding="utf-8")
        visual = text.index("### ui_visual_risk")
        section_five = text.index("## 5. 分层影响分析")
        section_six = text.index("## 6. 风险分级")
        self.assertLess(section_five, visual)
        self.assertLess(visual, section_six)

        checklist = text[text.index("### 人工补搜检查") :]
        prototype_lines = [line for line in checklist.splitlines() if "Vue.prototype" in line]
        target_lines = [
            line
            for line in checklist.splitlines()
            if "globalProperties" in line or "provide/inject" in line
        ]
        self.assertEqual(len(prototype_lines), 1)
        self.assertEqual(len(target_lines), 1)
        self.assertNotEqual(prototype_lines[0], target_lines[0])

    def test_residual_audit_is_a_writable_shape_not_just_a_permitted_word(self) -> None:
        # SKILL.md allows `entry_mode: residual-audit`; the contract, the
        # template and a golden fixture have to make it actually writable.
        contract = (ROOT / "references" / "report-contract.md").read_text(
            encoding="utf-8"
        )
        for token in (
            "entry_mode",
            "residual-audit",
            "residual_findings",
            "required_cleanup_assertions",
            "compat_shims_present",
            "runtime_lane_residues",
        ):
            self.assertIn(token, contract, token)

        template = (ROOT / "templates" / "decision-packet.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("### residual_findings", template)
        self.assertIn("| entry_mode |", template)

        fixture = ROOT / "fixtures" / "residual-audit"
        for name in (
            "vue2-to-vue3-upgrade-report.md",
            "upgrade-summary.json",
            "inventory.json",
        ):
            self.assertTrue((fixture / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()

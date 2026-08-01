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
        self.assertNotIn("delivery-explore", content)
        self.assertNotIn("delivery-frame-spec", content)
        self.assertNotIn("delivery-plan-tasks", content)
        self.assertNotIn("delivery-execute-verify", content)
        self.assertIn("Name, never run, migration recipes", content)
        self.assertIn("Composition API", content)
        self.assertIn(".vue2-to-vue3-upgrade-analysis", content)
        self.assertIn("Minimum load (every run)", content)
        self.assertIn("python -m unittest discover -s tests", content)

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
        self.assertIn("never runs", recipes.lower() + skill.lower())
        self.assertIn("Name, never run", skill)

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
            "evidence/vue2-to-vue3-upgrade",
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

    def test_agents_yaml_exists(self) -> None:
        text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("vue2-to-vue3-upgrade-impact-analysis", text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "frontend_upgrade_report_contract", ROOT / "scripts" / "generate_upgrade_report.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GENERATOR
assert SPEC.loader is not None
SPEC.loader.exec_module(GENERATOR)


class SkillStructureTests(unittest.TestCase):
    def test_skill_is_concise_and_references_exist(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(content.splitlines()), 200)
        self.assertTrue(content.startswith("---\n"))
        self.assertIn("name: frontend-dependency-upgrade-impact-analysis", content)
        self.assertIn("frontend-dependency-upgrade-report.md", content)
        self.assertIn("--json-output", content)
        self.assertIn("run_with_compatible_node.py", content)
        self.assertIn("Markdown decision report plus optional structured JSON", content)
        references = set(re.findall(r"`references/([^`]+\.md)`", content))
        self.assertTrue(references)
        for relative in references:
            self.assertTrue((ROOT / "references" / relative).is_file(), relative)
        self.assertTrue((ROOT / "references" / "node-runtime-compatibility.md").is_file())
        self.assertTrue((ROOT / "scripts" / "run_with_compatible_node.py").is_file())

    def test_openai_metadata_matches_skill(self) -> None:
        content = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$frontend-dependency-upgrade-impact-analysis", content)
        match = re.search(r'short_description:\s+"([^"]+)"', content)
        self.assertIsNotNone(match)
        self.assertGreaterEqual(len(match.group(1)), 25)
        self.assertLessEqual(len(match.group(1)), 64)

    def test_skill_contains_no_auxiliary_readme(self) -> None:
        self.assertFalse((ROOT / "README.md").exists())

    def test_machine_enums_documented_where_they_are_enforced(self) -> None:
        """The generator constants are the single definition source; docs must not drift from them."""
        docs = {
            name: (ROOT / "references" / name).read_text(encoding="utf-8")
            for name in (
                "report-contract.md",
                "risk-model.md",
                "node-runtime-compatibility.md",
                "lockfile-and-evidence.md",
                "target-discovery-and-removal.md",
                "analysis-evidence-schema.md",
                "decision-record-schema.md",
            )
        }
        missing: list[str] = []

        def require(doc: str, values: object, label: str) -> None:
            for value in values:  # type: ignore[union-attr]
                if value not in docs[doc]:
                    missing.append(f"{doc} 缺少 {label}：{value}")

        require("report-contract.md", GENERATOR.REPORT_SECTION_TITLES, "报告章节 anchor")
        require("report-contract.md", GENERATOR.EVIDENCE_DIMENSIONS, "证据维度")
        require("analysis-evidence-schema.md", GENERATOR.REMOVAL_COVERAGE_AREAS, "删除覆盖维度")
        require("analysis-evidence-schema.md", GENERATOR.REMOVAL_STATUSES, "删除结论枚举")
        require("report-contract.md", GENERATOR.SELECTION_STATUSES, "选择状态枚举")
        require("risk-model.md", GENERATOR.RISK_FACTORS, "风险因子")
        require("lockfile-and-evidence.md", GENERATOR.LOCK_NAMES, "受支持 lockfile")
        require("node-runtime-compatibility.md", GENERATOR.NODE_SUPPORT_STATUSES, "Node 支持状态枚举")
        require("node-runtime-compatibility.md", GENERATOR.NODE_CONSTRAINT_KINDS, "Node 约束来源类别")
        require(
            "target-discovery-and-removal.md",
            [option for option, _title, _applicability, _evidence in GENERATOR.DISPOSITION_OPTIONS],
            "处置方案枚举",
        )
        require("report-contract.md", ("analysis-evidence", "curated-map"), "替代候选来源枚举")
        require("report-contract.md", GENERATOR.ALTERNATIVE_RANK_SIGNALS, "替代候选排序信号")
        require("target-discovery-and-removal.md", GENERATOR.ALTERNATIVE_RANK_SIGNALS, "替代候选排序信号")
        require("target-discovery-and-removal.md", ("fits", "conflicts"), "约束匹配枚举")
        require("target-discovery-and-removal.md", ("established", "needs-research"), "重构方案状态枚举")
        require("target-discovery-and-removal.md", ("reviewed", "curated-only", "pending"), "调研状态枚举")
        require("target-discovery-and-removal.md", ("available", "missing"), "选项完整性枚举")
        require("target-discovery-and-removal.md", GENERATOR.PRIMARY_TRACKS, "主轨枚举")
        require("report-contract.md", GENERATOR.PRIMARY_TRACKS, "主轨枚举")
        require("report-contract.md", GENERATOR.CONFIRMATION_STATUSES, "确认队列状态枚举")
        require("report-contract.md", GENERATOR.DECISION_RECORD_STATUSES, "决策记录状态枚举")
        require("decision-record-schema.md", GENERATOR.DECISION_RECORD_STATUSES, "决策记录状态枚举")
        require("target-discovery-and-removal.md", GENERATOR.REFACTOR_SCALES, "改造规模枚举")
        require("target-discovery-and-removal.md", GENERATOR.PROVENANCE_KINDS, "依赖来源枚举")
        require("report-contract.md", GENERATOR.PROVENANCE_KINDS, "依赖来源枚举")
        if str(GENERATOR.PARENT_CHAIN_LIMIT) not in docs["target-discovery-and-removal.md"]:
            missing.append("target-discovery-and-removal.md 缺少父包链展示上限")
        if GENERATOR.DECISION_FILE_NAME not in docs["decision-record-schema.md"]:
            missing.append("decision-record-schema.md 缺少默认决策文件名")
        for threshold in (
            GENERATOR.REFACTOR_SCALE_SMALL_FILES, GENERATOR.REFACTOR_SCALE_SMALL_POINTS,
            GENERATOR.REFACTOR_SCALE_MEDIUM_FILES, GENERATOR.REFACTOR_SCALE_MEDIUM_POINTS,
        ):
            if str(threshold) not in docs["target-discovery-and-removal.md"]:
                missing.append(f"target-discovery-and-removal.md 缺少改造规模阈值：{threshold}")
        for constant in ("REPLACEMENT_MAP_REVIEWED", "RESEARCH_CRITERIA", "REFACTOR_STAGES", "ALTERNATIVE_RANK_SIGNALS"):
            if constant not in docs["target-discovery-and-removal.md"]:
                missing.append(f"target-discovery-and-removal.md 缺少常量名：{constant}")
        for threshold in (GENERATOR.RISK_LOW_MAX, GENERATOR.RISK_MEDIUM_MAX):
            if str(threshold) not in docs["risk-model.md"]:
                missing.append(f"risk-model.md 缺少等级阈值：{threshold}")
        if GENERATOR.NODE_SCHEDULE_REVIEWED not in docs["node-runtime-compatibility.md"]:
            # The reviewed date lives in code; the doc only needs to say the table is a snapshot.
            self.assertIn("NODE_SCHEDULE_REVIEWED", docs["node-runtime-compatibility.md"])
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()

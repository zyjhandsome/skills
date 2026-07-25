from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()

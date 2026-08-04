from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillIndependenceTests(unittest.TestCase):
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
            "vue2-to-vue3-upgrade-impact-analysis",
            "openspec/changes",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path.relative_to(ROOT)} couples to {token}")


if __name__ == "__main__":
    unittest.main()

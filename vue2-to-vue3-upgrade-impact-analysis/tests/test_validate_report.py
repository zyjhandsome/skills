from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts" / "validate_report.py"
FIXTURES = ROOT / "fixtures"

MINIMAL_SECTIONS = """
## 1. 基线与假设
- lockfile：无 lockfile（复现性风险升高）
## 2. 仓画像与依赖就绪度
x
## 3. 推荐迁移路径
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：vue-compat（本技能不执行）
## 4. 子系统影响清单
{subsystem_table}
## 5. 分层影响分析
x
## 6. 风险分级
x
## 7. 确认队列
{queue_table}
## 8. 验证矩阵
x
## 9. 回滚与责任人
x
## 10. 未决问题与证据缺口
### 人工补搜检查
- slot-scope / Vue.filter / 非 vue-* 包 / lockfile：已声明
"""


def _status_block(
    analysis: str = "complete",
    decision: str = "decided",
    gate: str = "ready",
) -> str:
    return f"""# probe

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | {analysis} |
| decision_status | {decision} |
| batch_implementation_gate | {gate} |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | /tmp/x |
"""


class ValidateReportTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATE), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_partial_fixture_passes(self) -> None:
        result = self._run(str(FIXTURES / "valid-report.md"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_complete_fixture_passes(self) -> None:
        result = self._run(str(FIXTURES / "valid-report-complete.md"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_evidence_dir_complete_passes(self) -> None:
        result = self._run("--evidence-dir", str(FIXTURES / "evidence-complete"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_path_exit_4(self) -> None:
        result = self._run(str(FIXTURES / "no-such-report.md"))
        self.assertEqual(result.returncode, 4)

    def test_rejects_complete_missing_subsystem_record(self) -> None:
        body = _status_block() + MINIMAL_SECTIONS.format(
            subsystem_table=(
                "| 子系统 | scope_status | 风险 | 就绪度 | 命名配方 | 说明 |\n"
                "|---|---|---|---|---|---|\n"
                "| `core-vue` | in_scope | high | needs-major | x | x |\n"
                "| `ui` | in_scope | blocker | replace | x | x |"
            ),
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | decided | ok | proceed:path:compat-big-bang |\n"
                "| `subsystem:core-vue` | subsystem | decided | ok | proceed:subsystem:core-vue |\n"
                "| `subsystem:ui` | subsystem | decided | ok | proceed:subsystem:ui |"
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "vue2-to-vue3-upgrade-report.md"
            report.write_text(body, encoding="utf-8")
            records = root / "decision-records"
            records.mkdir()
            (records / "migration-path__compat-big-bang.md").write_text("# path\n", encoding="utf-8")
            (records / "subsystem__ui.md").write_text("# ui\n", encoding="utf-8")
            result = self._run("--evidence-dir", str(root))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("subsystem__core-vue.md", result.stdout)

    def test_rejects_name_recipe_without_never_run(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=(
                "| 子系统 | scope_status | 风险 | 就绪度 | 命名配方 | 说明 |\n"
                "|---|---|---|---|---|---|\n"
                "| `core-vue` | in_scope | medium | needs-major | x | x |"
            ),
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` / `other` |"
            ),
        )
        body = body.replace(
            "- 命名配方（Name, never run）：vue-compat（本技能不执行）",
            "- 命名配方：vue-compat",
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("Name-never-run", result.stdout)

    def test_rejects_subsystem_ready_before_path_decided(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=(
                "| 子系统 | scope_status | 风险 | 就绪度 | 命名配方 | 说明 |\n"
                "|---|---|---|---|---|---|\n"
                "| `ui` | in_scope | blocker | replace | x | x |"
            ),
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |\n"
                "| `subsystem:ui` | subsystem | ready | ok | `proceed:subsystem:ui` / `defer` |"
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("before path is decided", result.stdout)

    def test_rejects_missing_lockfile_baseline(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=(
                "| 子系统 | scope_status | 风险 | 就绪度 | 命名配方 | 说明 |\n"
                "|---|---|---|---|---|---|\n"
                "| `core-vue` | in_scope | medium | needs-major | x | x |"
            ),
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        body = body.replace("- lockfile：无 lockfile（复现性风险升高）", "- 无锁声明")
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("lockfile", result.stdout.lower())

    def test_rejects_missing_manual_gap_checklist(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=(
                "| 子系统 | scope_status | 风险 | 就绪度 | 命名配方 | 说明 |\n"
                "|---|---|---|---|---|---|\n"
                "| `core-vue` | in_scope | medium | needs-major | x | x |"
            ),
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        body = body.replace("### 人工补搜检查\n- slot-scope / Vue.filter / 非 vue-* 包 / lockfile：已声明\n", "- x\n")
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("人工补搜检查", result.stdout)

    def test_rejects_high_subsystem_missing_from_queue(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=(
                "| 子系统 | scope_status | 风险 | 就绪度 | 命名配方 | 说明 |\n"
                "|---|---|---|---|---|---|\n"
                "| `core-vue` | in_scope | high | needs-major | x | x |"
            ),
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("missing from confirmation queue", result.stdout)


if __name__ == "__main__":
    unittest.main()

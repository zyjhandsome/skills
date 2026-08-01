from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts" / "validate_report.py"
FIXTURES = ROOT / "fixtures"

DEFAULT_SUBSYSTEM_ROWS = """| 子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明 |
|---|---|---|---|---|---|---|
| `core-vue` | in_scope | medium | needs-major | no | vue-compat | note |
| `router` | in_scope | medium | needs-major | no | manual-router4 | note |
| `build` | in_scope | medium | needs-major | no | webpack-to-vite | note |
| `store` | in_scope | medium | needs-major | no | vuex4 | note |
| `ui` | not_applicable | n/a | unused | no | — | no UI kit |
| `test` | in_scope | medium | needs-major | no | test-utils | note |
| `lint-ide` | in_scope | medium | needs-major | no | eslint-vue3 | note |
| `i18n-plugins` | not_applicable | n/a | unused | no | — | none |
| `composition-existing` | in_scope | low | unused | no | — | none |
| `blockers` | in_scope | n/a | unused | no | — | none |"""

MINIMAL_SECTIONS = """
## 1. 基线与假设
- lockfile：`package-lock.json`
- lockfile_status: present
- 说明：分析说明（非占位）
## 2. 仓画像与依赖就绪度
| 包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据 |
|---|---|---|---|---|
| `vue` | 2.7.16 | needs-major | vue3 | lock |
## 3. 推荐迁移路径
- 推荐路径 id：`compat-big-bang`
- Composition API 全仓重写：另立项，本次不评估工作量
- 命名配方（Name, never run）：vue-compat（本技能不执行）
- runtime_axis: compat
- build_axis: vite
- topology_axis: single-cutover
## 4. 子系统影响清单
{subsystem_table}
## 5. 分层影响分析
分析说明（非占位）
## 6. 风险分级
分析说明（非占位）
## 7. 确认队列
{queue_table}
## 8. 验证矩阵
分析说明（非占位）
## 9. 回滚与责任人
分析说明（非占位）
## 10. 未决问题与证据缺口
### 人工补搜检查
- slot-scope：无命中
- Vue.filter：无命中
- 非 `vue-*`：无候选
- Vue.prototype：无挂载
- globalProperties / provide/inject：n/a（无自定义挂载）
- lockfile：lockfile_status=present
"""


def _status_block(
    analysis: str = "complete",
    decision: str = "decided",
    gate: str = "ready",
    report_path: str = "fixtures",
) -> str:
    return f"""# probe

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | {analysis} |
| decision_status | {decision} |
| batch_implementation_gate | {gate} |
| implementation_readiness | not_assessed |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | {report_path} |
| evidence_as_of | 2026-08-01 |
"""


def _record(unit: str, status: str = "decided", risk: str = "high") -> str:
    typ, uid = unit.split(":", 1)
    token = (
        f"proceed:{typ}:{uid}"
        if status == "decided"
        else ("defer" if status == "deferred" else "other")
    )
    return (
        "| 字段 | 内容 |\n|---|---|\n"
        f"| 单元键 | {unit} |\n"
        f"| 类型 | {typ} |\n"
        "| 当前结论 | ok |\n"
        f"| 风险 | {risk} |\n"
        "| 命名配方 | x |\n"
        "| 兼容性证据（URL） | https://example.com |\n"
        "| 已命名验证项 | smoke |\n"
        "| 回滚触发条件 + 恢复目标 | revert |\n"
        "| 责任人 | frontend |\n"
        f"| 推荐确认选项 | proceed:{typ}:{uid} |\n"
        f"| 确认队列状态 | {status} |\n"
        f"| 人工答复 | {token} |\n"
    )


def _high_ui_table() -> str:
    return DEFAULT_SUBSYSTEM_ROWS.replace(
        "| `ui` | not_applicable | n/a | unused | no | — | no UI kit |",
        "| `ui` | in_scope | blocker | replace | yes | gogocode-element | Element |",
    )


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
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = _status_block(report_path=str(root.resolve())) + MINIMAL_SECTIONS.format(
                subsystem_table=_high_ui_table().replace(
                    "| `core-vue` | in_scope | medium | needs-major | no | vue-compat | note |",
                    "| `core-vue` | in_scope | high | needs-major | yes | vue-compat | note |",
                ),
                queue_table=(
                    "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                    "|---|---|---|---|---|\n"
                    "| `path:compat-big-bang` | path | decided | ok | proceed:path:compat-big-bang |\n"
                    "| `subsystem:core-vue` | subsystem | decided | ok | proceed:subsystem:core-vue |\n"
                    "| `subsystem:ui` | subsystem | decided | ok | proceed:subsystem:ui |"
                ),
            )
            if "实施需另授权" not in body:
                body = body.replace(
                    f"| report_path | {root.resolve()} |",
                    f"| report_path | {root.resolve()} |\n\n**横幅：** 实施需另授权，本技能不改代码",
                )
            report = root / "vue2-to-vue3-upgrade-report.md"
            report.write_text(body, encoding="utf-8")
            records = root / "decision-records"
            records.mkdir()
            (records / "migration-path__compat-big-bang.md").write_text(
                _record("path:compat-big-bang"), encoding="utf-8"
            )
            (records / "subsystem__ui.md").write_text(
                _record("subsystem:ui", risk="blocker"), encoding="utf-8"
            )
            result = self._run("--evidence-dir", str(root))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("subsystem__core-vue.md", result.stdout)

    def test_rejects_name_recipe_without_never_run(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
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
            subsystem_table=_high_ui_table(),
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
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        body = body.replace(
            "- lockfile：`package-lock.json`\n- lockfile_status: present",
            "- 无锁声明",
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("lockfile", result.stdout.lower())

    def test_rejects_ready_when_no_lockfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = _status_block(report_path=str(root.resolve())) + MINIMAL_SECTIONS.format(
                subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
                queue_table=(
                    "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                    "|---|---|---|---|---|\n"
                    "| `path:compat-big-bang` | path | decided | ok | proceed:path:compat-big-bang |"
                ),
            )
            body = body.replace(
                "- lockfile：`package-lock.json`",
                "- lockfile：无 lockfile（复现性风险升高）",
            )
            body = body.replace("- lockfile_status: present", "- lockfile_status: absent")
            body = body.replace(
                f"| report_path | {root.resolve()} |",
                f"| report_path | {root.resolve()} |\n\n**横幅：** 实施需另授权，本技能不改代码",
            )
            report = root / "vue2-to-vue3-upgrade-report.md"
            report.write_text(body, encoding="utf-8")
            records = root / "decision-records"
            records.mkdir()
            (records / "migration-path__compat-big-bang.md").write_text(
                _record("path:compat-big-bang"), encoding="utf-8"
            )
            result = self._run("--evidence-dir", str(root))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("lockfile_status=present", result.stdout)

    def test_rejects_missing_axis_markers(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        body = body.replace("- runtime_axis: compat\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("runtime_axis:", result.stdout)

    def test_rejects_missing_manual_gap_checklist(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        body = body.replace(
            "### 人工补搜检查\n"
            "- slot-scope：无命中\n"
            "- Vue.filter：无命中\n"
            "- 非 `vue-*`：无候选\n"
            "- Vue.prototype：无挂载\n"
            "- globalProperties / provide/inject：n/a（无自定义挂载）\n"
            "- lockfile：lockfile_status=present\n",
            "- x\n",
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("人工补搜检查", result.stdout)

    def test_rejects_checklist_title_without_required_items(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        body = body.replace(
            "### 人工补搜检查\n"
            "- slot-scope：无命中\n"
            "- Vue.filter：无命中\n"
            "- 非 `vue-*`：无候选\n"
            "- Vue.prototype：无挂载\n"
            "- globalProperties / provide/inject：n/a（无自定义挂载）\n"
            "- lockfile：lockfile_status=present\n",
            "### 人工补搜检查\n- 已检查\n",
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("manual checklist missing item", result.stdout)

    def test_rejects_high_subsystem_missing_from_queue(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS.replace(
                "| `core-vue` | in_scope | medium | needs-major | no | vue-compat | note |",
                "| `core-vue` | in_scope | high | needs-major | yes | vue-compat | note |",
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

    def test_rejects_deferred_blocker_with_ready_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = _status_block(report_path=str(root.resolve())) + MINIMAL_SECTIONS.format(
                subsystem_table=_high_ui_table(),
                queue_table=(
                    "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                    "|---|---|---|---|---|\n"
                    "| `path:compat-big-bang` | path | decided | ok | proceed:path:compat-big-bang |\n"
                    "| `subsystem:ui` | subsystem | deferred | ok | proceed:subsystem:ui / defer |"
                ),
            )
            body = body.replace(
                f"| report_path | {root.resolve()} |",
                f"| report_path | {root.resolve()} |\n\n**横幅：** 实施需另授权 handoff only",
            )
            report = root / "vue2-to-vue3-upgrade-report.md"
            report.write_text(body, encoding="utf-8")
            records = root / "decision-records"
            records.mkdir()
            (records / "migration-path__compat-big-bang.md").write_text(
                _record("path:compat-big-bang"), encoding="utf-8"
            )
            (records / "subsystem__ui.md").write_text(
                _record("subsystem:ui", "deferred", "blocker"), encoding="utf-8"
            )
            result = self._run("--evidence-dir", str(root))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("blocked/deferred", result.stdout)

    def test_rejects_bare_dot_report_path(self) -> None:
        body = _status_block(
            analysis="partial",
            decision="needs_choice",
            gate="frozen",
            report_path=".",
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
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
            self.assertIn("report_path", result.stdout)

    def test_rejects_wrong_absolute_report_path(self) -> None:
        body = _status_block(
            analysis="partial",
            decision="needs_choice",
            gate="frozen",
            report_path="C:/totally/wrong",
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
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
            self.assertIn("does not match actual report directory", result.stdout)

    def test_rejects_unknown_path_id(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:banana-path` | path | ready | ok | proceed:path:banana-path |"
            ),
        )
        body = body.replace(
            "- 推荐路径 id：`compat-big-bang`",
            "- 推荐路径 id：`banana-path`",
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("unknown path id", result.stdout)

    def test_rejects_incomplete_default_subsystem_set(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=(
                "| 子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明 |\n"
                "|---|---|---|---|---|---|---|\n"
                "| `core-vue` | in_scope | medium | needs-major | no | vue | note |"
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
            self.assertIn("missing default subsystem rows", result.stdout)

    def test_rejects_axis_conflict_with_path_preset(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        body = body.replace("runtime_axis: compat", "runtime_axis: direct-vue3")
        body = body.replace("topology_axis: single-cutover", "topology_axis: coexist")
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("conflicts with", result.stdout)

    def test_rejects_queue_path_mismatch_recommended(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:direct-vue3` | path | ready | ok | proceed:path:direct-vue3 |"
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("does not match §3", result.stdout)

    def test_rejects_missing_evidence_as_of(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        body = body.replace("| evidence_as_of | 2026-08-01 |\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("evidence_as_of", result.stdout)

    def test_rejects_decision_record_without_http_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = _status_block(report_path=str(root.resolve())) + MINIMAL_SECTIONS.format(
                subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
                queue_table=(
                    "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                    "|---|---|---|---|---|\n"
                    "| `path:compat-big-bang` | path | decided | ok | proceed:path:compat-big-bang |"
                ),
            )
            body = body.replace(
                f"| report_path | {root.resolve()} |",
                f"| report_path | {root.resolve()} |\n\n**横幅：** 实施需另授权 handoff only",
            )
            report = root / "vue2-to-vue3-upgrade-report.md"
            report.write_text(body, encoding="utf-8")
            records = root / "decision-records"
            records.mkdir()
            bad = _record("path:compat-big-bang").replace(
                "https://example.com",
                "not-a-url",
            )
            (records / "migration-path__compat-big-bang.md").write_text(
                bad, encoding="utf-8"
            )
            result = self._run("--evidence-dir", str(root))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("http(s) URL", result.stdout)

    def test_rejects_single_line_shallow_checklist(self) -> None:
        body = _status_block(
            analysis="partial", decision="needs_choice", gate="frozen"
        ) + MINIMAL_SECTIONS.format(
            subsystem_table=DEFAULT_SUBSYSTEM_ROWS,
            queue_table=(
                "| 单元 | 类型 | 状态 | 问题 | 选项 |\n"
                "|---|---|---|---|---|\n"
                "| `path:compat-big-bang` | path | ready | ok | "
                "`proceed:path:compat-big-bang` / `defer` |"
            ),
        )
        body = body.replace(
            "### 人工补搜检查\n"
            "- slot-scope：无命中\n"
            "- Vue.filter：无命中\n"
            "- 非 `vue-*`：无候选\n"
            "- Vue.prototype：无挂载\n"
            "- globalProperties / provide/inject：n/a（无自定义挂载）\n"
            "- lockfile：lockfile_status=present\n",
            "### 人工补搜检查\n"
            "- slot-scope / Vue.filter / 非 `vue-*` / Vue.prototype / "
            "globalProperties / lockfile：已声明\n",
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertTrue(
                "dedicated line" in result.stdout or "shallow answer" in result.stdout,
                result.stdout,
            )


if __name__ == "__main__":
    unittest.main()

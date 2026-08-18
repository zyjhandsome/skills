from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import json
import shutil
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
- host_node_version: v18.20.4
- current_node_contract: >=18 from engines and CI
- current_node_evidence: engines declaration; CI Node 18 green build
- target_node_requirement: ^18.0.0 || >=20.0.0
- target_node_sources: vue@3.5.18 no engines.node; vite@5.4.19 engines.node ^18.0.0 || >=20.0.0; https://registry.npmjs.org/vite/5.4.19
- node_compatibility_status: compatible
- node_transition_strategy: same-node
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
| 命名配方 | 实施期命令 | 失败证明什么 | 证据状态 |
|---|---|---|---|
| vue-compat | alias vue to @vue/compat then build | missing migration build | 待实施阶段 |
| manual-router4 | migrate router per Vue Router 4 guide | 404 or history break | 待实施阶段 |
| webpack-to-vite | vite build after human-accept config | non-zero vite build | 待实施阶段 |
| vuex4 | Vuex 4 install API smoke | store inject fail | 待实施阶段 |
| test-utils | @vue/test-utils v2 mount | unit suite red | 待实施阶段 |
| eslint-vue3 | eslint-plugin-vue vue3 rules | leftover Vue2 lint | 待实施阶段 |
| gogocode-element | element form/table pages render | Plus mapping missing | 待实施阶段 |
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
| schema | vue3-upgrade-report/v1 |
| producer | vue2-to-vue3-upgrade-impact-analysis |
| summary_path | {report_path}/upgrade-summary.json |
| visual_acceptance_required | yes |
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

    def test_rejects_ui_trigger_without_visual_risk_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = (FIXTURES / "valid-report.md").read_text(encoding="utf-8")
            start = text.index("### ui_visual_risk")
            end = text.index("## 6. 风险分级", start)
            text = text[:start] + text[end:]
            text = text.replace("| report_path | fixtures |", f"| report_path | {root.resolve()} |")
            report = root / "report.md"
            report.write_text(text, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3)
            self.assertIn("ui_visual_risk", result.stdout + result.stderr)

    def test_rejects_missing_compact_summary_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = (FIXTURES / "valid-report.md").read_text(encoding="utf-8")
            text = text.replace("| summary_path | fixtures/upgrade-summary.json |", "| summary_path | TBD |")
            text = text.replace("| report_path | fixtures |", f"| report_path | {root.resolve()} |")
            report = root / "report.md"
            report.write_text(text, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3)
            self.assertIn("summary_path", result.stdout + result.stderr)

    def test_evidence_dir_complete_passes(self) -> None:
        result = self._run("--evidence-dir", str(FIXTURES / "evidence-complete"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def _copy_complete_evidence(self, target: Path) -> None:
        shutil.copytree(FIXTURES / "evidence-complete", target, dirs_exist_ok=True)
        report = target / "vue2-to-vue3-upgrade-report.md"
        body = report.read_text(encoding="utf-8")
        body = body.replace(
            "| report_path | fixtures/evidence-complete |",
            f"| report_path | {target.resolve()} |",
        ).replace(
            "| summary_path | fixtures/evidence-complete/upgrade-summary.json |",
            f"| summary_path | {(target / 'upgrade-summary.json').resolve()} |",
        )
        report.write_text(body, encoding="utf-8")
        summary = target / "upgrade-summary.json"
        data = json.loads(summary.read_text(encoding="utf-8"))
        data["report_path"] = str(report.resolve())
        data["inventory_path"] = str((target / "inventory.json").resolve())
        data["decision_records"] = [
            str(path.resolve()) for path in sorted((target / "decision-records").glob("*.md"))
        ]
        summary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_evidence_dir_rejects_missing_summary_and_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "evidence"
            self._copy_complete_evidence(root)
            (root / "upgrade-summary.json").unlink()
            inventory = root / "inventory.json"
            if inventory.exists():
                inventory.unlink()

            result = self._run("--evidence-dir", str(root))

            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("upgrade-summary.json", result.stdout)
            self.assertIn("inventory.json", result.stdout)

    def test_evidence_dir_rejects_cross_artifact_status_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "evidence"
            self._copy_complete_evidence(root)
            summary = root / "upgrade-summary.json"
            data = json.loads(summary.read_text(encoding="utf-8"))
            data["recommended_path"] = "direct-vue3"
            data["axes"] = {
                "runtime": "direct-vue3",
                "build": "vite",
                "topology": "single-cutover",
            }
            summary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            result = self._run("--evidence-dir", str(root))

            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("recommended_path", result.stdout)

    def test_evidence_dir_rejects_decision_record_manifest_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "evidence"
            self._copy_complete_evidence(root)
            summary = root / "upgrade-summary.json"
            data = json.loads(summary.read_text(encoding="utf-8"))
            data["decision_records"] = []
            summary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            result = self._run("--evidence-dir", str(root))

            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("decision_records", result.stdout + result.stderr)

    def test_evidence_dir_rejects_named_recipe_summary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "evidence"
            self._copy_complete_evidence(root)
            summary = root / "upgrade-summary.json"
            data = json.loads(summary.read_text(encoding="utf-8"))
            data["named_recipes"] = [
                recipe for recipe in data["named_recipes"] if recipe != "eslint-vue3"
            ]
            summary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            result = self._run("--evidence-dir", str(root))

            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("named_recipes", result.stdout + result.stderr)

    def test_multi_batch_accepts_documented_host_port_entry_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "evidence"
            batches = [
                root / "workspace" / "desktop__variant-default__scope-full-stack",
                root / "host-port" / "mobile__variant-default__scope-page-closure",
            ]
            for batch in batches:
                self._copy_complete_evidence(batch)
            (root / "BATCH-INDEX.md").write_text(
                "# Batch index\n\n"
                "| path | workspace | variant | scope | analysis_status | decision_status | batch_implementation_gate |\n"
                "|---|---|---|---|---|---|---|\n"
                + "\n".join(
                    f"| {batch.relative_to(root).as_posix()} | {batch.parent.name} | default | full-stack | complete | decided | ready |"
                    for batch in batches
                ),
                encoding="utf-8",
            )

            result = self._run("--evidence-dir", str(root))

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

    def test_rejects_missing_target_node_requirement(self) -> None:
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
        body = body.replace("- target_node_requirement: ^18.0.0 || >=20.0.0\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("target_node_requirement", result.stdout)

    def test_rejects_ready_gate_with_unknown_node_matrix(self) -> None:
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
                "- target_node_requirement: ^18.0.0 || >=20.0.0",
                "- target_node_requirement: unknown (target versions not selected)",
            ).replace(
                "- node_compatibility_status: compatible",
                "- node_compatibility_status: unknown",
            ).replace(
                "- node_transition_strategy: same-node",
                "- node_transition_strategy: undecided",
            ).replace(
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
            result = self._run("--evidence-dir", str(root))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("Node status conflict/unknown", result.stdout)

    def test_upgrade_required_node_makes_build_high_and_required(self) -> None:
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
            "- node_compatibility_status: compatible",
            "- node_compatibility_status: upgrade-required",
        ).replace(
            "- node_transition_strategy: same-node",
            "- node_transition_strategy: upgrade-before-vue",
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("requires §4 build risk", result.stdout)

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

    def test_host_port_fixture_ok(self) -> None:
        result = self._run(str(FIXTURES / "valid-report-host-port.md"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_host_port_rejects_compat_runtime(self) -> None:
        body = (FIXTURES / "valid-report-host-port.md").read_text(encoding="utf-8")
        body = body.replace("runtime_axis: direct-vue3", "runtime_axis: compat")
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "vue2-to-vue3-upgrade-report.md"
            # report_path in status must match parent dir name for path check —
            # write under a dir named like status report_path or patch status.
            body = body.replace("| report_path | fixtures |", f"| report_path | {tmp} |")
            body = body.replace(
                "| summary_path | fixtures/upgrade-summary.json |",
                f"| summary_path | {Path(tmp).as_posix()}/upgrade-summary.json |",
            )
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            combined = result.stdout + result.stderr
            self.assertTrue(
                "host-port" in combined and ("compat" in combined or "conflicts" in combined),
                combined,
            )

    def test_host_port_requires_source_markers(self) -> None:
        body = (FIXTURES / "valid-report-host-port.md").read_text(encoding="utf-8")
        body = body.replace("- source_root: `/repo/vue2-source`\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "vue2-to-vue3-upgrade-report.md"
            body = body.replace("| report_path | fixtures |", f"| report_path | {tmp} |")
            body = body.replace(
                "| summary_path | fixtures/upgrade-summary.json |",
                f"| summary_path | {Path(tmp).as_posix()}/upgrade-summary.json |",
            )
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("source_root:", result.stdout + result.stderr)

    def test_rejects_validation_matrix_missing_named_recipe(self) -> None:
        body = (FIXTURES / "valid-report.md").read_text(encoding="utf-8")
        body = body.replace(
            "| `gogocode-element` | Element 主表单/表格页渲染 | Plus 映射缺失 | 待执行 |\n",
            "",
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "vue2-to-vue3-upgrade-report.md"
            body = body.replace("| report_path | fixtures |", f"| report_path | {tmp} |")
            body = body.replace(
                "| summary_path | fixtures/upgrade-summary.json |",
                f"| summary_path | {Path(tmp).as_posix()}/upgrade-summary.json |",
            )
            report.write_text(body, encoding="utf-8")
            result = self._run(str(report))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("gogocode-element", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

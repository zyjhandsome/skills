from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "valid-report.md"


def load_validator():
    path = ROOT / "scripts" / "validate_report.py"
    spec = importlib.util.spec_from_file_location("validate_report", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules; register before exec.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator()


class ReportValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.text = FIXTURE.read_text(encoding="utf-8")

    def write(self, text: str, name: str = "java-dependency-upgrade-report.md") -> Path:
        path = self.tmp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def errors_for(self, text: str) -> list[str]:
        return validator.validate_report(self.write(text)).errors

    def mutate_inventory_row(
        self,
        text: str,
        component: str,
        changes: dict[int, str],
    ) -> str:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith(f"| `{component}` |"):
                cells = line.split("|")
                for cell_index, value in changes.items():
                    cells[cell_index] = f" {value} "
                lines[index] = "|".join(cells)
                return "\n".join(lines) + "\n"
        self.fail(f"inventory row not found: {component}")

    def test_fixture_passes(self) -> None:
        self.assertEqual(validator.validate_report(FIXTURE).errors, [])

    def test_raw_template_is_rejected(self) -> None:
        errors = validator.validate_report(ROOT / "templates" / "decision-packet.md").errors
        self.assertTrue(any("模板" in message for message in errors))

    def test_missing_status_field(self) -> None:
        text = self.text.replace("| network_mode | online |\n", "")
        self.assertTrue(any("network_mode" in message for message in self.errors_for(text)))

    def test_illegal_status_value(self) -> None:
        text = self.text.replace("| analysis_status | partial |", "| analysis_status | done |")
        self.assertTrue(any("取值非法" in message for message in self.errors_for(text)))

    def test_duplicate_status_field_is_rejected(self) -> None:
        text = self.text + "\n| 字段 | 取值 |\n|---|---|\n| analysis_status | complete |\n"
        self.assertTrue(any("状态字段重复" in message for message in self.errors_for(text)))

    def test_decided_status_cannot_keep_ready(self) -> None:
        text = self.text.replace(
            "| decision_status | needs_choice |", "| decision_status | decided |"
        )
        self.assertTrue(
            any(
                "decision_status" in message and "ready" in message
                for message in self.errors_for(text)
            )
        )

    def test_complete_with_needs_choice_conflicts(self) -> None:
        text = self.text.replace("| analysis_status | partial |", "| analysis_status | complete |")
        errors = self.errors_for(text)
        self.assertTrue(any("需要清空" in m or "不得完成分析" in m for m in errors))

    def test_complete_with_ready_item_conflicts(self) -> None:
        text = self.text.replace(
            "| analysis_status | partial |", "| analysis_status | complete |"
        ).replace("| decision_status | needs_choice |", "| decision_status | decided |")
        self.assertTrue(any("ready" in message for message in self.errors_for(text)))

    def test_missing_section(self) -> None:
        text = self.text.replace("## 8. 验证矩阵", "## 8. 其他")
        self.assertTrue(any("验证矩阵" in message for message in self.errors_for(text)))

    def test_required_heading_must_match_exactly(self) -> None:
        text = self.text.replace("## 1. 基线与假设", "## 1. 非基线与假设补充")
        self.assertTrue(any("基线与假设" in message for message in self.errors_for(text)))

    def test_section_order(self) -> None:
        lines = self.text.splitlines()
        start = lines.index("## 9. 回滚与责任人")
        end = lines.index("## 10. 未决问题与证据缺口")
        reordered = lines[:start] + lines[end:] + lines[start:end]
        errors = self.errors_for("\n".join(reordered))
        self.assertTrue(any("顺序" in message for message in errors))

    def test_inventory_requires_existence_column(self) -> None:
        text = self.text.replace("| 目标存在性 ", "| 目标状态 ")
        self.assertTrue(any("表头列" in message for message in self.errors_for(text)))

    def test_illegal_existence_value(self) -> None:
        text = self.text.replace("| 2.21.4 | upgrade | yes |", "| 2.21.4 | upgrade | maybe |")
        self.assertTrue(
            any("目标存在性取值非法" in message for message in self.errors_for(text))
        )

    def test_upgrade_target_cannot_be_empty(self) -> None:
        text = self.mutate_inventory_row(
            self.text,
            "com.fasterxml.jackson.core:jackson-databind",
            {4: ""},
        )
        self.assertTrue(any("必须填写目标版本" in message for message in self.errors_for(text)))

    def test_inventory_semantic_cells_cannot_be_empty(self) -> None:
        text = self.mutate_inventory_row(
            self.text,
            "com.fasterxml.jackson.core:jackson-databind",
            {2: "", 3: "", 5: "", 10: "", 11: "", 12: "", 13: ""},
        )
        errors = self.errors_for(text)
        self.assertTrue(any("必填单元格为空" in message for message in errors))
        self.assertGreaterEqual(
            sum("必填单元格为空" in message for message in errors),
            6,
        )

    def test_non_existing_target_must_be_blocked(self) -> None:
        text = self.text.replace(
            "| `io.netty:netty-*` | blocked |", "| `io.netty:netty-*` | ready |"
        )
        self.assertTrue(any("必须在确认队列中为 blocked" in m for m in self.errors_for(text)))

    def test_component_missing_from_queue(self) -> None:
        text = self.text.replace(
            "| `com.fasterxml.jackson.core:jackson-databind` | ready | 是否按 Owner 属性（`upgrade-owner`）把 Jackson 家族升至 2.21.4？ | `proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4` / `defer` / `other` |\n",
            "",
        )
        self.assertTrue(any("缺少确认队列条目" in m for m in self.errors_for(text)))

    def test_illegal_queue_status(self) -> None:
        text = self.text.replace("| `io.netty:netty-*` | blocked |", "| `io.netty:netty-*` | waiting |")
        self.assertTrue(any("确认队列状态非法" in m for m in self.errors_for(text)))

    def test_pending_baseline_fixture_passes(self) -> None:
        path = ROOT / "fixtures" / "valid-report-pending-baseline.md"
        self.assertEqual(validator.validate_report(path).errors, [])

    def test_pending_row_forbids_proceed(self) -> None:
        pending = (ROOT / "fixtures" / "valid-report-pending-baseline.md").read_text(
            encoding="utf-8"
        )
        text = pending.replace(
            "| `defer` / `other` |",
            "| `proceed:com.netflix.eureka:eureka-client:2.0.5` / `defer` / `other` |",
        )
        self.assertTrue(
            any("pending 行不得提供" in message for message in self.errors_for(text))
        )

    def test_pending_requires_marker(self) -> None:
        pending = (ROOT / "fixtures" / "valid-report-pending-baseline.md").read_text(
            encoding="utf-8"
        )
        text = pending.replace("**待补证**", "基线未确认").replace("补证清单", "后续步骤")
        self.assertTrue(
            any("须标注待补证" in message for message in self.errors_for(text))
        )

    def test_existence_no_cannot_use_pending(self) -> None:
        text = self.text.replace(
            "| `io.netty:netty-*` | blocked |", "| `io.netty:netty-*` | pending |"
        ).replace(
            "| 重述目标 / `other` |",
            "| `defer` / `other` |",
        )
        # Also inject pending marker into the netty question so only existence rule fires.
        text = text.replace(
            "显式降级至 4.1.136.Final，但成员返回 404，目标不可达",
            "显式降级·待补证：成员 404",
        )
        errors = self.errors_for(text)
        self.assertTrue(any("必须在确认队列中为 blocked" in m for m in errors))

    def test_no_viable_path_cannot_be_ready(self) -> None:
        # n/a existence avoids the existence→blocked rule; treatment rule must still force blocked.
        old_inv = (
            "| `io.netty:netty-*`（8 个成员，含 `netty-codec-base`、`netty-codec-compression`） "
            "| `gateway` | 4.2.15.Final | 4.1.136.Final | downgrade | no | no-viable-path "
            "| — | n/a |"
        )
        new_inv = (
            "| `io.netty:netty-*`（8 个成员，含 `netty-codec-base`、`netty-codec-compression`） "
            "| `gateway` | 4.2.15.Final | — | unknown | n/a | no-viable-path "
            "| — | n/a |"
        )
        text = self.text.replace(old_inv, new_inv).replace(
            "| `io.netty:netty-*` | blocked |",
            "| `io.netty:netty-*` | ready |",
        ).replace(
            "| 重述目标 / `other` |",
            "| `defer` / `other` |",
        )
        self.assertTrue(
            any(
                "no-viable-path 必须在确认队列中为 blocked" in m
                for m in self.errors_for(text)
            )
        )

    def test_pending_decision_record_requires_baseline_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "java-dependency-upgrade-report.md"
            shutil.copyfile(
                ROOT / "fixtures" / "valid-report-pending-baseline.md", report
            )
            records = root / "decision-records"
            records.mkdir()
            src = (
                ROOT
                / "fixtures"
                / "decision-records"
                / "com.netflix.eureka__eureka-client.md"
            )
            body = src.read_text(encoding="utf-8").replace(
                "| baseline_evidence_status | pending-tree |",
                "| baseline_evidence_status | confirmed |",
            )
            (records / src.name).write_text(body, encoding="utf-8")
            errors = validator.validate_report(report).errors
            self.assertTrue(
                any("baseline_evidence_status" in message for message in errors)
            )

    def test_blocked_row_cannot_offer_proceed_or_defer(self) -> None:
        text = self.text.replace(
            "| 重述目标 / `other` |",
            "| `proceed:io.netty:netty-handler:4.1.136.Final` / `defer` |",
        )
        self.assertTrue(any("blocked 行不得提供" in message for message in self.errors_for(text)))

    def test_ready_row_options_cannot_be_empty(self) -> None:
        text = self.text.replace(
            "`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4` / `defer` / `other`",
            "",
        )
        self.assertTrue(any("选项为空" in message for message in self.errors_for(text)))

    def test_gate_ready_with_blocked_item(self) -> None:
        text = self.text.replace(
            "| batch_implementation_gate | frozen |", "| batch_implementation_gate | ready |"
        )
        self.assertTrue(
            any("batch_implementation_gate 不得为 ready" in m for m in self.errors_for(text))
        )

    def test_inventory_requires_treatment_column(self) -> None:
        text = self.text.replace("| 建议处置 ", "| 处置方案 ")
        self.assertTrue(any("表头列" in message for message in self.errors_for(text)))

    def test_illegal_treatment_value(self) -> None:
        text = self.text.replace("| upgrade | yes | upgrade-owner |", "| upgrade | yes | pin-it |")
        self.assertTrue(
            any("建议处置取值非法" in message for message in self.errors_for(text))
        )

    def test_na_existence_only_for_no_target_treatments(self) -> None:
        text = self.text.replace("| upgrade | yes | upgrade-owner |", "| upgrade | n/a | upgrade-owner |")
        self.assertTrue(any("n/a 仅允许" in message for message in self.errors_for(text)))

    def test_na_existence_allows_ready_for_remove(self) -> None:
        text = self.text.replace(
            "| 2.21.2 | 2.21.4 | upgrade | yes | upgrade-owner |",
            "| 2.21.2 | — | unknown | n/a | remove |",
        )
        errors = self.errors_for(text)
        self.assertFalse(any("必须在确认队列中为 blocked" in m for m in errors))
        self.assertFalse(any("n/a 仅允许" in m for m in errors))

    def test_complete_fixture_passes(self) -> None:
        complete = ROOT / "fixtures" / "valid-report-complete.md"
        self.assertEqual(validator.validate_report(complete).errors, [])

    def test_non_ga_versions_are_detected(self) -> None:
        cases = {
            "3.20.0-RC1": True,
            "1.0.0.RC1": True,
            "4.2.0.Alpha5": True,
            "1.0.0.Beta2": True,
            "2.0.0.M5": True,
            "1.0.0-SNAPSHOT": True,
            "9.13.0-preview1": True,
            "21-ea": True,
            "3.0.0-EAP2": True,
            "1.0.0-nightly": True,
            "4.1.136.Final": False,
            "2.21.4": False,
        }
        for version, expected in cases.items():
            self.assertEqual(
                bool(validator.NON_GA_PATTERN.search(version)),
                expected,
                msg=version,
            )

    def test_non_ga_target_warns_when_existence_yes(self) -> None:
        text = self.text.replace(
            "| 2.21.2 | 2.21.4 | upgrade | yes | upgrade-owner |",
            "| 2.21.2 | 2.21.4-RC1 | upgrade | yes | upgrade-owner |",
        )
        # Keep jackson queue blocked so only WARN on existence=yes, not ready ERROR.
        text = text.replace(
            "| `com.fasterxml.jackson.core:jackson-databind` | ready |",
            "| `com.fasterxml.jackson.core:jackson-databind` | blocked |",
        )
        findings = validator.validate_report(self.write(text))
        self.assertTrue(any("非 GA" in message for message in findings.warnings))
        self.assertFalse(any("不得进入 ready" in message for message in findings.errors))

    def test_non_ga_ready_is_error_without_allow_marker(self) -> None:
        text = self.text.replace(
            "| 2.21.2 | 2.21.4 | upgrade | yes | upgrade-owner |",
            "| 2.21.2 | 2.21.4-RC1 | upgrade | yes | upgrade-owner |",
        )
        errors = self.errors_for(text)
        self.assertTrue(any("不得进入 ready" in message for message in errors))

    def test_non_ga_ready_allowed_with_marker(self) -> None:
        text = self.text.replace(
            "| 2.21.2 | 2.21.4 | upgrade | yes | upgrade-owner |",
            "| 2.21.2 | 2.21.4-RC1 | upgrade | yes | upgrade-owner |",
        ).replace(
            "| `com.fasterxml.jackson.core:jackson-databind` | ready | 是否按 Owner 属性（`upgrade-owner`）把 Jackson 家族升至 2.21.4？ | `proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4` / `defer` / `other` |",
            "| `com.fasterxml.jackson.core:jackson-databind` | ready | non-ga-allowed：是否升至 2.21.4-RC1？ | `proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4-RC1` / `defer` / `other` |",
        )
        errors = self.errors_for(text)
        self.assertFalse(any("不得进入 ready" in message for message in errors))

    def test_analysis_blocked_cannot_keep_ready(self) -> None:
        text = self.text.replace(
            "| analysis_status | partial |", "| analysis_status | blocked |"
        )
        errors = self.errors_for(text)
        self.assertTrue(any("analysis_status=blocked" in message for message in errors))

    def test_gate_frozen_errors_when_queue_fully_cleared(self) -> None:
        complete = (ROOT / "fixtures" / "valid-report-complete.md").read_text(
            encoding="utf-8"
        )
        text = complete.replace(
            "| 4.1.136.Final | downgrade | no | no-viable-path |",
            "| 4.1.136.Final | downgrade | yes | upgrade-owner |",
        ).replace(
            "| `io.netty:netty-*` | blocked |",
            "| `io.netty:netty-*` | decided |",
        )
        errors = validator.validate_report(self.write(text)).errors
        self.assertTrue(any("必须为 ready" in message for message in errors))

    def test_decided_queue_status_allowed_when_complete(self) -> None:
        complete = ROOT / "fixtures" / "valid-report-complete.md"
        self.assertIn("| decided |", complete.read_text(encoding="utf-8"))
        self.assertEqual(validator.validate_report(complete).errors, [])

    def test_replace_row_preserves_requested_and_recommended_targets(self) -> None:
        text = self.mutate_inventory_row(
            self.text,
            "com.fasterxml.jackson.core:jackson-databind",
            {
                4: "3.20.0",
                5: "unknown",
                6: "no",
                7: "replace-component",
                8: "`org.apache.commons:commons-lang3:3.20.0`",
                9: "yes",
            },
        ).replace(
            "`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4`",
            "`replace:org.apache.commons:commons-lang3:3.20.0`",
        )
        self.assertEqual(self.errors_for(text), [])

    def test_replace_row_requires_reachable_recommended_target(self) -> None:
        text = self.mutate_inventory_row(
            self.text,
            "com.fasterxml.jackson.core:jackson-databind",
            {
                4: "3.20.0",
                5: "unknown",
                6: "no",
                7: "replace-component",
                8: "`org.apache.commons:commons-lang3:3.20.0`",
                9: "unknown",
            },
        ).replace(
            "`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4`",
            "`replace:org.apache.commons:commons-lang3:3.20.0`",
        )
        self.assertTrue(
            any("推荐替代存在性必须为 yes" in message for message in self.errors_for(text))
        )

    def test_blocked_options_allow_remove_in_prose(self) -> None:
        text = self.text.replace(
            "重述目标 / `other`",
            "不可 remove；重述目标 / `other`",
        )
        self.assertEqual(self.errors_for(text), [])

    def test_blocked_options_allow_english_restate(self) -> None:
        text = self.text.replace("重述目标 / `other`", "restate target / `other`")
        self.assertEqual(self.errors_for(text), [])

    def test_family_wildcard_matches_member_queue_key(self) -> None:
        text = self.text.replace(
            "| `io.netty:netty-*` | blocked |",
            "| `io.netty:netty-handler` | blocked |",
        )
        self.assertFalse(
            any("缺少确认队列条目" in message for message in self.errors_for(text))
        )

    def test_proceed_version_must_match_inventory_target(self) -> None:
        text = self.text.replace(
            "`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4`",
            "`proceed:com.fasterxml.jackson.core:jackson-databind:9.9.9`",
        )
        self.assertTrue(
            any("proceed 版本与清单目标不一致" in message for message in self.errors_for(text))
        )

    def test_replace_version_must_match_recommended_target(self) -> None:
        text = self.mutate_inventory_row(
            self.text,
            "com.fasterxml.jackson.core:jackson-databind",
            {
                4: "3.20.0",
                5: "unknown",
                6: "no",
                7: "replace-component",
                8: "`org.apache.commons:commons-lang3:3.20.0`",
                9: "yes",
            },
        ).replace(
            "`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4`",
            "`replace:org.apache.commons:commons-lang3:9.9.9`",
        )
        self.assertTrue(
            any(
                "replace 版本与清单推荐替代不一致" in message
                for message in self.errors_for(text)
            )
        )

    def test_missing_target_with_verified_same_gav_alternative_is_ready(self) -> None:
        text = self.mutate_inventory_row(
            self.text,
            "com.fasterxml.jackson.core:jackson-databind",
            {
                4: "9.9.9",
                5: "upgrade",
                6: "no",
                7: "choose-alternative",
                8: "`com.fasterxml.jackson.core:jackson-databind:2.21.3`",
                9: "yes",
            },
        ).replace(
            "`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4`",
            "`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.3`",
        )
        self.assertEqual(self.errors_for(text), [])

    def test_explicit_downgrade_uses_normal_ready_confirmation(self) -> None:
        text = self.mutate_inventory_row(
            self.text,
            "com.fasterxml.jackson.core:jackson-databind",
            {4: "2.20.0", 5: "downgrade", 7: "move-owner", 13: "降级 / 高"},
        ).replace(
            "是否按 Owner 属性（`upgrade-owner`）把 Jackson 家族升至 2.21.4？",
            "显式降级：是否按 Owner 属性把 Jackson 家族降级至 2.20.0？",
        ).replace(
            "`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4`",
            "`proceed:com.fasterxml.jackson.core:jackson-databind:2.20.0`",
        )
        self.assertEqual(self.errors_for(text), [])

    def test_downgrade_rejects_misnamed_upgrade_treatment(self) -> None:
        text = self.mutate_inventory_row(
            self.text,
            "com.fasterxml.jackson.core:jackson-databind",
            {4: "2.20.0", 5: "downgrade", 13: "降级 / 高"},
        ).replace(
            "是否按 Owner 属性（`upgrade-owner`）把 Jackson 家族升至 2.21.4？",
            "显式降级：是否降级至 2.20.0？",
        )
        self.assertTrue(any("对应 move-*" in message for message in self.errors_for(text)))

    def test_complete_missing_six_layer_is_error(self) -> None:
        text = (ROOT / "fixtures" / "valid-report-complete.md").read_text(
            encoding="utf-8"
        )
        text = "\n".join(
            line for line in text.splitlines() if not line.startswith("| 配置 |")
        )
        self.assertTrue(
            any("六层影响分析未点名" in message for message in self.errors_for(text))
        )

    def test_complete_empty_decision_record_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "java-dependency-upgrade-report.md"
            shutil.copyfile(ROOT / "fixtures" / "valid-report-complete.md", report)
            shutil.copytree(ROOT / "fixtures" / "decision-records", root / "decision-records")
            (root / "decision-records" / "com.fasterxml.jackson.core__jackson-databind.md").write_text(
                "", encoding="utf-8"
            )
            self.assertTrue(
                any("决策记录为空" in message for message in validator.validate_report(report).errors)
            )

    def test_legacy_defer_treatment_rejected(self) -> None:
        text = self.text.replace("| no | no-viable-path |", "| no | defer |")
        self.assertTrue(
            any("不得再用 defer" in message for message in self.errors_for(text))
        )

    def test_extra_fixtures_pass(self) -> None:
        for name in (
            "valid-report-remove.md",
            "valid-report-replace.md",
            "valid-report-open-target.md",
            "valid-report-choose-alternative.md",
            "valid-report-pending-baseline.md",
        ):
            path = ROOT / "fixtures" / name
            self.assertEqual(validator.validate_report(path).errors, [], msg=name)

    def test_pending_baseline_with_decision_record_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "java-dependency-upgrade-report.md"
            shutil.copyfile(
                ROOT / "fixtures" / "valid-report-pending-baseline.md", report
            )
            records = root / "decision-records"
            records.mkdir()
            src = (
                ROOT
                / "fixtures"
                / "decision-records"
                / "com.netflix.eureka__eureka-client.md"
            )
            shutil.copyfile(src, records / src.name)
            self.assertEqual(validator.validate_report(report).errors, [])

    def test_decision_record_queue_status_must_match_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "java-dependency-upgrade-report.md"
            shutil.copyfile(ROOT / "fixtures" / "valid-report-complete.md", report)
            shutil.copytree(
                ROOT / "fixtures" / "decision-records", root / "decision-records"
            )
            record = (
                root
                / "decision-records"
                / "com.fasterxml.jackson.core__jackson-databind.md"
            )
            record.write_text(
                record.read_text(encoding="utf-8").replace(
                    "| 确认队列状态 | decided |",
                    "| 确认队列状态 | ready |",
                ),
                encoding="utf-8",
            )
            errors = validator.validate_report(report).errors
            self.assertTrue(
                any("确认队列状态与报告确认队列不一致" in message for message in errors)
            )

    def test_complete_requires_decision_records(self) -> None:
        complete = (ROOT / "fixtures" / "valid-report-complete.md").read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "java-dependency-upgrade-report.md"
            report.write_text(complete, encoding="utf-8")
            errors = validator.validate_report(report).errors
            self.assertTrue(any("决策记录" in message for message in errors))

    def test_sample_evidence_multi_passes(self) -> None:
        evidence = ROOT / "examples" / "sample-evidence-multi"
        code = validator.main(["--evidence-dir", str(evidence)])
        self.assertEqual(code, 0)


class BatchLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def place(self, relative: str) -> None:
        target = self.tmp / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURE, target)

    def errors(self) -> list[str]:
        return validator.validate_batch_layout(self.tmp)[0].errors

    def test_single_batch_at_root(self) -> None:
        self.place("java-dependency-upgrade-report.md")
        self.assertEqual(self.errors(), [])

    def test_single_batch_in_subdir_is_rejected(self) -> None:
        self.place("exact/boot-bom__boot-3.2.x/java-dependency-upgrade-report.md")
        self.assertTrue(any("证据目录根" in message for message in self.errors()))

    def test_multi_batch_requires_index(self) -> None:
        self.place("exact/boot-bom__boot-3.2.x/java-dependency-upgrade-report.md")
        self.place("exact/app-library__no-boot/java-dependency-upgrade-report.md")
        self.assertTrue(any("BATCH-INDEX.md" in message for message in self.errors()))

    def test_multi_batch_valid_layout(self) -> None:
        self.place("exact/boot-bom__boot-3.2.x__variant-default__scope-json/java-dependency-upgrade-report.md")
        self.place("exact/app-library__no-boot__variant-default__scope-lucene/java-dependency-upgrade-report.md")
        (self.tmp / "BATCH-INDEX.md").write_text(
            "\n".join(
                [
                    "# 批次索引",
                    "",
                    "| 目录 | 权威层 | Boot 线 | 构建变体 | 批次范围 | 决策域 | 成员 | analysis_status | decision_status | batch_implementation_gate |",
                    "|---|---|---|---|---|---|---|---|---|---|",
                    "| exact/boot-bom__boot-3.2.x__variant-default__scope-json/ | boot-bom | boot-3.2.x | default | json | — | jackson, netty | partial | needs_choice | frozen |",
                    "| exact/app-library__no-boot__variant-default__scope-lucene/ | app-library | no-boot | default | lucene | — | lucene | partial | needs_choice | frozen |",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self.assertEqual(self.errors(), [])

    def test_multi_batch_index_must_list_batches_and_status_fields(self) -> None:
        self.place("exact/boot-bom__boot-3.2.x/java-dependency-upgrade-report.md")
        self.place("exact/app-library__no-boot/java-dependency-upgrade-report.md")
        (self.tmp / "BATCH-INDEX.md").write_text("# 批次索引\n空壳\n", encoding="utf-8")
        errors = self.errors()
        self.assertTrue(any("analysis_status" in message for message in errors))
        self.assertTrue(any("未索引批次" in message for message in errors))

    def test_batch_index_requires_values_not_only_headers(self) -> None:
        self.place("exact/boot-bom__boot-3.2.x__variant-default__scope-json/java-dependency-upgrade-report.md")
        self.place("exact/app-library__no-boot__variant-default__scope-lucene/java-dependency-upgrade-report.md")
        (self.tmp / "BATCH-INDEX.md").write_text(
            "\n".join(
                [
                    "| 目录 | 权威层 | Boot 线 | 构建变体 | 批次范围 | 决策域 | 成员 | analysis_status | decision_status | batch_implementation_gate |",
                    "|---|---|---|---|---|---|---|---|---|---|",
                    "| exact/boot-bom__boot-3.2.x__variant-default__scope-json/ | | | | | — | | partial | needs_choice | frozen |",
                    "| exact/app-library__no-boot__variant-default__scope-lucene/ | | | | | — | | partial | needs_choice | frozen |",
                ]
            ),
            encoding="utf-8",
        )
        errors = self.errors()
        self.assertTrue(any("必填值为空" in message for message in errors))

    def test_decision_domain_layout_and_index(self) -> None:
        self.place(
            "exact/app-library__no-boot__variant-default__scope-commons-lang__domain-commons-lang-major/"
            "java-dependency-upgrade-report.md"
        )
        self.place("exact/app-library__no-boot__variant-default__scope-lucene/java-dependency-upgrade-report.md")
        (self.tmp / "BATCH-INDEX.md").write_text(
            "\n".join(
                [
                    "| 目录 | 权威层 | Boot 线 | 构建变体 | 批次范围 | 决策域 | 成员 | analysis_status | decision_status | batch_implementation_gate |",
                    "|---|---|---|---|---|---|---|---|---|---|",
                    "| exact/app-library__no-boot__variant-default__scope-commons-lang__domain-commons-lang-major/ | app-library | no-boot | default | commons-lang | commons-lang-major | commons-lang | partial | needs_choice | frozen |",
                    "| exact/app-library__no-boot__variant-default__scope-lucene/ | app-library | no-boot | default | lucene | — | lucene | partial | needs_choice | frozen |",
                ]
            ),
            encoding="utf-8",
        )
        self.assertEqual(self.errors(), [])

    def test_decision_domain_requires_index_column(self) -> None:
        self.place(
            "exact/app-library__no-boot__variant-default__scope-commons-lang__domain-commons-lang-major/"
            "java-dependency-upgrade-report.md"
        )
        self.place("exact/app-library__no-boot__variant-default__scope-lucene/java-dependency-upgrade-report.md")
        (self.tmp / "BATCH-INDEX.md").write_text(
            "\n".join(
                [
                    "| 目录 | 权威层 | Boot 线 | 成员 | analysis_status | decision_status | batch_implementation_gate |",
                    "|---|---|---|---|---|---|---|",
                    "| exact/app-library__no-boot__commons-lang-major/ | app-library | no-boot | commons-lang | partial | needs_choice | frozen |",
                    "| exact/app-library__no-boot/ | app-library | no-boot | lucene | partial | needs_choice | frozen |",
                ]
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("缺少结构化索引表" in message for message in self.errors()))

    def test_empty_boot_line_is_rejected(self) -> None:
        self.place("exact/boot-bom__boot-__variant-default__scope-netty/java-dependency-upgrade-report.md")
        self.place("exact/app-library__no-boot__variant-default__scope-lucene/java-dependency-upgrade-report.md")
        (self.tmp / "BATCH-INDEX.md").write_text(
            "\n".join(
                [
                    "| 目录 | 权威层 | Boot 线 | 成员 | analysis_status | decision_status | batch_implementation_gate |",
                    "|---|---|---|---|---|---|---|",
                    "| exact/boot-bom__boot-/ | boot-bom | boot- | netty | blocked | not_needed | frozen |",
                    "| exact/app-library__no-boot/ | app-library | no-boot | lucene | partial | needs_choice | frozen |",
                ]
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("boot-line 非法" in message for message in self.errors()))

    def test_illegal_layer_and_boot_line(self) -> None:
        self.place("exact/mystery__3.2.x__variant-default__scope-x/java-dependency-upgrade-report.md")
        self.place("exact/app-library__no-boot__variant-default__scope-lucene/java-dependency-upgrade-report.md")
        (self.tmp / "BATCH-INDEX.md").write_text("# 批次索引\n", encoding="utf-8")
        errors = self.errors()
        self.assertTrue(any("authority-layer 非法" in message for message in errors))
        self.assertTrue(any("boot-line 非法" in message for message in errors))

    def test_missing_report(self) -> None:
        self.assertTrue(any("找不到" in message for message in self.errors()))


class CliTests(unittest.TestCase):
    def test_exit_codes(self) -> None:
        self.assertEqual(validator.main([str(FIXTURE)]), 0)
        self.assertEqual(validator.main([str(ROOT / "templates" / "decision-packet.md")]), 3)
        self.assertEqual(validator.main([str(ROOT / "does-not-exist.md")]), 4)

    def test_fixtures_dir_is_not_evidence_layout(self) -> None:
        # Sample files are named valid-report*.md — not java-dependency-upgrade-report.md.
        code = validator.main(["--evidence-dir", str(ROOT / "fixtures")])
        self.assertEqual(code, 3)

    def test_evidence_dir_single_renamed_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "java-dependency-upgrade-report.md"
            shutil.copyfile(FIXTURE, target)
            self.assertEqual(validator.main(["--evidence-dir", tmp]), 0)


if __name__ == "__main__":
    unittest.main()

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
        text = self.text.replace("| 2.21.4 | yes |", "| 2.21.4 | maybe |")
        self.assertTrue(
            any("目标存在性取值非法" in message for message in self.errors_for(text))
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
        text = self.text.replace("| `io.netty:netty-*` | blocked |", "| `io.netty:netty-*` | pending |")
        self.assertTrue(any("确认队列状态非法" in m for m in self.errors_for(text)))

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
        text = self.text.replace("| yes | upgrade-owner |", "| yes | pin-it |")
        self.assertTrue(
            any("建议处置取值非法" in message for message in self.errors_for(text))
        )

    def test_na_existence_only_for_no_target_treatments(self) -> None:
        text = self.text.replace("| yes | upgrade-owner |", "| n/a | upgrade-owner |")
        self.assertTrue(any("n/a 仅允许" in message for message in self.errors_for(text)))

    def test_na_existence_allows_ready_for_remove(self) -> None:
        text = self.text.replace(
            "| 2.21.2 | 2.21.4 | yes | upgrade-owner |",
            "| 2.21.2 | — | n/a | remove |",
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
            "| 2.21.2 | 2.21.4 | yes | upgrade-owner |",
            "| 2.21.2 | 2.21.4-RC1 | yes | upgrade-owner |",
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
            "| 2.21.2 | 2.21.4 | yes | upgrade-owner |",
            "| 2.21.2 | 2.21.4-RC1 | yes | upgrade-owner |",
        )
        errors = self.errors_for(text)
        self.assertTrue(any("不得进入 ready" in message for message in errors))

    def test_non_ga_ready_allowed_with_marker(self) -> None:
        text = self.text.replace(
            "| 2.21.2 | 2.21.4 | yes | upgrade-owner |",
            "| 2.21.2 | 2.21.4-RC1 | yes | upgrade-owner |",
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

    def test_gate_frozen_warns_when_queue_fully_cleared(self) -> None:
        complete = (ROOT / "fixtures" / "valid-report-complete.md").read_text(
            encoding="utf-8"
        )
        text = complete.replace(
            "| 4.1.136.Final | no | defer |",
            "| 4.1.136.Final | yes | upgrade-owner |",
        ).replace(
            "| `io.netty:netty-*` | blocked |",
            "| `io.netty:netty-*` | decided |",
        )
        warnings = validator.validate_report(self.write(text)).warnings
        self.assertTrue(any("可为 ready" in message for message in warnings))

    def test_decided_queue_status_allowed_when_complete(self) -> None:
        complete = (ROOT / "fixtures" / "valid-report-complete.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("| decided |", complete)
        self.assertEqual(self.errors_for(complete), [])

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
        self.place("exact/boot-bom__boot-3.2.x/java-dependency-upgrade-report.md")
        self.place("exact/app-library__no-boot/java-dependency-upgrade-report.md")
        (self.tmp / "BATCH-INDEX.md").write_text(
            "\n".join(
                [
                    "# 批次索引",
                    "",
                    "| 目录 | 权威层 | Boot 线 | 成员 | analysis_status | decision_status | batch_implementation_gate |",
                    "|---|---|---|---|---|---|---|",
                    "| exact/boot-bom__boot-3.2.x/ | boot-bom | boot-3.2.x | jackson, netty | partial | needs_choice | frozen |",
                    "| exact/app-library__no-boot/ | app-library | no-boot | lucene | partial | needs_choice | frozen |",
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

    def test_illegal_layer_and_boot_line(self) -> None:
        self.place("exact/mystery__3.2.x/java-dependency-upgrade-report.md")
        self.place("exact/app-library__no-boot/java-dependency-upgrade-report.md")
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

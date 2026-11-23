"""Regression tests for the reviewed parser, gate, and contract fixes.

Each test names an observable behavior that was wrong. They are expected to fail
until the corresponding implementation lands.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_upgrade_report.py"
SPEC = importlib.util.spec_from_file_location("frontend_upgrade_review_fixes", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

RUNNER_SPEC = importlib.util.spec_from_file_location(
    "frontend_upgrade_review_runner", ROOT / "scripts" / "run_with_compatible_node.py"
)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = RUNNER
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)

MIGRATION_SPEC = importlib.util.spec_from_file_location(
    "frontend_upgrade_review_migration", ROOT / "scripts" / "generate_migration_demand_diff.py"
)
MIGRATION = importlib.util.module_from_spec(MIGRATION_SPEC)
sys.modules[MIGRATION_SPEC.name] = MIGRATION
assert MIGRATION_SPEC.loader is not None
MIGRATION_SPEC.loader.exec_module(MIGRATION)

HOST = ("20.18.0", "C:/node/node.exe")
MANAGERS = (["nvm-windows"], {"nvm-windows": ["20.18.0"]})


def run_main(argv: list[object], *, host: str = "20.18.0", managers=MANAGERS) -> int:
    with (
        patch.object(MODULE, "current_host_node_runtime", return_value=(host, HOST[1])),
        patch.object(MODULE, "detect_node_managers", return_value=managers),
    ):
        return MODULE.main([str(item) for item in argv])


def write_npm_project(root: Path, deps: dict[str, str], packages: dict, *, engines: str = ">=18 <21") -> None:
    (root / "package.json").write_text(
        json.dumps({"engines": {"node": engines}, "dependencies": deps}),
        encoding="utf-8",
    )
    (root / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": packages}),
        encoding="utf-8",
    )
    (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")


def read_report(out: Path) -> dict:
    return json.loads((out / "frontend-dependency-upgrade-report.json").read_text(encoding="utf-8"))


class SemverAndRuntimeTests(unittest.TestCase):
    def test_range_with_space_after_comparator_is_understood(self) -> None:
        self.assertIs(MODULE.semver_satisfies("18.2.0", ">= 18.0.0 < 20.0.0"), True)
        self.assertIs(MODULE.semver_satisfies("20.1.0", ">= 18.0.0 < 20.0.0"), False)
        self.assertIs(MODULE.semver_satisfies("18.2.0", ">= 18"), True)
        self.assertIs(MODULE.semver_satisfies("1.0.0", "> 0.9 <= 1.2"), True)

    def test_prerelease_numeric_identifiers_compare_numerically(self) -> None:
        self.assertEqual(MODULE.compare_versions("1.0.0-alpha.10", "1.0.0-alpha.2"), 1)
        self.assertEqual(MODULE.compare_versions("1.0.0-alpha.2", "1.0.0-alpha.10"), -1)

    def test_runtime_switch_required_still_offers_proceed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_npm_project(root, {"axios": "1.6.8"}, {"node_modules/axios": {"version": "1.6.8"}})
            out = root / "out"
            code = run_main(
                [root, "--upgrade", "axios::1.7.9", "--offline", "--output-dir", out, "--json-output"],
                host="26.5.0",
            )
            report = read_report(out)["reports"][0]
            self.assertEqual(code, 7)
            self.assertEqual(report["exact_upgrade_status"], "ready")
            self.assertIn("proceed:axios@1.7.9", [item["option_id"] for item in report["confirmation"]["options"]])
            self.assertFalse(any("runtime-switch-required" in item for item in report["implementation_blockers"]))


class LockParserTests(unittest.TestCase):
    def test_yarn_before_and_after_use_their_own_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            before = root / "before"
            after = root / "after"
            for directory, direct in ((before, "1.0.3"), (after, "2.0.4")):
                directory.mkdir()
                (directory / "package.json").write_text(json.dumps({
                    "dependencies": {"leaf": direct, "wrapper": "2.0.0"},
                    "engines": {"node": ">=18 <21"},
                }), encoding="utf-8")
                lock = (
                    '# yarn lockfile v1\n\nwrapper@2.0.0:\n  version "2.0.0"\n'
                    '  dependencies:\n    leaf "2.0.4"\n\nleaf@2.0.4:\n  version "2.0.4"\n'
                )
                if directory == before:
                    lock += '\nleaf@1.0.3:\n  version "1.0.3"\n'
                (directory / "yarn.lock").write_text(lock, encoding="utf-8")
            out = root / "out"
            code = run_main([
                root, "--before-package-json", before / "package.json", "--before-lock", before / "yarn.lock",
                "--after-package-json", after / "package.json", "--after-lock", after / "yarn.lock",
                "--offline", "--output-dir", out, "--json-output",
            ])
            report = read_report(out)["reports"][0]
            self.assertEqual(report["before_lock_version"], "1.0.3")
            self.assertEqual(report["after_lock_version"], "2.0.4")
            self.assertEqual(report["baseline_status"], "matches_from")
            self.assertEqual(code, 7)

    def test_npm_hoisted_workspace_direct_version_comes_from_root_node_modules(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            web = root / "apps" / "web"
            web.mkdir(parents=True)
            (web / "package.json").write_text(
                json.dumps({"name": "web", "dependencies": {"axios": "^1.6.8"}}),
                encoding="utf-8",
            )
            (root / "package.json").write_text(
                json.dumps({"private": True, "engines": {"node": ">=18 <21"}}),
                encoding="utf-8",
            )
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {
                    "": {"dependencies": {}},
                    "apps/web": {"dependencies": {"axios": "^1.6.8"}},
                    "node_modules/axios": {"version": "1.6.8"},
                },
            }), encoding="utf-8")
            out = root / "out"
            code = run_main([
                root, "--workspace-importer", "apps/web",
                "--after-package-json", web / "package.json",
                "--upgrade", "axios::1.7.9", "--offline",
                "--output-dir", out, "--json-output",
            ])
            report = read_report(out)["reports"][0]
            self.assertNotEqual(code, 3)
            self.assertEqual(report["current_lock_version"], "1.6.8")
            self.assertEqual(report["baseline_status"], "matches_from")

    def test_npm_v2_nested_workspace_version_is_not_replaced_by_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 2,
                "packages": {
                    "": {},
                    "apps/web": {"dependencies": {"axios": "^1.6.8"}},
                    "node_modules/axios": {"version": "0.21.4"},
                    "apps/web/node_modules/axios": {"version": "1.6.8"},
                },
                "dependencies": {"axios": {"version": "0.21.4"}},
            }), encoding="utf-8")
            snapshot = MODULE.parse_lock(root / "package-lock.json", ["axios"], importer="apps/web")
            self.assertEqual(snapshot.direct_versions.get("axios"), "1.6.8")

    def test_yarn_v1_uses_manifest_selector_when_several_versions_exist(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18 <21"},
                "dependencies": {"axios": "^1.6.8"},
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            (root / "yarn.lock").write_text(
                "# yarn lockfile v1\n\n"
                "axios@^0.21.0:\n  version \"0.21.4\"\n\n"
                "axios@^1.6.8:\n  version \"1.6.8\"\n",
                encoding="utf-8",
            )
            out = root / "out"
            code = run_main([root, "--upgrade", "axios::1.7.9", "--offline", "--output-dir", out, "--json-output"])
            report = read_report(out)["reports"][0]
            self.assertNotEqual(code, 3, "multiple yarn versions must not make the baseline unknown")
            self.assertEqual(report["upgrade"]["from_version"], "1.6.8")

    def test_yarn_berry_reads_colon_version(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18 <21"},
                "dependencies": {"axios": "^1.6.8"},
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            (root / "yarn.lock").write_text(
                '__metadata:\n  version: 8\n\n'
                '"axios@npm:^1.6.8":\n  version: 1.6.8\n  resolution: "axios@npm:1.6.8"\n'
                "  dependencies:\n    follow-redirects: \"npm:^1.15.6\"\n  languageName: node\n",
                encoding="utf-8",
            )
            out = root / "out"
            run_main([root, "--upgrade", "axios::1.7.9", "--offline", "--output-dir", out, "--json-output"])
            report = read_report(out)["reports"][0]
            self.assertEqual(report["upgrade"]["from_version"], "1.6.8")
            graph = MODULE.build_dependency_graph(root / "yarn.lock", {"axios"})
            self.assertNotIn("follow-redirects:", graph.dependents)
            self.assertTrue(any(edge.parent == "axios" for edge in graph.dependents.get("follow-redirects", [])))

    def test_bun_keeps_scoped_package_names_and_jsonc_format(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            lock = root / "bun.lock"
            lock.write_text(
                '{\n  "lockfileVersion": 1,\n'
                '  "workspaces": { "": { "dependencies": { "@vue/shared": "^3.4.0" } } },\n'
                '  "packages": {\n'
                '    "@vue/shared": ["@vue/shared@3.4.0", "", {}, "sha512-a"],\n'
                '  },\n}\n',
                encoding="utf-8",
            )
            snapshot = MODULE.parse_lock(lock, ["@vue/shared"])
            self.assertEqual(snapshot.direct_versions.get("@vue/shared"), "3.4.0")
            self.assertEqual(RUNNER.read_lockfile_format(lock), "1")

    def test_pnpm_snapshot_pin_does_not_block_exact_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18 <21"},
                "dependencies": {"axios": "^1.6.8", "follow-redirects": "^1.15.6"},
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            (root / "pnpm-lock.yaml").write_text(
                "lockfileVersion: '9.0'\n\nimporters:\n\n  .:\n    dependencies:\n"
                "      axios:\n        specifier: ^1.6.8\n        version: 1.6.8\n"
                "      follow-redirects:\n        specifier: ^1.15.6\n        version: 1.15.6\n\n"
                "snapshots:\n\n  axios@1.6.8:\n    dependencies:\n      follow-redirects: 1.15.6\n\n"
                "  follow-redirects@1.15.6: {}\n",
                encoding="utf-8",
            )
            out = root / "out"
            run_main([
                root, "--upgrade", "follow-redirects::1.15.9", "--offline",
                "--output-dir", out, "--json-output",
            ])
            report = read_report(out)["reports"][0]
            self.assertEqual(report["exact_upgrade_status"], "ready")
            self.assertIn(
                "proceed:follow-redirects@1.15.9",
                [item["option_id"] for item in report["confirmation"]["options"]],
            )
            self.assertFalse(any("父依赖" in item for item in report["implementation_blockers"]))


class GateAndEvidenceTests(unittest.TestCase):
    def test_output_location_preserves_source_points_on_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_npm_project(root, {"axios": "1.6.8"}, {"node_modules/axios": {"version": "1.6.8"}})
            src = root / "src"
            src.mkdir()
            (src / "main.js").write_text("import axios from 'axios';\naxios.create();\n", encoding="utf-8")
            argv = [root, "--upgrade", "axios::1.7.9", "--offline", "--json-output"]
            out = root / "reports"
            run_main([*argv, "--output-dir", out])
            expected = read_report(out)["code_points"]
            self.assertIn("src/main.js", {point["file"] for point in expected})
            for destination in (root, src):
                with self.subTest(destination=destination.name):
                    for _ in range(2):
                        run_main([*argv, "--output-dir", destination])
                        self.assertEqual(read_report(destination)["code_points"], expected)
            custom = src / "upgrade-review.json"
            for _ in range(2):
                run_main([*argv, custom, "--output-dir", root])
                self.assertEqual(json.loads(custom.read_text(encoding="utf-8"))["code_points"], expected)

    def test_schema_example_and_node_runtime_only_evidence_load(self) -> None:
        doc = (ROOT / "references" / "analysis-evidence-schema.md").read_text(encoding="utf-8")
        example = json.loads(doc.split("```json", 1)[1].split("```", 1)[0])
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "evidence.json"
            path.write_text(json.dumps(example), encoding="utf-8")
            loaded = MODULE.load_analysis_evidence(path)
            report = MODULE.PackageReport(
                MODULE.Upgrade("legacy-client", "", "", intent="auto-assess"),
                "",
            )
            MODULE.apply_analysis_evidence([report], loaded)
            self.assertEqual(report.alternative_candidates[0].compliance_status, "eligible")
            path.write_text(json.dumps({"node_runtime": {"selected_project_node": "16.20.2"}}), encoding="utf-8")
            self.assertEqual(MODULE.load_analysis_evidence(path), {})

    def test_choice_not_rendered_in_the_queue_is_invalid(self) -> None:
        blocked = MODULE.PackageReport(MODULE.Upgrade("legacy", "1.0.0", "", intent="auto-assess"), "")
        blocked.confirmation = MODULE.ConfirmationQuestion(package="legacy", track="pending-removal-evidence", status="blocked")
        blocked.removal.status = "uncertain"
        reason = MODULE.revalidate_decision(
            blocked,
            MODULE.HumanDecision(package="legacy", choice="remove"),
        )
        self.assertIn("确认队列", reason)

        ready = MODULE.PackageReport(MODULE.Upgrade("legacy", "1.0.0", "", intent="auto-assess"), "")
        ready.confirmation = MODULE.ConfirmationQuestion(
            package="legacy",
            track="remove",
            options=[MODULE.ConfirmationOption("remove", "确认删除"), MODULE.ConfirmationOption("other", "其他")],
        )
        ready.removal.status = "safe_removal_candidate"
        self.assertEqual(
            MODULE.revalidate_decision(ready, MODULE.HumanDecision(package="legacy", choice="remove")),
            "",
        )
        other = MODULE.revalidate_decision(
            blocked,
            MODULE.HumanDecision(package="legacy", choice="remove", source="other"),
        )
        self.assertEqual(other, "")

    def test_explicit_decision_file_survives_a_mixed_batch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_npm_project(
                root,
                {"axios": "1.6.8", "legacy": "1.0.0"},
                {
                    "node_modules/axios": {"version": "1.6.8"},
                    "node_modules/legacy": {"version": "1.0.0"},
                },
            )
            (root / "src").mkdir()
            (root / "src" / "a.ts").write_text("import axios from 'axios';\nimport legacy from 'legacy';\n", encoding="utf-8")
            decisions = root / "human-decisions.json"
            decisions.write_text(json.dumps({"decisions": [{
                "package": "axios",
                "track": "proceed-exact",
                "choice": "proceed:axios@1.7.9",
            }]}), encoding="utf-8")
            out = root / "out"
            run_main([
                root, "--upgrade", "axios::1.7.9", "--assess", "legacy", "--offline",
                "--decision-file", decisions, "--output-dir", out, "--json-output",
            ])
            exact = json.loads((out / "exact" / "frontend-dependency-upgrade-report.json").read_text(encoding="utf-8"))
            self.assertEqual(exact["reports"][0]["decision"]["status"], "confirmed")
            self.assertEqual(exact["decision_status"], "not_needed")
            self.assertFalse(any("unknown-package" in item for item in exact["decision_warnings"]))

    def test_code_scan_skips_evidence_decision_and_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_npm_project(root, {"legacy": "1.0.0"}, {"node_modules/legacy": {"version": "1.0.0"}})
            (root / "src").mkdir()
            (root / "src" / "a.ts").write_text("import legacy from 'legacy';\n", encoding="utf-8")
            evidence = root / "dependency-analysis-evidence.json"
            evidence.write_text(json.dumps({"packages": {"legacy": {"reason": "停止维护"}}}), encoding="utf-8")
            out = root / "analysis-out"
            argv = [
                root, "--assess", "legacy", "--offline",
                "--analysis-evidence-file", evidence,
                "--output-dir", out, "--json-output",
            ]
            run_main(argv)
            run_main(argv)
            data = read_report(out)
            files = {point["file"] for point in data["code_points"]}
            self.assertIn("src/a.ts", files)
            self.assertFalse(any("dependency-analysis-evidence.json" in item for item in files))
            self.assertFalse(any(item.startswith("analysis-out/") for item in files))

    def test_researched_no_candidate_and_chinese_summary_are_rendered(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_npm_project(root, {"legacy": "1.0.0"}, {"node_modules/legacy": {"version": "1.0.0"}})
            (root / "src").mkdir()
            (root / "src" / "a.ts").write_text("import legacy from 'legacy';\nlegacy();\n", encoding="utf-8")
            evidence = root / "evidence.json"
            evidence.write_text(json.dumps({"packages": {"legacy": {
                "research_conclusion": "no-candidate",
                "reviewed_summary": "上游已归档，本仓库没有可替换的合规包。",
                "mapped_flows": ["订单提交 /src/a.ts"],
            }}}), encoding="utf-8")
            out = root / "out"
            run_main([
                root, "--assess", "legacy", "--offline",
                "--analysis-evidence-file", evidence,
                "--output-dir", out, "--json-output",
            ])
            data = read_report(out)
            report = data["reports"][0]
            text = (out / "frontend-dependency-upgrade-report.md").read_text(encoding="utf-8")
            self.assertEqual(report["research_status"], "reviewed")
            self.assertIn("上游已归档，本仓库没有可替换的合规包。", text)
            self.assertIn("订单提交 /src/a.ts", text)

    def test_complete_report_does_not_repeat_the_draft_remaining_work_line(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_npm_project(root, {"axios": "1.6.8"}, {"node_modules/axios": {"version": "1.6.8"}}, engines=">=18")
            (root / "src").mkdir()
            (root / "src" / "main.js").write_text("import axios from 'axios'\n", encoding="utf-8")
            decisions = root / "human-decisions.json"
            decisions.write_text(json.dumps({"decisions": [{
                "package": "axios", "track": "proceed-exact", "choice": "proceed:axios@1.7.9",
            }]}), encoding="utf-8")
            out = root / "out"
            metadata = {
                "versions": {
                    "1.6.8": {"version": "1.6.8"},
                    "1.7.9": {"version": "1.7.9"},
                },
                "time": {"1.6.8": "2024-01-01T00:00:00.000Z", "1.7.9": "2024-06-01T00:00:00.000Z"},
            }
            args = [
                root, "--upgrade", "axios:1.6.8:1.7.9", "--decision-file", decisions,
                "--output-dir", out, "--finalize-review", "--no-upstream-evidence", "--json-output",
            ]
            with (
                patch.object(MODULE, "ensure_network_reachability", return_value={"network_reachability": "ok"}),
                patch.object(MODULE, "request_json", return_value=metadata),
                patch.object(MODULE, "request_text", return_value=None),
                patch.object(MODULE, "probe_http_reachable", return_value=True),
            ):
                code = run_main(args)
            text = (out / "frontend-dependency-upgrade-report.md").read_text(encoding="utf-8")
            self.assertEqual(code, 0)
            self.assertEqual(read_report(out)["analysis_status"], "complete")
            self.assertNotIn("剩余工作：标记为 `complete` 前", text)

    def test_npm_dedupe_pkg_set_and_audit_fix_count_as_lock_mutations(self) -> None:
        for command in ('npm dedupe', 'npm pkg set "overrides.axios=1.7.9"', "npm audit fix"):
            self.assertEqual(RUNNER.classify_command(command), "dependency-install-or-upgrade", command)
            self.assertTrue(RUNNER.NPM_MUTATING_RE.search(command), command)


class MigrationDemandDiffFixTests(unittest.TestCase):
    def _pair(self, root: Path) -> tuple[Path, Path]:
        source = root / "A"
        host = root / "B"
        source.mkdir()
        host.mkdir()
        (source / "package.json").write_text(json.dumps({
            "dependencies": {"axios": "^0.21.0", "left-pad": "^1.3.0"},
            "devDependencies": {"webpack": "^4.46.0"},
        }), encoding="utf-8")
        (host / "package.json").write_text(json.dumps({
            "dependencies": {"vue": "^3.4.0", "axios": "^1.6.0"},
        }), encoding="utf-8")
        (host / "package-lock.json").write_text(json.dumps({
            "lockfileVersion": 3,
            "packages": {
                "": {"dependencies": {"vue": "^3.4.0", "axios": "^1.6.0"}},
                "node_modules/vue": {"version": "3.4.21"},
                "node_modules/axios": {"version": "1.6.8"},
                "node_modules/lodash": {"version": "4.17.21"},
            },
        }), encoding="utf-8")
        return source, host

    def _rows(
        self, root: Path, extra: list[str], pair: tuple[Path, Path] | None = None,
    ) -> tuple[int, dict, list[dict]]:
        source, host = pair or self._pair(root)
        out = root / "out"
        code = MIGRATION.main([
            "--source-root", str(source),
            "--implementation-target", str(host),
            "--output-dir", str(out),
            *extra,
        ])
        summary = json.loads((out / "dependency-summary.json").read_text(encoding="utf-8"))
        rows = json.loads((out / "demand-diff.json").read_text(encoding="utf-8"))["packages"]
        return code, summary, rows

    def test_closure_keeps_names_missing_from_source_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            closure = root / "pkgs.txt"
            closure.write_text("axios\nlocal-vendor-lib\n", encoding="utf-8")
            _code, _summary, rows = self._rows(root, ["--closure-packages", str(closure)])
            self.assertEqual(sorted(row["package"] for row in rows), ["axios", "local-vendor-lib"])

    def test_transitive_host_package_is_not_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            closure = root / "pkgs.txt"
            closure.write_text("lodash\n", encoding="utf-8")
            _code, _summary, rows = self._rows(root, ["--closure-packages", str(closure)])
            self.assertEqual(rows[0]["disposition"], "add-to-B")
            self.assertNotIn("4.17.21", rows[0]["b_status"])

    def test_yarn_host_reuse_requires_a_direct_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, host = self._pair(root)
            (host / "package-lock.json").unlink()
            (host / "yarn.lock").write_text(
                '# yarn lockfile v1\n\naxios@^1.6.0:\n  version "1.6.8"\n'
                '  dependencies:\n    left-pad "^1.3.0"\n\nleft-pad@^1.3.0:\n  version "1.3.0"\n'
                '\naxios@^0.21.0:\n  version "0.21.4"\n', encoding="utf-8",
            )
            closure = root / "closure.txt"
            closure.write_text("left-pad\n", encoding="utf-8")
            code, summary, rows = self._rows(root, ["--closure-packages", str(closure)], (source, host))
            self.assertEqual(rows[0]["disposition"], "add-to-B")
            self.assertEqual(rows[0]["queue_status"], "ready")
            self.assertEqual(code, 7)
            self.assertEqual(summary["batch_implementation_gate"], "frozen")
            closure.write_text("axios\n", encoding="utf-8")
            _, _, rows = self._rows(root, ["--closure-packages", str(closure)], (source, host))
            self.assertEqual(rows[0]["b_status"], "present@1.6.8")

    def test_saved_reuse_is_reopened_when_host_loses_the_package(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, host = self._pair(root)
            closure = root / "closure.txt"
            closure.write_text("axios\n", encoding="utf-8")
            decisions = root / "decisions.json"
            args = ["--closure-packages", str(closure), "--decision-file", str(decisions)]
            decisions.write_text(json.dumps({"axios": "proceed:demand:axios:reuse-B-major-review"}), encoding="utf-8")
            code, summary, _ = self._rows(root, args, (source, host))
            self.assertEqual((code, summary["batch_implementation_gate"]), (0, "ready"))
            write_npm_project(host, {"vue": "^3.4.0"}, {"node_modules/vue": {"version": "3.4.21"}})
            for stale in ("reuse-B", "reuse-B-major-review"):
                with self.subTest(stale=stale):
                    decisions.write_text(json.dumps({"axios": f"proceed:demand:axios:{stale}"}), encoding="utf-8")
                    code, summary, rows = self._rows(root, args, (source, host))
                    self.assertEqual((rows[0]["b_status"], rows[0]["disposition"]), ("absent", "add-to-B"))
                    self.assertEqual(rows[0]["queue_status"], "ready")
                    self.assertEqual((code, summary["batch_implementation_gate"]), (7, "frozen"))
            for choice in ("add-to-B", "copy-local"):
                with self.subTest(choice=choice):
                    decisions.write_text(json.dumps({"axios": f"proceed:demand:axios:{choice}"}), encoding="utf-8")
                    code, summary, rows = self._rows(root, args, (source, host))
                    self.assertEqual(rows[0]["disposition"], choice)
                    self.assertEqual((code, summary["batch_implementation_gate"]), (0, "ready"))

    def test_loose_proceed_prefix_does_not_decide_and_defer_freezes_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            decisions = root / "decisions.json"
            decisions.write_text(json.dumps({
                "axios": "proceed:全部放行",
                "left-pad": "defer",
                "webpack": "defer",
            }), encoding="utf-8")
            code, summary, rows = self._rows(root, ["--decision-file", str(decisions)])
            by_name = {row["package"]: row for row in rows}
            self.assertEqual(code, 7)
            self.assertEqual(by_name["axios"]["queue_status"], "ready")
            self.assertEqual(summary["batch_implementation_gate"], "frozen")

    def test_valid_token_rewrites_disposition_and_clears_to_not_needed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            decisions = root / "decisions.json"
            decisions.write_text(json.dumps({
                "axios": "proceed:demand:axios:reuse-B-major-review",
                "left-pad": "proceed:demand:left-pad:add-to-B",
                "webpack": "proceed:demand:webpack:add-to-B",
            }), encoding="utf-8")
            code, summary, rows = self._rows(root, ["--decision-file", str(decisions)])
            by_name = {row["package"]: row for row in rows}
            self.assertEqual(code, 0)
            self.assertEqual(summary["decision_status"], "not_needed")
            self.assertEqual(summary["batch_implementation_gate"], "ready")
            self.assertEqual(by_name["axios"]["disposition"], "reuse-B-major-review")

    def test_missing_host_vue_is_not_reported_as_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "A"
            host = root / "B"
            source.mkdir()
            host.mkdir()
            (source / "package.json").write_text(json.dumps({"dependencies": {"vue": "^2.6.10"}}), encoding="utf-8")
            (host / "package.json").write_text(json.dumps({"dependencies": {"axios": "^1.6.0"}}), encoding="utf-8")
            (host / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {
                    "": {"dependencies": {"axios": "^1.6.0"}},
                    "node_modules/axios": {"version": "1.6.8"},
                },
            }), encoding="utf-8")
            out = root / "out"
            MIGRATION.main([
                "--source-root", str(source), "--implementation-target", str(host), "--output-dir", str(out),
            ])
            rows = json.loads((out / "demand-diff.json").read_text(encoding="utf-8"))["packages"]
            self.assertNotEqual(rows[0]["disposition"], "reuse-B")


class DocumentContractTests(unittest.TestCase):
    def test_description_stays_within_the_skill_limit_and_names_non_goals(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        description = re.search(r"description: >\n(.*?)---", text, re.S)
        self.assertIsNotNone(description)
        body = " ".join(line.strip() for line in description.group(1).splitlines()).strip()
        self.assertLessEqual(len(body), 1024)
        self.assertIn("post-upgrade CSS", body)
        self.assertIn("page-level migration", body)

    def test_generator_examples_separate_skill_dir_from_project_root(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("<skill-dir>/scripts/generate_upgrade_report.py", text)
        self.assertIn("<project-root>", text)
        self.assertNotIn("python scripts/generate_upgrade_report.py .", text)

    def test_report_contract_matches_rendered_column_and_option_gate(self) -> None:
        contract = (ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        discovery = (ROOT / "references" / "target-discovery-and-removal.md").read_text(encoding="utf-8")
        runtime = (ROOT / "references" / "node-runtime-compatibility.md").read_text(encoding="utf-8")
        risk = (ROOT / "references" / "risk-model.md").read_text(encoding="utf-8")
        self.assertIn("其他可选版本", contract)
        self.assertNotIn("兼容回退版本", contract)
        self.assertNotIn("requires_migration` 的删除路径", contract)
        self.assertNotIn("requires_migration` 时算一条可执行路径", discovery)
        self.assertIn("不新增第 14 个", runtime)
        self.assertNotIn("无变化=0", risk)

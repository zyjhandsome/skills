from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_upgrade_report.py"
SPEC = importlib.util.spec_from_file_location("frontend_upgrade_report", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

RUNNER_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_with_compatible_node.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("frontend_upgrade_node_runner", RUNNER_SCRIPT)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = RUNNER
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)


class UpgradeReportTests(unittest.TestCase):
    def tearDown(self) -> None:
        MODULE.configure_http_cache(None, 0, enabled=False)

    def test_exact_upgrade_allows_from_to_be_inferred_from_lock(self) -> None:
        upgrade = MODULE.parse_upgrade_spec("axios::1.7.9")
        self.assertEqual(upgrade.package, "axios")
        self.assertEqual(upgrade.from_version, "")
        self.assertEqual(upgrade.to_version, "1.7.9")
        self.assertEqual(upgrade.intent, "exact-upgrade")

    def test_exact_upgrade_still_requires_target(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.parse_upgrade_spec("axios:0.27.2:")

    def test_package_json_diff_allows_add_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            before = root / "before.json"
            after = root / "after.json"
            before.write_text(json.dumps({"dependencies": {"old": "1.0.0"}}), encoding="utf-8")
            after.write_text(json.dumps({"dependencies": {"new": "2.0.0"}}), encoding="utf-8")
            rows = MODULE.compare_package_json(before, after)
            values = {(row.package, row.from_version, row.to_version) for row in rows}
            self.assertIn(("old", "1.0.0", ""), values)
            self.assertIn(("new", "", "2.0.0"), values)

    def test_special_manifest_diff_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            before = root / "before.json"
            after = root / "after.json"
            before.write_text(json.dumps({"overrides": {"foo": "1.0.0"}}), encoding="utf-8")
            after.write_text(json.dumps({"overrides": {"foo": "2.0.0"}, "resolutions": {"bar": "3.0.0"}}), encoding="utf-8")
            changes = MODULE.compare_special_fields(before, after)
            self.assertTrue(any("overrides" in change and "2.0.0" in change for change in changes))
            self.assertTrue(any("resolutions" in change for change in changes))

    def test_npm_lock_direct_and_duplicate_versions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "package-lock.json"
            path.write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/axios": {"version": "1.7.9"},
                    "node_modules/example/node_modules/axios": {"version": "0.27.2"},
                },
            }), encoding="utf-8")
            lock = MODULE.parse_lock(path, ["axios"])
            self.assertEqual(lock.direct_versions["axios"], "1.7.9")
            self.assertEqual(set(lock.all_versions["axios"]), {"0.27.2", "1.7.9"})

    def test_npm_v1_nested_version_is_not_direct(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "package-lock.json"
            path.write_text(json.dumps({
                "lockfileVersion": 1,
                "dependencies": {
                    "wrapper": {"version": "1.0.0", "dependencies": {"axios": {"version": "0.27.2"}}},
                    "axios": {"version": "1.7.9"},
                },
            }), encoding="utf-8")
            lock = MODULE.parse_lock(path, ["axios"])
            self.assertEqual(lock.direct_versions["axios"], "1.7.9")
            self.assertEqual(set(lock.all_versions["axios"]), {"0.27.2", "1.7.9"})

    def test_pnpm_importer_direct_version(self) -> None:
        content = """lockfileVersion: '9.0'
importers:
  .:
    dependencies:
      axios:
        specifier: 1.7.9
        version: 1.7.9
packages:
  axios@1.7.9:
    resolution: {integrity: abc}
"""
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "pnpm-lock.yaml"
            path.write_text(content, encoding="utf-8")
            lock = MODULE.parse_lock(path, ["axios"])
            self.assertEqual(lock.direct_versions["axios"], "1.7.9")
            self.assertIn("1.7.9", lock.all_versions["axios"])

    def test_yarn_single_version_resolution(self) -> None:
        content = 'axios@^1.7.0:\n  version "1.7.9"\n  resolved "https://example.invalid"\n'
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "yarn.lock"
            path.write_text(content, encoding="utf-8")
            lock = MODULE.parse_lock(path, ["axios"])
            self.assertEqual(lock.direct_versions["axios"], "1.7.9")

    def test_ui_scan_does_not_flag_unrelated_custom_component(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "src").mkdir()
            (root / "src" / "Unrelated.tsx").write_text("export const X = () => <CustomCard />;", encoding="utf-8")
            (root / "src" / "List.tsx").write_text("import { Table } from 'antd';\nexport const X = () => <Table />;", encoding="utf-8")
            report = MODULE.PackageReport(
                MODULE.Upgrade("antd", "4.24.16", "5.22.0", "ui"),
                "https://www.npmjs.com/package/antd",
                change_type="major",
            )
            points, _, _ = MODULE.analyze_code_modification_points(root, [report], 100, 100, 100_000)
            files = {point.file for point in points}
            self.assertIn("src/List.tsx", files)
            self.assertNotIn("src/Unrelated.tsx", files)

    def test_code_scan_compiles_package_regex_once_per_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "src").mkdir()
            (root / "src" / "a.ts").write_text("import axios from 'axios';", encoding="utf-8")
            (root / "src" / "b.ts").write_text("import axios from 'axios';", encoding="utf-8")
            report = MODULE.PackageReport(
                MODULE.Upgrade("axios", "0.27.2", "1.7.9", "request"),
                "https://www.npmjs.com/package/axios",
                change_type="major",
            )
            original = MODULE.package_reference_regex
            with patch.object(MODULE, "package_reference_regex", wraps=original) as compile_regex:
                MODULE.analyze_code_modification_points(root, [report], 100, 100, 100_000)
            self.assertEqual(compile_regex.call_count, 1)

    def test_side_effect_import_is_a_direct_reference(self) -> None:
        regex = MODULE.package_reference_regex("antd")
        self.assertRegex("import 'antd/dist/reset.css';", regex)

    def test_markdown_table_split_preserves_escaped_pipe(self) -> None:
        self.assertEqual(MODULE.split_markdown_row("| a \\| b | c |"), ["a | b", "c"])

    def test_seven_factor_risk_is_reproducible(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "0.27.2", "1.7.9", "request"),
            "https://www.npmjs.com/package/axios",
            change_type="major",
            baseline_status="matches_from",
            observed_lock_versions=["0.27.2"],
            evidence_completeness="complete",
        )
        point = MODULE.CodeModificationPoint(
            "axios", "src/auth/request.ts", 1, "Direct package usage", "import axios from 'axios'",
            "official evidence", "review", "test auth", "P0", "high",
        )
        risk = MODULE.risk_score(report, [point], [], "auto", "auto")
        self.assertEqual(risk.total, sum(risk.factors.values()))
        self.assertEqual(risk.final_level, "High")
        self.assertEqual(set(risk.factors), {
            "version_change", "dependency_type", "usage_scope", "business_criticality",
            "lockfile_change", "test_coverage_gap", "peer_compatibility",
        })

    def test_version_repository_takes_precedence_over_top_level(self) -> None:
        metadata = {
            "repository": {"url": "git+https://github.com/vuejs/core.git"},
            "versions": {
                "2.7.16": {"repository": {"url": "git+https://github.com/vuejs/vue.git"}},
                "3.5.18": {"repository": {"url": "git+https://github.com/vuejs/core.git", "directory": "packages/vue"}},
            },
        }
        self.assertEqual(
            MODULE.repository_details_for_version(metadata, "2.7.16"),
            ("git+https://github.com/vuejs/vue.git", "", "npm-version-metadata"),
        )
        self.assertEqual(
            MODULE.repository_details_for_version(metadata, "3.5.18"),
            ("git+https://github.com/vuejs/core.git", "packages/vue", "npm-version-metadata"),
        )

    def test_changelog_extraction_handles_atx_setext_and_index_markers(self) -> None:
        atx = "# Changes\n\n## [2.7.16] (2023-12-24)\n\nVue fix\n\n## [2.7.15]\nOld"
        setext = "Version 4.1.0\n-------------\nVuex fix\n\nVersion 4.0.2\n-------------\nOld"
        index = "# Changelog\n\n* [jQuery 3.7.1](https://blog.jquery.com/release-3-7-1/)\n"
        self.assertIn("Vue fix", MODULE.extract_changelog_section(atx, "2.7.16", 1000))
        self.assertIn("Vuex fix", MODULE.extract_changelog_section(setext, "4.1.0", 1000))
        self.assertIn("blog.jquery.com", MODULE.extract_changelog_section(index, "3.7.1", 1000))

    def test_changelog_discovery_handles_default_dev_branch_and_localized_name(self) -> None:
        seen: list[str] = []

        def fake_request(url: str, timeout: int, attempts: int = 2) -> str | None:
            seen.append(url)
            return "# 2.10.4\nA sufficiently long fix description." if url.endswith("/dev/CHANGELOG.en-US.md") else None

        with patch.object(MODULE, "request_json", return_value={}), patch.object(MODULE, "request_text", side_effect=fake_request):
            text, url = MODULE.fetch_changelog("element-plus/element-plus", "", 1, default_branch="dev")
        self.assertIn("2.10.4", text)
        self.assertTrue(url.endswith("/dev/CHANGELOG.en-US.md"))
        self.assertTrue(any("CHANGELOG.en-US.md" in candidate for candidate in seen))

    def test_historical_changelog_reuses_known_path_before_tree_search(self) -> None:
        historical = "## 1.2.3\nHistorical release details.\n"
        with (
            patch.object(MODULE, "request_text", return_value=historical) as request,
            patch.object(MODULE, "fetch_changelog") as fallback,
        ):
            text, url, section = MODULE.resolve_historical_changelog(
                "owner/repo",
                "pkg",
                "1.2.3",
                "",
                {"gitHead": "commit-123"},
                "main",
                "# Changelog\n",
                "https://raw.githubusercontent.com/owner/repo/main/CHANGELOG.md",
                1,
                1000,
            )
        self.assertEqual(request.call_count, 1)
        fallback.assert_not_called()
        self.assertIn("commit-123/CHANGELOG.md", url)
        self.assertIn("Historical release details", text)
        self.assertIn("Historical release details", section)

    def test_monorepo_release_does_not_fall_back_to_unrelated_same_semver(self) -> None:
        releases = [
            {"tag_name": "compiler@1.2.3", "name": "compiler 1.2.3", "body": "x" * 100, "html_url": "https://example.test/compiler"},
            {"tag_name": "runtime@1.2.3", "name": "runtime 1.2.3", "body": "y" * 100, "html_url": "https://example.test/runtime"},
        ]
        with patch.object(MODULE, "request_json", return_value=releases):
            selected = MODULE.fetch_github_releases("owner/repo", "unknown-package", 1, 1, "packages/unknown")
        self.assertEqual(selected["1.2.3"]["status"], "ambiguous")

    def test_github_release_fetch_stops_after_target_versions_are_found(self) -> None:
        first_page = [
            {
                "tag_name": "pkg@1.2.3",
                "name": "pkg 1.2.3",
                "body": "release details " * 10,
                "html_url": "https://example.test/pkg-1.2.3",
            },
            *[
                {
                    "tag_name": f"pkg@0.0.{index}",
                    "name": f"pkg 0.0.{index}",
                    "body": "release details " * 10,
                    "html_url": f"https://example.test/pkg-0.0.{index}",
                }
                for index in range(99)
            ],
        ]
        with patch.object(MODULE, "request_json", return_value=first_page) as request:
            selected = MODULE.fetch_github_releases(
                "owner/repo", "pkg", 1, 5, target_versions=["1.2.3"]
            )
        self.assertEqual(request.call_count, 1)
        self.assertIn("1.2.3", selected)
        self.assertNotIn("_collection", selected)

    def test_http_cache_reuses_success_and_stable_miss(self) -> None:
        class Headers:
            @staticmethod
            def get_content_charset() -> str:
                return "utf-8"

        class Response:
            headers = Headers()

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *_: object) -> None:
                return None

            @staticmethod
            def read() -> bytes:
                return b'{"ok": true}'

        with tempfile.TemporaryDirectory() as raw:
            MODULE.configure_http_cache(raw, 3600)
            with patch.object(MODULE.urllib.request, "urlopen", return_value=Response()) as urlopen:
                self.assertEqual(MODULE.request_text("https://example.test/data", 1), '{"ok": true}')
                self.assertEqual(MODULE.request_text("https://example.test/data", 1), '{"ok": true}')
            self.assertEqual(urlopen.call_count, 1)

            MODULE.configure_http_cache(raw, 3600)
            with patch.object(MODULE.urllib.request, "urlopen", side_effect=AssertionError("network used")):
                self.assertEqual(MODULE.request_text("https://example.test/data", 1), '{"ok": true}')

            missing = MODULE.urllib.error.HTTPError(
                "https://example.test/missing", 404, "not found", None, None
            )
            with patch.object(MODULE.urllib.request, "urlopen", side_effect=missing) as urlopen:
                self.assertIsNone(MODULE.request_text("https://example.test/missing", 1))
                self.assertIsNone(MODULE.request_text("https://example.test/missing", 1))
            self.assertEqual(urlopen.call_count, 1)

    def test_version_repository_validation_runs_concurrently_and_keeps_order(self) -> None:
        metadata = {
            "default_branch": "main",
            "repository": {"url": "git+https://github.com/owner/pkg.git"},
            "versions": {
                version: {
                    "repository": {"url": "git+https://github.com/owner/pkg.git"},
                    "gitHead": f"commit-{version}",
                }
                for version in ("1.0.0", "1.1.0", "1.2.0", "1.3.0")
            },
            "time": {},
        }
        releases = {
            version: {
                "body": "release details " * 10,
                "url": f"https://example.test/{version}",
                "published": "",
                "name": version,
                "tag": f"v{version}",
                "source_kind": "github-release",
                "status": "substantive",
                "pointer_urls": [],
            }
            for version in ("1.1.0", "1.2.0", "1.3.0")
        }
        changelog = "\n".join(
            f"## {version}\nChanges for {version}\n"
            for version in ("1.1.0", "1.2.0", "1.3.0")
        )
        lock = threading.Lock()
        active = 0
        max_active = 0

        def validate(*_: object) -> tuple[str, str, str]:
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.02)
            with lock:
                active -= 1
            return "confirmed", "test", ""

        args = MODULE.parse_args([
            ".", "--upgrade", "pkg:1.0.0:1.3.0", "--network-workers", "3",
        ])
        with (
            patch.object(MODULE, "request_json", return_value=metadata),
            patch.object(MODULE, "validate_version_repository", side_effect=validate),
            patch.object(MODULE, "fetch_github_releases", return_value=releases),
            patch.object(MODULE, "fetch_changelog", return_value=(changelog, "https://example.test/changelog")),
        ):
            report = MODULE.collect_package_report(
                MODULE.Upgrade("pkg", "1.0.0", "1.3.0"),
                args,
            )
        self.assertGreaterEqual(max_active, 2)
        self.assertEqual([note.version for note in report.notes], ["1.1.0", "1.2.0", "1.3.0"])

    def test_batch_packages_share_worker_budget_and_keep_order(self) -> None:
        lock = threading.Lock()
        active = 0
        max_active = 0

        def collect(upgrade: object, args: object) -> object:
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.02)
            with lock:
                active -= 1
            return upgrade

        upgrades = [
            MODULE.Upgrade("a", "1.0.0", "1.1.0"),
            MODULE.Upgrade("b", "1.0.0", "1.1.0"),
            MODULE.Upgrade("c", "1.0.0", "1.1.0"),
        ]
        args = MODULE.parse_args([
            ".", "--upgrade", "a:1.0.0:1.1.0", "--network-workers", "6",
        ])
        with patch.object(MODULE, "collect_package_report", side_effect=collect):
            reports = MODULE.collect_package_reports(upgrades, args)
        self.assertGreaterEqual(max_active, 2)
        self.assertEqual([report.package for report in reports], ["a", "b", "c"])

    def test_report_validator_detects_markdown_table_column_mismatch(self) -> None:
        markdown = "| A | B |\n|---|---|\n| only-one |\n"
        self.assertTrue(MODULE.markdown_table_errors(markdown))

    def test_release_page_candidate_rejects_pr_and_accepts_official_blog(self) -> None:
        self.assertFalse(MODULE.is_release_page_candidate("https://github.com/vuejs/vuex/pull/1883"))
        self.assertFalse(MODULE.is_release_page_candidate("https://github.com/vuejs/vuex/commit/abcdef"))
        self.assertTrue(MODULE.is_release_page_candidate("https://blog.jquery.com/2023/jquery-3-7-1-released/"))

    def test_peer_compatibility_detects_vuex4_vue2_conflict(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("vuex", "3.6.2", "4.1.0", "state"),
            "https://www.npmjs.com/package/vuex",
            target_peer_dependencies={"vue": "^3.2.0"},
        )
        lock = MODULE.LockSnapshot(direct_versions={"vue": "2.7.16"})
        MODULE.assess_peer_compatibility(report, MODULE.ManifestSnapshot(), MODULE.LockSnapshot(), lock, MODULE.LockSnapshot())
        self.assertEqual(report.peer_compatibility_status, "incompatible")
        self.assertTrue(any("不满足" in conflict for conflict in report.peer_compatibility_conflicts))

    def test_semver_range_checks_all_comparators(self) -> None:
        self.assertTrue(MODULE.semver_satisfies("2.7.16", ">=2 <3"))
        self.assertFalse(MODULE.semver_satisfies("3.2.0", ">=2 <3"))
        self.assertTrue(MODULE.semver_satisfies("2.5.0", "2.0.0 - 2.9.9"))
        self.assertTrue(MODULE.semver_satisfies("16.20.2", "<=16"))
        self.assertFalse(MODULE.semver_satisfies("17.0.0", "<=16"))

    def test_node_runtime_switches_when_host_node_conflicts_with_project(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = MODULE.ManifestSnapshot(
                path=str(root / "package.json"),
                engines={"node": "<=16"},
            )
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["16.20.2"]})),
            ):
                runtime = MODULE.assess_node_runtime(root, manifest, [])
            self.assertEqual(runtime.status, "runtime-switch-required")
            self.assertEqual(runtime.execution_readiness, "ready-awaiting-approval")
            self.assertEqual(runtime.current_host_node, "20.18.0")
            self.assertEqual(runtime.selected_project_node, "16.20.2")
            self.assertTrue(any("EOL" in warning for warning in runtime.warnings))

    def test_node_runtime_detects_toolchain_metadata_without_special_casing_orchestrators(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrator = root / "node_modules" / "orchestration-helper"
            vite = root / "node_modules" / "vite"
            orchestrator.mkdir(parents=True)
            vite.mkdir(parents=True)
            (orchestrator / "package.json").write_text(json.dumps({
                "name": "orchestration-helper", "version": "1.0.0", "engines": {"node": ">=20"},
            }), encoding="utf-8")
            (vite / "package.json").write_text(json.dumps({
                "name": "vite", "version": "2.9.0", "engines": {"node": "<=16"},
            }), encoding="utf-8")
            manifest = MODULE.ManifestSnapshot(
                packages={
                    "orchestration-helper": MODULE.ManifestPackage("orchestration-helper", "devDependencies", "1.0.0"),
                    "vite": MODULE.ManifestPackage("vite", "devDependencies", "2.9.0"),
                },
                engines={"node": "<=16"},
            )
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["16.20.2"]})),
            ):
                runtime = MODULE.assess_node_runtime(root, manifest, [])
            self.assertTrue(any(item.kind == "toolchain-engine" for item in runtime.observed_runtime_evidence))
            self.assertFalse(any("orchestration-helper" in item.source for item in runtime.observed_runtime_evidence))
            self.assertEqual(runtime.status, "runtime-switch-required")
            self.assertNotIn("control_plane_requirement", MODULE.asdict(runtime))

    def test_lock_confirmed_toolchain_engine_can_define_project_node_range(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            vite = root / "node_modules" / "vite"
            vite.mkdir(parents=True)
            (vite / "package.json").write_text(json.dumps({
                "name": "vite", "version": "2.9.0", "engines": {"node": "<=16"},
            }), encoding="utf-8")
            manifest = MODULE.ManifestSnapshot(
                packages={"vite": MODULE.ManifestPackage("vite", "devDependencies", "2.9.0")},
            )
            lock = MODULE.LockSnapshot(
                kind="npm",
                direct_versions={"vite": "2.9.0"},
            )
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["16.20.2"]})),
            ):
                runtime = MODULE.assess_node_runtime(root, manifest, [], lock=lock)
            self.assertEqual(runtime.status, "runtime-switch-required")
            self.assertTrue(any(
                item.kind == "toolchain-engine" and item.authority == "authoritative"
                for item in runtime.project_constraints
            ))

    def test_resolve_frontend_workspace_fails_without_package_json(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            args = MODULE.parse_args([str(root), "--upgrade", "axios::1.7.9", "--offline"])
            resolution = MODULE.resolve_frontend_workspace(root, args)
            self.assertEqual(resolution.status, "failed")
            self.assertTrue(resolution.reason)

    def test_build_bundle_blocks_when_frontend_workspace_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            args = MODULE.parse_args([
                str(root), "--upgrade", "axios::1.7.9", "--offline",
                "--output-dir", str(root / "out"),
            ])
            bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.importer_resolution, "failed")
            self.assertEqual(bundle.analysis_status, "blocked")
            self.assertEqual(bundle.status, "blocked")
            self.assertEqual(bundle.reports[0].change_type, "unknown")
            self.assertNotEqual(bundle.reports[0].recommended_action, "upgrade")
            self.assertTrue(any(item.get("package") == "__frontend_workspace__" for item in bundle.pending_human_decisions))
            self.assertEqual(bundle.node_runtime.selected_project_node, "")
            markdown = MODULE.markdown_report(bundle)
            self.assertIn("前端 workspace 解析：`failed`", markdown)

    def test_main_returns_5_when_frontend_workspace_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            code = MODULE.main([
                str(root), "--upgrade", "axios::1.7.9", "--offline",
                "--output-dir", str(root / "out"),
            ])
            self.assertEqual(code, 5)
            self.assertTrue((root / "out" / "frontend-dependency-upgrade-report.md").is_file())

    def test_node_runtime_unknown_without_constraints_does_not_select_host(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("26.5.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                runtime = MODULE.assess_node_runtime(root, MODULE.ManifestSnapshot(), [])
            self.assertEqual(runtime.status, "unknown")
            self.assertEqual(runtime.execution_readiness, "blocked")
            self.assertEqual(runtime.current_host_node, "26.5.0")
            self.assertEqual(runtime.selected_project_node, "")
            self.assertEqual(runtime.selected_manager, "")
            self.assertEqual(runtime.compatible_installed_versions, [])
            self.assertTrue(any("未发现权威项目 Node 约束" in warning for warning in runtime.warnings))

    def test_node_runtime_conflicting_pins_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".nvmrc").write_text("16.20.2\n", encoding="utf-8")
            (root / ".node-version").write_text("18.20.4\n", encoding="utf-8")
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                runtime = MODULE.assess_node_runtime(root, MODULE.ManifestSnapshot(), [])
            self.assertEqual(runtime.status, "constraint-conflict")
            self.assertEqual(runtime.execution_readiness, "blocked")
            self.assertTrue(any("pin 不一致" in blocker for blocker in runtime.blockers))

    def test_node_runtime_missing_manager_is_an_implementation_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = MODULE.ManifestSnapshot(engines={"node": "<=16"})
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                runtime = MODULE.assess_node_runtime(root, manifest, [])
            self.assertEqual(runtime.status, "manager-missing")
            self.assertEqual(runtime.execution_readiness, "blocked")
            self.assertTrue(runtime.installation_guidance)

    def test_node_runtime_prefers_installed_lts_candidate(self) -> None:
        self.assertEqual(
            MODULE.preferred_node_version(["16.20.2", "17.9.1", "18.20.4"]),
            "18.20.4",
        )

    def test_node_runner_requires_granular_approvals(self) -> None:
        args = RUNNER.parse_args([
            ".", "--node-version", "16.20.2", "--command", "npm ci", "--execute",
            "--approve-runtime-switch",
        ])
        with self.assertRaises(ValueError):
            RUNNER.verify_approvals(args)
        self.assertEqual(RUNNER.classify_command("npm ci"), "dependency-install-or-upgrade")
        self.assertEqual(RUNNER.classify_command("npm i"), "dependency-install-or-upgrade")
        self.assertEqual(RUNNER.classify_command("cd web && pnpm install"), "dependency-install-or-upgrade")
        self.assertEqual(RUNNER.classify_command("npm run build"), "project-scripts")
        node_install = RUNNER.parse_args([
            ".", "--node-version", "16.20.2", "--command", "nvm install 16.20.2",
            "--execute", "--approve-runtime-switch", "--approve-project-scripts",
        ])
        with self.assertRaises(ValueError):
            RUNNER.verify_approvals(node_install)

    def test_node_runner_dry_run_does_not_switch_runtime(self) -> None:
        if MODULE.os.name != "nt":
            self.skipTest("nvm-windows path fixture")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runtime = root / "nvm" / "v16.20.2"
            runtime.mkdir(parents=True)
            (runtime / "node.exe").write_bytes(b"")
            args = RUNNER.parse_args([
                str(root), "--node-version", "16.20.2", "--manager", "nvm-windows",
                "--command", "npm run build",
            ])
            with patch.dict(MODULE.os.environ, {"NVM_HOME": str(root / "nvm")}, clear=False):
                code, plan = RUNNER.execute(args)
            self.assertEqual(code, 0)
            self.assertFalse(plan["execute"])
            self.assertEqual(plan["mode"], "isolated-child-process")
            self.assertEqual(plan["restoration"], "not-required")

    def test_node_runner_global_fallback_restores_original_in_finally(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            args = RUNNER.parse_args([
                str(root), "--node-version", "16.20.2", "--manager", "nvm-windows",
                "--command", "npm run build", "--execute",
                "--approve-runtime-switch", "--approve-project-scripts",
            ])
            completed = RUNNER.subprocess.CompletedProcess(["nvm"], 0, stdout="ok", stderr="")
            with (
                patch.object(RUNNER, "current_node", side_effect=[
                    ("20.18.0", "C:/nvm/nodejs/node.exe"),
                    ("16.20.2", "C:/nvm/nodejs/node.exe"),
                    ("20.18.0", "C:/nvm/nodejs/node.exe"),
                ]),
                patch.object(RUNNER, "select_manager", return_value=("nvm-windows", None)),
                patch.object(RUNNER.shutil, "which", return_value="C:/nvm/nvm.exe"),
                patch.object(RUNNER.subprocess, "run", return_value=completed) as process,
                patch.object(RUNNER, "run_shell_command", return_value={
                    "command": "npm run build",
                    "scope": "project-scripts",
                    "started": "now",
                    "node_version": "16.20.2",
                    "node_path": "C:/nvm/nodejs/node.exe",
                    "exit_code": 0,
                }),
            ):
                code, plan = RUNNER.execute(args)
            self.assertEqual(code, 0)
            self.assertEqual(plan["restoration"], "verified")
            uses = [call.args[0] for call in process.call_args_list]
            self.assertIn(["nvm", "use", "16.20.2"], uses)
            self.assertIn(["nvm", "use", "20.18.0"], uses)

    def test_node_constraint_snapshot_ignores_dependency_only_manifest_changes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / "package.json"
            manifest.write_text(json.dumps({
                "engines": {"node": "<=16"},
                "dependencies": {"axios": "0.27.2"},
            }), encoding="utf-8")
            before = RUNNER.snapshot_node_constraints(root)
            manifest.write_text(json.dumps({
                "engines": {"node": "<=16"},
                "dependencies": {"axios": "1.7.9"},
            }), encoding="utf-8")
            after = RUNNER.snapshot_node_constraints(root)
            self.assertEqual(before, after)

    def test_jquery_discovery_uses_3x_migration_stage_before_4x(self) -> None:
        metadata = {"versions": {version: {} for version in ("1.12.4", "2.2.4", "3.7.1", "4.0.0")}}
        candidates = MODULE.discover_target_candidates(
            metadata, MODULE.Upgrade("jquery", "1.12.4", "", intent="target-discovery")
        )
        versions = [candidate.version for candidate in candidates]
        self.assertIn("3.7.1", versions)
        self.assertIn("4.0.0", versions)
        self.assertNotIn("2.2.4", versions)

    def test_version_interval_is_complete_unless_explicitly_capped(self) -> None:
        metadata = {"versions": {version: {} for version in ("1.0.0", "1.1.0", "1.2.0", "2.0.0")}}
        upgrade = MODULE.Upgrade("example", "1.0.0", "2.0.0")
        versions, warnings, complete = MODULE.versions_in_range(metadata, upgrade, 0)
        self.assertEqual(versions, ["1.1.0", "1.2.0", "2.0.0"])
        self.assertTrue(complete)
        self.assertFalse(warnings)
        versions, warnings, complete = MODULE.versions_in_range(metadata, upgrade, 2)
        self.assertEqual(versions, ["1.2.0", "2.0.0"])
        self.assertFalse(complete)
        self.assertTrue(warnings)

    def test_stable_interval_excludes_prerelease_versions(self) -> None:
        metadata = {"versions": {version: {} for version in ("2.7.15", "2.7.16-beta.1", "2.7.16", "3.0.0-alpha.1")}}
        versions, _, complete = MODULE.versions_in_range(
            metadata, MODULE.Upgrade("vue", "2.7.15", "2.7.16"), 0
        )
        self.assertEqual(versions, ["2.7.16"])
        self.assertTrue(complete)

    def test_target_discovery_returns_bounded_exact_candidates(self) -> None:
        metadata = {
            "versions": {
                "1.0.0": {},
                "1.5.0": {"engines": {"node": ">=16"}},
                "2.0.0": {"peerDependencies": {"react": ">=18"}},
                "2.1.0-beta.1": {},
                "3.0.0": {},
            },
            "time": {"1.5.0": "2026-01-01T00:00:00Z"},
        }
        candidates = MODULE.discover_target_candidates(
            metadata,
            MODULE.Upgrade("example", "1.0.0", "", intent="target-discovery"),
        )
        self.assertLessEqual(len(candidates), 3)
        self.assertEqual([candidate.version for candidate in candidates], ["1.5.0", "2.0.0", "3.0.0"])
        self.assertTrue(all(MODULE.semver_key(candidate.version) for candidate in candidates))

    def test_assess_infers_current_version_and_keeps_removal_uncertain(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"legacy": "^1.0.0"}}), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/legacy": {"version": "1.2.3"}},
            }), encoding="utf-8")
            args = MODULE.parse_args([str(root), "--assess", "legacy", "--offline"])
            bundle = MODULE.build_bundle(args)
            report = bundle.reports[0]
            self.assertEqual(report.upgrade.from_version, "1.2.3")
            self.assertEqual(report.baseline_status, "matches_from")
            self.assertEqual(report.analysis_mode, "auto-assess")
            self.assertEqual(report.removal.status, "uncertain")
            self.assertEqual(report.recommended_action, "prefer-same-package-or-retain")
            self.assertEqual(report.decision_status, "needs_choice")
            self.assertEqual(bundle.decision_status, "needs_choice")
            self.assertEqual(bundle.behavior_parity_required, "yes")
            self.assertEqual(bundle.status, "draft")
            markdown = MODULE.markdown_report(bundle)
            self.assertLess(markdown.index("#### 删除可行性"), markdown.index("#### 同库目标版本候选"))
            self.assertLess(markdown.index("#### 同库目标版本候选"), markdown.index("#### 替代库候选"))
            self.assertFalse(MODULE.validate_report_contract(markdown))

    def test_removal_with_direct_usage_requires_migration(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="removal-assessment"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="removal-assessment",
            manifest_field="dependencies",
            observed_lock_versions=["1.2.3"],
        )
        point = MODULE.CodeModificationPoint(
            "legacy", "src/runtime.ts", 1, "Direct package usage", "import legacy from 'legacy'",
            "current source", "review", "test runtime", "P0", "high",
        )
        MODULE.assess_removal(report, [point])
        self.assertEqual(report.removal.status, "requires_migration")
        self.assertEqual(report.recommended_action, "plan-migration-before-removal")
        self.assertTrue(report.removal.blockers)

    def test_open_target_with_direct_usage_moves_to_same_package_candidates(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="auto-assess",
            target_candidates=[
                MODULE.TargetCandidate("legacy", "1.3.0", "same-major-latest"),
            ],
        )
        point = MODULE.CodeModificationPoint(
            "legacy", "src/runtime.ts", 1, "Direct package usage", "import legacy from 'legacy'",
            "current source", "review", "test runtime", "P0", "high",
        )
        MODULE.assess_removal(report, [point])
        self.assertEqual(report.removal.status, "requires_migration")
        self.assertEqual(report.recommended_action, "review-same-package-candidates")
        self.assertTrue(any("同库精确版本" in decision for decision in report.decision_required))

    def test_current_lock_equal_to_target_is_not_inferred_as_from(self) -> None:
        upgrade = MODULE.Upgrade("axios", "", "1.7.9")
        lock = MODULE.LockSnapshot(kind="npm", direct_versions={"axios": "1.7.9"})
        MODULE.infer_current_versions([upgrade], MODULE.LockSnapshot(), lock)
        self.assertEqual(upgrade.from_version, "")

    def test_offline_end_to_end_report_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "src").mkdir()
            (root / "src" / "request.ts").write_text("import axios from 'axios';\nexport default axios.create();", encoding="utf-8")
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "0.27.2"}}), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "0.27.2"}},
            }), encoding="utf-8")
            output = root / "reports"
            args = MODULE.parse_args([
                str(root), "--upgrade", "axios:0.27.2:1.7.9", "--offline",
                "--output-dir", str(output), "--json-output",
            ])
            bundle = MODULE.build_bundle(args)
            markdown_path = MODULE.write_bundle(bundle, args)
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertEqual(bundle.reports[0].baseline_status, "matches_from")
            self.assertEqual(bundle.reports[0].selection_status, "selected")
            self.assertEqual(bundle.decision_status, "not_needed")
            self.assertTrue(bundle.reports[0].constraints)
            self.assertEqual(set(bundle.report_paths), {"markdown", "json"})
            self.assertEqual(bundle.report_paths["markdown"], str(markdown_path))
            self.assertTrue(markdown_path.is_file())
            self.assertTrue(Path(bundle.report_paths["json"]).is_file())
            structured = json.loads(Path(bundle.report_paths["json"]).read_text(encoding="utf-8"))
            self.assertEqual(structured["pending_human_decisions"][0]["package"], "__node_runtime__")
            self.assertEqual(structured["node_runtime"]["status"], "unknown")
            self.assertIn("current_host_node", structured["node_runtime"])
            self.assertNotIn("control_plane_requirement", structured["node_runtime"])
            self.assertIn("### Node 运行时兼容性", markdown)
            self.assertIn("本机当前 Node", markdown)
            self.assertNotIn("控制面 Node", markdown)
            self.assertFalse(MODULE.validate_report_contract(markdown))
            for heading in MODULE.REQUIRED_HEADINGS:
                self.assertIn(f"<!-- section: {heading} -->", markdown)
                self.assertIn(f"## {MODULE.REPORT_SECTION_TITLES[heading]}", markdown)
            self.assertIn("## 升级摘要", markdown)
            self.assertIn("## 结论", markdown)
            self.assertIn("报告状态", markdown)
            self.assertNotIn("#### 删除可行性", markdown)
            self.assertNotIn("#### 处置决策顺序", markdown)

    def test_baseline_mismatch_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "0.27.2"}}), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "0.26.0"}},
            }), encoding="utf-8")
            args = MODULE.parse_args([str(root), "--upgrade", "axios:0.27.2:1.7.9", "--offline"])
            bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.status, "blocked")
            self.assertEqual(bundle.reports[0].baseline_status, "mismatch")

    def test_unknown_baseline_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "^1.0.0"}}), encoding="utf-8")
            args = MODULE.parse_args([str(root), "--assess", "axios", "--offline"])
            bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.status, "blocked")
            self.assertEqual(bundle.analysis_status, "blocked")
            self.assertEqual(bundle.reports[0].baseline_status, "unknown")

    def test_resolve_output_dir_uses_change_evidence_folder(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            change = root / "changes" / "admin-web-deps"
            change.mkdir(parents=True)
            output, note = MODULE.resolve_report_output_dir(root, None, str(change))
            self.assertEqual(output, (change / "evidence" / "frontend-dependency-upgrade").resolve())
            self.assertIn("change-dir", note)

    def test_resolve_output_dir_does_not_guess_unique_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            change = root / "changes" / "only-one"
            change.mkdir(parents=True)
            output, note = MODULE.resolve_report_output_dir(root, None, None)
            self.assertEqual(output, (root / "dependency-upgrade-report").resolve())
            self.assertIn("回退", note)

    def test_behavior_parity_prefers_same_package_over_removal(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="auto-assess",
            recommended_action="review-removal",
            target_candidates=[MODULE.TargetCandidate(
                "legacy", "1.3.0", "same-major-latest",
                compliance_status="eligible",
                criteria_checked=["security", "license"],
                evidence_urls=["https://example.invalid/release"],
            )],
        )
        MODULE.apply_behavior_parity(report)
        self.assertEqual(report.recommended_action, "prefer-same-package-upgrade")
        self.assertEqual(report.decision_status, "needs_choice")
        self.assertEqual(report.selection_status, "needs_explicit_choice")
        self.assertTrue(any("行为守恒" in item for item in report.decision_required))

    def test_exact_target_behavior_constraint_does_not_create_false_decision(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("antd", "4.24.16", "5.22.0", intent="exact-upgrade"),
            "https://www.npmjs.com/package/antd",
            analysis_mode="exact-upgrade",
            decision_status="not_needed",
            selection_status="selected",
        )
        MODULE.apply_behavior_parity(report)
        self.assertEqual(report.decision_status, "not_needed")
        self.assertEqual(report.selection_status, "selected")
        self.assertFalse(report.decision_required)
        self.assertTrue(any("行为守恒" in item for item in report.constraints))

    def test_analysis_evidence_imports_compliance_alternative_and_removal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            evidence_path = root / "evidence.json"
            evidence_path.write_text(json.dumps({
                "packages": {
                    "legacy": {
                        "reason": "停止维护",
                        "target_candidates": [{
                            "version": "1.3.0",
                            "compliance_status": "eligible",
                            "criteria_checked": ["security", "license", "maintenance"],
                            "evidence_urls": ["https://example.invalid/legacy-release"],
                        }],
                        "alternative_candidates": [{
                            "package": "replacement",
                            "version": "2.0.0",
                            "compliance_status": "eligible",
                            "criteria_checked": ["security", "license", "maintenance"],
                            "evidence_urls": ["https://example.invalid/replacement-docs"],
                        }],
                        "removal": {
                            "status": "requires_migration",
                            "evidence": ["shared wrapper imports package"],
                            "blockers": ["src/request.ts"],
                            "coverage_checked": ["business", "runtime"],
                            "confidence": "high",
                        },
                    },
                },
            }), encoding="utf-8")
            report = MODULE.PackageReport(
                MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
                "https://www.npmjs.com/package/legacy",
                analysis_mode="auto-assess",
                decision_required=["尚未建立治理或不合规依据；先核对仓库政策、安全、license、兼容性和维护状态。"],
            )
            evidence = MODULE.load_analysis_evidence(evidence_path)
            MODULE.apply_analysis_evidence([report], evidence)
            MODULE.reconcile_open_target_report(report)
            self.assertEqual(report.target_candidates[0].compliance_status, "eligible")
            self.assertEqual(report.alternative_candidates[0].package, "replacement")
            self.assertEqual(report.removal.status, "requires_migration")
            self.assertEqual(report.selection_status, "needs_explicit_choice")
            self.assertEqual(report.upgrade.reason, "停止维护")
            self.assertFalse(any(item.startswith("尚未建立治理") for item in report.decision_required))

    def test_safe_removal_candidate_requires_complete_coverage(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.removal_from_evidence("legacy", {
                "status": "safe_removal_candidate",
                "evidence": ["no consumers found"],
                "coverage_checked": ["business", "runtime"],
            })

    def test_allow_behavior_change_keeps_removal_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"legacy": "^1.0.0"}}), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/legacy": {"version": "1.2.3"}},
            }), encoding="utf-8")
            args = MODULE.parse_args([str(root), "--assess", "legacy", "--offline", "--allow-behavior-change"])
            bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.behavior_parity_required, "no")
            self.assertEqual(bundle.reports[0].recommended_action, "review-removal")


if __name__ == "__main__":
    unittest.main()

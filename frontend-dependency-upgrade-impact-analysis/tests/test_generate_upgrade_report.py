from __future__ import annotations

import datetime as dt
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

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic-frontend"


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

    def test_exact_direct_upgrade_emits_commands_and_requires_full_lock_convergence(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.6.8", "1.7.9", intent="exact-upgrade"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="exact-upgrade",
            manifest_field="dependencies",
            lock_kind="npm",
            peer_compatibility_status="not-applicable",
            after_lock_versions=["1.7.9"],
            provenance=MODULE.ProvenanceAssessment(kind="direct"),
        )
        runtime = MODULE.NodeRuntimeAssessment(status="compatible-current")
        MODULE.finalize_exact_upgrade_report(report, runtime)
        self.assertEqual(report.exact_upgrade_status, "ready")
        self.assertEqual(report.target_convergence_status, "confirmed")
        self.assertEqual(report.recommended_action, "upgrade-to-exact-target")
        self.assertIn("npm install axios@1.7.9", report.implementation_commands)
        self.assertIn("npm ls axios --all", report.implementation_commands)

    def test_exact_upgrade_is_blocked_when_any_lock_instance_remains_old(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.6.8", "1.7.9", intent="exact-upgrade"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="exact-upgrade",
            manifest_field="dependencies",
            lock_kind="npm",
            peer_compatibility_status="not-applicable",
            after_lock_versions=["1.7.9", "0.27.2"],
            provenance=MODULE.ProvenanceAssessment(kind="both"),
        )
        MODULE.finalize_exact_upgrade_report(
            report, MODULE.NodeRuntimeAssessment(status="compatible-current"),
        )
        self.assertEqual(report.exact_upgrade_status, "blocked")
        self.assertEqual(report.residual_lock_versions, ["0.27.2"])
        self.assertTrue(any("残留" in item for item in report.implementation_blockers))

    def test_exact_transitive_upgrade_uses_override_only_when_parent_ranges_accept_target(self) -> None:
        compatible = MODULE.PackageReport(
            MODULE.Upgrade("buried", "4.1.0", "4.3.0", intent="exact-upgrade"),
            "https://www.npmjs.com/package/buried",
            analysis_mode="exact-upgrade",
            lock_kind="pnpm",
            peer_compatibility_status="not-applicable",
            provenance=MODULE.ProvenanceAssessment(
                kind="transitive",
                parents=[MODULE.ParentEdge("parent-a", "2.0.0", "^4.0.0")],
            ),
        )
        runtime = MODULE.NodeRuntimeAssessment(status="compatible-current")
        MODULE.finalize_exact_upgrade_report(compatible, runtime)
        self.assertEqual(compatible.exact_upgrade_status, "ready")
        self.assertTrue(any("pnpm.overrides.buried=4.3.0" in item for item in compatible.implementation_commands))

        incompatible = MODULE.PackageReport(
            MODULE.Upgrade("buried", "4.1.0", "5.0.0", intent="exact-upgrade"),
            "https://www.npmjs.com/package/buried",
            analysis_mode="exact-upgrade",
            lock_kind="pnpm",
            peer_compatibility_status="not-applicable",
            provenance=compatible.provenance,
        )
        MODULE.finalize_exact_upgrade_report(incompatible, runtime)
        self.assertEqual(incompatible.exact_upgrade_status, "blocked")
        self.assertEqual(incompatible.implementation_commands, [])
        self.assertTrue(any("父依赖" in item for item in incompatible.implementation_blockers))

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

    def test_bun_text_lock_direct_and_nested_versions(self) -> None:
        content = """{
  // Bun text lockfile
  "lockfileVersion": 1,
  "workspaces": {
    "": { "name": "app", "dependencies": { "axios": "^1.7.9" } },
  },
  "packages": {
    "axios": ["axios@1.7.9", "", { "dependencies": {} }, "sha512-abc"],
    "legacy-wrapper/axios": ["axios@0.27.2", "", {}, "sha512-def"],
  },
}
"""
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "bun.lock"
            path.write_text(content, encoding="utf-8")
            lock = MODULE.parse_lock(path, ["axios"])
            self.assertEqual(lock.kind, "bun")
            self.assertEqual(lock.direct_versions["axios"], "1.7.9")
            self.assertEqual(set(lock.all_versions["axios"]), {"0.27.2", "1.7.9"})
            self.assertEqual(lock.warnings, [])

    def test_bun_binary_lock_reports_actionable_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "bun.lockb"
            path.write_bytes(b"\x00binary")
            lock = MODULE.parse_lock(path, ["axios"])
            self.assertEqual(lock.direct_versions, {})
            self.assertTrue(any("--save-text-lockfile" in warning for warning in lock.warnings))

    def test_bun_lock_is_detected_in_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "bun.lock").write_text('{"lockfileVersion": 1}', encoding="utf-8")
            detected = MODULE.detect_lock(root)
            self.assertIsNotNone(detected)
            self.assertEqual(detected.name, "bun.lock")

    def test_pnpm_catalog_spec_resolves_effective_range(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "pnpm-workspace.yaml").write_text(
                "packages:\n  - 'apps/*'\ncatalog:\n  axios: ^1.7.9\ncatalogs:\n  legacy:\n    axios: ^0.27.2\n",
                encoding="utf-8",
            )
            manifest_path = root / "package.json"
            manifest_path.write_text(
                json.dumps({"dependencies": {"axios": "catalog:", "vue": "catalog:legacy"}}),
                encoding="utf-8",
            )
            manifest = MODULE.load_manifest(manifest_path, root)
            self.assertEqual(manifest.packages["axios"].catalog_spec, "^1.7.9")
            self.assertEqual(manifest.packages["axios"].catalog_source, "pnpm-workspace.yaml#catalog")
            self.assertEqual(manifest.packages["vue"].catalog_spec, "")
            self.assertEqual(MODULE.clean_version("catalog:"), "catalog:")

    def test_missing_optional_lock_is_not_reported_as_missing_lockfile(self) -> None:
        self.assertEqual(MODULE.parse_lock(None, ["axios"], role="before").warnings, [])
        self.assertEqual(MODULE.parse_lock(None, ["axios"], role="after").warnings, [])
        current = MODULE.parse_lock(None, ["axios"], role="current")
        self.assertTrue(any("未在项目根目录找到受支持的 lockfile" in warning for warning in current.warnings))

    def test_unsupported_lock_type_names_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "deno.lock"
            path.write_text("{}", encoding="utf-8")
            lock = MODULE.parse_lock(path, ["axios"], role="current")
            self.assertTrue(any("deno.lock" in warning for warning in lock.warnings))

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

    def test_patch_upgrade_of_high_blast_radius_family_is_not_high(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.6.8", "1.6.9", "request"),
            "https://www.npmjs.com/package/axios",
            change_type="patch",
            baseline_status="matches_from",
            observed_lock_versions=["1.6.8"],
            evidence_completeness="complete",
        )
        points = [
            MODULE.CodeModificationPoint(
                "axios", "package.json", 6, MODULE.DECLARATION_CATEGORY, '"axios": "1.6.8"',
                "official evidence", "review", "test request", "P2", "high",
            ),
            MODULE.CodeModificationPoint(
                "axios", "src/main.js", 1, "Direct package usage", "import axios from 'axios'",
                "official evidence", "review", "test request", "P2", "high",
            ),
        ]
        risk = MODULE.risk_score(report, points, [], "auto", "auto")
        self.assertEqual(risk.factors["version_change"], 1)
        self.assertEqual(risk.factors["dependency_type"], 1)
        self.assertEqual(risk.factors["usage_scope"], 1)
        self.assertEqual(risk.factors["business_criticality"], 2)
        self.assertEqual(risk.total, sum(risk.factors.values()))
        self.assertEqual(risk.final_level, "Medium")
        self.assertTrue(any("业务关键性" in item for item in risk.uncertainties))

    def test_major_upgrade_of_same_family_stays_high(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "0.27.2", "1.7.9", "request"),
            "https://www.npmjs.com/package/axios",
            change_type="major",
            baseline_status="matches_from",
            observed_lock_versions=["0.27.2"],
            evidence_completeness="complete",
        )
        points = [
            MODULE.CodeModificationPoint(
                "axios", "src/request/client.ts", 1, "Direct package usage", "axios.create()",
                "official evidence", "review", "test request", "P0", "high",
            ),
        ]
        risk = MODULE.risk_score(report, points, [], "auto", "auto")
        self.assertEqual(risk.factors["dependency_type"], 5)
        self.assertEqual(risk.final_level, "High")

    def test_declaration_only_usage_is_uncertain_not_zero_risk(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy-client", "1.0.0", "1.0.1", "runtime"),
            "https://www.npmjs.com/package/legacy-client",
            change_type="patch",
            baseline_status="matches_from",
        )
        points = [
            MODULE.CodeModificationPoint(
                "legacy-client", "package.json", 4, MODULE.DECLARATION_CATEGORY, '"legacy-client": "1.0.0"',
                "official evidence", "review", "smoke", "P2", "high",
            ),
        ]
        risk = MODULE.risk_score(report, points, [], "auto", "auto")
        self.assertEqual(risk.factors["usage_scope"], 0)
        self.assertTrue(any("仅发现依赖声明" in item for item in risk.uncertainties))

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

    def test_semver_range_table_matches_npm_resolution(self) -> None:
        cases = (
            # partial caret/tilde, the most common engines.node shape
            ("22.0.0", "^18 || ^20 || ^22", True),
            ("21.0.0", "^18 || ^20 || ^22", False),
            ("16.20.2", "^16", True),
            ("17.0.0", "^16", False),
            ("18.1.0", "~18", True),
            ("19.0.0", "~18", False),
            ("20.1.0", "~>20.1", True),
            ("1.2.5", "~1.2.3", True),
            ("1.3.0", "~1.2.3", False),
            ("0.2.5", "^0.2.3", True),
            ("0.3.0", "^0.2.3", False),
            ("0.0.4", "^0.0.3", False),
            # hyphen ranges must not swallow the remaining OR alternatives
            ("20.11.0", "18.0.0 - 18.99.99 || >=20", True),
            ("18.19.0", "16.x - 18.x || >=20", True),
            ("19.5.0", "16.x - 18.x || >=20", False),
            ("2.3.4", "1.2.3 - 2.3.4", True),
            ("2.3.5", "1.2.3 - 2.3.4", False),
            ("2.9.9", "1.2.3 - 2", True),
            ("3.0.0", "1.2.3 - 2", False),
            # partial comparators and x-ranges
            ("19.0.0", ">18", True),
            ("18.0.0", ">18", False),
            ("18.20.0", "<=18", True),
            ("19.0.0", "<=18", False),
            ("20.5.0", ">=18.17 <21", True),
            ("18.16.0", ">=18.17 <21", False),
            ("20.1.0", "20.1.x", True),
            ("20.2.0", "20.1.x", False),
            ("20.11.1", ">=16.0.0 <=22.x", True),
            ("23.0.0", ">=16.0.0 <=22.x", False),
            ("14.21.3", "^14.17.0 || ^16.13.0 || >=18.0.0", True),
            ("16.10.0", "^14.17.0 || ^16.13.0 || >=18.0.0", False),
            # wildcards, equality and prerelease rules
            ("20.0.0", "*", True),
            ("20.0.0", "", True),
            ("20.0.0", "=20.0.0", True),
            ("20.0.1", "=20.0.0", False),
            ("18.0.0-nightly", ">=18", False),
            ("18.0.0-nightly", ">=18.0.0-alpha", True),
            # unparseable ranges stay unknown instead of silently reading as False
            ("20.0.0", "not-a-range", None),
            ("17.0.0", ">=18 || not-a-range", None),
            ("20.0.0", ">=18 || not-a-range", True),
        )
        mismatches = [
            (version, requirement, expected, MODULE.semver_satisfies(version, requirement))
            for version, requirement, expected in cases
            if MODULE.semver_satisfies(version, requirement) is not expected
        ]
        self.assertEqual(mismatches, [])

    def test_common_engines_range_is_not_treated_as_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            manifest = MODULE.ManifestSnapshot(
                path=str(root / "package.json"),
                engines={"node": "^18 || ^20 || ^22"},
            )
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                runtime = MODULE.assess_node_runtime(root, manifest, [])
            self.assertEqual(runtime.status, "compatible-current")
            self.assertEqual(runtime.selected_project_node, "20.18.0")
            self.assertEqual(runtime.blockers, [])

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
            self.assertEqual(runtime.selected_node_support, "eol")
            self.assertTrue(any("EOL" in warning for warning in runtime.warnings))

    def test_node_support_status_is_date_driven(self) -> None:
        today = dt.date(2026, 7, 25)
        self.assertEqual(MODULE.node_support_status("18.20.4", today)[0], "eol")
        self.assertEqual(MODULE.node_support_status("20.18.0", today)[0], "eol")
        self.assertEqual(MODULE.node_support_status("22.11.0", today)[0], "supported")
        self.assertEqual(MODULE.node_support_status("24.4.0", today)[0], "supported")
        # A major outside the reviewed schedule must stay unknown instead of being guessed.
        self.assertEqual(MODULE.node_support_status("99.0.0", today)[0], "unknown")
        self.assertEqual(MODULE.node_support_status("22.11.0", dt.date(2027, 3, 1))[0], "approaching-eol")
        self.assertEqual(MODULE.node_support_status("22.11.0", dt.date(2027, 5, 1))[0], "eol")

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

    def test_lock_declared_toolchain_engine_works_without_node_modules(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/vite": {"version": "5.2.0", "engines": {"node": "^18.0.0 || >=20.0.0"}},
                },
            }), encoding="utf-8")
            manifest = MODULE.ManifestSnapshot(
                packages={"vite": MODULE.ManifestPackage("vite", "devDependencies", "^5.2.0")},
            )
            lock = MODULE.parse_lock(root / "package-lock.json", ["vite"], ".", role="current")
            self.assertEqual(lock.declared_engines, {"vite": "^18.0.0 || >=20.0.0"})
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("16.20.2", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["fnm"], {"fnm": ["20.18.0"]})),
            ):
                runtime = MODULE.assess_node_runtime(root, manifest, [], lock=lock)
            self.assertEqual(runtime.status, "runtime-switch-required")
            self.assertEqual(runtime.selected_project_node, "20.18.0")
            self.assertTrue(any(
                item.source.startswith("vite@5.2.0 lock") and item.authority == "authoritative"
                for item in runtime.project_constraints
            ))

    def test_lock_declared_non_toolchain_engine_stays_observed(self) -> None:
        lock = MODULE.LockSnapshot(
            kind="npm",
            path="package-lock.json",
            direct_versions={"legacy-widget": "1.0.0"},
            declared_engines={"legacy-widget": ">=8 <13"},
        )
        derived = MODULE.lock_declared_runtime_evidence(lock)
        self.assertEqual([item.authority for item in derived], ["observed"])
        self.assertEqual([item.kind for item in derived], ["dependency-engine"])
        with tempfile.TemporaryDirectory() as raw:
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                runtime = MODULE.assess_node_runtime(Path(raw), MODULE.ManifestSnapshot(), [], lock=lock)
            self.assertEqual(runtime.status, "unknown")
            self.assertEqual(runtime.project_constraints, [])

    def test_pnpm_lock_declares_engines_for_direct_version(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "pnpm-lock.yaml"
            path.write_text(
                "lockfileVersion: '9.0'\n"
                "importers:\n"
                "  .:\n"
                "    devDependencies:\n"
                "      vite:\n"
                "        specifier: ^5.2.0\n"
                "        version: 5.2.0\n"
                "packages:\n"
                "\n"
                "  vite@5.2.0:\n"
                "    resolution: {integrity: sha512-deadbeef}\n"
                "    engines: {node: ^18.0.0 || >=20.0.0}\n"
                "    hasBin: true\n",
                encoding="utf-8",
            )
            lock = MODULE.parse_lock(path, ["vite"], ".", role="current")
            self.assertEqual(lock.direct_versions, {"vite": "5.2.0"})
            self.assertEqual(lock.declared_engines, {"vite": "^18.0.0 || >=20.0.0"})

    def test_pnpm_lock_declares_engines_in_nested_block_form(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "pnpm-lock.yaml"
            path.write_text(
                "lockfileVersion: '6.0'\n"
                "importers:\n"
                "  .:\n"
                "    dependencies:\n"
                "      typescript:\n"
                "        specifier: ^5.4.0\n"
                "        version: 5.4.5\n"
                "packages:\n"
                "\n"
                "  /typescript@5.4.5:\n"
                "    resolution: {integrity: sha512-cafe}\n"
                "    engines:\n"
                "      node: '>=14.17'\n"
                "    hasBin: true\n",
                encoding="utf-8",
            )
            lock = MODULE.parse_lock(path, ["typescript"], ".", role="current")
            self.assertEqual(lock.declared_engines, {"typescript": ">=14.17"})

    def test_npmrc_and_mise_pins_are_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".npmrc").write_text("use-node-version=20.18.0\n", encoding="utf-8")
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                runtime = MODULE.assess_node_runtime(root, MODULE.ManifestSnapshot(), [])
            self.assertEqual(runtime.status, "compatible-current")
            self.assertEqual(runtime.selected_project_node, "20.18.0")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "mise.toml").write_text(
                "[env]\nnode = \"skip-me\"\n\n[tools]\nnode = \"22.11.0\"\n", encoding="utf-8"
            )
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("22.11.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                runtime = MODULE.assess_node_runtime(root, MODULE.ManifestSnapshot(), [])
            self.assertEqual(
                [(item.source, item.requirement) for item in runtime.project_constraints],
                [("mise.toml#tools.node", "22.11.0")],
            )

    def test_pnpm_execution_env_node_version_is_a_project_pin(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = MODULE.ManifestSnapshot(
                path=str(root / "package.json"),
                pnpm={"executionEnv": {"nodeVersion": "18.20.4"}},
            )
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["fnm"], {"fnm": ["18.20.4"]})),
            ):
                runtime = MODULE.assess_node_runtime(root, manifest, [])
            self.assertEqual(runtime.status, "runtime-switch-required")
            self.assertEqual(runtime.selected_project_node, "18.20.4")

    def test_deployment_and_ci_configs_are_observed_not_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "netlify.toml").write_text(
                "[build.environment]\n  NODE_VERSION = \"20.18.0\"\n", encoding="utf-8"
            )
            (root / "vercel.json").write_text(
                json.dumps({"functions": {"api/*.ts": {"runtime": "nodejs20.x"}}}), encoding="utf-8"
            )
            circleci = root / ".circleci"
            circleci.mkdir()
            (circleci / "config.yml").write_text(
                "jobs:\n  build:\n    docker:\n      - image: cimg/node:22.11.0\n", encoding="utf-8"
            )
            (root / "Dockerfile").write_text("ARG NODE_VERSION=20.18.0\nFROM node:${NODE_VERSION}\n", encoding="utf-8")
            evidence = MODULE.observed_node_runtime_evidence(root)
            sources = {Path(item.source).name for item in evidence}
            self.assertEqual(sources, {"netlify.toml", "vercel.json", "config.yml", "Dockerfile"})
            self.assertEqual({item.authority for item in evidence}, {"observed"})
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("26.5.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                runtime = MODULE.assess_node_runtime(root, MODULE.ManifestSnapshot(), [])
            self.assertEqual(runtime.status, "unknown")
            self.assertEqual(runtime.selected_project_node, "")
            self.assertTrue(runtime.observed_runtime_evidence)

    def test_synthetic_fixture_node_status_not_compatible_with_host_26(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            out = Path(raw) / "report"
            args = MODULE.parse_args([
                str(FIXTURE_ROOT),
                "--upgrade", "axios::1.7.9",
                "--offline",
                "--output-dir", str(out),
            ])
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("26.5.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.importer_resolution, "confirmed")
            self.assertEqual(bundle.node_runtime.current_host_node, "26.5.0")
            self.assertNotEqual(bundle.node_runtime.status, "compatible-current")
            self.assertIn(bundle.node_runtime.status, {
                "runtime-switch-required", "runtime-missing", "manager-missing",
            })
            self.assertNotEqual(bundle.node_runtime.selected_project_node, "26.5.0")
            pin = (FIXTURE_ROOT / ".nvmrc").read_text(encoding="utf-8")
            self.assertEqual(pin.strip(), "20.18.0")

    def test_synthetic_fixture_dual_run_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            def run_once(tag: str):
                out = root / f"report-{tag}"
                args = MODULE.parse_args([
                    str(FIXTURE_ROOT), "--upgrade", "axios::1.7.9", "--offline",
                    "--output-dir", str(out),
                ])
                with (
                    patch.object(MODULE, "current_host_node_runtime", return_value=("26.5.0", "C:/node/node.exe")),
                    patch.object(MODULE, "detect_node_managers", return_value=([], {})),
                ):
                    return MODULE.build_bundle(args)

            a, b = run_once("a"), run_once("b")
            self.assertEqual(a.analysis_status, b.analysis_status)
            self.assertEqual(a.decision_status, b.decision_status)
            self.assertEqual(a.node_runtime.status, b.node_runtime.status)
            self.assertEqual(a.reports[0].risk.total, b.reports[0].risk.total)
            self.assertEqual(a.reports[0].baseline_status, b.reports[0].baseline_status)

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
            self.assertTrue(any("项目命令硬阻断" in item for item in runtime.blockers))

    def test_evidence_selected_project_node_establishes_runtime_without_repo_pin(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("26.5.0", "C:/node/node.exe")),
                patch.object(
                    MODULE,
                    "detect_node_managers",
                    return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]}),
                ),
            ):
                runtime = MODULE.assess_node_runtime(
                    root,
                    MODULE.ManifestSnapshot(),
                    [],
                    evidence={"selected_project_node": "20.18.0"},
                )
            self.assertEqual(runtime.status, "runtime-switch-required")
            self.assertEqual(runtime.execution_readiness, "ready-awaiting-approval")
            self.assertEqual(runtime.selected_project_node, "20.18.0")
            self.assertTrue(
                any(item.source == "analysis-evidence#selected_project_node" for item in runtime.project_constraints)
            )

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

    def test_node_runner_times_out_hung_project_command(self) -> None:
        args = RUNNER.parse_args([
            ".", "--node-version", "20.18.0", "--command", "npm run build", "--command-timeout", "5",
        ])
        self.assertEqual(args.command_timeout, 5)
        with (
            patch.object(RUNNER, "current_node", return_value=("20.18.0", "C:/node/node.exe")),
            patch.object(
                RUNNER.subprocess, "run",
                side_effect=RUNNER.subprocess.TimeoutExpired(cmd="npm run build", timeout=5),
            ),
        ):
            row = RUNNER.run_shell_command("npm run build", Path("."), {}, 5)
        self.assertEqual(row["exit_code"], 124)
        self.assertEqual(row["state"], "timeout")
        self.assertEqual(row["timeout_seconds"], 5)

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

    def test_lockfile_format_snapshot_tracks_version_not_tree_content(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            lock = root / "package-lock.json"
            lock.write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "0.27.2"}},
            }), encoding="utf-8")
            before = RUNNER.snapshot_lockfile_formats(root)
            lock.write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.7.9"}},
            }), encoding="utf-8")
            after = RUNNER.snapshot_lockfile_formats(root)
            self.assertEqual(before, {"package-lock.json": "3"})
            self.assertEqual(before, after)
            lock.write_text(json.dumps({
                "lockfileVersion": 2,
                "packages": {"node_modules/axios": {"version": "1.7.9"}},
            }), encoding="utf-8")
            drifted = RUNNER.snapshot_lockfile_formats(root)
            self.assertEqual(drifted, {"package-lock.json": "2"})

    def test_npm_lockfile_compatibility_matrix(self) -> None:
        self.assertTrue(RUNNER.npm_compatible_with_lockfile_version("6.14.18", "1"))
        self.assertFalse(RUNNER.npm_compatible_with_lockfile_version("9.8.1", "1"))
        self.assertTrue(RUNNER.npm_compatible_with_lockfile_version("8.19.4", "2"))
        self.assertFalse(RUNNER.npm_compatible_with_lockfile_version("10.5.0", "2"))
        self.assertTrue(RUNNER.npm_compatible_with_lockfile_version("10.5.0", "3"))
        self.assertFalse(RUNNER.npm_compatible_with_lockfile_version("6.14.18", "3"))

    def test_runner_blocks_npm_install_when_npm_incompatible_with_lockfile(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 1,
                "dependencies": {"axios": {"version": "0.27.2"}},
            }), encoding="utf-8")
            args = RUNNER.parse_args([
                str(root), "--node-version", "20.18.0", "--manager", "auto",
                "--command", "npm install axios@1.7.9", "--execute",
                "--approve-runtime-switch", "--approve-dependency-install",
            ])
            with (
                patch.object(RUNNER, "current_node", side_effect=[
                    ("20.18.0", "C:/node/node.exe"),
                    ("20.18.0", "C:/node/node.exe"),
                    ("20.18.0", "C:/node/node.exe"),
                ]),
                patch.object(RUNNER, "select_manager", return_value=("current", Path("C:/node"))),
                patch.object(RUNNER, "current_tool_version", return_value="10.8.2"),
                patch.object(RUNNER, "run_shell_command") as run_command,
            ):
                code, plan = RUNNER.execute(args)
            self.assertEqual(code, 2)
            self.assertIn("不兼容", plan.get("execution_error", ""))
            run_command.assert_not_called()

    def test_runner_fails_when_lockfile_format_drifts_without_approval(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            lock = root / "package-lock.json"
            lock.write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.7.9"}},
            }), encoding="utf-8")
            args = RUNNER.parse_args([
                str(root), "--node-version", "20.18.0",
                "--command", "npm install axios@1.7.9", "--execute",
                "--approve-runtime-switch", "--approve-dependency-install",
            ])

            def mutate_lock(command, project_root, env, timeout):
                lock.write_text(json.dumps({
                    "lockfileVersion": 2,
                    "packages": {"node_modules/axios": {"version": "1.7.9"}},
                }), encoding="utf-8")
                return {
                    "command": command,
                    "scope": "dependency-install-or-upgrade",
                    "started": "now",
                    "node_version": "20.18.0",
                    "node_path": "C:/node/node.exe",
                    "exit_code": 0,
                }

            with (
                patch.object(RUNNER, "current_node", side_effect=[
                    ("20.18.0", "C:/node/node.exe"),
                    ("20.18.0", "C:/node/node.exe"),
                    ("20.18.0", "C:/node/node.exe"),
                ]),
                patch.object(RUNNER, "select_manager", return_value=("current", Path("C:/node"))),
                patch.object(RUNNER, "current_tool_version", return_value="10.8.2"),
                patch.object(RUNNER, "run_shell_command", side_effect=mutate_lock),
            ):
                code, plan = RUNNER.execute(args)
            self.assertEqual(code, 7)
            self.assertEqual(plan["lock_format_integrity"], "changed")
            self.assertEqual(
                plan["lock_format_changes"]["package-lock.json"],
                {"before": "3", "after": "2"},
            )

    def test_runner_allows_lockfile_format_migration_when_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            lock = root / "package-lock.json"
            lock.write_text(json.dumps({
                "lockfileVersion": 2,
                "packages": {"node_modules/axios": {"version": "1.7.9"}},
            }), encoding="utf-8")
            args = RUNNER.parse_args([
                str(root), "--node-version", "20.18.0",
                "--command", "npm install axios@1.7.9", "--execute",
                "--approve-runtime-switch", "--approve-dependency-install",
                "--allow-lockfile-format-migration",
            ])

            def migrate_lock(command, project_root, env, timeout):
                lock.write_text(json.dumps({
                    "lockfileVersion": 3,
                    "packages": {"node_modules/axios": {"version": "1.7.9"}},
                }), encoding="utf-8")
                return {
                    "command": command,
                    "scope": "dependency-install-or-upgrade",
                    "started": "now",
                    "node_version": "20.18.0",
                    "node_path": "C:/node/node.exe",
                    "exit_code": 0,
                }

            with (
                patch.object(RUNNER, "current_node", side_effect=[
                    ("20.18.0", "C:/node/node.exe"),
                    ("20.18.0", "C:/node/node.exe"),
                    ("20.18.0", "C:/node/node.exe"),
                ]),
                patch.object(RUNNER, "select_manager", return_value=("current", Path("C:/node"))),
                patch.object(RUNNER, "run_shell_command", side_effect=migrate_lock),
            ):
                code, plan = RUNNER.execute(args)
            self.assertEqual(code, 0)
            self.assertEqual(plan["lock_format_integrity"], "migration-allowed")

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
            args = MODULE.parse_args([
                str(root), "--assess", "legacy", "--offline",
                "--output-dir", str(root / "out"),
            ])
            bundle = MODULE.build_bundle(args)
            report = bundle.reports[0]
            self.assertEqual(report.upgrade.from_version, "1.2.3")
            self.assertEqual(report.baseline_status, "matches_from")
            self.assertEqual(report.analysis_mode, "auto-assess")
            self.assertEqual(report.removal.status, "uncertain")
            self.assertEqual(report.recommended_action, "review-removal")
            self.assertEqual(report.decision_status, "needs_choice")
            self.assertEqual(bundle.decision_status, "needs_choice")
            self.assertEqual(bundle.behavior_parity_required, "yes")
            self.assertEqual(bundle.status, "draft")
            markdown = MODULE.markdown_report(bundle)
            self.assertNotIn("同库目标版本候选", markdown)
            self.assertLess(markdown.index("#### 依赖来源与父包链"), markdown.index("#### 删除可行性"))
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

    def test_open_target_with_direct_usage_moves_to_replacement_research(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="auto-assess",
        )
        point = MODULE.CodeModificationPoint(
            "legacy", "src/runtime.ts", 1, "Direct package usage", "import legacy from 'legacy'",
            "current source", "review", "test runtime", "P0", "high",
        )
        MODULE.assess_removal(report, [point])
        self.assertEqual(report.removal.status, "requires_migration")
        self.assertEqual(report.recommended_action, "research-replacement")
        self.assertTrue(any("替代库" in decision for decision in report.decision_required))

    def alternative_args(self, offline: bool = False) -> argparse.Namespace:
        return MODULE.parse_args(
            [".", "--assess", "axios", "--no-upstream-evidence"] + (["--offline"] if offline else [])
        )

    def test_curated_alternatives_resolve_exact_versions_from_registry(self) -> None:
        registry = {
            "ky": {
                "versions": {"1.9.0": {"license": "MIT"}, "2.0.2": {"license": "MIT", "engines": {"node": ">=22"}}},
                "time": {"2.0.2": "2026-04-21T00:00:00.000Z"},
            },
            "ofetch": {"versions": {"1.5.1": {"license": "MIT"}}, "time": {"1.5.1": "2025-11-01T00:00:00.000Z"}},
        }
        with patch.object(MODULE, "request_json", side_effect=lambda url, *_: registry.get(url.rsplit("/", 1)[-1])):
            candidates = MODULE.build_alternative_candidates("axios", self.alternative_args(), [])
        self.assertEqual([(item.package, item.version) for item in candidates], [("ky", "2.0.2"), ("ofetch", "1.5.1")])
        self.assertEqual({item.origin for item in candidates}, {"curated-map"})
        self.assertEqual({item.compliance_status for item in candidates}, {"unknown"})
        self.assertIn("2026-04-21", candidates[0].compliance_and_maintenance)
        self.assertIn("license=MIT", candidates[0].compliance_and_maintenance)
        self.assertEqual(candidates[0].engines, {"node": ">=22"})

    def test_deprecated_alternative_version_is_disqualified(self) -> None:
        registry = {"sass": {"versions": {"1.80.0": {"deprecated": "use dart-sass"}}, "time": {}}}
        with patch.object(MODULE, "request_json", side_effect=lambda url, *_: registry.get(url.rsplit("/", 1)[-1])):
            candidates = MODULE.build_alternative_candidates("node-sass", self.alternative_args(), [])
        self.assertEqual(len(candidates), 1)
        self.assertTrue(any("已弃用" in item for item in candidates[0].disqualifiers))

    def test_offline_alternatives_are_listed_without_versions(self) -> None:
        candidates = MODULE.build_alternative_candidates("moment", self.alternative_args(offline=True), [])
        self.assertEqual([item.package for item in candidates], ["dayjs", "date-fns", "luxon"])
        self.assertEqual({item.version for item in candidates}, {""})
        self.assertTrue(all("离线模式未解析精确版本" in item.disqualifiers for item in candidates))

    def test_unmapped_package_gets_no_curated_alternatives(self) -> None:
        self.assertEqual(MODULE.build_alternative_candidates("internal-widget", self.alternative_args(), []), [])

    def test_element_ui_has_element_plus_curated_lead(self) -> None:
        candidates = MODULE.build_alternative_candidates(
            "element-ui", self.alternative_args(offline=True), []
        )
        self.assertEqual([item.package for item in candidates], ["element-plus"])
        self.assertEqual({item.origin for item in candidates}, {"curated-map"})

    def test_curated_lead_sets_replace_track_not_native_refactor(self) -> None:
        report = self.open_target_report()
        report.upgrade = MODULE.Upgrade("element-ui", "2.13.2", "", intent="auto-assess")
        report.removal.status = "requires_migration"
        report.alternative_candidates = [
            MODULE.AlternativeCandidate(
                "element-plus", "", origin="curated-map", compliance_status="unknown"
            )
        ]
        report.refactor_plan = MODULE.build_refactor_plan(report, [
            MODULE.CodeModificationPoint(
                "element-ui", "src/main.js", 1, "UI component usage", "", "", "", "", "P1", "high"
            ),
        ])
        MODULE.assign_primary_track(report)
        question = MODULE.build_confirmation_question(report)
        self.assertEqual(report.primary_track, "replace")
        self.assertEqual(question.status, "blocked")
        self.assertIn("analysis-evidence", question.blocked_reason)
        self.assertNotIn("原生改造，确认吗", question.prompt)

    def test_cross_major_interval_soft_caps_unless_full_interval(self) -> None:
        versions = {f"2.{minor}.0": {} for minor in range(0, 30)}
        versions.update({f"3.{minor}.0": {} for minor in range(0, 30)})
        metadata = {"versions": versions}
        upgrade = MODULE.Upgrade("vue", "2.0.0", "3.29.0")
        selected, warnings, complete = MODULE.versions_in_range(metadata, upgrade, 0)
        self.assertEqual(len(selected), MODULE.INTERVAL_SOFT_CAP)
        self.assertFalse(complete)
        self.assertTrue(any("软截断" in item for item in warnings))
        selected_full, warnings_full, complete_full = MODULE.versions_in_range(
            metadata, upgrade, 0, full_interval=True
        )
        self.assertGreater(len(selected_full), MODULE.INTERVAL_SOFT_CAP)
        self.assertTrue(complete_full)
        self.assertFalse(warnings_full)

    def test_vue_cli4_loose_engines_does_not_mark_node26_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = MODULE.ManifestSnapshot(
                path=str(root / "package.json"),
                engines={"node": ">=8.9"},
                packages={
                    "@vue/cli-service": MODULE.ManifestPackage(
                        "@vue/cli-service", "devDependencies", "4.4.4"
                    )
                },
            )
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("26.5.1", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                runtime = MODULE.assess_node_runtime(root, manifest, [])
            self.assertNotEqual(runtime.status, "compatible-current")
            self.assertEqual(runtime.status, "runtime-missing")
            self.assertTrue(any("实跑推断" in item for item in runtime.warnings))
            self.assertTrue(any("practical Node" in item or "实跑推断" in item for item in runtime.blockers))

    def test_curated_alternative_does_not_change_recommended_action(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
            alternative_candidates=[MODULE.AlternativeCandidate("ky", "2.0.2", origin="curated-map")],
        )
        report.removal.status = "requires_migration"
        MODULE.reconcile_open_target_report(report)
        self.assertEqual(report.recommended_action, "research-replacement")
        self.assertTrue(any("由人决定" in item for item in report.decision_required))

    def test_reviewed_alternative_can_drive_replacement_and_replaces_curated_row(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
            alternative_candidates=[
                MODULE.AlternativeCandidate("ky", "2.0.2", origin="curated-map"),
                MODULE.AlternativeCandidate("ofetch", "1.5.1", origin="curated-map"),
            ],
        )
        report.removal.status = "requires_migration"
        MODULE.apply_analysis_evidence([report], {"axios": {"alternative_candidates": [{
            "package": "ky",
            "version": "2.0.2",
            "compliance_status": "eligible",
            "criteria_checked": ["node", "framework", "peer", "security", "license", "maintenance"],
            "evidence_urls": ["https://example.invalid/ky"],
        }]}})
        report.alternative_candidates[0].constraint_fit = "fits"
        MODULE.reconcile_open_target_report(report)
        self.assertEqual(
            [(item.package, item.origin) for item in report.alternative_candidates],
            [("ky", "analysis-evidence"), ("ofetch", "curated-map")],
        )
        self.assertEqual(report.recommended_action, "research-replacement")

    def test_disposition_options_cover_every_route_for_open_target(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
            alternative_candidates=[MODULE.AlternativeCandidate("ky", "2.0.2", origin="curated-map")],
        )
        report.removal.status = "requires_migration"
        MODULE.reconcile_open_target_report(report)
        options = {option.option: option for option in report.disposition_options}
        self.assertEqual(set(options), {row[0] for row in MODULE.DISPOSITION_OPTIONS})
        self.assertEqual(options["replace-with-alternative"].availability, "needs-research")
        self.assertEqual(options["native-platform-capability"].availability, "evidence-available")
        self.assertIn("fetch", options["native-platform-capability"].detail)
        self.assertEqual(options["internal-fork"].availability, "needs-research")

    def test_exact_upgrade_gets_no_alternatives_or_disposition_menu(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.6.8", "1.7.9", intent="exact-upgrade"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="exact-upgrade",
        )
        MODULE.reconcile_open_target_report(report)
        self.assertEqual(report.alternative_candidates, [])
        self.assertEqual(report.disposition_options, [])

    def test_alternative_incompatible_with_project_node_is_flagged(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
            alternative_candidates=[
                MODULE.AlternativeCandidate("ky", "2.0.2", origin="curated-map", engines={"node": ">=22"}),
                MODULE.AlternativeCandidate("ofetch", "1.5.1", origin="curated-map"),
            ],
        )
        runtime = MODULE.NodeRuntimeAssessment()
        runtime.selected_project_node = "20.18.0"
        MODULE.flag_alternative_runtime_conflicts([report], runtime)
        self.assertTrue(any("不兼容" in item for item in report.alternative_candidates[0].disqualifiers))
        self.assertEqual(report.alternative_candidates[0].constraint_fit, "conflicts")
        self.assertEqual(report.alternative_candidates[1].disqualifiers, [])
        self.assertEqual(report.alternative_candidates[1].constraint_fit, "fits")

    def test_engines_satisfied_by_project_node_counts_as_fitting(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
            alternative_candidates=[
                MODULE.AlternativeCandidate("ofetch", "1.5.1", origin="curated-map", engines={"node": ">=18"}),
            ],
        )
        runtime = MODULE.NodeRuntimeAssessment()
        runtime.selected_project_node = "20.18.0"
        MODULE.flag_alternative_runtime_conflicts([report], runtime)
        self.assertEqual(report.alternative_candidates[0].constraint_fit, "fits")

    def test_alternative_runtime_check_is_skipped_without_selected_node(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
            alternative_candidates=[
                MODULE.AlternativeCandidate("ky", "2.0.2", origin="curated-map", engines={"node": ">=22"}),
            ],
        )
        MODULE.flag_alternative_runtime_conflicts([report], MODULE.NodeRuntimeAssessment())
        self.assertEqual(report.alternative_candidates[0].disqualifiers, [])

    def test_runtime_conflict_resolves_a_compatible_fallback_version(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
            alternative_candidates=[
                MODULE.AlternativeCandidate("ky", "2.0.2", origin="curated-map", engines={"node": ">=22"}),
            ],
        )
        runtime = MODULE.NodeRuntimeAssessment()
        runtime.selected_project_node = "20.18.0"
        metadata = {"versions": {
            "1.7.5": {"engines": {"node": ">=18"}},
            "1.8.0": {"engines": {"node": ">=18"}, "deprecated": "moved"},
            "2.0.2": {"engines": {"node": ">=22"}},
        }}
        args = MODULE.parse_args(["."])
        with patch.object(MODULE, "request_json", return_value=metadata):
            MODULE.flag_alternative_runtime_conflicts([report], runtime, args)
        candidate = report.alternative_candidates[0]
        self.assertEqual(candidate.constraint_fit, "conflicts")
        self.assertEqual(candidate.fallback_version, "1.7.5")
        self.assertTrue(any("1.7.5" in item for item in candidate.disqualifiers))

    def test_offline_runtime_conflict_reports_no_fallback_without_network(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
            alternative_candidates=[
                MODULE.AlternativeCandidate("ky", "2.0.2", origin="curated-map", engines={"node": ">=22"}),
            ],
        )
        runtime = MODULE.NodeRuntimeAssessment()
        runtime.selected_project_node = "20.18.0"
        args = MODULE.parse_args([".", "--offline"])
        with patch.object(MODULE, "request_json", side_effect=AssertionError("offline 不得联网")):
            MODULE.flag_alternative_runtime_conflicts([report], runtime, args)
        self.assertEqual(report.alternative_candidates[0].fallback_version, "")

    def test_peer_conflict_with_project_marks_candidate_as_conflicting(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="auto-assess",
            alternative_candidates=[
                MODULE.AlternativeCandidate("fits-pkg", "2.0.0", peer_dependencies={"react": ">=18"}),
                MODULE.AlternativeCandidate("breaks-pkg", "3.0.0", peer_dependencies={"react": "^16"}),
                MODULE.AlternativeCandidate("unknown-pkg", "1.0.0", peer_dependencies={"vue": "^3"}),
            ],
        )
        manifest = MODULE.ManifestSnapshot(packages={"react": MODULE.ManifestPackage("react", "dependencies", "^18.2.0")})
        lock = MODULE.LockSnapshot(kind="npm", direct_versions={"react": "18.3.1"})
        MODULE.assess_alternative_constraint_fit([report], manifest, lock)
        self.assertEqual(
            [(item.package, item.constraint_fit) for item in report.alternative_candidates],
            [("fits-pkg", "fits"), ("breaks-pkg", "conflicts"), ("unknown-pkg", "unknown")],
        )

    def test_candidate_ranking_follows_declared_signal_priority(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="auto-assess",
            alternative_candidates=[
                MODULE.AlternativeCandidate("old-fit", "1.0.0", origin="curated-map", constraint_fit="fits", published="2020-01-01", license="MIT"),
                MODULE.AlternativeCandidate("conflicting", "9.0.0", origin="curated-map", constraint_fit="conflicts", published="2026-07-01", license="MIT"),
                MODULE.AlternativeCandidate("fresh-fit", "2.0.0", origin="curated-map", constraint_fit="fits", published="2026-06-01", license="MIT"),
                MODULE.AlternativeCandidate("deprecated-fit", "3.0.0", origin="curated-map", constraint_fit="fits", published="2026-07-20", license="MIT", deprecated=True),
                MODULE.AlternativeCandidate("reviewed", "4.0.0", origin="analysis-evidence", constraint_fit="unknown", published="2019-01-01"),
            ],
        )
        MODULE.rank_alternative_candidates([report])
        self.assertEqual(
            [item.package for item in report.alternative_candidates],
            ["reviewed", "fresh-fit", "old-fit", "deprecated-fit", "conflicting"],
        )
        self.assertEqual([item.rank for item in report.alternative_candidates], [1, 2, 3, 4, 5])
        self.assertEqual(
            report.alternative_candidates[1].rank_signals,
            [
                "human-reviewed=no", "project-constraint-fit=fits", "not-deprecated=yes",
                "recent-release=2026-06-01", "declared-license=MIT",
            ],
        )

    def test_ranking_does_not_change_recommended_action(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
            alternative_candidates=[MODULE.AlternativeCandidate("ky", "2.0.2", origin="curated-map", constraint_fit="fits")],
        )
        report.removal.status = "requires_migration"
        MODULE.reconcile_open_target_report(report)
        MODULE.rank_alternative_candidates([report])
        self.assertEqual(report.alternative_candidates[0].rank, 1)
        self.assertEqual(report.recommended_action, "research-replacement")

    def test_refactor_plan_is_built_from_real_call_sites(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("axios", "1.2.3", "", dependency_type="request", intent="auto-assess"),
            "https://www.npmjs.com/package/axios",
            analysis_mode="auto-assess",
        )
        points = [
            MODULE.CodeModificationPoint("axios", "src/request.ts", 1, "Direct package usage", "import axios", "", "", "", "P1", "high"),
            MODULE.CodeModificationPoint("axios", "package.json", 1, MODULE.DECLARATION_CATEGORY, "", "", "", "", "P1", "high"),
        ]
        plan = MODULE.build_refactor_plan(report, points)
        self.assertEqual(plan.status, "established")
        self.assertEqual(plan.stages, list(MODULE.REFACTOR_STAGES))
        self.assertTrue(any("src/request.ts" in group for group in plan.call_site_groups))
        self.assertTrue(any("fetch" in item for item in plan.native_routes))
        self.assertTrue(plan.validation_scope)

    def test_declaration_only_usage_leaves_refactor_plan_unestablished(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="auto-assess",
        )
        points = [MODULE.CodeModificationPoint("legacy", "package.json", 1, MODULE.DECLARATION_CATEGORY, "", "", "", "", "P1", "high")]
        plan = MODULE.build_refactor_plan(report, points)
        self.assertEqual(plan.status, "needs-research")
        self.assertEqual(plan.stages, [])
        self.assertTrue(any("运行时或动态用法" in item for item in plan.unknowns))

    def test_unremovable_package_with_call_sites_recommends_native_refactor(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="auto-assess",
        )
        report.removal.status = "not_viable"
        report.refactor_plan = MODULE.build_refactor_plan(report, [
            MODULE.CodeModificationPoint("legacy", "src/app.ts", 1, "Direct package usage", "", "", "", "", "P1", "high"),
        ])
        MODULE.reconcile_open_target_report(report)
        self.assertEqual(report.recommended_action, "plan-native-refactor")
        self.assertEqual(report.option_status, "available")

    def test_unremovable_package_without_any_route_is_blocked(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="auto-assess",
        )
        report.removal.status = "not_viable"
        MODULE.reconcile_open_target_report(report)
        self.assertEqual(report.recommended_action, "blocked-pending-options")
        self.assertEqual(report.option_status, "missing")
        self.assertEqual(report.research_status, "pending")
        self.assertTrue(any("不得标记为 complete" in item for item in report.decision_required))

    def test_option_gate_is_reported_without_overriding_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"legacy": "^1.0.0"}}), encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--assess", "legacy", "--offline",
                "--output-dir", str(root / "out"),
            ])
            bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.reports[0].option_status, "missing")
            markdown = MODULE.markdown_report(bundle)
            self.assertIn("选项完整性闸门", markdown)
            self.assertIn("未满足：`legacy`", markdown)
            self.assertIn("替代方案调研缺口", markdown)
            self.assertEqual(MODULE.validate_report_contract(markdown), [])

    def open_target_report(self, package: str = "legacy") -> "MODULE.PackageReport":
        return MODULE.PackageReport(
            MODULE.Upgrade(package, "1.2.3", "", intent="auto-assess"),
            f"https://www.npmjs.com/package/{package}",
            analysis_mode="auto-assess",
        )

    def provenance_project(self, root: Path, manifest: dict[str, object], lock: dict[str, object]) -> None:
        (root / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")

    def test_provenance_separates_direct_both_transitive_and_phantom(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.provenance_project(
                root,
                {"dependencies": {"declared-only": "^1.0.0", "shared": "^2.0.0", "parent-a": "^3.0.0"}},
                {
                    "lockfileVersion": 3,
                    "packages": {
                        "": {"dependencies": {"declared-only": "^1.0.0", "shared": "^2.0.0", "parent-a": "^3.0.0"}},
                        "node_modules/declared-only": {"version": "1.0.0"},
                        "node_modules/shared": {"version": "2.1.0"},
                        "node_modules/parent-a": {"version": "3.4.0", "dependencies": {"shared": "^2.0.0", "buried": "~4.1.0"}},
                        "node_modules/buried": {"version": "4.1.2"},
                        "node_modules/ghost": {"version": "5.0.0"},
                    },
                },
            )
            (root / "src").mkdir()
            (root / "src" / "app.js").write_text("import ghost from 'ghost';\nghost();\n", encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--offline",
                "--assess", "declared-only", "--assess", "shared",
                "--assess", "buried", "--assess", "ghost",
                "--output-dir", str(root / "out"),
            ])
            bundle = MODULE.build_bundle(args)
            kinds = {report.upgrade.package: report.provenance.kind for report in bundle.reports}
            self.assertEqual(kinds, {
                "declared-only": "direct", "shared": "both",
                "buried": "transitive", "ghost": "phantom",
            })
            tracks = {report.upgrade.package: report.primary_track for report in bundle.reports}
            self.assertEqual(tracks["buried"], "handle-parent")
            self.assertEqual(tracks["ghost"], "fix-phantom")
            buried = next(report for report in bundle.reports if report.upgrade.package == "buried")
            self.assertEqual([edge.package for edge in buried.provenance.parents], ["parent-a"])
            self.assertEqual(buried.provenance.chains, ["parent-a → buried"])
            ghost = next(report for report in bundle.reports if report.upgrade.package == "ghost")
            self.assertTrue(any("tsconfig paths" in item for item in ghost.provenance.unknowns))

    def test_pnpm_and_yarn_locks_also_yield_parent_edges(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pnpm = root / "pnpm-lock.yaml"
            pnpm.write_text(
                "lockfileVersion: '9.0'\n\nimporters:\n\n  .:\n    dependencies:\n"
                "      parent-a:\n        specifier: ^3.0.0\n        version: 3.4.0\n\n"
                "snapshots:\n\n  parent-a@3.4.0:\n    dependencies:\n      buried: 4.1.2\n\n"
                "  buried@4.1.2: {}\n",
                encoding="utf-8",
            )
            yarn = root / "yarn.lock"
            yarn.write_text(
                '# yarn lockfile v1\n\n\nparent-a@^3.0.0:\n  version "3.4.0"\n'
                '  dependencies:\n    buried "~4.1.0"\n\n'
                'buried@~4.1.0:\n  version "4.1.2"\n',
                encoding="utf-8",
            )
            for lock, requirement in ((pnpm, "4.1.2"), (yarn, "~4.1.0")):
                graph = MODULE.build_dependency_graph(lock, ["parent-a"])
                edges = graph.parents_of("buried")
                self.assertTrue(graph.supported, lock.name)
                self.assertEqual([(edge.parent, edge.parent_version, edge.requirement) for edge in edges],
                                 [("parent-a", "3.4.0", requirement)], lock.name)
                self.assertEqual(graph.paths_to("buried"), ([["parent-a", "buried"]], 1), lock.name)

    def test_missing_lock_leaves_parent_chains_unavailable(self) -> None:
        graph = MODULE.build_dependency_graph(None, ["declared"])
        self.assertFalse(graph.supported)
        report = self.open_target_report("buried")
        provenance = MODULE.assess_provenance(report, MODULE.ManifestSnapshot(), graph, [], set())
        self.assertEqual(provenance.kind, "unknown")
        self.assertTrue(any("未能解析依赖边" in item for item in provenance.unknowns))

    def test_phantom_detection_degrades_for_node_builtin_names(self) -> None:
        report = self.open_target_report("path")
        graph = MODULE.DependencyGraph(supported=True)
        point = MODULE.CodeModificationPoint(
            "path", "src/app.ts", 1, "Direct package usage", "import path from 'path'", "", "", "", "P1", "high",
        )
        provenance = MODULE.assess_provenance(report, MODULE.ManifestSnapshot(), graph, [point], set())
        self.assertEqual(provenance.kind, "unknown")
        self.assertTrue(any("Node 内置模块" in item for item in provenance.unknowns))

    def test_transitive_question_offers_parents_override_and_feature_removal(self) -> None:
        report = self.open_target_report("buried")
        report.provenance = MODULE.ProvenanceAssessment(
            kind="transitive",
            parents=[
                MODULE.ParentEdge("parent-a", "3.4.0", "~4.1.0", latest_stable="4.0.0", fix_available="dropped"),
                MODULE.ParentEdge("parent-b", "1.0.0", "^4.0.0"),
            ],
            chains=["parent-a → buried"],
            override_version="4.3.0",
        )
        MODULE.assign_primary_track(report)
        question = MODULE.build_confirmation_question(report)
        followups = MODULE.build_parent_followups(report)
        self.assertEqual(report.primary_track, "handle-parent")
        self.assertEqual(
            [option.option_id for option in question.options],
            ["handle-parent", "pin-override:buried@4.3.0", "remove-feature", "other"],
        )
        self.assertIn("parent-a", question.options[0].detail)
        self.assertEqual([item.package for item in followups], ["buried<-parent-a", "buried<-parent-b"])
        self.assertEqual(followups[0].options[0].option_id, "parent-upgrade:parent-a@4.0.0")

    def test_transitive_without_parents_is_blocked_rather_than_asked(self) -> None:
        report = self.open_target_report("buried")
        report.provenance = MODULE.ProvenanceAssessment(kind="transitive")
        MODULE.assign_primary_track(report)
        question = MODULE.build_confirmation_question(report)
        self.assertEqual(question.status, "blocked")
        self.assertIn("未解析出父包", question.blocked_reason)
        self.assertTrue(question.prerequisites)

    def test_both_removal_says_the_package_stays_as_a_transitive_dependency(self) -> None:
        report = self.open_target_report("shared")
        report.removal.status = "safe_removal_candidate"
        report.provenance = MODULE.ProvenanceAssessment(
            kind="both",
            parents=[MODULE.ParentEdge("parent-a", "3.4.0", "^2.0.0")],
            chains=["parent-a → shared"],
        )
        MODULE.assign_primary_track(report)
        question = MODULE.build_confirmation_question(report)
        self.assertEqual(report.primary_track, "remove")
        self.assertIn("handle-parent", report.alternate_tracks)
        self.assertIn("仍将作为传递依赖存在", question.options[0].label)
        self.assertIn("switch:handle-parent", [option.option_id for option in question.options])

    def test_override_version_is_the_lowest_that_satisfies_every_parent(self) -> None:
        report = self.open_target_report("buried")
        report.provenance = MODULE.ProvenanceAssessment(
            kind="transitive",
            parents=[
                MODULE.ParentEdge("parent-a", "3.4.0", ">=4.1.0"),
                MODULE.ParentEdge("parent-b", "1.0.0", "^4.0.0"),
            ],
        )
        registry = {"versions": {
            "4.0.9": {}, "4.1.0": {"engines": {"node": ">=22"}}, "4.2.0": {}, "5.0.0": {},
        }}
        args = MODULE.parse_args([".", "--assess", "buried", "--no-upstream-evidence"])
        with unittest.mock.patch.object(MODULE, "request_json", return_value=registry):
            MODULE.resolve_override_version(report, "20.11.1", args)
        self.assertEqual(report.provenance.override_version, "4.2.0")
        self.assertEqual(report.provenance.override_breaks, [])

    def test_override_names_the_parent_ranges_it_breaks(self) -> None:
        report = self.open_target_report("buried")
        report.provenance = MODULE.ProvenanceAssessment(
            kind="transitive",
            parents=[
                MODULE.ParentEdge("parent-a", "3.4.0", "^4.0.0"),
                MODULE.ParentEdge("parent-b", "1.0.0", "^5.0.0"),
            ],
        )
        registry = {"versions": {"4.2.0": {}, "5.0.0": {}}}
        args = MODULE.parse_args([".", "--assess", "buried", "--no-upstream-evidence"])
        with unittest.mock.patch.object(MODULE, "request_json", return_value=registry):
            MODULE.resolve_override_version(report, "", args)
        self.assertEqual(report.provenance.override_version, "4.2.0")
        self.assertEqual(report.provenance.override_breaks, ["parent-b@1.0.0 要求 ^5.0.0"])

    def test_parent_fix_flags_parents_that_no_longer_depend_on_the_package(self) -> None:
        report = self.open_target_report("buried")
        report.provenance = MODULE.ProvenanceAssessment(
            kind="transitive",
            parents=[MODULE.ParentEdge("parent-a", "3.4.0", "~4.1.0")],
        )
        args = MODULE.parse_args([".", "--assess", "buried", "--no-upstream-evidence"])
        with unittest.mock.patch.object(
            MODULE, "request_json",
            return_value={"versions": {"4.0.0": {"dependencies": {}}}, "dist-tags": {"latest": "4.0.0"}},
        ):
            MODULE.flag_parent_fix_availability(report, args)
        edge = report.provenance.parents[0]
        self.assertEqual(edge.fix_available, "dropped")
        self.assertEqual(edge.latest_stable, "4.0.0")

    def test_zero_hit_scan_waits_for_removal_evidence_instead_of_asking(self) -> None:
        report = self.open_target_report()
        report.removal.status = "uncertain"
        report.removal.coverage_checked = ["runtime"]
        MODULE.assign_primary_track(report)
        question = MODULE.build_confirmation_question(report)
        self.assertEqual(report.primary_track, "pending-removal-evidence")
        self.assertEqual(question.status, "blocked")
        self.assertEqual(question.options, [])
        self.assertTrue(any("动态" in item for item in question.prerequisites))

    def test_track_routes_to_replace_when_a_package_version_exists(self) -> None:
        report = self.open_target_report()
        report.removal.status = "requires_migration"
        report.alternative_candidates = [MODULE.AlternativeCandidate(
            "ky", "1.9.0", compliance_status="eligible", constraint_fit="fits",
            criteria_checked=["node", "framework", "peer", "security", "license", "maintenance"],
            evidence_urls=["https://example.invalid/ky"],
        )]
        report.refactor_plan = MODULE.build_refactor_plan(report, [
            MODULE.CodeModificationPoint("legacy", "src/app.ts", 1, "Direct package usage", "", "", "", "", "P1", "high"),
        ])
        MODULE.assign_primary_track(report)
        question = MODULE.build_confirmation_question(report)
        self.assertEqual(report.primary_track, "replace")
        # requires_migration is not a safe removal candidate, so remove is not an alternate track
        self.assertEqual(sorted(report.alternate_tracks), ["native-refactor"])
        ids = [option.option_id for option in question.options]
        self.assertEqual(ids[0], "replace:ky@1.9.0")
        self.assertEqual(ids[-1], "other")
        self.assertIn("switch:native-refactor", ids)
        self.assertNotIn("switch:remove", ids)
        self.assertFalse(any(option_id.startswith("same-package:") for option_id in ids))

    def test_track_falls_back_to_native_refactor_without_package_options(self) -> None:
        report = self.open_target_report()
        report.removal.status = "not_viable"
        report.refactor_plan = MODULE.build_refactor_plan(report, [
            MODULE.CodeModificationPoint("legacy", "src/app.ts", 4, "Direct package usage", "legacy()", "", "", "", "P1", "high"),
        ])
        MODULE.assign_primary_track(report)
        question = MODULE.build_confirmation_question(report)
        self.assertEqual(report.primary_track, "native-refactor")
        self.assertEqual(question.status, "ready")
        ids = [option.option_id for option in question.options]
        self.assertEqual(ids[0], "native-refactor")
        self.assertEqual(ids[-1], "other")
        self.assertNotIn("reject-native-refactor", ids)

    def test_reject_native_refactor_records_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "chosen.json"
            path.write_text(json.dumps({"decisions": [{
                "package": "legacy", "choice": "reject-native-refactor",
            }]}), encoding="utf-8")
            decisions, warnings = MODULE.load_decision_record(path)
            self.assertEqual(decisions, [])
            self.assertTrue(any("已废除" in item for item in warnings))

    def test_refactor_plan_grades_scale_and_lists_every_call_site(self) -> None:
        report = self.open_target_report()
        report.upgrade.dependency_type = "request"
        points = [
            MODULE.CodeModificationPoint("legacy", f"src/services/api{index}.ts", index, "Axios client API", "legacy.get()", "", "", "", "P1", "high")
            for index in range(1, 8)
        ]
        plan = MODULE.build_refactor_plan(report, points)
        self.assertEqual(len(plan.actions), 7)
        self.assertIn("超时", " ".join(plan.parity_checks))
        self.assertEqual(plan.scale, "M")
        self.assertIn("调用点 7 个、文件 7 个、跨公共包装器", plan.scale_basis)
        self.assertTrue(any("公共包装器" in item for item in plan.impact_surface))

    def test_unestablished_plan_reports_no_scale_and_no_call_site_table(self) -> None:
        report = self.open_target_report()
        plan = MODULE.build_refactor_plan(report, [
            MODULE.CodeModificationPoint("legacy", "package.json", 1, MODULE.DECLARATION_CATEGORY, "", "", "", "", "P2", "high"),
        ])
        self.assertEqual(plan.status, "needs-research")
        self.assertEqual(plan.scale, "")
        self.assertEqual(plan.actions, [])
        self.assertEqual(plan.parity_checks, [])

    def test_refactor_scale_uses_fixed_thresholds(self) -> None:
        self.assertEqual(MODULE.refactor_scale(1, 3, False)[0], "S")
        self.assertEqual(MODULE.refactor_scale(1, 3, True)[0], "M")
        self.assertEqual(MODULE.refactor_scale(11, 3, False)[0], "L")
        self.assertEqual(MODULE.refactor_scale(2, 31, False)[0], "L")

    def test_confirmation_queue_is_rendered_with_ids_and_decision_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "^1.0.0"}}), encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "api.ts").write_text("import axios from 'axios';\naxios.get('/x');\n", encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--assess", "axios", "--offline",
                "--output-dir", str(root / "out"),
            ])
            bundle = MODULE.build_bundle(args)
            markdown = MODULE.markdown_report(bundle)
            self.assertEqual(bundle.decision_status, "needs_choice")
            self.assertIn("<!-- section: Human Confirmation Queue -->", markdown)
            self.assertIn("人工确认队列", markdown)
            # Offline curated leads put replace on a blocked evidence gate until
            # analysis-evidence exists; ready menus still include `other`.
            self.assertTrue(
                "| other |" in markdown or "尚无已复核" in markdown or "analysis-evidence" in markdown,
                markdown[-2000:],
            )
            self.assertIn("human-decisions.json", markdown)
            self.assertTrue("待人工确认" in markdown or "待人工选型" in markdown or "确认队列 blocked" in markdown)
            self.assertIn("exit `7`", markdown)
            self.assertIn("batch_implementation_gate", markdown)
            self.assertIn("下一动作=照确认队列向用户提问或补证据，不是等待放行", markdown)
            self.assertNotIn("一包一问", markdown)
            self.assertEqual(MODULE.validate_report_contract(markdown), [])

    def test_main_returns_7_when_open_target_needs_choice(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "^1.0.0"}}), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.2.3"}},
            }), encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "api.ts").write_text("import axios from 'axios';\naxios.get('/x');\n", encoding="utf-8")
            code = MODULE.main([
                str(root), "--assess", "axios", "--offline",
                "--output-dir", str(root / "out"),
            ])
            self.assertEqual(code, 7)
            report_path = root / "out" / "frontend-dependency-upgrade-report.md"
            self.assertTrue(report_path.is_file())
            text = report_path.read_text(encoding="utf-8")
            self.assertTrue(
                "待人工确认" in text or "待人工选型" in text or "待补证据" in text
            )
            self.assertIn("本轮确认阶段", text)
            self.assertIn("下一动作=照确认队列向用户提问或补证据，不是等待放行", text)

    def test_main_returns_0_after_open_target_decision_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "^1.0.0"}}), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.2.3"}},
            }), encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "api.ts").write_text("import axios from 'axios';\naxios.get('/x');\n", encoding="utf-8")
            decisions = root / "chosen.json"
            decisions.write_text(json.dumps({"decisions": [{
                "package": "axios", "track": "native-refactor", "choice": "native-refactor",
                "rationale": "test", "decided_at": "2026-07-25T22:00:00+08:00",
            }]}), encoding="utf-8")
            code = MODULE.main([
                str(root), "--assess", "axios", "--offline",
                "--decision-file", str(decisions),
                "--output-dir", str(root / "out"),
            ])
            self.assertEqual(code, 0)

    def test_recorded_decision_stops_the_question_and_is_not_an_approval(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "^1.0.0"}}), encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "api.ts").write_text("import axios from 'axios';\naxios.get('/x');\n", encoding="utf-8")
            decisions = root / "chosen.json"
            decisions.write_text(json.dumps({"decisions": [{
                "package": "axios", "track": "native-refactor", "choice": "native-refactor",
                "rationale": "无合规替代", "decided_at": "2026-07-25T22:00:00+08:00",
            }]}), encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--assess", "axios", "--offline",
                "--decision-file", str(decisions),
                "--output-dir", str(root / "out"),
            ])
            bundle = MODULE.build_bundle(args)
            report = bundle.reports[0]
            self.assertEqual(report.decision.status, "confirmed")
            self.assertEqual(report.confirmation.status, "decided")
            self.assertEqual(report.selection_status, "selected")
            self.assertEqual(report.recommended_action, MODULE.DISPOSITION_SELECTED_ACTION)
            markdown = MODULE.markdown_report(bundle)
            self.assertIn("人工决策记录", markdown)
            self.assertIn("disposition-selected", markdown)
            self.assertIn("本技能到此结束", markdown)

    def test_invalidated_decision_is_asked_again_with_the_reason(self) -> None:
        report = self.open_target_report()
        report.removal.status = "requires_migration"
        report.alternative_candidates = [MODULE.AlternativeCandidate(
            package="ky", version="1.14.3", rationale="", deprecated="已弃用",
        )]
        MODULE.assign_primary_track(report)
        report.confirmation = MODULE.build_confirmation_question(report)
        decision = MODULE.HumanDecision(
            package="legacy", track="replace", choice="replace:ky@1.14.3",
            selected_package="ky", selected_version="1.14.3",
        )
        MODULE.apply_decisions([report], [decision])
        self.assertEqual(decision.status, "invalidated")
        self.assertIn("弃用", decision.invalidation_reason)
        self.assertNotEqual(report.confirmation.status, "decided")
        self.assertTrue(report.confirmation.prompt.startswith("（原选择已失效"))

    def test_alternative_offers_up_to_three_exact_versions(self) -> None:
        metadata = {
            "versions": {
                "0.9.0": {}, "1.14.3": {}, "2.0.0-beta.1": {}, "2.0.2": {},
            },
        }
        self.assertEqual(MODULE.previous_major_stable(metadata, "2.0.2"), "1.14.3")
        self.assertEqual(MODULE.previous_major_stable(metadata, "0.9.0"), "")
        candidate = MODULE.AlternativeCandidate(
            package="ky", version="2.0.2", rationale="",
            fallback_version="1.14.3", conservative_version="1.14.3",
        )
        self.assertEqual(MODULE.alternative_version_options(candidate), "1.14.3（兼容项目 Node）")
        candidate.fallback_version = ""
        self.assertEqual(MODULE.alternative_version_options(candidate), "1.14.3（上一个大版本，保守）")

    def test_switch_answers_are_rejected_as_final_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "chosen.json"
            path.write_text(json.dumps({"decisions": [
                {"package": "axios", "choice": "switch:remove"},
            ]}), encoding="utf-8")
            decisions, warnings = MODULE.load_decision_record(path)
            self.assertEqual(decisions, [])
            self.assertTrue(any("不是最终选择" in item for item in warnings))

    def test_handle_parent_alone_is_not_a_final_decision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "chosen.json"
            path.write_text(json.dumps({"decisions": [
                {"package": "left-pad", "choice": "handle-parent"},
            ]}), encoding="utf-8")
            decisions, warnings = MODULE.load_decision_record(path)
            self.assertEqual(decisions, [])
            self.assertTrue(any("父包追问" in item for item in warnings))

    def test_parent_followups_complete_marks_disposition_selected(self) -> None:
        report = self.open_target_report()
        report.upgrade.package = "qs"
        report.provenance.kind = "transitive"
        report.provenance.parents = [
            MODULE.ParentEdge("express", "4.18.2", "^6.0.0", "4.19.0", "still-depends", ""),
        ]
        report.primary_track = "handle-parent"
        report.confirmation = MODULE.build_confirmation_question(report)
        report.parent_questions = MODULE.build_parent_followups(report)
        report.decision_status = "needs_choice"
        report.selection_status = "needs_explicit_choice"
        decision = MODULE.HumanDecision(
            package="qs<-express",
            track="handle-parent",
            choice="parent-upgrade:express@4.19.0",
        )
        MODULE.apply_decisions([report], [decision])
        self.assertEqual(report.selection_status, "selected")
        self.assertEqual(report.recommended_action, MODULE.DISPOSITION_SELECTED_ACTION)
        self.assertEqual(report.decision_status, "not_needed")

    def test_offline_reviewed_alternative_stays_selectable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "^1.0.0"}}), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.2.3"}},
            }), encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "api.ts").write_text("import axios from 'axios';\naxios.get('/x');\n", encoding="utf-8")
            evidence = root / "evidence.json"
            evidence.write_text(json.dumps({"packages": {"axios": {
                "alternative_candidates": [{
                    "package": "ky",
                    "version": "1.14.3",
                    "compliance_status": "eligible",
                    "criteria_checked": [
                        "node", "framework", "peer", "security", "license", "maintenance",
                    ],
                    "evidence_urls": ["https://example.invalid/ky"],
                }],
                "removal": {
                    "status": "requires_migration",
                    "coverage_checked": list(MODULE.REMOVAL_COVERAGE_AREAS),
                    "evidence": ["src/api.ts"],
                },
            }}}), encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--assess", "axios", "--offline",
                "--analysis-evidence-file", str(evidence),
                "--output-dir", str(root / "out"),
            ])
            report = MODULE.build_bundle(args).reports[0]
            self.assertEqual(report.primary_track, "replace")
            ids = [option.option_id for option in (report.confirmation.options if report.confirmation else [])]
            self.assertIn("replace:ky@1.14.3", ids)
            self.assertIn("other", ids)

    def test_alternate_track_questions_are_rendered_for_switch(self) -> None:
        report = self.open_target_report()
        report.removal.status = "requires_migration"
        report.alternative_candidates = [MODULE.AlternativeCandidate(
            "ky", "1.9.0", compliance_status="eligible", constraint_fit="fits",
            origin="analysis-evidence",
            criteria_checked=["node", "framework", "peer", "security", "license", "maintenance"],
            evidence_urls=["https://example.invalid/ky"],
        )]
        report.refactor_plan = MODULE.build_refactor_plan(report, [
            MODULE.CodeModificationPoint("legacy", "src/app.ts", 1, "Direct package usage", "", "", "", "", "P1", "high"),
        ])
        MODULE.assign_primary_track(report)
        report.confirmation = MODULE.build_confirmation_question(report)
        report.alternate_questions = MODULE.build_alternate_track_questions(report)
        self.assertEqual(report.primary_track, "replace")
        self.assertTrue(any(item.track == "native-refactor" for item in report.alternate_questions))
        bundle = MODULE.AnalysisBundle(
            "t", "now", ".", "draft", [report], [], [], MODULE.ManifestSnapshot(),
            MODULE.LockSnapshot(), MODULE.LockSnapshot(), MODULE.LockSnapshot(), [],
            decision_status="needs_choice",
        )
        markdown = "\n".join(MODULE.render_confirmation_queue(bundle))
        self.assertIn("改轨问题：`native-refactor`", markdown)

    def test_truncated_cell_stays_on_one_markdown_row(self) -> None:
        row = "| " + " | ".join(MODULE.md_cell(value) for value in ("a" * 900, "b", "c")) + " |"
        self.assertNotIn("\n", row)
        self.assertEqual(len(MODULE.split_markdown_row(row)), 3)

    def test_offline_assess_renders_alternatives_and_disposition_menu(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "src").mkdir()
            (root / "src" / "request.ts").write_text("import axios from 'axios';", encoding="utf-8")
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "1.6.8"}}), encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--assess", "axios", "--offline", "--output-dir", str(root / "out"),
            ])
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                markdown = MODULE.markdown_report(MODULE.build_bundle(args))
            self.assertEqual(MODULE.validate_report_contract(markdown), [])
            self.assertIn("#### 替代库候选", markdown)
            self.assertIn("#### 处置方案选项", markdown)
            self.assertIn("| 1 | ky | 待解析 | - | curated-map |", markdown)
            self.assertIn("#### 原生重构方向", markdown)
            self.assertIn("#### 替代方案调研任务", markdown)
            for option, _title, _applicability, _evidence in MODULE.DISPOSITION_OPTIONS:
                self.assertIn(f"| {option} |", markdown)

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
            self.assertEqual(bundle.reports[0].selection_status, "needs_explicit_choice")
            self.assertEqual(bundle.decision_status, "needs_choice")
            self.assertEqual(bundle.batch_implementation_gate, "frozen")
            self.assertEqual(bundle.reports[0].primary_track, MODULE.PROCEED_EXACT_TRACK)
            self.assertIsNotNone(bundle.reports[0].confirmation)
            self.assertEqual(bundle.reports[0].confirmation.track, MODULE.PROCEED_EXACT_TRACK)
            # Offline fixture has no project Node pin → exact upgrade blocked → defer/other only
            self.assertEqual(bundle.reports[0].confirmation.status, "ready")
            option_ids = [opt.option_id for opt in bundle.reports[0].confirmation.options]
            self.assertIn("defer", option_ids)
            self.assertIn("other", option_ids)
            self.assertFalse(any(item.startswith("proceed:") for item in option_ids))
            self.assertIn("proceed-exact", markdown)
            self.assertIn("batch_implementation_gate", markdown)
            self.assertTrue(bundle.reports[0].constraints)
            self.assertEqual(set(bundle.report_paths), {"markdown", "json"})
            self.assertEqual(bundle.report_paths["markdown"], str(markdown_path))
            self.assertTrue(markdown_path.is_file())
            self.assertTrue(Path(bundle.report_paths["json"]).is_file())
            structured = json.loads(Path(bundle.report_paths["json"]).read_text(encoding="utf-8"))
            pending_packages = {item["package"] for item in structured["pending_human_decisions"]}
            self.assertIn("axios", pending_packages)
            self.assertIn("__node_runtime__", pending_packages)
            self.assertEqual(structured["batch_implementation_gate"], "frozen")
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
            args = MODULE.parse_args([
                str(root), "--upgrade", "axios:0.27.2:1.7.9", "--offline",
                "--output-dir", str(root / "out"),
            ])
            bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.status, "blocked")
            self.assertEqual(bundle.reports[0].baseline_status, "mismatch")

    def test_unknown_baseline_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "^1.0.0"}}), encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--assess", "axios", "--offline",
                "--output-dir", str(root / "out"),
            ])
            bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.status, "blocked")
            self.assertEqual(bundle.analysis_status, "blocked")
            self.assertEqual(bundle.reports[0].baseline_status, "unknown")

    def test_resolve_output_dir_uses_change_evidence_folder(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            change = root / "openspec" / "changes" / "admin-web-deps"
            change.mkdir(parents=True)
            output, note = MODULE.resolve_report_output_dir(root, None, str(change))
            self.assertEqual(output, (change / "evidence" / "frontend-dependency-upgrade").resolve())
            self.assertIn("change-dir", note)

    def test_resolve_output_dir_requires_change_dir_without_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            change = root / "openspec" / "changes" / "only-one"
            change.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "--change-dir"):
                MODULE.resolve_report_output_dir(root, None, None)

    def test_behavior_parity_constrains_every_route_without_picking_one(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("legacy", "1.2.3", "", intent="auto-assess"),
            "https://www.npmjs.com/package/legacy",
            analysis_mode="auto-assess",
            recommended_action="review-removal",
        )
        MODULE.apply_behavior_parity(report)
        self.assertEqual(report.recommended_action, "review-removal")
        self.assertEqual(report.decision_status, "needs_choice")
        self.assertEqual(report.selection_status, "needs_explicit_choice")
        self.assertTrue(any("行为守恒" in item for item in report.decision_required))
        self.assertTrue(any("同库升级不作为本轮选项" in item for item in report.constraints))

    def test_exact_target_behavior_constraint_still_requires_proceed_gate(self) -> None:
        report = MODULE.PackageReport(
            MODULE.Upgrade("antd", "4.24.16", "5.22.0", intent="exact-upgrade"),
            "https://www.npmjs.com/package/antd",
            analysis_mode="exact-upgrade",
            decision_status="not_needed",
            selection_status="selected",
        )
        MODULE.apply_behavior_parity(report)
        self.assertEqual(report.decision_status, "needs_choice")
        self.assertEqual(report.selection_status, "needs_explicit_choice")
        self.assertTrue(any("确认推进" in item for item in report.decision_required))
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
                            "criteria_checked": ["node", "framework", "peer", "security", "license", "maintenance"],
                            "evidence_urls": ["https://example.invalid/legacy-release"],
                        }],
                        "alternative_candidates": [{
                            "package": "replacement",
                            "version": "2.0.0",
                            "compliance_status": "eligible",
                            "criteria_checked": ["node", "framework", "peer", "security", "license", "maintenance"],
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
            self.assertEqual(report.target_candidates, [])
            self.assertTrue(any("已忽略 legacy.target_candidates" in item for item in report.warnings))
            self.assertEqual(report.alternative_candidates[0].package, "replacement")
            self.assertEqual(report.removal.status, "requires_migration")
            self.assertEqual(report.selection_status, "needs_explicit_choice")
            self.assertEqual(report.upgrade.reason, "停止维护")
            self.assertFalse(any(item.startswith("尚未建立治理") for item in report.decision_required))

    def test_eligible_replacement_requires_all_compatibility_and_governance_checks(self) -> None:
        with self.assertRaisesRegex(ValueError, "node"):
            MODULE.alternative_candidate_from_evidence("legacy", {
                "package": "replacement",
                "version": "2.0.0",
                "compliance_status": "eligible",
                "criteria_checked": ["security", "license", "maintenance"],
                "evidence_urls": ["https://example.invalid/replacement"],
            })

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
            args = MODULE.parse_args([
                str(root), "--assess", "legacy", "--offline", "--allow-behavior-change",
                "--output-dir", str(root / "out"),
            ])
            bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.behavior_parity_required, "no")
            self.assertEqual(bundle.reports[0].recommended_action, "review-removal")

    def _seed_frontend(self, root: Path, package: str = "pkg", version: str = "1.0.0") -> None:
        (root / "package.json").write_text(json.dumps({"dependencies": {package: version}}), encoding="utf-8")
        (root / "package-lock.json").write_text(json.dumps({
            "lockfileVersion": 3,
            "packages": {f"node_modules/{package}": {"version": version}},
        }), encoding="utf-8")

    def _sample_metadata(self) -> dict:
        return {
            "homepage": "https://example.test/pkg",
            "repository": {"url": "git+https://github.com/owner/pkg.git"},
            "versions": {
                "1.0.0": {"repository": {"url": "git+https://github.com/owner/pkg.git"}, "gitHead": "c100"},
                "1.1.0": {"repository": {"url": "git+https://github.com/owner/pkg.git"}, "gitHead": "c110"},
            },
            "time": {"1.0.0": "2024-01-01T00:00:00.000Z", "1.1.0": "2024-02-01T00:00:00.000Z"},
        }

    def test_upstream_evidence_persisted_for_exact_upgrade(self) -> None:
        metadata = self._sample_metadata()
        releases = {
            "1.1.0": {
                "body": "release details for 1.1.0 " * 5,
                "url": "https://github.com/owner/pkg/releases/tag/v1.1.0",
                "published": "2024-02-01",
                "name": "1.1.0",
                "tag": "v1.1.0",
                "source_kind": "github-release",
                "status": "substantive",
                "pointer_urls": [],
            }
        }
        changelog = "## 1.1.0\nChangelog body for 1.1.0\n"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._seed_frontend(root)
            output = root / "reports"
            args = MODULE.parse_args([
                str(root), "--upgrade", "pkg:1.0.0:1.1.0",
                "--output-dir", str(output), "--network-workers", "1",
            ])
            with (
                patch.object(MODULE, "request_json", return_value=metadata),
                patch.object(MODULE, "validate_version_repository", return_value=("confirmed", "ok", "")),
                patch.object(MODULE, "github_default_branch", return_value="main"),
                patch.object(MODULE, "fetch_github_releases", return_value=releases),
                patch.object(MODULE, "fetch_changelog", return_value=(changelog, "https://example.test/changelog")),
                patch.object(MODULE, "fetch_github_release_by_tag", return_value={}),
                patch.object(MODULE, "fetch_github_tag", return_value={}),
            ):
                bundle = MODULE.build_bundle(args, output)
                MODULE.write_bundle(bundle, args, output)
            evidence = output / "upstream-evidence"
            self.assertTrue(evidence.is_dir())
            self.assertTrue((evidence / "manifest.json").is_file())
            self.assertTrue((evidence / "pkg" / "registry.json").is_file())
            self.assertTrue((evidence / "pkg" / "1.1.0" / "release.md").is_file())
            self.assertTrue((evidence / "pkg" / "1.1.0" / "changelog.md").is_file())
            self.assertTrue((evidence / "pkg" / "1.1.0" / "sources.json").is_file())
            self.assertEqual(bundle.report_paths.get("upstream_evidence"), str(evidence.resolve()))
            self.assertIn("1.1.0", (evidence / "pkg" / "1.1.0" / "release.md").read_text(encoding="utf-8"))

    def test_online_network_failure_does_not_silently_read_local_upstream_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._seed_frontend(root)
            output = root / "reports"
            evidence = output / "upstream-evidence"
            MODULE.write_upstream_registry(evidence, "pkg", self._sample_metadata())
            note = MODULE.VersionNote(
                version="1.1.0",
                published="2024-02-01",
                change_type="minor",
                release_notes="cached release body for 1.1.0",
                changelog="cached changelog for 1.1.0",
                sources=["https://example.test/release"],
                evidence_status="partial",
                release_status="substantive",
                changelog_status="confirmed",
                repository_url="https://github.com/owner/pkg",
                repository_source="npm-version-metadata",
                repository_validation="confirmed",
            )
            MODULE.write_upstream_version_evidence(evidence, "pkg", note, evidence_origin="network")
            MODULE.update_upstream_manifest(
                evidence,
                package="pkg",
                from_version="1.0.0",
                to_version="1.1.0",
                versions=[{"version": "1.1.0", "status": "partial", "origin": "network"}],
            )
            args = MODULE.parse_args([
                str(root), "--upgrade", "pkg:1.0.0:1.1.0",
                "--output-dir", str(output), "--network-workers", "1",
            ])
            args.upstream_evidence_root = evidence
            with (
                patch.object(MODULE, "request_json", return_value=None),
                patch.object(MODULE, "request_text", return_value=None),
                patch.object(MODULE, "validate_version_repository", return_value=("candidate", "offline", "")),
                patch.object(MODULE, "github_default_branch", return_value="main"),
                patch.object(MODULE, "fetch_github_releases", return_value={}),
                patch.object(MODULE, "fetch_changelog", return_value=("", "")),
                patch.object(MODULE, "fetch_github_release_by_tag", return_value={}),
                patch.object(MODULE, "fetch_github_tag", return_value={}),
            ):
                report = MODULE.collect_package_report(MODULE.Upgrade("pkg", "1.0.0", "1.1.0"), args)
            self.assertFalse(report.used_local_upstream_evidence)
            self.assertNotIn("cached release body", report.notes[0].release_notes)
            self.assertIn("无法获取 npm 元数据", report.notes[0].release_notes)

    def test_offline_uses_local_upstream_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._seed_frontend(root)
            output = root / "reports"
            evidence = output / "upstream-evidence"
            MODULE.write_upstream_registry(evidence, "pkg", self._sample_metadata())
            note = MODULE.VersionNote(
                version="1.1.0",
                release_notes="offline local release",
                changelog="offline local changelog",
                sources=["https://example.test/r"],
                release_status="substantive",
                changelog_status="confirmed",
                evidence_status="partial",
            )
            MODULE.write_upstream_version_evidence(evidence, "pkg", note)
            args = MODULE.parse_args([
                str(root), "--upgrade", "pkg:1.0.0:1.1.0", "--offline",
                "--output-dir", str(output),
            ])
            args.upstream_evidence_root = evidence
            network_calls = {"json": 0, "text": 0}

            def track_json(*_a, **_k):
                network_calls["json"] += 1
                return None

            def track_text(*_a, **_k):
                network_calls["text"] += 1
                return None

            with (
                patch.object(MODULE, "request_json", side_effect=track_json),
                patch.object(MODULE, "request_text", side_effect=track_text),
            ):
                report = MODULE.collect_package_report(MODULE.Upgrade("pkg", "1.0.0", "1.1.0"), args)
            self.assertEqual(network_calls["json"], 0)
            self.assertEqual(network_calls["text"], 0)
            self.assertTrue(report.used_local_upstream_evidence)
            self.assertEqual(report.evidence_completeness, "partial")
            self.assertIn("offline local release", report.notes[0].release_notes)
            self.assertNotEqual(report.notes[0].evidence_status, "offline")

    def test_offline_without_local_evidence_stays_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._seed_frontend(root, "axios", "0.27.2")
            output = root / "reports"
            args = MODULE.parse_args([
                str(root), "--upgrade", "axios:0.27.2:1.7.9", "--offline",
                "--output-dir", str(output),
            ])
            report = MODULE.collect_package_report(MODULE.Upgrade("axios", "0.27.2", "1.7.9"), args)
            self.assertEqual(report.evidence_completeness, "offline")
            self.assertEqual(report.notes[0].evidence_status, "offline")
            self.assertIn("离线模式", report.notes[0].release_notes)
            self.assertFalse((output / "upstream-evidence").exists())

    def test_preflight_unreachable_exits_8_without_offline_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._seed_frontend(root)
            out = root / "out"

            def probe(url: str, _timeout: int) -> bool:
                return False

            with patch.object(MODULE, "probe_http_reachable", side_effect=probe):
                code = MODULE.main([
                    str(root), "--upgrade", "pkg:1.0.0:1.1.0",
                    "--output-dir", str(out),
                ])
            self.assertEqual(code, 8)
            self.assertFalse((out / "frontend-dependency-upgrade-report.md").exists())

    def test_preflight_registry_fail_github_ok_stays_online(self) -> None:
        args = MODULE.parse_args([".", "--upgrade", "pkg:1.0.0:1.1.0"])

        def probe(url: str, _timeout: int) -> bool:
            return "api.github.com" in url

        with patch.object(MODULE, "probe_http_reachable", side_effect=probe):
            result = MODULE.ensure_network_reachability(args)
        self.assertEqual(result["network_reachability"], "partial-github-only")
        self.assertFalse(result["awaiting_offline_confirmation"])

    def test_http_error_on_probe_counts_as_reachable(self) -> None:
        headers = {"X-RateLimit-Remaining": "0"}

        class FakeHTTPError(MODULE.urllib.error.HTTPError):
            def __init__(self) -> None:
                super().__init__(MODULE.GITHUB_PROBE_URL, 403, "forbidden", headers, None)

        with patch.object(MODULE.urllib.request, "urlopen", side_effect=FakeHTTPError()):
            self.assertTrue(MODULE.probe_http_reachable(MODULE.GITHUB_PROBE_URL, timeout=1))

    def test_empty_exact_interval_evidence_reprobes_github_and_exits_8_when_down(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._seed_frontend(root)
            output = root / "reports"
            metadata = self._sample_metadata()
            args = MODULE.parse_args([
                str(root), "--upgrade", "pkg:1.0.0:1.1.0",
                "--output-dir", str(output), "--network-workers", "1",
            ])
            with (
                patch.object(MODULE, "request_json", return_value=metadata),
                patch.object(MODULE, "validate_version_repository", return_value=("confirmed", "ok", "")),
                patch.object(MODULE, "github_default_branch", return_value="main"),
                patch.object(MODULE, "fetch_github_releases", return_value={}),
                patch.object(MODULE, "fetch_changelog", return_value=("", "")),
                patch.object(MODULE, "fetch_github_release_by_tag", return_value={}),
                patch.object(MODULE, "fetch_github_tag", return_value={}),
                patch.object(MODULE, "probe_http_reachable", return_value=False),
            ):
                with self.assertRaises(MODULE.NetworkReachabilityError) as ctx:
                    MODULE.collect_package_report(MODULE.Upgrade("pkg", "1.0.0", "1.1.0"), args)
            self.assertEqual(ctx.exception.stage, "exact-upgrade-github-evidence")
            self.assertTrue(ctx.exception.awaiting_offline_confirmation)

    def test_offline_flag_skips_reachability_probe(self) -> None:
        args = MODULE.parse_args([".", "--upgrade", "pkg:1.0.0:1.1.0", "--offline"])
        with patch.object(MODULE, "probe_http_reachable", side_effect=AssertionError("offline must not probe")):
            result = MODULE.ensure_network_reachability(args)
        self.assertEqual(result["network_reachability"], "skipped-offline")

    def test_no_upstream_evidence_disables_persist(self) -> None:
        metadata = self._sample_metadata()
        releases = {
            "1.1.0": {
                "body": "release details " * 10,
                "url": "https://example.test/1.1.0",
                "published": "",
                "name": "1.1.0",
                "tag": "v1.1.0",
                "source_kind": "github-release",
                "status": "substantive",
                "pointer_urls": [],
            }
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._seed_frontend(root)
            output = root / "reports"
            args = MODULE.parse_args([
                str(root), "--upgrade", "pkg:1.0.0:1.1.0",
                "--output-dir", str(output), "--no-upstream-evidence", "--network-workers", "1",
            ])
            with (
                patch.object(MODULE, "request_json", return_value=metadata),
                patch.object(MODULE, "validate_version_repository", return_value=("confirmed", "ok", "")),
                patch.object(MODULE, "github_default_branch", return_value="main"),
                patch.object(MODULE, "fetch_github_releases", return_value=releases),
                patch.object(MODULE, "fetch_changelog", return_value=("## 1.1.0\nfix\n", "https://example.test/c")),
                patch.object(MODULE, "fetch_github_release_by_tag", return_value={}),
                patch.object(MODULE, "fetch_github_tag", return_value={}),
            ):
                bundle = MODULE.build_bundle(args, output)
                MODULE.write_bundle(bundle, args, output)
            self.assertFalse((output / "upstream-evidence").exists())
            self.assertNotIn("upstream_evidence", bundle.report_paths)

    def test_cleanup_upstream_evidence_removes_directory(self) -> None:
        metadata = self._sample_metadata()
        releases = {
            "1.1.0": {
                "body": "release details " * 10,
                "url": "https://example.test/1.1.0",
                "published": "",
                "name": "1.1.0",
                "tag": "v1.1.0",
                "source_kind": "github-release",
                "status": "substantive",
                "pointer_urls": [],
            }
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._seed_frontend(root)
            output = root / "reports"
            args = MODULE.parse_args([
                str(root), "--upgrade", "pkg:1.0.0:1.1.0",
                "--output-dir", str(output), "--cleanup-upstream-evidence", "--network-workers", "1",
            ])
            with (
                patch.object(MODULE, "request_json", return_value=metadata),
                patch.object(MODULE, "validate_version_repository", return_value=("confirmed", "ok", "")),
                patch.object(MODULE, "github_default_branch", return_value="main"),
                patch.object(MODULE, "fetch_github_releases", return_value=releases),
                patch.object(MODULE, "fetch_changelog", return_value=("## 1.1.0\nfix\n", "https://example.test/c")),
                patch.object(MODULE, "fetch_github_release_by_tag", return_value={}),
                patch.object(MODULE, "fetch_github_tag", return_value={}),
            ):
                bundle = MODULE.build_bundle(args, output)
                markdown_path = MODULE.write_bundle(bundle, args, output)
            self.assertTrue(markdown_path.is_file())
            self.assertFalse((output / "upstream-evidence").exists())
            self.assertNotIn("upstream_evidence", bundle.report_paths)

    def test_assess_without_to_does_not_create_upstream_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._seed_frontend(root, "legacy", "1.2.3")
            output = root / "reports"
            args = MODULE.parse_args([
                str(root), "--assess", "legacy", "--offline",
                "--output-dir", str(output),
            ])
            bundle = MODULE.build_bundle(args, output)
            MODULE.write_bundle(bundle, args, output)
            self.assertFalse((output / "upstream-evidence").exists())
            self.assertNotIn("upstream_evidence", bundle.report_paths)

    def test_exact_upgrade_requires_proceed_confirmation_exit_7(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18"},
                "dependencies": {"axios": "1.6.8"},
            }), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.6.8"}},
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]})),
            ):
                code = MODULE.main([
                    str(root), "--upgrade", "axios::1.7.9", "--offline",
                    "--output-dir", str(root / "out"),
                ])
            self.assertEqual(code, 7)
            text = (root / "out" / "frontend-dependency-upgrade-report.md").read_text(encoding="utf-8")
            self.assertIn("proceed:axios@1.7.9", text)
            self.assertIn("batch_implementation_gate", text)
            self.assertIn("`frozen`", text)

    def test_exact_upgrade_implementation_blocked_offers_defer_not_proceed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18 <21"},
                "dependencies": {"axios": "1.6.8"},
            }), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.6.8"}},
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("26.5.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                code = MODULE.main([
                    str(root), "--upgrade", "axios::1.7.9", "--offline",
                    "--output-dir", str(root / "out"), "--json-output",
                ])
            self.assertEqual(code, 7)
            structured = json.loads(
                (root / "out" / "frontend-dependency-upgrade-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(structured["decision_status"], "needs_choice")
            self.assertEqual(structured["analysis_status"], "partial")
            report = structured["reports"][0]
            self.assertEqual(report["exact_upgrade_status"], "blocked")
            conf = report["confirmation"]
            self.assertEqual(conf["status"], "ready")
            option_ids = [opt["option_id"] for opt in conf["options"]]
            self.assertEqual(option_ids, ["defer", "other"])

    def test_deferred_exact_upgrade_exits_0_with_frozen_gate_not_exit_6(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18 <21"},
                "dependencies": {"axios": "1.6.8"},
            }), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.6.8"}},
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            decisions = root / "human-decisions.json"
            decisions.write_text(json.dumps({"version": 1, "decisions": [{
                "package": "axios",
                "track": "proceed-exact",
                "choice": "defer",
                "rationale": "node manager missing; finish Stage A",
            }]}), encoding="utf-8")
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("26.5.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=([], {})),
            ):
                code = MODULE.main([
                    str(root), "--upgrade", "axios::1.7.9", "--offline",
                    "--decision-file", str(decisions),
                    "--output-dir", str(root / "out"), "--json-output",
                ])
            self.assertEqual(code, 0)
            structured = json.loads(
                (root / "out" / "frontend-dependency-upgrade-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(structured["decision_status"], "not_needed")
            self.assertEqual(structured["analysis_status"], "partial")
            self.assertEqual(structured["batch_implementation_gate"], "frozen")
            self.assertTrue(
                any("Node" in item or "blocked" in item for item in structured["batch_gate_reasons"])
            )
            report = structured["reports"][0]
            self.assertEqual(report["recommended_action"], MODULE.DEFERRED_ACTION)
            self.assertEqual(report["selection_status"], "selected")
            self.assertEqual(report["exact_upgrade_status"], "blocked")
            self.assertEqual(report["confirmation"]["status"], "decided")

    def test_exact_upgrade_proceed_decision_clears_choice_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18"},
                "dependencies": {"axios": "1.6.8"},
            }), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.6.8"}},
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            decisions = root / "human-decisions.json"
            decisions.write_text(json.dumps({"decisions": [{
                "package": "axios",
                "track": "proceed-exact",
                "choice": "proceed:axios@1.7.9",
                "selected_package": "axios",
                "selected_version": "1.7.9",
                "rationale": "test proceed",
            }]}), encoding="utf-8")
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]})),
            ):
                code = MODULE.main([
                    str(root), "--upgrade", "axios::1.7.9", "--offline",
                    "--decision-file", str(decisions),
                    "--output-dir", str(root / "out"),
                ])
            self.assertEqual(code, 0)
            args = MODULE.parse_args([
                str(root), "--upgrade", "axios::1.7.9", "--offline",
                "--decision-file", str(decisions),
                "--output-dir", str(root / "out2"),
            ])
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]})),
            ):
                bundle = MODULE.build_bundle(args)
            report = bundle.reports[0]
            self.assertEqual(report.decision_status, "not_needed")
            self.assertEqual(report.selection_status, "selected")
            self.assertEqual(report.recommended_action, MODULE.PROCEED_SELECTED_ACTION)
            self.assertEqual(bundle.decision_status, "not_needed")
            self.assertEqual(bundle.batch_implementation_gate, "ready")

    def test_partition_upgrade_batches_splits_mixed_exact_and_open(self) -> None:
        upgrades = [
            MODULE.Upgrade("axios", "1.6.8", "1.7.9", intent="exact-upgrade"),
            MODULE.Upgrade("legacy", "1.0.0", "", intent="auto-assess"),
        ]
        batches = MODULE.partition_upgrade_batches(upgrades)
        self.assertEqual([item[0] for item in batches], ["exact", "open-target"])
        self.assertEqual([item.package for item in batches[0][1]], ["axios"])
        self.assertEqual([item.package for item in batches[1][1]], ["legacy"])

    def test_mixed_batch_main_writes_split_reports_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18"},
                "dependencies": {"axios": "1.6.8", "legacy": "1.0.0"},
            }), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/axios": {"version": "1.6.8"},
                    "node_modules/legacy": {"version": "1.0.0"},
                },
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "a.ts").write_text(
                "import axios from 'axios';\nimport legacy from 'legacy';\n",
                encoding="utf-8",
            )
            out = root / "evidence" / "frontend-dependency-upgrade"
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]})),
                patch.object(MODULE, "request_json", return_value={
                    "versions": {"1.6.8": {}, "1.7.9": {}},
                    "time": {"1.6.8": "2024-01-01", "1.7.9": "2024-06-01"},
                }),
                patch.object(MODULE, "fetch_github_releases", return_value={}),
                patch.object(MODULE, "fetch_changelog", return_value=("", "")),
                patch.object(MODULE, "validate_version_repository", return_value=("missing", "test", "")),
                patch.object(MODULE, "github_default_branch", return_value="main"),
            ):
                code = MODULE.main([
                    str(root),
                    "--upgrade", "axios::1.7.9",
                    "--assess", "legacy",
                    "--offline",
                    "--output-dir", str(out),
                ])
            self.assertIn(code, {0, 6, 7})
            self.assertTrue((out / "BATCH-INDEX.md").is_file())
            self.assertTrue((out / "exact" / "frontend-dependency-upgrade-report.md").is_file())
            self.assertTrue((out / "open-target" / "frontend-dependency-upgrade-report.md").is_file())

    def test_exact_upgrade_persists_upstream_evidence_even_when_release_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18"},
                "dependencies": {"axios": "1.6.8"},
            }), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.6.8"}},
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            out = root / "out"
            metadata = {
                "versions": {
                    "1.6.8": {"repository": {"url": "https://github.com/axios/axios.git"}},
                    "1.7.9": {"repository": {"url": "https://github.com/axios/axios.git"}},
                },
                "time": {"1.6.8": "2024-01-01T00:00:00.000Z", "1.7.9": "2024-06-01T00:00:00.000Z"},
                "repository": {"url": "https://github.com/axios/axios.git"},
            }
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]})),
                patch.object(MODULE, "request_json", return_value=metadata),
                patch.object(MODULE, "request_text", return_value=None),
                patch.object(MODULE, "fetch_github_releases", return_value={}),
                patch.object(MODULE, "fetch_changelog", return_value=("", "")),
                patch.object(MODULE, "validate_version_repository", return_value=("confirmed", "ok", "")),
                patch.object(MODULE, "github_default_branch", return_value="main"),
                # Empty release/changelog triggers a GitHub re-probe; keep online when reachable.
                patch.object(MODULE, "probe_http_reachable", return_value=True),
            ):
                args = MODULE.parse_args([
                    str(root), "--upgrade", "axios:1.6.8:1.7.9",
                    "--output-dir", str(out),
                ])
                bundle = MODULE.build_bundle(args)
                MODULE.write_bundle(bundle, args, out)
            evidence = out / "upstream-evidence"
            self.assertTrue(evidence.is_dir())
            self.assertTrue((evidence / "axios" / "registry.json").is_file())
            sources = evidence / "axios" / "1.7.9" / "sources.json"
            self.assertTrue(sources.is_file())
            payload = json.loads(sources.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("release_status"), "missing")
            self.assertEqual(payload.get("changelog_status"), "missing")
            self.assertTrue(any("upstream-evidence" in item for item in bundle.reports[0].warnings))

    def test_http_403_records_rate_limit_diagnostic(self) -> None:
        MODULE.reset_fetch_diagnostics("demo")
        headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1710000000"}

        class FakeHTTPError(MODULE.urllib.error.HTTPError):
            def __init__(self) -> None:
                super().__init__("https://api.github.com/repos/x/y/releases", 403, "forbidden", headers, None)

        with patch.object(MODULE.urllib.request, "urlopen", side_effect=FakeHTTPError()):
            text = MODULE.request_text("https://api.github.com/repos/x/y/releases", timeout=1, attempts=1)
        self.assertIsNone(text)
        diagnostics = MODULE.drain_fetch_diagnostics("demo")
        self.assertTrue(any("403" in item and "限流" in item for item in diagnostics))

    def test_batch_gate_stays_frozen_when_any_package_still_needs_choice(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18"},
                "dependencies": {"axios": "1.6.8", "legacy": "1.0.0"},
            }), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/axios": {"version": "1.6.8"},
                    "node_modules/legacy": {"version": "1.0.0"},
                },
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "a.ts").write_text("import axios from 'axios';\nimport legacy from 'legacy';\n", encoding="utf-8")
            upgrades = root / "upgrades.json"
            upgrades.write_text(json.dumps([
                {"package": "axios", "to": "1.7.9", "intent": "exact-upgrade"},
                {"package": "legacy", "intent": "auto-assess"},
            ]), encoding="utf-8")
            decisions = root / "human-decisions.json"
            decisions.write_text(json.dumps({"decisions": [{
                "package": "axios",
                "track": "proceed-exact",
                "choice": "proceed:axios@1.7.9",
                "selected_package": "axios",
                "selected_version": "1.7.9",
            }]}), encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--upgrades-file", str(upgrades), "--offline",
                "--decision-file", str(decisions),
                "--output-dir", str(root / "out"),
            ])
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]})),
            ):
                bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.decision_status, "needs_choice")
            self.assertEqual(bundle.batch_implementation_gate, "frozen")
            self.assertTrue(any("人工确认未完成" in item for item in bundle.batch_gate_reasons))

    def test_request_text_retries_incomplete_read_without_raising(self) -> None:
        class _BrokenBody:
            def read(self) -> bytes:
                raise MODULE.http.client.IncompleteRead(b"partial")

            def decode(self, *_args: object, **_kwargs: object) -> str:
                raise AssertionError("decode should not run")

        class _Response:
            headers = type("H", (), {"get_content_charset": staticmethod(lambda: "utf-8")})()

            def read(self) -> bytes:
                raise MODULE.http.client.IncompleteRead(b"partial")

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

        calls = {"n": 0}

        def fake_urlopen(_request: object, timeout: int = 0) -> _Response:
            calls["n"] += 1
            return _Response()

        with (
            patch.object(MODULE, "read_http_cache", return_value=(False, None)),
            patch.object(MODULE, "write_http_cache"),
            patch.object(MODULE.urllib.request, "urlopen", side_effect=fake_urlopen),
            patch.object(MODULE.time, "sleep", return_value=None),
        ):
            text = MODULE.request_text("https://example.test/releases", timeout=1, attempts=3)
        self.assertIsNone(text)
        self.assertEqual(calls["n"], 3)

    def test_code_scan_skips_openspec_and_report_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            src = root / "src"
            src.mkdir()
            (src / "main.js").write_text("import axios from 'axios'\n", encoding="utf-8")
            artifact_dir = root / "openspec" / "changes" / "x" / "evidence" / "frontend-dependency-upgrade"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "frontend-dependency-upgrade-report.json").write_text(
                json.dumps({"mockjs": {"version": "1.1.0"}}),
                encoding="utf-8",
            )
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "1.6.8"}}), encoding="utf-8")
            files, _warnings = MODULE.iter_code_files(root, max_files=100, max_file_bytes=1_000_000)
            relative = {str(path.relative_to(root)).replace("\\", "/") for path in files}
            self.assertIn("src/main.js", relative)
            self.assertIn("package.json", relative)
            self.assertFalse(any("openspec/" in item for item in relative))
            self.assertFalse(any("frontend-dependency-upgrade" in item for item in relative))

    def test_baseline_mismatch_skips_upstream_fetch_online(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({"dependencies": {"axios": "0.27.2"}}), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "0.26.0"}},
            }), encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--upgrade", "axios:0.27.2:1.7.9",
                "--output-dir", str(root / "out"),
            ])
            with (
                patch.object(MODULE, "ensure_network_reachability", return_value={"network_reachability": "ok"}),
                patch.object(MODULE, "request_json", side_effect=AssertionError("upstream should be skipped")) as request_json,
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]})),
            ):
                bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.analysis_status, "blocked")
            self.assertEqual(bundle.reports[0].baseline_status, "mismatch")
            self.assertTrue(any("跳过上游" in item for item in bundle.reports[0].warnings))
            request_json.assert_not_called()

    def test_finalize_review_sets_complete_when_gates_pass(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18"},
                "dependencies": {"axios": "1.6.8"},
            }), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.6.8"}},
            }), encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "main.js").write_text("import axios from 'axios'\n", encoding="utf-8")
            decisions = root / "human-decisions.json"
            decisions.write_text(json.dumps({"decisions": [{
                "package": "axios",
                "track": "proceed-exact",
                "choice": "proceed:axios@1.7.9",
                "selected_package": "axios",
                "selected_version": "1.7.9",
            }]}), encoding="utf-8")
            metadata = {
                "versions": {
                    "1.6.8": {"version": "1.6.8", "repository": {"type": "git", "url": "https://github.com/axios/axios.git"}},
                    "1.7.9": {"version": "1.7.9", "repository": {"type": "git", "url": "https://github.com/axios/axios.git"}},
                },
                "time": {"1.6.8": "2024-01-01T00:00:00.000Z", "1.7.9": "2024-06-01T00:00:00.000Z"},
            }

            def fake_request_json(url: str, _timeout: int) -> object:
                if "registry.npmjs.org/axios" in url and "/axios/" not in url.split("registry.npmjs.org/")[-1]:
                    return metadata
                return None

            args = MODULE.parse_args([
                str(root), "--upgrade", "axios:1.6.8:1.7.9",
                "--decision-file", str(decisions),
                "--output-dir", str(root / "out"),
                "--finalize-review",
                "--no-upstream-evidence",
            ])
            with (
                patch.object(MODULE, "ensure_network_reachability", return_value={"network_reachability": "ok"}),
                patch.object(MODULE, "request_json", side_effect=fake_request_json),
                patch.object(MODULE, "request_text", return_value=None),
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]})),
            ):
                bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.decision_status, "not_needed")
            self.assertEqual(bundle.analysis_status, "complete")
            self.assertEqual(bundle.status, "complete")
            self.assertEqual(MODULE.exit_code_for_bundle(bundle, args), 0)

    def test_finalize_review_rejected_for_offline(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": ">=18"},
                "dependencies": {"axios": "1.6.8"},
            }), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps({
                "lockfileVersion": 3,
                "packages": {"node_modules/axios": {"version": "1.6.8"}},
            }), encoding="utf-8")
            (root / ".nvmrc").write_text("20.18.0\n", encoding="utf-8")
            decisions = root / "human-decisions.json"
            decisions.write_text(json.dumps({"decisions": [{
                "package": "axios",
                "track": "proceed-exact",
                "choice": "proceed:axios@1.7.9",
                "selected_package": "axios",
                "selected_version": "1.7.9",
            }]}), encoding="utf-8")
            args = MODULE.parse_args([
                str(root), "--upgrade", "axios:1.6.8:1.7.9", "--offline",
                "--decision-file", str(decisions),
                "--output-dir", str(root / "out"),
                "--finalize-review",
            ])
            with (
                patch.object(MODULE, "current_host_node_runtime", return_value=("20.18.0", "C:/node/node.exe")),
                patch.object(MODULE, "detect_node_managers", return_value=(["nvm-windows"], {"nvm-windows": ["20.18.0"]})),
            ):
                bundle = MODULE.build_bundle(args)
            self.assertEqual(bundle.decision_status, "not_needed")
            self.assertEqual(bundle.analysis_status, "partial")
            self.assertNotEqual(bundle.status, "complete")
            self.assertEqual(MODULE.exit_code_for_bundle(bundle, args), 2)
            self.assertTrue(any("finalize-review 未通过" in item for item in bundle.decision_warnings))
            self.assertTrue(any("offline" in item.lower() or "离线" in item for item in bundle.decision_warnings))


if __name__ == "__main__":
    unittest.main()

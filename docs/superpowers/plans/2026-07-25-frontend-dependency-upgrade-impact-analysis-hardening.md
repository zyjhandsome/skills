# Frontend Dependency Upgrade Impact Analysis Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close P0 correctness/stability/robustness gaps so the skill’s generator and agent contract block non-frontend roots cleanly, never present host Node as selected project Node when status is `unknown`, and pass L0 tests plus L1/L2 contrast checks.

**Architecture:** Keep the Python generator as the deterministic collector/renderer. Add an explicit frontend-workspace preflight and tighten `assess_node_runtime` selection so empty project constraints cannot backfill `selected_project_node` from the host. Lock behavior with unit tests plus a checked-in synthetic fixture; use VoiceInk only as an external negative-control path in acceptance. Sync `SKILL.md` / references so agents cannot skip the gate.

**Tech Stack:** Python 3.10+ stdlib (`unittest`, `dataclasses`, `argparse`), existing `generate_upgrade_report.py` / `run_with_compatible_node.py`, Markdown report contract, host Node only as probe input (no skill-owned Node engines).

## Global Constraints

- Do not install, upgrade, remove, or run VoiceInk / fixture project scripts during analysis tasks.
- Do not mutate analyzed `.nvmrc`, `.node-version`, `.tool-versions`, or `package.json#engines` / `volta.node`.
- Preserve protocol Node statuses: `compatible-current` | `runtime-switch-required` | `runtime-missing` | `constraint-conflict` | `manager-missing` | `unknown`.
- Default report language remains Simplified Chinese; machine enums stay English.
- Success bar: `python tests/run_all.py` green; L1 synthetic dual-run stable; L2 VoiceInk (or equivalent no-manifest root) shows dedicated workspace failure semantics and does not label host Node as project Node.
- Spec source of truth: `docs/superpowers/specs/2026-07-25-frontend-dependency-upgrade-impact-analysis-eval-design.md`.

## File Structure

| File | Responsibility |
|---|---|
| `frontend-dependency-upgrade-impact-analysis/scripts/generate_upgrade_report.py` | Workspace preflight, Node selection fix, report header fields, exit codes |
| `frontend-dependency-upgrade-impact-analysis/tests/test_generate_upgrade_report.py` | Unit/integration locks for P0 behaviors |
| `frontend-dependency-upgrade-impact-analysis/fixtures/synthetic-frontend/*` | Checked-in L1 positive fixture (npm lock + pin vs modern host) |
| `frontend-dependency-upgrade-impact-analysis/SKILL.md` | Agent gate: resolve workspace before CLI; Node `unknown` forbids implementation advice |
| `frontend-dependency-upgrade-impact-analysis/references/node-runtime-compatibility.md` | Forbid host backfill when no authoritative constraints |
| `frontend-dependency-upgrade-impact-analysis/references/report-contract.md` | Document `importer_resolution` + selected Node empty-when-unknown |
| `frontend-dependency-upgrade-impact-analysis/references/lockfile-and-evidence.md` | Workspace/importer failure as baseline blocker |
| `docs/superpowers/specs/2026-07-25-frontend-dep-upgrade-eval-findings.md` | Short evaluation matrix filled during acceptance |

No new runtime dependencies. Do not split `generate_upgrade_report.py` in this plan unless a task exceeds ~80 new lines of unrelated logic; prefer focused helpers next to existing Node/manifest helpers.

---

### Task 1: Clear selected project Node when runtime status is `unknown`

**Files:**
- Modify: `frontend-dependency-upgrade-impact-analysis/scripts/generate_upgrade_report.py` (`assess_node_runtime`, ~2067–2125)
- Test: `frontend-dependency-upgrade-impact-analysis/tests/test_generate_upgrade_report.py`

**Interfaces:**
- Consumes: `assess_node_runtime(project_root, manifest, reports, evidence=..., lock=...) -> NodeRuntimeAssessment`
- Produces: when `status == "unknown"` because there are no authoritative `project_constraints`, `selected_project_node == ""`, `selected_manager == ""`, `compatible_installed_versions` does not treat unconstrained host as a project selection, `execution_readiness == "blocked"`

Root cause: `version_satisfies_all(version, [])` returns `True`, so the host Node enters `compatible_installed_versions` and becomes `selected_project_node` even after status is set to `unknown`.

- [x] **Step 1: Write the failing test**

Add to `UpgradeReportTests` in `tests/test_generate_upgrade_report.py`:

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest frontend-dependency-upgrade-impact-analysis.tests.test_generate_upgrade_report.UpgradeReportTests.test_node_runtime_unknown_without_constraints_does_not_select_host
```

From repo root, if package-style import fails, run:

```bash
cd frontend-dependency-upgrade-impact-analysis
python -m unittest tests.test_generate_upgrade_report.UpgradeReportTests.test_node_runtime_unknown_without_constraints_does_not_select_host -v
```

Expected: FAIL — `selected_project_node` is currently `"26.5.0"` (or similar host) and/or `compatible_installed_versions` is non-empty.

- [x] **Step 3: Write minimal implementation**

In `assess_node_runtime`, after the branch that sets `status = "unknown"` when `not assessment.project_constraints`, skip host-driven selection. Concrete change pattern:

```python
elif not assessment.project_constraints:
    assessment.status = "unknown"
    assessment.warnings.append("未发现权威项目 Node 约束；不能仅凭当前 Node 声称兼容")
    # Do not treat unconstrained host Node as a project-compatible candidate.
    assessment.compatible_installed_versions = []
    assessment.selected_project_node = ""
    assessment.selected_manager = ""
```

And guard the later selection block so it does not run when status is already `unknown` for missing constraints. Minimal safe approach: wrap the candidate/selection block (from building `candidate_versions` through assigning `selected_project_node`) in `if assessment.project_constraints:` **or** after selection completes, if `assessment.status == "unknown"` and not `assessment.project_constraints`, force-clear:

```python
if assessment.status == "unknown" and not assessment.project_constraints:
    assessment.compatible_installed_versions = []
    assessment.selected_project_node = ""
    assessment.selected_manager = ""
    assessment.recommended_strategy = "read-only-analysis"
```

Prefer the force-clear at the end of selection (before execution_readiness assignment) so evidence-provided `selected_project_node` still conflicts via existing conflict checks when constraints exist; when constraints are empty, evidence-selected node without constraints should remain blocked/unknown per current warning semantics — if evidence supplies `selected_project_node` with empty constraints, keep existing conflict/assignment behavior only when evidence is present; otherwise clear.

Exact end-of-function guard (place just before `execution_readiness` assignment):

```python
if assessment.status == "unknown" and not assessment.project_constraints:
    if not str(evidence.get("selected_project_node") or ""):
        assessment.compatible_installed_versions = []
        assessment.selected_project_node = ""
        assessment.selected_manager = ""
        assessment.recommended_strategy = "read-only-analysis"
```

- [x] **Step 4: Run test to verify it passes**

```bash
cd frontend-dependency-upgrade-impact-analysis
python -m unittest tests.test_generate_upgrade_report.UpgradeReportTests.test_node_runtime_unknown_without_constraints_does_not_select_host -v
```

Expected: PASS

Also re-run existing Node tests:

```bash
python -m unittest tests.test_generate_upgrade_report.UpgradeReportTests.test_node_runtime_switches_when_host_node_conflicts_with_project tests.test_generate_upgrade_report.UpgradeReportTests.test_node_runtime_conflicting_pins_block -v
```

Expected: PASS

- [x] **Step 5: Commit**

```bash
git add frontend-dependency-upgrade-impact-analysis/scripts/generate_upgrade_report.py frontend-dependency-upgrade-impact-analysis/tests/test_generate_upgrade_report.py
git commit -m "fix(frontend-dep-upgrade): do not select host Node when project constraints are unknown"
```

---

### Task 2: Frontend workspace preflight gate

**Files:**
- Modify: `frontend-dependency-upgrade-impact-analysis/scripts/generate_upgrade_report.py` (`AnalysisBundle`, `build_bundle`, `markdown_report`, `main`)
- Test: `frontend-dependency-upgrade-impact-analysis/tests/test_generate_upgrade_report.py`

**Interfaces:**
- Consumes: `project_root`, optional `--after-package-json` / `--before-package-json`
- Produces:
  - `resolve_frontend_workspace(project_root: Path, args: argparse.Namespace) -> FrontendWorkspaceResolution`
  - `FrontendWorkspaceResolution(status: str, manifest_path: str, reason: str)` where `status` is `"confirmed"` or `"failed"`
  - `AnalysisBundle.importer_resolution: str` (`"confirmed"` | `"failed"`)
  - On `failed`: `analysis_status="blocked"`, `status="blocked"`, pending decision for `__frontend_workspace__`, package `change_type` not `"added"`, `recommended_action` steers to resolve workspace; `main` returns exit code `5`

- [x] **Step 1: Write the failing tests**

```python
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
```

Also add:

```python
def test_main_returns_5_when_frontend_workspace_missing(self) -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        code = MODULE.main([
            str(root), "--upgrade", "axios::1.7.9", "--offline",
            "--output-dir", str(root / "out"),
        ])
        self.assertEqual(code, 5)
        self.assertTrue((root / "out" / "frontend-dependency-upgrade-report.md").is_file())
```

- [x] **Step 2: Run tests to verify they fail**

```bash
cd frontend-dependency-upgrade-impact-analysis
python -m unittest \
  tests.test_generate_upgrade_report.UpgradeReportTests.test_resolve_frontend_workspace_fails_without_package_json \
  tests.test_generate_upgrade_report.UpgradeReportTests.test_build_bundle_blocks_when_frontend_workspace_missing \
  tests.test_generate_upgrade_report.UpgradeReportTests.test_main_returns_5_when_frontend_workspace_missing -v
```

Expected: FAIL — `resolve_frontend_workspace` missing / `importer_resolution` missing.

- [x] **Step 3: Write minimal implementation**

Add near manifest helpers:

```python
@dataclass
class FrontendWorkspaceResolution:
    status: str  # confirmed | failed
    manifest_path: str = ""
    reason: str = ""


def resolve_frontend_workspace(project_root: Path, args: argparse.Namespace) -> FrontendWorkspaceResolution:
    candidates: list[Path] = []
    if getattr(args, "after_package_json", None):
        candidates.append(Path(args.after_package_json))
    if getattr(args, "before_package_json", None):
        candidates.append(Path(args.before_package_json))
    candidates.append(project_root / "package.json")
    for path in candidates:
        resolved = path if path.is_absolute() else (project_root / path)
        if resolved.is_file():
            return FrontendWorkspaceResolution("confirmed", str(resolved.resolve()), "")
    return FrontendWorkspaceResolution(
        "failed",
        "",
        "未找到 frontend workspace 的 package.json；请显式传入前端目录或 --after-package-json，勿对非前端仓库静默分析。",
    )
```

Extend `AnalysisBundle` with:

```python
importer_resolution: str = "confirmed"
```

In `build_bundle`:
1. Call `resolution = resolve_frontend_workspace(project_root, args)` early after path checks.
2. Set `bundle`-bound `importer_resolution = resolution.status`.
3. If `failed`:
   - force `status = "blocked"`, `analysis_status = "blocked"`
   - append pending decision `{"package": "__frontend_workspace__", "selection_status": "failed", "decisions": resolution.reason}`
   - for each package report after baseline/risk: set `change_type = "unknown"` if it was `"added"`; set `recommended_action = "resolve-frontend-workspace"`; append a constraint/warning with `resolution.reason`
4. Still produce the report (investigative draft) — do not raise — so agents get a blocked packet.

In `markdown_report` header bullets, add after project root:

```python
f"- 前端 workspace 解析：`{bundle.importer_resolution}`",
```

In `main`, after writing bundle:

```python
if bundle.importer_resolution == "failed":
    print(bundle.pending_human_decisions[0]["decisions"] if bundle.pending_human_decisions else "前端 workspace 未解析", file=sys.stderr)
    return 5
```

Place this check before or after baseline exit 3; workspace failure should win (return 5 even if baseline also unknown).

- [x] **Step 4: Run tests to verify they pass**

```bash
cd frontend-dependency-upgrade-impact-analysis
python -m unittest \
  tests.test_generate_upgrade_report.UpgradeReportTests.test_resolve_frontend_workspace_fails_without_package_json \
  tests.test_generate_upgrade_report.UpgradeReportTests.test_build_bundle_blocks_when_frontend_workspace_missing \
  tests.test_generate_upgrade_report.UpgradeReportTests.test_main_returns_5_when_frontend_workspace_missing -v
python tests/run_all.py
```

Expected: new tests PASS; full suite green (fix any older tests that assumed missing package.json still yields `draft` / exit 3 only — update those assertions to `blocked` / exit 5).

- [x] **Step 5: Commit**

```bash
git add frontend-dependency-upgrade-impact-analysis/scripts/generate_upgrade_report.py frontend-dependency-upgrade-impact-analysis/tests/test_generate_upgrade_report.py
git commit -m "feat(frontend-dep-upgrade): block analysis when frontend workspace package.json is missing"
```

---

### Task 3: Synthetic L1 fixture and dual-run / Node pin tests

**Files:**
- Create: `frontend-dependency-upgrade-impact-analysis/fixtures/synthetic-frontend/package.json`
- Create: `frontend-dependency-upgrade-impact-analysis/fixtures/synthetic-frontend/.nvmrc`
- Create: `frontend-dependency-upgrade-impact-analysis/fixtures/synthetic-frontend/package-lock.json`
- Create: `frontend-dependency-upgrade-impact-analysis/fixtures/synthetic-frontend/src/main.js`
- Modify: `frontend-dependency-upgrade-impact-analysis/tests/test_generate_upgrade_report.py`

**Interfaces:**
- Consumes: fixture root as `project_root`
- Produces: offline exact-upgrade bundle with `importer_resolution="confirmed"`, Node status in `{runtime-switch-required, runtime-missing, manager-missing}` (not `compatible-current` when host is patched to 26.5.0), dual-run equal key fields

- [x] **Step 1: Create fixture files**

`package.json`:

```json
{
  "name": "synthetic-frontend",
  "private": true,
  "engines": { "node": ">=18 <21" },
  "dependencies": {
    "axios": "1.6.8"
  }
}
```

`.nvmrc`:

```text
20.18.0
```

`package-lock.json` (lockfileVersion 3 minimal):

```json
{
  "name": "synthetic-frontend",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "synthetic-frontend",
      "dependencies": {
        "axios": "1.6.8"
      },
      "engines": { "node": ">=18 <21" }
    },
    "node_modules/axios": {
      "version": "1.6.8",
      "resolved": "https://registry.npmjs.org/axios/-/axios-1.6.8.tgz",
      "integrity": "sha512-fixture"
    }
  }
}
```

`src/main.js`:

```javascript
import axios from "axios";
export const client = axios.create({ timeout: 5000 });
```

- [x] **Step 2: Write failing integration tests**

```python
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic-frontend"


def test_synthetic_fixture_node_status_not_compatible_with_host_26(self) -> None:
    args = MODULE.parse_args([
        str(FIXTURE_ROOT),
        "--upgrade", "axios::1.7.9",
        "--offline",
        "--output-dir", str(FIXTURE_ROOT / ".tmp-report-a"),
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
    def run_once(tag: str):
        out = FIXTURE_ROOT / f".tmp-report-{tag}"
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
```

- [x] **Step 3: Run tests**

```bash
cd frontend-dependency-upgrade-impact-analysis
python -m unittest \
  tests.test_generate_upgrade_report.UpgradeReportTests.test_synthetic_fixture_node_status_not_compatible_with_host_26 \
  tests.test_generate_upgrade_report.UpgradeReportTests.test_synthetic_fixture_dual_run_is_stable -v
```

Expected: PASS if Tasks 1–2 done and fixture valid; if baseline/inference fails, fix fixture lock/`from` inference (`axios::1.7.9` should infer from lock `1.6.8`).

- [x] **Step 4: Commit**

```bash
git add frontend-dependency-upgrade-impact-analysis/fixtures/synthetic-frontend frontend-dependency-upgrade-impact-analysis/tests/test_generate_upgrade_report.py
git commit -m "test(frontend-dep-upgrade): add synthetic frontend fixture and Node dual-run locks"
```

Add `fixtures/synthetic-frontend/.tmp-report-*` to `frontend-dependency-upgrade-impact-analysis/.gitignore` if reports are written inside the fixture; or point `--output-dir` at `tempfile.TemporaryDirectory()` instead of fixture-local paths (preferred — update tests to use `tempfile` to avoid gitignore churn).

---

### Task 4: Sync agent contract and references

**Files:**
- Modify: `frontend-dependency-upgrade-impact-analysis/SKILL.md`
- Modify: `frontend-dependency-upgrade-impact-analysis/references/node-runtime-compatibility.md`
- Modify: `frontend-dependency-upgrade-impact-analysis/references/report-contract.md`
- Modify: `frontend-dependency-upgrade-impact-analysis/references/lockfile-and-evidence.md`
- Test: `frontend-dependency-upgrade-impact-analysis/tests/test_skill_structure.py` (keep line budget < 200)

**Interfaces:**
- Consumes: behaviors from Tasks 1–2
- Produces: docs that match CLI enums and exit code 5; SKILL still < 200 lines

- [x] **Step 1: Patch SKILL.md workflow**

In **Resolve scope and baseline**, after frontend workspace bullets, add an explicit CLI precondition:

```markdown
5. Before calling the generator, confirm the resolved frontend workspace contains `package.json` (or pass `--after-package-json`). If resolution fails, stop; the generator returns exit code `5` with `importer_resolution=failed` and must not be treated as an upgrade recommendation.
```

In **Node runtime compatibility gate**, add:

```markdown
7. When `node_runtime_status=unknown` (no authoritative project constraints), keep `selected_project_node` unset. Never recommend implementation commands or treat the host Node as the project runtime.
```

Renumber carefully; keep total lines < 200 (trim elsewhere if needed — prefer shortening examples over deleting gates).

- [x] **Step 2: Patch references**

`node-runtime-compatibility.md` §2 after the `unknown` bullet:

```markdown
- 无权威项目约束导致 `unknown`：`selected_project_node` 必须为空/`未建立`，禁止把本机当前 Node 回填为项目 Node；`compatible_installed_versions` 在无约束时不用于项目选型。
```

`report-contract.md` Upgrade Summary / 完成状态:

```markdown
- `importer_resolution`：`confirmed` 或 `failed`（失败时报告状态与 `analysis_status` 均为 `blocked`，并在待人工决策中包含 `__frontend_workspace__`）
- `selected_project_node`：仅在存在权威项目约束或经证据明确指定且通过校验时填写；`node_runtime_status=unknown` 且无约束时必须为空
```

`lockfile-and-evidence.md`: note that missing frontend `package.json` is a workspace/importer blocker equivalent in severity to unknown baseline for implementation gating.

- [x] **Step 3: Run structure tests**

```bash
cd frontend-dependency-upgrade-impact-analysis
python -m unittest tests.test_skill_structure -v
python tests/run_all.py
```

Expected: PASS; SKILL line count still < 200.

- [x] **Step 4: Commit**

```bash
git add frontend-dependency-upgrade-impact-analysis/SKILL.md frontend-dependency-upgrade-impact-analysis/references/node-runtime-compatibility.md frontend-dependency-upgrade-impact-analysis/references/report-contract.md frontend-dependency-upgrade-impact-analysis/references/lockfile-and-evidence.md
git commit -m "docs(frontend-dep-upgrade): align skill and refs with workspace and Node unknown gates"
```

---

### Task 5: Acceptance — L0/L1/L2 + evaluation findings

**Files:**
- Create: `docs/superpowers/specs/2026-07-25-frontend-dep-upgrade-eval-findings.md`
- Verify against: `D:\Hzhao\AI_Test\VoiceInk-main` (external; do not modify)

**Interfaces:**
- Consumes: hardened generator + fixture
- Produces: findings matrix with D1–D10 scores; VoiceInk command transcript summary

- [x] **Step 1: Run full unit suite (L0)**

```bash
cd frontend-dependency-upgrade-impact-analysis
python tests/run_all.py
```

Expected: OK (all tests).

- [x] **Step 2: L1 offline report smoke (optional manual)**

```bash
cd frontend-dependency-upgrade-impact-analysis
python scripts/generate_upgrade_report.py fixtures/synthetic-frontend \
  --upgrade axios::1.7.9 \
  --offline \
  --output-dir "$TEMP/synthetic-dep-report"
```

Expected: `importer_resolution=confirmed` in report; Node status not `compatible-current` on host 26.5 if pin is 20.x; `.nvmrc` unchanged.

- [x] **Step 3: L2 VoiceInk negative control**

```bash
python scripts/generate_upgrade_report.py "D:\Hzhao\AI_Test\VoiceInk-main" \
  --upgrade axios::1.7.9 \
  --offline \
  --output-dir "$TEMP/voiceink-dep-report-after"
echo Exit:$LASTEXITCODE
```

Expected:
- Exit code `5`
- Report contains `importer_resolution`=`failed` (or Chinese workspace failure)
- `analysis_status=blocked`
- `selected_project_node` empty / `未建立`
- No recommendation to `npm install` VoiceInk
- Do not modify any file under `D:\Hzhao\AI_Test\VoiceInk-main`

- [x] **Step 4: Write findings doc**

Create `docs/superpowers/specs/2026-07-25-frontend-dep-upgrade-eval-findings.md` with a short table:

| Dimension | Score | Notes |
|---|---|---|
| D2 Scope/baseline | Pass/Partial | VoiceInk exit 5 + failed importer |
| D5 Node gate | Pass/Partial | unknown clears selected node; synthetic pin vs 26.5 |
| D8 Stability | Pass/Partial | dual-run test |
| D9 Robustness | Pass/Partial | no-manifest path |
| … | … | fill remaining D1–D10 briefly |

List P0 items closed vs P1 backlog (multi-workspace auto-discovery, richer seven-factor explainability).

- [x] **Step 5: Commit findings**

```bash
git add docs/superpowers/specs/2026-07-25-frontend-dep-upgrade-eval-findings.md
git commit -m "docs(frontend-dep-upgrade): record post-hardening evaluation findings"
```

---

## Spec coverage self-review

| Spec requirement | Task |
|---|---|
| Dual-track eval + harden to success bar B | Tasks 1–5 |
| Workspace preflight / no silent non-frontend analysis | Task 2, 4, 5 L2 |
| Node unknown must not backfill host as project Node | Task 1, 4, 5 |
| Synthetic L1 + VoiceInk L2 | Tasks 3, 5 |
| SKILL/agent contract sync | Task 4 |
| Tests green + contrast trustworthy | Task 5 |
| P1 backlog only documented | Task 5 findings |
| No VoiceInk app modification | Global Constraints + Task 5 |

Placeholder scan: none intentional. Fixture temp dirs should use `tempfile` in tests (Task 3 note). Type names: `FrontendWorkspaceResolution`, `importer_resolution`, exit `5` used consistently across Tasks 2–5.

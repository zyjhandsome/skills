# Frontend Dependency Upgrade Impact Analysis — Evaluation & Hardening Design

Date: 2026-07-25  
Status: Approved for spec review (brainstorming)  
Skill path: `frontend-dependency-upgrade-impact-analysis/`

## 1. Purpose and success criteria

### 1.1 Purpose

Evaluate the skill for **agent practical usability** and **implementation quality**, then produce a hardening design focused on **correctness, stability, and robustness**, including **host Node vs project Node** semantics.

### 1.2 Outcomes (chosen)

- **B + C:** evaluation report plus actionable improvement design; emphasize whether an agent can stably produce a trustworthy decision packet.
- **Depth C:** static review + run existing tests + lightweight E2E contrast (synthetic positive fixture + real-repo negative control).
- **Success bar B:** after design approval and implementation planning, P0 gaps are fixed until **tests are green** and **contrast reports are semantically trustworthy**.

### 1.3 Out of scope

- Upgrading or modifying the VoiceInk application itself.
- Making optional orchestration tools a default Node axis.
- Broad UX/doc rewrites unrelated to trustworthy decisions.
- Treating report generation as implementation approval.

## 2. Evaluation architecture

### 2.1 Three layers under review

| Layer | Artifacts | Focus |
|---|---|---|
| A. Agent contract | `SKILL.md` + `references/*` | Followability, gates, ambiguity |
| B. Deterministic core | `scripts/generate_upgrade_report.py`, `scripts/run_with_compatible_node.py` | Correctness, stability, robustness |
| C. Verification assets | `tests/*` + contrast fixtures (to add) | Regression locks for P0 behavior |

### 2.2 Approach (chosen: dual-track)

1. Score a fixed dimension matrix with evidence.
2. Validate with:
   - L0: existing unit/structure tests
   - L1: synthetic frontend positive fixture
   - L2: VoiceInk negative control
3. Promote only blockers of the success bar to P0 hardening.

### 2.3 Environment baseline (host, not project)

Recorded at design time on the evaluation host:

| Runtime | Version / note |
|---|---|
| Host Node | `v26.5.0` (`D:\Program Files\nodejs\node.exe`) |
| Host Python | `3.14.6` (script runner; skill has no package.json engines) |
| Skill self-test | `57` tests OK via `tests/run_all.py` |
| Node version managers | Not detected in VoiceInk probe output (`未检测到`) |

The skill directory itself is Python-driven analysis tooling; it does not declare a required Node version for the skill. Node constraints apply to **analyzed frontend projects** and to **approved project-command execution**.

## 3. Evaluation dimensions and scoring

### 3.1 Severity

- **P0:** wrong decision, wrong implementation authorization, host runtime pollution, or silent analysis of the wrong target.
- **P1:** reduces trust/repeatability without directly causing wrong implementation.
- **P2:** polish; does not block success bar B.

Each dimension scores **Pass / Partial / Fail**.

### 3.2 Dimension table

| ID | Dimension | Looks for | Evidence | Default severity |
|---|---|---|---|---|
| D1 | Contract integrity | SKILL ↔ references ↔ CLI consistency; completable gates | docs + scripts | P0–P1 |
| D2 | Scope and baseline correctness | frontend workspace resolution; `from` inference; unknown/mismatch → blocked | locks + L2 | **P0** |
| D3 | Impact evidence quality | import/config chains; zero hits ≠ safe removal; version identity | generator + method refs | P0–P1 |
| D4 | Risk model repeatability | same inputs → same seven-factor total; overrides traceable | risk-model + tests | P1 |
| D5 | Node gate correctness | host vs project separation; enum semantics; no project-constraint mutation | node-runtime refs + L1 | **P0** |
| D6 | Safety boundary | no install/switch/scripts without granular approval | runner + Boundaries | **P0** |
| D7 | Agent operability | stable step execution; skipped gates | workflow rehearsal | P0–P1 |
| D8 | Stability / idempotence | dual-run field equality; cache predictability | dual-run + cache tests | **P0–P1** |
| D9 | Robustness / failure semantics | missing lock/frontend/network; offline honesty | fault fixtures + L2 | **P0** |
| D10 | Testability | P0 behaviors locked by automated tests | tests + fixtures | P1 |

### 3.3 Hard conditions

**Correctness (D2/D3/D5)**

1. Without a uniquely resolved frontend importer, do not silently analyze the whole repo.
2. Unknown baseline or conflicting claimed `from` → `analysis_status=blocked`, showing manifest/lock/claim.
3. `node_runtime_status` must be a protocol enum only:
   - `compatible-current`
   - `runtime-switch-required`
   - `runtime-missing`
   - `constraint-conflict`
   - `manager-missing`
   - `unknown`
4. When status is `unknown`, do not present the host Node as the selected project Node recommendation.

**Stability (D8)**

1. Offline/synthetic dual runs keep `analysis_status`, `decision_status`, `node_runtime_status`, and seven-factor total identical.
2. HTTP cache hits must not silently change validated version-identity conclusions (or must mark stale).

**Robustness (D9)**

1. Failure paths emit machine-readable status plus Chinese blockers; no “looks successful” partial packets.
2. Runner global-switch fallback restores in `finally`; restore failure blocks further commands.
3. `--offline` / network errors must not pretend upstream evidence is complete.

**Finding format**

```text
[ID] dimension / severity
phenomenon → evidence path → impact → suggested action (doc / script / test)
```

## 4. Contrast matrix and execution

### 4.1 Layers

| Layer | Action | Pass criteria |
|---|---|---|
| L0 | `python tests/run_all.py` | all green |
| L1 | generator on synthetic fixture (`--offline` allowed) | contract fields present; Node status matches pinned constraints |
| L2 | read-only resolve on `D:\Hzhao\AI_Test\VoiceInk-main` | explicit no-frontend / blocked; no fabricated baseline |

Evaluation order: static contract → L0 → L1 → L2 → P0 backlog → harden → re-run matrix.

### 4.2 L1 synthetic positive fixture

Intended path (created during implementation, not this spec commit):

`frontend-dependency-upgrade-impact-analysis/fixtures/synthetic-frontend/`

Minimum contents:

- `package.json` with a small direct dependency (e.g. `axios`) and `engines.node` such as `>=18 <21`
- `.nvmrc` exact pin consistent with engines (e.g. `20.18.0`)
- `package-lock.json` with resolvable direct version
- `src/main.js` with a real import/require hit
- Host Node `26.5.0` intentionally outside the fixture range → expect `runtime-switch-required` or `runtime-missing` depending on installed managers/runtimes

Command shape:

```bash
python scripts/generate_upgrade_report.py <fixture-root> \
  --upgrade axios::<to> \
  --output-dir <tmp>/dependency-upgrade-report \
  --offline
```

L1 assertions:

1. Status enums are protocol-valid and consistent with baseline.
2. `node_runtime.current_host_node` reflects host `26.5.0`.
3. Under the incompatible pin, status is not `compatible-current`.
4. Fixture `.nvmrc` / `engines` are unchanged after analysis.
5. Dual run: key statuses and seven-factor total match.

Also keep a fault variant: missing lock or claimed `from` mismatch → must `blocked`.

### 4.3 L2 VoiceInk negative control

Root: `D:\Hzhao\AI_Test\VoiceInk-main`

Known facts:

- No `package.json` anywhere in the tree (Python/PyQt6 desktop app).
- Not a valid frontend npm workspace for this skill.

Expected (explicit either-or):

- Stop during frontend workspace resolution with “no supported frontend importer”; or
- Emit report with `analysis_status=blocked` and pending decision to choose a workspace / confirm non-frontend repo.

P0 failures:

- Silently treating the repo as an npm frontend
- Fabricating lock baseline or project Node constraints
- Recommending `npm install` or Node switching for VoiceInk

### 4.4 Preliminary L2 probe (design-time evidence)

Command:

```bash
python scripts/generate_upgrade_report.py D:\Hzhao\AI_Test\VoiceInk-main \
  --upgrade axios::1.7.9 \
  --output-dir <temp> \
  --offline
```

Observed:

- Non-zero exit; report `analysis_status=blocked` (unknown baseline) — partially correct.
- Still writes full 12-section report as `exact-upgrade` with change type `added`.
- With **no authoritative project Node constraints**, summary still shows project Node as host `26.5.0` while status is `unknown` — misleading.
- CLI has **no dedicated “frontend workspace unresolved” gate**; it assumes `project_root` is already the frontend importer. This gaps against SKILL’s “never silently analyze the whole monorepo / ask when ambiguous” rule.

These are **candidate P0 findings** to confirm and score during evaluation execution, then fix under the hardening plan.

## 5. Data flow, error handling, hardening

### 5.1 Data flow

```text
User input
  → [Agent] resolve frontend workspace (SKILL contract)
  → [Generator] manifest/lock → baseline
  → [Generator] read-only Node preflight (host vs project)
  → upstream evidence (optional offline) + code scan
  → seven-factor score + Markdown/JSON report
  → [Agent] review heuristics before delivery
  → [Only after implementation approval] run_with_compatible_node.py
```

Boundary: generator assumes `project_root` is already the frontend workspace; it does not implement SKILL multi-candidate discovery.

### 5.2 Target failure semantics

| Condition | Target status | Forbidden |
|---|---|---|
| No frontend manifest/importer | `blocked` + explicit unresolved-importer reason | Default “added exact upgrade” narrative |
| Baseline unknown / `from` conflict | `analysis_status=blocked` | Treating `--allow-baseline-mismatch` as a green light |
| No authoritative Node constraints | `node_runtime_status=unknown`; selected project Node empty / `未建立` | Filling selected project Node with host |
| Host incompatible, compatible Node installed | `runtime-switch-required` | Analysis-phase `nvm use` |
| Restore failure after global switch | task `blocked`; stop further commands | Continue build/test |

### 5.3 P0 hardening directions

1. **Workspace preflight gate (script + SKILL alignment)**  
   When no `package.json` / agreed frontend signal: short-circuit or force `importer_resolution=failed` in the report header; ban default “added upgrade” framing.

2. **Tighten Node field semantics**  
   If status is `unknown`, leave `selected_project_node` unset/`未建立`; never backfill host. Keep “current host Node” and “selected project Node” visually and structurally distinct.

3. **Fixtures and regression locks**  
   Add L1 synthetic frontend and L2 no-manifest root tests/assertions: enums, no pin-file mutation, dual-run idempotence.

4. **Agent contract patch**  
   SKILL must state: resolve workspace before CLI; completion criteria for non-frontend roots; when Node is `unknown`, do not recommend implementation commands.

P1 backlog (does not block B): richer seven-factor explainability, HTTP cache operator docs, automatic multi-workspace discovery beyond explicit ask/stop.

### 5.4 Component boundaries for implementation

| Unit | Responsibility | Depends on |
|---|---|---|
| `generate_upgrade_report.py` | Read-only analysis + gate semantics | manifests, locks, network/cache, analysis-evidence JSON |
| `run_with_compatible_node.py` | Approved command execution + restore | installed Node/managers; never workspace discovery |
| `references/*` | Authoritative protocol | must stay enum-consistent with scripts |
| `tests` + `fixtures` | Lock P0 behaviors | no mandatory networked E2E |

### 5.5 Test plan mapped to success bar B

| Case | Layer | Assertion |
|---|---|---|
| Existing suite + new P0 tests | L0 | all green |
| Synthetic exact upgrade offline dual-run | L1 | statuses/risk equal; Node not `compatible-current` under pin 20 |
| No `package.json` root | L2 | dedicated blocked/failure semantics; host not labeled as project Node |
| Runner dry-run / approval granularity | unit (existing + extend if needed) | no switch without approvals |

## 6. Deliverables after this spec

1. Written evaluation matrix filled with Pass/Partial/Fail and P0/P1/P2 findings (implementation-plan phase / first execution tasks).
2. Implementation plan via `writing-plans` (only after user approves this spec file).
3. P0 code/doc/test changes until L0 green and L1/L2 contrast semantics trustworthy.
4. Backlog list for P1/P2.

## 7. Spec self-review notes

- Placeholders: none intentional; fixture path is specified for implementation, not created in this commit.
- Consistency: success bar B, approach 3, and L0/L1/L2 are aligned across sections.
- Scope: single implementation plan is feasible (workspace gate + Node field semantics + fixtures/tests + SKILL patch).
- Ambiguity resolved: VoiceInk is a **negative control**, not a full upgrade sample; host Node 26.5 is evaluation context, not a skill engines requirement.

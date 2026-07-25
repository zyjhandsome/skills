---
name: frontend-dependency-upgrade-impact-analysis
description: >
  Analyze frontend dependency upgrades and package-governance decisions without
  implementing them. Use for an exact package upgrade, a package-only
  removal/upgrade/replacement assessment, or a compliance concern. Resolve the
  frontend workspace and authoritative lock baseline, collect version-specific
  upstream and code-impact evidence, detect host/project Node runtime
  conflicts, score seven-factor risk, and produce a Simplified Chinese
  Markdown decision report plus optional structured JSON. Preserve observable behavior
  by default and keep removal/replacement and runtime installation as human
  choices unless the user explicitly allows them.
---

# Frontend Dependency Upgrade Impact Analysis

Produce an evidence-backed decision packet and validation plan. The bundled generator is a deterministic collector and Markdown renderer; review and enrich its heuristic findings before presenting a report as authoritative.

## Boundaries

- Do not install, upgrade, remove, replace, run migration codemods, edit application code, or execute project build/test scripts without explicit authorization.
- Read manifests, lockfiles, source, tests, git diffs, and non-mutating package metadata.
- Read-only Node/runtime probes are allowed. Runtime switching, Node installation, dependency installation, and project scripts require explicit implementation authorization.
- Treat report generation as analysis only, never as implementation approval.
- Do not create lifecycle/change records or redefine caller scope. The caller owns approvals and lifecycle state.

## Resolve scope and baseline

1. Resolve the project root; default to the current directory and state the assumption.
2. Resolve the frontend workspace/importer:
   - prefer an explicit path or workspace name;
   - exclude obvious backend/server/API, miniprogram, and native-app importers unless included;
   - use a single uniquely supported frontend candidate;
   - ask when multiple frontend candidates remain. Never silently analyze the whole monorepo.
3. Accept:
   - `package → exact to` or `package:from:to`;
   - `package` without a target;
   - optional `from`, reason, scope, and explicit behavior-change/removal/replacement allowance.
4. Infer a missing `from` only from the target importer's direct lock resolution or an authoritative before-lock.
5. Before calling the generator, confirm the resolved frontend workspace contains `package.json` (or pass `--after-package-json`). If resolution fails, stop; the generator returns exit code `5` with `importer_resolution=failed` and must not be treated as an upgrade recommendation.
6. If the direct version is unknown or conflicts with the claimed `from`, set `analysis_status=blocked` and show the manifest spec, importer, lock resolution, claim, and required decision.

Read `references/lockfile-and-evidence.md` for lock formats, workspace rules, and version-specific repository validation.

## Node runtime compatibility gate

Before recommending implementation:

1. Record the Node currently active on the host, then detect project Node constraints from exact runtime pins, `package.json` engines/Volta, CI/container evidence, installed toolchain metadata, and target-package engines.
2. Compare the current host Node with the project-compatible range. Do not introduce optional orchestration tools as a default runtime axis.
3. Stop on contradictory authoritative project constraints. If the host Node is incompatible but a compatible project Node exists, mark `runtime-switch-required`, not `constraint-conflict`.
4. Prefer an already installed compatible project runtime in an isolated child process. Use a guarded global switch only when isolation is unavailable.
5. Support nvm-windows, POSIX nvm, fnm, Volta, and asdf. If the manager or compatible Node is missing, report the blocker and exact one-time installation guidance; do not install automatically.
6. After approved execution, restore and verify the original host Node/runtime state in a `finally` path. Do not add temporary `.nvmrc`, engine, CI, shell-profile, or compatibility changes.
7. When `node_runtime_status=unknown` (no authoritative project constraints), keep `selected_project_node` unset. Never recommend implementation commands or treat the host Node as the project runtime.

Read `references/node-runtime-compatibility.md` before determining runtime readiness or executing any project command.

## Default posture and modes

Preserve observable behavior unless the user explicitly allows behavior change, deletion, or replacement:

- prefer a same-package exact upgrade;
- allow only necessary API/config adaptations for the chosen target;
- keep deletion/replacement as `needs_explicit_choice`;
- exclude drive-by business/UI refactors and backend contract changes.

Modes:

- **Exact upgrade:** analyze the confirmed `from → to` interval.
- **Open target:** assess evidence in order `remove → same-package candidates → alternatives → retain/exempt/isolate/fork/remove feature`.
- **Removal:** inspect direct, indirect, dynamic, tooling, peer, and transitive use. Zero static hits do not prove safe removal.
- **Compliance/replacement:** verify the stated concern, then compare bounded exact candidates.

Read `references/target-discovery-and-removal.md` whenever `to` is absent or removal/replacement is in scope.

## Workflow

1. Inventory dependency fields, overrides/resolutions, package manager, engines, runtime pins, workspace, and lock importer.
2. Parse the applicable npm, pnpm, or Yarn lock. Record direct and observed versions, duplicates, peer context, and baseline status.
3. Run the read-only Node runtime preflight and compare the current host Node with project-command requirements.
4. Select the analysis mode and apply the default behavior posture.
5. Resolve upstream identity per version:
   - prefer `versions[version].repository` over npm top-level metadata;
   - validate `gitHead` or a package-aware tag against historical package name/version;
   - split evidence when repository lineage changes.
6. Collect official release, changelog, migration, peer/engine, security, support, and license evidence with direct URLs.
7. Map imports/configuration first. Prefer a code knowledge graph; otherwise use bounded static search. Trace wrappers and callers to pages, routes, workflows, and tests.
8. Produce modification candidates with file, line, current usage, upstream reason, recommendation, validation, priority, and confidence.
9. For open targets, assess removal before comparing 1–3 same-package versions; research 2–3 alternatives only when same-package options are not viable or replacement is explicitly requested.
10. Record reviewed candidate/removal/runtime facts using `references/analysis-evidence-schema.md` and import them with `--analysis-evidence-file`.
11. Score the seven factors in `references/risk-model.md`, then derive regression scope, rollout controls, monitoring, and rollback triggers.
12. Generate and validate the Markdown report. Review every incomplete or heuristic section before delivery.

Read `references/impact-analysis-method.md` for evidence priority, impact-chain mapping, and stopping conditions. Read only the relevant family in `references/package-categories.md`.

## Output

Resolve the report directory in this order:

1. explicit `--output-dir`;
2. explicit existing `--change-dir` → `<change-dir>/evidence/frontend-dependency-upgrade/`;
3. fallback `<project-root>/dependency-upgrade-report/`, with the assumption stated.

Write:

- `frontend-dependency-upgrade-report.md`;
- optional `frontend-dependency-upgrade-report.json` via `--json-output`.

The report must expose `analysis_status`, `decision_status`, package-level `selection_status`, `behavior_parity_required`, constraints, baseline status, recommendations, pending human decisions, and actual report paths. Read `references/report-contract.md` before generation or review.

Default visible prose to Simplified Chinese. Preserve package names, versions, paths, commands, code identifiers, URLs, API names, and machine enums.

## Generator

```bash
python scripts/generate_upgrade_report.py <project-root> \
  --upgrade <package>:<from>:<to> \
  --change-dir <existing-change-dir>
```

Common forms:

```bash
# Exact upgrade; infer from the authoritative current lock
python scripts/generate_upgrade_report.py . \
  --upgrade axios::1.7.9 \
  --output-dir dependency-upgrade-report

# Open-target governance analysis with reviewed evidence
python scripts/generate_upgrade_report.py . \
  --assess deprecated-client \
  --reason "deprecated-client=不符合维护状态要求" \
  --analysis-evidence-file dependency-analysis-evidence.json \
  --json-output

# Explicit opt-out from behavior preservation
python scripts/generate_upgrade_report.py . \
  --assess legacy-client \
  --allow-behavior-change

# Offline draft
python scripts/generate_upgrade_report.py . \
  --upgrade vite:4.5.0:5.2.0 \
  --offline
```

Upstream collection uses bounded concurrency (`--network-workers`, default `6`) and a six-hour public-response cache in the user cache directory. Use `--no-http-cache` for a forced fresh read, `--http-cache-ttl` to change freshness, or `--http-cache-dir` to relocate the cache. Use `--max-versions` only for an explicitly incomplete exploratory draft.

An unknown or mismatched baseline is fatal by default. Use `--allow-baseline-mismatch` only for a visibly blocked investigative draft.

After the caller has approved implementation, dry-run the selected installed Node and commands first:

```bash
python scripts/run_with_compatible_node.py <project-root> \
  --node-version <exact-version> \
  --command "<install-or-upgrade-command>" \
  --command "<build-or-test-command>"
```

Only after matching explicit approvals, add `--execute --approve-runtime-switch` and the applicable `--approve-dependency-install` / `--approve-project-scripts` flags. The runner never installs Node, prefers an isolated child PATH, falls back to guarded nvm-windows switching only when required, and verifies restoration plus Node-constraint integrity.

## Completion gate

Before marking the analysis complete, verify:

- baseline, lock type, workspace, and importer are confirmed (`importer_resolution=confirmed`; non-frontend roots stay blocked);
- current host Node, project Node constraints, runtime manager availability, selected project runtime, execution readiness, and restoration plan are explicit;
- contradictory project Node constraints remain blocked; missing managers/runtimes remain implementation blockers until explicitly installed; `unknown` Node status never treats host Node as the project runtime;
- exact upgrades cover the full version interval; open targets preserve the required decision order;
- every eligible candidate has checked criteria and evidence URLs;
- removal evidence covers all required dimensions or remains visibly uncertain;
- high-confidence modification points cite both application and upstream evidence;
- the seven-factor total and any risk override are reproducible;
- critical workflows include positive, failure, and recovery validation;
- rollout and rollback have concrete triggers;
- all required Markdown sections and table widths validate;
- visible prose is in the requested language and heuristic output has been reviewed.

## References

- `references/impact-analysis-method.md` — evidence sequence, impact mapping, completeness.
- `references/target-discovery-and-removal.md` — open targets, behavior posture, removal, alternatives.
- `references/analysis-evidence-schema.md` — reviewed JSON evidence contract.
- `references/lockfile-and-evidence.md` — baselines, lockfiles, monorepo/version identity.
- `references/node-runtime-compatibility.md` — Node constraint precedence, isolated execution, manager adapters, installation and restoration gates.
- `references/risk-model.md` — seven-factor scoring and validation depth.
- `references/package-categories.md` — package-family-specific concerns.
- `references/report-contract.md` — Markdown sections, fields, language, and output.

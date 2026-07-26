---
name: frontend-dependency-upgrade-impact-analysis
description: >
  Analyze, never implement, a frontend dependency upgrade, removal, replacement, or
  compliance concern. Use when asked to assess an exact package upgrade, decide what
  to do about an unmaintained or vulnerable package, or check whether the project Node
  runtime can run the upgrade commands at all. Resolves the frontend workspace and
  authoritative lock baseline, collects version-specific upstream and code-impact
  evidence, detects host/project Node conflicts, scores seven-factor risk, and writes a
  Markdown decision report plus optional structured JSON in Simplified Chinese.
  Behavior preservation is the default. Open-target disposition and exact-upgrade
  proceed/defer stay human choices via the confirmation queue; batch_implementation_gate
  freezes Stage B/C until the batch is clear. This skill ends at the decision report,
  never at implementation.
---

# Frontend Dependency Upgrade Impact Analysis

Produce an evidence-backed decision packet and validation plan — analysis only. The generator collects and renders; review heuristics before treating a report as authoritative. Exact upgrades (clear `from → to`) skip disposition choice but still need proceed/defer confirmation (batchable). Open targets must finish one-package-at-a-time disposition questions. Stage A ends only when `decision_status≠needs_choice`; Stage B/C require `batch_implementation_gate=ready` plus caller authorization.

## Boundaries

- Do not install, upgrade, remove, replace, run migration codemods, edit application code, or execute project build/test scripts without explicit authorization.
- Read manifests, lockfiles, source, tests, git diffs, and non-mutating package metadata.
- Read-only Node/runtime probes are allowed. Runtime switching, Node installation, dependency installation, and project scripts require explicit implementation authorization.
- Treat report generation as analysis only, never as implementation approval.
- Do not create lifecycle/change records or redefine caller scope. The caller owns approvals and lifecycle state.
- **Human Decision Interaction Gate:** If `decision_status=needs_choice`, do not end Stage A. Read queue phase (`evidence`/`choice`/`mixed`) and `batch_implementation_gate`. On `blocked`, gather evidence / clear blockers and regenerate. On `ready`: open targets → ask one package at a time verbatim; exact upgrades (`proceed-exact`) → may batch-confirm `proceed:pkg@version` / `defer` / `other`. After `switch:<track>`, ask the alternate-track question; do not write switch to the decision file. `handle-parent` alone is not final. Record finals in `--decision-file`, regenerate to `disposition-selected` / `proceed-selected`. Exit `7` = draft written, confirmations unfinished. If `batch_implementation_gate=frozen`, do not open implementation plans or execute. Read `references/human-confirmation-gates.md`.

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

Before recommending any project command: record host Node; collect authoritative pins/engines (and toolchain-derived ranges when undeclared); stop on constraint conflicts; prefer an isolated installed project Node over global switch; support nvm-windows/nvm/fnm/Volta/asdf without auto-install; restore host state after approved execution; keep `selected_project_node` unset when status is `unknown`. Full rules in `references/node-runtime-compatibility.md`.

## Default posture and modes

Preserve observable behavior unless the user explicitly allows behavior change, deletion, or replacement:

- every route an open target can take must keep observable behavior identical; parity is a constraint on all of them, not a preference for one;
- allow only necessary API/config adaptations for the chosen target;
- keep deletion/replacement/rewrite/parent handling as `needs_explicit_choice`;
- exclude drive-by business/UI refactors and backend contract changes.

Modes:

- **Exact upgrade:** analyze the confirmed `from → to` interval, then require proceed/defer confirmation before Stage B/C.
- **Open target:** a listed package has to go, so the only routes are remove, replace, native rewrite, or handling the parent that pulls it in. **A same-package upgrade is never offered** — the version number moving forward does not resolve whatever put the package on the list; pass an exact target version if an upgrade is what you want. "Keep it" and "time-boxed exemption" are not offered either. Triage into one `primary_track` by asking, in order, *where does it come from → is it actually used → is there a package to switch to → otherwise rewrite it in first-party code*: `handle-parent` / `fix-phantom` / `pending-removal-evidence` / `remove` / `replace` / `native-refactor`. Alternate tracks stay visible and the human can switch tracks.
- **Provenance:** classify every package as `direct` / `both` / `phantom` / `transitive` / `unknown` from the manifest, the lock's dependency edges, and real call sites. Provenance decides which routes exist at all: an undeclared package has no declaration to drop, and one nobody calls cannot be rewritten. Transitive packages get parent chains, per-parent ranges, whether each parent's newest stable already dropped the dependency, and the lowest override version that satisfies every parent.
- **Removal:** inspect direct, indirect, dynamic, tooling, peer, and transitive use. Zero static hits do not prove safe removal.
- **Compliance/replacement:** verify the stated concern, then compare bounded exact candidates.

Read `references/target-discovery-and-removal.md` whenever `to` is absent or removal/replacement is in scope.

## Workflow

1. Inventory dependency fields, overrides/resolutions, package manager, engines, runtime pins, workspace, and lock importer.
2. Parse the applicable npm, pnpm, Yarn, or Bun lock. Record direct and observed versions, duplicates, peer context, `catalog:` resolution, and baseline status.
3. Run the read-only Node runtime preflight and compare the current host Node with project-command requirements.
4. Select the analysis mode and apply the default behavior posture.
5. Resolve upstream identity per version:
   - prefer `versions[version].repository` over npm top-level metadata;
   - validate `gitHead` or a package-aware tag against historical package name/version;
   - split evidence when repository lineage changes.
6. Collect official release, changelog, migration, peer/engine, security, support, and license evidence with direct URLs.
7. Map imports/configuration first. Prefer a code knowledge graph; otherwise use bounded static search. Trace wrappers and callers to pages, routes, workflows, and tests.
8. Produce modification candidates with file, line, current usage, upstream reason, recommendation, validation, priority, and confidence.
9. For open targets, classify provenance, assess removal, list replacement packages with exact registry-resolved versions ranked by machine-checkable signals only, give a scan-driven native refactor direction as the fallback when no package fits, resolve parent chains and the lowest viable override for transitive packages, and render the full disposition menu. Curated replacement leads are `curated-map`/`unknown` evidence and never change the recommendation; only reviewed `analysis-evidence` candidates can. Every open target must end with at least one actionable option — removal, a replacement package, an established refactor plan, or parent handling; `option_status=missing` blocks `complete`.
10. When the curated map has no entry, the emitted research checklist is mandatory work, not a suggestion: research candidates against the listed criteria (never download counts) and write the verdict back through `--analysis-evidence-file` per `references/analysis-evidence-schema.md`, alongside reviewed removal/runtime facts.
11. Score the seven factors in `references/risk-model.md`, then derive regression scope, rollout controls, monitoring, and rollback triggers.
12. Generate and validate the Markdown report. Review every incomplete or heuristic section. A full menu in the report is not a final disposition.
13. Work the confirmation queue before claiming Stage A complete. Open targets: one `ready` package at a time (replace offers exact `package@version` plus `other`). Exact upgrades: batch-confirm proceed/defer when multiple `to` targets are ready. Never ask `blocked` packages. `switch:<track>` is not a decision. After `handle-parent`, ask per-parent follow-ups.
14. Record final answers per `references/decision-record-schema.md`, regenerate, and stop at the decision packet. Only hand off to Stage B when `batch_implementation_gate=ready`. Confirmed selections are not implementation approval.

Read `references/impact-analysis-method.md` for evidence priority, impact-chain mapping, and stopping conditions. Read only the relevant family in `references/package-categories.md`.

## Output

Resolve the report directory in this order:

1. existing `--change-dir` (default) → `<change-dir>/evidence/frontend-dependency-upgrade/`  
   Typical OpenSpec path: `openspec/changes/<id>/evidence/frontend-dependency-upgrade/`;
2. explicit `--output-dir` override when the caller must write elsewhere.
3. Mixed exact + open-target batches auto-split into `exact/` and `open-target/` under that directory (plus `BATCH-INDEX.md`). Exact upgrades download-first into `upstream-evidence/`.

Do not invent a project-root report folder. Without `--change-dir` or `--output-dir`, stop with an error. This skill may create `evidence/frontend-dependency-upgrade/` inside an **existing** change directory; it must not create the change itself.

Write `frontend-dependency-upgrade-report.md`, plus optional `frontend-dependency-upgrade-report.json` via `--json-output`.

The report must expose `analysis_status`, `decision_status`, package-level `selection_status`, `behavior_parity_required`, constraints, baseline status, recommendations, pending human decisions, and actual report paths. Read `references/report-contract.md` before generation or review.

Language split is deliberate: this skill, its flags, and machine enums stay in English; visible prose in the delivered report defaults to Simplified Chinese. Preserve package names, versions, paths, commands, code identifiers, URLs, and API names verbatim.

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
  --change-dir openspec/changes/<id>

# Open-target governance analysis with reviewed evidence
python scripts/generate_upgrade_report.py . \
  --assess deprecated-client \
  --reason "deprecated-client=不符合维护状态要求" \
  --analysis-evidence-file dependency-analysis-evidence.json \
  --change-dir openspec/changes/<id> \
  --json-output

# Offline draft (local upstream-evidence readback allowed)
python scripts/generate_upgrade_report.py . \
  --upgrade vite:4.5.0:5.2.0 \
  --change-dir openspec/changes/<id> \
  --offline
```

Upstream collection uses bounded concurrency (`--network-workers`, default `6`) and a six-hour HTTP cache. Flags: `--no-http-cache`, `--http-cache-ttl`, `--http-cache-dir`, `--max-versions` (exploratory truncation only).

For exact upgrades, the generator also writes a report-adjacent `upstream-evidence/` pack (npm registry slice plus per-version release/changelog artifacts). Network success overwrites local files; network failure or `--offline` reads the same directory when present. Disable with `--no-upstream-evidence`. Default is keep; delete after a successful report write with `--cleanup-upstream-evidence`. Local readback must not mark evidence `complete`.

An unknown or mismatched baseline is fatal by default. Use `--allow-baseline-mismatch` only for a visibly blocked investigative draft.

After the caller has approved implementation, dry-run the selected installed Node and commands first:

```bash
python scripts/run_with_compatible_node.py <project-root> \
  --node-version <exact-version> \
  --command "<install-or-upgrade-command>" \
  --command "<build-or-test-command>"
```

Only after matching explicit approvals, add `--execute --approve-runtime-switch` and the applicable `--approve-dependency-install` / `--approve-project-scripts` flags. The runner never installs Node, prefers an isolated child PATH, falls back to guarded nvm-windows switching only when required, and verifies restoration plus Node-constraint integrity. Each command has a `--command-timeout` (default `1800`s, `0` waits forever); a timeout reports exit code `124` and still runs restoration.

## Completion gate

Before marking the analysis complete, verify:

- `decision_status` is not `needs_choice`; open targets are `disposition-selected` and exact upgrades are `proceed-selected` or `deferred` via the decision file. **Never** set `analysis_status=complete` while `needs_choice` remains; do not open Stage B/C while `batch_implementation_gate=frozen`;
- baseline, lock type, workspace, and importer are confirmed (`importer_resolution=confirmed`; non-frontend roots stay blocked);
- current host Node, project Node constraints, runtime manager availability, selected project runtime, execution readiness, and restoration plan are explicit;
- contradictory project Node constraints remain blocked; missing managers/runtimes remain implementation blockers until explicitly installed; `unknown` Node status never treats host Node as the project runtime;
- exact upgrades cover the full version interval; open targets preserve the required decision order and option completeness;
- every eligible candidate has checked criteria and evidence URLs;
- removal evidence covers all required dimensions or remains visibly uncertain;
- high-confidence modification points cite both application and upstream evidence;
- the seven-factor total and any risk override are reproducible;
- critical workflows include positive, failure, and recovery validation;
- rollout and rollback have concrete triggers;
- all required Markdown sections and table widths validate;
- visible prose is in the requested language and heuristic output has been reviewed.

The skill endpoint is the finalized analysis/decision report. Implementation stays outside this skill.

## References

- `references/human-confirmation-gates.md` — where humans must confirm; exit `7`; Agent pause rules.
- `references/impact-analysis-method.md` — evidence sequence, impact mapping, completeness.
- `references/target-discovery-and-removal.md` — open targets, behavior posture, removal, alternatives.
- `references/analysis-evidence-schema.md` — reviewed JSON evidence contract.
- `references/decision-record-schema.md` — human selection record, revalidation on re-runs.
- `references/lockfile-and-evidence.md` — baselines, lockfiles, monorepo/version identity.
- `references/node-runtime-compatibility.md` — Node constraint precedence, isolated execution, manager adapters, installation and restoration gates.
- `references/risk-model.md` — seven-factor scoring and validation depth.
- `references/package-categories.md` — package-family-specific concerns.
- `references/report-contract.md` — Markdown sections, fields, language, and output.

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
  freezes Stage B/C until the batch is clear. This skill ends only after the queue is
  cleared, the decision file is written, the report is regenerated, and Agent review
  raises analysis_status to complete — never at a draft exit-7 handoff, never at
  implementation.
---

# Frontend Dependency Upgrade Impact Analysis

Produce an evidence-backed decision packet and validation plan — analysis only. The generator collects and renders; review heuristics before treating a report as authoritative. Exact upgrades (clear `from → to`) skip disposition choice but still need proceed/defer confirmation. All packages with `confirmation.status=ready` (open-target and exact-upgrade) are asked in the same wave; `switch:<track>` / `handle-parent` follow-ups open the next wave; `blocked` packages are never asked. Exit `7` / `needs_choice` means **ask the queue now**, not wait for the user to say “继续/放行”. Stage A ends only when `decision_status≠needs_choice`, the report is regenerated, and Agent review sets `analysis_status=complete`. `batch_implementation_gate=frozen` does not block that analysis endpoint; Stage B/C still require `ready` plus caller authorization.

## Boundaries

- Do not install, upgrade, remove, replace, run migration codemods, edit application code, or execute project build/test scripts without explicit authorization.
- Read manifests, lockfiles, source, tests, git diffs, and non-mutating package metadata.
- Read-only Node/runtime probes are allowed. Runtime switching, Node installation, dependency installation, and project scripts require explicit implementation authorization.
- Treat report generation as analysis only, never as implementation approval.
- Do not create lifecycle/change records or redefine caller scope. The caller owns approvals and lifecycle state.
- **Human Decision Interaction Gate:** If `decision_status=needs_choice`, do not end Stage A and do not stop after pasting the draft report. In the same turn, read queue phase (`evidence`/`choice`/`mixed`) and act: on `blocked` / `evidence`, gather evidence / clear blockers and regenerate (do not ask disposition/proceed); on `choice` / `mixed`, immediately ask **every** currently `ready` package verbatim in one wave (open-target options + exact-upgrade `proceed:pkg@version` / `defer` / `other`). Never ask `blocked` packages. After `switch:<track>`, ask the alternate-track question in the next wave; do not write switch to the decision file. `handle-parent` alone is not final — parent follow-ups are the next wave. Record finals in `--decision-file`, regenerate, then Agent-review to `analysis_status=complete` (`disposition-selected` / `proceed-selected` / `deferred`). Exit `7` = draft written + **next action is ask the queue**, not wait for release. If `batch_implementation_gate=frozen`, do not open implementation plans or execute — but still finish the analysis endpoint when decisions are recorded. Read `references/human-confirmation-gates.md`.

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

- **Exact upgrade:** analyze the confirmed `from → to` interval, then require proceed/defer confirmation before Stage B/C. When implementation is blocked (Node/parents/lock), hide `proceed` and ask only `defer`/`other` so Stage A can still finish; `defer` yields exit `0` with `batch_implementation_gate=frozen` until blockers clear.
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
6. Probe public reachability before upstream collection (Agent `curl` + generator probe). Never infer `--offline` from `.npmrc`/private registry/intranet shape. Collect official release, changelog, migration, peer/engine, security, support, and license evidence with direct URLs (exact-upgrade interval only for release/changelog packs).
7. Map imports/configuration first. Prefer a code knowledge graph; otherwise use bounded static search. Trace wrappers and callers to pages, routes, workflows, and tests.
8. Produce modification candidates with file, line, current usage, upstream reason, recommendation, validation, priority, and confidence.
9. For open targets, classify provenance, assess removal, list replacement packages with exact registry-resolved versions ranked by machine-checkable signals only, give a scan-driven native refactor direction as the fallback when no package fits, resolve parent chains and the lowest viable override for transitive packages, and render the full disposition menu. Curated replacement leads are `curated-map`/`unknown` evidence and never change the recommendation; only reviewed `analysis-evidence` candidates can. Every open target must end with at least one actionable option — removal, a replacement package, an established refactor plan, or parent handling; `option_status=missing` blocks `complete`.
10. When the curated map has no entry, the emitted research checklist is mandatory work, not a suggestion: research candidates against the listed criteria (never download counts) and write the verdict back through `--analysis-evidence-file` per `references/analysis-evidence-schema.md`, alongside reviewed removal/runtime facts.
11. Score the seven factors in `references/risk-model.md`, then derive regression scope, rollout controls, monitoring, and rollback triggers.
12. Generate and validate the Markdown report. Review every incomplete or heuristic section. A full menu in the report is not a final disposition.
13. Work the confirmation queue before claiming Stage A complete. On exit `7` / `needs_choice`, ask immediately in the same turn — never hand back a draft and wait for “放行”. Ask every currently `ready` package in one wave (open-target disposition options including exact `package@version` + `other`; exact-upgrade proceed/defer). Never ask `blocked` packages. `switch:<track>` is not a decision; after switch or `handle-parent`, open the next wave for the follow-up questions.
14. Record final answers per `references/decision-record-schema.md`, regenerate, Agent-review heuristics/upstream summaries, and only then mark `analysis_status=complete`. That is this skill’s endpoint. Only hand off to Stage B when `batch_implementation_gate=ready`. Confirmed selections are not implementation approval.

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

# Offline draft — ONLY after human/caller confirms (never from .npmrc/intranet heuristics)
python scripts/generate_upgrade_report.py . \
  --upgrade vite:4.5.0:5.2.0 \
  --change-dir openspec/changes/<id> \
  --offline
```

**Reachability gate:** Agent `curl -I --max-time 12 https://registry.npmjs.org/` then, on failure, `https://api.github.com/`. Registry or GitHub OK → stay online (no `--offline`). Both fail → ask human; only then `--offline`. Generator re-probes (exit `8`, `network_reachability=unreachable`, `awaiting_offline_confirmation`); no local `upstream-evidence` readback until `--offline`. Exact-upgrade mid-fetch with no usable release **and** changelog in the interval → re-probe GitHub; probe fail asks offline, 403/429 stays `partial`/`missing`. Details: `references/lockfile-and-evidence.md`.

Upstream uses `--network-workers` (default `6`) and a six-hour HTTP cache (`--no-http-cache`, `--http-cache-ttl`, `--http-cache-dir`, `--max-versions`). Exact upgrades write `upstream-evidence/` for the `from→to` interval; network success overwrites; **local readback requires `--offline`**. `--no-upstream-evidence` disables; `--cleanup-upstream-evidence` deletes after success. Local readback must not mark evidence `complete`.

Unknown/mismatched baseline is fatal by default; `--allow-baseline-mismatch` only for a visibly blocked investigative draft.

After the caller has approved implementation, dry-run the selected installed Node and commands first:

```bash
python scripts/run_with_compatible_node.py <project-root> \
  --node-version <exact-version> \
  --command "<install-or-upgrade-command>" \
  --command "<build-or-test-command>"
```

**Implementation hard rules:** never run install/ci/update/build/test/lint (or any lock-mutating command) with host Node outside this runner; `unknown` Node with no pin blocks project commands until an exact `selected_project_node` is established; freeze lock format fields by default (`lockfileVersion` / yarn metadata); npm major must be compatible with the existing lock before mutating commands; format migration requires report approval plus `--allow-lockfile-format-migration`; before claiming done, verify lock format unchanged. Only after matching approvals, add `--execute --approve-runtime-switch` and `--approve-dependency-install` / `--approve-project-scripts`. The runner never installs Node, prefers isolated child PATH, verifies restoration, Node-constraint integrity, and lock-format integrity (exit `7` if format drifts without approval). `--command-timeout` default `1800`s (`0` = forever); timeout exit `124` still restores.

## Completion gate

Before marking the analysis complete, verify:

- `decision_status` is not `needs_choice`; open targets are `disposition-selected` and exact upgrades are `proceed-selected` or `deferred` via the decision file; the report was regenerated after the decision file write; Agent review raised `analysis_status` to `complete`. **Never** set `analysis_status=complete` while `needs_choice` remains; **never** treat exit `7` draft delivery as skill completion; do not open Stage B/C while `batch_implementation_gate=frozen` (`frozen` may remain after Stage A if Node/runtime blockers exist — that does not block the analysis endpoint);
- baseline, lock type, workspace, and importer are confirmed (`importer_resolution=confirmed`; non-frontend roots stay blocked);
- current host Node, project Node constraints, runtime manager availability, selected project runtime, execution readiness, and restoration plan are explicit;
- contradictory project Node constraints remain blocked; missing managers/runtimes remain implementation blockers until explicitly installed; `unknown` Node status never treats host Node as the project runtime and hard-blocks project commands until an exact project Node is established;
- lock format fields stay frozen unless migration was explicitly approved; host-Node lock drift must not be committed;
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

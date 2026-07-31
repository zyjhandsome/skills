---
name: java-dependency-upgrade-impact-analysis
description: >
  Analyze, never implement, a Java/Maven/Gradle dependency upgrade, downgrade,
  BOM conflict, or whole-repo upgrade inventory. Use when asked to assess exact
  GAV from→to upgrades, Spring Boot–managed jars (Netty, Jackson, Lucene, Eureka),
  commons-lang migrations, CVE-driven version moves, unused-jar removal, transitive
  exclusion/force-align, or component replacement.
---

# Java Dependency Upgrade Impact Analysis

Produce an evidence-backed decision packet — analysis only. Do not change
manifests, run version-mutating build commands, apply migration codemods, or
edit application code.

## Minimal caller input

A **short prompt** is enough: invoke the skill, give the project root (or accept
the stated cwd), and provide either an exact from→to table/GAV list or “整仓巡检”.
Resolve the report directory under Output unless the caller overrides it.

## Environment preflight

Before any analysis (including manifest-only reads), run
`references/environment-preflight.md`. Missing `java`, the **selected** build
tool (system `mvn`/`gradle` preferred; wrapper-only is a graded pass — see
preflight), or Python → batch-wide `analysis_status=blocked`; list gaps in
chat; **do not write** reports. Host JDK vs project declaration mismatch is
recorded, not a block. Network probe runs in the same wave; dual
registry+GitHub failure follows the existing offline confirm gate (not a
tool-preflight failure).

## Boundaries

- **Allowed:** read `pom.xml` / Gradle files / version catalogs; run
  verified non-mutating resolution (`dependency:tree`, `help:effective-pom`,
  `dependencies`, `dependencyInsight`); search
  source/tests; fetch upstream release/changelog/CVE evidence; write reports
  under the resolved Output directory.
- **Forbidden:** install/upgrade/remove dependencies; edit build or source
  files; run migration codemods; treat compile/startup success as release proof.
- **Lifecycle safety:** before any Maven/Gradle goal that can enter a build
  lifecycle, inspect bound goals for format/apply/flatten/codegen writes.
  Never run bare `dependency:analyze`; use `dependency:analyze-only` only when
  fresh compiled outputs already exist, otherwise use call-site/config evidence
  and mark `usage_status=ambiguous`. Snapshot `git status` before/after every
  build-tool probe and stop on a new tracked-file change.
- **Default posture:** preserve observable behavior unless the user explicitly
  allows behavior change.
- **Treatment then owner:** pick `recommended_treatment` from
  `references/treatment-ladder.md` (direct: remove → upgrade → replace;
  transitive: exclude-if-untouched → upgrade-introducer → force-align →
  replace-introducer) before locking a version authority move. Then apply
  owner-first (`references/owner-and-resolution.md`: BOM bump → property →
  family BOM → per-GAV pin). Per-GAV pins / force-align need a complete Decision
  Record after residual conflict.
- **GA-only targets** for production recommendations; non-GA → `blocked` unless
  the user explicitly allows (`target_channel=non-ga`).
- **Name, never run, migration recipes** for MAJOR coordinate/package moves.
- **Explicit downgrades are allowed for analysis.** Caller `from > to` authorizes
  analyzing the target (not implementing it): downgrade warning + High scrutiny +
  normal per-unit confirmation. Missing motive is an evidence gap, not a
  batch-wide blocker. **Pending baseline ≠ downgrade block:** reachable target
  with unconfirmed `resolved_from` → queue-`pending` + evidence checklist, not
  queue-`blocked` or `ready`+`proceed`. **Transitive moves need a path menu:**
  prefer `upgrade-introducer` / `move-introducer`, then `force-align` with full
  DR — never lead with a bare leaf pin (`next-action-choice-menus.md`).

## Dual entry

| Entry | Input | First action |
|---|---|---|
| Exact table | `groupId:artifactId` + `from` + `to` (optional module) | Validate resolved baseline; analyze interval |
| Repo inventory | project root, no targets | Build candidate list; ask which batch to analyze |

Normalize every item to the candidate schema in
`references/dual-entry-and-batching.md`. One analysis batch = **one authority
layer × one Boot line × one build variant × one bounded batch scope**, with an
additional `decision_domain` only when a MAJOR/coordinate migration must be
isolated inside that combination. Apply
`references/common-upgrade-patterns.md` for family / CVE / unused / replace
patterns.

## Workflow

1. Run environment preflight; resolve project root, build tool, modules, JDK
   and Spring Boot lines plus active Maven profiles / Gradle properties. State
   assumptions. Exit `5` → stop (`blocked`); exit `6` → ask build tool (not blocked).
2. Collect **declared** and **effective** versions. Prefer tree/insight over
   pom-only parsers. Use bounded leaf-module probes with explicit timeouts; do
   not run an unbounded whole-reactor tree before batch selection. For directs,
   record `usage_status` from safe analyze-only evidence plus call sites/config;
   framework/reflection-only dependencies default to `ambiguous`, not `unused`.
3. **Target existence precheck — before owner and impact work.** Probe
   reachability (`references/reachability-and-upstream.md`). Verify every family
   member at exact `to` (`target_artifact_exists`); reject non-GA unless allowed.
   If a requested target/member is missing, preserve it as `requested_*`, then
   search for 1–3 verified GA alternatives. Same-GAV version →
   `choose-alternative` + `proceed:`; coordinate change → `replace-*` +
   `replace:`; none → `no-viable-path` + `blocked`. Treatments without a target
   use `n/a`.
4. Classify effective owner; for transitives record `introducer_gav` and whether
   an introducer move converges to the target. Assign `recommended_treatment`.
   Pending tooling/tree → `next-action-choice-menus.md` §A before any `proceed`.
5. If Maven Tools MCP is available, use it for version/CVE/POM facts; else
   registry/GitHub/`gh`/WebFetch. Never invent versions or silently substitute
   artifacts. Every alternative remains a human choice; same-GAV alternatives
   use `proceed:g:a:v`, coordinate changes use `replace:g:a:v`.
6. Map SemVer risk and gather official changelog/migration notes for the exact
   interval (`references/common-gav-repos.md`). Open/CVE without `to`: recommend
   a GA fix range with URLs, then ask — do not auto-pick.
7. Map code/config/test impact (`references/impact-and-validation.md`). Mark
   fact vs inference. Transitive moves: explore path menu §B with verified
   evidence (introducer / force-align / replace starter-or-stack / native rewrite).
8. Score risk; draft packet + Decision Records (baseline checklist + path-option
   menu fields when §A/§B apply).
9. Work the confirmation queue (`references/human-confirmation-gates.md`): list
   every `ready`/`pending` unit in one wave; each needs its own explicit answer.
   `pending` = tooling catch-up only (`defer`/`other`); `ready` uses
   `proceed:…` / `remove` / `exclude` / `replace:…` / `defer` / `other`. No
   blanket proceed. Never ask proceed on `blocked`. Record, regenerate, Agent
   review → `analysis_status=complete`.
10. Stop. Do not open implementation plans from this skill.

## Output

Resolve the report directory in this order:

1. Explicit `--output-dir` override when the caller must write elsewhere.
2. Existing `--change-dir` → `<change-dir>/evidence/java-dependency-upgrade/`
3. Else under the analyzed project root, match an existing
   `openspec/changes/<id>/` (one → use; many → ask; none → ask for
   `--change-dir` or `--output-dir`).

Do **not** invent a project-root report folder or create OpenSpec changes.
This skill **may** create `evidence/java-dependency-upgrade/` inside an
**existing** change directory. Until the path is resolved: if environment
preflight passed, **read-only analysis is allowed**; **do not write** reports.
Preflight failure → stop (no analysis, no write).

Write at least `java-dependency-upgrade-report.md`. Multi-batch layout:
`<entry-kind>/<authority-layer>__<boot-line>__variant-<build-variant>__scope-<batch-scope>[__domain-<decision-domain>]/…`
plus root `BATCH-INDEX.md`
(`entry-kind` = `exact` / `open-target`; `boot-line` = `boot-<line>` / `no-boot`).
Prose defaults to Simplified Chinese; keep GAV/versions/paths/commands/enums/URLs
verbatim. Required sections: `references/report-contract.md`. State the actual
resolved report path in the packet header.

## Validator

```shell
python scripts/validate_report.py <report.md>
python scripts/validate_report.py --evidence-dir <evidence-dir> [--json]
```

Exit `0` pass / `3` errors / `4` path missing. A pass means well-formed, never that
evidence is sufficient. Fixtures: `fixtures/valid-report*.md` (partial/complete/
remove/replace/open-target/choose-alternative/pending-baseline); multi-batch under
`examples/sample-evidence-multi/`. Decision records live in `decision-records/`
beside each report.

## Status axes

| Axis | Meaning |
|---|---|
| `analysis_status` | `partial` / `blocked` / `complete` — packet-level; `blocked` = batch-wide baseline/offline/**environment-preflight** gate (see confirmation gates) |
| `decision_status` | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | `frozen` / `ready` (informational; this skill never implements) |
| also required | `behavior_parity_required`, `network_mode`, `report_path` — see `references/report-contract.md` |

Never set `analysis_status=complete` while `decision_status=needs_choice` or any
queue `ready`/`pending`. Never set `analysis_status=blocked` while any queue
`ready`/`pending`. Residual evidence-`blocked` may remain after complete (gate
stays `frozen`). Uncleared `ready`/`pending` ⇒ **ask now**, not “继续/放行”.

## Completion gate

- Environment preflight passed (JDK + selected `mvn`|`gradle`|wrapper + Python)
- Baselines/owner/treatment recorded; targets + alternatives verified; ladder +
  owner-first done or ruled out; upstream URLs or offline gaps; fact/inference
  split; queue zero `ready`/`pending`; `decision-records/` complete; validator
  exit `0`; Agent review → `analysis_status=complete`

## References

`references/next-action-choice-menus.md`, `references/environment-preflight.md`,
`references/treatment-ladder.md`, `references/owner-and-resolution.md`,
`references/dual-entry-and-batching.md`, `references/reachability-and-upstream.md`,
`references/impact-and-validation.md`, `references/human-confirmation-gates.md`,
`references/report-contract.md`, `references/decision-record-schema.md`,
`references/common-gav-repos.md`, `references/common-upgrade-patterns.md`,
`templates/decision-packet.md`, `templates/decision-record.md`, `scripts/`,
`fixtures/`, `examples/sample-evidence-multi/`.

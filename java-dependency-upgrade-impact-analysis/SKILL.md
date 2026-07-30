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

Callers may use a **short prompt** (skill name + project root + upgrade table
or “整仓巡检”). All hard rules below still apply; do not wait for the user to
restate owner-first, treatment-ladder, confirmation-queue, or batching rules.

## Minimal caller input

Require only:

1. This skill invoked (by name or description match)
2. Project root (or cwd assumption stated)
3. Either an exact from→to table / GAV list, or an inventory request

Report directory is resolved by the skill (see Output). Callers need not
restate the path in the prompt unless they must override it.

## Environment preflight

Before any analysis (including manifest-only reads), run
`references/environment-preflight.md`. Missing `java`, the **selected** build
tool (system `mvn` or `gradle` on PATH — wrappers do not count), or Python →
batch-wide `analysis_status=blocked`; list gaps in chat; **do not write**
reports. Host JDK vs project declaration mismatch is recorded, not a block.
Network probe runs in the same wave; dual registry+GitHub failure follows the
existing offline confirm gate (not a tool-preflight failure).

## Boundaries

- **Allowed:** read `pom.xml` / Gradle files / version catalogs; run
  non-mutating resolution (`dependency:tree`, `help:effective-pom`,
  `dependencies`, `dependencyInsight`, `dependency:analyze`); search
  source/tests; fetch upstream release/changelog/CVE evidence; write reports
  under the resolved Output directory.
- **Forbidden:** install/upgrade/remove dependencies; edit build or source
  files; run migration codemods; treat compile/startup success as release proof.
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
- **Downgrades** use the same workflow as upgrades when `from → to` is explicit.

## Dual entry

| Entry | Input | First action |
|---|---|---|
| Exact table | `groupId:artifactId` + `from` + `to` (optional module) | Validate resolved baseline; analyze interval |
| Repo inventory | project root, no targets | Build candidate list; ask which batch to analyze |

Normalize every item to the candidate schema in
`references/dual-entry-and-batching.md`. One analysis batch = **one authority
layer × one Boot line**. Apply `references/common-upgrade-patterns.md` for
family / CVE / unused / replace patterns.

## Workflow

1. Run environment preflight; resolve project root, build tool, modules, JDK
   and Spring Boot lines. State assumptions. Tool/Python failure → stop
   (`blocked`).
2. Collect **declared** and **effective** versions. Prefer tree/insight over
   pom-only parsers. For directs, record `usage_status` via analyze/call sites.
3. **Target existence precheck — before owner and impact work.** Probe
   reachability (`references/reachability-and-upstream.md`). Verify every family
   member at exact `to` (`target_artifact_exists`); reject non-GA unless allowed.
   Missing member → `blocked`. Treatments without a target use `n/a`.
4. Classify effective owner; for transitives record `introducer_gav` and whether
   an introducer upgrade already lifts the hole. Assign `recommended_treatment`.
5. If Maven Tools MCP is available, use it for version/CVE/POM facts; else
   registry/GitHub/`gh`/WebFetch. Never invent versions or silently substitute
   artifacts (replacement is a confirmed `replace-*` treatment).
6. Map SemVer risk and gather official changelog/migration notes for the exact
   interval (`references/common-gav-repos.md`). Open/CVE without `to`: recommend
   a GA fix range with URLs, then ask — do not auto-pick.
7. Map code/config/test impact (`references/impact-and-validation.md`). Mark
   fact vs inference.
8. Score risk; draft the packet (`templates/decision-packet.md`) and Decision
   Records (`templates/decision-record.md`).
9. Work the confirmation queue (`references/human-confirmation-gates.md`): list
   every `ready` **decision unit** in one wave; each unit needs its own explicit
   answer (`proceed:g:a:v` / `remove` / `exclude` / `replace:…` / `defer` /
   `other`). No blanket proceed. Never ask `blocked`. Record, regenerate, Agent
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
`<entry-kind>/<authority-layer>__<boot-line>/…` plus root `BATCH-INDEX.md`
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
evidence is sufficient. Reference fixtures: `fixtures/valid-report.md` (partial /
needs_choice) and `fixtures/valid-report-complete.md` (complete with residual
blocked).

## Status axes

| Axis | Meaning |
|---|---|
| `analysis_status` | `partial` / `blocked` / `complete` — packet-level; `blocked` = batch-wide baseline/offline/**environment-preflight** gate (see confirmation gates) |
| `decision_status` | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | `frozen` / `ready` (informational; this skill never implements) |

Never set `analysis_status=complete` while `decision_status=needs_choice` or while
any confirmation-queue row is still `ready`. Never set `analysis_status=blocked`
while any queue row is `ready`. Residual evidence-`blocked` rows may remain after
complete; they keep the implementation gate `frozen`. See
`references/human-confirmation-gates.md` status transition table.

Uncleared `ready` queue ⇒ **ask now**, not wait for “继续/放行”.

## Completion gate

- Environment preflight passed (JDK + selected `mvn`|`gradle` + Python)
- Baseline effective versions recorded; owner + treatment classified
- `target_artifact_exists` verified (or `n/a` for no-target treatments); non-GA
  blocked unless explicitly allowed
- Treatment ladder + owner-first attempted or ruled out with evidence
- Upstream interval evidence cited with URLs (or explicit offline gaps)
- Impact items separate fact/inference; empty test scope stated when applicable
- Confirmation queue: zero `ready` (answered → `decided` / `deferred`; evidence
  gaps may remain `blocked`); Decision Records complete
- Report regenerated; `scripts/validate_report.py` exits `0`; Agent review sets
  `analysis_status=complete`

## References

- `references/treatment-ladder.md` — remove/upgrade/exclude/force/replace
- `references/environment-preflight.md` — JDK / mvn|gradle / Python PATH gates
- `references/owner-and-resolution.md` — effective graph, ownership, override
- `references/dual-entry-and-batching.md` — inventory, exact table, batching
- `references/reachability-and-upstream.md` — network probe, changelog, MCP
- `references/impact-and-validation.md` — six-layer impact, validation matrix
- `references/human-confirmation-gates.md` — per-unit proceed/defer protocol
- `references/report-contract.md` — Markdown sections and status fields
- `references/decision-record-schema.md` — Decision Record fields
- `references/common-gav-repos.md` — common GAV → GitHub mapping
- `references/common-upgrade-patterns.md` — PATCH/CVE/unused/replace heuristics
- `templates/decision-packet.md` — report skeleton
- `templates/decision-record.md` — per-component record
- `scripts/validate_report.py` — structural validator
- `fixtures/valid-report.md` — partial / needs_choice reference packet
- `fixtures/valid-report-complete.md` — complete with residual blocked

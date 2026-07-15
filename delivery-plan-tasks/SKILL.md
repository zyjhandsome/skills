---
name: delivery-plan-tasks
description: >-
  Use when an approved software requirement needs a technical design, executable
  task breakdown, implementation-readiness review, or implementation gate —
  e.g. “写设计与任务/拆分实现任务”, after delivery-frame-spec approved Standard/High
  (or Debug-Medium/High) scope, write design.md/tasks.md, vertical slices,
  validation matrix. Does not implement. Hands off to delivery-execute-verify
  after explicit user go.
---

# Delivery Plan Tasks

## Iron Rules

1. Do not implement. Any CRITICAL readiness finding blocks handoff and the implementation gate.
2. OpenSpec `design.md` / `tasks.md` are the only plan/tasks truth — no parallel Markdown copies.
3. Vertical behavior slices with real paths/symbols and falsifiable validation; no horizontal “all types → all backend → tests last.”
4. Implementation go = **one** user ask (High: same ask + cost/risk/rollback summary; five facets Agent-internal).
5. Stage end: emit the **required handoff subset**. If chaining is unsupported, tell the user「请使用 delivery-execute-verify」.
6. Do **not** add a fifth user-visible router skill; do **not** paste long system essays into this `SKILL.md`.

## Overview

Turn an approved requirement into one trustworthy technical plan and executable vertical tasks grounded in current code facts.

**Hard gate:** Do not implement. Do not hand off while any readiness CRITICAL remains.

## Language and artifacts

- This `SKILL.md` is English.
- **All human-facing Markdown artifacts default to Chinese** — plan/tasks/readiness bodies, headings, tables, prose — following the Chinese templates under `references/`. Only paths, commands, code identifiers, and machine-readable keys/enums stay English. When OpenSpec holds `design.md`/`tasks.md`, write their prose in Chinese too; only OpenSpec's machine-parsed skeleton (defined in `delivery-frame-spec`) stays English.
- If the user works in another language, follow the user's language instead; machine keys still stay English.
- When refreshing facts from the brief, update the brief’s **Code Facts** block (Chinese heading `代码事实`, including `证据表`). Do not invent a second fact document. Refer to brief parts by name, never by section numbers.

## Input Contract

Require:

- approved brief/spec or equivalent;
- route/risk and specification-gate record;
- current code facts and project constraints;
- artifact backend and unique state source;
- known validation capability.

If the spec has blocking ambiguity, code facts are stale, or planning would change approved behavior, return to `delivery-frame-spec`.

## Capability Adapters

Codebase Memory MCP, OpenSpec, Superpowers, and all four `delivery-*` skills are **hard prerequisites** of this family, assumed co-installed (cross-skill `../delivery-*/references/…` paths depend on it). Treat any absence as an exception to report, not a normal mode; without OpenSpec only Read-only routes work — there is no substitute Markdown backend.

Expect a `capability_snapshot` in the incoming handoff (format defined in `delivery-frame-spec`, Prerequisite preflight section). Trust nominal values; re-probe only anomalies and capabilities this stage relies on whose state may have changed (e.g. index freshness after a rebase). If no snapshot arrived, run that preflight once here and record it. Update the snapshot on state changes and pass it forward.

**Preflight failure — fixed 3-line report (Chinese):**

```text
缺什么：<memory|openspec|superpowers 的具体异常枚举>
能否降级：<可 degraded 定点取证续规划 / 必须恢复 OpenSpec 后才能写 design/tasks>
下一步请你：<例如：恢复 openspec CLI / 刷新 Memory 索引>
```

Naming convention: refer to external capabilities as repo + capability — e.g. Superpowers `writing-plans`, OpenSpec `apply` (`/opsx-apply`), Codebase Memory MCP `trace_path`. Inside a subsection titled with the owning repo, bare capability names refer to that repo. Bare skill names elsewhere are reserved for the `delivery-*` family.

### Codebase Memory MCP — path and impact verification

Use current index/architecture, graph search, path tracing, snippets, and impact detection to verify:

- real integration points and symbols;
- callers and shared boundaries;
- tests and likely regression surface;
- whether facts survived a rebase or refactor.

Discover current schemas before calls. If the snapshot marks `memory: stale-index | down`, refresh the index when safe or use targeted source/git evidence, mark degradation, and report the outage. Never invent a path from naming conventions.

**Index freshness probe (required):** if integration paths/symbols from the brief or tasks are on disk but Memory search misses them, set `memory: stale-index`, mark degradation, and report via the fixed 3-line form. Never invent a path from naming conventions; never treat a stale miss as “symbol gone.”

This is code memory (evidence only). It is never the plan/tasks backend or state source; artifact truth lives in the OpenSpec change.

### OpenSpec — the only artifact backend

OpenSpec design/tasks are the only planning truth:

- recover the active change and dependencies;
- check other active changes for overlapping specs, files, or capabilities; sequence the work or report the conflict instead of planning over it;
- generate/update design and tasks in that change (OpenSpec `continue`/`update`, host command `/opsx-continue` / `/opsx-update`);
- run strict structural validation where supported (OpenSpec `validate`);
- keep requirement/scenario traceability;
- do not create a second Markdown plan/tasks set.

This skill is normally reached on the Standard/High route (including Debug-Medium/High mutation) with an active OpenSpec change created in `delivery-frame-spec`. Map the plan to `design.md` and tasks to `tasks.md` in that change; do not create parallel `plan.md`/`tasks.md` beside the OpenSpec artifacts.

If the OpenSpec backend becomes unavailable, stop. Restore OpenSpec before continuing; never improvise a duplicate backend.

### Superpowers — quality methods

- `writing-plans` may inform task granularity and completeness, but must not create a competing plan when OpenSpec owns artifacts.
- `dispatching-parallel-agents` may inform independence domains and file/state ownership after tasks are valid.
- `using-git-worktrees` may inform whether planned parallel domains can be safely isolated.

These are planning-quality inputs only. Actual SubAgent dispatch and worktree creation belong to `delivery-execute-verify` after the implementation gate.

The primary workflow owner remains this skill.

## Refresh Facts Before Planning

Re-check paths/symbols when:

- branch/rebase changed since the brief;
- target files are missing or renamed;
- dependency versions or architecture changed;
- impact evidence is older than current diff/head.

Update the existing brief **Code Facts** block (and Evidence Table) or record a fact refresh. Missing integration points are blockers, not placeholders.

## Design Process

1. Restate approved goals, non-goals, risk, and constraints.
2. Confirm real integration points and validation infrastructure.
3. Present 2–3 viable approaches when trade-offs are material.
4. Compare compatibility, reversibility, complexity, risk, testability, and migration.
5. Recommend one approach with evidence (also stamp the recommended option with「建议：」when asking the user to pick).
6. Define data/control flow, interfaces, failure handling, observability, migration, and rollback as applicable.
7. Build a requirement → design → task → validation traceability matrix.
8. Split implementation into ordered vertical tasks.
9. Run readiness review.

Do not manufacture alternatives for trivial choices. Do not skip alternatives for expensive or irreversible choices.

## Artifact Rules

Read only as needed:

- `references/plan-template.md`
- `references/tasks-template.md`
- `references/readiness-review.md`

The plan describes how. It cannot silently change what the approved spec requires.

## Dependency Invalidation

Artifact dependencies are directional:

- brief/spec change invalidates plan, tasks, readiness, implementation gate, affected implementation acceptance, and final verification;
- plan/design change invalidates affected tasks, readiness, implementation gate, affected task validation, and final verification;
- tasks change invalidates readiness, implementation gate, affected task validation, and final verification;
- validation-command changes invalidate affected evidence and final verification.

Mark invalidated artifacts/gates stale before editing them. Re-run all downstream gates before handoff; an old approval never covers changed content.

## Vertical Task Rule

Prefer a thin user/system behavior that includes its necessary types, logic, integration, and test.

Avoid horizontal batches such as:

- "create all data types";
- "implement all backend code";
- "implement all UI";
- "add all tests at the end."

A shared contract or migration-preparation task may be a prerequisite only when it is independently testable and genuinely unlocks multiple vertical slices. Horizontal layer splits (all types → all backend → all UI → tests last) are not vertical slices even when split across agents.

## Task Minimum Fields

Every task includes:

- behavior-oriented title;
- mapped Requirement/Scenario;
- dependencies;
- exact files and symbols;
- allowed and forbidden scope;
- implementation steps;
- test-first or approved alternative validation;
- exact command/action and expected result;
- rollback/migration note when relevant;
- completion definition;
- ownership/conflict note for parallel work.

No "implement backend," "add tests," guessed paths, or unbounded cleanup.

## Test and Validation Matrix

For each Requirement/Scenario record:

- verification layer: unit/integration/E2E/manual/security/migration;
- test file or fixture;
- exact command/action;
- expected success;
- what a failure proves;
- approved degradation and coverage gap, if any.

Validation must be capable of failing for the missing behavior.

## Parallel Planning

Parallelize only tasks with:

- no shared mutable state;
- no overlapping files, or explicit ownership;
- stable prerequisite contracts;
- independently runnable validation.

Use separate worktrees/branches when supported. Define integration order and post-merge validation.

Do not parallelize merely to keep three agents busy.

## Readiness Review

Before the readiness checklist below, run `../delivery-execute-verify/references/artifact-gate-checks.md` items G1–G3 (and G5 if Medium/High). Any FAIL is a **阻塞项**.

Human-facing findings use the Chinese labels in `references/readiness-review.md`:

- **阻塞项** (blocking) — blocks implementation.
- **警告项** (warning) — fix or obtain explicit risk acceptance.
- **建议项** (suggestion) — optional, non-blocking.

If a backend requires machine enums, map them as `阻塞项=CRITICAL`, `警告项=WARNING`, `建议项=SUGGESTION`; do not expose the English enum as the default human-facing heading.

Check:

1. approved spec coverage;
2. current paths/symbols and blast radius;
3. no scope creep;
4. failure and edge behavior;
5. compatibility, migration, rollback, security, performance, observability as applicable;
6. vertical task size and ordering;
7. executable, falsifiable validation;
8. parallel ownership and integration conflicts;
9. no unresolved overlap with other active changes (shared specs, files, or capabilities);
10. artifact backend structural validation.

## Implementation Gate

Every route requires an explicit user go before implementation; artifact completeness alone never authorizes it.

- Quick: lightweight contract is complete **and the user explicitly approved implementation** (usually recorded in `delivery-frame-spec`; this skill is usually skipped).
- Medium: no blocking finding, warnings resolved/accepted, user confirms implementation (single go ask).
- High: no blocking finding; Agent **internally** verifies design, tasks, rollback, security, and validation and records that checklist in the state source; user confirms implementation with the **same single go ask** as Medium, plus a short cost/risk/rollback summary. Do **not** quiz the user facet-by-facet.

Persist the gate (approver/time; High also: internal five-facet checklist result) in the unique state source.

### Gate and approach clarification (batch clarification)

Fixed-choice moments in this stage use the same family rule as `delivery-frame-spec`: follow `../delivery-frame-spec/references/batch-clarification.md` (click first, typing fallback; platform-agnostic). **Only explicit per-item choice** — never「全部按推荐」or bulk-accept. **Every fixed-choice question must include a recommendation** (`推荐：…` +「建议：」on the recommended option + rationale). Do not switch modes solely to obtain a choice UI. Keep implementation gates separate from product-clarification waves.

**Approach pick** (Design Process steps 3–5, when trade-offs are material): after showing 2–3 approaches with tradeoffs inline, ask one fixed-choice question whose options are the approaches (impact on each label; recommended option prefixed with「建议：」; prompt states `推荐：…` + rationale; optional escape「其他（我来说明）」). The user must select; do not auto-apply the recommendation.

**Implementation go — Medium and High:** one fixed-choice question only (see `batch-clarification.md` **Gate ask shape**). Options: `建议：开始实施` / `先不实施` / `有修改（说明）`. High must include a short plain-language summary of scope, cost/risk, rollback, and next skill/task id. If any internal High facet fails readiness, do **not** ask for go — fix artifacts first. User「开始实施」approves the go package after Agent self-check; it is not bulk-accept of unresolved product questions.

## Handoff

Return a compact handoff with the **required subset** (Chinese labels: `references/handoff-template.md`): `stage`, `state_source`, `capability_snapshot`, `gate_status`, `evidence_mode`, `next_skill`, `required_inputs`, `stop_condition`.

```text
stage: delivery-plan-tasks
state_source:
capability_snapshot:
evidence_mode:
gate_status:
plan/tasks:
traceability:
readiness_result:
validation_plan:
risk/gates:
parallel_ownership:
next_skill: delivery-execute-verify
required_inputs:
stop_condition:
```

If skill chaining is unsupported, stop and tell the user exactly:「请使用 delivery-execute-verify」.

## Red Flags

- Planning from stale paths after rebase.
- Any Markdown plan/tasks copy created beside the OpenSpec change.
- Calling horizontal layers "vertical slices."
- Deferring all tests until implementation ends.
- Tasks without exact paths, symbols, or expected validation.
- Parallel agents editing the same files without ownership.
- Plan changes requirements without returning to framing.
- Structural validation treated as semantic readiness.
- Any CRITICAL ignored because of deadline or manager request.
- Binding gate questions to a named IDE/agent/tool, expanding High’s internal five facets into a user quiz (or dribbling them across messages), omitting the required recommendation on a fixed-choice question, switching mode only to obtain a choice UI, or offering「全部按推荐」/ bulk-accept that skips per-question user choice.

Stop, repair the authoritative artifacts, and re-run readiness review.

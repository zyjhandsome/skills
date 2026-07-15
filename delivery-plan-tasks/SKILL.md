---
name: delivery-plan-tasks
description: >-
  Use when an approved software requirement needs a technical design, executable
  task breakdown, implementation-readiness review, or implementation gate —
  e.g. “写技术方案”, “拆分实现任务”, “做实现就绪审查”, or “过实现闸门”, after
  delivery-frame-spec approved Standard/High (or Debug-Medium/High) scope. Writes
  design.md/tasks.md, vertical slices, and a validation matrix. Does not implement.
  Hands off to delivery-execute-verify after explicit user go.
---

# Delivery Plan Tasks

## Iron Rules

1. Do not implement. Any CRITICAL readiness finding blocks handoff and the implementation gate.
2. OpenSpec `design.md` / `tasks.md` are the only plan/tasks truth — no parallel Markdown copies.
3. Vertical behavior slices with real paths/symbols and falsifiable validation; no horizontal “all types → all backend → tests last.”
4. Implementation go = **one** user ask (High: same ask + cost/risk/rollback summary; five facets Agent-internal).
5. Stage end: emit one complete `delivery-handoff/v1` object, including blocked/end states. If chaining is unsupported, tell the user「请使用 delivery-execute-verify」only after the implementation gate permits transition.
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

- a compatible `delivery-handoff/v1` transport snapshot whose `source_revision` still matches current state;
- approved brief/spec or equivalent;
- route/risk and specification-gate record;
- current code facts and project constraints;
- artifact backend and unique state source;
- known validation capability.

If the spec has blocking ambiguity, code facts are stale, or planning would change approved behavior, return to `delivery-frame-spec`.

## Capability Adapters

Treat the four `delivery-*` skills and shared references as one atomic Family (`../delivery-frame-spec/references/family-contract.md`). OpenSpec is mandatory for mutating routes; Memory and Superpowers are preferred but degradable; SubAgent/worktree and structured UI are optional accelerators. Never invent a substitute Markdown artifact backend.

Expect compatible `family_version`, `capability_snapshot`, and `capability_bindings` in the incoming handoff. Trust nominal health but resolve/re-probe operations this stage relies on whose binding or state may have changed. If the Family major is unsupported, stop automatic chaining; if bindings are absent, run the shared preflight/adapter discovery once here. Update both health and bindings on change.

**Preflight failure — fixed 3-line report (Chinese):**

```text
缺什么：<memory|openspec|superpowers 的具体异常枚举>
能否降级：<可 degraded 定点取证续规划 / 必须恢复 OpenSpec 后才能写 design/tasks>
下一步请你：<例如：恢复 openspec CLI / 刷新 Memory 索引>
```

Naming convention: refer to external capabilities as repo + semantic capability — e.g. Superpowers `writing-plans`, OpenSpec `continue_artifacts`, Codebase Memory MCP `trace_path`. Record actual aliases in `capability_bindings`; bare skill names elsewhere are reserved for the `delivery-*` family.

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

Read `../delivery-frame-spec/references/openspec-adapter.md`, reuse or refresh `capability_bindings.openspec`, and resolve the current schema plus `inspect_change`, `continue_artifacts`, and `validate_structure` operations. OpenSpec design/tasks remain the only planning truth:

- recover the active change and dependencies;
- check other active changes for overlapping specs, files, or capabilities; sequence the work or report the conflict instead of planning over it;
- generate/update design and tasks through the resolved `continue_artifacts` operation;
- run the resolved `validate_structure` operation where supported;
- keep requirement/scenario traceability;
- do not create a second Markdown plan/tasks set.

This skill is normally reached on the Standard/High route with an active OpenSpec change created in `delivery-frame-spec`. Map plan/tasks to the slots reported by the current schema; `design.md` / `tasks.md` are common defaults, not an instruction to create parallel files when the schema differs.

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
3. Inventory material decision points and classify authority using **Technical Decision Authority** below.
4. Present 2–3 viable approaches only when the trade-off is material; do not manufacture alternatives for agent-owned details.
5. Compare compatibility, reversibility, complexity, risk, testability, migration, operations, and cost as applicable.
6. Recommend one approach with evidence. Decide and record agent-owned choices; ask the user only for user-required choices.
7. Define data/control flow, interfaces, failure handling, observability, migration, and rollback as applicable.
8. Build a requirement → design → task → validation traceability matrix.
9. Split implementation into ordered vertical tasks.
10. Run readiness review.

Do not manufacture alternatives for trivial choices. Do not skip alternatives for expensive or irreversible choices.

## Technical Decision Authority

Classify every planning uncertainty before asking the user:

| Class | Action |
|---|---|
| Evidence-findable fact | Inspect code/tests/config/approved artifacts; update Code Facts; do not ask the user |
| Agent-owned implementation detail | If inside approved behavior, low-risk, reversible, and not material to user constraints, decide with evidence and record the rationale in `design.md` |
| Spec-affecting product decision | If it changes behavior, scope, acceptance, product risk, or an irreversible product boundary, return to `delivery-frame-spec` |
| User-required technical decision | If it materially changes cost/deployment, migration/compatibility, rollback/operations, security posture, an irreversible technical choice, or an explicit user constraint, record it in the **Technical Decision Inventory** and ask the user |

Before any user-required plan ask, show the complete current inventory. Batch all independent blockers in one wave; hold dependent choices until their premise is decided. Record every result in `design.md`. Reuse recorded decisions while the authoritative artifacts and conditions remain unchanged.

Before readiness, run the shared **Clarification completeness sweep** limited to plan-owned decision dimensions and record the result in `design.md` / readiness. Product discoveries backflow to frame; do not reopen them as technical choices.

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

Before the readiness checklist below, run `../delivery-execute-verify/references/artifact-gate-checks.md` items G1–G3, **G8**, and G5 when Medium/High. Any FAIL is a **阻塞项**.

### Active-change path overlap (G8)

Before readiness pass:

1. List other active OpenSpec changes (`openspec list` or equivalent).
2. Collect this change's allowed paths/symbols from `tasks.md` / design.
3. Collect overlapping paths from other changes' `tasks.md` / proposal Impact sections when available.
4. If any path/symbol overlaps → record a **阻塞项** unless the user explicitly accepts the sequencing risk and the acceptance is listed in the implementation-gate summary (`accepted_warning_ids` or equivalent). Do not silently plan parallel edits on the same files.

Human-facing findings use the Chinese labels in `references/readiness-review.md`:

- **阻塞项** (blocking) — blocks implementation.
- **警告项** (warning) — fix or obtain explicit risk acceptance.
- **建议项** (suggestion) — optional, non-blocking.

If a backend requires machine enums, map them as `阻塞项=CRITICAL`, `警告项=WARNING`, `建议项=SUGGESTION`; do not expose the English enum as the default human-facing heading.

Check:

1. approved spec coverage;
2. current paths/symbols and blast radius;
3. no scope creep;
4. no unresolved user-required technical decision; agent-owned decisions have rationale and spec-affecting decisions have completed frame backflow;
5. the plan-owned clarification completeness sweep is recorded with no remaining material blocker;
6. failure and edge behavior;
7. compatibility, migration, rollback, security, performance, observability as applicable;
8. vertical task size and ordering;
9. executable, falsifiable validation;
10. parallel ownership and integration conflicts;
11. no unresolved overlap with other active changes (shared specs, files, or capabilities);
12. artifact backend structural validation.

## Implementation Gate

Every route requires an explicit user go before implementation; artifact completeness alone never authorizes it.

- Quick: lightweight contract is complete **and the user explicitly approved implementation** (usually recorded in `delivery-frame-spec`; this skill is usually skipped).
- Medium: no blocking finding; warnings are resolved or explicitly listed in the visible go summary for acceptance; user confirms implementation (single go ask).
- High: no blocking finding; warnings are resolved or explicitly listed in the visible go summary; Agent **internally** verifies design, tasks, rollback, security, and validation and records that checklist in the state source; user confirms implementation with the **same single go ask** as Medium, plus a short cost/risk/rollback summary. Do **not** quiz the user facet-by-facet.

Persist the gate in the unique state source with approver, time, current artifact revision, explicitly accepted warning IDs, and—on High—the internal five-facet checklist result. Any artifact revision change invalidates that gate until readiness and approval are re-established.

An implementation go may accept only warning items explicitly shown in the gate summary. Hidden, newly discovered, or materially changed warnings remain unresolved and invalidate the go.

### Gate and approach clarification (batch clarification)

Fixed-choice moments in this stage use the same family rule as `delivery-frame-spec`: follow `../delivery-frame-spec/references/batch-clarification.md` (click first, typing fallback; platform-agnostic). When a host question tool is available, map the wave through `../delivery-frame-spec/references/question-ui-adapters.md`. **Only explicit per-item choice** — never「全部按推荐」or bulk-accept. **Every fixed-choice question must include a recommendation** (`推荐：…` +「建议：」on the recommended option + rationale). Do not switch modes solely to obtain a choice UI. Keep implementation gates separate from product-clarification waves.

**Technical decision wave** (Design Process steps 3–6): ask only decisions classified as user-required. Show the complete current Technical Decision Inventory, then ask all independent blockers in one wave using the shared protocol; dependent choices wait for the next wave. If only one approach-level decision exists, one fixed-choice question is enough. Agent-owned details are decided and recorded without user interruption; spec-affecting decisions return to frame.

**Implementation go — Medium and High:** one fixed-choice question only (see `batch-clarification.md` **Gate ask shape**). Options: `建议：开始实施` / `先不实施` / `有修改（说明）`. Include every warning proposed for acceptance in the visible summary; High also includes scope, cost/risk, rollback, and next skill/task id. If any internal High facet or user-required technical decision fails readiness, do **not** ask for go — fix artifacts first. User「开始实施」approves only the displayed go package and accepts only its listed warnings; it is not acceptance of hidden warnings or unresolved decisions.

## Handoff

Before handing off, read `../delivery-frame-spec/references/handoff-contract.md` and emit one complete, strictly parseable `delivery-handoff/v1` JSON object using `references/handoff-template.md`. Put plan/tasks, decisions, traceability, readiness, validation, gates, and parallel ownership in `stage_payload`. When local Python is available, validate the final object with `../delivery-frame-spec/scripts/validate_handoff.py` before output.

Presentation projection is view-only: when supported, show `pipeline` for plan/gates, `tasks` projected from authoritative `tasks.md`, `review` projected from readiness findings, and `handoff` only after the implementation gate passes. Otherwise render the same information as Markdown. Never let presentation status replace OpenSpec task truth.

Record `presentation_capability` using the shared contract. For `delivery-ui/v1` or `legacy-v0`, follow `../delivery-frame-spec/references/structured-presentation-adapter.md`; when capability is unknown, use Markdown. Preserve canonical capability enums and map them only in the UI projection.

If skill chaining is unsupported, stop and tell the user exactly:「请使用 delivery-execute-verify」.

## Red Flags

- Planning from stale paths after rebase.
- Any Markdown plan/tasks copy created beside the OpenSpec change.
- Calling horizontal layers "vertical slices."
- Deferring all tests until implementation ends.
- Tasks without exact paths, symbols, or expected validation.
- Parallel agents editing the same files without ownership.
- Plan changes requirements without returning to framing.
- Asking the user to decide an evidence-findable fact or a low-risk reversible implementation detail.
- Entering readiness or the implementation gate with an unresolved user-required technical decision, hidden warning, or incomplete frame backflow.
- Structural validation treated as semantic readiness.
- Any CRITICAL ignored because of deadline or manager request.
- Binding gate questions to a named IDE/agent/tool, expanding High’s internal five facets into a user quiz (or dribbling them across messages), omitting the required recommendation on a fixed-choice question, switching mode only to obtain a choice UI, or offering「全部按推荐」/ bulk-accept that skips per-question user choice.

Stop, repair the authoritative artifacts, and re-run readiness review.

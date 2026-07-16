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

Shared family protocol: `../delivery-frame-spec/references/family-contract.md`. Handoff schema and template: `../delivery-frame-spec/references/handoff-contract.md` + `../delivery-frame-spec/references/handoff-template.md` (Plan block). Question protocol: `../delivery-frame-spec/references/batch-clarification.md`. OpenSpec operations: `../delivery-frame-spec/references/openspec-adapter.md`.

## Iron Rules

1. Do not implement. Any blocking readiness finding (阻塞项) blocks handoff and the implementation gate.
2. OpenSpec `design.md` / `tasks.md` (per the active schema's slots) are the only plan/tasks truth — no parallel Markdown copies.
3. Vertical behavior slices with real paths/symbols and falsifiable validation; no horizontal “all types → all backend → tests last.”
4. Implementation go = **one** user ask (High: same ask + cost/risk/rollback summary; five facets Agent-internal).
5. Stage end: emit one complete `delivery-handoff/v1` object (including blocked/end states), validate, persist. If chaining is unsupported, tell the user「请使用 delivery-execute-verify」only after the gate permits transition.
6. Hard prerequisites are assumed available; on a real runtime failure stop and report per `family-contract.md` — no degraded planning mode.

## Overview

Turn an approved requirement into one trustworthy technical plan and executable vertical tasks grounded in current code facts.

## Input Contract

Require: a compatible `delivery-handoff/v1` snapshot whose `source_revision` matches current state (from chat, or from the change's persisted `handoff.json` in a new session); approved brief/spec; route/risk and specification-gate record; current code facts; the unique state source; known validation capability.

If the spec has blocking ambiguity, code facts are stale, or planning would change approved behavior, return to `delivery-frame-spec`. When Execute returned here with an `alignment_backflow` packet, complete the three-item re-entry consume check (`handoff-contract.md` §7) before continuing.

## Capability roles

- **Codebase Memory MCP — path and impact verification.** Verify real integration points and symbols, callers and shared boundaries, tests and regression surface, and whether facts survived a rebase/refactor. Never invent a path from naming conventions. Index freshness rule: `family-contract.md` §5.
- **OpenSpec — the only artifact backend.** Resolve `inspect_change`, `continue_artifacts`, `validate_structure`. Recover the active change; check other active changes for overlap; generate/update design and tasks via `continue_artifacts`; run `validate_structure` where supported; keep requirement/scenario traceability.
- **Superpowers — planning-quality inputs only.** `writing-plans` for granularity/completeness; `dispatching-parallel-agents` for independence domains; `using-git-worktrees` for isolation feasibility. Actual dispatch and worktrees belong to `delivery-execute-verify`.

## Refresh Facts Before Planning

Re-check paths/symbols when the branch/rebase changed since the brief, target files are missing/renamed, dependencies or architecture changed, or impact evidence is older than the current head. Update the brief's **Code Facts** block (Chinese heading `代码事实`, including `证据表`); do not invent a second fact document. Missing integration points are blockers, not placeholders.

## Design Process

1. Restate approved goals, non-goals, risk, and constraints.
2. Confirm real integration points and validation infrastructure.
3. Inventory material decision points; classify authority (table below).
4. Present 2–3 viable approaches only when the trade-off is material.
5. Compare compatibility, reversibility, complexity, risk, testability, migration, operations, cost as applicable.
6. Recommend one approach with evidence; decide and record agent-owned choices; ask the user only for user-required choices.
7. Define data/control flow, interfaces, failure handling, observability, migration, rollback as applicable.
8. Build a requirement → design → task → validation traceability matrix.
9. Split implementation into ordered vertical tasks.
10. Run readiness review.

Do not manufacture alternatives for trivial choices; do not skip alternatives for expensive or irreversible ones.

### Proportional depth (Standard/Medium)

For a Medium change that is single-module, touches no red-line surface, and has a bounded file set, `design.md` may be compact: decision records + integration point list + validation matrix, without ceremonial architecture sections. Readiness still runs with the full G-check set for Medium (G1–G3, G5, G8) — proportionality reduces artifact depth, never gate checks. High always uses full depth. Record the chosen depth and its justification in `design.md`; proportionality never skips the implementation gate or falsifiable validation.

## Technical Decision Authority

| Class | Action |
|---|---|
| Evidence-findable fact | Inspect code/tests/config/artifacts; update Code Facts; do not ask |
| Agent-owned implementation detail | If inside approved behavior, low-risk, reversible, not material to user constraints: decide with evidence, record rationale in `design.md` |
| Spec-affecting product decision | Changes behavior/scope/acceptance/product risk/irreversible product boundary → return to `delivery-frame-spec` |
| User-required technical decision | Materially changes cost/deployment, migration/compatibility, rollback/operations, security posture, an irreversible technical choice, or an explicit user constraint → record in the Technical Decision Inventory and ask |

Before any user-required ask, show the complete current inventory; batch all independent blockers in one wave per the shared protocol; record every result in `design.md`. Before readiness, run the shared clarification completeness sweep limited to plan-owned dimensions; product discoveries backflow to frame.

## Task rules

**Vertical slices:** prefer a thin user/system behavior including its types, logic, integration, and test. A shared contract or migration-prep task may be a prerequisite only when independently testable and genuinely unlocking multiple slices. Horizontal layer splits are not vertical slices even when split across agents.

**Task minimum fields:** behavior-oriented title; mapped Requirement/Scenario; dependencies; exact files and symbols; allowed and forbidden scope; implementation steps; test-first or approved alternative validation; exact command/action and expected result; rollback/migration note when relevant; completion definition; ownership/conflict note for parallel work. No "implement backend", guessed paths, or unbounded cleanup. Templates: `references/plan-template.md`, `references/tasks-template.md`.

**Validation matrix:** for each Requirement/Scenario record verification layer, test file/fixture, exact command, expected success, what a failure proves, and any approved coverage gap. Validation must be capable of failing for the missing behavior.

**Parallel planning:** parallelize only tasks with no shared mutable state, no overlapping files (or explicit ownership), stable prerequisite contracts, and independently runnable validation. Define integration order and post-merge validation. Do not parallelize merely to keep agents busy.

## Dependency Invalidation

Directional: brief/spec change invalidates plan, tasks, readiness, gate, affected acceptance, and final verification; plan/design change invalidates affected tasks and everything downstream; tasks change invalidates readiness and downstream; validation-command change invalidates affected evidence and final verification. Mark invalidated artifacts stale before editing; re-run all downstream gates before handoff — an old approval never covers changed content.

## Readiness Review

First run `../delivery-execute-verify/references/artifact-gate-checks.md` items G1–G3, **G8**, and G5 when Medium/High; any FAIL is a 阻塞项. G8 (active-change path overlap): list other active changes, collect this change's allowed paths from `tasks.md`/design, compare with theirs; any overlap is a 阻塞项 unless the user explicitly accepts sequencing risk in the gate summary (`accepted_warning_ids`).

Findings use Chinese labels (`references/readiness-review.md`): **阻塞项** / **警告项** / **建议项** (machine mapping CRITICAL/WARNING/SUGGESTION when a backend requires enums).

Check: approved spec coverage; current paths/symbols and blast radius; no scope creep; no unresolved user-required decision (agent-owned decisions have rationale, spec-affecting ones completed frame backflow); sweep recorded with no material blocker; failure/edge behavior; compatibility/migration/rollback/security/performance/observability as applicable; vertical task size and ordering; executable falsifiable validation; parallel ownership and integration conflicts; no unresolved overlap with other active changes; artifact backend structural validation.

## Implementation Gate

Every route requires an explicit user go before implementation; artifact completeness alone never authorizes it.

- Quick: contract go usually recorded in `delivery-frame-spec`; this skill is usually skipped.
- Medium: no blocking finding; warnings resolved or explicitly listed in the visible go summary; single go ask.
- High: same single go ask, plus a short cost/risk/rollback summary; Agent **internally** verifies design/tasks/rollback/security/validation and records that checklist in the state source. Never a facet-by-facet user quiz.

Ask shape and options (`建议：开始实施` / `先不实施` / `有修改（说明）`): `batch-clarification.md` **Gate ask shape**. Persist the gate with approver, time, artifact revision, accepted warning IDs, and (High) the internal five-facet result. Any artifact revision change invalidates the gate. A go accepts only warnings explicitly shown in the summary; hidden or newly discovered warnings invalidate it. If any internal High facet or user-required decision fails readiness, do not ask for go — fix artifacts first.

## Handoff

Follow the shared contract and template (Plan block). Put plan/tasks, decisions, traceability, readiness, validation, gates, and parallel ownership in `stage_payload`; persist `handoff.json` after validation.

## Red Flags

- Planning from stale paths after rebase; inventing paths from naming conventions.
- Any Markdown plan/tasks copy beside the OpenSpec change.
- Calling horizontal layers "vertical slices"; deferring all tests to the end; tasks without exact paths/symbols/validation.
- Plan changes requirements without returning to framing; asking the user to decide an evidence-findable fact or low-risk reversible detail.
- Entering readiness/gate with an unresolved user-required decision, hidden warning, or incomplete frame backflow.
- Structural validation treated as semantic readiness; any 阻塞项 ignored because of deadline or manager request.
- Violating the batch-clarification protocol (see its Anti-patterns).

Stop, repair the authoritative artifacts, and re-run readiness review.

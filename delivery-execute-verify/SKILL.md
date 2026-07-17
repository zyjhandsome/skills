---
name: delivery-execute-verify
description: >-
  Use when implementing an approved task set or a user-approved scoped defect/debug
  contract, or when verifying development work — e.g. “开始实施”, “按 tasks.md 执行”,
  “按已批准范围修复缺陷”, “跑新鲜验证”, or “确认是否已完成”. Applies TDD,
  SubAgent waves, fresh tests, and code review. Ends at verified handoff; does not
  sync or archive OpenSpec changes — that belongs to the resolved OpenSpec
  `archive_change` operation.
---

# Delivery Execute Verify

Shared family protocol: `../delivery-frame-spec/references/family-contract.md`. Handoff schema and template: `../delivery-frame-spec/references/handoff-contract.md` + `../delivery-frame-spec/references/handoff-template.md` (Execute block). Question protocol: `../delivery-frame-spec/references/batch-clarification.md`. OpenSpec operations: `../delivery-frame-spec/references/openspec-adapter.md`.

## Iron Rules

1. No mutation without a recorded explicit user go for this route (including Quick/Debug-Low).
2. No completion / merge / “done” language while required validation is failing or stale.
3. Ends at `overall_status: verified` + `stage_payload.archive.status: deferred_to_openspec` — **never** sync/archive OpenSpec inside this skill.
4. Default execute inline; parallel SubAgents only when independence checks pass. Trust diffs and reviews, not SubAgent summaries alone.
5. Stage end: emit one complete `delivery-handoff/v1` object (in-progress, blocked, verified, and end states), validate, persist. After verified, state the resolved archive operation (`next_action`); ask before any commit/PR. Backflow returns to frame/plan follow the chain relay rule (`family-contract.md` §1): continue in the same session when the host can load the upstream skill directly.
6. Hard prerequisites are assumed available; on a real runtime failure stop and report per `family-contract.md` — no degraded execution or verification mode.

## Overview

Implement only approved scope, keep authoritative tasks synchronized, switch to evidence-driven debugging on failure, and require fresh runtime plus specification evidence before completion. Close-out: when the Fresh Verification Gate and review gates pass and all authoritative tasks are complete, end at `verified`, write evidence, and hand archive to the resolved OpenSpec `archive_change` operation. Commit / push / PR remain user-gated. Deployment, rollout, and post-release monitoring are out of scope.

## Input Contract

Standard/High require: a compatible `delivery-handoff/v1` snapshot whose revision matches current OpenSpec state (from chat, or the change's persisted `handoff.json`); unique state source; approved plan/tasks; route/risk and implementation-gate record; validation commands; forbidden scope.

Quick/Debug require: a handoff/contract revision matching the current lightweight change; goal and non-goals; affected files/symbols; observable acceptance or reproduction; validation command; risk/unknowns; a recorded explicit user go bound to the current contract revision.

Debug routing: Low-risk scoped mutation only from a user-approved debug contract (read-only diagnosis needs no go); Medium-risk mutation requires the Standard route artifacts and gates; High-risk mutation requires the High route and both High gate records. Debug is not a risk level and never bypasses gates.

If inputs are missing, return to `delivery-frame-spec` or `delivery-plan-tasks`. Do not invent an implicit requirement during implementation.

## Capability roles

- **OpenSpec — the only execution backend.** Resolve `inspect_change`, `apply_tasks`, `continue_artifacts`, `validate_structure`, `verify_coherence`, `archive_change` as needed. OpenSpec tasks are the only task state. **Do not** invoke `archive_change` here and do not silently sync delta specs; after verified close-out, point `next_action` at the resolved archive operation.
- **Codebase Memory MCP — impact evidence.** Locate implementation and failure paths, check actual blast radius against planned scope, identify affected callers/tests, review final diff impact. Refresh the index after edits before relying on impact evidence (`family-contract.md` §5). Never a task store or state source.
- **Superpowers — quality methods.** `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `dispatching-parallel-agents`, `subagent-driven-development`, `using-git-worktrees`, `requesting-code-review` / `receiving-code-review`, `finishing-a-development-branch`. Methods never become a second task owner.

## Preflight

Before editing:

1. Recover state and current task.
2. Verify the implementation gate and explicit user go are bound to the current artifact revision — including Quick and Debug-Low. If approval is missing or its revision differs, stop, mark it stale, and obtain a click-first go before any mutation.
3. Confirm exact task scope, files/symbols, validation, dependencies; route any new uncertainty through **Decision Routing** before mutation.
4. Inspect full repository status (staged, unstaged, untracked); preserve unrelated user changes; check target-file collisions. Re-run G8 (`references/artifact-gate-checks.md`): if another active change's paths now overlap this change's allowed paths, stop unless the user accepted the sequencing risk at the gate.
5. Run or confirm the task's baseline validation. If baseline fails, switch to systematic diagnosis; proceed only when evidence proves the failure pre-existed and is independent of the target behavior, and the user approves a degradation record (command, failure signature, independence evidence, unaffected checks, scope/risk, approver, time, expiry). If independence is unknown, block.
6. Stop if branch/artifacts diverged enough to invalidate the plan.

## SubAgent Orchestration

SubAgents and independent review are available (hard prerequisite); resolve the host's **actual maximum concurrency and worktree support** into `capability_bindings.subagents` — never infer capacity from desired parallelism. Choose execution mode from task facts; ask the user only when isolation, uncommitted state, cost, or destructive integration requires a decision.

**Default: inline.** Sequential fresh SubAgents when multiple well-specified tasks need clean context + two-stage review but shared integration makes parallel unsafe. Parallel batches only when 2+ tasks are dependency-ready with no overlapping files/shared mutable state, independent validation, isolated workspaces, and available slots.

Build a dependency/file-ownership graph from approved `tasks.md` (Quick/Debug contract = single node unless it defines independent subtasks). Same-file tasks run sequentially; after each wave: review, integrate, validate, then next wave.

Worktree/git mutations require the same user authorization as ordinary git ops. Never stash/commit/discard user uncommitted changes to enable worktrees.

SubAgent packets must be self-contained (scope, files, validation, return format); SubAgents must not edit global task state or reinterpret scope from whole-chat context. Statuses: `completed` | `completed_with_concerns` | `needs_context` | `blocked` (Chinese labels and full checklists: `references/subagent-orchestration.md`). Main Agent inspects the real diff, runs spec then quality review, integrates, validates, then updates OpenSpec tasks — never trust the summary alone.

## User decision clicks

Fixed-choice decisions in this stage (missing go, baseline degradation acceptance, colliding user changes, destructive/irreversible external action, cost-affecting mode override, commit/PR/merge choice) follow the shared batch-clarification protocol. Reuse a recorded authorization while its exact operation and conditions remain unchanged. Scope ambiguity returns to `delivery-frame-spec`; design/task ambiguity returns to `delivery-plan-tasks`.

## Task Loop

For each ready task: mark only it in progress → load only its required context → write a failing behavior test when appropriate → confirm it fails for the intended reason → minimal implementation → task-level validation to green → refactor under passing tests → check diff against allowed/forbidden scope → record evidence and mark only proven work complete → next dependency-ready task.

Do not bulk-check tasks at the end. Do not uncheck unrelated tasks because final integration failed; reopen only affected work plus the final verification gate.

## TDD Rules

RED → GREEN → REFACTOR for behavior changes and bug fixes when infrastructure supports it.

**Timing guard (required):** never issue the failing-test edit and the production-code edit in the same parallel tool batch. Sequence: write the failing test only → run and **observe** RED for the intended reason → minimal implementation → observe GREEN. If this agent wrote implementation before its test, remove that unverified implementation and restart with RED (never delete pre-existing user code).

If TDD is genuinely unsuitable, record why, the approved alternative, and the residual coverage gap. Do not install a large framework solely for ceremony.

## Systematic Debugging Switch

Any bug, failed test, or unexpected behavior pauses ordinary implementation: reproduce → capture logs/input/environment → bound the failing path → one falsifiable root-cause hypothesis → one minimal experiment → fix root cause → run original reproduction and regressions. Do not classify a failure as flaky because a retry passes; require evidence of nondeterministic infrastructure/timing.

## Decision Routing and Alignment Backflow

| Discovery | Return/update |
|---|---|
| fact establishable from code/tests/logs/config | investigate; record evidence in the current task |
| behavior or acceptance wrong/unknown | `delivery-frame-spec` (brief/spec + approval) |
| design/decomposition, cost, migration, compatibility, rollback, or operations wrong/unknown | `delivery-plan-tasks` (design/tasks/readiness + gate) |
| low-risk reversible detail inside approved scope | decide in the current task; record rationale |
| current-stage authorization/exception needed | ask here via user decision clicks |
| impact expands or red-line domain appears | `delivery-frame-spec` (risk/route/gates) |

Pause affected mutation before backflow; update authoritative artifacts before continuing code. Every return to frame/plan carries this packet in the task/verification record and handoff:

```text
alignment_backflow:
  discovery / evidence / affected_scope / invalidated_artifacts /
  decision_needed / recommended_resolution / resume_point
```

The re-entering stage runs the three-item consume check in `handoff-contract.md` §7. Cascading invalidation: spec change invalidates plan/tasks/readiness/gate/affected acceptance/final verification; plan/tasks change invalidates readiness/gate/affected validation/final verification; detail change invalidates affected task validation and final verification. After correction: re-run the affected gates, resume only affected tasks, and always run fresh final verification before close.

## Fresh Verification Gate

Immediately before any completion claim, run `references/artifact-gate-checks.md` items G1–G6 as applicable. Then: identify the commands proving current requirements → run the full current set → read complete output/exit codes/failure counts → verify each Requirement/Scenario against implementation → check diff/impact against plan and forbidden scope → run risk-appropriate code review → resolve CRITICAL, fix or explicitly accept WARNING → record commands, time, outputs, residual risk.

Runtime tests prove current runtime/static state; OpenSpec verify proves spec completeness/coherence. Neither substitutes for the other.

## Verified close-out protocol

Trigger (all required): implementation go recorded; every authoritative task `- [x]` (or lightweight contract fully done); Fresh Verification Gate freshly passed with recorded evidence; spec coherence check passed with no blocking gaps; code review gate satisfied — **Medium/High: an independent reviewer (separate SubAgent or human) returns `pass`/`warn` with no CRITICAL** (`code_review.mode: independent`; SubAgent review is always available, so there is no self-review close for Medium/High); Low: independent review by default, `low_accepted` only if the user explicitly declines and accepts residual risk; no open blocking residual.

Then, in the same turn: write/update `verification.md` (template: `references/verification-template.md`) with evidence and residuals → set `overall_status: verified` + `archive.status: deferred_to_openspec` → state that sync/archive is not done here and the next step is the resolved `archive_change` operation → offer optional next steps (archive, then commit/PR/merge/keep) — **ask** before any git mutation.

Use the close-out wizard to eliminate hand-written close-out JSON: `../delivery-frame-spec/scripts/delivery_scaffold.mjs close-out --change-dir <change> --review-status pass --reviewer <id> --evidence "<command: result>" [--approved-by <who>]`. It runs `validate_delivery_change --claim-verified`, computes the revision, emits and validates the verified handoff, and persists `handoff.json` — it never runs archive or git. The review/evidence flags describe work that already happened; the wizard is a recorder, not a substitute for the gates.

Must not claim verified when any required validation failed or was not freshly run, any authoritative task remains open, or Medium/High independent review is missing. Non-blocking residuals (optional release smoke, accepted WARNINGs, `no writeback needed`) do not block close-out when recorded in evidence.

After close-out, decide whether to update README, CONTEXT, ADR, Wiki, or a reusable Skill (canonical `specs/` updates happen during OpenSpec archive, not here); record `no writeback needed` when applicable.

## Review

Review for correctness and edge/failure behavior; security/privacy/permission where applicable; migration/rollback/compatibility; maintainability and project patterns; tests and falsifiability; unintended scope and user changes. Treat review suggestions as hypotheses: verify before changing; re-run affected and final validation after fixes.

## Handoff

Follow the shared contract and template (Execute block). Put execution, verification, review, archive deferral, and alignment backflow in `stage_payload`; persist `handoff.json` after validation. Never project `closed` or an archive path before OpenSpec archive actually completes.

## References

Read as needed:

- `references/implementation-loop.md` — task/debug records, TDD timing guard
- `references/verification-template.md`
- `references/artifact-gate-checks.md` — G1–G8
- `references/subagent-orchestration.md` — Chinese templates and checklists
- `scripts/validate_delivery_change.mjs`
- `../delivery-frame-spec/scripts/delivery_scaffold.mjs` — new-handoff / quick-pack / close-out scaffolds
- `tests/` — dev-time regression scripts; run `tests/test_template_anchor_consistency.mjs` whenever templates or `validate_delivery_change.mjs` anchors change

## Red Flags

- Any mutation without a recorded explicit user go (any route).
- Required validation failing or not freshly run; "retry passed, therefore flaky"; OpenSpec verify treated as proof tests pass.
- Tasks bulk-checked/unchecked; tests deferred until all implementation ends.
- Parallel agents sharing files/state, dispatched before prerequisites integrate, or worktrees created over user uncommitted changes.
- A SubAgent given vague scope, whole-chat context, or permission to edit global task state; its summary trusted without diff, review, and integration validation.
- Medium/High `verified` without an independent review record.
- Scope expanding without artifact/risk backflow; returning upstream without the `alignment_backflow` packet; re-asking an unchanged recorded authorization.
- Merge recommendation or “done” language before evidence; review skipped for a closing release window.
- Syncing delta specs into `openspec/specs/` or moving the change to archive from this skill; claiming `closed`/archived when only this skill's gate passed.
- Violating the batch-clarification protocol (see its Anti-patterns).

Any red flag blocks verified close-out.

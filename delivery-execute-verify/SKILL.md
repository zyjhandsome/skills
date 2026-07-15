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

## Iron Rules

1. No mutation without a recorded explicit user go for this route (including Quick/Debug-Low).
2. No completion / merge / “done” language while required validation is failing or stale.
3. Ends at `overall_status: verified` + `stage_payload.archive.status: deferred_to_openspec` — **never** sync/archive OpenSpec inside this skill.
4. Default execute inline; parallel SubAgents only when independence checks pass. Trust diffs and reviews, not SubAgent summaries alone.
5. Stage end: emit one complete `delivery-handoff/v1` object, including in-progress, blocked, verified, and end states. If chaining is unsupported, tell the user to run the resolved OpenSpec archive operation only after verified; ask before any commit/PR.
6. Do **not** invent a parallel `delivery-archive` skill; do **not** paste long system essays into this `SKILL.md`.

## Overview

Implement only approved scope, keep authoritative tasks synchronized, switch to evidence-driven debugging on failure, and require fresh runtime plus specification evidence before completion.

**Close-out rule:** When the Fresh Verification Gate and review gates pass and all authoritative tasks are complete, this skill ends at `overall_status: verified`. Write verification evidence, offer next steps, and **do not** sync delta specs or archive the OpenSpec change here. Hand archive to the resolved OpenSpec `archive_change` operation so the installed version's sync summary and confirmations stay intact. Commit / push / PR remain user-gated and are never auto-executed.

## Language and artifacts

- This `SKILL.md` is English.
- **All human-facing Markdown artifacts default to Chinese** — verification reports, handoffs, orchestration and degradation records — following the Chinese templates under `references/`. Only paths, commands, code identifiers, raw tool/test output (paste as-is), and machine-readable keys/enums stay English. When OpenSpec holds artifacts, only its machine-parsed skeleton (defined in `delivery-frame-spec`) stays English.
- If the user works in another language, follow the user's language instead; machine keys still stay English.
- SubAgent machine statuses are English enums (`completed`, `completed_with_concerns`, `needs_context`, `blocked`); Chinese labels live in `references/subagent-orchestration.md`.

## Input Contract

Standard/High require:

- a compatible `delivery-handoff/v1` snapshot whose source/artifact revision matches current OpenSpec state;
- unique state source;
- approved plan/tasks;
- route/risk and implementation-gate record;
- validation commands/actions;
- forbidden scope.

Quick/Debug require:

- a compatible handoff/contract revision matching the current lightweight change;
- goal and non-goals;
- affected/candidate files or symbols;
- observable acceptance or reproduction;
- validation command;
- risk/unknowns;
- a recorded explicit user go for implementation bound to the current contract/artifact revision (approver/time/revision and accepted warning IDs).

For Debug:

- Low-risk scoped mutation may proceed only from a debug contract the user explicitly approved; read-only diagnosis needs no go.
- Medium-risk mutation requires Standard-route brief/spec, plan/tasks, readiness review, and the Standard/Medium approvals.
- High-risk/red-line investigation may continue read-only, but mutation requires High-route brief/spec, plan/tasks, readiness review, and both High gate records: specification-scope go **and** implementation go (each a **single** user ask; High’s design/tasks/rollback/security/validation checklist is Agent-internal at plan stage — see `batch-clarification.md` Gate ask shape).

Debug is not a risk level and never bypasses risk-appropriate gates.

If inputs are missing, return to `delivery-frame-spec` or `delivery-plan-tasks`. Do not invent an implicit requirement during implementation.

## Capability Adapters

Treat the four `delivery-*` skills and shared references as one atomic Family (`../delivery-frame-spec/references/family-contract.md`). OpenSpec is mandatory for mutating routes; Memory and Superpowers are preferred but degradable; SubAgent/worktree and structured UI are optional accelerators. Never invent a substitute Markdown artifact backend.

Expect compatible `family_version`, `capability_snapshot`, and `capability_bindings` in the incoming handoff. Trust nominal health but resolve/re-probe operations this stage relies on whose binding or state may have changed (index freshness after edits, OpenSpec reachability before verify). If the Family major is unsupported, stop automatic chaining; if bindings are absent, run the shared preflight/adapter discovery once here. Update both health and bindings in the final handoff.

**Preflight failure — fixed 3-line report (Chinese):**

```text
缺什么：<memory|openspec|superpowers 的具体异常枚举>
能否降级：<可 degraded 影响面证据 / OpenSpec unavailable 则必须停止实施与 verify>
下一步请你：<例如：恢复 OpenSpec 后再继续 / 接受 Memory degraded 并记录>
```

Naming convention: refer to external capabilities as repo + semantic capability — e.g. Superpowers `systematic-debugging`, OpenSpec `apply_tasks`, Codebase Memory MCP `trace_path`. Inside a subsection titled with the owning repo, bare capability names refer to that repo. Bare skill names elsewhere are reserved for the `delivery-*` family.

### OpenSpec — the only execution backend

Read `../delivery-frame-spec/references/openspec-adapter.md`, reuse or refresh `capability_bindings.openspec`, and resolve `inspect_change`, `apply_tasks`, `continue_artifacts`, `validate_structure`, `verify_coherence`, and `archive_change` as needed.

- OpenSpec tasks are the only task state.
- Use resolved `apply_tasks` for implementation and `continue_artifacts` when artifacts must change.
- Use resolved `validate_structure` / `verify_coherence` for specification–implementation coherence.
- **Do not** invoke `archive_change` inside this skill, and do not silently sync delta specs into the canonical specs area. After verified close-out, set handoff `next_action` to the resolved archive operation, preserving the current OpenSpec version's warnings and confirmation flow.
- Do not create duplicate Markdown tasks or treat verify as runtime proof.

If the active OpenSpec backend becomes unavailable, stop implementation and verification actions that depend on it. Restore OpenSpec before continuing. Never create emergency Markdown state beside an unresolved OpenSpec change.

Every route arrives with an OpenSpec change created in `delivery-frame-spec`: Quick/Debug-Low a lightweight change, Standard/High a full change. Use the current schema's resolved slots for tasks and verification evidence; common filenames are documented in the adapter but never override the active schema. If Quick/Debug-Low work escalates, re-enter `delivery-frame-spec` to upgrade the same change.

### Codebase Memory MCP — impact evidence

Use available graph/search/trace/snippet/change-impact capabilities to:

- locate implementation and failure paths;
- check actual blast radius against planned scope;
- identify affected callers/tests;
- review final diff impact.

Discover current schemas first. Ensure index freshness after changes when required; a change-impact query is not necessarily an index refresh.

This is code memory (evidence only): it locates paths and impact but never stores tasks or serves as the state source. Authoritative task state stays in the OpenSpec change.

If the snapshot marks `memory: stale-index | down`, use targeted source, tests, config, error stacks, and git diff/history. Record `evidence_mode: degraded` in the task/verification record, report the outage, and state what impact evidence is missing.

### Superpowers — quality methods

Use when relevant:

- `test-driven-development` for feature/bug behavior;
- `systematic-debugging` for failures or surprises;
- `verification-before-completion` before any success claim;
- `dispatching-parallel-agents` for 2+ proven-independent task domains;
- `subagent-driven-development` for fresh sequential implementers with per-task reviews;
- `using-git-worktrees` for safe file/process isolation;
- `requesting-code-review` and `receiving-code-review` for review loops;
- `finishing-a-development-branch` after evidence passes.

If the snapshot marks `superpowers: partial | missing` for a listed skill (exception, since installation is assumed), execute the equivalent inline protocols below and report the gap. These methods never become a second task owner.

## Preflight

Before editing:

1. Recover state and current task.
2. Verify the implementation gate and explicit user go are bound to the current artifact revision — including Quick and Debug-Low. If approval is missing or its revision differs, stop, mark it stale, and obtain a click-first go (see **User decision clicks**) before any mutation.
3. Confirm exact task scope, files/symbols, validation, dependencies, and that no unresolved alignment decision remains. Route any new uncertainty through **Decision Routing and Alignment Backflow** before mutation.
4. Inspect full repository status, including staged, unstaged, and untracked files; preserve unrelated user changes.
5. Check whether planned target files collide with user changes.
6. Run or confirm the task's baseline validation.
7. If baseline fails, switch to systematic diagnosis. Proceed only when evidence proves the failure pre-existed and is independent of the target behavior, and the user approves a degradation record containing command, failure signature, independence evidence, unaffected targeted checks, scope/risk, approver, time, and expiry. If independence is unknown or target acceptance is affected, block.
8. Stop if branch/artifacts diverged enough to invalidate the plan.

## Automatic SubAgent Orchestration

After preflight, resolve and record `capability_bindings.subagents`: availability, actual maximum concurrency, worktree support, and independent-review availability. Unknown concurrency defaults to one/inline; never infer capacity from desired parallelism. Then choose execution mode from task facts (do not ask the user unless isolation, uncommitted state, cost, or destructive integration requires a decision — then use **User decision clicks**).

**Default: inline.** Use sequential fresh SubAgents when multiple well-specified tasks need clean context + two-stage review but shared integration makes parallel unsafe. Use parallel batches only when 2+ tasks are dependency-ready with no overlapping files/shared mutable state, independent validation, isolated workspaces, and available concurrency slots — never exceed the resolved maximum or parallelize to fill idle Agents.

Build a dependency/file-ownership graph from approved `tasks.md` (Quick/Debug contract = single node unless it defines independent subtasks). Same-file tasks run sequentially; after each wave: review, integrate, validate, then next wave.

Worktree/git mutations require the same user authorization as ordinary git ops. Never stash/commit/discard user uncommitted changes to enable worktrees. Full worktree/integration checklist: `references/subagent-orchestration.md`.

SubAgent packet must be self-contained (scope, files, validation, return format); SubAgents must not edit global task state or reinterpret scope from whole-chat context. Statuses: `completed` | `completed_with_concerns` | `needs_context` | `blocked`. Main Agent inspects real diff, runs spec then quality review, integrates, validates, then updates OpenSpec tasks — never trust the summary alone.

**Fallback:** no SubAgent/worktree → inline sequential with same TDD/evidence gates. No independent reviewer → record `independent_review: unavailable` + `review_mode: self_fresh_context`; Low may close only with explicit user acceptance of residual risk; Medium/High stay blocked.

Read `references/subagent-orchestration.md` for Chinese templates; `references/subagent-orchestration-test.md` / `references/workflow-system-regression-test.md` when changing orchestration or cross-stage contracts.

## User decision clicks

Whenever this stage needs a fixed-choice user decision (missing implementation go, degradation acceptance, unsafe worktree / colliding user changes, destructive or irreversible external action, cost/isolation-affecting mode override, commit/PR/merge choice), follow `../delivery-frame-spec/references/batch-clarification.md`: click first, typing fallback; no named IDE/tool; gate decisions separate from product waves; independent blockers in one wave; every question needs「推荐：」+「建议：」; multi-question waves never use「全部按推荐」; High five facets never become a user quiz. When a host question tool is available, map the wave through `../delivery-frame-spec/references/question-ui-adapters.md`. Reuse a recorded authorization while its exact operation and conditions remain unchanged. Scope ambiguity returns to `delivery-frame-spec`; design/task ambiguity returns to `delivery-plan-tasks`.

## Task Loop

For each ready task:

1. Mark only that task in progress.
2. Load only its required context.
3. Write a failing behavior test when appropriate.
4. Run it and confirm failure is due to missing behavior.
5. Write minimal implementation.
6. Run task-level validation to green.
7. Refactor only under passing tests.
8. Check diff against allowed/forbidden scope.
9. Record evidence and mark only proven work complete.
10. Continue to the next dependency-ready task.

Do not bulk-check tasks at the end. Do not uncheck unrelated tasks merely because final integration failed; reopen/block only affected work plus the final verification gate.

## TDD Rules

Use test-driven development for behavior changes and bug fixes when infrastructure supports it:

- RED: minimal failing test, observed failing for the intended reason.
- GREEN: minimal implementation, observed passing.
- REFACTOR: cleanup while all relevant tests remain green.

**Timing guard (required):** Do **not** issue the failing-test edit and the production-code edit in the same parallel tool batch. Sequence must be:

1. write/adjust the failing test only;
2. run it and **observe** RED (import error / assertion failure for the intended reason);
3. only then write minimal implementation;
4. run and observe GREEN.

If this agent wrote implementation before its test, remove that unverified implementation and restart the behavior with RED. Do not delete pre-existing user code.

If TDD is genuinely unsuitable, record why, the approved alternative, and residual coverage gap. Do not install a large framework solely for ceremony.

## Systematic Debugging Switch

Any bug, failed test, or unexpected behavior pauses ordinary implementation:

```text
reproduce
→ capture logs/input/environment
→ bound the failing path
→ form one falsifiable root-cause hypothesis
→ run one minimal experiment
→ fix root cause
→ run original reproduction and regressions
```

Do not classify a failure as flaky because a retry passes. Require evidence of nondeterministic infrastructure/timing rather than product behavior.

## Decision Routing and Alignment Backflow

| Discovery | Return/update |
|---|---|
| fact can be established from code/tests/logs/config | investigate and record evidence in the current task; do not ask the user |
| behavior or acceptance is wrong/unknown | `delivery-frame-spec`; brief/spec and approval |
| design/task decomposition, cost, migration, compatibility, rollback, or operational plan is wrong/unknown | `delivery-plan-tasks`; design/tasks/readiness and implementation gate |
| low-risk reversible implementation detail inside approved scope | decide in the current task and record rationale; do not ask the user |
| current-stage authorization/exception is required | ask here through **User decision clicks** and record the decision |
| impact expands or red-line domain appears | `delivery-frame-spec`; risk/route/gates |

Pause affected mutation before backflow. Update authoritative artifacts before continuing code. Every return to frame/plan must carry this packet in the task/verification record and handoff:

```text
alignment_backflow:
  discovery: <what changed or became unknown>
  evidence: <code/test/log/diff anchors>
  affected_scope: <requirements/design/tasks/validation affected>
  invalidated_artifacts: <artifacts and approvals now stale>
  decision_needed: <one concrete decision or correction required>
  recommended_resolution: <recommendation + material impact>
  resume_point: <task/check to resume after re-approval>
```

Do not make the user reconstruct context. If several independent backflow decisions share the same owner stage, that stage presents them in one wave; dependent decisions remain sequenced.

### Cascading invalidation and re-entry

Before backflow, mark downstream truth stale:

- spec change invalidates plan/tasks, readiness, implementation gate, affected task acceptance, and final verification;
- plan/tasks change invalidates readiness, implementation gate, affected task validation, and final verification;
- implementation-detail change invalidates the affected task validation and final verification.

After correction:

1. re-run the specification gate if behavior/scope changed;
2. re-run readiness review whenever plan/tasks changed;
3. obtain the risk-appropriate implementation gate again;
4. resume only affected tasks;
5. always run fresh final verification before close.

## Granular Task State

Maintain separate truth for:

- individual task implementation;
- task-level validation;
- integration/final validation;
- specification verification;
- code review;
- close-out readiness (verified vs still open).

One final failure blocks overall completion but does not erase evidence for independent completed tasks. Reopen tasks whose acceptance is invalidated. Archive/sync of the OpenSpec change is a separate OpenSpec step after this skill.

## Fresh Verification Gate

Immediately before any completion claim, run `references/artifact-gate-checks.md` items G1–G6 as applicable. Then:

1. Identify commands/actions proving current requirements.
2. Run the full, current set.
3. Read complete output, exit codes, and failure counts.
4. Verify each Requirement/Scenario against implementation.
5. Check diff/impact against plan and forbidden scope.
6. Run code review appropriate to risk.
7. Resolve CRITICAL; fix or explicitly accept WARNING.
8. Record commands, time, outputs, degradations, and residual risk.

Runtime tests and specification verification are complementary:

- tests/build/E2E prove current runtime/static state;
- OpenSpec verify or equivalent proves completeness/correctness/coherence.

Neither substitutes for the other.

## Verified close-out protocol

Trigger (all required):

1. Implementation go was recorded earlier for this route.
2. Every task in the authoritative `tasks.md` is `- [x]` (or the Quick/Debug lightweight contract is fully done).
3. Fresh Verification Gate just passed with recorded commands/time/results (runtime/static as required by the plan).
4. Spec coherence check done (OpenSpec `validate` / verify or equivalent) with no blocking gaps.
5. Code review gate satisfied for the route risk:
   - **Medium/High:** an **independent** reviewer (separate SubAgent or human) must return `pass` or `warn` with no CRITICAL; record `code_review.mode: independent` and `independent_review: required_pass|required_warn_accepted`. **`self_fresh_context` never closes Medium/High.**
   - **Low:** independent preferred; if unavailable, `independent_review: low_accepted` only with explicit user acceptance of residual risk.
6. No open **blocking** residual (CRITICAL findings, failing required tests, incomplete required tasks).

Then, **in the same turn**:

1. Write/update `verification.md` (or equivalent attachment) under the change with evidence and residuals.
2. Set handoff `stage_payload.overall_status: verified` and `stage_payload.archive.status: deferred_to_openspec`.
3. State clearly that OpenSpec sync/archive is **not** done by this skill; recommended next step is the resolved `archive_change` operation for the active change — keep its interactive sync summary and confirms.
4. Offer optional next steps: OpenSpec archive, then commit / PR / merge / keep working tree — **ask** before any git mutation.

**Must not claim verified when:**

- any required validation failed or was not freshly run;
- any authoritative task remains `- [ ]`;
- Medium/High independent review is still required and missing, or review `mode` is `self_fresh_context`;
- OpenSpec backend is `unavailable` when verify depends on it.

**Non-blocking residuals do not block verified close-out** when recorded in verification evidence, for example:

- optional manual release smoke (real media binary, installer UI) explicitly marked non-blocking / post-release;
- accepted WARNING findings with rationale;
- `no writeback needed` for README/Wiki.

Do not auto-sync or auto-archive to “finish the loop.” Do not invent a second delivery archive skill that bypasses OpenSpec prompts.

## Review

Review for:

- correctness and edge/failure behavior;
- security/privacy/permission where applicable;
- migration/rollback/compatibility;
- maintainability and project patterns;
- tests and falsifiability;
- unintended scope and user changes.

Treat review suggestions as hypotheses: verify before changing. Re-run affected and final validation after fixes.

## Close and Write Back

Only after all gates pass:

1. mark final task/verification state complete;
2. run the **Verified close-out protocol** (evidence + `verified` handoff) — do **not** sync or archive OpenSpec here;
3. point `next_action` at the resolved OpenSpec `archive_change` operation, then offer branch/PR/merge/keep options without destructive cleanup (**ask** before commit/push/merge);
4. decide whether to update README, CONTEXT, ADR, Wiki, routing rules, or a reusable Skill (canonical OpenSpec `specs/` updates happen during OpenSpec archive/sync, not here);
5. explicitly record `no writeback needed` when applicable;
6. report evidence, residual risks, and that archive is deferred to OpenSpec.

Never commit, push, or merge merely because a manager requests success wording. Never silently sync/archive OpenSpec changes from this skill.

**Scope boundary:** this skill ends at verified evidence, knowledge writeback decisions, and an explicit handoff to OpenSpec archive + git/PR options. Deployment, rollout (canary/feature flags), and post-release monitoring are out of scope.

## Handoff

Before handing off, read `../delivery-frame-spec/references/handoff-contract.md` and emit one complete, strictly parseable `delivery-handoff/v1` JSON object using `references/handoff-template.md`. Put execution, verification, review, archive deferral, and alignment backflow in `stage_payload`. When local Python is available, validate the final object with `../delivery-frame-spec/scripts/validate_handoff.py` before output.

Presentation projection is view-only: when supported, show `tasks` from authoritative task state, `review` from fresh verification/code review, and `handoff` for continuation, backflow, or OpenSpec archive. Otherwise render the same information as Markdown. Never project `closed` or an archive path before OpenSpec archive actually completes.

Record `presentation_capability` using the shared contract. For `delivery-ui/v1` or `legacy-v0`, follow `../delivery-frame-spec/references/structured-presentation-adapter.md`; when capability is unknown, use Markdown. Preserve canonical capability enums and map them only in the UI projection.

Rules:

- Do not use optimistic completion language while any required gate is failing or stale.
- When gates pass, `overall_status` is `verified` and `archive` is `deferred_to_openspec` (unless genuinely N/A); `next_action` must name OpenSpec archive when a change remains active.
- Pass the final `capability_snapshot` forward; update it if Memory/OpenSpec/Superpowers state changed during execution.
- If skill chaining is unsupported, stop after this handoff and tell the user the exact resolved `archive_change` command/operation; if no binding exists, report that instead of guessing an alias. Ask before commit/PR.

## References

Read as needed:

- `references/implementation-loop.md`
- `references/verification-template.md`
- `references/handoff-template.md`
- `references/artifact-gate-checks.md`
- `references/subagent-orchestration.md`
- `references/subagent-orchestration-test.md`
- `references/workflow-system-regression-test.md`
- `scripts/validate_delivery_change.py`
- `../delivery-frame-spec/scripts/validate_handoff.py`
- `../delivery-frame-spec/references/family-contract.md`
- `../delivery-frame-spec/references/openspec-adapter.md`
- `../delivery-frame-spec/references/handoff-contract.md`
- `../delivery-frame-spec/references/question-ui-adapters.md`
- `../delivery-frame-spec/references/structured-presentation-adapter.md`

## Red Flags

- Any mutation starts without a recorded explicit user go (any route, including Quick/Debug-Low).
- Binding user decisions to a named IDE/agent/tool, dribbling independent gate decisions across turns instead of one wave, omitting the required recommendation on a fixed-choice question, switching mode only to obtain a choice UI, or offering「全部按推荐」/ bulk-accept that skips per-question user choice.
- Required validation fails or was not freshly run.
- "Retry passed, therefore flaky."
- OpenSpec verify is treated as proof tests pass.
- All tasks are bulk-checked or bulk-unchecked.
- Tests are deferred until all implementation ends.
- Independent tasks are not delegated despite available safe SubAgent isolation, without a recorded reason.
- Parallel Agents share files/state or start before prerequisites are integrated.
- Worktree tasks are dispatched before integration authorization and destination are known.
- Baseline failures or target-file collisions are ignored.
- A SubAgent receives vague scope, whole-chat context, or permission to edit global task state.
- SubAgent summary is trusted without diff, review, and integration validation.
- A fresh-context self-review is labeled independent.
- Medium/High `verified` with `code_review.mode: self_fresh_context` or missing `independent_review`.
- User uncommitted changes are stashed/committed/discarded to make worktrees convenient.
- Random multi-fix debugging.
- Scope expands without artifact/risk backflow.
- Asking the user to resolve product/design ambiguity inside execute, or returning upstream without the evidence-backed `alignment_backflow` packet.
- Re-asking an unchanged, already recorded authorization.
- Review is skipped because the release window is closing.
- Merge recommendation or “done” language before evidence.
- Syncing delta specs into `openspec/specs/` or moving the change to `openspec/changes/archive/` from this skill (bypasses OpenSpec archive).
- Claiming `closed` / archived while only this skill’s verified gate passed.
- Asset writeback silently omitted.

Any red flag blocks verified close-out.

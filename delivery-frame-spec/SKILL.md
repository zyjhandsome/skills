---
name: delivery-frame-spec
description: >-
  Use when starting, resuming, investigating, or reframing a software development
  request before implementation readiness is established — e.g. “请处理这个开发需求”,
  “给需求定框”, “明确需求边界”, “判断 Quick/Standard/High”, add/change a feature,
  clarify scope, route Quick/Standard/High/Debug, or recover an OpenSpec change.
  Default entry when the change intent is clear. Hands off to delivery-plan-tasks
  or delivery-execute-verify (or delivery-explore if direction is still open).
---

# Delivery Frame Spec

Shared family protocol (versioning, hard prerequisites, language rules, naming): `references/family-contract.md`. Handoff schema, persistence, and templates: `references/handoff-contract.md` + `references/handoff-template.md`. Question protocol: `references/batch-clarification.md`. Do not restate those files; follow them.

## Iron Rules

1. No implementation until an explicit user go is recorded for this route (Quick/Debug-Low: contract go here; Standard/High: implementation gate in `delivery-plan-tasks`).
2. OpenSpec is the only artifact/state backend — never invent parallel Markdown state beside a change.
3. If direction is still open, hand to `delivery-explore`; do not invent a locked goal.
4. Specification gate = **one** user ask. High’s five facets stay Agent-internal — never a user multi-quiz.
5. Stage end: emit one complete `delivery-handoff/v1` object (including read-only, blocked, and end states), validate, persist per the handoff contract. When a transition is allowed, follow the chain relay rule (`family-contract.md` §1): if the host can load skill files directly (e.g. Claude Code), read the next skill's `SKILL.md` and continue in the same session; only when the host cannot, tell the user「请使用 <next_skill>」.
6. OpenSpec / Codebase Memory MCP / Superpowers / SubAgent are hard prerequisites: use them directly; on a real runtime failure stop and report per `family-contract.md` — no degraded modes, no substitute backends.

## Overview

Default entry point for development requests. Route internally, establish the minimum trustworthy code facts, align intent with reality, and produce only the artifacts required by risk. Never expose a separate "router step" to the user — routing is the first operation of this skill.

### 30-second routing card

| Route | Use when | Next |
|---|---|---|
| Read-only | Explain/investigate; no change requested | end |
| Quick | Bounded impact; **no** red-line domain; reversible | contract go → `delivery-execute-verify` |
| Standard | Feature/cross-file/unclear fit; default risk Medium | spec gate → `delivery-plan-tasks` |
| High | Auth/payment/privacy/migration/public API/core path, or multiple escalation signals | spec gate → `delivery-plan-tasks` (stronger gates) |
| Debug | Failure/regression/flake — then apply **actual** Low/Medium/High risk for mutation | Low fix → execute; Med/High mutation → Standard/High path |

Unable to judge → bias higher. Red-line hit → **not** Quick. Negative cases and gate details: `references/routing-and-gates.md`.

## Brief part names

The brief has one physical body: `proposal.md` in the active OpenSpec change (structure and Chinese headings: `references/brief-template.md`). Refer to parts by stable name, never section numbers: Intent（意图）· Code Facts（代码事实，含证据表）· Current State（现状摘要）· Reuse & Conflicts（可复用/需扩展/冲突）· Mount Points（挂载点候选）· Ripple（波及线索）· Alignment & Gates（消歧与闸门）· Open Questions（开放问题清单）· Risk Rating（风险定级与闸门建议）· Explore Handoff Consume（Explore 交接消费）· State Source（状态源与工件位置）.

Authority: product decisions only in **Open Questions**; gate approvals only in **State Source**.

## Start Here

1. Identify the project root and user request.
2. Recover existing state before creating anything: user-provided artifact path first, then existing OpenSpec change relevant to the request. If state and artifacts disagree, stop and report the exact mismatch; do not rebuild from chat memory.
3. Inspect only enough evidence to classify the request and bound impact (Memory-first: architecture, graph search, `trace_path`, snippets). Stop investigating once evidence suffices to choose a route; deep design belongs to `delivery-plan-tasks`.
4. Choose Read-only, Quick, Standard, High, or Debug.
5. Complete this skill's route-specific output.
6. Hand off explicitly to `delivery-plan-tasks`, `delivery-execute-verify`, or end.

If the product direction is genuinely open (suggestions, opportunity mapping, “what should we build next?”), hand the user to `delivery-explore` first; resume framing after a direction is chosen.

## Capability roles

- **Codebase Memory MCP** — evidence provider only: architecture, symbols, call paths, snippets, blast radius. Discover the current tool schema before calling. It indexes code facts, never requirement artifacts, state, or product decisions. Index freshness rule: `family-contract.md` §5. When OpenWiki/ADR/glossary exist and are in scope, read them as semantic context; if docs and the physical call graph disagree, prefer the call graph and verify with source/tests.
- **OpenSpec** — the only artifact backend. Resolve semantic operations via `references/openspec-adapter.md`; record bindings in `capability_bindings.openspec`. Recover/create one change through `inspect_change` / `create_change`. This skill owns framing and gates; OpenSpec owns physical change/artifact state.
- **Superpowers** — method layer. Prefer `delivery-explore` for open ideation; brainstorming disciplines may inform framing but never own artifacts, state, or question delivery.

### Artifact depth by route

| Route | Change artifacts | Next stage |
|---|---|---|
| Read-only | none (no change) | end |
| Quick / Debug-Low | lightweight change: `proposal.md` carries the contract, minimal `tasks.md`; no `design.md`. If the active schema’s `validate` requires ≥1 delta, add a **minimal** `specs/<cap>/spec.md` (one Requirement + Scenario) — do not expand to Standard depth | `delivery-execute-verify` |
| Standard / High | full change: `proposal.md` (brief) + delta spec now; `design.md` + `tasks.md` in `delivery-plan-tasks` | `delivery-plan-tasks` |
| Debug — Medium / High mutation | Standard / High artifacts respectively | `delivery-plan-tasks` |

Map Delivery artifacts to the slots the current OpenSpec schema reports (`references/openspec-adapter.md` §3). When a Quick task escalates, upgrade the same change; never start a second state source.

## Routes

### Read-only

Explanation or investigation without requested changes. Output: conclusion, evidence, uncertainty, no mutation. End.

### Quick

Only when impact is bounded and **no** red-line domain is involved (auth, payment, permission, privacy, migration, concurrency, public API/protocol, destructive behavior, core business paths are **never** Quick). Create the lightweight contract (`references/routing-and-gates.md` has the shape): goal/non-goals, affected files/symbols, observable behavior, minimum validation, forbidden scope, risk/unknowns, clarification completeness sweep result. Prefer scaffolding it: `scripts/delivery_scaffold.mjs quick-pack --change-dir openspec/changes/<id> --capability <cap> --goal … --impact …` emits proposal/minimal delta spec/tasks with the exact machine anchors `validate_delivery_change.mjs` reads — fill the placeholders, then run the schema's `validate`. Quick has no `design.md` **by design**: when `openspec status` shows design incomplete, tell the user that is expected for this lane; never write a filler design to satisfy status. Clarify blocking product questions via batch clarification. Present the contract, obtain an explicit go (e.g. “开始实施”), record approver/time/contract revision/accepted warning IDs, then hand off to `delivery-execute-verify`. A complete contract without a revision-bound go does not authorize implementation.

### Standard

Features, cross-file behavior, refactors, unclear requirement/code fit. Produce the full brief + delta spec, pass the specification gate, hand off to `delivery-plan-tasks`. Default risk Medium; escalate to High on red-line or multiple combined signals.

### High

Same artifact set as Standard; differences are trigger and gate strength:

| Dimension | Standard (Medium) | High |
|---|---|---|
| Trigger | any single escalation signal | red-line domain, or multiple combined signals |
| Risk Rating | hit/miss/uncertain + gate advice | same, plus why each red-line surface is or is not touched |
| Implementation gate (plan stage) | single go ask | same single go ask + cost/risk/rollback summary; five facets Agent-internal |
| Plan content | rollback/migration/security as applicable | rollback, security, migration mandatory, each falsifiably validated |
| Review at execute | independent review required | same; no acceptance shortcut |
| Debug re-entry | Debug-Medium mutation | Debug-High mutation; needs both High approvals |

If a High row cannot be satisfied, stay blocked; do not quietly run it as Standard.

### Debug

Failures, regressions, flaky tests, unexpected behavior. Output a scoped debug contract: symptom, reproduction entry, candidate boundary, non-goals, regression command, route risk, sweep result, approval state.

- Low-risk scoped diagnosis may proceed read-only; a Low-risk fix requires explicit user approval of the debug contract before `delivery-execute-verify`.
- Medium-risk mutation enters the Standard route (brief/spec + plan + Standard gates).
- High-risk/red-line mutation enters the High route (both High gates). Debug is a request mode, not a risk level; never a bypass.

## Risk Rules

Any one of these requires at least Standard: crosses module/service/process/database boundaries; changes shared state, persistence format, public infrastructure, or callers; lacks adequate validation for the core path; introduces a dependency or deployment/CI change; conflicts with ADR/constitution/current spec/observed behavior; impact cannot be bounded. Red-line domain or multiple combined signals → High.

Risk Rating writing must include hit features, missed High features, uncertainties, and gate advice — never a bare label. Unable to judge → Medium; uncertain → bias higher. The agent may recommend risk with evidence but must not self-approve a Medium/High downgrade.

## Alignment Loop (Standard / High; Quick when blocking questions exist)

**Phase A — Inventory:** draft Intent; inspect targeted current behavior and fill Code Facts + Evidence Table; separate facts / inferences / decisions (product decisions only in Open Questions); fill Alignment & Gates; publish the full Open Questions list. Then run the **facts readiness gate** (`references/routing-and-gates.md`). If passed → show the brief and **immediately** start the first clarification wave; do not wait for a verbal “confirm brief.”

**Phase B — Disambiguation:** follow `references/batch-clarification.md` for waves, ordering, recommendations, stop condition, and the clarification completeness sweep (Chinese wording example: `references/clarification-example.md`; host tool mapping: `references/question-ui-adapters.md`). Record every answer in Open Questions only; update Intent boundaries. Do not ask what code/tests/logs/config can establish. Sensible defaults without asking only for low-risk, reversible, in-scope choices that don't alter observable product behavior — record the assumption; never use a default to bypass a gate or a blocking Open Question.

Then write/update the delta spec and run the Specification Gate.

**Explore-handoff consume self-check (required):** when a `delivery-explore` handoff is present, the active `proposal.md` MUST contain the five-checkbox **Explore Handoff Consume** block (`references/brief-template.md`), all boxes checked and matching the body; with no explore handoff, the section is one line `N/A — 无 explore handoff`. Chat-only summary or empty section = gate failure. `risk_signal` is a hint only; re-derive route/risk from evidence.

## Evidence Discipline

Label every important statement **Fact** (code/test/log/config/approved doc), **Inference** (needs confirmation), or **Decision** (explicit user/approved choice). Bind facts in the Evidence Table to paths/symbols/tests/queries. Mark unknowns; never convert uncertainty into a confident requirement.

## Specification Gate

Agent checklist — not a user multi-quiz:

- Intent explicit (goal, non-goals, success criteria);
- Code Facts (with Evidence Table) and Alignment & Gates present; facts readiness passed;
- critical facts evidenced; inferences labeled;
- blocking Open Questions decided or explicitly deferred as non-blocking; no implementation-blocking TBD;
- clarification completeness sweep recorded;
- requirements have falsifiable scenarios and failure behavior; applicable non-functional constraints captured with acceptance criteria or explicitly out of scope;
- route and risk match evidence (Risk Rating complete);
- Explore Handoff Consume block satisfied;
- Medium/High scope approval persisted in State Source.

If any check fails, remain in this skill. When it passes, ask **one** scope-approval question (Gate ask shape in `batch-clarification.md`); persist answer, approver, time, artifact revision, and accepted warning IDs in State Source; then hand off.

## Backflow re-entry

When Execute returns here with an `alignment_backflow` packet, complete the three-item re-entry consume check in `handoff-contract.md` §7 before reopening any gate.

## Handoff

Follow `references/handoff-contract.md` + `references/handoff-template.md` (Frame block). Put route, risk, confirmed artifacts, forbidden scope, and open questions in `stage_payload`. Generate the skeleton instead of typing it: `scripts/delivery_scaffold.mjs new-handoff delivery-frame-spec --change-dir <change>` (computes `artifact_revision` and timestamps; you fill only business fields and the gate).

## Red Flags

- Creating a new state source before checking for one; any parallel `brief.md` / state file beside the change's `proposal.md`.
- Reading the whole repository before choosing a route.
- Writing implementation code during Standard/High framing; handing off without a recorded user go.
- Choosing Quick for a red-line domain, or because documentation feels expensive.
- Waiting for an explicit “confirm brief” after the facts readiness gate passed.
- Skipping the Explore-handoff consume self-check; recording product decisions outside Open Questions.
- Violating the batch-clarification protocol (padding, bulk-accept, missing recommendation, dependent questions in the same wave, five-facet user quiz — full list in `batch-clarification.md` Anti-patterns).
- Treating Codebase Memory output as a product decision; letting an auxiliary skill redefine scope.

Any red flag: stop, correct the artifact/state, re-run the relevant gate.

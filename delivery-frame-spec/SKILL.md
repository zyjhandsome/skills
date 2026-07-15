---
name: delivery-frame-spec
description: >-
  Use when starting, resuming, investigating, or reframing a software development
  request before implementation readiness is established — e.g. “请处理这个开发需求”,
  add/change a feature, clarify scope, route Quick/Standard/High/Debug, or recover
  an OpenSpec change. Default entry when the change intent is clear. Hands off to
  delivery-plan-tasks or delivery-execute-verify (or delivery-explore if direction
  is still open).
---

# Delivery Frame Spec

## Iron Rules

1. No implementation until an explicit user go is recorded for this route (Quick/Debug-Low: contract go here; Standard/High: implementation gate in `delivery-plan-tasks`).
2. OpenSpec is the only artifact/state backend — never invent parallel Markdown state beside a change.
3. If direction is still open, hand to `delivery-explore`; do not invent a locked goal.
4. Specification gate = **one** user ask. High’s five facets stay Agent-internal — never a user multi-quiz.
5. Stage end: emit the **required handoff subset**. If chaining is unsupported, tell the user「请使用 delivery-plan-tasks」or「请使用 delivery-execute-verify」(or explore) as applicable.
6. Do **not** add a fifth user-visible router skill; do **not** paste long system essays into this `SKILL.md`.

## Overview

This is the default entry point for development requests. Route internally, establish the minimum trustworthy code facts, align intent with reality, and produce only the artifacts required by risk.

**Hard gates:**

- Except for a user-approved Quick route or user-approved Debug/Low contract, do not write implementation code before the specification gate passes.
- **Universal implementation approval:** no route starts implementation without an explicit user go. Quick and Debug/Low obtain it as user approval of the lightweight/debug contract; Standard(Medium) and High obtain it at the implementation gate in `delivery-plan-tasks`. Contract or artifact completeness alone never authorizes implementation.

### 30-second routing card

| Route | Use when | Next |
|---|---|---|
| Read-only | Explain/investigate; no change requested | end |
| Quick | Bounded impact; **no** red-line domain; reversible | contract go → `delivery-execute-verify` |
| Standard | Feature/cross-file/unclear fit; default risk Medium | spec gate → `delivery-plan-tasks` |
| High | Auth/payment/privacy/migration/public API/core path, or multiple escalation signals | spec gate → `delivery-plan-tasks` (stronger gates) |
| Debug | Failure/regression/flake — then apply **actual** Low/Medium/High risk for mutation | Low fix → execute; Med/High mutation → Standard/High path |

Unable to judge → bias higher. Red-line hit → **not** Quick (see `references/routing-and-gates.md`).
## Language and artifacts

- This `SKILL.md` is English.
- **All human-facing Markdown artifacts default to Chinese** (brief/spec/contract bodies, headings, tables, prose), following the Chinese templates under `references/`. Only these stay English: paths, commands, code identifiers, machine-readable keys/enums (e.g. `capability_snapshot` keys, `medium`/`high`), and OpenSpec's machine-parsed skeleton (below).
- **OpenSpec backend exception:** `openspec validate` parses English structural markers. In OpenSpec-held specs keep `## Purpose`, `## Requirements`, `## ADDED/MODIFIED/REMOVED/RENAMED Requirements`, the `### Requirement:` / `#### Scenario:` header prefixes, and the `SHALL`/`MUST` keyword inside each requirement statement — write everything else (requirement names, scenario names, bodies) in Chinese, e.g. `### Requirement: 转写历史跨重启保留` + “系统 SHALL 在重启后仍显示历史记录”. `proposal.md`/`design.md` prose is fully Chinese.
- If the user works in another language, follow the user's language instead; the machine-parsed skeleton still stays English.
- Refer to brief parts by **stable English names** below. Do not use section numbers (`§`, `§§1–4`, etc.).

### Brief part names

The brief has one physical body: `proposal.md` in the active OpenSpec change.

| English name (use in this skill) | Chinese heading (use in the brief body) |
|---|---|
| Intent | 意图 |
| Code Facts | 代码事实 |
| Current State | 现状摘要 |
| Reuse & Conflicts | 可复用 / 需扩展 / 冲突 |
| Mount Points | 挂载点候选 |
| Ripple | 波及线索 |
| Evidence Table | 证据表 |
| Alignment & Gates | 消歧与闸门 |
| Open Questions | 开放问题清单 |
| Risk Rating | 风险定级与闸门建议 |
| Explore Handoff Consume | Explore 交接消费 |
| State Source | 状态源与工件位置 |

Brief structure: **Intent** → **Code Facts** (includes Evidence Table) → **Alignment & Gates** (includes **Explore Handoff Consume** before **State Source**).

Authority: product decisions only in **Open Questions**; gate approvals only in **State Source**.

## Start Here

1. Identify the project root and user request; reuse the incoming `capability_snapshot` or run the prerequisite preflight.
2. Recover existing state before creating anything.
3. Inspect only enough evidence to classify the request and bound impact.
4. Choose Read-only, Quick, Standard, High, or Debug.
5. Complete this skill's route-specific output.
6. Hand off explicitly to `delivery-plan-tasks`, `delivery-execute-verify`, or end.

If the product direction is still genuinely open (suggestions, opportunity mapping, “what should we build next?”), do not invent a locked goal here — hand the user to `delivery-explore` first, then resume framing after a direction is chosen.

Never expose a separate "router step" to the user. Routing is the first operation of this skill.

When chaining is unsupported, stop after the handoff and tell the user「请使用 <next_skill>」(or explore) as applicable.

## Capability Adapters

Use capabilities by role; never make them competing workflow owners. Codebase Memory MCP, OpenSpec, Superpowers, and all four `delivery-*` skills are **hard prerequisites** of this family, assumed co-installed (cross-skill `../delivery-*/references/…` paths depend on it). Treat any absence as an exception to report, not a normal mode; without OpenSpec only Read-only routes work — there is no substitute Markdown backend.

Naming convention: refer to external capabilities as repo + capability — e.g. Superpowers `brainstorming`, OpenSpec `apply` (`/opsx-apply`), Codebase Memory MCP `trace_path`. Inside a subsection titled with the owning repo, bare capability names refer to that repo. Bare skill names elsewhere are reserved for the `delivery-*` family.

### Prerequisite preflight — capability snapshot

The family tracks prerequisite health in one machine-readable `capability_snapshot`; this skill owns the definition:

```text
capability_snapshot:
  memory: ok | stale-index | down                  # MCP reachable; repo index present and fresh
  openspec: initialized | cli-only | unavailable   # repo adopted | CLI works but repo not initialized | CLI broken
  superpowers: loaded | partial(<missing>) | missing
```

Rules:

- If no snapshot arrived from `delivery-explore`, probe the three prerequisites once here (entry preflight) and record the snapshot.
- Installation is assumed, so `memory: stale-index|down`, `openspec: unavailable`, and `superpowers: partial|missing` are exceptions: report them and apply the matching adapter degradation. `openspec: cli-only` is a normal repo state and only drives the `openspec init` proposal; if the user declines init, routes that need formal artifacts stop with a reported stop condition instead of inventing a substitute backend.
- Trust nominal values from an incoming snapshot; re-probe only anomalies and capabilities this stage is about to rely on whose state may have changed (e.g. repo init state before creating a change).
- Update the snapshot when a capability's state changes, and pass it forward in the handoff.

**Preflight failure — fixed 3-line report (Chinese):** whenever any prerequisite is non-nominal in a way that blocks or degrades this stage, tell the user exactly:

```text
缺什么：<memory|openspec|superpowers 的具体异常枚举>
能否降级：<可 degraded 继续 / 必须恢复后才能变更 / 仅只读>
下一步请你：<例如：同意 openspec init / 修复 Memory 索引 / 仅继续只读调查>
```

### Codebase Memory MCP — evidence provider

Prefer it for architecture, symbols, call paths, snippets, and blast radius. Discover the current tool schema before calling it. Typical capabilities include:

- repository/index status and architecture;
- semantic or graph search;
- path/call tracing;
- targeted code snippets;
- change-impact detection.

This is **code memory**, not the artifact backend and not a file manager. It indexes code facts, not requirement artifacts. Never treat it as the state source, the artifact store, or a product decision; it only supplies evidence.

If the snapshot marks `memory: stale-index | down`, use targeted source, tests, config, docs, error stacks, and git history/diff; mark `evidence_mode: degraded` and report the outage. Never replace a graph query with an unbounded whole-repository text dump.

**Index freshness probe (required):** if a path/symbol is known to exist on disk (git status, user, prior read, or contract/tasks) but Memory `search_graph` / `search_code` / `get_code_snippet` misses it, you MUST set `memory: stale-index`, mark `evidence_mode: degraded`, and report via the fixed 3-line form. Do not treat a graph miss as proof the code is absent.

When project docs such as OpenWiki / ADR / glossary exist and are in scope, read them as semantic context. If missing or stale, note that; do not hard-require them. If docs and MCP call-graph disagree, prefer the physical call graph and sample source/tests to verify.

### OpenSpec — the only artifact backend

The OpenSpec CLI is a default-installed prerequisite. Repo-level adoption (`openspec init`) is tracked as `openspec: initialized | cli-only` in the snapshot. If the repository is not initialized, propose `openspec init`; if the user declines, mutating routes stop with a reported stop condition — there is no substitute Markdown backend.

- Recover/create one change (typically via OpenSpec `new`/`propose`, host command `/opsx-new` / `/opsx-propose`).
- Treat OpenSpec status and artifacts as the only state source.
- Do not create parallel state files, duplicate specs, or duplicate tasks.
- This skill owns framing and gates; OpenSpec owns physical change/artifact state.

#### Artifact depth by route

Every mutating route walks through an OpenSpec change. Routes differ in artifact depth and next stage, not in backend:

| Route | Change artifacts | Next stage |
|---|---|---|
| Read-only | none (no change) | end |
| Quick / Debug-Low | lightweight change: `proposal.md` carries the contract, minimal `tasks.md`; no `design.md` or delta spec required | `delivery-execute-verify` |
| Standard / High | full change: `proposal.md` (brief) + delta spec now; `design.md` + `tasks.md` in `delivery-plan-tasks` | `delivery-plan-tasks` |
| Debug — Medium / High mutation | Standard / High artifacts respectively | `delivery-plan-tasks` |

When OpenSpec holds a change, map artifacts to its slots instead of adding parallel files: `proposal.md` (why/what ≈ brief), `changes/<id>/specs/<cap>/spec.md` (delta spec), `design.md` (≈ plan), `tasks.md`. Non-native artifacts such as `verification.md` may attach under the default `spec-driven` schema, or become managed artifacts via a custom schema (`openspec schema init/fork`).

When a Quick task escalates to Standard, upgrade the same change with the full artifact set; never start a second state source.

### delivery-explore — optional pre-framing stage

When direction is open, prefer `delivery-explore` (Codebase Memory–grounded opportunity mapping) over inventing scope in this skill. Explore output is informal and is never an approved brief/spec. After the user picks a direction, this skill owns framing and gates.

#### Input Contract from explore handoff

When a `delivery-explore` handoff is present, consume these fields explicitly (do not invent a second state source from them):

| Incoming field | How this skill consumes it |
|---|---|
| `capability_snapshot` | Reuse nominal values; re-probe only anomalies and capabilities about to be relied on |
| `evidence_mode` | Carry forward; if `degraded`, keep Memory degradation marking in the brief |
| `chosen_direction` | Seed **Intent** goal (user may revise; confirmation is still required) |
| `non_goals` | Seed **Intent** boundaries / non-goals |
| `code_anchors` | Starting points for **Code Facts** / **Mount Points** targeted inspection |
| `risk_signal` | Routing **hint only** (`none` → likely Quick/Standard; `standard-likely` → Standard/Medium; `high-likely` → High). Re-derive route/risk from evidence; never treat explore’s signal as an approved risk level |
| `unknowns` | Candidate entries for **Open Questions** (not automatic decisions) |
| `state_source` | Must be `none`; this skill creates/recovers the OpenSpec change as the sole state source |
| `required_inputs` / `stop_condition` | Honor stop; otherwise require user confirmation of the chosen (or revised) direction before the specification gate |

**Explore-handoff consume self-check (required):** before the specification gate (or Quick contract go), the active change's `proposal.md` MUST contain the fixed checkbox block **Explore Handoff Consume** / Chinese heading `Explore 交接消费` from `references/brief-template.md` (Quick: same heading and five checkboxes inside the lightweight contract body — do not invent a parallel file).

- If a `delivery-explore` handoff is present: all five boxes MUST be checked, and each claim MUST match the brief/contract body (empty section, chat-only summary, or unchecked boxes = gate failure).
- If there was no explore handoff: the section MUST be a single line `N/A — 无 explore handoff` (not omitted).

The five checks (same meaning as the template checkboxes):

1. `chosen_direction` appears in **Intent** (or an explicit user-revised goal replaces it).
2. `non_goals` appear in **Intent** boundaries (or marked N/A with reason).
3. `code_anchors` drove at least one **Code Facts** / **Mount Points** inspection (paths/symbols cited).
4. `risk_signal` was treated as hint only; **Risk Rating** was re-derived from code facts (hit/miss/uncertain written).
5. `unknowns` were folded into **Open Questions** or explicitly dropped as non-blocking.

### Superpowers — method layer

Do not invoke `brainstorming` as a second workflow owner. Prefer `delivery-explore` for open ideation in the delivery family. If brainstorming disciplines are useful inside framing (concrete alternatives with tradeoffs), reuse them here without letting brainstorming own artifacts or state; question delivery follows this skill's batch clarification rules.

## Recover Before Creating

Check, in order:

1. User-provided state/artifact path.
2. Existing OpenSpec change relevant to the request.

If state and artifacts disagree, stop and report the exact mismatch. Do not rebuild from chat memory.

## Minimal Routing Investigation

Determine:

- request mode: answer/investigate/change/debug;
- likely files, symbols, callers, and tests;
- persistence, public contract, permission, migration, concurrency, or deployment impact;
- existing validation capability;
- whether an approved spec or executable tasks already exist.

Stop investigating once evidence is sufficient to choose a route. Deep technical design belongs to `delivery-plan-tasks`.

## Routes

### Read-only

Use for explanation or investigation without requested changes.

Output: conclusion, evidence, uncertainty, and no mutation. End.

### Quick

Use only when impact is bounded and **no** red-line domain is involved. Auth, payment, permission, privacy, migration, concurrency, public API/protocol, destructive behavior, and core business paths are **never** Quick — escalate to High (or Standard only when code facts prove that surface is untouched). See `references/routing-and-gates.md` negative cases.

Create a lightweight contract containing:

- goal and non-goals;
- affected files/symbols;
- observable behavior;
- minimum validation;
- forbidden scope;
- risk and unknowns.

Optionally include open product questions; when blocking, clarify them with batch clarification (rules below).

Present the contract to the user and obtain an explicit go (e.g. “开始实施”). Record the approval (approver/time) in the contract, then hand off to `delivery-execute-verify`. A complete contract without a recorded user go does not authorize implementation.

Persist the contract as a lightweight OpenSpec change (`proposal.md` carries the contract, minimal `tasks.md`; no `design.md` or delta spec). If the work later escalates, upgrade the same change to the full Standard/High artifact set.

### Standard

Use for features, cross-file behavior, refactors, or unclear requirement/code fit.

Produce the full brief (Intent + Code Facts + Alignment & Gates) plus spec, pass the specification gate, then hand off to `delivery-plan-tasks`.

Standard is the route name; its default risk level is Medium. Escalate to High when a red-line domain or multiple combined signals apply.

### High

Use for auth, payment, permission, privacy, migration, concurrency, public API/protocol, destructive behavior, or core business paths.

Produce the full brief plus spec, persist approval, and require a second implementation gate in `delivery-plan-tasks`.

#### Standard vs High — what actually differs

Both produce the same artifact set (full brief + delta spec here; `design.md` + `tasks.md` in `delivery-plan-tasks`). The differences are trigger and gate strength:

| Dimension | Standard (risk Medium) | High |
|---|---|---|
| Trigger | any single escalation signal (see Risk Rules) | red-line domain hit, or multiple combined signals |
| Risk Rating writing | hit/miss/uncertain + gate advice | same, plus must show why each red-line surface is or is not touched |
| Implementation gate (`delivery-plan-tasks`) | no blocking finding; warnings resolved or accepted; user confirms implementation (single go ask) | no blocking finding; Agent internally verifies design/tasks/rollback/security/validation into state source; user confirms with the **same single go ask**, plus cost/risk/rollback summary — never a five-facet user quiz |
| Plan content | rollback/migration/security sections as applicable | rollback, security, and migration sections mandatory, each with falsifiable validation |
| Review at execute stage | independent review required; degraded self-review never closes it | same, and no degradation acceptance can close it |
| Debug interaction | Debug-Medium mutation re-enters here | Debug-High mutation re-enters here and needs both High approvals |

If a table row cannot be satisfied for High, the work stays blocked; do not quietly run it as Standard.

### Debug

Use for failures, regressions, flaky tests, or unexpected behavior.

Output a scoped debug contract: symptom, reproduction entry, candidate boundary, non-goals, regression command, route risk, and approval state.

- Low-risk scoped diagnosis may proceed read-only; a Low-risk fix (any mutation) requires explicit user approval of the debug contract before handing off to `delivery-execute-verify`.
- Medium-risk mutation must enter the Standard route, complete brief/spec plus `delivery-plan-tasks`, and pass the Standard/Medium gates.
- High-risk or red-line diagnosis may remain read-only, but any mutation must enter the High route, complete brief/spec plus `delivery-plan-tasks`, and pass both High gates.

Debug describes the request mode; Low/Medium/High still governs approval strength. Do not use Debug to bypass Standard/High artifacts for a risky fix.

## Risk Rules

Any one of these requires at least Standard:

- crosses module/service/process/database boundaries;
- changes shared state, persistence format, public infrastructure, or callers;
- lacks adequate validation for the core path;
- introduces a dependency or deployment/CI change;
- conflicts with ADR, constitution, current spec, or observed behavior;
- impact cannot be bounded.

Any red-line domain or multiple combined signals suggests High.

Risk writing (Standard/High **Risk Rating**) must include: hit features, missed High features, uncertainties, and gate advice — not a bare label. Unable to judge → Medium; uncertain → bias higher; any High feature hit → default High unless code facts show that surface is untouched.

The agent may recommend risk with evidence. It must not self-approve a Medium/High downgrade.

## Backend Failure

If OpenSpec becomes unavailable after formal artifacts exist (`openspec: unavailable`):

1. stop mutation and implementation;
2. do not create a competing state/spec/tasks copy — no emergency Markdown state;
3. report the outage and last verified state, then restore OpenSpec before continuing.

## Brief (Standard / High)

Follow `references/brief-template.md`. Single body: the active OpenSpec change's `proposal.md`. Never a parallel `brief.md` or `code-fact-brief.md`. Quick / Debug-Low do not require the full brief structure.

Clarification wording for users lives in `references/clarification-example.md` (Chinese). Do not copy that SOP into the brief body.

### Facts readiness gate

Before writing the delta spec or starting product disambiguation, check:

- **Intent:** goal, success criteria, and boundaries/non-goals are written;
- **Code Facts** including **Evidence Table:** facts have evidence (**Mount Points** has a real required path; evidence bound in the table or inline);
- **Open Questions** is presentable; **Risk Rating** includes hit / miss / uncertain; **Explore Handoff Consume** is present (`N/A — 无 explore handoff`, or all five boxes checked when an explore handoff existed); **State Source** names one state source.

If passed → show the brief (including full **Open Questions**) and **immediately** start batch clarification with the first wave of independent blocking questions. Do **not** wait for “confirm brief.” If structure is missing or the user challenges facts / mount points / ripple → targeted re-inspect, update the same brief, re-check. Product choices in **Open Questions** still require interactive clarification.

## Alignment Loop

Two phases for Standard/High (and whenever Quick has blocking questions):

### Phase A — Inventory

1. Draft **Intent:** goal, non-goals, and success.
2. Inspect targeted current behavior; fill **Code Facts** and the **Evidence Table**.
3. Separate facts, inferences, and decisions; product decisions belong only in **Open Questions** (Evidence Table decision rows are indexes only).
4. Fill **Alignment & Gates**; publish **Open Questions** to the user (full list visible). Pass the facts readiness gate.

### Phase B — Disambiguation

5. Select every currently blocking **open** decision that materially changes scope, acceptance, risk, or irreversible behavior, ordered dependency-root first. Show the full **Open Questions** list (including which items are in this wave and any omitted non-blocking topics).
6. Clarify with **batch clarification** (rules below): one wave lists every currently independent blocking question together. Prefer click/select UI; typing is the fallback.
7. Record every answer in **Open Questions** only; update **Intent** boundaries/scenarios. Do not treat Evidence Table or **State Source** as the product-decision register.
8. After answers, skip any conditional questions that no longer apply. If answers spawn new blocking decisions, open the next wave. Stop when remaining answers would no longer materially change scope, acceptance, risk, or irreversible behavior; record the rest in **Open Questions** as non-blocking with the assumed default.

Then write/update the delta spec and run the Specification Gate.

### Batch clarification rule

**Shared protocol (required):** before any fixed-choice ask, follow `references/batch-clarification.md`. Form factor: **click first, typing fallback**. Do not bind to a specific IDE, coding agent, or tool name. Do not switch modes solely to obtain a choice UI.

Family mode: **批量澄清 (Batch clarification).** There is no「全部按推荐」/ bulk-accept shortcut. Every listed blocking item needs an explicit user choice (or an explicit skip when marked inapplicable). **Every fixed-choice question must include a recommendation** (prompt line「推荐：…」+ recommended option prefixed with「建议：」+ one-sentence rationale). Recommendation ≠ decision — never auto-apply it.

**Delivery order:**

1. Show the full **Open Questions** list (this wave’s independent blockers + omitted non-blocking / not-yet-triggered topics).
2. Ask **all currently independent** blocking questions in one message (click UI for the wave when available; otherwise Markdown). Multi-answer replies such as `1B 2A` are allowed on the typing fallback.
3. Record answers, drop dependents whose trigger was not met, then open the next wave if needed. Dependent questions stay out of a wave until their premise is decided.

Two failure modes remain forbidden:

- **Padding** — asking questions whose answers do not materially change scope, acceptance, risk, or irreversible behavior;
- **Bulk-accept / skip-the-user** — offering「全部按推荐」、silent application of defaults, or otherwise skipping per-question user choice on blocking items.

Showing the full **Open Questions** list before the first clarification wave is required. Product clarification is batched by wave; implementation gates are asked separately (see `delivery-plan-tasks` / `delivery-execute-verify`).

### Clarification ordering and stop

- **Ordering — dependency root first:** put questions whose answers decide whether others still matter at the earliest wave; after each wave, drop dependents whose trigger was not met. Within a wave (no remaining dependency), order by impact on scope or acceptance.
- **No hard question-count budget:** ask every materially blocking item; do not pad; non-material topics stay out of the quiz and may be recorded as assumed defaults.
- **Stop condition:** stop as soon as remaining answers would not materially change scope, acceptance, risk, or irreversible behavior. Never stop early by bulk-accepting defaults for still-blocking items.

### Question structure

Do not ask the user for information that can be established from code, tests, logs, configuration, or approved artifacts. Ask only when a product choice materially changes scope, acceptance, risk, or irreversible behavior.

Each question uses this structure (Chinese example: `references/clarification-example.md`):

1. **Why this is being asked** — one concise sentence tied to verified code facts.
2. **Options** — normally 2–4 concrete choices; each label carries the material scope, risk, migration, privacy, or UX consequence in short form. If the question is genuinely open-ended and options cannot be honestly enumerated, do not fabricate choices — ask in prose for freeform input. Include at most one escape option such as「其他（我来说明）」when fixed choices might not cover the user.
3. **Recommendation (required on fixed-choice)** — state the recommended option and one evidence-based reason in the prompt (`推荐：B — …`); prefix that option’s label with「建议：». Distinguish recommendation from decision; the user must still choose.
4. **The ask** — present the whole independent wave together (click first, typing fallback). Never offer「全部按推荐」as an option.

Use sensible defaults without asking only when the choice is low-risk, reversible, inside approved scope, and does not alter observable product behavior. Record the assumption in the brief. Never use a default to bypass a Medium/High gate or a product decision listed as blocking in **Open Questions**.

## Evidence Discipline

Label every important statement as:

- **Fact** — directly supported by code, test, log, config, or approved document.
- **Inference** — plausible interpretation that still needs confirmation.
- **Decision** — explicit user or approved-artifact choice.

Bind facts in the **Evidence Table** (or inline under **Code Facts**) to paths/symbols/tests/tool queries. Mark unknowns; never convert uncertainty into a confident requirement. Record product **Decision** outcomes in **Open Questions**; **State Source** holds gate approval only.

## Artifacts

Read the templates only when needed:

- `references/brief-template.md` — Intent + Code Facts + Alignment & Gates
- `references/spec-template.md`
- `references/routing-and-gates.md`
- `references/batch-clarification.md` — family batch clarification (click first, typing fallback; platform-agnostic)
- `references/clarification-example.md`
- `references/handoff-template.md`

## Specification Gate

Before handing off to `delivery-plan-tasks`, verify (Agent checklist — not a user multi-quiz):

- goal, non-goals, and success criteria are explicit (**Intent**);
- Standard/High brief has **Code Facts** (with Evidence Table) and **Alignment & Gates**, and passed facts readiness;
- critical facts have evidence;
- inferences are labeled;
- code-incapable product decisions are confirmed in **Open Questions** (blocking items decided or explicitly deferred as non-blocking);
- no implementation-blocking TBD remains;
- requirements have falsifiable scenarios and failure behavior;
- applicable non-functional constraints (performance, security/privacy, observability, compatibility) are captured with acceptance criteria in the spec, or explicitly marked out of scope — not deferred silently to planning;
- route and risk match evidence (**Risk Rating** writing complete);
- Medium/High scope approval is persisted in **State Source**.
- **Explore Handoff Consume** is present in `proposal.md`: five boxes checked when an explore handoff existed, or `N/A — 无 explore handoff`.

If any check fails, remain in this skill.

When the checklist passes, ask the user **one** scope-approval question (see `references/batch-clarification.md` **Gate ask shape**): approve scope → enter `delivery-plan-tasks`; do not ask them to re-confirm every Open Question or every spec scenario. Persist their answer in **State Source**. The Explore-handoff checkbox block in `proposal.md` must already satisfy the consume self-check.

## Handoff

Return a compact handoff with the **required subset** (Chinese labels: `references/handoff-template.md`): `stage`, `state_source`, `capability_snapshot`, `gate_status`, `evidence_mode`, `next_skill`, `required_inputs`, `stop_condition`.

```text
stage: delivery-frame-spec
route/risk:
state_source:
confirmed_artifacts:
evidence_mode:
capability_snapshot:
gate_status:
next_skill:
required_inputs:
stop_condition:
```

Automatic skill loading is optional. If unsupported, stop after this handoff and tell the user exactly「请使用 <next_skill>」(e.g.「请使用 delivery-plan-tasks」).

## Red Flags

- Creating a new state source before checking for one.
- Calling routing a user-visible extra phase.
- Reading the whole repository before choosing a route.
- Asking dependent questions in the same wave as their premise, forcing one-question-per-message dribbling for independent blockers, binding clarification to a named IDE/agent/tool, switching mode only to obtain a choice UI, omitting the required recommendation (「推荐：」+「建议：」option) on a fixed-choice question, offering「全部按推荐」/ bulk-accept that skips per-question user choice, or turning High’s internal five-facet checklist into a user-facing multi-quiz.
- Padding clarification with non-material questions.
- Skipping Open Questions visibility on Standard/High before clarification.
- Waiting for an explicit “confirm brief” when the facts readiness gate already passed.
- Writing implementation code during Standard/High framing.
- Handing off to implementation on any route without an explicit, recorded user go.
- Choosing Quick because documentation feels expensive.
- Choosing Quick for auth/payment/privacy/migration/public-API/destructive/core-path work, or any listed negative case in `routing-and-gates.md`.
- Receiving a `delivery-explore` handoff but skipping Explore-handoff consume self-check — including missing/empty **Explore Handoff Consume** in `proposal.md`, unchecked boxes, or chat-only explore summary with no checkbox block.
- Creating or extending any Markdown state/spec/tasks beside an OpenSpec change.
- Creating a parallel `brief.md` or `code-fact-brief.md` beside the change's `proposal.md`.
- Recording product decisions outside Open Questions, or treating Evidence Table / State Source as the decision register.
- Copying clarification-message SOP into the brief artifact body.
- Referring to brief parts by section numbers instead of the named parts above.
- Treating Codebase Memory output as a product decision.
- Letting an auxiliary skill redefine scope.

Any red flag means stop, correct the artifact/state, and re-run the relevant gate.

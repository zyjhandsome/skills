---
name: delivery-explore
description: >-
  Use when product direction is open, the user wants feature/idea suggestions,
  opportunity/tradeoff maps, or codebase-grounded exploration before committing
  to a change — e.g. “还想加啥/给建议/机会地图/what's missing”, “探索产品方向”,
  “做机会或权衡地图”, or “基于代码看看还能做什么”. Evidence-first via Codebase
  Memory MCP; does not implement or approve requirements. Hands off only to
  delivery-frame-spec — never to plan or execute.
---

# Delivery Explore

## Iron Rules

1. No implementation code; no formal OpenSpec delivery state; the map is never an approved spec.
2. Memory-first evidence; if Memory is down/stale, degrade and say so (`evidence_mode: degraded`).
3. Next skill only: `delivery-frame-spec` (or end). Never hand off to plan or execute.
4. Stage end: emit one complete `delivery-handoff/v1` object (see `references/handoff-template.md`), including terminal/end states. If skill chaining is unsupported, tell the user to say「请使用 delivery-frame-spec」when a transition is allowed.
5. Do **not** add a fifth user-visible router skill; do **not** paste long system essays into this `SKILL.md`.

## Overview

Pre-delivery exploration: map what the codebase already does, surface grounded opportunity directions, and help the user pick a candidate before formal framing.

**Hard gates:**

- Do not write implementation code.
- Do not create or mutate formal delivery state (no OpenSpec change as state source, no approved brief/spec/tasks).
- Do not treat exploration output as an approved requirement.
- Do not hand off to `delivery-plan-tasks` or `delivery-execute-verify`. The only next skill is `delivery-frame-spec` (or end).

Position in the family:

```text
delivery-explore → delivery-frame-spec → delivery-plan-tasks → delivery-execute-verify
```

When chaining is unsupported or the user asks which stage to load, use the stage map above and the handoff `next_skill` field.

## Language and artifacts

- This `SKILL.md` is English.
- **All human-facing output defaults to Chinese** — exploration maps, direction lists, recommendations, and handoff values — using the Chinese templates under `references/` (`explore-output-template.md`, `handoff-template.md`). Only paths, symbols, commands, and machine-readable keys/enums (`evidence_mode`, `risk_signal` values, handoff keys) stay English.
- If the user works in another language, follow the user's language instead; machine keys still stay English.

## When To Use

Use this skill when:

- the user asks for suggestions (“还想加啥功能？”, “你有什么建议?”);
- the goal is open-ended ideation, opportunity mapping, or “what’s missing?”;
- a problem is real but the product choice among several directions is not yet locked;
- the user wants a thinking partner before entering the specification gate.

Do **not** use this skill when:

- the user already named a concrete change to frame → `delivery-frame-spec`;
- an approved spec needs a plan → `delivery-plan-tasks`;
- approved tasks need implementation/verification → `delivery-execute-verify`;
- the request is pure Q&A about existing behavior with no ideation → Read-only via `delivery-frame-spec` or a direct answer.

## Capability Adapters

Use capabilities by role; never make them competing workflow owners. Treat the four `delivery-*` skills and shared references as one atomic Family (`../delivery-frame-spec/references/family-contract.md`). OpenSpec is mandatory for mutating routes; Memory and Superpowers are preferred but degradable; SubAgent/worktree and structured UI are optional accelerators. Never invent a substitute Markdown artifact backend.

Naming convention: refer to external capabilities as repo + semantic capability — e.g. Superpowers `brainstorming`, OpenSpec `inspect_change`, Codebase Memory MCP `get_architecture`. Record actual aliases in `capability_bindings`; bare skill names elsewhere are reserved for the `delivery-*` family.

### Prerequisite preflight

When this skill starts the family (usual case), probe the three external capabilities once and record `family_version`, a `capability_snapshot`, and only the `capability_bindings` actually resolved (formats defined in `delivery-frame-spec` and `../delivery-frame-spec/references/family-contract.md`):

```text
capability_snapshot:
  memory: ok | stale-index | down
  openspec: initialized | cli-only | unavailable
  superpowers: loaded | partial(<missing>) | missing
```

Non-nominal `memory`/`superpowers` values and `openspec: unavailable` are exceptions to report (installation is assumed); `openspec: cli-only` is a normal repo state. Pass the snapshot forward in the handoff so `delivery-frame-spec` does not re-probe nominal capabilities.

**Preflight failure — fixed 3-line report (Chinese):**

```text
缺什么：<memory|openspec|superpowers 的具体异常枚举>
能否降级：<可 degraded 继续探索 / 必须恢复后才能取证>
下一步请你：<例如：修复 Memory 索引 / 允许仅用定点源码继续>
```

### Codebase Memory MCP — primary evidence provider

Prefer Memory **before** free-form ideation. Discover tool schemas first (`GetMcpTools` / server catalog). Typical sequence:

1. Confirm project/index readiness (`index_repository` only if clearly stale or missing and the user/context allows).
2. `get_architecture` (overview / clusters / boundaries / hotspots as needed).
3. `search_graph` / `query_graph` / `search_code` for themes the user cares about.
4. `trace_path` / `get_code_snippet` for high-value candidates before recommending them.

This is **code memory**, not a product decision engine and not an artifact store. Bind claims to paths/symbols/clusters. If the snapshot marks `memory: stale-index | down`, use targeted source/docs/tests/git, mark `evidence_mode: degraded`, and report the outage. Never replace a graph query with an unbounded whole-repository dump.

**Index freshness probe (required):** known-on-disk path/symbol missed by Memory search → set `memory: stale-index`, `evidence_mode: degraded`, report the fixed 3-line form. Do not treat a graph miss as proof the code is absent.

### OpenSpec — read-only context only

If the repo uses OpenSpec, resolve only the required read/status capability through `../delivery-frame-spec/references/openspec-adapter.md`, then **read** active changes and main specs to avoid duplicate or conflicting suggestions. Do not create a change, do not rewrite proposal/design/tasks as the explore outcome, and do not become a second state source.

Optional: if the user explicitly asks to keep notes, offer a disposable exploration note path they choose; default is **inline only**. Capturing a formal change belongs to `delivery-frame-spec` after they pick a direction.

### OpenSpec `explore` / Superpowers `brainstorming` — method reuse, not owners

Reuse useful stance from a resolved OpenSpec exploration/read capability and disciplines from the resolved Superpowers `brainstorming` method (2–3 options, tradeoffs, recommendation). Do **not** invoke them as parallel workflow owners or write their native design artifacts from this skill. This skill owns the delivery-family exploration stage.

## Start Here

1. Identify project root and the exploration prompt; when starting the family, run the prerequisite preflight and record the `capability_snapshot`.
2. Recover context: relevant OpenSpec changes (read-only), recent commits, README/product docs — only enough to orient.
3. Run Memory-first evidence gathering (or degraded fallback).
4. Separate **Fact / Inference / Decision** on every material claim.
5. Produce an exploration map (see Output Contract).
6. Help the user select or refine **one** candidate direction.
7. Run the **Direction Alignment Exit Check** below.
8. Emit the explore `delivery-handoff/v1` (validate with `validate_handoff.py`). Only after this handoff may framing create an OpenSpec change.
9. Hand off to `delivery-frame-spec`, or end if they only wanted advice.

### Checkpoint — no formal change yet

**Before the explore handoff is emitted and validated, it is forbidden to:**

- call OpenSpec `create_change` / `openspec new change` / equivalent;
- write `openspec/changes/<id>/` proposal, design, specs, or tasks as delivery state;
- invent a parallel Markdown state file for the exploration outcome.

Read-only OpenSpec `list` / `show` / main specs is allowed. Creating the change belongs exclusively to `delivery-frame-spec` after direction selection.

## Stance

- Evidence before opinions.
- Multiple interesting directions are allowed; do not funnel into a single interrogative path too early.
- Prefer diagrams/tables when they clarify architecture or tradeoffs.
- When product choices become blocking for *which* direction to pursue, use **batch clarification** aligned with `delivery-frame-spec` (`../delivery-frame-spec/references/batch-clarification.md`; click first, typing fallback; no named IDE/agent/tool). When a host question tool is available, map the wave through `../delivery-frame-spec/references/question-ui-adapters.md`:
  1. Show the candidate directions (map). Each fixed-choice question must include a recommendation (`推荐：…` + recommended option prefixed with「建议：」+ one-sentence rationale). Recommendation ≠ decision.
  2. Direction selection is usually a **single** question after the map. If multiple **independent** forks remain, list those forks together in one wave. For a single question, an unambiguous「按推荐方向」counts as selecting that direction; a multi-fork wave still requires per-item choices.
  3. Prefer click/select UI when available; otherwise Markdown typing fallback (multi-answer codes allowed for a multi-fork wave). Do not switch modes solely to obtain a choice UI.
- Gate asks (specification / implementation) are owned by `delivery-frame-spec` / `delivery-plan-tasks` and use the **single go** shape in `batch-clarification.md`; explore only uses batch clarification for **direction** forks, not High five-facet quizzes.

## Direction Alignment Exit Check

Before handing a selected direction to `delivery-frame-spec`, verify:

- `chosen_direction` states one candidate in the user's terms and names the problem/value it targets;
- every unresolved fork that could change the chosen direction is decided; independent forks followed batch clarification;
- `non_goals` captures known boundaries, or explicitly says which boundaries remain for framing;
- evidence-findable gaps were investigated; remaining uncertainty is listed under `unknowns` without inventing decisions;
- `direction_alignment` is `selected`. If a direction-changing fork remains, use `needs_choice`, remain in explore, and open the next clarification wave; if the user only wanted advice, end without framing.

This is candidate-direction alignment, not specification approval. Do not ask frame-owned scope, acceptance, or irreversible product questions merely to make explore look complete; pass them as `unknowns`.

## Output Contract

Default: keep the map **inline** in the conversation. Structure:

```text
## 探索结论（非正式）
证据模式：full | degraded
方向对齐状态：selected | needs_choice
代码锚点：<paths / symbols / clusters>

### 方向清单
1. <名称> — <一句话价值>
   证据：...
   大致影响面：...
   风险信号：none | standard-likely | high-likely
2. ...

### 非目标（本次探索不建议碰）
- ...

### 未知项
- ...

### 推荐
首选：<N> — <为何，基于哪些事实>
备选：<N> — <何时改选>
```

Rules:

- Directions without a code or product-doc anchor are labeled **Inference** and ranked below evidence-backed ones.
- Do not invent persistence/privacy/public-API work as “easy wins.”
- Risk signals are hints for the later frame route; they are not a self-approved risk level. Mapping into `delivery-frame-spec` vocabulary: `none` → likely Quick/Standard, `standard-likely` → likely Standard (default risk Medium), `high-likely` → likely High. The frame stage re-derives route/risk from evidence; explore never fixes them.
- Never claim “规格已批准” or “可以开始实现.”

## Boundary vs `delivery-frame-spec`

| | delivery-explore | delivery-frame-spec |
|---|---|---|
| Intent | What *might* we do? | What are we doing *this* change? |
| Artifacts | Informal map (inline) | Brief/spec + gates + state source |
| Memory | Broad map then zoom | Minimal facts to route and specify |
| Questions | Multi-thread OK until pick; fixed-choice pick via batch clarification (usually one direction question; independent forks may share a wave; each question needs recommendation; no bulk-accept; see frame-spec `batch-clarification.md`) | Batch clarification by dependency wave (independent blockers listed together; each question needs「推荐：」+「建议：」; no「全部按推荐」) |
| Code mutation | Forbidden | Forbidden until Quick/Debug-Low or later stages |
| Next skill | `delivery-frame-spec` only | plan / execute / end |

If during explore the user suddenly locks a concrete change (“就做这个”), stop expanding the map and hand off to `delivery-frame-spec` immediately with the chosen direction and evidence anchors.

If during `delivery-frame-spec` the direction is still genuinely open, that skill should send the user back here rather than inventing a fake locked goal.

## Handoff

Before handing off, read `../delivery-frame-spec/references/handoff-contract.md` and emit one complete, strictly parseable `delivery-handoff/v1` JSON object using `references/handoff-template.md`. Put direction-specific fields in `stage_payload`; keep the common contract canonical. When local Python is available, validate the final object with `../delivery-frame-spec/scripts/validate_handoff.py` before output.

Presentation projection is view-only: when the host supports structured delivery rendering, show `pipeline` with explore active, then show `handoff` only after `direction_alignment: selected`. Otherwise render the same fields as Markdown. Never let a presentation view create state or imply approval.

Record `presentation_capability` once using the shared contract. When its mode is `delivery-ui/v1` or `legacy-v0`, read `../delivery-frame-spec/references/structured-presentation-adapter.md`; when unknown, use Markdown. Keep `capability_snapshot` canonical and apply compatibility mapping only at the presentation boundary.

If automatic skill loading is unsupported, stop after this handoff and tell the user exactly:「请使用 delivery-frame-spec」.

Set `next_skill: delivery-frame-spec` only when `direction_alignment: selected`. `needs_choice` is not a frame handoff state: continue explore clarification, or end if the user declines to select a direction.

## Red Flags

- Creating OpenSpec/Markdown delivery state from explore — including calling `create_change` before the explore handoff is emitted/validated.
- Filling both `next_skill` and `next_action` with non-null values in the explore handoff.
- Handing off to plan or execute.
- Treating Memory clusters/hotspots as product priorities without user intent.
- Writing implementation, scaffolds, or “quick spikes” that mutate the repo.
- Running unbounded repo-wide dumps instead of targeted Memory/source queries.
- Letting OpenSpec `explore` or Superpowers `brainstorming` redefine scope or own artifacts.
- Presenting the exploration map as an approved spec.
- Marking `direction_alignment: selected` while a direction-changing fork remains unresolved.

Any red flag: stop, correct course, and remain in explore or hand off cleanly to `delivery-frame-spec` without carrying false approval.

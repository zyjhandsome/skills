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

Shared family protocol: `../delivery-frame-spec/references/family-contract.md`. Handoff schema and template: `../delivery-frame-spec/references/handoff-contract.md` + `../delivery-frame-spec/references/handoff-template.md` (Explore block). Question protocol: `../delivery-frame-spec/references/batch-clarification.md`.

## Iron Rules

1. No implementation code; no formal OpenSpec delivery state; the map is never an approved spec.
2. Memory-first evidence; bind claims to paths/symbols/clusters.
3. Next skill only: `delivery-frame-spec` (or end). Never hand off to plan or execute.
4. Stage end: emit one complete `delivery-handoff/v1` object (including end states), validate it. When a transition is allowed, follow the chain relay rule (`family-contract.md` §1): if the host can load skill files directly (e.g. Claude Code), read `delivery-frame-spec/SKILL.md` and continue in the same session; only when the host cannot, tell the user「请使用 delivery-frame-spec」.
5. Hard prerequisites (OpenSpec/Memory/Superpowers/SubAgent) are assumed available; on a real runtime failure stop and report per `family-contract.md` — no degraded exploration mode.

## Overview

Pre-delivery exploration: map what the codebase already does, surface grounded opportunity directions, and help the user pick a candidate before formal framing.

```text
delivery-explore → delivery-frame-spec → delivery-plan-tasks → delivery-execute-verify
```

Use this skill for open-ended ideation, opportunity mapping, “还想加啥功能？”, or when the product choice among directions is not yet locked. Do **not** use it when the user already named a concrete change (→ `delivery-frame-spec`), an approved spec needs a plan (→ `delivery-plan-tasks`), approved tasks need implementation (→ `delivery-execute-verify`), or the request is pure Q&A (Read-only via frame or a direct answer).

## Capability roles

- **Codebase Memory MCP — primary evidence provider.** Discover tool schemas first. Typical sequence: confirm index readiness → `get_architecture` (overview/clusters/boundaries/hotspots) → `search_graph` / `query_graph` / `search_code` for user themes → `trace_path` / `get_code_snippet` for high-value candidates before recommending them. Index freshness rule: `family-contract.md` §5. Never replace a graph query with an unbounded whole-repository dump.
- **OpenSpec — read-only context only.** Read active changes and main specs (via the adapter's `inspect_change`) to avoid duplicate or conflicting suggestions. **Before the explore handoff is emitted and validated, it is forbidden to** call `create_change`, write `openspec/changes/<id>/` artifacts as delivery state, or invent a parallel Markdown state file. Creating the change belongs exclusively to `delivery-frame-spec` after direction selection.
- **Superpowers `brainstorming` — method reuse, not owner.** Reuse its disciplines (2–3 options, tradeoffs, recommendation) without letting it own artifacts or state.

## Start Here

1. Identify project root and the exploration prompt.
2. Recover context: relevant OpenSpec changes (read-only), recent commits, README/product docs — only enough to orient.
3. Run Memory-first evidence gathering.
4. Separate **Fact / Inference / Decision** on every material claim.
5. Produce an exploration map (Output Contract below).
6. Help the user select or refine **one** candidate direction.
7. Run the **Direction Alignment Exit Check**.
8. Emit + validate the explore handoff. Only after this handoff may framing create an OpenSpec change.
9. Hand off to `delivery-frame-spec`, or end if they only wanted advice.

## Stance

- Evidence before opinions. Multiple interesting directions are allowed; do not funnel into a single interrogative path too early. Prefer diagrams/tables when they clarify architecture or tradeoffs.
- When product choices become blocking for *which* direction to pursue, use batch clarification per the shared protocol. Direction selection is usually a **single** question after the map; if multiple **independent** forks remain, list them together in one wave. For a single question, an unambiguous「按推荐方向」counts as selecting that direction; a multi-fork wave still requires per-item choices.
- Gate asks (specification/implementation) are owned by frame/plan; explore only clarifies **direction** forks.

## Direction Alignment Exit Check

Before handing a selected direction to `delivery-frame-spec`, verify:

- `chosen_direction` states one candidate in the user's terms and names the problem/value it targets;
- every unresolved fork that could change the chosen direction is decided (independent forks via batch clarification);
- `non_goals` captures known boundaries, or says which boundaries remain for framing;
- evidence-findable gaps were investigated; remaining uncertainty is listed under `unknowns` without inventing decisions;
- `direction_alignment` is `selected`. If a direction-changing fork remains → `needs_choice`, stay in explore and open the next wave; if the user only wanted advice → end without framing.

This is candidate-direction alignment, not specification approval. Do not ask frame-owned scope/acceptance/irreversible questions merely to look complete; pass them as `unknowns`.

## Output Contract

Default: keep the map **inline** in the conversation (structure: `references/explore-output-template.md`, Chinese). Key sections: 探索结论 / 方向清单（证据 + 影响面 + 风险信号）/ 非目标 / 未知项 / 推荐（首选 + 备选）.

Rules:

- Directions without a code or product-doc anchor are labeled **Inference** and ranked below evidence-backed ones.
- Do not invent persistence/privacy/public-API work as “easy wins.”
- Risk signals are hints for the frame route (`none` → likely Quick/Standard, `standard-likely` → Standard/Medium, `high-likely` → High); the frame stage re-derives route/risk from evidence. Never claim “规格已批准” or “可以开始实现.”
- If the user explicitly asks to keep notes, offer a disposable note path they choose; default is inline only.

## Boundary vs `delivery-frame-spec`

Explore asks “what *might* we do?” with an informal inline map; frame asks “what are we doing *this* change?” with brief/spec + gates + state source. If the user suddenly locks a concrete change (“就做这个”), stop expanding the map and hand off immediately with the chosen direction and evidence anchors. If framing finds the direction still genuinely open, frame sends the user back here.

## Handoff

Follow the shared contract and template (Explore block). `next_skill: delivery-frame-spec` only when `direction_alignment: selected`; `needs_choice` is not a handoff state. Explore handoffs are not persisted to disk (no change exists yet).

## Red Flags

- Creating OpenSpec/Markdown delivery state from explore — including `create_change` before the handoff is emitted/validated.
- Handing off to plan or execute; marking `selected` while a direction-changing fork remains.
- Treating Memory clusters/hotspots as product priorities without user intent.
- Writing implementation, scaffolds, or “quick spikes” that mutate the repo.
- Running unbounded repo-wide dumps instead of targeted queries.
- Presenting the exploration map as an approved spec.

Any red flag: stop, correct course, and remain in explore or hand off cleanly without carrying false approval.

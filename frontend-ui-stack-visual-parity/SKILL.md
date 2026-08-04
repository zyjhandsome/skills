---
name: frontend-ui-stack-visual-parity
description: >
  Diagnose and fix visual/style regressions after a frontend UI-stack upgrade
  (e.g. Vue3 + Element Plus + Tailwind, el-table/vxe-table mix) when behavior
  mostly works but search bars, forms, and tables look wrong. Use when the user
  mentions post-upgrade style issues, Tailwind Preflight vs Element Plus,
  tw- prefix coexistence, table/form theme drift, or visual parity after
  Element UI→Plus / Vue2→Vue3 cutover. Phase A is evidence-only delimitation;
  Phase B may edit CSS/config only after an explicit user go. Does not re-run
  Vue2→Vue3 path selection or install/upgrade dependencies. Produces an
  independent report, capture manifest, and compact summary; strict parity
  requires a traceable baseline and deterministic capture context.
---

# Frontend UI Stack Visual Parity

Post-cutover **visual** diagnosis and CSS/config remediation. This Skill owns
only its output bundle and explicit Phase B gate. It does not import, require,
or write state for any migration-analysis or software-lifecycle Skill.

## Boundaries

| Allowed | Forbidden until explicit go | Always forbidden |
|---|---|---|
| Read manifests, CSS/Tailwind/Vite config, SFCs, global style entry order | Edit CSS, Tailwind config, theme variables, style imports | `npm/pnpm/yarn/bun install` or dependency upgrades |
| Inventory UI CSS stack; propose Preflight / order / shell fixes | Broad redesign / design-system restyle | Re-opening Vue2→Vue3 migration path choice |
| Write report under resolved output dir (after path confirm) | Refactors unrelated to visual parity | Treating functional smoke as visual complete |
| Phase B: minimal CSS/config edits in approved scope | Editing business JS/API/router logic for “style” | Blanket “继续/全部放行” as go |

**Default posture:** preserve observable behavior and layout intent; change
presentation/config only.

**Standalone go tokens (Phase B):** require an explicit phrase such as `开始修复` /
`go:visual-fix` / `批准按方案改 CSS` bound to the **current** packet revision.
Natural language「继续 / 看起来没问题 / 全部放行」alone is **not** go.

## Execution scopes

| Scope | Output | Mutation rule |
|---|---|---|
| `analysis_only` (default) | independent output bundle | no source/config edits |
| `analysis_and_remediation` | same bundle, updated after verification | requires this Skill's revision-bound Phase B go |

Every report emits `schema: visual-parity-report/v1`, `producer`,
`execution_scope`, and `source_snapshot`. These fields describe this output
only; they do not grant authority in another workflow.

## Minimal caller input

Project/workspace root (or accept cwd) + optional 1–2 worst page routes/files.
If pages omitted, discover a typical **search + primary table** list page.

## Output directory

Resolve in order:

1. Explicit `--output-dir`
2. Else candidate: `<project-root>/.ui-stack-visual-parity`

For (2), restate the absolute path and get
`confirm:output-dir` or `--output-dir <path>` before writing. Until confirmed:
read-only; no report files.

Write the independent output bundle:

- `ui-stack-visual-parity-report.md`: full diagnosis and verification record.
- `visual-summary.json`: compact consumer view; keep ≤8 KiB and reference paths
  instead of copying report prose or image bytes.
- `capture-manifest.json`: capture environment, routes/states, image/diff paths;
  never embed screenshots/base64 in Markdown or JSON.

Templates: `templates/visual-parity-packet.md`, `templates/visual-summary.json`,
and `templates/capture-manifest.json`. Prose: Simplified Chinese; keep package names,
paths, class prefixes, commands, enums, URLs verbatim.

Before claiming completion, run
`python scripts/validate_visual_report.py <report.md>`. A passing validator
proves report shape only; it does not manufacture a baseline or visual evidence.
Also run `python scripts/validate_visual_summary.py <visual-summary.json>`.

## Status axes

| Axis | Values |
|---|---|
| `analysis_status` | `partial` / `blocked` / `complete` |
| `strategy_status` | `needs_choice` / `decided` / `not_needed` |
| `remediation_status` | `not_started` / `awaiting_go` / `in_progress` / `done` / `skipped` |
| `behavior_parity_required` | usually `yes` |
| `report_path` | concrete dir (not bare `.`) |
| `evidence_as_of` | `YYYY-MM-DD` |
| `assessment_mode` | `strict_parity` / `consistency_review` |
| `final_visual_result` | `pending` / `pass` / `fail` |

Never set `analysis_status=complete` while `strategy_status=needs_choice`.
Never start Phase B while `remediation_status` is not `awaiting_go` **and** a
revision-bound go is recorded in the report State Source section.

`assessment_mode=strict_parity` requires a traceable pre-upgrade/reference
baseline. Without one, use `consistency_review`, name the approved substitute
standard, and never claim pixel parity.

## Workflow

### Phase A — Delimit (default; no CSS edits)

1. Resolve frontend workspace and execution scope; state assumptions and output path.
2. Inventory CSS/UI stack per `references/config-inventory.md` (Tailwind
   preflight/prefix/important; Element/other UI theme + `--*-*` vars; global
   import order; primary table stack el-table vs vxe vs mix; icons; heavy
   third-party CSS: editor/tree/DAG/etc.).
3. Resolve baseline + deterministic capture context per
   `references/visual-capture-contract.md`; choose strict parity vs consistency review.
4. Pick **primary sample**: search region + **primary** table page (default
   prefer `el-table` when mixed). Pick **secondary** sample only if vxe (or
   other) is in scope for regression — secondary must not drive global strategy.
5. Run diagnosis steps in `references/diagnosis-workflow.md` after choosing the
   `with-tailwind` vs `no-tailwind` branch from config inventory. With Tailwind:
   Preflight contrast (describe or apply only if user already authorized a
   temporary local experiment; prefer documenting the experiment plan when
   edits are still forbidden) → search-only → empty table → in-cell controls.
   Without Tailwind: skip Preflight experiments; rank kit major / global reset /
   theme / Teleport / project overrides first, then layer peel.
6. Label Fact / Inference / Decision. Rank causes (Preflight×UI kit, shell
   layout, table chrome, in-cell controls, import order, third-party CSS).
7. Present one primary cause and the minimum evidence-backed remediation set
   (`references/strategy-options.md`). Ask for strategy choice if blocking.
8. Fill verification checklist (`references/verification-checklist.md`) into
   the report. Set `strategy_status=decided` only after the strategy is decided.
   Set `remediation_status=awaiting_go` and stop for a revision-bound Phase B go.

### Phase B — Remediate (only after explicit go)

1. Re-read the approved strategy + forbidden scope from the report.
2. Apply **minimal** CSS/config changes only (Tailwind config, global style
   order, scoped shell/table overrides, theme variable tweaks in approved
   files). No dependency version changes.
3. Re-run the deterministic capture contract and verification checklist on
   primary (and secondary if listed).
4. Update report: files touched, before/after notes, residual risks,
   `remediation_status=done` (or list blockers).
5. Refresh and validate report, capture manifest, and compact summary. Never
   self-authorize a scope change.

## Default sample priority (when mixed tables)

1. Search + `el-table` + in-cell Element controls  
2. One `vxe-table` page as secondary regression only  

## Context budget and portability

Default handoff to any caller is the path to `visual-summary.json`, not the full
report. Load the full report only for a named finding/route, and load an image
only for a named state. The output bundle must remain usable when every other
Skill folder is absent.

## Red flags

- Editing CSS before revision-bound go
- Claiming strict parity without a traceable baseline
- Using a vxe-only page to set global Tailwind/Element strategy
- Calling functional E2E pass “visual parity complete”
- Expanding into Composition rewrite or UI kit replacement without a new ask
- Copying screenshots or the full report into conversational context when paths suffice

## References

- Always: `references/config-inventory.md`, `references/diagnosis-workflow.md`,
  `references/verification-checklist.md`, `references/visual-capture-contract.md`
- On demand: `references/strategy-options.md`, `references/baseline-capture-runbook.md`,
  `templates/visual-parity-packet.md`

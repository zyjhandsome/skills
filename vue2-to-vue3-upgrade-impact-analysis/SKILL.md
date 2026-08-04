---
name: vue2-to-vue3-upgrade-impact-analysis
description: >
  Analyze, never implement, a Vue 2.x to Vue 3.x framework upgrade for one
  frontend workspace or a multi-repo inventory. Use when assessing Vue2→Vue3
  migration impact, @vue/compat vs direct Vue3 cutover, Vue CLI/Webpack→Vite,
  Vue Router 4, Vuex/Pinia, Element UI→Element Plus (or other UI), test-utils,
  or blocking Vue plugins. Writes a Simplified Chinese decision packet with
  confirmation queue and batch_implementation_gate. Ends at analysis_status
  complete — never at implementation or codemod execution. Produces an
  independent full report, decision records, inventory evidence, and a compact
  JSON summary with structured UI visual-risk evidence.
---

# Vue 2 → Vue 3 Upgrade Impact Analysis

Produce an evidence-backed decision packet — analysis only. Do not change
manifests, run install/upgrade, apply migration codemods, or edit application
code.

## Minimal caller input

A **short prompt** is enough: invoke the skill, give the project root (or accept
the stated cwd), and either analyze one frontend workspace or ask for
「多仓巡检」. Resolve the report directory under Output unless overridden.

## Environment preflight

Before analysis (including manifest-only reads), run
`references/environment-preflight.md` / `scripts/preflight.py`. Missing Node
(or project pin probe), package manager detection, or Python → batch-wide
`analysis_status=blocked`; list gaps in chat; **do not write** reports. Host
Node vs `engines` mismatch is recorded, not a hard block. Network probe runs in
the same wave; dual registry+docs failure follows the offline confirm gate.

## Boundaries

- **Allowed:** read `package.json` / lockfiles / config / source / tests; run
  read-only inventory (`scripts/profile_inventory.py`); fetch official migration
  docs; write reports under the resolved Output directory.
- **Forbidden:** `npm/pnpm/yarn/bun install` or upgrade; edit source or config;
  run migration codemods; treat build/start success as release proof.
- **Name, never run, migration recipes** for `@vue/compat`, gogocode,
  `vue-upgrade-tool`, `webpack-to-vite`, etc. See
  `references/named-migration-recipes.md`.
- **Default posture:** preserve observable behavior unless the user explicitly
  allows behavior change.
- **Composition API:** full Options→Composition rewrite is **out of scope**
  (mark「另立项」). Only assess **existing** `@vue/composition-api` / `setup`
  compatibility.
- **Independence:** this skill does not import or require any other skill.

## Dual entry

| Entry | Input | First action |
|---|---|---|
| Single workspace | project/workspace root | Preflight → profile → full packet |
| Multi-repo inventory | roots list or parent dir | Build candidate table; ask which batch to analyze |

Normalize candidates per `references/dual-entry-and-batching.md`. One analysis
batch = **one frontend workspace × one build variant × one bounded scope**.

## Default recommended path

Unless evidence rules it out, recommend path id `compat-big-bang` with axes
`runtime_axis: compat`, `build_axis: vite`, `topology_axis: single-cutover`
(see `references/migration-path-ladder.md`). Wave 1 still confirms one path id;
§3 must state all three axes. Human `proceed:path:…` / `other` required.

## Workflow

1. Run environment preflight; resolve project root and frontend workspace
   (ask if multiple). Exit `5` → stop (`blocked`). State assumptions.
2. Run light inventory (`scripts/profile_inventory.py` or equivalent read-only
   scan). Cover all default subsystems in
   `references/subsystem-inventory.md`. Record `lockfile_status` as `present`,
   `absent`, or `unparsed`; keep the handoff gate frozen unless it is `present`.
3. Classify each subsystem (`risk`, readiness, `required_for_path`). List
   Vue-related and candidate plugin packages (including non-`vue-*` names found
   through peer metadata, name heuristics, imports, or `Vue.use`) with Vue3 readiness
   (`ready` / `needs-major` / `replace` / `unknown` / `unused`).
4. Pick `recommended_path` + three axes; name recipes; never execute them.
5. Map impact (`references/impact-and-validation.md`): breaking API surfaces,
   UI/library jumps, router/store/build/test, smoke/E2E needs. Cite URLs from
   `references/official-docs-index.md` (fetch pages; do not invent breaks).
   Mark fact vs inference. Composition rewrite = out of scope note only.
   Complete §10 人工补搜检查 even when profile signals look complete. Register
   every `Vue.prototype.$*` definition/consumer and its `globalProperties` or
   `provide/inject` migration target.
   When UI/CSS triggers are present, also complete the structured
   `ui_visual_risk` block; a one-line “run visual regression” note is
   insufficient. Name affected surfaces, CSS anchors, baseline needs, required
   states, and a generic next action without requiring another Skill.
6. Draft packet + Decision Records (path + each High/blocker /
   `required_for_path=yes` subsystem).
7. Work confirmation queue (`references/human-confirmation-gates.md`):
   - Wave 1: migration **path** (`ready`) — ask now.
   - After path `decided`: Wave 2+ every High/blocker /
     `required_for_path=yes` **subsystem** currently `ready`, same wave.
   Never ask `blocked`. No blanket proceed. Record → regenerate → Agent review
   → `analysis_status=complete`.
8. Stop. Do not open implementation plans from this skill.

「继续 / 全部放行 / 别再问了 / 全部纳入」**≠** proceed token. Do **not**
infer `decided`. Re-prompt with verbatim `proceed:path:…` /
`proceed:subsystem:…` menus. Natural language never writes `人工答复`.

## Output

Resolve the report directory in this order:

1. Explicit `--output-dir` override.
2. Else default candidate:
   `<project-root>/.vue2-to-vue3-upgrade-analysis`

Use (2) after restating the absolute path and getting explicit
confirmation (`--output-dir <that-path>` or `confirm:output-dir`). Until
confirmed: read-only analysis only; **do not write**. Preflight failure →
stop. Oral「写到仓库」alone is not enough.

Write the independent output bundle:

- `vue2-to-vue3-upgrade-report.md`: full decision packet.
- `upgrade-summary.json`: compact consumer view, ≤12 KiB; paths and bounded
  arrays only, no copied report sections.
- `inventory.json`: raw profiler output when profiling ran.
- `decision-records/*.md`: only for path and High/blocker decisions.

Multi-batch layout:
`<entry-kind>/<workspace-slug>__variant-<build-variant>__scope-<batch-scope>/`
plus root `BATCH-INDEX.md` (`entry-kind` = `workspace` / `inventory`).
Prose defaults to Simplified Chinese; keep package names, versions, paths,
commands, enums, and URLs verbatim. Required sections:
`references/report-contract.md`.

## Validator

```shell
python -m unittest discover -s tests -v
python scripts/validate_report.py <report.md>
python scripts/validate_report.py --evidence-dir <evidence-dir> [--json]
python scripts/validate_upgrade_summary.py <upgrade-summary.json>
python scripts/preflight.py --project-root <dir> [--json]
python scripts/profile_inventory.py --project-root <dir> [--json]
```

Exit `0` pass / `3` errors / `4` path missing (validator). A pass means
well-formed, never that evidence is sufficient. Fixtures:
`fixtures/valid-report*.md`, `fixtures/decision-records/`, and
`fixtures/evidence-complete/` for `--evidence-dir`.

## Status axes

| Axis | Meaning |
|---|---|
| `analysis_status` | `partial` / `blocked` / `complete` |
| `decision_status` | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | `frozen` / `ready` (**handoff only**; never implements) |
| `implementation_readiness` | always `not_assessed` in this skill |
| also required | `behavior_parity_required`, `network_mode`, `report_path`, `evidence_as_of` |

Reports that inventory a UI-kit major, Tailwind/reset change, mixed table stack,
scoped-style/fallthrough risk, or heavy visual library also require
`visual_acceptance_required=yes` and the §5 `ui_visual_risk` block.

Never set `analysis_status=complete` while `decision_status=needs_choice` or any
queue `ready`/`pending`. Uncleared askable rows ⇒ **ask now**, not “继续/放行”.
`batch_implementation_gate=ready` requires `lockfile_status=present` in §1 and every
High/blocker / `required_for_path=yes` row `decided` — still never start
install, codemod, or source edits from this skill. Validator also enforces:
concrete `report_path` (not bare `.`), default subsystem full set, path id ∈
ladder matching §3/§7, and path preset ↔ axis consistency.

## Completion gate

- Preflight passed (Node probe + package manager detect + Python)
- Workspace profiled; subsystems + `required_for_path` classified; path + axes
  stated; recipes named not run; fact/inference split; Composition rewrite
  scoped out; every High/blocker / `required_for_path=yes` queued + recorded;
  queue zero `ready`/`pending`; `decision-records/` complete; validator exit
  `0`; Agent review → `analysis_status=complete`

## Context budget and portability

Return the path to `upgrade-summary.json` by default. Load the full report only
for a named section, one decision record for a named decision, and inventory
only for a named evidence question. The output bundle must validate and remain
useful when every other Skill folder is absent.

## References

**Minimum load (every run):** `references/environment-preflight.md`,
`references/subsystem-inventory.md`, `references/human-confirmation-gates.md`.

**On demand:** `references/dual-entry-and-batching.md`,
`references/migration-path-ladder.md`, `references/impact-and-validation.md`,
`references/official-docs-index.md`, `references/named-migration-recipes.md`, `references/common-upgrade-patterns.md`,
`references/next-action-choice-menus.md`, `references/report-contract.md`,
`references/decision-record-schema.md`, `templates/decision-packet.md`, `templates/decision-record.md`, `scripts/`, `fixtures/`.

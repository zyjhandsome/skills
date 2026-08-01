---
name: vue2-to-vue3-upgrade-impact-analysis
description: >
  Analyze, never implement, a Vue 2.x to Vue 3.x framework upgrade for one
  frontend workspace or a multi-repo inventory. Use when assessing Vue2→Vue3
  migration impact, @vue/compat vs direct Vue3 cutover, Vue CLI/Webpack→Vite,
  Vue Router 4, Vuex/Pinia, Element UI→Element Plus (or other UI), test-utils,
  or blocking Vue plugins. Writes a Simplified Chinese decision packet with
  confirmation queue and batch_implementation_gate. Ends at analysis_status
  complete — never at implementation or codemod execution.
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

Unless evidence rules it out, recommend:

**单仓大爆炸切流 + 仓内 `@vue/compat` 分步清 warning + 构建必须同升（偏 Vite）**

Path id: `compat-big-bang`. Alternatives and when to switch:
`references/migration-path-ladder.md`. Confirmation still requires a human
`proceed:path:…` (or `other`).

## Workflow

1. Run environment preflight; resolve project root and frontend workspace
   (ask if multiple). Exit `5` → stop (`blocked`). State assumptions.
2. Run light inventory (`scripts/profile_inventory.py` or equivalent read-only
   scan). Cover all default subsystems in
   `references/subsystem-inventory.md`. Record lockfile presence/absence.
3. Classify each subsystem: `in_scope` / `not_applicable` / `blocker` /
   `high` / `medium` / `low`. List Vue-related packages with Vue3 readiness
   (`ready` / `needs-major` / `replace` / `unknown` / `unused`).
4. Pick `recommended_path` from `references/migration-path-ladder.md`. Name
   applicable recipes; never execute them.
5. Map impact (`references/impact-and-validation.md`): breaking API surfaces,
   UI/library jumps, router/store/build/test, smoke/E2E needs. Mark fact vs
   inference. Composition rewrite = out of scope note only. Complete §10
   人工补搜检查 even when profile signals look complete.
6. Draft packet + Decision Records (path unit + each High/blocker subsystem).
7. Work confirmation queue (`references/human-confirmation-gates.md`):
   - Wave 1: migration **path** (`ready`) — ask now.
   - After path `decided`: Wave 2+ every High/blocker **subsystem** currently
     `ready`, same wave, each with its own answer.
   Never ask `blocked`. No blanket proceed. Record → regenerate → Agent review
   → `analysis_status=complete`.
8. Stop. Do not open implementation plans from this skill.

「继续 / 全部放行 / 别再问了」**≠** proceed token. Do **not** infer
`decided`. Re-prompt with verbatim `proceed:path:…` /
`proceed:subsystem:…` menus. Natural language never writes `人工答复`.

## Output

Resolve the report directory in this order:

1. Explicit `--output-dir` override.
2. Existing `--change-dir` → `<change-dir>/evidence/vue2-to-vue3-upgrade/`
3. Else under the analyzed project root, match an existing
   `openspec/changes/<id>/` (one → use; many → ask).
4. Else default candidate:
   `<project-root>/.vue2-to-vue3-upgrade-analysis`

Do **not** create OpenSpec changes. Prefer (2)/(3) when a change dir applies;
otherwise use (4) after restating the absolute path and getting explicit
confirmation (`--output-dir <that-path>` or `confirm:output-dir`). Until
confirmed: read-only analysis only; **do not write**. Preflight failure →
stop. Oral「写到仓库」alone is not enough.

Write at least `vue2-to-vue3-upgrade-report.md`. Multi-batch layout:
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
| `batch_implementation_gate` | `frozen` / `ready` (informational; never implements) |
| also required | `behavior_parity_required`, `network_mode`, `report_path` |

Never set `analysis_status=complete` while `decision_status=needs_choice` or any
queue `ready`/`pending`. Uncleared askable rows ⇒ **ask now**, not “继续/放行”.
`batch_implementation_gate=ready` is informational only — never start install,
codemod, or source edits from this skill.

## Completion gate

- Preflight passed (Node probe + package manager detect + Python)
- Workspace profiled; subsystems classified; path recommended; recipes named
  not run; fact/inference split; Composition rewrite scoped out; every
  High/blocker subsystem queued + recorded; queue zero `ready`/`pending`;
  `decision-records/` complete; validator exit `0`; Agent review →
  `analysis_status=complete`

## References

**Minimum load (every run):** `references/environment-preflight.md`,
`references/subsystem-inventory.md`, `references/human-confirmation-gates.md`.

**On demand:** `references/dual-entry-and-batching.md`,
`references/migration-path-ladder.md`, `references/impact-and-validation.md`,
`references/named-migration-recipes.md`, `references/common-upgrade-patterns.md`,
`references/next-action-choice-menus.md`, `references/report-contract.md`,
`references/decision-record-schema.md`,
`references/sibling-skill-drift-checklist.md` (maintainer only; no runtime
coupling), `templates/decision-packet.md`, `templates/decision-record.md`,
`scripts/`, `fixtures/`.

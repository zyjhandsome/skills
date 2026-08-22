---
name: vue2-to-vue3-upgrade-impact-analysis
description: >
  Analyze, never implement, a Vue 2.x to Vue 3.x framework upgrade for one
  frontend workspace, a multi-repo inventory, or an A→B path/axes decision.
  Use when assessing Vue2→Vue3 impact, @vue/compat vs direct Vue3, Vue
  CLI/Webpack→Vite, Router 4, Vuex/Pinia, Element UI→Plus, or blocking plugins.
  Also use when auditing what a previous Vue3 migration left behind.
  Do not use when one page is already chosen for native hosting and the caller
  needs revision-bound behavior, visual, permission, or rollback evidence —
  that belongs to migrate-vue2-pages-to-vue3-host.
---

# Vue 2 → Vue 3 Upgrade Impact Analysis

Produce an evidence-backed decision packet — analysis only. Do not change
manifests, run install/upgrade, apply migration codemods, or edit application
code.

## Minimal caller input

A **short prompt** is enough: invoke the skill, give the project root (or accept
the stated cwd), and either analyze one frontend workspace, ask for「多仓巡检」,
or name A→B (`source_root` + `implementation_target`). Resolve the report
directory under Output unless overridden.

## Environment preflight

Before analysis (including manifest-only reads), run
`references/environment-preflight.md` / `scripts/preflight.py`. Missing Node
(or project pin probe), package manager detection, or Python → batch-wide
`analysis_status=blocked`; list gaps in chat; **do not write** reports. Host vs
project Node mismatch is recorded, not a hard block. Node is two-plane: the
project's effective contract, separate from the selected target toolchain's
`engines.node` intersection. Unknown target range or unresolved conflict keeps
the handoff frozen; `upgrade-required` also needs `confirm:node-strategy:…`.
Network probe same wave; dual registry+docs failure → offline confirm gate.

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
- **Host-port:** never edit A; implement-on B only; see ladder host-port rules.

## Dual entry (+ host-port)

| Entry | Input | First action |
|---|---|---|
| Single workspace | project root | Preflight → profile → packet |
| Multi-repo inventory | roots / parent | Candidate table → ask batch |
| Host-port A→B | `source_root=A` + `implementation_target=B` | Preflight/profile A; contrast B; packet for B |

Normalize per `references/dual-entry-and-batching.md`. One batch = **workspace ×
build variant × scope** (A→B: workspace=A; scope often `page-closure`).

## Default recommended path

- **In-place:** `compat-big-bang` (`compat` + `vite` + `single-cutover`) unless
  evidence favors `direct-vue3` or coexistence. Deviating to in-place
  `direct-vue3` requires a §3 `default_path_deviation:` line naming what compat
  would have absorbed and which validations take over.
- **A→B / 并入 / iframe 收编:** `host-port-direct` (`direct-vue3` +
  `existing-vite` + `host-port`). §1 needs `source_root`,
  `implementation_target`, `forbid_source_mutation: yes`. Compat is **not**
  primary. Same git repo with a separate Vue3 host workspace is also
  `host-port`, not in-place. Axes + Wave 1 `proceed:path:…` still required —
  details in `references/migration-path-ladder.md`.

## Workflow

1. Preflight; ask every triggered Wave 0 setup confirm in **one** message, each
   with a recommendation and a verbatim reply
   (`references/user-decision-catalog.md`). Exit `5` → `blocked`.
2. Light inventory (`scripts/profile_inventory.py`). Cover
   `references/subsystem-inventory.md`. Record `lockfile_status`
   `present|absent|unparsed`; gate stays `frozen` unless `present`. Bind the
   packet to `repo_revision` and state `browser_support_floor` (§1 anchors).
   `vue_major=3` → stop, or declare status `entry_mode: residual-audit` and use
   the residual packet shape in `references/report-contract.md`; never write a
   Vue2-baseline packet over an already-Vue3 workspace.
3. Build the Node compatibility matrix from current pins/`engines`/CI/container
   evidence and the **exact selected target versions** of the build, test, SSR,
   and package-manager toolchain. Do not call this a universal “Vue 3 minimum”:
   use registry metadata and official docs as of `evidence_as_of`. Classify it
   as `compatible` / `upgrade-required` / `conflict` / `unknown`; put any Node
   transition under the `build` subsystem and name `same-node`,
   `upgrade-before-vue`, or `temporary-dual-node` strategy.
4. Classify subsystems (`risk`, readiness, `required_for_path`) and Vue-related
   packages (`ready` / `needs-major` / `replace` / `unknown` / `unused`).
5. Pick `recommended_path` + three axes; name recipes; never execute. Give every
   named recipe one `recipe_constraints` row (`after` + `atomic`) per
   `references/implementation-sequencing-constraints.md` — order and atomicity
   are code facts, not a schedule.
6. Map impact (`references/impact-and-validation.md`); cite
   `references/official-docs-index.md`. Fact vs inference. Composition rewrite
   out of scope. Complete §10 人工补搜检查. Register every `Vue.prototype.$*`
   and `globalProperties` / `provide/inject` target. UI/CSS triggers → full
   `ui_visual_risk` block; a UI-kit `replace`/`needs-major` additionally needs
   `### ui_behavior_contract` + `ui_cutover_staging:` — mount timing, prop/enum
   renames and trigger-slot content shape are invisible to the build *and* to the
   visual diff. Dev and build are **two runtime lanes**: one named validation
   each. Any capture also needs a `console-baseline`, whose disposal duty is keyed
   by emitter (framework / target kit / toolchain), never by a remembered message
   list; and removing an error-swallowing shim makes latent defects fail on load.
7. Draft packet + Decision Records (path + High/blocker /
   `required_for_path=yes`).
8. Confirmation queue (`references/human-confirmation-gates.md`): Wave 1 path;
   after path decided, Wave 2+ ready High/blocker / required subsystems.
   Record → regenerate → Agent review → `analysis_status=complete`.
9. Stop. Do not open implementation plans.

「继续 / 全部放行 / 别再问了 / 全部纳入」**≠** proceed token. Re-prompt verbatim
`confirm:…` / `proceed:path:…` / `proceed:subsystem:…` menus, recommendation
first. Wave here = a confirmation batch, not a caller's session phase.

## Output

1. Explicit `--output-dir` **is** confirmation — do not re-ask. The candidate
   `<project-root>/.vue2-to-vue3-upgrade-analysis` (after `confirm:output-dir`)
   is standalone-only: a caller that owns an evidence root must pass
   `--output-dir`. Until confirmed: read-only.
2. Bundle: `vue2-to-vue3-upgrade-report.md`, `upgrade-summary.json` (≤12 KiB),
   `inventory.json` when profiled, `decision-records/*.md`.
3. Multi-batch:
   `<entry-kind>/<slug>__variant-<v>__scope-<s>/` + `BATCH-INDEX.md`.
4. Prose ZH; enums/paths/URLs verbatim. Contract:
   `references/report-contract.md`.

## Validator

```shell
python -m unittest discover -s tests -v
python scripts/validate_report.py <report.md>
python scripts/validate_report.py --evidence-dir <evidence-dir> [--json]
python scripts/validate_upgrade_summary.py <upgrade-summary.json>
python scripts/preflight.py --project-root <dir> [--json]
python scripts/profile_inventory.py --project-root <dir> [--json] [--output <inventory.json>]
```

Exit `0` pass / `3` errors / `4` missing. Pass = shape only. Fixtures:
`fixtures/valid-report*.md`, `decision-records/`, `evidence-complete/`.

## Status axes

| Axis | Meaning |
|---|---|
| `analysis_status` | `partial` / `blocked` / `complete` |
| `decision_status` | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | `frozen` / `ready` (handoff only) |
| `implementation_readiness` | always `not_assessed` |
| also required | `behavior_parity_required`, `network_mode`, `report_path`, `evidence_as_of` |

UI-kit / Tailwind / mixed tables / scoped-style risk →
`visual_acceptance_required=yes` + §5 `ui_visual_risk`. Never `complete` while
queue has `ready`/`pending`. Gate `ready` needs lockfile `present` + all High /
blocker / required rows `decided` — still never install/codemod from this skill.

## Completion gate

Preflight OK; profiled; path+axes; recipes named not run; Composition scoped
out; Node current/target contracts evidenced and transition decided; High /
blocker / required queued+recorded; queue clear; DRs complete; validator `0`;
Agent review → `analysis_status=complete`.

## Context budget and portability

Return `upgrade-summary.json` by default (includes `lockfile_status`,
`named_recipes`, `named_validations`, `recipe_constraints`). Load the full report only for a named
section, one decision record for a named decision, and inventory only for a
named evidence question. The output bundle must validate and remain useful
when every other Skill folder is absent.

## References

**Minimum load (every run):** `references/environment-preflight.md`,
`references/subsystem-inventory.md`, `references/human-confirmation-gates.md`,
`references/user-decision-catalog.md`; plus `references/report-contract.md`
before writing any packet — the validator enforces fields listed only there.

**On demand:** `references/dual-entry-and-batching.md`,
`references/migration-path-ladder.md`, `references/impact-and-validation.md`,
`references/implementation-sequencing-constraints.md`,
`references/official-docs-index.md`, `references/named-migration-recipes.md`,
`references/common-upgrade-patterns.md`,
`references/next-action-choice-menus.md`,
`references/decision-record-schema.md`, `templates/decision-packet.md`,
`templates/decision-record.md`, `scripts/`, `fixtures/`.

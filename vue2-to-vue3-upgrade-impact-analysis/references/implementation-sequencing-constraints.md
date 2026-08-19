# Implementation sequencing constraints — describe order, never schedule

This stage records **what must already be true before what**. It never creates
tasks, assigns owners, estimates effort, or batches work. A constraint is either
a code fact from the profile or a fixed Vue3 migration semantic; anything that
needs approved scope to decide is not a constraint and does not belong here.

Every named recipe in `named_recipes` gets exactly one `recipe_constraints` row
in `upgrade-summary.json`: `id`, `after` (sequence anchors or other recipe ids),
`atomic` (`yes` / `no`). Contract and validator rules:
`report-contract.md`, `scripts/validate_upgrade_summary.py`.

## Sequence anchors

Fixed phase order. `after` may only reference one of these anchors or another
named recipe.

| Anchor | Holds when | Evidence source |
|---|---|---|
| `baseline-green` | the pre-upgrade workspace installs and builds on its current lane | §1 `current_node_contract` + a known-green build, not a declaration alone |
| `visual-baseline` | pre-upgrade visual states are captured | only meaningful when `visual_acceptance_required: yes`; §5 `baseline_status` |
| `node-lane` | the target toolchain's Node range is resolvable and selectable everywhere it is declared | §1 `target_node_requirement` + `node_transition_strategy` |
| `first-install` | the first dependency install runs under the target lane | requires `node-lane` |
| `runtime-cutover` | the Vue runtime has moved (alias to `@vue/compat`, or `vue@3` directly) | §3 `runtime_axis` |
| `post-cutover` | the app boots on the Vue 3 runtime | anything only judgeable after boot |

## Constraint rules

1. **`node-lane` precedes `first-install`.** A Node move that only changes a
   developer machine is not a lane. The lane is only established when local
   pins, `engines`, CI, container/devcontainer, deployment builder, and
   Corepack/`packageManager` all resolve to the target range, or a
   `temporary-dual-node` strategy defines both lanes with a switch condition.
2. **`visual-baseline` precedes every dependency and source mutation.** The
   baseline window closes at the first mutation and cannot be reopened at the
   same revision. When the pre-upgrade app cannot start on any available lane,
   that is a decision to record now (substitute capture surface, or "no
   baseline" as a residual), not a surprise for the implementation stage.
3. **`runtime-cutover` precedes mechanical codemods.** Codemod output is only
   reviewable against a runtime that already reports the new semantics; running
   transforms first produces diffs nobody can falsify.
4. **Atomicity is a property of the recipe, not of the schedule.**
   `atomic: yes` means the recipe has no intermediate state the workspace can
   sit in — a runtime alias, a router factory swap, or a build-entry move either
   lands whole or is reverted whole. `atomic: no` means it may land directory by
   directory with a reviewable diff per batch.
5. **The rollback unit is the pre-upgrade revision on the old lane.** Proving
   rollback means a frozen install plus build of that revision, not reverting a
   single file. Name it whenever a recipe is `atomic: yes`.
6. **Interaction assertions come from the candidate list, not from improvised
   smoke.** `inventory.json` →
   `source_impact_signals.interaction_assertion_candidates` locates every hit of
   the silent-break family (`model_option`, `native_modifier`,
   `keycode_modifier`, `transition_component`) with file and line. These breaks
   keep build and lint green, so each row needs an input→state-write-back check
   of its own. When `truncated: true`, the list is incomplete: re-scan before
   treating it as the closure.
7. **`model_option` rows still need the live/dead split.** The scanner locates
   the option; whether a parent consumes the component through `v-model`
   (silently rebound to `modelValue`, write-back dead) is cross-file judgement
   and is closed by the §10 `人工补搜检查` row, not by the scanner.

## Out of this stage

Task titles, ownership, effort, parallel batching, delivery order, and any
approval flow. Those depend on approved scope, which does not exist yet at
analysis time. Emit constraints; let whoever plans read them.

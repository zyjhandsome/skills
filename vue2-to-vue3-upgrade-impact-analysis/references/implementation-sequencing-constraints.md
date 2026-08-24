# Implementation sequencing constraints — describe order, never schedule

This stage records **what must already be true before what**. It never creates
tasks, assigns owners, estimates effort, or batches work. A constraint is either
a code fact from the profile or a fixed Vue3 migration semantic; anything that
needs approved scope to decide is not a constraint and does not belong here.

Every named recipe in `named_recipes` gets exactly one `recipe_constraints` row
in `upgrade-summary.json`: `id`, `after` (sequence anchors or other recipe ids),
`atomic` (`yes` / `no`), and `overlaps_with` when the recipe shares call sites
with another named recipe. Contract and validator rules:
`report-contract.md`, `scripts/validate_upgrade_summary.py`.

## Sequence anchors

Fixed phase order. `after` may only reference one of these anchors or another
named recipe.

| Anchor | Holds when | Evidence source |
|---|---|---|
| `baseline-green` | the pre-upgrade workspace installs and builds on its current lane | §1 `current_node_contract` + a known-green build, not a declaration alone |
| `visual-baseline` | pre-upgrade visual states are captured | only meaningful when `visual_acceptance_required: yes`; §5 `baseline_status` |
| `console-baseline` | pre-upgrade runtime console output is captured under the same conditions as the later capture | §8 console validation; required whenever any post-cutover functional validation is named |
| `node-lane` | the target toolchain's Node range is resolvable and selectable everywhere it is declared | §1 `target_node_requirement` + `node_transition_strategy` |
| `first-install` | the first dependency install runs under the target lane | requires `node-lane` |
| `runtime-cutover` | the Vue runtime has moved (alias to `@vue/compat`, or `vue@3` directly) | §3 `runtime_axis` |
| `post-cutover` | the app boots on the Vue 3 runtime, on **every** lane the workspace has (dev and build) | anything only judgeable after boot |

## Constraint rules

1. **`node-lane` precedes `first-install`.** A Node move that only changes a
   developer machine is not a lane. The lane is only established when local
   pins, `engines`, CI, container/devcontainer, deployment builder, and
   Corepack/`packageManager` all resolve to the target range, or a
   `temporary-dual-node` strategy defines both lanes with a switch condition.
2. **`visual-baseline` and `console-baseline` precede every dependency and
   source mutation.** Both baseline windows close at the first mutation and
   cannot be reopened at the same revision. When the pre-upgrade app cannot
   start on any available lane, that is a decision to record now (substitute
   capture surface, or "no baseline" as a residual), not a surprise for the
   implementation stage. A console baseline is what separates an environmental
   error from an upgrade regression later; without it that split is an opinion.
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
   the silent-break/runtime-fatal family (`model_option`, `native_modifier`,
   `keycode_modifier`, `transition_component`, `sync_modifier`,
   `options_filters_access`, `router_error_suppression`,
   `router_named_target`, `ui_trigger_slot_target`, `kit_icon_class_prop`,
   `external_global_runtime`) with file and line. These breaks
   keep build and lint green, so each row needs an input→state-write-back check
   or runtime round-trip of its own. `cap` is per signal; when `truncated: true`,
   use `truncated_signals` plus hit/emitted counts to re-scan the incomplete
   families before treating the list as the closure.
7. **`model_option` rows still need the live/dead split.** The scanner locates
   the option; whether a parent consumes the component through `v-model`
   (silently rebound to `modelValue`, write-back dead) is cross-file judgement
   and is closed by the §10 `人工补搜检查` row, not by the scanner.
8. **Overlapping recipes need a declared owner.** Two recipes overlap when they
   rewrite the same call sites — the canonical case is a Vue core codemod and a
   UI-kit codemod both touching `.sync` / `v-model` bindings on kit components.
   Each recipe can be individually correct and the composition still wrong,
   because neither owns the intersection: the core codemod produces a valid Vue3
   binding carrying the old kit's prop name, and the kit codemod never revisits
   a binding the core codemod already rewrote. Declare the pair in
   `overlaps_with` (mutually — a one-sided declaration is the unowned
   intersection itself), and name **one §8 validation for the intersection**,
   distinct from either recipe's own validation. Ordering does not fix this:
   whichever runs second sees output the other already normalized.
9. **Both runtime lanes are sequenced, not just one.** When the workspace has a
   dev lane and a build lane, `post-cutover` holds only when the app boots on
   both. A recipe validated on one lane is validated on one lane.
10. **External globals close only after real mount.** A
    `manual-external-global-script` recipe may be statically reviewed before
    cutover, but its readiness, instance lookup and behavior round-trip must run
    after `post-cutover`. An auth/login placeholder is not the mounted consumer.

## Out of this stage

Task titles, ownership, effort, parallel batching, delivery order, and any
approval flow. Those depend on approved scope, which does not exist yet at
analysis time. Emit constraints; let whoever plans read them.

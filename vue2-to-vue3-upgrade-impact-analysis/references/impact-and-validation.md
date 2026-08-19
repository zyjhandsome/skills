# Impact and validation

## Evidence priority

1. Lockfile + `package.json` declared versions (fact). Record the scanner's
   `lockfile_status: present|absent|unparsed` in §1. Anything except `present`
   keeps `batch_implementation_gate=frozen` (still not a preflight hard block).
2. Config presence (`vue.config.js`, `vite.config.*`, babel, eslint)
3. Bounded source search via `profile_inventory.py`: filters / `Vue.filter`,
   `$listeners`, `.sync`, `new Vue(`, `Vue.use`, `slot-scope` / legacy `slot=`,
   event bus, router `addRoutes` / `*`, lifecycle destroy hooks,
   `Vue.prototype.$*` definitions/consumers, `globalProperties`, packages
   registered through `Vue.use`, and the silent-break family: `.native` /
   keyCode modifiers, component `model:` option, `Vue.component` /
   `Vue.directive` / `Vue.mixin` global registration, `Vue.extend` /
   `Vue.observable` / `propsData`, `<transition>` usage, AMD-style async
   component factories, and same-element `v-for`+`v-if`. Also complete §10
   `人工补搜检查` for residual gaps and non-`vue-*` blockers (`tui-editor`,
   internal plugins, editors, etc.).

   **Interaction assertion candidates:** counts plus five samples per signal are
   not a closure. `source_impact_signals.interaction_assertion_candidates`
   locates every `model_option`, `native_modifier`, `keycode_modifier` and
   `transition_component` hit with file, line and excerpt, bounded by its own
   `cap` and `truncated` flag (separate from the file-scan `truncated`). Each
   row needs an interaction-level check named in §8; `truncated: true` means the
   list is incomplete and must be re-scanned before it is treated as complete.
   Sequencing and atomicity for these rows:
   `implementation-sequencing-constraints.md`.

   **Silent-break rule:** `model_option` hits must be split into live options
   (a parent consumes the component via `v-model` — Vue3 silently rebinds to
   `modelValue` and the write-back chain goes dead; mark blocker) and dead
   options (parents bind the prop explicitly; low). `.native`, transition
   class renames, missing `emits`, `v-bind` order, watch-on-array and mixin
   data shallow merge all keep build and lint green — they must be closed by
   the fixed §10 rows plus interaction-level validations named in §8, never
   by "build passed".
4. Official docs URLs for the exact interval / library major — start from
   `official-docs-index.md` (EOL + two-layer modification model + canonical
   hubs + high-signal checklist), then fetch the linked page; do not invent
   breaks from memory. Static checklist = candidates; name Migration Build
   warnings / per-component `compatConfig` as the dynamic backlog (do not run)
5. Inference — label explicitly

**Installed target major vs migration document.** A doc URL pins the interval
being crossed; it never pins what `npm i <pkg>` resolves to. Every package the
implementation stage will install needs its target major resolved from registry
metadata at `evidence_as_of` and written into the packet, and any gap between
that major and the migration-guide interval is itself a recorded decision. Rules
and the `peer_conflicts` obligation: `subsystem-inventory.md`.

**Exact-pin peers.** Some Vue packages peer-depend on an exact version rather
than a range — `@vue/compat` declares `"vue": "<same exact version>"`, not a
caret range. Where that holds, "keep `vue` / `@vue/compat` / `@vue/compiler-sfc`
aligned" stops being a discipline the reviewer must enforce and becomes a
package-manager-enforced constraint: a mismatched pin fails or warns at install
time instead of drifting silently. Record which alignment rules are
tool-enforced and which still need a named validation.

## Impact layers (report §5)

| Layer | Examples |
|---|---|
| 代码 | SFC API breaks, filters, functional components, render `h` |
| 配置 | alias `vue`→`@vue/compat`, Vite/CLI, env defines |
| 路由 | Router 3→4 history/mode, guards, `*` catch-all |
| 状态 | Vuex install → Vuex4 / Pinia module map |
| UI | Element UI→Plus (or peer UI) component/API/CSS |
| 测试 | test-utils v1→v2, mount options, E2E smoke value |
| 构建/部署 | Vite build output, publicPath/base, current/target Node contract, CI/container/deploy Node alignment |

## Node compatibility matrix

In §1, write concrete lines for `host_node_version`, `current_node_contract`,
`current_node_evidence`, `target_node_requirement`, `target_node_sources`,
`node_compatibility_status`, and `node_transition_strategy`.

- `current_node_contract` answers what the existing project is configured or
  evidenced to run on. Distinguish pins/declarations from a known-green build.
- `target_node_requirement` is the semver intersection for the selected target
  versions, not the requirement of an unversioned “Vue 3”.
- `target_node_sources` lists `package@version → engines.node` (or explicitly
  `no engines.node`) with registry/official evidence and `evidence_as_of`.
- If target versions are not concrete enough to resolve engines, use
  `node_compatibility_status: unknown`; do not let the handoff become `ready`.
- `upgrade-required` makes the `build` subsystem High and
  `required_for_path=yes`. Its decision record must cover local development,
  CI, Docker/devcontainer, deployment builders, package-manager/Corepack,
  native addons, caches, and rollback.

### Worked intersection (shape, not a lookup table)

Three selected packages, each with a differently shaped union range, observed on
one `evidence_as_of`:

```text
vite@8.2.1      engines.node = ^20.19.0 || >=22.12.0
vitest@4.1.11   engines.node = ^20.0.0 || ^22.0.0 || >=24.0.0
vue-i18n@11.4.8 engines.node = >= 22
```

`vite ∩ vitest` = `^20.19.0 || ^22.12.0 || >=24.0.0` — an operand that appears in
neither input. Adding `vue-i18n` removes the Node 20 branch entirely, leaving
`^22.12.0 || >=24.0.0`. Two lessons the packet must reflect: copying any single
operand ("Node 20+", "^20.19.0 || >=22.12.0") is wrong, and a single library
major on a subsystem that looks unrelated to the build can delete a whole Node
lane. Re-resolve these numbers per run; they are a shape, not a fact to reuse.

Name validations for: existing baseline on its current Node; existing baseline
on the proposed target Node before Vue dependency changes (when feasible);
frozen install + build/test on the target Node; and alignment of every declared
Node surface after implementation.

## Browser support floor and build entries

§1 must state `browser_support_floor:` from browserslist/`.browserslistrc`
evidence (or an explicit "no config + Vite modern default, decision needed").
Vue 3 drops IE11 and Vite's default build target is modern browsers; an
enterprise floor below that makes `@vitejs/plugin-legacy` (or path rejection)
a `build`-subsystem decision, not an implementation-stage surprise.

Multi-page workspaces must carry the inventory `build_entries` evidence
(`vue.config.js` `pages`, custom entry globs, `public/*.html`, `main*` files)
into the `build` decision: every entry maps to a Vite `rollupOptions.input`
row and is a candidate for visual sample selection. A dropped entry is a
silently missing build surface.

## Validation matrix guidance

§8 table headers (required): `命名配方 | 实施期命令 | 失败证明什么 | 证据状态`.

Every in-scope §4 recipe other than `—` must have one §8 row. Commands are
**named for the implementation stage**; do not run them here. `证据状态` is
usually `待实施阶段` / `待执行`.

Also name, without executing:

- Smoke/E2E routes over deep unit rewrites when UT migration cost is high
- Visual sample states when `visual_acceptance_required=yes` (generic next action only)
- Rollback = redeploy previous workspace release / revert upgrade branch

## Structured UI visual risk

Set `visual_acceptance_required: yes` when any of these is evidenced: UI-kit
major/replacement, Tailwind/reset/Preflight change, global theme variables,
scoped-style or class/style fallthrough changes, mixed table stacks, or heavy
editor/tree/DAG CSS. Inventory at least:

- legacy `/deep/`, `>>>`, `::v-deep`, structural and Element-internal selectors;
- actual global CSS entry/cascade order and theme variable roots;
- UI-kit icon system migration (element-ui font icons `el-icon-*` →
  Element Plus SVG icon components; string `:icon` props stop rendering,
  `.el-icon-*` CSS selectors go dead) — a mandatory trigger, not optional;
- UI-kit component value contracts that shift silently (e.g. Element Plus
  checkbox/radio `:label`→`:value` deprecation, date-picker `value-format`
  defaults, removed `medium` size);
- transition class renames (`v-enter`→`v-enter-from`): animations fail
  silently with a green build — include animated states when present;
- mount container DOM change (Vue3 no longer replaces the host el;
  `#app > *` style selectors may shift);
- SCSS `@import` → `@use` semantics when the build migration rewrites
  `prependData`/`additionalData` (namespace isolation can drop globals);
- Tailwind prefix/Preflight/important/content/safelist and dynamic classes;
- primary search + table page and secondary table when mixed;
- Teleport/append target, overflow/z-index and theme inheritance;
- baseline status and required visual states — on a UI-kit migration the
  required states must cover icon states, navigation states and popper
  triggers, not only table/dialog states.

Write these as the §5 `ui_visual_risk` block defined by `report-contract.md`.
Keep it self-contained: record required visual states and a generic next action;
do not require, invoke, or name another Skill.

When `visual_acceptance_required=yes`, name **at least 5 unique required states**
(e.g. default, empty, data, popper/overlay, icon/toolbar). Downstream visual
gates hard-count evidence rows with a floor of five; naming fewer states fails
only after the pre-upgrade baseline window has already closed.

## Out of scope work

Full Composition API rewrite, design-system restyle unrelated to Vue3, backend
contract changes.

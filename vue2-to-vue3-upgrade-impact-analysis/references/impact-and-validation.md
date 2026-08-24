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
   component factories, same-element `v-for`+`v-if`, `$options.filters` object
   access, bare `<template>` wrappers, CSS that suppresses target-kit overlay
   chrome, and the runtime-lane family (`module.exports` / `exports.x` inside
   source, `require.context`). Also complete §10 `人工补搜检查` for residual gaps
   and non-`vue-*` blockers (`tui-editor`, internal plugins, editors, etc.).

   **Interaction assertion candidates:** counts plus five samples per signal are
   not a closure.    `source_impact_signals.interaction_assertion_candidates`
   locates every `model_option`, `native_modifier`, `keycode_modifier`,
   `transition_component`, `sync_modifier`, `options_filters_access`,
   `router_error_suppression` and `router_named_target` hit
   plus `kit_icon_class_prop`, `lone_template_wrapper`,
   `kit_chrome_css_suppression` and correlated `external_global_runtime` hits
   with file, line and excerpt, bounded by its own
   per-signal `cap`, `truncated_signals`, and hit/emitted counts (separate from
   the file-scan `truncated`). Each
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

   **`.sync` carries a prop name, not just a syntax.** `:p.sync="x"` →
   `v-model:p="x"` is the correct Vue3 rewrite and is safe when the component is
   your own. It is **not** safe when the component belongs to a UI kit that this
   same upgrade replaces: the argument `p` is the *old* kit's prop name, and the
   new kit may have renamed it (a dialog/drawer `visible` becoming `modelValue`
   is the common case). The rewritten binding then compiles, lints and builds
   clean while writing to a prop nothing reads — and because such components
   usually gate a subtree, the visible symptom is a child that never mounts and
   a `$refs` lookup that returns `undefined`, far from the binding. Split
   `sync_modifier` hits by whether the target is a first-party component or a
   kit component under replacement, and resolve the kit ones against the target
   kit's current API before naming the assertion.

   **`$options.filters` is a second call shape.** Codemods rewrite the template
   pipe `{{ x | f }}` and routinely leave `this.$options.filters.f(x)` alone;
   Vue3 removes the entry altogether, so those sites throw at runtime with no
   static fingerprint. Treat pipe rewrites and object-access rewrites as two
   separate closures.

   **A bare `<template>` stops being an abstract wrapper.** Vue 2's codegen
   unwrapped any `<template>` that carried no slot target and emitted its
   children directly, so wrapping a panel body in a plain `<template>` was a
   free grouping device. Vue 3 classifies `template` as an abstract wrapper
   **only** when it carries `v-if` / `v-else` / `v-else-if` / `v-for` /
   `v-slot`; bare, it is an ordinary element and compiles to
   `createElementVNode("template", …)`. The children then mount into a real
   `<template>` element, which the UA stylesheet renders `display: none` — an
   entire section of the page silently blanks with no error, no warning, and no
   diff in the emitted component tree. It survives every codemod because the
   markup is valid in both majors, and it survives a screenshot comparison
   whenever the affected route was only reached at `component-shell`. Two
   properties make it cheap to close: `lone_template_wrapper` locates every
   indented no-attribute `<template>` (the SFC root sits at column 0 and is
   excluded), and `eslint-plugin-vue`'s `vue/no-lone-template` reports the same
   shape, so name a **static** validation for this row rather than resting on a
   rendered check. Hits in `.html` files may legitimately be native
   web-component templates; resolve those, do not assume them.

   **The mount container is no longer replaced, so its selector matches
   twice.** Vue 2's `el` / `$mount` replaced the host element with the rendered
   root; Vue 3's `mount()` renders **into** the container and leaves it in
   place. When `index.html` carries `<div id="app">` and the root SFC's own root
   element also carries `id="app"` — the overwhelmingly common Vue CLI shape —
   the upgraded DOM contains both, nested. This is not only the selector shift
   noted under `ui_visual_risk`: every global rule on that selector now applies
   **twice**, so `#app { padding-top: … }` doubles the offset, borders and
   backgrounds stack, and `min-height` compounds. The duplicate `id` also makes
   `document.getElementById` resolve to the outer element. Compare the mount
   selector in the HTML entry against the root component's root element
   attributes and record the collision; the fix is a decision (drop one side)
   and belongs in the packet, not in the implementer's judgment.

   **A UI-kit icon prop can turn a CSS class into a tag identity.** Legacy kits
   accepted font/sprite class strings (`el-icon-*`, `sprite-icon ...`) on
   `icon`; component-based target kits commonly require a Component instead.
   Depending on the exact target implementation, the old value either becomes
   a silent missing icon or is passed to DOM creation as a tag name. A
   whitespace-delimited class string is then capable of throwing during mount
   and blanking the route. Resolve severity against the selected target-kit
   version; never downgrade a proven mount throw to visual polish. Every
   `kit_icon_class_prop` row needs a render/interaction assertion after its prop
   is rewritten to a component, icon slot, or wrapper component. Identifier
   bindings the scanner cannot classify remain a §10 manual lookup.

   **Silence can also break in the other direction.** The family above is about
   working code going quiet. The inverse is code that was *already* wrong and was
   being muffled, where the upgrade removes the muffler and a latent defect
   becomes a hard failure on first load. Two router shapes carry it, and the
   `router_error_suppression` / `router_named_target` candidates locate them:

   - **A prototype patch that swallows navigation rejections.** The Router 3 era
     answer to redundant-navigation noise was to overwrite
     `VueRouter.prototype.push/replace` with a version that catches and discards
     the rejection. Router 4 has no such prototype to overwrite, so the patch
     silently stops applying — every rejection the app was throwing away for
     years now surfaces at once. The same applies to any `.catch(() => {})` on a
     navigation call. Inventory the patch *and* what it was hiding; deleting the
     patch is a one-line change whose blast radius is the entire route table.
   - **Required params are validated instead of ignored.** Navigating by name
     without the params the path pattern requires is silent in Router 3 and
     **throws** in Router 4. Combined with the swallowing patch above, such a
     call can have been broken since the day it was written, and it typically
     sits in app bootstrap, so the first symptom after cutover is a blank page
     rather than a broken link. Every name-target `push`/`replace` needs its
     params checked against the route definition — this is a per-call-site
     closure, not a codemod.
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

Which packages must be aligned depends on the path: `runtime_axis: compat` needs
`vue` + `@vue/compat` + `@vue/compiler-sfc`; `direct-vue3` needs at least `vue` +
`@vue/compiler-sfc`; an SSR workspace adds `@vue/server-renderer`. State the set
this workspace actually needs in §2, and keep the handoff `frozen` when the
selected target version is unavailable for any member of it — a partially
resolvable set is a conflict, not a rounding error.

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

## Dev lane and build lane are two runtime faces

Treat the toolchain the same way the Node matrix is treated: as **two planes that
must be evidenced separately**. A dev server and a production build do not share
module resolution, entry topology, or environment handling, so "the build is
green" is not evidence about the dev lane and vice versa. Each divergence class
below produces a defect that is invisible on one lane and fatal on the other:

| Class | Why the lanes disagree |
|---|---|
| Source-level CommonJS (`module.exports`, `exports.x`) | A production build passes source through the rollup commonjs transform; the dev server serves source as native ESM and the import resolves to `undefined` |
| `require.context` | A Webpack-only API with no Vite equivalent on either lane — but it fails at different times, and a glob-import shim must be checked on both |
| Multi-entry (MPA) URL shape | Vue CLI `pages` serves flat paths with history fallback; a Vite MPA is addressed by real HTML file paths. `rollupOptions.input` fixes the build without fixing the dev URL |
| `base` / `publicPath` | Dev almost always serves from `/`, so a wrong `base` only appears in the built artifact |
| Env and mode branches | `process.env` inlining, `import.meta.env`, and `NODE_ENV`-gated code take different branches per lane |
| Dependency pre-bundling | Dev pre-bundles `node_modules` with esbuild; the build does not. A CJS-only dependency can work on exactly one lane |

Obligations for the packet:

- Record which lanes the workspace actually has (`dev`, `build`+static serve,
  SSR/preview) in the `build` subsystem row, and carry the MPA entry evidence
  into the **dev URL shape**, not only into `rollupOptions.input`.
- §8 must name **at least one validation per lane**, and `named_validations`
  must contain a dev-lane entry whenever a dev lane exists. A single row that
  says "build passes" satisfies neither.
- The runtime-lane signals (`source_cjs_export`, `webpack_require_context`) are
  lane evidence, not interaction assertions: they belong in the §10 runtime-lane
  row and in the `build` decision record.

## External global scripts are a runtime contract

Bare globals injected by an HTML or dynamically-created `<script>` are neither
npm dependencies nor Vue plugins. When inventory correlates an external script
loader with `window.X` / `globalThis.X` readiness or instance-registry polling,
name `manual-external-global-script` and keep the row runtime-required.

Static review may establish loader ownership, URL/base behavior, DOM selectors,
polling bounds and cleanup, but it cannot prove instance-registration timing.
After cutover, assert on every applicable runtime lane that the script loads,
the ready condition terminates, the instance is retrievable, and one minimal
behavior round-trip succeeds (for an editor, set/get content). Vue3 host-element
preservation and tick/mount timing are part of this check. If auth prevents the
real component from mounting, the assertion is unexecuted rather than passed.

## Console baseline

`visual-baseline` has a sibling. Runtime console output must be captured on the
**pre-upgrade revision under the same capture conditions** as the post-upgrade
capture, and named as a `console-baseline` sequence anchor obligation.

Without it, every post-upgrade console error is arguable: a third-party editor
throwing `SecurityError`, an analytics script timing out, a backend 404 in a
detached environment all look exactly like upgrade regressions, and the party
that wants the gate to pass is the one classifying them. With it, the
regression set is a diff and the environmental set is proven pre-existing.

Name it whenever the packet names any post-cutover functional validation. The
baseline window closes at the first dependency or source mutation, exactly like
the visual baseline, so it costs nothing extra when captured in the same pass
and cannot be recovered afterwards at the same revision.

### Which console output carries a disposal obligation

Define the obligation by **emitter**, never by an enumerated list of remembered
message texts: a list of strings is read as exhaustive, and every warning
outside it gets filed as pre-existing noise by whoever wants the gate to pass.
Classify each distinct message by where it comes from:

| Emitter | Examples | Why it is upgrade-relevant |
|---|---|---|
| Vue core runtime | compat-mode warnings, removed instance APIs, `Runtime directive used on component with non-element root node`, failed component/prop resolution | the framework stating that a construct no longer holds |
| The target UI kit itself | the kit's own deprecation helper firing on every mount of a migrated component (a `type` enum value, a renamed slot) | you migrated *onto* an API the new major already deprecates — see below |
| Build / style toolchain | style-compiler `@import` deprecation (re-emitted per compile and amplified when injected via `additionalData`), plugin/loader deprecations | the new toolchain's own removal clock, and the highest-volume class |
| Application code | app-level warn/error | may be pre-existing — the baseline decides, not the reader |

Rules:

- Anything **absent from `console-baseline` is a regression candidate**
  regardless of emitter, and anything present in it is pre-existing only for
  the same message class, not for the same page.
- Count distinct message classes; do not sample. A per-mount warning is one
  class with a large count. Volume is not severity and severity is not volume,
  so a screenful of one deprecation must not be allowed to bury one error.
- **Deprecated on arrival.** A codemod maps an old API to the target's nearest
  equivalent, and that equivalent is sometimes already deprecated in the target
  major. The result is a whole class of warnings that no app-level review will
  attribute to the migration. Treat it as codemod residue (see
  `named-migration-recipes.md`): expect one call site per warning, and dispose
  the class in one pass instead of chasing instances.
- Exactly three legal dispositions: **rewrite** to the non-deprecated API;
  **config-silenced**, meaning a scoped suppression of one *named* deprecation
  id in build config (the style compiler's deprecation-silencing option is the
  common case) recorded with that id, the reason, and the condition that removes
  it; or **accepted-residual** with an owner. Blanket console filtering,
  wrapping `console.*`, and any suppression of errors are never legal.

## Browser support floor and build entries

§1 must state `browser_support_floor:` from browserslist/`.browserslistrc`
evidence (or an explicit "no config + Vite modern default, decision needed").
Vue 3 drops IE11 and Vite's default build target is modern browsers; an
enterprise floor below that makes `@vitejs/plugin-legacy` (or path rejection)
a `build`-subsystem decision, not an implementation-stage surprise.

Multi-page workspaces must carry the inventory `build_entries` evidence
(`vue.config.js` `pages`, custom entry globs, `public/*.html`, `main*` files)
into the `build` decision: every entry maps to a Vite `rollupOptions.input`
row **and to a dev-server URL** (see the lane table above), and is a candidate
for visual sample selection. A dropped entry is a silently missing build
surface; an entry whose dev URL shape changed is a build that ships while
nobody can open the page locally.

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
- UI-kit icon system migration (element-ui font icons `el-icon-*` and
  class-based sprites → target-kit icon components; old string props may either
  stop rendering or abort mount when interpreted as a tag identity;
  `.el-icon-*` CSS selectors go dead) — a mandatory trigger, not optional;
- UI-kit component value contracts that shift silently — these belong to the
  `ui_behavior_contract` block below, not here; list them there and keep this
  block to what a screenshot can actually show;
- transition class renames (`v-enter`→`v-enter-from`): animations fail
  silently with a green build — include animated states when present;
- mount container DOM change (Vue3 renders into the host el instead of
  replacing it, so `#app > *` selectors shift **and** an id/class shared by the
  HTML container and the root component's root element now matches twice,
  doubling padding/border/min-height — see the evidence note above);
- SCSS `@import` → `@use` semantics when the build migration rewrites
  `prependData`/`additionalData`: namespace isolation can drop globals, which is
  the visual half. The other half is not visual at all — `@import` is deprecated
  in current Dart Sass, so keeping it (which is what a working style build does)
  emits a deprecation per compile unit, multiplied by every file the injected
  preamble reaches. That half belongs to the console taxonomy above and is
  disposed there, not by a screenshot;
- Tailwind prefix/Preflight/important/content/safelist and dynamic classes;
- primary search + table page and secondary table when mixed;
- Teleport/append target, overflow/z-index and theme inheritance. Inventory
  every rule that **suppresses or overrides the kit's own overlay chrome**
  (dialog/drawer `__header`, `__headerbtn`, `__close`, popper arrows) —
  `kit_chrome_css_suppression` locates the `display:none` / `visibility:hidden`
  shape. The failure is not that scoped styles cannot reach teleported nodes:
  teleported children do carry the emitting component's scope id. It is that
  such rules are almost always *descendant* selectors (`::v-deep .el-drawer__header`,
  or a local wrapper class), and teleport removes the anchor from the ancestor
  chain, so the selector stops matching. The suppressed chrome returns while the
  replacement the app drew for it stays, and the symptom is a **duplicated
  control** — two close buttons, two titles — not a missing one. Resolve each
  rule by asking whether its anchor stays behind, and prefer the kit's own
  opt-out prop over CSS;
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

## Structured UI behavior contract

Replacing a UI kit (or crossing its major) shifts two independent things: how it
**looks**, and how it **behaves**. `ui_visual_risk` covers the first. The second
needs its own §5 block, `### ui_behavior_contract`, because every item in it
keeps the build green *and* survives a visual diff — the screenshots match
because the broken state never renders at all.

Required when §4 `ui` is `in_scope` with readiness `replace` or `needs-major`.
Inventory at least:

- **Mount timing.** Overlay components in the new kit are commonly lazy: the
  subtree does not exist until the model value flips true. Any code that reads
  `this.$refs.child` before opening — or immediately after setting the flag,
  without awaiting a tick — silently gets `undefined`. The symptom surfaces far
  from the cause, usually as a dead button rather than as an error at the
  binding.
- **Prop renames.** Value contracts that change identity while keeping their
  meaning: a dialog/drawer `visible` becoming `modelValue`, checkbox/radio
  `:label` becoming `:value`, date-picker `value-format` defaults. Combined with
  a mechanical `.sync` rewrite these produce bindings that compile and write
  nowhere.
- **Icon prop identity.** A legacy font/sprite class string is not a Component.
  Resolve every `kit_icon_class_prop` candidate against the selected target
  kit, and assert both successful mount and the actual icon/toolbar action.
- **Enum renames.** Dropped or renamed enum values (`mini` / `medium` sizes,
  type/status vocabularies). An unrecognized enum value is usually ignored, not
  rejected.
- **Event contract.** `update:<prop>` names follow prop renames; missing `emits`
  declarations turn into attrs fallthrough and double-fire; payload shapes
  change per component.
- **Slot contract.** Slot names and scoped-slot parameter shapes.
- **Slot content shape.** Independent of names: what a slot is allowed to
  *contain*. Trigger/reference slots (popover, tooltip, dropdown) in modern kits
  route their single child through a directive that clones the child VNode, which
  requires an **element-rooted** node. Passing a component whose own root is
  another component compiles, renders, and diffs identically, then warns
  `Runtime directive used on component with non-element root node` at runtime
  while ref forwarding — and therefore popper positioning — silently fails. A
  mechanical slot rename cannot see this: the name is already correct. Inventory
  every trigger slot whose direct child is a component tag rather than a plain
  element, and assert the trigger interaction, not just the render.

Close each with an interaction-level assertion in §8 and mirror the list into
`ui_behavior_contract.required_assertions` (3..20) so a summary-only consumer
still sees them. Contract details: `report-contract.md`.

## Out of scope work

Full Composition API rewrite, design-system restyle unrelated to Vue3, backend
contract changes.

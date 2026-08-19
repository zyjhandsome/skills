# Official docs index (URL + high-signal checklist)

Thin pointer layer — **not** a dump of Vue migration guides.

**Rules**

1. Prefer these canonical URLs when citing compatibility evidence.
2. At analysis time, **fetch** the linked page (or offline cache) for the exact
   interval / library major; do not invent breaking-change details from memory.
3. Do **not** paste migration-guide prose into this skill. When upstream moves,
   update URLs / checklist rows here only.
4. Decision Records and report §4/§5 evidence columns should use these URLs
   (or more specific sub-anchors discovered while fetching).

Primary hub: https://v3-migration.vuejs.org/

## Analysis framing (impact + modification points)

### Vue 2 EOL

Vue 2 reached end-of-life on **2023-12-31** (see hub above). Extended LTS is
transition-only, not a long-term alternative to Vue 3. Record this in baseline /
risk narrative; it does not by itself enumerate code edits.

### Breaking-changes index = static modification catalog

https://v3-migration.vuejs.org/breaking-changes/ is the authoritative **static**
catalog for `core-vue` modification points. Workflow:

1. Run inventory (`profile_inventory.py` signals).
2. Map each hit (and §10 人工补搜 gaps) to a row in the checklist below.
3. Cite the specific official page in §4/§5 and Decision Records.
4. Treat unmapped high-risk APIs as evidence gaps, not silent omit.

Static mapping alone is incomplete for behavioral breaks that leave weak
source fingerprints.

### Migration Build (`@vue/compat`) = dynamic modification backlog

https://v3-migration.vuejs.org/migration-build — Vue 2–compatible behavior on
the Vue 3 runtime. Compile/runtime **warnings drive the remaining edit backlog**.

| Fact for the packet | Implication for this skill (Stage A) |
|---|---|
| Warnings enumerate residual Vue2 APIs still exercised | Name “compat warning 清零” in validation / `core-vue` DR; **do not** install compat or run the app here |
| App-level compat MODE (e.g. MODE 2/3) sets default behavior | Path notes for `compat-big-bang`; exact MODE from fetched docs + project choice |
| Per-component `compatConfig` can narrow exceptions | Call out when a few components need temporary Vue2 behavior while the rest migrate; still require a removal date |
| Compat is a bridge, not the end state | Packet must plan drop-compat → standard `vue` |

**Two-layer modification-point model (required mental model):**

1. **Static (this stage):** inventory + breaking-changes checklist → candidate
   modification points (fact when sampled; else gap).
2. **Dynamic (implementation stage, name only):** Migration Build warnings →
   ground-truth backlog and acceptance (“no residual compat warnings” on smoke
   routes). Stage A records residual risk if warnings cannot be collected yet.

## Canonical URLs by subsystem

| Subsystem / topic | Canonical URL | Use for |
|---|---|---|
| `core-vue` breaking index | https://v3-migration.vuejs.org/breaking-changes/ | Static Vue2→3 modification catalog |
| `core-vue` migration build | https://v3-migration.vuejs.org/migration-build | `@vue/compat`, warnings, `compatConfig` |
| Framework recommendations | https://v3-migration.vuejs.org/recommendations | Vite / Pinia / Volar defaults |
| `router` (3→4) | https://router.vuejs.org/guide/migration/ | Vue Router 3→4 primary cutover |
| `router` (4→5 note) | https://router.vuejs.org/guide/migration/v4-to-v5 | v5 is a **major**, not a minor line; most 3→4 work stays on v4 docs, but the installed major must be pinned (see note below) |
| `store` (Vuex bridge) | https://vuex.vuejs.org/guide/migrating-to-4-0-from-3-x.html | Vuex 3→4 |
| `store` (Pinia target) | https://pinia.vuejs.org/cookbook/migration-vuex.html | Vuex→Pinia |
| `ui` (Element) | https://element-plus.org/en-US/guide/migration.html | Element UI→Plus |
| `test` | https://test-utils.vuejs.org/migration/ | `@vue/test-utils` v1→v2 |
| `build` (Vite) | https://vite.dev/guide/ | Prefer with recommendations (`vitejs.dev` redirects here) |
| `build` Node support (selected Vite major) | https://vite.dev/guide/migration | Follow the migration page for the exact selected major; do not copy the latest major's Node floor onto older targets |
| Vue quick start toolchain | https://vuejs.org/guide/quick-start | Requirement applies to the current create-vue/Vite scaffold, not a universal floor for every Vue 3 app |
| npm registry metadata | `https://registry.npmjs.org/<package>/<version>` | Exact `engines.node` for every selected target package; record absent fields explicitly |
| Vue 2 EOL (`2023-12-31`) | https://v3-migration.vuejs.org/ | Timing / Extended LTS context only |

Other UI stacks (Ant Design Vue, Vuetify, …): use that library’s own migration
page; do not invent Element Plus URLs for them.

**`vue-router` major note.** The `latest` dist-tag has moved past v4 (currently
the v5 line), so a bare `npm i vue-router` resolves to v5, not v4. Two separate
facts must be recorded, never collapsed into one: the **migration document** for
a Vue2 workspace is still v3→v4, while the **installed major** is its own
decision that must be pinned and evidenced from registry metadata at
`evidence_as_of`. `unplugin-vue-router` is deprecated upstream (merged into
vuejs/router, its deprecation notice points at the v4→v5 guide) — a hit on it is
a router-major decision, not a version bump.

## High-signal breaking checklist

Use while mapping impact and completing report §10 `人工补搜检查`. Map each
hit to a fact (inventory / source sample) or explicit evidence gap.

**Closure rule (mandatory):** every row whose inventory key is `—` has no
machine scanner — it MUST therefore appear as a dedicated row in report §10
`人工补搜检查` with a substantive answer. A checklist row that is neither
machine-scanned nor manually answered is a contract violation, not an
acceptable omission. This closes the "index knows, nobody checks" gap.

| Signal / API | Inventory key (if any) | Official page |
|---|---|---|
| Global API → `createApp` (`new Vue`, `Vue.use`, …) | `new_vue`, `vue_use` | https://v3-migration.vuejs.org/breaking-changes/global-api |
| Tree-shakable global / internal APIs | — | https://v3-migration.vuejs.org/breaking-changes/global-api-treeshaking |
| Filters removed | `filters_option`, `vue_filter_register` | https://v3-migration.vuejs.org/breaking-changes/filters |
| `$listeners` removed | `listeners_removed` | https://v3-migration.vuejs.org/breaking-changes/listeners-removed |
| `.sync` / component `v-model` rework | `sync_modifier` | https://v3-migration.vuejs.org/breaking-changes/v-model |
| Slots unification (`$scopedSlots`, `slot-scope`, legacy `slot=`) | `scoped_slots_changed`, `slot_scope`, `slot_attr_legacy` | https://v3-migration.vuejs.org/breaking-changes/slots-unification |
| `$children` removed | `children_removed` | https://v3-migration.vuejs.org/breaking-changes/children |
| Event bus `$on` / `$off` / `$once` removed | `event_bus` | https://v3-migration.vuejs.org/breaking-changes/events-api |
| Functional components | `functional_component` | https://v3-migration.vuejs.org/breaking-changes/functional-components |
| Async components → `defineAsyncComponent` | `async_component_legacy`（AMD 式工厂；`components:` 内 `() => import()` 需人工核对） | https://v3-migration.vuejs.org/breaking-changes/async-components |
| `emits` option（未声明 emit 走 fallthrough 双触发） | — | https://v3-migration.vuejs.org/breaking-changes/emits-option |
| Component `model:` option → `modelValue`（静默失效，双向绑定哑火） | `model_option` | https://v3-migration.vuejs.org/breaking-changes/v-model |
| Render function `h` / API | — | https://v3-migration.vuejs.org/breaking-changes/render-function-api |
| `$attrs` includes `class` / `style` | — | https://v3-migration.vuejs.org/breaking-changes/attrs-includes-class-style |
| `v-if` + `v-for` precedence（Vue3 反转为 v-if 先） | `v_for_with_v_if` | https://v3-migration.vuejs.org/breaking-changes/v-if-v-for |
| `.native` modifier removed（静默失效） | `native_modifier` | https://v3-migration.vuejs.org/breaking-changes/v-on-native-modifier-removed |
| keyCode modifiers removed | `keycode_modifier` | https://v3-migration.vuejs.org/breaking-changes/keycode-modifiers |
| Global registration (`Vue.component` / `Vue.directive` / `Vue.mixin`) → app instance | `global_component_register`, `global_directive_register`, `global_mixin_register` | https://v3-migration.vuejs.org/breaking-changes/global-api |
| Custom directive hook renames (`bind`→`beforeMount`, `inserted`→`mounted`, …) | — | https://v3-migration.vuejs.org/breaking-changes/custom-directives |
| Transition class renames (`v-enter`→`v-enter-from`; 动画静默失效) | `transition_component`（组件命中后须人工核对 CSS 类名） | https://v3-migration.vuejs.org/breaking-changes/transition |
| `v-bind` merge order（后写覆盖，Vue2 相反） | — | https://v3-migration.vuejs.org/breaking-changes/v-bind |
| Watch on arrays（需 `deep` 才触发变更） | — | https://v3-migration.vuejs.org/breaking-changes/watch |
| Attribute coercion（枚举属性 / `false` 不再移除） | — | https://v3-migration.vuejs.org/breaking-changes/attribute-coercion |
| Mixin data merge is shallow | — | https://v3-migration.vuejs.org/breaking-changes/data-option |
| `Vue.extend` / `Vue.observable` / `propsData` removed | `vue_extend`, `vue_observable`, `props_data_option` | https://v3-migration.vuejs.org/breaking-changes/global-api |
| Lifecycle / vnode hook renames (`beforeDestroy`→`beforeUnmount`, …) | `destroy_lifecycle` | https://v3-migration.vuejs.org/breaking-changes/vnode-lifecycle-events |
| `$set` / `$delete` / `Vue.set` removed | `set_delete_removed` | https://v3-migration.vuejs.org/breaking-changes/ (Removed APIs) |
| Mount no longer replaces host el（容器 DOM 结构变化，`#app > *` 选择器受影响） | — | https://v3-migration.vuejs.org/breaking-changes/mount-changes |
| Router `addRoutes` / `path: '*'` | `router_add_routes`, `router_wildcard` | https://router.vuejs.org/guide/migration/ |

## Citation habit

Example evidence cell:

> https://v3-migration.vuejs.org/breaking-changes/filters — inventory `vue_filter_register` hits in `src/filters/`

When `network_mode=offline`, still list the intended URL and mark the claim as
inference / unverified against live docs.

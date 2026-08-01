# Migration path ladder

Pick **one** `recommended_path` before scoring subsystem work. Human must still
confirm via `proceed:path:<id>`.

Also state **three orthogonal axes** in report §3 (required markers). Path id is
a convenience preset; axes record the real choices. Use `other` on Wave 1 when
the human wants a non-default axis mix.

## Orthogonal axes (required in §3)

| Axis marker | Allowed values | Meaning |
|---|---|---|
| `runtime_axis:` | `compat` / `direct-vue3` | Migration build vs direct Vue3 |
| `build_axis:` | `vite` / `cli5-webpack5` / `existing-vite` | Toolchain move (may be phased) |
| `topology_axis:` | `single-cutover` / `coexist` | One-repo cutover vs side-by-side |

## Paths (Wave 1 presets)

| Path id | Default axes | Prefer when |
|---|---|---|
| `compat-big-bang` | `compat` + `vite` + `single-cutover` | **Default.** Typical Vue2 app; can freeze features for a cutover window |
| `direct-vue3` | `direct-vue3` + `vite` + `single-cutover` | Small surface, few Vue2-only APIs, deps already Vue3-ready |
| `microfrontend-coexist` | `compat` or `direct-vue3` + build as needed + `coexist` | Cannot cut over one shell; need per-module migration |
| `deferred-inventory-only` | (axes optional / `n/a`) | Multi-repo scan only; human deferred all workspaces |

## Default

Recommend `compat-big-bang` unless evidence shows `direct-vue3` is clearly
cheaper **or** microfrontend coexistence is mandatory.

When recommending `compat-big-bang`, still write the three axis lines explicitly.
If build should stay on Vue CLI 5 / Webpack 5 first, keep path id
`compat-big-bang` only if the human accepts via `other` **or** set
`build_axis: cli5-webpack5` in §3 and record that in the path Decision Record.

## Explicit non-goals of every path

- Full Options API → Composition API / `<script setup>` rewrite (另立项)
- Drive-by business refactors

## Ordering inside `compat-big-bang` (describe only)

1. Profile + dependency readiness
2. Vue 2.7 stepping stone if still on ≤2.6 (optional prep)
3. Build axis: Vite **or** CLI5/Webpack5 transition (must become Vue3-capable)
4. `@vue/compat` MODE 2 → clear compile/runtime warnings (`runtime_axis: compat`)
5. Vue Router 4 / store (Vuex 4 bridge or Pinia) / UI major
6. Drop compat → standard `vue`
7. Topology cutover + rollback = previous release

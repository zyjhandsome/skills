# Migration path ladder

Pick **one** `recommended_path` before scoring subsystem work. Human must still
confirm via `proceed:path:<id>`.

## Paths

| Path id | Meaning | Prefer when |
|---|---|---|
| `compat-big-bang` | **Default.** Single-repo production cutover; inside the branch use `@vue/compat`, clear warnings, then drop compat. Build toolchain upgrades in the same effort (prefer Vite). | Typical Vue2 app; can freeze features for a cutover window; stacks vary but one workspace ships as a unit |
| `direct-vue3` | Skip or minimize compat; move straight to standard Vue3 build | Small surface, few Vue2-only APIs, dependencies already Vue3-ready |
| `microfrontend-coexist` | Keep Vue2 and Vue3 apps side-by-side (qiankun / Module Federation / dual deploy) | Cannot cut over one shell; need per-module migration across apps |
| `deferred-inventory-only` | Inventory done; no upgrade path chosen this batch | Multi-repo scan only; human deferred all workspaces |

## Default

Recommend `compat-big-bang` unless evidence shows `direct-vue3` is clearly
cheaper **or** microfrontend coexistence is mandatory.

## Explicit non-goals of every path

- Full Options API → Composition API / `<script setup>` rewrite (另立项)
- Drive-by business refactors

## Ordering inside `compat-big-bang` (describe only)

1. Profile + dependency readiness
2. Vue 2.7 stepping stone if still on ≤2.6 (optional prep)
3. Build → Vite (or Vue3-capable toolchain) — **must move with the upgrade**
4. `@vue/compat` MODE 2 → clear compile/runtime warnings
5. Vue Router 4 / store (Vuex 4 bridge or Pinia) / UI major
6. Drop compat → standard `vue`
7. Single-repo cutover + rollback = previous release

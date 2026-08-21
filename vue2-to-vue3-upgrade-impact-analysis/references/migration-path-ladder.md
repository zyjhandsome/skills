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
| `topology_axis:` | `single-cutover` / `coexist` / `host-port` | One-repo cutover vs side-by-side vs port into existing Vue3 host |

## Paths (Wave 1 presets)

| Path id | Default axes | Prefer when |
|---|---|---|
| `compat-big-bang` | `compat` + `vite` + `single-cutover` | **Default for single-repo in-place.** Typical Vue2 app; can freeze features for a cutover window |
| `direct-vue3` | `direct-vue3` + `vite` + `single-cutover` | Small surface, few Vue2-only APIs, deps already Vue3-ready (still in-place) |
| `host-port-direct` | `direct-vue3` + `existing-vite` + `host-port` | **Default for A→B.** Read Vue2 source A; adapt into existing Vue3 host B; do **not** install `@vue/compat` on A or as B primary path |
| `microfrontend-coexist` | `compat` or `direct-vue3` + build as needed + `coexist` | Cannot cut over one shell; need per-module migration / long-lived dual deploy |
| `deferred-inventory-only` | (axes optional / `n/a`) | Multi-repo scan only; human deferred all workspaces |

## UI-kit cutover staging (required when the kit changes)

The three axes describe the runtime, the build and the topology. They do not
describe **when the UI kit moves**, and on a workspace built on a Vue2-only kit
that is usually the single biggest lever on blast radius. State it in §3 as
`ui_cutover_staging:` whenever the `ui` subsystem is `in_scope` with readiness
`replace` or `needs-major`.

| Value | Meaning | Prefer when |
|---|---|---|
| `with-runtime` | the kit is replaced in the same step as the runtime cutover | the kit surface is small, or a compat layer cannot keep the old kit alive |
| `after-runtime` | the runtime moves first (usually behind `@vue/compat`, old kit still mounted), the kit is replaced as a separate step | the kit surface is large, and the packet can evidence that the old kit still functions under the chosen runtime |

Why it is a first-class decision rather than scheduling: with `with-runtime`, the
Vue core rewrite and the kit rewrite land on **the same call sites**. Each
transform can be individually correct and the composition still wrong — a core
codemod turns `:visible.sync` into a valid Vue3 `v-model:visible` that names a
prop the new kit no longer has. `after-runtime` separates those two rewrites so
each has an observable, falsifiable intermediate state.

The cost of `after-runtime` is real and must be recorded too: a compat layer is
transitional debt with a removal condition, `@vue/compat` peers on an **exact**
`vue` version, and whether the Vue2 kit actually works under compat is an
**assumption until evidenced** — name a validation for it, do not assume it.

## Default

**Single-repo in-place:** recommend `compat-big-bang` unless evidence shows
`direct-vue3` is clearly cheaper **or** microfrontend coexistence is mandatory.

**Deviating from the in-place default must be argued.** When the packet selects
`runtime_axis: direct-vue3` with `topology_axis: single-cutover`, §3 must carry
`default_path_deviation:` stating what the default would have absorbed (compat
shims the silent-failure family — `.sync`, filters, removed instance APIs — so
those breaks surface as warnings instead of as dead bindings), why that
absorption is not needed or not worth its removal debt here, and which named
validations take over that coverage. A preset chosen without that sentence is a
preference, not a decision.

**A→B host-port (source A read-only, implement on B):** recommend
`host-port-direct`. Never recommend `compat-big-bang` as the primary path for
this topology. `runtime_axis` must stay `direct-vue3`; `topology_axis` must be
`host-port`. Prefer `build_axis: existing-vite` (reuse host B toolchain) unless
B is not Vite.

### Host-port hard rules

- Analyze / inventory **source A**; `implementation_target` = host **B**.
- Mutation policy: **forbid edits to A**; all implementation happens in B.
- Scope often `page-closure` (entry SFC + direct business children + page-local
  API/utils/styles). Full-stack A inventory is allowed only when explicitly asked.
- Named recipes adapt into B's Router/store/UI stack — do **not** name
  `vue-compat` as the primary recipe for this path.
- Contrast B's Vue/Router/store/UI majors in §3/§5 (fact vs inference).
- **Lock dual-root:** record both A and B lock statuses; handoff gate follows
  **B** (`host_lockfile_status`). A missing lock is a reproducibility note for
  the source inventory, not an automatic permanent freeze when B lock is present.

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

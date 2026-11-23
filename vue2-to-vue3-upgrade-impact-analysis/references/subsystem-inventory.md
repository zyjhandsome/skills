# Subsystem inventory (default full-stack)

Every workspace packet must classify these subsystems. Missing detection →
`unknown` with evidence gap, not silent omit.

Two different facts share this table and must never be collapsed into one cell:
the **migration document** to read (fixed by the interval you are crossing) and
the **installed target major** (resolved from registry metadata at
`evidence_as_of`). See "Installed target major" below.

| Subsystem id | What to detect | Migration document (interval) | Installed target |
|---|---|---|---|
| `core-vue` | `vue` major/version, SFC compiler | Vue 2→3 breaking index | `vue` 3.x + `@vue/compiler-sfc` at the **same exact version** |
| `router` | `vue-router` | v3→v4 guide (primary cutover for a Vue2 workspace) | `vue-router` — `latest` has moved past v4; resolve and pin the major, and record v4-vs-v5 as a decision |
| `build` | Vue CLI / Webpack / Vite; multi-entry evidence (`build_entries`: `pages`, entry globs, `public/*.html`); browser floor (browserslist → Vite target / `@vitejs/plugin-legacy`); builder-selection signals `source_cjs_export`, `webpack_require_context`, `umd_library_export` | Vite migration page **for the selected major**, or Vue CLI 5 / webpack 5 docs when `build_axis` stays `cli5-webpack5` | The builder named by `build_axis`. Vue CLI 5 + `vue-loader` 17 and a kept webpack 5 config are valid Vue 3 targets; do not treat Vite as mandatory |
| `store` | Vuex / Pinia / both | Vuex 3→4, or Vuex→Pinia cookbook | In-place default is Vuex 4. Pinia only when the A→B host already uses it, or the user replies `confirm:store-target:pinia` |
| `ui` | Element UI / Ant Design Vue 1.x / Vuetify 2 / other | that library's own migration page | Matching Vue3 library (e.g. Element Plus), major resolved from registry |
| `test` | `@vue/test-utils`, Jest/Vitest, E2E | test-utils v1→v2 | `@vue/test-utils` v2 line + Vitest/Jest Vue3 config |
| `lint-ide` | eslint-plugin-vue, Vetur/Volar | eslint-plugin-vue Vue3 rule set | Vue3 eslint rules + Volar / `vue-tsc` |
| `i18n-plugins` | vue-i18n; peer metadata; non-`vue-*` packages proven imported then registered via `Vue.use`; plugin/editor/grid name candidates are provisional only | `vue-i18n` v8→v9 guide | Resolve the installed major; later `vue-i18n` majors raise `engines.node` and must enter the Node matrix |
| `composition-existing` | `@vue/composition-api` on Vue ≤2.6, and Vue 2.7 native `setup`. `ctx.root` / `ctx.parent` / `ctx.listeners` / `ctx.refs` are absent from the Vue 3 setup context | listeners-removed page; inventory key `composition_context_removed` | Remove the bridge plugin on Vue 3. Removed context fields are compatibility work, not a full Composition rewrite |
| `blockers` | Packages with no Vue3 line, opaque/internal packages, unresolved plugin candidates | — | replace / fork / remove / defer decision |

## Builder-selection evidence

`source_cjs_export`, `webpack_require_context` and `umd_library_export` (including
`libraryTarget: 'umd'` and `qiankun`) are evidence for the existing `build_axis`
values. Heavy CJS, `require.context`, or UMD library output is a reason to keep
`cli5-webpack5` instead of assuming `vite`. They do **not** add a `build_axis`
value. Rsbuild/Rspack is not an axis; if a human still wants it, that is Wave 1
`other`, and the packet must keep `build_axis` inside `vite` / `cli5-webpack5` /
`existing-vite`.

## Installed target major

Any package the implementation stage will actually install must have its target
**major resolved from registry `dist-tags` / version metadata at
`evidence_as_of`** and written into the packet. A migration guide URL pins the
interval being crossed, never the version that `npm i <pkg>` will produce; the
two drift apart the moment upstream ships a new major. Concretely:

- Never state an installed target as a bare number copied from this file or from
  a doc title. Resolve it, cite it, date it.
- A bare install (`npm i <pkg>`) resolves `dist-tags.latest`. When `latest` is
  ahead of the migration-guide interval, the gap itself is a decision the packet
  must record, not an assumption.
- Do not resolve through `latest` / `next` / `rc` / `beta` / `edge` tags. Those
  tags are maintained per package and routinely point somewhere unexpected
  (a `next` tag can be years older than `latest`).

## Cross-subsystem peer constraints (`peer_conflicts`)

Subsystem rows are classified independently, but peer ranges are not: a router
major can constrain the build tool and the store, a test runner can constrain
the build tool, an i18n major can constrain Node. When a selected target's
`peerDependencies` reach into another subsystem, record it on **both** rows —
in the §4 说明 cell and in each subsystem decision record — as
`peer_conflicts: <package>@<version> → <peer> <range> (subsystem)`. An unrecorded
peer range becomes an install-time warning or resolution failure that no
subsystem owned.

## `blockers` vs dedicated subsystems (dedupe)

- If a Vue2-only package is already owned by a dedicated subsystem row
  (e.g. `element-ui` → `ui`, `vue-i18n` → `i18n-plugins`), do **not** also
  queue `blockers` for that same package.
- Set `blockers` risk to `n/a` (or list residuals only) and keep
  `queue_eligible=no` when every blocker package is covered elsewhere.
- Queue `blockers` only for residual packages that have **no** dedicated
  subsystem owner.
- Dedicated ownership needs package-specific evidence (import/registration,
  peer metadata, or maintainer documentation). A name heuristic or a generic
  `i18n_mode` decision does not own the package; unresolved candidates go to
  `blockers`.
- Regardless of owner, every §2 `unknown` package needs one D19 action token in
  that owner's §4 note and `分叉人工答复`. This is not duplicate queueing: the
  token decides the package action, while `proceed:subsystem:<id>` decides scope.

## Classification fields (per subsystem)

| Field | Values |
|---|---|
| `scope_status` | `in_scope` / `not_applicable` |
| `risk` | `blocker` / `high` / `medium` / `low` / `n/a` |
| `readiness` | `ready` / `needs-major` / `replace` / `unknown` / `unused` |
| `required_for_path` | `yes` / `no` — path cannot hand off as `ready` unless every `yes` is `decided` |
| `queue_eligible` | `yes` if `risk` in `blocker|high` **or** `required_for_path=yes`, after path decided |

## Default `required_for_path` (upgrade paths)

| Subsystem | Default |
|---|---|
| `core-vue` | `yes` |
| `router` | `yes` |
| `build` | `yes` |
| `ui` | `yes` (always `yes` when `risk=blocker`) |
| `i18n-plugins` | `yes` when residual Vue2-only plugins/editors are `high`/`blocker` |
| `store` / `test` / `lint-ide` / `composition-existing` | `no` unless caller expands |
| `blockers` | `no` when deduped into dedicated rows; else `yes` for residual blockers |

Any `in_scope` row with `risk` in `blocker|high` **must** set `required_for_path=yes`.

Treat heuristic or `Vue.use` discoveries as `unknown` until peer metadata or an
official/current maintainer source proves readiness. Never silently omit an
opaque package and never claim `replace` from its name alone.

## Composition API rule

- `composition-existing`: analyze compatibility of **current** usage only.
- Do **not** estimate full Options→Composition rewrite effort.
- Packet must state:「Composition API 全仓重写：另立项，本次不评估工作量」.

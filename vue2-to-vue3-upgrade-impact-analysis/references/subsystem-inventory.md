# Subsystem inventory (default full-stack)

Every workspace packet must classify these subsystems. Missing detection →
`unknown` with evidence gap, not silent omit.

| Subsystem id | What to detect | Typical Vue3 target |
|---|---|---|
| `core-vue` | `vue` major/version, SFC compiler | `vue@3` + `@vue/compiler-sfc` |
| `router` | `vue-router` | `vue-router@4`（主迁移目标；v5 为后续可选线，见 official-docs-index） |
| `build` | Vue CLI / Webpack / Vite; multi-entry evidence (`build_entries`: `pages`, entry globs, `public/*.html`); browser floor (browserslist → Vite target / `@vitejs/plugin-legacy`) | Vite (`vite` + `@vitejs/plugin-vue`) — **must upgrade with Vue**; every entry maps to a Vite input |
| `store` | Vuex / Pinia / both | Pinia preferred; Vuex 4 acceptable bridge |
| `ui` | Element UI / Ant Design Vue 1.x / Vuetify 2 / other | Matching Vue3 library (e.g. Element Plus) |
| `test` | `@vue/test-utils`, Jest/Vitest, E2E | test-utils v2 + Vitest/Jest Vue3 config |
| `lint-ide` | eslint-plugin-vue, Vetur/Volar | Vue3 eslint rules + Volar / `vue-tsc` |
| `i18n-plugins` | vue-i18n; peer metadata; non-`vue-*` packages imported then registered via `Vue.use`; plugin/editor/grid name candidates | Vue3-compatible majors or explicit replacement |
| `composition-existing` | `@vue/composition-api`, Vue 2.7 `setup` usage | Remove bridge plugin on Vue3; no full rewrite |
| `blockers` | Packages with no Vue3 line, opaque/internal packages, unresolved plugin candidates | replace / fork / remove / defer decision |

## `blockers` vs dedicated subsystems (dedupe)

- If a Vue2-only package is already owned by a dedicated subsystem row
  (e.g. `element-ui` → `ui`, `vue-i18n` → `i18n-plugins`), do **not** also
  queue `blockers` for that same package.
- Set `blockers` risk to `n/a` (or list residuals only) and keep
  `queue_eligible=no` when every blocker package is covered elsewhere.
- Queue `blockers` only for residual packages that have **no** dedicated
  subsystem owner.

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

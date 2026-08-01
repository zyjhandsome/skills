# Subsystem inventory (default full-stack)

Every workspace packet must classify these subsystems. Missing detection →
`unknown` with evidence gap, not silent omit.

| Subsystem id | What to detect | Typical Vue3 target |
|---|---|---|
| `core-vue` | `vue` major/version, SFC compiler | `vue@3` + `@vue/compiler-sfc` |
| `router` | `vue-router` | `vue-router@4` |
| `build` | Vue CLI / Webpack / Vite | Vite (`vite` + `@vitejs/plugin-vue`) — **must upgrade with Vue** |
| `store` | Vuex / Pinia / both | Pinia preferred; Vuex 4 acceptable bridge |
| `ui` | Element UI / Ant Design Vue 1.x / Vuetify 2 / other | Matching Vue3 library (e.g. Element Plus) |
| `test` | `@vue/test-utils`, Jest/Vitest, E2E | test-utils v2 + Vitest/Jest Vue3 config |
| `lint-ide` | eslint-plugin-vue, Vetur/Volar | Vue3 eslint rules + Volar / `vue-tsc` |
| `i18n-plugins` | vue-i18n and other Vue plugins | Vue3-compatible majors |
| `composition-existing` | `@vue/composition-api`, Vue 2.7 `setup` usage | Remove bridge plugin on Vue3; no full rewrite |
| `blockers` | Packages with no Vue3 line | replace / fork / remove / defer decision |

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
| `queue_eligible` | `yes` if `risk` in `blocker|high` after path decided |

## Composition API rule

- `composition-existing`: analyze compatibility of **current** usage only.
- Do **not** estimate full Options→Composition rewrite effort.
- Packet must state:「Composition API 全仓重写：另立项，本次不评估工作量」.

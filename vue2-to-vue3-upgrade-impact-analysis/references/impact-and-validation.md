# Impact and validation

## Evidence priority

1. Lockfile + `package.json` declared versions (fact). **No lockfile** → record
   in §1 with `lockfile` wording and treat version reproducibility as elevated
   risk (still not a preflight hard block).
2. Config presence (`vue.config.js`, `vite.config.*`, babel, eslint)
3. Bounded source search via `profile_inventory.py`: filters / `Vue.filter`,
   `$listeners`, `.sync`, `new Vue(`, `Vue.use`, `slot-scope` / legacy `slot=`,
   event bus, router `addRoutes` / `*`, lifecycle destroy hooks. Also complete
   §10 `人工补搜检查` for residual gaps and non-`vue-*` blockers
   (`tui-editor`, editors, etc.).
4. Official docs URLs for the exact interval / library major
5. Inference — label explicitly

## Impact layers (report §5)

| Layer | Examples |
|---|---|
| 代码 | SFC API breaks, filters, functional components, render `h` |
| 配置 | alias `vue`→`@vue/compat`, Vite/CLI, env defines |
| 路由 | Router 3→4 history/mode, guards, `*` catch-all |
| 状态 | Vuex install → Vuex4 / Pinia module map |
| UI | Element UI→Plus (or peer UI) component/API/CSS |
| 测试 | test-utils v1→v2, mount options, E2E smoke value |
| 构建/部署 | Vite build output, publicPath/base, CI Node version |

## Validation matrix guidance

Prefer naming:

- Install/build commands **for the implementation stage** (do not run here)
- Smoke/E2E routes over deep unit rewrites when UT migration cost is high
- Visual regression for UI library majors
- Rollback = redeploy previous workspace release / revert upgrade branch

## Out of scope work

Full Composition API rewrite, design-system restyle unrelated to Vue3, backend
contract changes.

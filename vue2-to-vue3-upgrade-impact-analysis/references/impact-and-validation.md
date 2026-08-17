# Impact and validation

## Evidence priority

1. Lockfile + `package.json` declared versions (fact). Record the scanner's
   `lockfile_status: present|absent|unparsed` in §1. Anything except `present`
   keeps `batch_implementation_gate=frozen` (still not a preflight hard block).
2. Config presence (`vue.config.js`, `vite.config.*`, babel, eslint)
3. Bounded source search via `profile_inventory.py`: filters / `Vue.filter`,
   `$listeners`, `.sync`, `new Vue(`, `Vue.use`, `slot-scope` / legacy `slot=`,
   event bus, router `addRoutes` / `*`, lifecycle destroy hooks,
   `Vue.prototype.$*` definitions/consumers, `globalProperties`, and packages
   registered through `Vue.use`. Also complete §10 `人工补搜检查` for residual
   gaps and non-`vue-*` blockers (`tui-editor`, internal plugins, editors, etc.).
4. Official docs URLs for the exact interval / library major — start from
   `official-docs-index.md` (EOL + two-layer modification model + canonical
   hubs + high-signal checklist), then fetch the linked page; do not invent
   breaks from memory. Static checklist = candidates; name Migration Build
   warnings / per-component `compatConfig` as the dynamic backlog (do not run)
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
- Tailwind prefix/Preflight/important/content/safelist and dynamic classes;
- primary search + table page and secondary table when mixed;
- Teleport/append target, overflow/z-index and theme inheritance;
- baseline status and required visual states.

Write these as the §5 `ui_visual_risk` block defined by `report-contract.md`.
Keep it self-contained: record required visual states and a generic next action;
do not require, invoke, or name another Skill.

## Out of scope work

Full Composition API rewrite, design-system restyle unrelated to Vue3, backend
contract changes.

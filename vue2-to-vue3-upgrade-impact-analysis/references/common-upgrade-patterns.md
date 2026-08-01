# Common upgrade patterns

## Pattern: Vue CLI → Vite with Vue3

- Detect `@vue/cli-service` / `vue.config.js`
- Name `webpack-to-vite` + Vite Vue3 plugin docs
- Build is **in_scope** and usually `high` or `blocker` if stuck on Webpack-only plugins

## Pattern: Element UI

- `element-ui` has no Vue3 line → `ui` risk `blocker` or `high`
- Name `gogocode-element` + Element Plus migration / breaking-change discussion
- Often cannot be sliced; call out「UI 大步」in path notes

## Pattern: Vuex

- Vuex 4 supports Vue3 (install API change) — bridge OK
- Prefer Pinia as long-term recommendation; coexistence possible during migration
- Do not force Pinia rewrite if Vuex4 unblocks cutover — record residual

## Pattern: Filters / $listeners / .sync / event bus

- Mechanical or semi-mechanical; name `gogocode-vue` or `vue-upgrade-tool`
- Event bus `new Vue()` → mitt / provide-inject / store (describe only)

## Pattern: Already on Vite + Vue2

- `vite-plugin-vue2` is transitional; Vue3 uses `@vitejs/plugin-vue`
- Still recommend dropping Vue2 Vite plugin in the same upgrade batch

## Pattern: Microfrontend host

- If qiankun / Module Federation detected, evaluate `microfrontend-coexist`
  only when single-app cutover is impossible

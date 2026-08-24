# Common upgrade patterns

Name the matching recipe; never run it in this skill. Record residuals in §10.

## Pattern: Vue CLI → Vite with Vue3

- Detect `@vue/cli-service` / `vue.config.js`
- Name `webpack-to-vite` + Vite Vue3 plugin docs
- Build is **in_scope** and usually `high` or `blocker` if stuck on Webpack-only plugins

## Pattern: Element UI

- `element-ui` has no Vue3 line → `ui` risk `blocker` or `high`
- Name `gogocode-element` + Element Plus migration / breaking-change discussion
- Often cannot be sliced; call out「UI 大步」in path notes
- Set `visual_acceptance_required=yes` and fill `ui_visual_risk`

## Pattern: Vuex

- Vuex 4 supports Vue3 (install API change) — bridge OK
- Prefer Pinia as long-term recommendation; coexistence possible during migration
- Do not force Pinia rewrite if Vuex4 unblocks cutover — record residual
- Name `manual-pinia-or-vuex4`

## Pattern: Filters / $listeners / .sync / event bus

- Mechanical or semi-mechanical; name `gogocode-vue` or `vue-upgrade-tool`
- Event bus `new Vue()` → mitt / provide-inject / store (describe only)

## Pattern: `Vue.prototype.$*`

- Inventory every definition and `this.$*` consumer in §10 (separate rows)
- Name the Vue3 target: `app.config.globalProperties` and/or `provide/inject`
- Do not treat a one-line “has globals” note as complete

## Pattern: External global script + mount timing

- Detect HTML/dynamic script loaders together with `window.X` / `globalThis.X`
  readiness or instance-registry consumers
- These are bare runtime globals, not npm packages and not `Vue.use` plugins
- Name `manual-external-global-script`; record loader ownership, URL/base,
  polling timeout/cleanup, host DOM selector and every consumer
- Static review is necessary but cannot close instance-registration timing:
  require a post-cutover runtime assertion on each applicable lane (loaded,
  ready, instance retrievable, minimal behavior round-trip)
- Auth or routing that prevents the real component from mounting leaves the
  assertion unexecuted; it does not convert it into a static pass

## Pattern: Class components / decorators

- Detect `vue-class-component`, `vue-property-decorator`, `vuex-class`
- Name `manual-class-api`; Options rewrite is **not** a Composition-API 全仓重写
- If the only path is a full `<script setup>` rewrite, mark that rewrite「另立项」and keep this packet on behavior-preserving conversion

## Pattern: `vue-i18n` v8

- v8 `Vue.use(VueI18n)` / `this.$i18n` → v9 `createI18n`
- Name `manual-i18n`; decide legacy mode vs API update; keep locale fallback in §8

## Pattern: Functional components / JSX

- Vue 2 `{ functional: true }` / template `functional` and JSX render functions break
- Name `gogocode-vue` and/or `manual-jsx`; record `h` import and fragment behavior

## Pattern: Already on Vite + Vue2

- `vite-plugin-vue2` is transitional; Vue3 uses `@vitejs/plugin-vue`
- Still recommend dropping Vue2 Vite plugin in the same upgrade batch

## Pattern: Microfrontend host

- If qiankun / Module Federation detected, evaluate `microfrontend-coexist`
  only when single-app cutover is impossible

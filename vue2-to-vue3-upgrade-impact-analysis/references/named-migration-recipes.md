# Named migration recipes — name, never run

Stage A **must name** applicable recipes with official/source URLs. Stage A
**never runs** them (no codemod write, no install, no temp-dir transform).
Prefer compatibility / migration URLs from `official-docs-index.md` when
citing Vue core, Router, Vuex/Pinia, test-utils, or Element Plus.

Canonical ids below are preferred. Extra kebab-case ids (for example
host-port local names) are allowed in the packet; they still need a §8 row.

Each named recipe must appear in §8 with an **implementation-stage** command
shape and what a failure proves. Do not run those commands here.

## Canonical recipes

| Recipe id | Tool | When to name | Typical globs | Implementation-stage command shape (do not run) | Human must accept |
|---|---|---|---|---|---|
| `vue-compat` | `@vue/compat` | Default `compat-big-bang` | `package.json`, `vue.config.js` / `vite.config.*`, `main.js` | alias `vue` → `@vue/compat`; set `compatConfig`; build | compat removal date / exit condition |
| `gogocode-vue` | `gogocode-plugin-vue` + `gogocode-cli` | Mechanical API/template breaks | `src/**/*.{vue,js,ts}` | `gogocode` vue plugin over `src` (then diff review) | every generated diff |
| `gogocode-element` | `gogocode-plugin-element` | Element UI → Element Plus | `src/**/*.vue`, Element imports | `gogocode` element plugin; then visual sample pages | component/CSS leftovers |
| `manual-vant4` | Vant official Vue 3 line | Vant 2 is used by a Vue2 mobile entry | mobile entry, Vant imports, mobile views and styles | move Vant 2 registrations/imports to the current Vue3-compatible Vant line; compare mobile states | component/API/style differences and browser floor |
| `vue-upgrade-tool` | `vue-upgrade-tool` (vue-metamorph) | JS/TS/SFC/test-utils codemods | `src/**/*.{vue,js,ts}`, tests | `vue-upgrade-tool` then manual verify | every change |
| `vue-codemod` | `vuejs/vue-codemod` | Older official scripts | same as above | only if vue-upgrade-tool does not fit | every change |
| `webpack-to-vite` | `originjs/webpack-to-vite` | Vue CLI/Webpack → Vite | `vue.config.js`, `public/`, CI | scaffold Vite config; human-accept before replacing CLI | `vite.config` / env / `base` |
| `manual-cli5-webpack5` | Vue CLI 5 / webpack 5 docs | CLI 4 project whose custom webpack surface should stay stable during Vue runtime cutover | `package.json`, `vue.config.js`, loaders/plugins | upgrade CLI packages/loaders/plugins without changing entry topology; preserve `pages`, aliases, chunks and assets | CLI is maintenance-only; record a separate future Vite decision |
| `eslint-vue3` | `eslint-plugin-vue` Vue3 rules | Lint after engine move | `.eslintrc*`, `eslint.config.*` | enable Vue3 rule set; fail on leftovers | false-positive suppressions |
| `manual-router4` | Vue Router 4 migration guide | `vue-router` 3 present | `src/router/**` | `createRouter` / `createWebHistory`; replace `*` catch-all | 404 and guard order |
| `manual-pinia-or-vuex4` | Pinia / Vuex 4 docs | Store present | `src/store/**` | Vuex 4 install API, or map modules to Pinia | do not force Pinia if Vuex4 unblocks |
| `manual-i18n` | `vue-i18n` v9 docs | `vue-i18n` v8 / legacy API | `src/i18n/**`, `$t` call sites | v8→v9 createI18n / legacy mode decision | locale fallback |
| `manual-plugin-audit` | package peer metadata + upstream source | plugin readiness is unknown or plugin injects `$*` globals | plugin registration, injected globals, every consumer | replace, fork, or adapt one plugin at a time after an evidence-backed decision | ownership and behavior-parity oracle per plugin |
| `manual-class-api` | class-component / decorator docs | `vue-class-component` / `vue-property-decorator` | `src/**/*.{vue,ts}` | Options rewrite or Vue 3 class interop | decorator leftovers |
| `manual-jsx` | Vue 3 JSX plugin docs | `jsx` / `h` render returning arrays | `src/**/*.{jsx,tsx,js}` | `@vitejs/plugin-vue-jsx` + `h` import | fragment / `class` vs `className` |

Example phrasing in packet:

> 命名配方：`vue-compat` + `gogocode-element`（URL…）。**本技能不执行。**

Forbidden in Stage A: `npx vue-upgrade-tool`, `gogocode -s`, `npm i vue@3`,
alias edits, running transforms into `src-out`.

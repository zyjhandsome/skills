# Named migration recipes — name, never run

Stage A **must name** applicable recipes with official/source URLs. Stage A
**never runs** them (no codemod write, no install, no temp-dir transform).

| Recipe id | Tool | When to name | Notes |
|---|---|---|---|
| `vue-compat` | `@vue/compat` | Default `compat-big-bang` | Official migration build; set removal date |
| `gogocode-vue` | `gogocode-plugin-vue` + `gogocode-cli` | Mechanical API/template breaks | https://github.com/thx/gogocode |
| `gogocode-element` | `gogocode-plugin-element` | Element UI → Element Plus | Element Plus migration page |
| `vue-upgrade-tool` | `vue-upgrade-tool` (vue-metamorph) | JS/TS/SFC/test-utils codemods | Verify every change manually |
| `vue-codemod` | `vuejs/vue-codemod` | Older official scripts | Lower priority if vue-upgrade-tool fits |
| `webpack-to-vite` | `originjs/webpack-to-vite` | Vue CLI/Webpack → Vite | Scaffold only; human accept config |
| `eslint-vue3` | `eslint-plugin-vue` Vue3 rules | Lint after engine move | Static leftover detection |
| `manual-router4` | Vue Router migration guide | Always when vue-router 3 present | `createRouter` / `history` |
| `manual-pinia-or-vuex4` | Pinia / Vuex 4 docs | Store present | Pinia preferred long-term |

Example phrasing in packet:

> 命名配方：`vue-compat` + `gogocode-element`（URL…）。**本技能不执行。**

Forbidden in Stage A: `npx vue-upgrade-tool`, `gogocode -s`, `npm i vue@3`,
alias edits, running transforms into `src-out`.

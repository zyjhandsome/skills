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
| `gogocode-vue` | `gogocode-plugin-vue` + `gogocode-cli` (**unmaintained**) | Mechanical API/template breaks | `src/**/*.{vue,js,ts}` | `gogocode` vue plugin over `src` (then diff review) | every generated diff |
| `gogocode-element` | `gogocode-plugin-element` (**unmaintained**, still `0.0.x`) | Element UI → Element Plus | `src/**/*.vue`, Element imports | `gogocode` element plugin; then visual sample pages | component/CSS leftovers |
| `manual-vant4` | Vant official Vue 3 line | Vant 2 is used by a Vue2 mobile entry | mobile entry, Vant imports, mobile views and styles | move Vant 2 registrations/imports to the current Vue3-compatible Vant line; compare mobile states | component/API/style differences and browser floor |
| `vue-upgrade-tool` | `vue-upgrade-tool` (vue-metamorph) | JS/TS/SFC/test-utils codemods | `src/**/*.{vue,js,ts}`, tests | `vue-upgrade-tool` then manual verify | every change |
| `vue-codemod` | `vuejs/vue-codemod` | Older official scripts | same as above | only if vue-upgrade-tool does not fit | every change |
| `webpack-to-vite` | `@originjs/webpack-to-vite` (npm scope required; the bare name `webpack-to-vite` is not a published package; **unmaintained**) | Vue CLI/Webpack → Vite | `vue.config.js`, `public/`, CI | scaffold Vite config; human-accept before replacing CLI | `vite.config` / env / `base`; every generated option re-checked against the **selected** Vite major |
| `manual-cli5-webpack5` | Vue CLI 5 / webpack 5 docs | CLI 4 project whose custom webpack surface should stay stable during Vue runtime cutover | `package.json`, `vue.config.js`, loaders/plugins | upgrade CLI packages/loaders/plugins without changing entry topology; preserve `pages`, aliases, chunks and assets | CLI is maintenance-only; record a separate future Vite decision |
| `eslint-vue3` | `eslint-plugin-vue` Vue3 rules | Lint after engine move | `.eslintrc*`, `eslint.config.*` | enable Vue3 rule set; fail on leftovers | false-positive suppressions |
| `manual-router4` | Vue Router 4 migration guide | `vue-router` 3 present | `src/router/**`, **plus every `push`/`replace` call site** | `createRouter` / `createWebHistory`; replace `*` catch-all; drop the router-prototype error-swallowing patch and check every name-target navigation for the params its route requires | 404 and guard order; each navigation that the old error swallowing was hiding |
| `manual-pinia-or-vuex4` | Pinia / Vuex 4 docs | Store present | `src/store/**` | Vuex 4 install API, or map modules to Pinia | do not force Pinia if Vuex4 unblocks |
| `manual-i18n` | `vue-i18n` v8→v9 migration guide (document); installed major resolved separately | `vue-i18n` v8 / legacy API | `src/i18n/**`, `$t` call sites | v8→v9 `createI18n` / legacy mode decision; then confirm the installed major's own `engines.node` in the Node matrix | locale fallback; Node floor raised by the chosen major |
| `manual-plugin-audit` | package peer metadata + upstream source | plugin readiness is unknown or plugin injects `$*` globals | plugin registration, injected globals, every consumer | replace, fork, or adapt one plugin at a time after an evidence-backed decision | ownership and behavior-parity oracle per plugin |
| `manual-external-global-script` | loader source + external script contract | HTML/dynamic script injection is correlated with bare-global readiness or instance polling | loader URL/base, host DOM selector, polling lifecycle, global registry and every consumer | preserve or adapt the loader after runtime cutover; verify loaded → ready → instance → behavior round-trip on every applicable lane | static review never closes mount/registration timing; auth-walled execution remains unverified |
| `manual-class-api` | class-component / decorator docs | `vue-class-component` / `vue-property-decorator` | `src/**/*.{vue,ts}` | Options rewrite or Vue 3 class interop | decorator leftovers |
| `manual-jsx` | Vue 3 JSX plugin docs | `jsx` / `h` render returning arrays | `src/**/*.{jsx,tsx,js}` | `@vitejs/plugin-vue-jsx` + `h` import | fragment / `class` vs `className` |

**`unmaintained` tag.** Naming an unmaintained tool stays allowed — an official
migration page may still point at it — but the packet must carry the tag, oblige
human review of every generated diff, and must not treat the output as correct
for the *selected* target major. A scaffolder written against an older major
emits options that the current major has renamed or dropped. Prefer an actively
maintained equivalent whenever one covers the same interval.

The Tool column names the **document or transform**, not the version you will
install; installed majors are resolved per `subsystem-inventory.md`.

## Recipe intersections

Recipes are named per subsystem, but transforms are not partitioned by
subsystem: two of them can rewrite the same call sites, and the defect lives in
the intersection that neither owns. Declare every such pair in
`recipe_constraints[].overlaps_with` (mutually) and give the intersection its
own §8 row. Known intersection shapes:

| Pair | Shared call sites | What the intersection row must prove |
|---|---|---|
| `gogocode-vue` × `gogocode-element` (or any core codemod × kit codemod) | `.sync` / `v-model` bindings, slot syntax, and icon props on kit components | that each rewritten binding names a prop the **target kit** actually declares — a core codemod emits `v-model:<old-prop>`, which is valid Vue3 and wrong for a renamed kit prop |
| kit codemod × `eslint-vue3` | templates the codemod rewrote | that unresolved components and unknown elements fail lint, so codemod artifacts such as an upper-cased HTML tag (`<p>` → `<P>`, which Vue3 resolves as a component) do not reach a green build |
| template codemod × component registration | `components` option / global registration | that every element the rewritten template references is registered — a codemod that swaps an icon or component in the template does not add the corresponding registration |

## Codemod residual audit

Any recipe whose Tool column is a codemod carries a standing audit obligation in
§8, independent of the diff review. Name these as check classes, not as a bug
list — the classes are stable, while any given tool's defects are not:

- **Re-parse the output.** The transform's own output must compile and lint
  under the target toolchain, including template identifier casing and
  unresolved components.
- **Rewrites are partial by default.** For every API the codemod handles in one
  syntactic form, check the other forms (template pipe vs `$options.filters`
  object access; `.sync` vs explicit `:prop` + `@update:prop`).
- **Cross-file effects are out of a codemod's reach.** Registration, parent
  bindings and prop identity in another package are not visible to an AST
  transform over a single file.
- **Codemod output is not evidence of behavior.** A green build over
  codemod-rewritten source proves the transform produced parseable code, nothing
  more; the interaction assertions still have to run.
- **Deprecated on arrival.** A codemod maps an old API to the target's nearest
  equivalent, and the target major sometimes already deprecates that
  equivalent — a tool pinned at `0.0.x` cannot know which. The output is
  correct, builds clean, looks identical, and warns on every mount, once per
  call site the transform touched. Resolve the target's own deprecation list
  before naming the recipe, and dispose the class in one pass under the console
  taxonomy in `impact-and-validation.md`; chasing the warnings one page at a
  time after verification is how this class normally gets found.
- **Removing a suppression is itself a change.** Codemods delete or invalidate
  the shims that were muffling failures (a patched router prototype, a
  `.catch` swallow, a global handler keyed on an old API). The diff looks like
  a deletion of dead code and behaves like the removal of a filter over the
  whole feature it guarded.

Observed defects from real runs may be appended below this section as a dated,
evidence-linked appendix. They are hints, not a checklist: verify against the
tool version actually selected before relying on any of them.

**Admission rule for that appendix.** Accept an entry only when it carries a
concrete evidence pointer — the file or route where it was observed, the command
that exposed it, and the observation date — plus the tool version in use at the
time. Reject anything sourced from recollection, from a summary that no longer
names where it happened, or from another project's hearsay: an appendix of
unverifiable folklore makes packets longer without making any of them safer, and
readers cannot tell which lines still apply.

Example phrasing in packet:

> 命名配方：`vue-compat` + `gogocode-element`（URL…）。**本技能不执行。**

Forbidden in Stage A: `npx vue-upgrade-tool`, `gogocode -s`, `npm i vue@3`,
alias edits, running transforms into `src-out`.

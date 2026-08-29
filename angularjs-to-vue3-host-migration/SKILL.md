---
name: angularjs-to-vue3-host-migration
description: Use when assessing, designing, or verifying migration of AngularJS 1.x/jQuery/JSP/Thymeleaf mixed legacy pages into an existing Vue 3 host repository. Supports dual-repo source-vs-host comparison, page-level migration units, business-flow and variable-chain reconstruction, host-stack gap analysis, URL/permission/API rollback gates, and evidence reports for projects like hiapm -> apmweb3. Not for greenfield Vue 3 creation unless no host repository exists.
---

# AngularJS To Vue 3 Host Migration

Use this skill to produce evidence and page-level designs for moving AngularJS 1.x, jQuery, JSP, Thymeleaf, and server-rendered page islands into an existing Vue 3 host. Default to **hosted migration**: source repo A supplies legacy behavior; host repo B owns the final entry, shell, auth, build, API conventions, components, state, i18n, proxy, and runtime gates.

This skill is independent. Do not depend on `delivery-*` or other migration skills. Reuse ideas only by restating the needed rule here.

## Modes

- `assess`: compare source A and Vue3 host B, identify overlaps, gaps, risks, and candidate migration units.
- `design`: produce an implementation-ready page/user-behavior design for one specified migration unit.
- `verify`: define and/or run parity checks for behavior, permission, URL, API, display contract, visual evidence, rollback, and host build gates.
- `greenfield`: use only when the user explicitly has no Vue3 host. This is not the default path.

`design` accepts `profile=repair` when the host already has the unit's entry and the goal is source parity repair. See Shell-Page Repair in `references/hosted-vue3-migration-method.md`.

Default mode is `assess` unless the user names a page or asks for implementation design/verification.

## Required Inputs

For hosted migration, require:

- source repo A path, such as `hiapm`
- host repo B path, such as `apmweb3`
- migration unit when doing `design` or `verify`: page, URL, route, menu item, or user behavior

If only one repo is available, perform source-only assessment and state that host landing design cannot be completed.

## Workflow

1. Confirm mode, source repo A, host repo B, and optional migration unit.
2. Prefer Codebase Memory when available: index both repos, use graph search/trace/snippets for code discovery, then fall back to `rg` for templates, literals, configs, and vendor-excluded scans.
3. Load `references/hosted-vue3-migration-method.md` before any hosted migration assessment or design.
4. Load `references/jquery-vue3-business-logic-analysis.md` and `references/business-logic-variable-flow-analysis.md` when analyzing a concrete page/user behavior.
5. Do not load `references/angularjs-vue3-migration-method.md` on the hosted path. Load it only in `greenfield` mode, or when the user confirms no Vue3 host exists.
6. First read host B conventions before proposing landing code:
   - MPA/SPA entry layout, router, route meta, auth/permission, axios/API client, state store, component library, i18n, proxy, env config, lockfile, Node baseline, lint/build/test gates.
   - Host compile overlay: `lintOnSave`, TS `noImplicitAny`/`strict`, Prettier/EditorConfig indentation, dev-server error-overlay scope, and actual `node -v` versus the declared baseline.
7. Build a source A page-entry inventory before deep scanning:
   - JSP, Thymeleaf, HTML, server templates, page-level `ng-app`/`ng-controller`, AngularJS modules/controllers/services/directives/filters, jQuery entry functions, Ajax, DOM operations, plugins.
   - Exclude dependency and evidence noise: `.git`, `node_modules`, `dist`, `build`, `target`, `coverage`, `reports`, `evidence`, `openspec`, `test`, `tests`, `e2e-tests`, `vendor`, `vendors`, `lib`, `libs`, `locale`, `locales`, generated bundles, minified files, `*.spec.*`, `*.test.*`, `*.e2e.*`.
8. Produce A/B page comparison:
   - `unmigrated`, `partial-overlap`, `already-migrated`, `host-page-only`, `host-component`, `host-shell`, `unknown`.
   - Include old URL/template and new host entry/route when evidence exists.
   - Treat filename/path matches as candidates only. Include match basis, candidate score, and whether human correction is required. Never mark `already-migrated` from filename matching alone.
   - Distinguish host pages/entries from reusable components and shell files. Do not treat every `.vue` file or root `index.html` as a page.
9. Produce URL and entry mapping:
   - Prefer Java/Spring route annotations, menu config, server template returns, MPA `getPages()`/`src/pages/*/*.ts`, and host route/menu evidence over guessed file paths.
   - Mark file-derived URL guesses as low confidence until backed by route/menu/MPA evidence.
10. Choose migration units as independently switchable pages or user behaviors, not whole-repo batches.
11. For each selected unit, produce a page closure:
   - source templates/fragments/scripts/controllers/services/APIs/assets, including page CSS and the shared CSS/sprite/plugin styles it depends on
   - display-contract matrix rows for every source region of the unit
   - page-init and side-effect list: `angular.module(...).run`, controller init, `$timeout`/`setInterval`, first-paint `$http`, default filter values
   - host files/components/stores/API modules to reuse or change
   - old URL -> new entry mapping
   - permissions/session assumptions
   - API contracts and response-code handling
   - rollback switch and rollback condition
   - parity checks and unresolved evidence
12. When the unit is `partial-overlap` because a host shell/page already exists, treat it as unmigrated until a display-contract matrix exists. Layout presence is not migration evidence: data, copy, widget shape, defaults, and CSS are separately verifiable and usually missing. One or two filled click flows never release an existing shell page.
13. Generate evidence baseline artifacts when requested:

```bash
python scripts/generate_migration_plan.py assess \
  --project-name "hiapm-to-apmweb3" \
  --source-repo "D:/path/hiapm" \
  --host-repo "D:/path/apmweb3" \
  --output-dir reports/angularjs-vue3-migration
```

14. Treat script output as evidence baseline only. Do not treat generated tables as implementation design until reviewed against source and host code. Header-only FLOW/VAR/CHAIN contracts are not design-ready, and generated tables never substitute for the display-contract matrix.

## Scan Commands

Use Codebase Memory first. Use these `rg` commands only as fallback or for non-code/template evidence:

```bash
rg -n --glob '!{node_modules,dist,build,target,coverage,reports,evidence,openspec,test,tests,e2e-tests,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' --glob '!*.spec.*' --glob '!*.test.*' "ng-app|ng-controller|ng-repeat|ng-model|ng-src|ng-click|ng-change|angular\.module|\.controller\(|\.component\(|\.directive\(|\.service\(|\.factory\(|\.filter\(" <source>
rg -n --glob '!{node_modules,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' "\$scope|\$rootScope|\$watch|\$emit|\$broadcast|\$http|\$resource|\$q" <source>
rg -n --glob '!{node_modules,dist,build,target,coverage,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' "\$\(document\)\.ready|\$\(function|\.on\(|\.click\(|\.change\(|\.submit\(|\$\.ajax\(|\.val\(|\.html\(|\.append\(" <source>
rg -n --glob '!{node_modules,dist,build,target,coverage,reports,evidence,openspec,test,tests,e2e-tests,vendor,vendors,lib,libs,locale,locales}/**' --glob '!*.min.*' --glob '!*.spec.*' --glob '!*.test.*' "th:(text|if|each|href|src|class|object|field|value|action|replace|insert|fragment|with|unless|switch|case|include|attr)\b|<%@|jsp:|session\.|request\.|data-|window\.|location\.href|setInterval\(" <source>
rg -n "createApp|createRouter|defineStore|axios|i18n|proxy|vite|webpack|scripts/getpage|element-plus|@opentiny/vue|ant-design-vue|naive-ui|pinia|jquery" <host>
```

These commands discover candidates only. Read definitions, callers, templates, callbacks, API wrappers, and final consumers before drawing conclusions.

## Hosted Migration Rules

- Reuse host B shell, auth/session, router/MPA entry, API client, i18n mechanism, state pattern, env, proxy, and lint/build/test gates.
- Do not use host B table/select/modal components to replace a source page's custom widget unless the interaction is equivalent: same input affordance, same selection/read-only semantics, same default value, same validation and limits, same submit/format shape. When the source specifies geometry, dialog width and centering are also part of the contract. Host components are for equivalent generic chrome such as buttons, inputs, and overlays.
- Do not copy source A JSP/Thymeleaf global layout into host B. You **must** still extract the page-level CSS closure, including the shared `common.css` / sprite / plugin styles the page assumes, and reproduce it host-native and page-scoped in B. Never assume source global styles still exist.
- Land source i18n text verbatim. Source `zh.json` / `en.json` entries are the acceptance baseline; do not paraphrase, shorten, or change punctuation. Any deviation needs its own matrix row with reason and approver.
- Every visible number, list, label, and badge needs an API plus a field formula. Sums, joins, select-all titles, and derived counters belong in the chain tables, not in prose.
- Treat an existing host shell page as `partial-overlap` and produce a display-contract matrix. One or two click flows do not release it.
- A slice is complete only when the host entry mounts it, it calls its API, and the user can reach it in the browser. Adding `lib/` helpers or component files alone is not complete.
- Do not default to creating a Vue3 skeleton. Use greenfield Vite/create-vue only when no host exists.
- Do not replace host B runtime stack unless the gap analysis proves a blocker and the user approves.
- Bind evidence to source and host revisions. If either repo changes, affected evidence and design decisions expire.
- Keep FLOW/VAR/CHAIN tables scoped to the selected page/user behavior. Do not emit whole-repo empty chains.

## Display Contract

One matrix row per source region of the unit, with a stable `DISP-<unit>-<region>-<n>` ID. Columns and status enums are defined in `references/hosted-vue3-migration-method.md`.

Rules:

- The matrix is one persisted artifact reused across `assess`, `design`, and `verify`. Incremental repairs update existing rows instead of starting a new analysis round.
- Display-contract parity is code-comparable and mandatory. It is separate from pixel/screenshot measurement, and `manual-only` never excuses copy, widget shape, defaults, geometry, or field formulas.
- DOM presence is not visibility. For rows marked as visible copy or visible numbers, confirm the element is actually visible at runtime, since host or shared CSS such as `font-size: 0` can hide correct markup.

## Host Compile Overlay

Read these host facts before landing code, and record them as parity requirements:

- `lintOnSave`, dev-server overlay scope, TS `noImplicitAny`/`strict`, Prettier/EditorConfig indentation.
- Actual `node -v` versus host-declared Volta/`.nvmrc`/`engines.node`. A test or build run on a different Node is not verification evidence.
- Do not reformat, retype, or otherwise "fix along the way" legacy files outside approved scope. Host `lintOnSave` can turn an unrelated dirty file into a full-page overlay; record those files as residuals with an owner instead of editing them.
- A compile failure on the current unit's entry is blocking. A repo-wide overlay from unrelated files is a residual, and neither may be reported as a healthy dev server.

## Output Contracts

User-facing evidence reports, copied table contracts, and filled FLOW/VAR/CHAIN rows default to Simplified Chinese. Keep status enums, IDs (`FLOW-ID`, `unmigrated`, `not-ready: empty-contract`), paths, commands, URLs, and CSV field keys in English.

Field-level column definitions, status enums, and table headers live in `references/hosted-vue3-migration-method.md`. Do not restate them here or in orchestration prompts. This section only lists what must exist for a mode to pass.

### Assess

- source/host revision, repo acquisition status and warnings, git hygiene summary
- host stack summary including host compile overlay
- source page-entry inventory, A/B page comparison with match basis and human-correction flags
- URL / entry mapping backed by Java route, menu, template return, or MPA entry
- vendor-excluded coupling counts, suggested first units, gaps, risks
- for any `partial-overlap` unit: a first-pass display-contract matrix with `B 现状` filled, so shell presence is not mistaken for migration

### Design

For one page or user behavior:

- page closure including CSS closure
- display-contract matrix with stable IDs
- page-init and side-effect list
- source i18n text table with any approved deviations
- behavior flow plus variable/API chains, including a field formula for each visible number/list
- host reuse/change/create decisions, URL mapping, permission/session/API parity, rollback switch and condition
- vertical slices whose completion criterion is entry mounted and user-reachable
- design-ready gate: page closure, display-contract matrix, page-init list, i18n table, CSS closure table, 1-2 filled core flows, material chains, host decisions, URL mapping, permission/API/rollback draft. A shell page missing any one of these is `not-ready`.

### Verify

- behavior, page-init, permission, URL, API, runtime, rollback checks
- display-contract parity: matrix row by row, code-comparable, mandatory, with runtime visibility confirmed for visible copy and numbers
- entry-wiring parity: each slice is mounted, called, and reachable
- visual measurement parity: screenshots/measurements, otherwise `manual-only`. `manual-only` here does not exempt any display-contract row.
- completion authority: domain verify evidence cannot by itself declare migration complete; require Delivery verified evidence, current host revision, and no blocking residuals

## Bundled Resources

- `references/hosted-vue3-migration-method.md`: hosted dual-repo migration method, display-contract matrix, and report contracts. Load on every hosted run.
- `references/angularjs-vue3-migration-method.md`: AngularJS construct mapping and greenfield fallback guidance. Not loaded on the hosted path; load only in `greenfield` mode or when no host exists.
- `references/jquery-vue3-business-logic-analysis.md`: jQuery business logic analysis method and table contracts.
- `references/business-logic-variable-flow-analysis.md`: evidence-backed business-flow and variable-chain tracing contracts.
- `scripts/generate_migration_plan.py`: generates dual-repo evidence baseline artifacts for `assess`, `design`, or `verify`.

# Hosted AngularJS/JSP/jQuery To Vue3 Migration Method

## Position

Default to migrating into an existing Vue3 host repository. The host owns the final entry, shell, auth, routing or MPA entry model, API client, state, component library, i18n, proxy, build, lockfile, Node baseline, and test gates.

Create a new Vite/create-vue project only when no host exists.

## Report Language

User-facing evidence reports and copied table contracts default to Simplified Chinese. Keep status enums, IDs, paths, commands, URLs, and CSV field keys in English.

## Inputs

For hosted migration, collect:

| Input | Required For | Notes |
|---|---|---|
| Source repo A | assess/design/verify | Legacy AngularJS/jQuery/JSP/Thymeleaf code. |
| Host repo B | assess/design/verify | Existing Vue3 final export/entry. |
| Migration unit | design/verify | Page, route, menu item, URL, or user behavior. |
| Source revision | all source-based outputs | Commit or timestamp. |
| Host revision | all host-based outputs | Commit or timestamp. |

If either revision changes, mark related evidence and design decisions stale.

## Repo Acquisition And Revision Binding

A clone/fetch command failure is not automatically terminal. Continue only when the final repository path is a valid git worktree and HEAD is readable.

Record acquisition evidence:

| Field | Meaning |
|---|---|
| repo role | source or host |
| repo path | final path used by the analysis |
| acquisition status | cloned, existing-git-repo, clone-warning-existing-git-repo, failed |
| acquisition warning | command failure such as exit 128, SSL workaround, retry note |
| revision | `git rev-parse --short HEAD` |
| dirty entries | current `git status --porcelain` count |
| usable for stage | yes only when git repo and revision are readable |

Do not make `sslVerify=false` a default strategy. If it was used during diagnosis, record it as a warning and bind the final evidence to the reused repository revision.

## Git Hygiene Gate

Before implementation planning, execution, verification, commit, or completion claims, review git status separately for source A and host B.

Rules:

- A must remain read-only; source changes require review and usually invalidate evidence.
- B may change only during the approved execute stage and only inside approved scope.
- `node_modules`, dependency caches, build outputs, coverage, `dist`, `build`, `target`, `vendor`, and generated bundles must not enter intended commits.
- `src/` clean is useful but does not prove the whole repository is clean. Distinguish business clean from repo clean.
- Lockfile changes require explicit explanation: approved dependency change, package-manager resolution drift, or accidental install noise.
- If dependency/cache/build noise appears, record whether it was aborted, cleaned, or still blocking.

## Modes

### assess

Goal: decide what can be migrated and in what order.

Required outputs:

- host stack summary, including host compile overlay
- source page-entry inventory
- A/B page comparison
- coupling counts excluding vendor
- recommended first migration units
- gaps and risks
- first-pass display-contract matrix for every `partial-overlap` unit, with `B 现状` filled

### design

Goal: make one migration unit ready for implementation.

Required outputs:

- page closure, including CSS closure
- display-contract matrix with stable IDs
- page-init and side-effect list
- source i18n text table
- source behavior/data/API chains, with a field formula for every visible number/list
- reuse/change/create decisions in host
- old URL to new entry mapping
- permission/session/API parity contract
- rollback switch and condition
- vertical slices whose completion criterion is entry mounted and user-reachable
- verification checklist
- unresolved evidence

### verify

Goal: prove migrated behavior is equivalent enough to release or identify gaps.

Required outputs:

- behavior, permission, URL, API, runtime, rollback checks
- display-contract parity, row by row, with runtime visibility confirmed for visible copy and numbers
- entry-wiring parity per slice
- visual measurement evidence only when screenshots or measurements exist
- manual-only label when visual measurement is missing, which never exempts a display-contract row

## Host-First Discovery

Read host B before designing landing code:

| Host Area | Evidence To Capture |
|---|---|
| Entry model | MPA entries, SPA router, route records, lazy pages, menu registration. |
| Build | Vite, Vue CLI, Webpack, Rollup, custom scripts, env files. |
| Runtime | Vue version, Node engines, lockfile, package manager. |
| API | axios/fetch wrapper, interceptors, base URL, timeout, error normalization. |
| Auth/session | route guards, token/cookie/session use, 401/403 handling, refresh/logout. |
| State | Pinia, Vuex, composables, globals, cache. |
| UI | component library, table/form/modal/date/upload/chart wrappers. |
| i18n | vue-i18n or host-specific translation helper. |
| Proxy/env | dev proxy, gateway path, env variables. |
| Tests | lint/build/test scripts, Playwright/Cypress/Vitest/Jest gates. |

Do not override host conventions unless the gap analysis proves they cannot support the page and the user approves a host change.

Host discovery must include common hosted-MPA details:

- `volta.node`, `.nvmrc`, `.node-version`, and `engines.node`
- `scripts/getpage.js`, `src/pages/*/*.ts`, HTML entries, and page-specific boot files
- `@opentiny/vue`, Element Plus, and any dual component-library setup
- host-side jQuery usage, even in a Vue3 repository
- axios/login store/cookie/gateway/session bridge conventions

## Source Page Inventory

Find page entries first, then trace inward.

Source entry candidates:

- `.jsp`, `.jspx`, `.html`, `.htm`, `.ftl`, `.vm`
- Thymeleaf markers: `th:*`, `layout:*`, fragments
- JSP markers: `<%@`, `<jsp:`, `${...}`, server-side includes
- AngularJS page islands: `ng-app`, `ng-controller`, `angular.module`, controllers/directives/components
- jQuery entries: `$(function)`, `$(document).ready`, `initPage`, `loadData`, event binding
- server session/request usage: `session`, `request`, hidden inputs, global variables rendered by server templates

Exclude dependency noise:

```text
.git node_modules dist build target coverage vendor vendors lib libs locale locales
*.min.js *.min.css generated bundles source maps
```

## A/B Page Comparison

Normalize page keys from URL, route, menu label, template filename, component filename, and directory context. Treat automated matching as a candidate map, not a truth table. Classify every candidate:

| Status | Meaning |
|---|---|
| `unmigrated` | Source page exists; no host counterpart found. |
| `partial-overlap` | Source and host overlap by name/route/domain but behavior is not proven equivalent. |
| `already-migrated` | Host page exists and parity evidence exists or user confirms. |
| `host-page-only` | Host page entry exists without source counterpart. |
| `host-component` | Host reusable component exists without page-entry evidence. |
| `host-shell` | Host bootstrap shell such as root `index.html`; not a business page by itself. |
| `unknown` | Evidence is insufficient. |

Each row should include old URL/template, new host entry when known, match basis, candidate score, confidence, human-correction flag, and next action.

Rules:

- Do not mark `already-migrated` from filename/path similarity.
- Treat `partial-overlap` as unmigrated work until a display-contract matrix exists. A present host shell proves layout only; data, copy, widget shape, defaults, and CSS are separately verifiable and are usually still missing.
- `workBench` vs `workbench`, `taskManage` vs `taskManagement`, and similar token variants require human correction.
- Host `.vue` files under components should be classified as component candidates, not host pages, unless route/menu/MPA evidence proves they are entries.
- Root `index.html` and other shell/bootstrap files should be downgraded unless route/menu/runtime evidence proves they are the selected unit's landing point.
- Exclude `openspec/`, `reports/`, `evidence/`, coverage output, generated report HTML, `e2e-tests/`, and `*.spec.*` / `*.test.*` files from page inventory and coupling counts.
- Large host-component counts from reusable components are noise; include them only as page-closure dependencies.

## URL And Entry Mapping

Build a separate URL/entry map before design:

| Field | Evidence |
|---|---|
| source URL | Java/Spring route annotation, menu config, gateway route, or server template entry. |
| SPA/hash route | AngularJS `$routeProvider.when(...)` or ui-router `.state(..., { url })`. |
| source template | JSP/Thymeleaf return value, `templateUrl`, view resolver target, or template path. |
| server controller | Java file and line for `@RequestMapping`, `@GetMapping`, or equivalent. |
| host entry | MPA HTML/TS entry, Vue Router route, menu registration, or shell mount. |
| mapping status | candidate, confirmed, unresolved, host-only-candidate. |

File-path URL guesses are low confidence. Do not use guessed URLs as acceptance criteria without route/menu/runtime evidence.

## Mixed-Stack Page Closure

For one page/user behavior, merge AngularJS, jQuery, and server template evidence into one closure instead of separate parallel reports.

Include:

- server template and fragments
- rendered globals, hidden fields, session/request-dependent values
- AngularJS module/controller/service/directive/filter/template expressions
- jQuery entry functions, events, DOM operations, plugin lifecycle
- page-init and side effects, including `run` blocks, timers, and first-paint requests
- page CSS and the shared CSS/sprite/plugin styles it depends on
- source i18n keys and their verbatim text
- API endpoints, request fields, response-code handling
- navigation/deep-link behavior
- host files to reuse/change/create

## Landing Rules

Reuse from host B:

- shell, auth/session, route/menu/permission registration
- API client and interceptors
- state pattern
- i18n mechanism, proxy, env, build and test gates
- generic chrome with equivalent interaction: buttons, inputs, overlays, layout primitives

Do not reuse host B table/select/modal components to replace a source page's custom widget unless the interaction passes the equivalence test below. API correctness does not make a widget swap acceptable; users perceive a wrong display contract as an unfinished migration.

Do not copy source A JSP/Thymeleaf global layout into host B. You **must** still extract the page-level CSS closure, including shared `common.css` / sprite / bootstrap-plugin styles the page assumes, and reproduce it host-native and page-scoped in B. Never assume source global styles are still present.

Land source i18n text verbatim. Keep migration units independently switchable and rollbackable.

### Interaction Equivalence Test

A host component may replace a source widget only when all five hold:

| Axis | Requirement |
|---|---|
| Input affordance | Same way the user provides the value: click, type, check, drag, pick. |
| Selection semantics | Same read-only vs editable, single vs multi, checked-list vs tag-list, list+popover vs table. |
| Default value | Same initial value, initial selection, and initial empty/loading state. |
| Validation and limits | Same required rules, min length, max count, at-least-one rules, and messages. |
| Submit/format shape | Same payload shape, separator, ordering, and display formatting. |

When the source specifies geometry, dialog width/height, centering, and column widths are part of the contract, not a styling preference.

Any failing axis is a deviation. Record it as its own matrix row with reason and approver; do not resolve it silently.

## Display Contract Matrix

For every source region of the unit, emit one row with a stable ID `DISP-<unit>-<region>-<n>`. This matrix is a persisted artifact created in `assess` for `partial-overlap` units, filled in `design`, and checked row by row in `verify`. Incremental repairs update existing rows rather than opening a new analysis round.

| 源区域 | 可见文案（源 i18n 原文） | 控件形态 | API + 字段/公式 | 默认值/校验 | 依赖 CSS（页级 + common + sprite） | 启动副作用 | B 现状 |
|---|---|---|---|---|---|---|---|

Column rules:

- 可见文案: copied verbatim from source `zh.json` / `en.json` or the template literal, with `file:line`.
- 控件形态: describe the interaction shape, not a component-library name. "只读列表 + 勾选框" is a contract; "el-select" is not.
- API + 字段/公式: endpoint plus the exact expression producing the visible value, including sums, joins, and derived titles.
- 依赖 CSS: page CSS plus every shared style the region assumes, including sprites and rules such as `font-size: 0`.
- 启动副作用: which page-init step populates this region on first paint.

`B 现状` enum: `missing`, `mismatched`, `wired-unverified`, `verified`, `approved-deviation`.

Rules:

- Display-contract parity is code-comparable and mandatory in `verify`. It is separate from pixel/screenshot measurement.
- `manual-only` may describe missing screenshot/measurement evidence. It never exempts copy, widget shape, defaults, geometry, or field formulas.
- DOM presence is not visibility. For rows carrying visible copy or visible numbers, confirm runtime visibility, since host or shared CSS can hide otherwise correct markup.

## Source i18n Text Table

| Key | 源原文 | B 当前文案 | 状态 | 偏离原因 | 批准人 | 证据 |
|---|---|---|---|---|---|---|

Status enum: `verbatim`, `mismatched`, `approved-deviation`, `missing-key`. Source text is the default acceptance baseline. Paraphrase, shortening, and punctuation changes are `mismatched`, not style choices. A host glossary or an obsolete source string can justify a deviation, but only as an `approved-deviation` row.

## Page Init And Side Effects

Click flows alone leave a shell page empty on first paint. List page-init separately from user actions:

| INIT-ID | 触发 | 位置 | 动作 | 影响区域 | 默认值 | 清理/停止条件 | 证据 | B 现状 |
|---|---|---|---|---|---|---|---|---|

Cover at minimum: `angular.module(...).run`, controller/directive init, `$timeout` / `setInterval` / delayed popups, first-paint `$http` calls, default filter and sort values, and server-rendered globals consumed at boot.

## CSS Closure

| 区域 | 页级 CSS | 依赖的共享样式 | 依赖类型 | B 落地方式 | 证据 |
|---|---|---|---|---|---|

Dependency types include shared base rules, sprite/background images, icon fonts, bootstrap/jQuery plugin styles, and visibility tricks such as `font-size: 0` or negative text-indent. Landing method must be host-native and page-scoped: a scoped fallback in B, a host token, or a host component style. Do not copy source global stylesheets wholesale, and do not assume they still load.

## Report From Code

Generate reports from repository evidence. Write the user-facing markdown in Simplified Chinese; keep CSV field keys and status enums in English.

- page inventory
- host stack
- page comparison
- URL / entry mapping
- coupling counts
- page closures for selected units
- display-contract matrix, source i18n text table, page-init list, CSS closure table
- validation gates

Do not fill generic implementation templates without code evidence. Empty FLOW/VAR/CHAIN tables are allowed only for a specified unit as a contract, not for the whole repository.

Generated script tables are an evidence baseline. They never substitute for the display-contract matrix, and filling one or two click-flow rows does not release an existing host shell page.

## Design-Ready Gate

Do not enter Delivery framing from a header-only design contract. A unit is design-ready only when it has:

- page closure: source templates/fragments/scripts/controllers/services/APIs/assets
- display-contract matrix rows for every source region of the unit
- page-init and side-effect list
- source i18n text table with any deviations recorded and approved
- CSS closure table with a host-native landing method per dependency
- at least 1-2 filled business-flow rows for material actions
- material variable/API chains, or explicit unresolved edges with runtime checks
- a field formula for every visible number and list
- host reuse/change/create decisions
- old source URL to new host entry mapping backed by Java/menu/MPA evidence
- permission/session/API parity draft
- rollback switch and condition

If these are empty or only table headers, mark the design gate `not-ready: empty-contract` and remain in design. For a `partial-overlap` shell page, a missing display-contract matrix, page-init list, i18n table, or CSS closure table is `not-ready` on its own.

## Host Compile Overlay

Capture and carry these host facts as parity requirements:

| Item | Why it matters |
|---|---|
| `lintOnSave` and dev-server overlay scope | An unrelated dirty file can blank the whole page and look like a migration defect. |
| TS `noImplicitAny` / `strict` | New helper modules fail the host build even when logic is correct. |
| Prettier/EditorConfig indentation | Reformatting a legacy file creates a large out-of-scope diff. |
| Declared Node baseline vs actual `node -v` | A run on the wrong Node is not verification evidence. |

Rules:

- Do not reformat, retype, or opportunistically fix legacy files outside approved scope. Record them as residuals with an owner and file list.
- A compile failure on the current unit's entry is blocking.
- A repo-wide overlay caused by unrelated files is a residual. Neither case may be reported as a healthy dev server.
- Record the actual Node version used for each build/test run next to the host-declared baseline.

## Concrete Gates

| Gate | Required Evidence |
|---|---|
| Behavior parity | Inputs, validation, branches, success/error states, empty/loading states. |
| Page-init parity | `run` blocks, controller init, timers/delayed popups, first-paint requests, default filter values. |
| Display-contract parity | Every matrix row: source-verbatim copy, widget shape, field formula, defaults, geometry, CSS dependency, runtime visibility. Mandatory and code-comparable. |
| Entry-wiring parity | Each slice is mounted at the host entry, calls its API, and is reachable by the user in the browser. |
| Permission parity | Menu visibility, route access, button hide/disable, server-side rejection. |
| URL parity | Old deep link, query/hash, redirects, browser back/forward, external links. |
| API parity | Endpoint, method, params/body, response codes, failure handling, messages. |
| Visual measurement parity | Screenshots, measurements, diff threshold, or mark manual-only. Does not cover display-contract rows. |
| Runtime parity | Host Node actually used vs declared baseline, lockfile, existing lint/build/test commands, host compile overlay disposition. |
| Git hygiene | No dependency/cache/build directory noise in intended commit; source A unchanged; B changes scoped. |
| Rollback | Switch, owner, affected URL/page, restore condition, data compatibility. |
| Completion authority | Delivery verified or valid repair-scope approval + domain verify + current host revision + no blocking residuals. |

## Completion Authority

`angularjs-to-vue3-host-migration verify` produces domain evidence. It is necessary but not sufficient for a completion claim.

Do not announce a page migration complete unless all are true:

- The implementing path has a current authority record: a Delivery `verified` handoff on the full path, or a valid repair-scope approval with no escalation triggers on the shell-page repair path.
- Domain verify evidence is current for the same source and host revisions.
- Host B revision is the revision that was built, tested, and reviewed.
- Git hygiene has no blocking dependency/cache/build noise.
- Every display-contract row is `verified` or `approved-deviation`.
- Every slice passes entry-wiring parity.
- Behavior, page-init, permission, URL, API, runtime/build, rollback, and visual/manual-only disposition have no blocking residuals.

## Shell-Page Repair

Use this variant when the host already has the unit's entry and the goal is parity repair rather than a new landing.

Entry conditions, all required:

- the unit is `partial-overlap` with a proven host MPA/router entry
- the user has authorized changes to host B
- the goal is source parity only: no new API contract, no permission-model change, no traffic switch or rollback-scope change

Method:

1. Produce or refresh the display-contract matrix, page-init list, i18n text table, and CSS closure table.
2. Slice by source region, one matrix group at a time.
3. Per slice: restate the source contract, change B, confirm the entry is mounted and reachable, then walk the region in the browser against the same path on the source site.
4. Update matrix rows in place and re-run display-contract parity incrementally.

Escalate out of repair and back to full framing when any of these appear: a missing or changed API contract, a permission-model change, new behavior beyond source parity, or a discovery that the original source closure never scanned the region.

## First Slice

Before expanding to the whole repository, run the method on one mixed page such as `home`, `taskManage`, or `projectProgress`:

1. inventory source closure, including CSS and i18n
2. identify host landing point and classify it as new landing or existing shell
3. map old URL to new entry
4. build the display-contract matrix and page-init list
5. trace one or two core actions
6. define gates and rollback
7. review with maintainers

Only then batch additional pages.

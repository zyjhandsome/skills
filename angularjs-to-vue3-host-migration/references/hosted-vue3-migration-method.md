# Hosted AngularJS/JSP/jQuery To Vue3 Migration Method

## Position

Default to migrating into an existing Vue3 host repository. The host owns the final entry, shell, auth, routing or MPA entry model, API client, state, component library, i18n, proxy, build, lockfile, Node baseline, and test gates.

This method is read-only for application code. It produces evidence, page contracts, repair plans, and verification conclusions; implementation belongs to the approved execute owner outside this domain skill.

Create a new Vite/create-vue project only when no host exists.

## Report Language

User-facing evidence reports and copied table contracts default to Simplified Chinese. Keep status enums, IDs, paths, commands, URLs, and CSV field keys in English.

## Inputs

For hosted migration, collect:

| Input | Required For | Notes |
|---|---|---|
| Source repo A | assess/design/verify | Legacy AngularJS/jQuery/JSP/Thymeleaf code. |
| Host repo B | assess/design/verify | Existing Vue3 final export/entry. |
| Migration units | design/verify | 1 to 5 pages, routes, menu items, URLs, or user behaviors. See `Unit Batches`. |
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

## Revision Freshness Gate

Bind every migration packet to the current source and host revisions, and also to the concrete files that supplied the page contract. Repository HEAD equality is required but not sufficient when the page contract rests on generated inventories or earlier conclusions.

Before each wave that consumes older evidence, refresh these sources when they exist:

| Source | Examples | Stale Effect |
|---|---|---|
| Source routes | Java/Spring `@RequestMapping`, AngularJS route/ui-router states, JSP/template returns | URL, unit identity, and page closure stale |
| Source copy | `zh.json`, `en.json`, JSP/template literals, server-rendered labels | i18n table and display-contract copy stale |
| Source behavior/API | controllers, services, jQuery handlers, request payload builders | FLOW/VAR/CHAIN and API parity stale |
| Host entries | `scripts/getpage.js`, `src/pages/*/*.ts`, Vue Router, menu/permission registration | host landing and entry-wiring evidence stale |
| Host runtime | `package.json`, lockfile, Node version files, build/test config, lint overlay config | runtime/build verification stale |

Record a `freshness_manifest` with path, digest or timestamp, repository revision, and evidence owner for each source. If a digest changes, do not reuse the previous "decided" value as a gate against the current source. Re-open the affected MATRIX rows or design section and quote the current evidence.

Common stale traps:

- Source copy changing from one business term to another invalidates old acceptance text.
- A newly added AngularJS hash/state invalidates an earlier "source has no such route" conclusion.
- A host MPA page added on `develop` can be `develop-native` for a different contract, not automatic parity for this hash.

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
- host baseline gap table
- source page-entry inventory
- A/B page comparison
- coupling counts excluding vendor
- recommended first migration units
- gaps and risks
- first-pass display-contract matrix for every `partial-overlap` unit, with `B 现状` filled

### design

Goal: make 1 to 5 migration units ready for implementation. Admission and per-unit obligations: `Unit Batches`.

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

Goal: prove migrated behavior is equivalent enough to release or identify gaps. One conclusion per unit; one failing unit fails the batch.

Required outputs:

- behavior, permission, URL, API, runtime, rollback checks
- display-contract parity, row by row, with runtime visibility confirmed for visible copy and numbers
- entry-wiring parity per slice
- visual measurement evidence only when screenshots or measurements exist
- manual-only label when visual measurement is missing, which never exempts a display-contract row
- a recorded runtime-evidence attempt whenever browser automation is reported unavailable

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
| CSS/asset baseline | Global stylesheets actually loaded, reset/normalize, utility or grid sheet presence, sprite sheets and coordinate maps, icon fonts, base font stack. |
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

Codebase Memory false negatives require fallback evidence before conclusions:

- Zero Route nodes does not prove there are no entries in an MPA host. Use `getPages()`, `src/pages/*/*.ts`, HTML entries, menus, and route guards.
- A graph snippet showing `route_path: '/'` can be a bootstrap shell or parser artifact. Verify Java annotations, route objects, or menu records before using it as a landing.
- `static/`, `scripts/`, `src/i18n`, generated route tables, and JSP/Thymeleaf templates may be excluded or under-indexed. Read files for those contracts and record the fallback reason.
- Empty Vue SFC inbound traces do not prove a component is unused. Check imports, route lazy loaders, page boot files, and template registrations.
- Same-named Java methods, controllers, or API wrappers can represent different pages or flows. Compare URL, params, caller, and response fields before treating them as evidence.

### Host Baseline Gap Table

Source pages assume a global environment that the host usually does not provide. Capture this once per host repository during `assess`, not once per page, so later units do not rediscover the same gap through broken rendering.

| 基线类别 | A 假定的全局依赖 | A 证据 | B 是否提供 | B 落地方式 | 状态 |
|---|---|---|---|---|---|

Cover at minimum:

- CSS reset/normalize and global base rules, including base font stack and any rule such as `font-size: 0` that hides otherwise correct markup
- Bootstrap or another utility/grid sheet, plus the version the template's class names were written against
- sprite sheets with their coordinate/size maps, icon fonts, and empty-state images
- jQuery and the jQuery plugin styles/behaviors the template boots
- global JS libraries the template assumes, such as date, table, chart, validation, or dialog helpers
- server-rendered globals, hidden inputs, and session/request values injected into `window`

Status enum: `host-provides`, `host-partial`, `host-missing`, `not-needed`.

A `host-missing` or `host-partial` row is a standing constraint for every page closure in this host: each source region depending on it needs an explicit B landing method in its CSS closure row. Discovering a missing global baseline while repairing a page is a symptom of a skipped assess step, not a new finding.

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
| `already-migrated` | Host page has closed source parity, outbound traffic points to it when authorized, and it is independently reachable at runtime. |
| `dest-built-unwired` | Host destination page or helper exists, but source/host outbound navigation still lands on A or on an unapproved fallback. |
| `wired-hidden` | Host entry or tab is wired, but runtime flags, permissions, `v-if`, feature switches, or parent shell state make it unreachable or invisible. |
| `develop-native` | Host `develop` has a native page, but its route/hash/query contract is not this source unit. Treat as a candidate, not parity. |
| `orphan-mpa` | MPA HTML/TS entry exists, but no matching source contract or reachable menu/route proves it is the selected unit. |
| `deprecated-removed` | Source unit was removed from scope/SDD by decision. Do not restore it without a new approved change. |
| `host-page-only` | Host page entry exists without source counterpart. |
| `host-component` | Host reusable component exists without page-entry evidence. |
| `host-shell` | Host bootstrap shell such as root `index.html`; not a business page by itself. |
| `unknown` | Evidence is insufficient. |

Each row should include old URL/template, new host entry when known, match basis, candidate score, confidence, human-correction flag, and next action.

Rules:

- Do not mark `already-migrated` from filename/path similarity.
- A host entry counts as proven only when route, menu, or MPA registration says so. Filename similarity, directory proximity, and matcher candidate scores are not entry evidence. Record which of the two a row rests on, because a `repair` decision made on a filename guess turns an unmigrated page into a phantom shell repair.
- Route shape is part of identity. A source route with a dynamic segment (`/phones/:phoneId`) never maps to a host route without one (`/phones`), even when every filename token matches. Redirect records are hops, not landing points, and must not lend their target's component to the redirect path.
- Treat `partial-overlap` as unmigrated work until a display-contract matrix exists. A present host shell proves layout only; data, copy, widget shape, defaults, and CSS are separately verifiable and are usually still missing.
- Treat `dest-built-unwired`, `wired-hidden`, `develop-native`, and `orphan-mpa` as open states. They can support planning, but they cannot be counted as migrated or used to close archive/completion gates.
- A tab label, hash alias, query parameter, or destination HTML file with a similar name is not a route-shape match. Keep one source hash/URL as one UNIT unless current route evidence proves they are the same runtime view.
- `deprecated-removed` is a scope decision. Restoring it is a new requirement, not a repair.
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

Evidence source branches:

- If Java/Spring routes are absent, AngularJS `$routeProvider`, ui-router states, hash routes, `templateUrl`, or runtime menu hash values are valid source URL evidence when tied to the selected template.
- If MPA helpers are absent, Vue Router route records and menu route records are valid host entry evidence.
- If neither source nor host has explicit route records, file paths remain guesses until runtime, menu, server return, or user-provided environment evidence confirms the landing.

## Source Contract Gates

Carry these source contracts through `assess`, `design`, repair, execute, and `verify`. They are gates, not optional notes.

### Navigation Landing

- Normalize absolute menu/cache/`data-href`/`window.open`/`location.href` values to the current source path before deciding the host landing. Do not carry a source absolute origin into host code unchanged.
- If the B landing is only a shell or skeleton and lacks the source page's full business body or page CSS closure, keep the source URL as the landing target until B parity is proven. Do not change navigation just to point at a Vue entry.
- Use one landing function per UNIT for every outbound path: cards, menus, reminder dialogs, success callbacks, deep links, and upgrade/creation flows. Divergent ad hoc URL builders are a blocker.
- Record a navigation landing row with source URL, normalized source path, candidate B entry, whether B is shell/skeleton/full parity, final landing target, and evidence.
- Treat outbound switching as its own authorized slice. Building a destination page or helper is `dest-built-unwired` until every approved outbound path is changed and verified; when switch authorization is absent, contract tests should assert that theoretical B HTML targets do not appear in active href/open locations.
- Distinguish URL semantics by destination:
  - app-internal navigation may strip origin and normalize duplicate legacy context paths while preserving query and hash;
  - iframe chrome may intentionally keep the source origin, and that `keepOrigin` behavior can be the completed contract;
  - emails, cached external links, and user-copyable absolute links must usually remain absolute with the source/root path proven by current code.
- Query and hash fields are contracts. Preserve fields such as `iframe`, `associate`, entity IDs, and task/detail IDs by source provenance; do not substitute a nearby project/user field unless the mapping is proven.

### Comparison And Identity

- Treat comparison operators and runtime types as source contracts. Template `==`, JavaScript `===`, numeric strings from APIs, booleans encoded as strings, and empty-string/null branches must be preserved or recorded as approved deviations.
- Map identity fields from source evidence: server-rendered hidden inputs, globals, session/request fields, DOM IDs, API response fields, and template variables. Do not replace an identity with a nearby host store getter unless the source-to-host field mapping is proven.
- Put comparison and identity assumptions into FLOW/VAR/CHAIN conditions, payload mappings, and display-contract rows when they affect visible state, permissions, routing, or API payloads.

### Shared Modal Modes

- Split shared dialogs by source mode. First-time binding, add/edit, cancel, success, failure, redirect, and permission-limited variants need separate rows when copy, buttons, validation, side effects, or navigation differ.
- Do not summarize a multi-mode public modal as one generic dialog unless all modes have the same source contract.

### Hit Layer And Selector-DOM

- When restoring `position:absolute`, `float`, `z-index`, negative margins, overlays, or expanded clickable containers, verify both visual stacking and click targets. A restored layout that covers a star, checkbox, link, or card action is not parity.
- Bind source CSS selectors to the real rendered DOM in B. If a Bootstrap/jQuery selector was written for a source element but B renders a component-library wrapper, either adjust the DOM/host selector or record a deviation. A selector that matches no effective node is missing CSS.
- Confirm hover/open/active utility classes used by the template, not just page-level files. Classes such as spacing helpers, visibility toggles, icon state classes, and sprite hooks belong in the CSS closure when the source DOM uses them.

### Mounted View Closure

- Scope a shell-page repair to views actually mounted by the selected wrapper: `ui-view`, `ng-include`, directive/component usage, server includes, router/menu landing, and runtime evidence. A template file present under `tpls/`, `views/`, or `pages/` is not a migrated or missing region unless the selected UNIT mounts it.
- If a host repo is a Vue2-to-Vue3 upgrade repo and the legacy area is still an AngularJS island, use source A and SIT/runtime behavior as the acceptance baseline. The earlier Vue host can provide clues, but it does not override the source AngularJS contract.

### Runtime-Hidden Source Functions

- Treat source code that is present but hidden by runtime CSS or classes as its own display-contract row. Visibility toggles such as `display:none !important`, `*-hide`, collapsed tabs, role-hidden blocks, and feature flags must record source code presence and runtime visibility separately.
- Default to SIT/runtime visibility for release parity. Showing a source-hidden function, or hiding a runtime-visible source function, requires an `approved-deviation` with reason and approver.

### Interruption Hygiene

- After an interrupted repair or execute session, scan the touched UNIT before continuing for duplicate modal instances, duplicate functions/helpers, repeated hash/route writes, unresolved merge fragments, and unclosed `<template>`/`<script>`/`<style>` blocks.
- Record any finding as blocker or residual before resuming implementation; do not layer another partial fix over an unknown interrupted state.

### Contract Test Harness

- Run contract tests through the host toolchain when importing TS/Vue code: Vitest, ts-node/tsx configured for the repo, Vite test setup, or the host's existing equivalent.
- Prefer executable display-contract tests for repair work when the contract can be checked without a browser: copy text, CSS class presence, API payload shape, derived formulas, and entry wiring. These tests are evidence for matrix rows, not a replacement for the matrix.
- Do not strip TypeScript or Vue code with regex and then import the result as verification evidence. If the test cannot load through the host toolchain, isolate a pure-JS function or mark the contract test harness as unresolved.

### Browser Automation Disposition

- Attempt runtime evidence through the host toolchain before declaring it unavailable: an existing Playwright/Cypress/Puppeteer setup, the host dev server plus a one-off headless screenshot or DOM-dump script, or any runtime inspection the host already supports. Record the attempt and the concrete failure reason. "No browser automation" is a finding that must be earned, not a default.
- Only after a recorded failed attempt may runtime checks be treated as blocked. Then keep affected matrix rows `wired-unverified` or `mismatched` and record the blocked checks as residuals. A user hard refresh or manual observation note is useful context, but it is not agent-owned verification evidence.
- Do not mark runtime visibility, hit-layer, hover/open state, modal geometry, sprite rendering, or entry-wiring rows as `verified` without agent-obtained browser/runtime evidence.
- A row that can never get agent-obtained evidence closes only as `manual-verified`, recording who checked it, the exact runtime condition checked, and when. This is a human release decision, not an agent conclusion, and it may not be applied in bulk to a whole region.

## Mixed-Stack Page Closure

For one page/user behavior, merge AngularJS, jQuery, and server template evidence into one closure instead of separate parallel reports.

Include:

- server template and fragments
- rendered globals, hidden fields, session/request-dependent values
- AngularJS module/controller/service/directive/filter/template expressions
- jQuery entry functions, events, DOM operations, plugin lifecycle
- page-init and side effects, including `run` blocks, timers, animation hooks, plugin scripts, global enhancement scripts, and first-paint requests
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

Land source i18n text verbatim. If no source i18n files exist, visible template literals and server-rendered literals are the copy baseline. Keep migration units independently switchable and rollbackable.

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

`B 现状` enum: `missing`, `mismatched`, `wired-unverified`, `verified`, `manual-verified`, `approved-deviation`.

Rules:

- Display-contract parity is code-comparable and mandatory in `verify`. It is separate from pixel/screenshot measurement.
- `manual-only` may describe missing screenshot/measurement evidence. It never exempts copy, widget shape, defaults, geometry, or field formulas.
- DOM presence is not visibility. For rows carrying visible copy or visible numbers, confirm runtime visibility, since host or shared CSS can hide otherwise correct markup.
- `manual-verified` closes only a runtime condition the agent could not obtain evidence for after a recorded failed attempt, and only with checker, checked condition, and date. It never covers copy, widget shape, field formulas, defaults, or geometry, which are all comparable in code.
- One row per page is a skeleton, not a matrix. A generated whole-page row marked `(skeleton)` must be split by source region — search, filters, list, thumbnails, badges, empty state, deep links — before the unit can be design-ready.
- The matrix is one ledger even for a batch. Every row carries the owning unit, so rows are filled, verified, and closed per unit rather than per batch.
- A closed matrix means every row is `verified`, `manual-verified`, or `approved-deviation`. `wired-unverified` is an open row, not a soft pass.

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

Dependency types include shared base rules, template utility classes, sprite/background images, icon fonts, bootstrap/jQuery plugin styles, and visibility tricks such as `font-size: 0`, negative text-indent, `display:none !important`, and `*-hide` switch classes. Landing method must be host-native and page-scoped: a scoped fallback in B, a host token, or a host component style. Do not copy source global stylesheets wholesale, and do not assume they still load.

Rules:

- Inventory every utility class used by the selected source template, including Bootstrap-shaped classes such as `dropdown`, `modal`, `btn`, `pull-*`, grid/flex helpers, state classes, and project-local helpers. If host B does not load Bootstrap or the original utility sheet, each used class needs a B landing method.
- Inventory every sprite/icon class used by the selected source template, including icon name, size class, background image, coordinate/position rule, and B landing method. Missing image, missing size, missing coordinate, or empty rendered icon is `mismatched`.
- Preserve source cascade semantics. New legacy CSS must not add same-specificity default rules that override source state classes such as `status-*`, `font-*`, active/open/disabled classes, validation classes, or empty-state image classes.
- Empty states are one display contract: visible copy, image/icon, spacing, and trigger condition. Correct text with a missing image or broken sprite is not `verified`.
- Runtime-hidden source functions must be represented. If source markup exists but SIT hides it, default to hidden; making it visible requires `approved-deviation`.
- A component-library overlay can host a migrated dialog, but it is not automatically equivalent to a Bootstrap/source modal. Width, title bar, footer buttons, iconography, destructive theme, close behavior, and success/error affordances must match or be recorded as deviations.
- Rich text editor swaps are deviations unless the five-axis interaction equivalence test passes. Toolbar affordance, paste/upload behavior, validation, output format, and read-only rendering are part of the contract.

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
- display-contract matrix rows for every source region of the unit, split from any generated whole-page `(skeleton)` row
- host baseline gap table with the A column filled, and a page-level landing method for every `host-missing` / `host-partial` baseline this page depends on
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

## Unit Batches

`design` and `verify` accept 1 to 5 units per run. A batch is several independent units sharing one artifact set, not one larger page, and it never relaxes a gate: the design-ready gate is judged per unit, one `not-ready` unit blocks the batch, and the fastest recovery is to drop that unit from the batch rather than hold the rest.

Admission — all must hold, otherwise split the batch:

| Rule | Why |
|---|---|
| At most 5 units | Beyond that the High cost/risk/rollback summary stops being reviewable. |
| One shared design scope | `repair` and `new-landing` have different approval chains; a mixed batch would need both. |
| Each unit resolves to exactly one source page | A unit name matching several pages has no definite scope. |
| No two units share a host landing | Same-file units must be sequenced or merged. |
| Every shared host surface has one owner | Router registration, menu, shared i18n, global stylesheets, and global store land once, as a prerequisite task group; other units depend on them read-only. |

Per-unit properties a batch must preserve: page closure, matrix rows, i18n table, CSS closure, rollback switch, verify conclusion, and completion decision. Batch conclusions are never averaged.

Pilot rule: the first unit of an A/B repo pair runs alone, because the host compile overlay, CSS closure landing method, entry-mounting pattern, and runtime-evidence feasibility are only proven by implementing and verifying once. Batching before that multiplies one wrong assumption by N. Remaining units may draft contracts in parallel with the pilot's implementation, but the pilot's change must be archived before the batch enters planning, or cross-change path overlap turns into a readiness blocker. Recorded measured evidence for those host facts, bound to the current host revision, can substitute for the pilot; nothing else can.

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
- For new or changed TS helpers in the selected UNIT, annotate callback parameters and empty arrays/objects immediately when host `noImplicitAny` or `strict` can infer `any[]`, `never[]`, or implicit `any`. Do not leave this to a later compile pass.
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
| Source contract gates | Navigation landing, comparison and identity mapping, shared modal modes, mounted view closure, runtime-hidden functions, hit layer, selector-to-DOM binding, CSS utility closure, interruption hygiene, contract test harness, and browser automation disposition. |
| API parity | Endpoint, method, params/body, response codes, failure handling, messages. |
| Visual measurement parity | Screenshots, measurements, diff threshold, or mark manual-only. Does not cover display-contract rows. |
| Runtime parity | Host Node actually used vs declared baseline, lockfile, existing lint/build/test commands, host compile overlay disposition. |
| Git hygiene | No dependency/cache/build directory noise in intended commit; source A unchanged; B changes scoped. |
| Rollback | Switch, owner, affected URL/page, restore condition, data compatibility. |
| Completion authority | Delivery verified + domain verify + current host revision + no blocking residuals. |

## Completion Authority

`angularjs-to-vue3-host-migration verify` produces domain evidence. It is necessary but not sufficient for a completion claim.

Do not announce a page migration complete unless all are true:

- The implementing path has a current authority record: a Delivery `verified` handoff for the approved scope.
- Domain verify evidence is current for the same source and host revisions.
- Host B revision is the revision that was built, tested, and reviewed.
- Git hygiene has no blocking dependency/cache/build noise.
- Every display-contract row is `verified`, `manual-verified`, or `approved-deviation`.
- Every slice passes entry-wiring parity.
- Behavior, page-init, permission, URL, API, runtime/build, rollback, and visual/manual-only disposition have no blocking residuals.
- No UNIT remains in `dest-built-unwired`, `wired-hidden`, `develop-native`, `orphan-mpa`, or other open comparison states.
- Known formula, row-order, API-payload, URL, permission, or entry-wiring residuals prevent a green completion/archive status. A packet with zero verified MATRIX rows can be archived only as an explicit partial/residual handoff, not as parity complete.

## Shell-Page Repair

Use this read-only variant when the host already has the unit's entry and the goal is parity repair rather than a new landing.

Entry conditions, all required:

- the unit is `partial-overlap` with a host MPA/router entry proven by route, menu, or MPA registration, not by filename similarity
- the source route and the host route have the same shape, so a detail page cannot be repaired against a list page
- the user wants a repair-scoped design/verification packet
- the goal is source parity only: no new API contract, no permission-model change, no traffic switch or rollback-scope change

Method:

1. Produce or refresh the display-contract matrix, page-init list, i18n text table, and CSS closure table.
2. Slice by source region, one matrix group at a time.
3. Per slice: restate the source contract, intended B files/entry points, verification steps, source-contract gates, residuals, and escalation triggers.
4. Update matrix rows in place only for evidence-backed B status. Do not mark rows verified from planned work.
5. Hand the repair slice plan to the approved execute owner before any B application code change.

`partial-overlap` is allowed to enter repair design because the host has a plausible mounted entry. It is still open work: until MATRIX rows, page-init, URL/API, CSS, and runtime reachability close, it must not be labeled `already-migrated`.

A repair packet still requires two approval records for High migration work: one scope/specification approval and one implementation-go approval. The repair fast lane may run Frame and Plan in the same session, but it must not collapse the two gates into one. Application code changes still belong to the approved execute owner, and the completion authority record is unchanged. Any escalation trigger below cancels the repair fast lane and returns the unit to full framing.

Same-wrapper discoveries can stay in repair design: a source region found later under the same mounted wrapper may be added to the matrix and slice plan without restarting the whole assessment. Escalate out of repair and back to full framing when any of these appear: a different page or wrapper, a missing or changed API contract, a permission-model change, new behavior beyond source parity, traffic switching, rollback-scope change, or a discovery that the original source closure never scanned the selected wrapper.

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

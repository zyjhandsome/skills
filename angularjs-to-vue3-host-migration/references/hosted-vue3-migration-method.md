# Hosted AngularJS/JSP/jQuery To Vue3 Migration Method

## Position

Default to migrating into an existing Vue3 host repository. The host owns the final entry, shell, auth, routing or MPA entry model, API client, state, component library, i18n, proxy, build, lockfile, Node baseline, and test gates.

Create a new Vite/create-vue project only when no host exists.

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

- host stack summary
- source page-entry inventory
- A/B page comparison
- coupling counts excluding vendor
- recommended first migration units
- gaps and risks

### design

Goal: make one migration unit ready for implementation.

Required outputs:

- page closure
- source behavior/data/API chains
- reuse/change/create decisions in host
- old URL to new entry mapping
- permission/session/API parity contract
- rollback switch and condition
- verification checklist
- unresolved evidence

### verify

Goal: prove migrated behavior is equivalent enough to release or identify gaps.

Required outputs:

- behavior, permission, URL, API, runtime, rollback checks
- visual evidence only when screenshots or measurements exist
- manual-only label when visual evidence is not measured

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

Normalize page keys from URL, route, menu label, template filename, component filename, and directory context. Classify every candidate:

| Status | Meaning |
|---|---|
| `unmigrated` | Source page exists; no host counterpart found. |
| `partial-overlap` | Source and host overlap by name/route/domain but behavior is not proven equivalent. |
| `already-migrated` | Host page exists and parity evidence exists or user confirms. |
| `host-only` | Host page exists without source counterpart. |
| `unknown` | Evidence is insufficient. |

Each row should include old URL/template, new host entry when known, confidence, and next action.

## Mixed-Stack Page Closure

For one page/user behavior, merge AngularJS, jQuery, and server template evidence into one closure instead of separate parallel reports.

Include:

- server template and fragments
- rendered globals, hidden fields, session/request-dependent values
- AngularJS module/controller/service/directive/filter/template expressions
- jQuery entry functions, events, DOM operations, plugin lifecycle
- API endpoints, request fields, response-code handling
- navigation/deep-link behavior
- host files to reuse/change/create

## Landing Rules

- Reuse host shell and auth.
- Reuse host API client/interceptors.
- Reuse host route/menu/permission registration.
- Reuse host state pattern.
- Reuse host component library and table/form/modal wrappers.
- Extract business behavior from JSP/Thymeleaf; do not copy source layout into host.
- Keep migration units independently switchable and rollbackable.

## Report From Code

Generate reports from repository evidence:

- page inventory
- host stack
- page comparison
- coupling counts
- page closures for selected units
- validation gates

Do not fill generic implementation templates without code evidence. Empty FLOW/VAR/CHAIN tables are allowed only for a specified unit as a contract, not for the whole repository.

## Concrete Gates

| Gate | Required Evidence |
|---|---|
| Behavior parity | Inputs, validation, branches, success/error states, empty/loading states. |
| Permission parity | Menu visibility, route access, button hide/disable, server-side rejection. |
| URL parity | Old deep link, query/hash, redirects, browser back/forward, external links. |
| API parity | Endpoint, method, params/body, response codes, failure handling, messages. |
| Visual parity | Screenshots, measurements, diff threshold, or mark manual-only. |
| Runtime parity | Host Node, lockfile, existing lint/build/test commands. |
| Git hygiene | No dependency/cache/build directory noise in intended commit; source A unchanged; B changes scoped. |
| Rollback | Switch, owner, affected URL/page, restore condition, data compatibility. |
| Completion authority | Delivery verified + domain verify + current host revision + no blocking residuals. |

## Completion Authority

`angularjs-to-vue3-host-migration verify` produces domain evidence. It is necessary but not sufficient for a completion claim.

Do not announce a page migration complete unless all are true:

- Delivery has a current `verified` handoff.
- Domain verify evidence is current for the same source and host revisions.
- Host B revision is the revision that was built, tested, and reviewed.
- Git hygiene has no blocking dependency/cache/build noise.
- Behavior, permission, URL, API, runtime/build, rollback, and visual/manual-only disposition have no blocking residuals.

## First Slice

Before expanding to the whole repository, run the method on one mixed page such as `home`, `taskManage`, or `projectProgress`:

1. inventory source closure
2. identify host landing point
3. map old URL to new entry
4. trace one or two core actions
5. define gates and rollback
6. review with maintainers

Only then batch additional pages.

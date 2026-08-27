# AngularJS To Vue 3 Migration Method

Distilled from `D:\projects\book2skills\AngularJS 前端项目升级迁移到 Vue 3 的深度研究报告.md`.

## Hosted Migration Override

For this skill, the default migration path is now hosted migration into an existing Vue3 repository. Load `references/hosted-vue3-migration-method.md` first when a host repo exists.

Use this file for AngularJS construct mapping, risk background, and greenfield fallback only. Do not recommend creating a Vite/create-vue skeleton when the user's Vue3 host already exists.

## Coverage Standard

Use this reference to produce a migration plan that preserves the report's core judgments:

- Treat AngularJS 1.x to Vue 3 as a system migration, not package upgrade.
- Prefer gradual migration for medium and large systems.
- Put browser support, Node/CI baseline, test coverage, and coexistence policy before implementation.
- Clarify bridge library fit instead of assuming any Angular/Vue bridge is safe.
- Move framework-coupled AngularJS code behind general boundaries before translating UI.
- Put rollback, acceptance criteria, test cases, and monitoring in the same plan as implementation tasks.

## Core Position

AngularJS 1.x to Vue 3 is not a normal dependency upgrade. Treat it as a frontend runtime, component model, routing, state, testing, build, and release migration.

Default recommendation for medium and large systems:

```text
inventory first
build Vue 3 platform boundary
preserve auth and routing continuity
migrate shared assets
migrate low-coupling pages
migrate complex forms/directives/plugins
remove AngularJS runtime last
```

Prefer gradual migration over big-bang rewrite unless the system is small, business scope is frozen, and regression risk is low.

## Preconditions To Confirm

Capture these assumptions before estimating:

| Area | Decision Needed |
|---|---|
| Browser support | Vue 3 and Vite target modern browsers. IE11 support requires a different strategy. |
| Node and CI baseline | New Vue/Vite projects require modern Node and updated CI runners or images. |
| Project size | Page count, route count, component/directive count, service/API count, third-party dependency count. |
| Router | ui-router, ngRoute, hash routes, deep links, redirects, route resolves, guards. |
| Build | Gulp, Grunt, Webpack, Bower, custom scripts, multi-entry deployment. |
| Tests | Karma/Jasmine, Protractor, manual regression, existing E2E, screenshot or visual checks. |
| Release model | Whether dual-stack routing, iframe shell, micro frontend, or route flagging is acceptable. |
| Team | Frontend, QA, architecture owner, backend/API support, DevOps support. |

## Migration Path Selection

| Path | Use When | Strength | Risk |
|---|---|---|---|
| Route-level strangler migration | Medium/large systems need continuous delivery | Small release batches, clear rollback, aligns with route ownership | Dual-stack governance and shared auth/routing complexity |
| Vue 3 app shell plus old AngularJS routes | Need early platform boundary and rollout control | New shell owns navigation, auth, tracking, errors, release switches | History, hash, iframe or parent-child communication can become platform work |
| Component-island bridge | Need tactical Vue inside existing AngularJS pages | Fast first migration, useful for shared widgets | Bridge lifecycle, deep watch, performance, and dependency maturity risks |
| Full rewrite | Small or intentionally frozen system | Clean target architecture | Highest regression concentration and delayed value delivery |

Use bridges as transition mechanisms, not target architecture. `ngVue` is primarily a Vue 2 bridge. Community Vue 3 bridges require maturity review. Do not choose a bridge because it avoids migration design.

## Bridge Library Decision Rules

Do not treat all bridge libraries as equivalent:

| Bridge | Fit For AngularJS 1.x To Vue 3 | Decision Rule |
|---|---|---|
| `ngVue` | Primarily AngularJS 1.x + Vue 2 | Use only as a short-lived Vue 2 transition when unavoidable. It is not a Vue 3 end state and creates a later Vue 2 to Vue 3 migration. |
| `ngVue3` | Community AngularJS 1.x + Vue 3 bridge | Accept only as tactical component-island support after maturity review, breaking-change review, and clear removal plan. |
| `ngx-vue` | Angular, not AngularJS, and commonly archived | Do not choose for AngularJS 1.x to Vue 3 migration. Exclude from primary path unless the repository being migrated is actually Angular 2+. |

Bridge use must be time-boxed. A bridge should have:

- owner
- pages/components allowed to use it
- performance monitoring
- exit criteria
- removal milestone

If a bridge becomes the only way new pages can be delivered, the migration is drifting into a long-lived hybrid architecture and needs re-planning.

## Code Audit Commands

Use these commands as a first pass when a repository is available. They should create evidence for the inventory, not replace manual review:

```bash
rg -n "angular\.module|\.component\(|\.directive\(|\.controller\(|\.service\(|\.factory\(|\.provider\(|\.filter\(" src
rg -n "\$scope|\$rootScope|\$watch|\$emit|\$broadcast" src
rg -n "\$http|\$resource|\$q|interceptor" src
rg -n "\$stateProvider|\$urlRouterProvider|ui-router|ngRoute|\$location" src
rg -n "ng-repeat|ng-if|ng-show|ng-model|ng-class|ng-style|filter:" src
rg -n "jquery|\$\(|moment|lodash|chart|editor|datepicker|upload" src
rg -n "Karma|Jasmine|Protractor|selenium|cypress|playwright" .
rg -n "gulp|grunt|bower|webpack|vite|rollup" .
```

Classify findings into:

- app shell and bootstrap
- routes and permissions
- page controllers
- reusable components
- directives with templates
- directives with raw DOM or jQuery behavior
- services/factories/providers
- API and interceptors
- filters and formatting logic
- third-party UI/plugin dependencies
- tests and CI
- legacy build and deploy paths

## AngularJS To Vue 3 Mapping

| AngularJS 1.x | Vue 3 Target | Migration Rule |
|---|---|---|
| `angular.module()` | `createApp()` and app shell | Rebuild application boundary; do not mimic module globals. |
| controller + `$scope` | SFC + `setup()` + `ref/reactive` | Declare state explicitly and keep side effects out of computed values. |
| component bindings `<`, `@`, `&` | props and emits | Make input/output contracts explicit. |
| directive with template | Vue component | Prefer components for visual behavior. |
| directive with DOM behavior | Vue custom directive or component lifecycle | Use custom directives only for low-level DOM reuse. |
| service/factory/provider | API modules, composables, Pinia stores | First remove AngularJS DI coupling, then adopt Vue boundaries. |
| filter | computed, methods, utility functions | Do not recreate global template filters. |
| `$http`, `$resource` | fetch or axios API client | Centralize auth headers, base URL, errors, timeout, retry. |
| `$q` | Promise and async/await | Normalize async behavior during API extraction. |
| `$watch` | `watch` or `watchEffect` | Watch only necessary sources; avoid deep bridge watching. |
| `$emit` / `$broadcast` | props/emits, Pinia, or a narrow event bus | Prefer ownership and store boundaries over broad events. |
| ui-router / ngRoute | Vue Router 4 | Map route meta, guards, lazy pages, redirects, and legacy deep links. |
| `ng-repeat` | `v-for` with `:key` | Filter/sort through computed arrays before rendering. |
| `ng-if` / `ng-show` | `v-if` / `v-show` | Preserve mount/unmount semantics and state reset behavior. |
| `ng-model` | `v-model` / `modelValue` events | Component v-model has explicit event semantics in Vue 3. |
| Karma/Jasmine | Vitest + Vue Test Utils | New code should start with modern tests. |
| Protractor | Playwright or Cypress | Cover critical route and business flows in real browsers. |

## Concrete Migration Examples

### AngularJS Component To Vue 3 SFC

Map AngularJS component bindings to explicit Vue props and emits. Do not preserve controller shape if a Vue component boundary is clearer.

```js
angular.module('app').component('userEditor', {
  bindings: {
    user: '<',
    onSaved: '&'
  },
  template: `
    <form ng-submit="$ctrl.save()">
      <input ng-model="$ctrl.form.name">
      <button type="submit">保存</button>
    </form>
  `,
  controller: function (UserApi) {
    this.$onInit = () => {
      this.form = angular.copy(this.user)
    }
    this.save = async () => {
      const saved = await UserApi.update(this.form)
      this.onSaved({ user: saved })
    }
  }
})
```

```vue
<script setup>
import { reactive, watch } from 'vue'
import { userApi } from '@/api/userApi'

const props = defineProps({
  user: { type: Object, required: true }
})

const emit = defineEmits(['saved'])
const form = reactive({ ...props.user })

watch(
  () => props.user,
  (next) => Object.assign(form, next),
  { deep: true }
)

async function save() {
  const saved = await userApi.update(form)
  emit('saved', saved)
}
</script>

<template>
  <form @submit.prevent="save">
    <input v-model="form.name" />
    <button type="submit">保存</button>
  </form>
</template>
```

Migration meaning:

- `<` binding becomes props.
- `&` callback becomes emits.
- `ng-model` becomes `v-model`.
- `$onInit` initialization becomes setup state initialization.
- API access moves through a framework-independent API module.

### AngularJS Service To API Module And Pinia

First remove AngularJS dependency injection, then decide whether data is local composable state or shared Pinia state.

```ts
export const userApi = {
  async getById(id: string) {
    const res = await fetch(`/api/users/${id}`, { credentials: 'include' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json()
  }
}
```

```ts
import { defineStore } from 'pinia'
import { userApi } from '@/api/userApi'

export const useUserStore = defineStore('user', {
  state: () => ({
    current: null,
    loading: false
  }),
  actions: {
    async load(id: string) {
      this.loading = true
      try {
        this.current = await userApi.getById(id)
      } finally {
        this.loading = false
      }
    }
  }
})
```

### ui-router To Vue Router

Preserve old deep links before changing route style:

```ts
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/users/:id',
      component: () => import('@/pages/UserDetailPage.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/#/users/:id',
      redirect: to => `/users/${to.params.id}`
    }
  ]
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth /* && not logged in */) {
    return '/login'
  }
})
```

Route migration must explicitly cover:

- route name and URL preservation
- hash to history redirects
- `resolve` replacement
- auth guard and permission guard
- menu state
- browser back/forward behavior
- bookmarked URLs and external links

## Implementation Sequence

### Phase 0: Inventory And Freeze Boundaries

Scan and classify:

- modules, components, directives, controllers
- services, factories, providers, filters
- `$scope`, `$rootScope`, `$watch`, events
- routes, resolves, guards, redirects, hash URLs
- `$http`, `$resource`, `$q`, interceptors
- templates and `ng-*` directives
- jQuery plugins, charting, upload, date picker, rich text, table libraries
- tests and manual regression assets
- build and release scripts

Deliverables:

- migration inventory
- route and permission map
- API and service map
- third-party dependency replacement table
- test baseline
- priority and risk ranking

### Phase 1: Vue 3 Foundation

Create a Vue 3 foundation with Vite or create-vue, Vue Router, Pinia, ESLint, Vitest, and basic CI. Establish:

- app shell and layout
- route conventions and `meta`
- API client and error model
- session/auth adapter
- shared styles and tokens
- base components
- lint/test/build commands
- release and rollback switches

### Phase 2: Compatibility Layer

Build compatibility before page migration:

- old URL to new URL map
- token/session compatibility
- unified API adapter
- menu and permission source compatibility
- event or parent-child communication for coexistence
- feature flag or route-level rollback

Do not change auth protocol and UI framework at the same time unless explicitly required.

Compatibility layer checklist:

- API client owns base URL, credentials, auth headers, timeout, retry, and error normalization.
- Auth adapter preserves login, refresh, logout, 401, 403, expired-token, and cross-tab behavior.
- Route adapter preserves old URLs, hash routes, redirects, params, query strings, and browser history.
- Permission adapter preserves menu, route, and button-level permission semantics.
- Coexistence adapter defines iframe, parent-child message, route switch, or micro-frontend communication.
- Feature flags allow route-level rollback without redeploying the whole app.

### Phase 3: Shared Assets

Migrate shared assets before business pages:

- buttons, inputs, modal, table, form layout
- permission button/directive equivalents
- error messages and toast/notification
- date/currency/status formatting utilities
- upload, chart, editor wrappers or replacements
- common list/detail/form page shells

### Phase 4: First Page Batch

Start with low-coupling read-only pages or non-critical list/detail pages. Validate:

- route entry and deep links
- auth and permission behavior
- API request/response behavior
- visual layout and responsive behavior
- E2E smoke flow
- monitoring and rollback path

### Phase 5: Complex Pages

Move complex forms, heavy directives, charting, jQuery plugins, uploads, drag/drop, and rich text after the team has stable Vue patterns.

Require page-level acceptance criteria before starting each complex page:

- field-by-field form validation comparison
- route and permission matrix
- API and error handling matrix
- old/new screenshot comparison
- performance baseline
- rollback switch

### Phase 6: AngularJS Removal

Remove old stack only after all routes and pages are migrated:

- AngularJS bundle and runtime
- old routes and redirects no longer needed
- Bower/Gulp/Grunt or old Webpack scripts
- bridge libraries
- unused services, filters, directives
- old tests replaced or retired

## Risk Controls

| Risk | Control |
|---|---|
| Route and bookmark breakage | Maintain old-to-new URL map; test external deep links and hash URLs. |
| Auth/session drift | Build an auth adapter first; test login, refresh, logout, 401, 403, expired token. |
| Performance regression | Track JS size, route switch time, Lighthouse, memory, and RUM metrics. |
| Bridge maturity | Keep bridge use tactical and time-boxed; avoid core domain lock-in. |
| Weak tests | Add smoke and critical E2E first; require tests for new Vue components and stores. |
| Browser mismatch | Confirm modern browser matrix before choosing Vue 3/Vite baseline. |
| CI baseline too old | Upgrade Node, runners, package registry, and images before large page migration. |
| UI inconsistency | Migrate design tokens and base components before page volume work. |

## Coexistence Pitfalls

Write these into engineering standards before the first mixed release:

- Do not mechanically put `v-if` and `v-for` on the same node when translating `ng-repeat` plus filters. Prefer a computed list, then render with `v-for`.
- Keep computed values side-effect free. Use `watch` for side effects.
- Avoid deep bridge watching. AngularJS bridge deep watch can traverse/copy large objects during digest and create serious performance regressions.
- Do not confuse AngularJS `ng-model` with Vue 3 component `v-model`. Vue 3 component v-model uses explicit `modelValue` and `update:modelValue` semantics.
- Do not convert every AngularJS directive to a Vue custom directive. Visual and stateful behavior should usually become a component.
- Do not replace all third-party UI plugins during the same step as framework migration unless the page is isolated and well-tested.
- Do not remove old URLs until deep links, bookmarks, and support documents are updated or redirected.

## Testing, Performance, And Monitoring

Testing starts with the first migrated page, not the end of migration.

Recommended layers:

| Layer | Tooling | What To Cover |
|---|---|---|
| Static checks | ESLint, TypeScript or vue-tsc, dependency audit | new Vue modules, shared API/client code, stores |
| Unit tests | Vitest | pure utilities, formatters, API wrappers, stores, composables |
| Component tests | Vue Test Utils or Cypress Component Testing | forms, modal, table, permission widgets, upload widgets |
| E2E | Playwright or Cypress | login, permissions, core business flows, deep links, rollback route switches |
| Visual regression | Playwright screenshots or approved screenshot baseline | migrated screens, complex forms, charts, layout shells |
| Performance | Lighthouse CI, bundle size, DevTools trace, RUM | first load, route switch, large lists, charts, dual-stack pages |
| Production monitoring | Sentry or equivalent, logs, metrics, alerting | error rate, blank screen rate, API failure, slow route, rollback events |

Performance gates should track at least:

- JavaScript bundle size by route
- first contentful paint or equivalent local metric
- route switch time
- API error rate
- client exception count
- blank screen rate
- memory growth on repeated route switching

## Migration Management Template

Do not manage migration as a plain task list. Every migration item should carry rollback and acceptance criteria.

| Task | Owner | Start | End | Milestone | Acceptance Criteria | Rollback | Tests | Dependencies | Status |
|---|---|---|---|---|---|---|---|---|---|
| Inventory and dependency register | [fill] | [date] | [date] | Baseline approved | modules/routes/deps/risks captured and reviewed | document version rollback | inventory sampling | repo access, build runnable | not started |
| Vue 3 skeleton | [fill] | [date] | [date] | New skeleton works | dev/build/test/lint pass; Router/Pinia available | keep old build | skeleton smoke test | Node, CI, registry | not started |
| Auth and API compatibility | [fill] | [date] | [date] | Gray traffic possible | login/refresh/logout/401/403 consistent | switch to old auth entry | auth and API matrix | backend, gateway | not started |
| Shared components | [fill] | [date] | [date] | Component MVP | button/input/modal/table key states replaceable | component rollback | unit/component/visual | design tokens | not started |
| First page batch | [fill] | [date] | [date] | First Vue route online | URL, auth, tracking, permission, performance accepted | route flag to old page | E2E, regression, performance baseline | router/API/components | not started |
| AngularJS removal | [fill] | [date] | [date] | Old stack removed | old bundle/routes/deps removed | prior stable release | full regression, Lighthouse, monitoring | all pages migrated | not started |

## Estimation Guidance

Use three planning scales when code metrics are unknown:

| Scale | Typical Scope | Team | Timeline | Person-days |
|---|---|---|---|---:|
| Small | 20-40 pages, 80-150 components/directives | 2 FE + shared QA | 8-14 weeks | 45-100 |
| Medium | 40-80 pages, 150-300 components/directives | 4 FE + 1 QA + tech lead | 16-28 weeks | 120-220 |
| Large | 80-150+ pages, 300+ components/directives | 6-8 FE + 2 QA + architect | 7-12 months | 260-500+ |

Increase estimates for low automation, old CI, IE11 constraints, many jQuery plugins, complex forms, or unclear ownership.

Use these estimates as planning defaults, not promises. Adjust upward when:

- tests are mostly manual
- route ownership is unclear
- multiple product teams share pages
- third-party UI widgets are unmaintained
- old browser support remains
- package registry or CI runners are old
- authentication or permissions are tightly coupled to AngularJS services

## Suggested Medium-Project Timeline

For a medium SPA with modern browser target, 4 frontend engineers, 1 QA, and a part-time technical lead:

| Period | Work |
|---|---|
| Weeks 1-2 | inventory, dependency register, risk review |
| Weeks 3-5 | Vue 3 skeleton, CI, Router, Pinia, API client, auth/session adapter |
| Weeks 6-8 | shared components, style tokens, formatting utilities, error handling |
| Weeks 9-14 | low-coupling list/detail pages, first gray release, rollback exercise |
| Weeks 15-22 | forms, dashboards, complex business pages, plugin replacement |
| Weeks 23-28 | AngularJS dependency removal, full regression, performance acceptance, final cutover |

If the user asks for a Gantt chart, generate it from these phases and adapt dates to the real start date.

## Acceptance Criteria

Technical:

- Vue 3 app can run, build, lint, and test in CI.
- Router, permission, menu, and API client are stable.
- AngularJS routes are replaced or intentionally retained behind rollback.
- Core pages have no console errors.
- Old dependencies are removed after final cutover.

Business:

- Critical user journeys match old behavior.
- Form fields, validation, defaults, prompts, pagination, sorting, filters, and permissions are consistent.
- Error messages and exceptional flows are covered.
- Online error rate, blank-screen rate, and performance do not regress materially.

## Recommended First Modules

1. App shell, navigation, login entry, 403/404, empty and error pages.
2. Shared components and style tokens.
3. API adapter and shared state boundaries.
4. Low-coupling read-only list/detail pages.
5. Medium-complexity forms.
6. Dashboards and charts.
7. Heavy directive, jQuery plugin, rich text, upload, drag/drop pages.
8. AngularJS dependency and build cleanup.

## Source Priority

When updating or defending recommendations, prefer sources in this order:

1. AngularJS official support status and AngularJS docs for components, directives, filters, providers, `$http`, `$q`, and `$resource`.
2. Vue official docs for quick start, SFC, `<script setup>`, props/events, forms, computed/watchers, custom directives, lifecycle.
3. Vue Router, Pinia, Vite, Vitest, and Vue Test Utils official docs for target architecture.
4. Chrome/web.dev, Playwright, Cypress, and Sentry official docs for performance, browser testing, and monitoring.
5. Engineering migration case studies such as Thoughtworks, LeanIX, and Holistics for strategy tradeoffs.
6. Bridge repositories such as ngVue, ngVue3, and ngx-vue only for bridge feasibility, not target architecture design.

## Completeness Checklist

A migration plan based on this method is incomplete if it lacks any of:

- assumptions and missing information
- browser and Node baseline decision
- migration path comparison
- bridge library decision when bridge is discussed
- detailed impact table
- AngularJS-to-Vue mapping
- code audit evidence or commands
- phased plan with rollback
- testing plan
- performance and monitoring plan
- risk register with early warning signals
- resource and timeline estimate
- first-module recommendation
- final AngularJS removal criteria

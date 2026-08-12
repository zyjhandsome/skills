# Vue 2 to Vue 3 transformations

## Migration posture

Preserve observable behavior first. Apply only the structural changes needed to
land safely in host B. Defer unrelated redesign, global state redesign, and broad
Composition API conversion.

## Core mapping

| Vue 2/source pattern | Vue 3 host direction | Required check |
|---|---|---|
| `new Vue`, `Vue.use` | `createApp`, per-app plugin install | MPA entry isolation |
| `Vue.prototype.$x` | explicit import/injection; rare `globalProperties` | testability and typing |
| `Vue.filter` | imported formatter/computed value | locale and null behavior |
| global directive | Vue 3 directive hooks or component behavior | focus/input timing |
| mixin | composable or explicit shared option | collision and lifecycle order |
| event bus | typed emitter, Pinia, or direct component event | listener cleanup |
| `.sync` | `v-model:<prop>` / explicit update event | two-way timing |
| `value` + `input` | `modelValue` + `update:modelValue` | form validation |
| `$listeners` | merged attrs/listeners handling | wrapper forwarding |
| `$scopedSlots` | Vue 3 slots | fallback rendering |
| old lifecycle hooks | Vue 3 names/Composition hooks | mount/update order |
| Vuex 3 | local state, composable, or Pinia by ownership | reset and persistence |
| Router 3 | Router 4 only where nested routing is real | base/hash/query behavior |
| Element UI | Element Plus or B wrapper | API and visual parity |

Review removed/changed Vue APIs in actual code rather than applying blind global
replacements. Pay special attention to render functions, JSX, dynamic components,
transitions, keep-alive, teleport-like modal assumptions, custom model contracts,
deep selectors, and array/ref unwrapping.

## TypeScript policy

- Convert external boundaries first: props, emits, API request/response, store
  state/actions, route/query parameters, message payloads, table row models.
- Permit `defineComponent` with Options API when it reduces migration risk.
- Do not hide uncertainty with broad `any`. Use narrow adapters at untyped legacy
  boundaries and record their removal condition.
- Preserve domain field optionality and server nullability; do not “clean up” data
  shapes during framework migration.
- Keep generated or third-party types isolated from domain types.

## State migration

Do not translate every Vuex module into one Pinia store mechanically.

| Ownership | Target |
|---|---|
| one component | component state |
| one page/component subtree | page composable or page Pinia store |
| multiple entries in B | global Pinia store |
| server-owned, cheaply reloadable | query/service state rather than permanent global cache |

Preserve initialization order, reset/logout behavior, persistence keys, optimistic
updates, concurrent requests, and derived-state semantics.

## Router and MPA

- Keep B as MPA when that is its established architecture.
- For a simple migrated entry, mount the page without Vue Router.
- For an entry with genuine nested views, install Router 4 into that entry only.
- Reproduce required query/hash parsing, guards, titles, back/forward behavior, and
  deep links. If old URLs are explicitly non-goal, remove compatibility only after
  callers and menus have switched.
- Do not create one giant SPA as an incidental migration effect.

## UI and special dependencies

For every component/library mapping, distinguish:

```text
API compatibility / rendered DOM / styling / keyboard interaction /
accessibility / data behavior / performance / license
```

- Element UI → Element Plus: verify renamed props/events/slots, form validation,
  popup containers, date/time semantics, pagination, table selection, loading,
  notification duration, and CSS variables. Inventory computed styles before
  substitution; explicitly reconcile component density, fonts, line heights,
  cell padding, borders, radii, colors, icons, teleports, and wrapping with a
  page-scoped compatibility layer. Do not inherit host defaults accidentally.
- vxe-table 3 → 4: use the exact upstream interval analysis; verify editors,
  formatters, validation, virtual scrolling, export, keyboard behavior, and row
  identity with production-scale data.
- SpreadJS Vue 2 → Vue 3: verify license entitlement, binding availability, formula,
  import/export, locale, clipboard, printing, and file fidelity before scheduling
  the page.
- ECharts 4 → 5: replace CommonJS component loading with supported ESM imports and
  verify options, themes, resize, disposal, tooltip, export, and large data.
- Drag/drop, rich text, mobile UI, screenshot/export libraries: treat replacement
  as a behavior contract, not a package-name substitution.

For exact versions, Node/peer requirements, upstream migration evidence,
alternatives, license, and lock impact, follow
`runtime-and-dependency-compatibility.md`. Block the disposition when authoritative
version-specific evidence is unavailable.

## Styles

Do not bulk-copy A's reset or global theme into B. Start from B's tokens and layout,
then add the smallest page-scoped compatibility layer needed for parity. Record
every deliberate visual difference. Follow `visual-parity-validation.md` before
changing source CSS or replacing the UI library.

## Forbidden combined refactors

Unless separately approved, do not combine framework migration with:

- business rule or API contract changes;
- global navigation redesign;
- permission model changes;
- large store normalization;
- broad naming/folder cleanup;
- blanket Composition API conversion;
- design-system replacement beyond required host adaptation.

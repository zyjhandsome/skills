# AngularJS Construct Mapping

Load this on a hosted or greenfield run when the selected unit has AngularJS controllers, directives, components, or filters. It maps constructs and runtime semantics. It does not authorize a new Vue 3 shell when a host already exists.

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

## Runtime Semantics

| AngularJS 1.x construct | Source runtime semantics | Vue 3 host target | Parity check |
|---|---|---|---|
| Directive `scope: { x: '=' }` | A child write syncs back to the parent model. | `props` plus `emit('update:x')`. Use `defineModel` only when the host Vue is 3.4 or newer. | Do not assign to `props.x`. |
| `transclude: true` | Transcluded content binds the outer scope, not the isolate scope. | `<slot>` or a scoped slot. | Check which scope the slot expression reads. |
| `require: '^parent'` / `'?ngModel'` | The directive receives an ancestor controller. | `provide` / `inject`. | A `?` require must inject a default instead of throwing. |
| `$compile(html)(scope)` | The runtime compiles directives and events inside the string. | Structured data plus `<component :is>` or a conditional branch. | `v-html` does not bind directives or events, so it cannot carry the compiled result. |
| `ngModelController` (`$parsers`, `$validators`, `ng-model-options`) | A failed parser sets the model to `undefined`. | The host form component. | If the source submit path depends on an `undefined` field, reproduce that in the request builder. |
| Built-in filters (`number`, `currency`, `date`, `filter`, `orderBy`) | `null` and `undefined` render empty. `date` tokens are lowercase `yyyy` and `dd`. | An explicit formatter. | Rounding and empty-string behavior differ by AngularJS version. Read them from the version the source repo actually ships. Do not assume them. |

## Coexistence Pitfalls

- Do not mechanically put `v-if` and `v-for` on the same node when translating `ng-repeat` plus filters. Prefer a computed list, then render with `v-for`.
- Keep computed values side-effect free. Use `watch` for side effects.
- Avoid deep bridge watching. AngularJS bridge deep watch can traverse/copy large objects during digest and create serious performance regressions.
- Do not confuse AngularJS `ng-model` with Vue 3 component `v-model`. Vue 3 component v-model uses explicit `modelValue` and `update:modelValue` semantics.
- Do not convert every AngularJS directive to a Vue custom directive. Visual and stateful behavior should usually become a component.
- Do not replace all third-party UI plugins during the same step as framework migration unless the page is isolated and well-tested.
- Do not remove old URLs until deep links, bookmarks, and support documents are updated or redirected.

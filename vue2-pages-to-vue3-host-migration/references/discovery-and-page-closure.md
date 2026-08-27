# Discovery and page closure

## Goal

Establish the minimum complete code and runtime closure for one independently
switchable page or user behavior. File proximity is not a dependency boundary.

## Evidence order

1. Confirm repository roots, current branches, manifests, locks, and available
   architecture documentation.
2. Follow repository-local discovery instructions.
3. Prefer an available code knowledge graph for architecture, symbol search,
   inbound/outbound paths, snippets, and cross-cutting queries.
4. Trace entry bootstrap functions, root components, routers, stores, HTTP clients,
   permission helpers, layout mounts, message handlers, and their callers.
5. Read exact source for high-impact symbols before deciding a disposition.
6. Use bounded text search for configuration, HTML entry templates, CSS/SCSS,
   string message types, dynamic import strings, and verified graph gaps.
7. Use runtime traces, browser network logs, and tests to resolve dynamic behavior
   that static analysis cannot prove.

Do not infer absence from a stale index. Refresh configured indexes when a known
path or symbol is missing. If no graph is available and repository policy permits
bounded search, record the reduced evidence mode and validate dynamic edges at
runtime instead of pretending the closure is complete.

## Architecture inventory

Record A and B separately:

| Surface | Inspect |
|---|---|
| Bootstrap | MPA/SPA entry, app creation, plugins, global properties |
| Navigation | HTML entries, router mode/base, nested routes, menu mapping |
| Layout | header, side navigation, content sizing, portals, z-index |
| State | Vuex/Pinia modules, persistence, cross-entry assumptions |
| Data | HTTP client, interceptors, API prefixes, caching, cancellation |
| Identity | login, cookie/domain, token refresh, roles, permission directives |
| UX platform | UI library, global CSS/reset, icons, fonts, locale, theme |
| Runtime | Node pins/engines, package manager, lockfile, build tool |
| Delivery | build outputs, public base, proxy, deploy target, fallback URL |
| Validation | unit, component, E2E, screenshot, performance, production signals |

## Migration-unit closure

Start at the real entry and recursively collect:

- root and nested components, async components, render functions, slots;
- router definitions, guards, redirects, query/hash parsing;
- Vuex modules, page-local state, local/session storage keys;
- API functions, interceptors, request/response transforms, downloads/uploads;
- directives, filters, mixins, plugins, `Vue.prototype`, event buses;
- CSS/SCSS/Less imports, scoped/deep selectors, CSS variables, fonts, images;
- iframe URLs, `postMessage` sends/listeners, parent/window/document access;
- UI, table, chart, editor, spreadsheet, drag/drop, export dependencies;
- permissions, roles, feature flags, locale keys, analytics and logs;
- tests, fixtures, mocks, business examples, operational dashboards.

Classify every closure item:

```text
reuse-B | adapt-to-B | replace | add-to-B | copy-local | retire | unknown
```

`unknown` is a blocker when it can change behavior, security, deployment,
licensing, runtime, rollback, or acceptance.

## Style closure

For every user-visible migration unit, produce a structured style closure before
design is ready. Do not treat the SFC's local `<style>` block as the boundary.
Recursively record:

- SFC/page/component style blocks and CSS/SCSS/Less entry files;
- `@import`, Sass `@use` / `@forward`, variables, mixins, functions and
  placeholder selectors;
- A global/reset/utility selectors actually used by the migrated subtree;
- CSS custom properties and their definition/fallback chain;
- scoped/deep selectors, pseudo elements and hover/focus/active/disabled states;
- runtime class/style bindings and theme/dark-mode selectors;
- fonts, images, background assets, SVG/sprite/icon-font assets and licenses;
- cascade provenance, specificity and production load order.

Each entry records `id / kind / source / evidence / disposition / target` using
the normal closure dispositions. `unknown` is blocking. Copy page-owned styles
and permitted assets when that is the smallest parity-preserving choice; convert
A-global dependencies into a page-scoped B compatibility layer. Never copy A's
global reset or theme wholesale.

## Host protocol inventory

For each iframe or micro-frontend edge, record:

- sender, receiver, message/event name and payload shape;
- source and target origin checks;
- lifecycle timing and repeated-listener behavior;
- URL/query/hash fields and encoding;
- cookie/localStorage/sessionStorage dependencies;
- parent DOM access, height/scroll/focus coordination;
- navigation, refresh, login expiry, modal, notification, download behavior;
- replacement in a B-native page and removal condition.

Distinguish behavior contracts from accidental transport. For example, “host
refreshes current data” is the contract; `postMessage({type:'refresh'})` is only
the current transport.

## Complexity and batch signal

Score relatively rather than pretending to produce universal effort estimates:

```text
closure breadth
+ nested-route count
+ state coupling
+ API and permission complexity
+ host-message count
+ special-library risk
+ visual density
+ data-volume/performance risk
+ missing-test penalty
```

Choose a pilot with representative host integration and ordinary data behavior,
but without the highest-risk spreadsheet, editable-grid, visualization, or
approval workflow. Do not choose only a trivial static page; it will not validate
the migration substrate.

## Required discovery output

For every migration unit, provide:

```text
unit_id / entry / user_value / owners
source_revision / host_revision / evidence_mode
source_mount / host_mount
routes / roles / APIs / states / messages
closure_items + disposition
runtime_and_dependency_status
visual_baseline_status
complexity / blockers / recommended_batch
rollback_target / exit_signal
```

Bind the output to the current revision pair. A later round must mark it stale
when either revision changes.

# Host integration, slicing, and iframe exit

## Land in B, not beside B

A migrated page must reuse B's application shell and platform services:

- layout, header, navigation, watermark and notifications;
- login/session expiry, permissions and role context;
- HTTP client, error handling, tracing and analytics;
- locale, icons, theme/tokens and common UI wrappers;
- build entry conventions, public base, proxy and deployment output.

Do not copy A's shell, duplicate B's login flow, or keep parent-window assumptions in
native pages.

## Migration registry

Centralize legacy/native selection instead of scattering conditions:

```ts
type MigrationMode = 'legacy-iframe' | 'native'

interface MigrationEntry {
  unitId: string
  menuCode: string
  mode: MigrationMode
  legacyUrl?: string
  nativeUrl: string
  fallbackEnabled: boolean
  rollout?: { environments?: string[]; roles?: string[]; users?: string[] }
}
```

The registry is a pattern, not a mandated schema. Reuse the host's existing feature
flag system when it provides equivalent control, auditability, and rollback.

## Replace host protocols

Classify each legacy `postMessage` or parent-window behavior:

| Contract | Native replacement |
|---|---|
| iframe height/scroll | normal B layout; delete transport |
| role/menu context | B Pinia/store or explicit props/context |
| refresh current page | page service/composable method |
| navigation | B menu or entry-local Router 4 |
| login expiry | B HTTP/session handler |
| modal/notification | B UI service |
| download/export | B service with matching browser behavior |
| cross-page durable data | URL, Pinia, or backend according to ownership |

During coexistence:

- type and validate message payloads;
- validate `event.origin` and sender identity;
- replace wildcard target origins with explicit trusted origins;
- register and remove listeners exactly once per lifecycle;
- preserve timing until both sender and receiver have switched.

## Vertical migration slices

Prefer this order for each unit:

1. Capture baseline and define contract.
2. Add the B entry and feature switch with legacy fallback.
3. Integrate B identity, HTTP, permissions, locale and layout.
4. Migrate one end-to-end behavior, including types, UI, state, API and tests.
5. Repeat behavior slices until the native entry is complete.
6. Validate functional, permission, visual and performance parity.
7. Enable native mode for a bounded audience/environment.
8. Observe, exercise rollback, then expand.
9. Remove unit-specific messages and legacy caller paths after the observation gate.

Avoid horizontal plans such as “convert all stores”, “convert all components”, then
“test everything”. They delay usable evidence and make rollback ambiguous.

## Batch selection

- Pilot: one ordinary CRUD/query page plus one representative table/permission page.
- Early batches: configuration, logs, read-only queries, standard tables.
- Later batches: dashboards, dynamic reports, editable grids, import/export.
- Last/high-control batches: spreadsheets, budgets, approvals, dense permission
  matrices, mobile-specific flows, large-data virtualized pages.

Recalculate order from discovered closure, business criticality, usage, available
test data, ownership, and shared-platform readiness. Do not hard-code project names
or page counts into this Skill.

## Rollback contract

For every unit record:

```text
switch owner / switch granularity / fallback target / rollback command or action /
data compatibility / trigger / expected recovery time / validation / expiry
```

Rollback must not require a new build when the approved rollout design promises an
immediate switch. Verify fallback in the same environment before widening rollout.
If native and legacy writes can diverge, design data compatibility or prohibit
dual-write operation explicitly.

For visual rollback evidence, prefer a page-only legacy URL. An iframe that embeds
A's complete navigation/header inside B's shell is a nested-shell defect unless an
explicit decision accepts it. Use the same deterministic fixture for source,
native, and legacy captures; assert the selected migration mode and iframe page
identity before capture.

## Exit gates

Remove a unit's iframe fallback only after:

- all approved roles and workflows pass parity checks;
- production-equivalent data volume and error paths are validated;
- native usage covers the required audience for the observation window;
- logs show no required calls to the legacy entry;
- rollback has either been exercised or explicitly retired by the release owner;
- message listeners, URL builders, proxy/config and menu references are identified
  for removal.

Shut down source A only after every unit passes these gates, operational owners
approve the release action, and archival/recovery requirements are satisfied.
Code verification alone does not authorize production shutdown.

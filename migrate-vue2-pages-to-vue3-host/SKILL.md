---
name: migrate-vue2-pages-to-vue3-host
description: >
  Use when a Vue 2 page or independently switchable user behavior must be
  natively hosted in an existing Vue 3 repository, especially when the host
  currently embeds the source through an iframe or micro-frontend boundary. Use
  when the caller needs revision-bound evidence for behavior, visual appearance,
  permissions, data semantics, runtime compatibility, or rollback of that
  cross-repository host-port. Do not use for in-place Vue 2→3 workspace upgrades,
  path/axes decision packets, or open-ended product exploration — those belong
  to vue2-to-vue3-upgrade-impact-analysis.
---

# Migrate Vue 2 Pages to a Vue 3 Host

## Purpose

Migrate one independently switchable user behavior at a time from source A to
host B while preserving observable behavior, visual appearance, permissions,
data semantics, runtime reproducibility, and rollback capability. Prefer a
strangler migration into B; keep A read-only except for explicitly authorized
defect fixes and temporary compatibility.

## Independence contract

1. Operate as a complete migration-domain Skill. Do not require, invoke, or own
   another Skill.
2. Emit `vue-migration-domain/v1` evidence. It is not a requirements, task,
   approval, release, or deployment state store.
3. When an external lifecycle exists, consume its approved scope and authorization
   as inputs, return neutral evidence, and leave lifecycle state ownership to the
   caller.
4. Remain read-only. There is no `execute` mode. Never mutate application code,
   lockfiles, feature switches, or runtimes. A plan, recommendation, or completed
   assessment is not authorization.
5. Follow repository-local instructions for code discovery. Prefer configured
   code graphs and targeted symbol tracing; use bounded static search for config,
   styles, strings, templates, or verified graph gaps.
6. Default to behavior and visual parity. A redesign, workflow change, URL break,
   permission change, or data semantic change requires an explicit decision.
7. Resolve Node, package manager, lockfile, build tools, dependency versions,
   licenses, and peer constraints inside this Skill before project commands.
8. Do not introduce Vue 2, `@vue/compat`, or source-only globals into host B unless
   a time-boxed compatibility boundary is explicitly approved.

## Select the mode

| Mode | Purpose | Mutation |
|---|---|---|
| `assess` | Compare A/B, discover closures, capture risks and recommend direction/batches | Read-only |
| `design` | Define B-native landing, vertical slices, parity, runtime, rollback and verification | Evidence only |
| `verify` | Re-run current functional, visual, runtime, build and rollback checks | No new scope |

This Skill never applies slices. An external implementer owns code mutation.
Record any caller-supplied `implementation_authorization` as a reference only;
it does not grant this Skill permission to edit A or B.

Recover the latest domain packet before every round. If source revision, host
revision, approved scope, dependency baseline, or visual baseline changed, mark
affected evidence stale and refresh it before continuing. If the migration unit,
`source_entry`, or host entry (route or HTML entry) is missing or still a
placeholder, stop and obtain the concrete values before discovery.

## Load references progressively

| Need | Read |
|---|---|
| Discover A/B architecture, entry closure, callers, stores, APIs, and complexity | `references/discovery-and-page-closure.md` |
| Convert Vue APIs, components, router, state, TypeScript, and special libraries | `references/vue2-to-vue3-transformations.md` |
| Integrate with B, slice batches, keep fallback, replace messaging, retire iframe/A | `references/host-integration-slicing-and-iframe-exit.md` |
| Preserve styles and produce standalone visual evidence | `references/visual-parity-validation.md` |
| Check Node, package manager, lockfile, build tools, licenses, and dependencies | `references/runtime-and-dependency-compatibility.md` |
| Persist neutral evidence across rounds and interoperate with an external lifecycle | `references/domain-packet-and-lifecycle-interoperability.md` |

## Core workflow

1. **Recover context.** Identify A, B, requested migration units with concrete
   `source_entry` and host entry (route or HTML entry), current revisions,
   previous domain evidence, approved scope, authorization status, deployment
   boundary, and whether the round is assess, design, or verify. Stop when unit
   or entry inputs are incomplete; do not invent them.
2. **Discover both architectures.** Establish entry points, layouts, routers,
   state, HTTP/auth, permissions, i18n, styles, runtime, build, deployment, tests,
   and active iframe or micro-frontend protocols.
3. **Choose a migration unit.** Use an independently switchable behavior or page
   entry, not an arbitrary folder or horizontal layer.
4. **Compute its closure.** Trace components, stores, APIs, directives, filters,
   mixins, assets, styles, messages, dependencies, permissions, and tests. For a
   user-visible unit, produce a complete `style_closure`: page/SFC styles,
   CSS/SCSS/Less dependencies, global selectors used, variables, fonts, images,
   icons, runtime classes, pseudo states, cascade/load order and dispositions.
5. **Freeze parity contracts.** Capture behavior, API, permission, URL, error,
   performance, accessibility, and visual baselines before source evidence changes.
   Define the comparison boundary: keep B's shell host-native by default and hold
   the migrated content root to strict A parity. Treat tables as a dedicated
   visual contract when present.
6. **Pass runtime/dependency gates.** Resolve A and B separately; choose reuse,
   adapt, replace, add, copy-local, retire, or block for every dependency.
7. **Design the B-native landing.** Reuse B's shell, auth, HTTP, i18n, UI system,
   state conventions, observability, and MPA/router pattern. Do not copy A's shell.
8. **Plan vertical slices.** Include behavior, types, integration, tests, visual
   rows, feature switch, rollback, and falsifiable completion in every slice.
   Hand the slices to the caller; do not implement them here.
9. **Record authorization only as a reference.** Copy allowed scope, forbidden
   scope, validation obligations, and rollback conditions when the caller supplied
   them. Stop and return discovery backflow if verify would need to mutate code,
   dependencies, fixtures, runtime, or feature switches.
10. **Verify freshly.** Before every visual capture, assert URL/hash, page marker,
    and deterministic fixture identity. Re-run screenshot diff, computed-style,
    semantic, interaction, permission, runtime, build, performance, rollback, and
    independent review checks. Return discovery backflow for implementation
    defects; do not edit application code. Repeat the complete affected state set;
    do not convert UI-library defaults into accepted differences. Validate JSON
    artifacts with `scripts/validate_runtime_evidence.mjs`,
    `scripts/validate_visual_evidence.mjs`, and `scripts/validate_domain_packet.mjs`.
11. **Exit safely.** Recommend removing fallback, listeners, legacy URLs/config,
    and A only after observation, rollback retirement, and release-owner criteria
    pass. The caller performs those mutations.

## Default architecture decisions

- Prefer page-by-page native migration into B over upgrading all of A and then
  moving it, unless A must remain an independently supported Vue 3 product.
- Keep an existing iframe as temporary fallback when it already works; do not add
  a new micro-frontend framework solely for the transition.
- Keep B's MPA architecture when intentional. Add Router 4 only inside entries
  that genuinely need nested client-side routes.
- Convert state by ownership: component-local stays local, page-wide becomes a
  page composable/store, and only cross-entry state becomes global Pinia state.
- Preserve Options API when it lowers risk; require TypeScript at boundaries
  without forcing an unrelated Composition API rewrite.
- Extract shared code only after repeated demand is proven.

## Hard gates

### Revision freshness

Bind every packet and authorization to `source_revision` and `host_revision`.
Changes to either revision invalidate affected closure, dependency, baseline,
design, authorization, and verification evidence. Never resume from chat memory
when a persisted packet and the repositories disagree.

### Visual parity

Require `visual-parity-evidence/v1` for user-visible migration unless an explicit
decision permits redesign. Before any visual conclusion, prove this session can
produce a **traceable image measurement**: image reading, OCR, color extraction,
pixel or perceptual diff, or an independent multimodal analyzer. If it cannot,
archive screenshots for humans only. Do not infer page identity, layout, color,
font, or icon facts from pixels or from reading CSS. Block strict-parity visual
conclusions. Design is not ready. Domain verification cannot pass.

Freeze a `visual-migration-contract/v1` and bind it via
`migration_contract.path` / `digest`. Capture at least five representative state
rows with stable browser, viewport, locale, timezone, fonts, data, animation, and
masks. Define host-shell and migrated-content comparison scopes explicitly. Assert
the route and page identity before each capture; a screenshot of the wrong page is
a failed check. For tables, require geometry, typography, wrapping, border, state,
control, and interaction evidence. Do not claim parity from code review,
functional E2E, or screenshots alone. Validate completed evidence with
`scripts/validate_visual_evidence.mjs` when a JSON evidence artifact is available.

For strict parity, require structured style evidence rather than a prose or
self-attested `computed_style=pass`: a complete style closure, per-state computed
style artifacts, page layout/typography/box/interaction metrics, semantic color
roles, and exact icon-content/geometry/paint/accessibility checks for every
contracted icon. Preserve A's migrated-content colors and icon identity through a
page-scoped B-compatible layer; do not copy A's global reset/theme or alter B's
shell tokens to repair one page. Each visual state owns a distinct A baseline
artifact recorded in a revision-bound baseline manifest.

### Runtime compatibility

Require `runtime-compatibility-evidence/v1` for A and B before install, build,
test, codemod, or migration commands. Block when Node, package manager, lock owner,
dependency target, license, registry, or command readiness is unknown or conflicted.
Validate completed JSON evidence with `scripts/validate_runtime_evidence.mjs`.

### Authorization

`implementation_authorization` is a copied reference to an observed approval. It
must record current revision binding, allowed scope, forbidden scope, validation
obligations, and rollback conditions when status is `approved`. This Skill still
does not mutate. Runtime installation, dependency installation, lock mutation,
feature switching, and production operations stay with the caller.

### Rollback

Keep a tested native/legacy selection mechanism until the observation window
closes. A fallback that cannot be exercised in the target environment is not a
rollback plan.

## Output contract

Return or update one `vue-migration-domain/v1` packet containing:

- source/host revision pair and packet digest;
- migration-unit inventory and closure dispositions;
- host protocol, runtime and dependency evidence;
- behavior, visual, permission, URL and performance parity status;
- target design, vertical slices, validation, rollback and exit criteria;
- facts, inferences, decisions, blockers and authorization reference;
- fresh verification results without claiming external lifecycle completion.

Validate a persisted JSON packet with `scripts/validate_domain_packet.mjs`; its
`packet_digest` must be the validator's canonical `sha256:<hex>` value.

Default to inline output for read-only assessment. Write a packet only to an
explicit caller-provided artifact directory. Follow
`references/domain-packet-and-lifecycle-interoperability.md`.

## Completion rules

- Mark assessment complete only when evidence-findable facts are investigated and
  material unknowns are explicit.
- Mark design ready only when every approved scenario maps to a vertical slice,
  validation row, migration step, dependency disposition, and rollback condition,
  and the visual measurement chain plus required baseline are unblocked.
- Mark domain verification pass only when current-revision functional, visual,
  runtime/build, permission, rollback, and required independent review evidence
  pass with no blocking residual, and visual evidence came from a traceable
  image measurement chain.
- Never equate domain verification with production rollout, external lifecycle
  completion, deployment, traffic switching, monitoring, or source shutdown.

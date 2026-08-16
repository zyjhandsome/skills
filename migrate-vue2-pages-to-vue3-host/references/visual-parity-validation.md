# Visual parity validation

## Default requirement

Require visual validation for behavior-preserving page migration. “Same styles”
does not require identical framework DOM, but it does require approved visual and
interaction behavior to remain within defined tolerances.

## Evidence contract

Produce a revision-bound record:

```yaml
schema: visual-parity-evidence/v1
producer: migrate-vue2-pages-to-vue3-host
authority: domain_evidence_only
source_revision: <source A revision>
host_revision: <host B revision>
assessment_mode: strict_parity | approved_redesign
migration_contract:
  path: <path to visual-migration-contract/v1 JSON>
  digest: <sha256 of that file>
baseline:
  source: <running A, screenshots, design, or approved substitute>
  manifest_path: <visual-baseline-manifest/v1 JSON>
  manifest_digest: <sha256 of that file>
  substitute_approved_by: null
comparison_boundary:
  host_shell: host_native | strict_parity | explicitly_accepted
  migrated_content: strict_parity | approved_redesign
  content_root_selector: <stable selector>
capture:
  browser: <tool/browser/version>
  viewport: <width x height>
  device_scale_factor: <value>
  locale: <value>
  timezone: <value>
  font_ready_condition: <value>
  animation_policy: <value>
  fixture_id: <stable fixture fingerprint>
difference_policy:
  forbidden: []
  tolerance_bound: []
  explicitly_accepted: []
required_states: []
style_closure:
  status: complete
  entries: []
  unresolved: []
page_style_contract:
  metrics: []
  result: not_run
color_contract:
  metrics: []
  result: not_run
contains_icons: false
icon_contract: null
contains_table: false
table_contract: null
legacy_boundary:
  detected: false
  detection_method: <registry/config/runtime inspection>
  evidence_path: <artifact path>
  evidence_digest: <sha256>
rollback:
  applicable: false
  tested: false
  nested_shell: false
  deterministic_fixture: false
  result: not_run
global_style_changed: false
global_collateral: []
review:
  mode: independent | authorized_human
  reviewer: null
final_visual_result: not_run | fail | pass
```

For a pass claim, `difference_policy.forbidden` must be empty; tolerance and
accepted-difference rows must reference existing state IDs. Candidate state rows
must assert `migration_mode=native` when a legacy boundary exists. When global
styles changed, each collateral row identifies its route and kind (`migrated` or
`existing_host`), passes identity checks, and carries candidate/diff artifact
paths plus SHA-256 digests.

Keep screenshots and diffs as files; store paths and digests in the record. Do not
embed large binaries or claim another system's visual completion.

Freeze a separate `visual-migration-contract/v1` before capture. It binds the unit
identity, fixture, required state classes, and whether a legacy iframe boundary is
required:

```yaml
schema: visual-migration-contract/v1
source_revision: <source A revision>
host_revision: <host B revision>
unit_id: <stable unit id>
native_identity:
  url: <expected capture URL>
  route: <expected hash/router state>
  marker: <expected data-visual-unit value>
fixture_id: <stable fixture fingerprint>
required_state_classes: [<at least five distinct classes>]
style_requirements:
  style_closure_required: true
  required_style_surfaces: [layout, typography, box_model, interaction]
  required_style_properties: []
  required_color_roles: []
  required_icon_ids: []
legacy_boundary_required: true | false
```

Evidence `migration_contract.path` / `digest` must point at that file. Each state
row's identity `expected` values and `capture.fixture_id` must match the contract.
Candidate and diff artifacts must be distinct across states. Every state also
references a state-specific A baseline image and a machine-readable computed-style
artifact. The top-level baseline points to a `visual-baseline-manifest/v1` that
binds all state baselines to the source revision and fixture; it is not the digest
of one reused screenshot. Validate completed JSON with
`scripts/validate_visual_evidence.mjs`.

## Capture the baseline first

Before changing or removing A, capture each representative row:

```text
id / unit / route / role / locale / viewport / browser /
data fixture or dataset / UI state / source revision /
baseline path+digest / candidate path+digest / diff policy / result
```

Require at least five meaningful rows and cover applicable state classes:

- initial loading, loaded, empty, error and permission-denied;
- forms: untouched, validation errors, filled, disabled, submitted;
- tables: default, sorted, filtered, paginated, selected, expanded, edited;
- dialogs, dropdowns, tooltips, notifications and long-content overflow;
- charts/spreadsheets at representative and large data volume;
- supported locales and desktop/mobile viewports.

Use stable data, locale, timezone, fonts, browser version, animation settings, and
capture timing. Mask only genuinely nondeterministic regions and record every mask.

Write a baseline manifest with one row per required state:

```yaml
schema: visual-baseline-manifest/v1
source_revision: <A revision>
fixture_id: <fixture fingerprint>
states:
  - id: <state id>
    state_class: <class>
    path: <baseline image>
    digest: <sha256>
```

Different states normally have different baseline artifacts and digests. Reusing
one screenshot for loading, loaded, empty, editing, and error is invalid even when
the file exists.

## Style, color, typography and icon contracts

Freeze style requirements in the visual migration contract before implementation.
The evidence must cover every contracted surface, property, semantic color role
and icon ID.

`style_closure` records page/SFC styles, preprocessor imports and symbols, global
selectors used, CSS variables, runtime classes, fonts, images and icons, including
their disposition into B. It must be complete with no unresolved item for a pass.

`page_style_contract.metrics[]` records:

```text
surface / id / selector / state_class / property /
baseline / candidate / tolerance / result
```

Use the `layout`, `typography`, `box_model`, and `interaction` surfaces when
applicable. Contract exact font-family order, available weight, font size,
line-height, box-sizing and wrapping semantics; use numeric tolerances only for
properties where a bounded geometric difference is legitimate.

`color_contract.metrics[]` records the same selector/state context plus a semantic
`role`, for example page background, body text, border, primary action, status
success/warning/error, placeholder, focus and disabled. Normalize computed colors
to a stable representation before exact comparison. Do not infer parity from
matching Sass variable names.

When `required_icon_ids` is non-empty, set `contains_icons=true` and provide an
`icon_contract`. For each icon record source and candidate asset path/digest plus a
rendered fingerprint, then exact or bounded metrics for `content`, `geometry`,
`paint`, and `accessibility`. Content covers SVG path/viewBox, sprite/glyph identity
or an equivalent deterministic fingerprint. A semantically similar replacement
with different content is a difference, not an automatic pass.

Each state links a computed-style JSON artifact with its own digest. That artifact
records the state ID, fixture ID and the actual selector/property measurements
used by the page and color contracts. Every reported candidate value must bind to
the matching state, selector and property in that artifact. A bare
`computed_style: pass` flag without this artifact is invalid.

## Define the comparison boundary

Default to a hybrid boundary for migration into an existing host:

- B's navigation, header, tabs, breadcrumbs, watermark, and other host shell stay
  host-native and are excluded from strict content-region pixel comparison;
- the migrated page content root, including tables, forms, overlays, and page-owned
  controls, remains in strict parity with A;
- portals rendered outside the content root still belong to the migrated page when
  triggered by it and require semantic and interaction validation;
- any shell or content exception requires an explicit policy entry, approver, and
  revision-bound affected rows.

Do not compare full-page screenshots as if the B-native shell must equal A. Capture
both a context screenshot and a stable content-region screenshot. Do not solve
content parity by copying A's shell or global reset into B.

## Prove page identity before every capture

Each state row must record expected value, actual value, and result for four
passing assertions before creating its artifact:

1. `url`: the actual origin, path, and query match the expected target;
2. `route`: the actual hash/router state matches the intended entry;
3. `marker`: a stable page-owned marker such as
   `[data-visual-unit="<unit-id>"]` exists and is visible;
4. `fixture`: row count, first-row key, scenario ID, or equivalent deterministic
   data fingerprint matches the frozen fixture.

Also assert the expected migration mode (`native` or `legacy-iframe`) where a
switch exists. A redirect, fallback route, login page, dashboard, missing marker,
or wrong fixture invalidates the capture even when an image was produced. Wait for
fonts, data, layout, and reduced/disabled animations before capture; use a bounded
readiness condition rather than an unexplained sleep.

## Table visual contract

When the migrated content contains a table or data grid, set
`contains_table=true` and validate it as a dedicated unit. Record baseline,
candidate, tolerance, and result for applicable metrics:

| Surface | Required checks |
|---|---|
| Container | x/y, width/height, background, border, radius, shadow, overflow |
| Header | height, cell padding, font family/size/weight/line-height, color, alignment, wrapping, sort/filter icons |
| Rows/cells | row height, column width, padding, borders, stripe/hover/current/selected states, alignment |
| Content | long text, ellipsis, wrapping, empty values, status colors, date/number formatting |
| Controls | buttons, inputs, selects, tags, checkboxes, radios, icons, pagination, tooltips |
| Advanced | fixed columns/header, horizontal/vertical scroll, expansion, tree rows, editors, virtual scrolling |

Cover the table capabilities that the source page actually exposes. The default
state set includes loading, populated, empty, error, long-content/narrow viewport,
and every supported sorted, filtered, paginated, selected, expanded, or edited
state. Do not invent unsupported interactions merely to satisfy a checklist.

Use computed styles and bounding boxes in addition to screenshot comparison. A
reasonable default geometry tolerance is 2 CSS pixels for row/header/control
height, padding, and critical column positions, but declare a page-specific
tolerance when browser rendering or grid virtualization requires another bound.
Require exact semantic agreement for font family order, font size, font weight,
status meaning, wrapping/clipping behavior, and visible control/icon identity.
New wrapping, truncation, overlap, hidden actions, wrong status color, or a changed
table density without approval is forbidden.

For Element UI to Element Plus migrations, do not assume component-name parity
implies visual parity. Measure and, when required, page-scope explicit values for:

- component size and density, table cell padding, row/header heights;
- font stack, line-height, header weight, text and placeholder colors;
- borders, radii, theme colors, hover/current/disabled states;
- button, input, tag, checkbox, pagination, loading and popup geometry;
- icon asset, viewBox, stroke/fill, size, baseline, and spacing;
- internal DOM/selectors, teleported overlays, z-index, and clipping.

Prefer B's supported components plus the smallest page-scoped compatibility layer.
Do not import A's global Element UI stylesheet or overwrite B's global tokens to
repair one page. If global CSS is unavoidable, apply the collateral gate below.

## Measurement chain

A screenshot file is not a visual conclusion. First prove a traceable image
measurement chain exists in this session: image reading, OCR, color extraction,
pixel or perceptual diff, or an independent multimodal analyzer.

If the chain is unavailable:

- keep screenshots as archive-only artifacts;
- do not infer identity, layout, color, font, or icon facts from pixels or CSS;
- stop strict-parity visual conclusions;
- design is not ready;
- domain verification cannot pass.

This blocker is independent of whether A is running. A running page without a
measurement chain still cannot support strict parity.

## Missing baseline

If the original A page cannot be captured:

1. Stop strict-parity verification.
2. Collect the strongest available substitute: production screenshots, approved
   design specifications, recorded walkthroughs, or business-owner review.
3. Obtain an explicit decision binding the substitute, affected states, allowed
   differences, and residual risk to the current revision pair.
4. Set `assessment_mode=approved_redesign` or approved substitute semantics; never
   claim exact parity.

An unapproved or incomplete substitute is a blocker.

## Difference policy

| Class | Examples | Disposition |
|---|---|---|
| Forbidden | missing controls, clipped content, changed hierarchy, wrong status color, hidden permission state, unusable focus/hover, modal behind overlay | must fix |
| Tolerance-bound | antialiasing, subpixel placement, platform font rasterization | numeric/region tolerance |
| Explicitly accepted | approved B shell spacing or component modernization | approver, revision and rows required |
| Dynamic | timestamps, random IDs, animated charts | stabilize or narrowly mask |

Do not label every Element Plus difference “expected”. Each material difference
must map to a policy entry or a fix.

## Validate at three levels

1. **Automated screenshot comparison:** same scenario, viewport, data and timing;
   retain baseline, candidate and diff artifacts.
2. **Computed-style and geometry comparison:** compare the contracted content and
   table metrics, not merely framework DOM structure.
3. **Semantic visual inspection:** hierarchy, density, alignment, wrapping, colors,
   states, overlays, scroll, focus, keyboard flow and accessibility signals.
4. **Interaction verification:** validation timing, popup placement, table editors,
   drag/drop, charts, spreadsheet input, clipboard, print and export.

Functional E2E does not replace screenshots; pixel diffs do not replace semantic
and interaction review.

## Failure and repair loop

For every failed row:

1. classify the cause as wrong identity/fixture, host global style, UI-library
   token/default, page CSS/asset, interaction state, or nondeterminism;
2. discard invalid artifacts caused by wrong identity or unstable data;
3. apply the smallest authorized page-scoped fix;
4. rerun the complete affected state set plus collateral rows when globals changed;
5. retain iteration results and set `final_visual_result=pass` only after every
   current-revision row passes.

If browser capture, image comparison, computed-style extraction, or required review
cannot run, report the visual gate as blocked/not run. Never downgrade a missing
tool or failed comparison to a prose-only pass.

Validate a JSON evidence artifact with:

```text
node scripts/validate_visual_evidence.mjs <visual-evidence.json>
```

The validator checks completeness and pass-claim integrity; it does not generate
screenshots or replace semantic review. It verifies artifact existence and SHA-256,
expected/actual page identity, unique state classes, numeric/exact table tolerances,
accepted-difference approval bindings, and legacy-boundary evidence. Do not use
placeholder paths or self-attested result flags without their underlying values.

## Legacy iframe visual checks

When rollback or coexistence uses an iframe:

- navigate through the same host entry and assert `legacy-iframe` mode;
- freeze the same fixture used by the native and source captures;
- prefer a page-only legacy target; fail or explicitly accept a nested A shell
  inside B instead of treating a double header/sidebar as parity;
- verify dimensions, scrolling, focus, overlays, authentication, and message timing;
- clear transient notifications and state before rollback capture unless the
  notification is part of that scenario.

## Global-style collateral gate

When migration changes global CSS, reset, theme variables, utility CSS config,
fonts, portal containers, z-index, or layout dimensions:

- capture at least one migrated page and two representative existing B pages;
- test dialogs/dropdowns mounted outside the component subtree;
- check table and non-table pages;
- verify scoped/deep selectors do not leak;
- inspect specificity and load order in the production build.

A migrated page passing while existing B pages regress is a failed migration.

## Completion gate

Pass only when:

- the evidence revision pair equals the current repositories;
- every required row has current artifacts and a result;
- every state baseline is present in the revision-bound baseline manifest and
  every state has a validated computed-style artifact;
- the style closure is complete with no unresolved dependency;
- page style, semantic color and contracted icon evidence cover every frozen
  requirement and pass declared tolerances;
- no forbidden difference remains;
- every state passes URL, route, marker, and fixture identity assertions;
- tolerances stay within approved thresholds;
- table-specific evidence passes whenever `contains_table=true`;
- iframe rollback has deterministic data and no unapproved nested shell when applicable;
- accepted differences bind approver, revisions, and affected rows;
- global collateral and interaction-sensitive checks pass;
- independent or authorized-human review is recorded;
- `final_visual_result=pass`.

This cannot mathematically guarantee every pixel in every client environment. It
provides a blocking, reproducible evidence standard and forbids a pass claim when
required visual proof is missing.

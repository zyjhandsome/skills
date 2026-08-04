# Visual capture contract

Use this contract for screenshots, browser-assisted inspection, or an approved
manual capture adapter. Do not install a browser framework solely to satisfy the
shape; if the target project has no reliable capture capability, keep strict
parity blocked or use an explicitly bounded consistency review.

## Assessment modes

| Mode | Requirement | Allowed claim |
|---|---|---|
| `strict_parity` | traceable pre-upgrade/reference baseline + comparable current evidence | parity pass/fail |
| `consistency_review` | approved design/token/current-main substitute standard | consistency pass/fail; never pixel parity |

## Required capture context

```yaml
capture_context:
  adapter: playwright | cypress | existing-e2e | devtools | manual
  browser: <name + version or exact environment label>
  viewport: <width>x<height>
  device_scale_factor: <number or unknown>
  locale: <locale>
  timezone: <timezone>
  theme: <light/dark/name>
  font_ready_condition: <condition>
  animation_policy: disabled | stabilized | unknown
  data_fixture: <stable fixture/account/seed>
  dynamic_masks: []
```

Unknown browser, viewport, font readiness, animation behavior, or unstable data
blocks `strict_parity`. A consistency review may proceed only when the missing
dimension cannot change the inspected result and that inference is recorded.

## Required sample states

Primary Element list page:

1. search/default;
2. search/expanded or wrapped at the target viewport;
3. table/empty;
4. table/data;
5. table/in-cell controls;
6. one Select/DatePicker/Dropdown popper open.

When the project has vxe or another secondary table in scope, capture one stable
secondary data state. Always capture one non-table page after any global reset,
Preflight, theme, import-order, or `important` change.

## Evidence manifest

Each required state records:

```yaml
- id: <stable state id>
  route: <route or file>
  state: <state description>
  baseline: <path/url/revision or substitute>
  current: <path/url/revision>
  diff: <path or manual/computed-style record>
  threshold: <numeric policy or named manual policy>
  result: pass | fail | pending | skip
  notes: <difference disposition>
```

`skip` is invalid for a required primary state unless the report records an
explicitly accepted coverage gap. Dynamic masks must identify the exact element/region and reason;
do not mask an entire table or search shell.

## Stability rules

- Wait for fonts, route data, table layout, and popper placement.
- Disable or stabilize transitions, caret blink, timers, random values, current
  date/time, and canvas animation.
- Pin locale/timezone and use deterministic fixtures.
- Treat ECharts/canvas, html2canvas output, drag ghosts, and generated documents
  as separate evidence surfaces; mask only when they are not acceptance targets.
- Save baseline/current/diff artifacts with the report revision.

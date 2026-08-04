# Baseline capture runbook (optional adapter)

Use this when Phase A is blocked only by missing runtime/screenshots. It does
**not** authorize `npm install`, dependency upgrades, or CSS edits. Those still
require an explicit caller/orchestration go outside this Skill.

## Preconditions

1. Compatible project Node installed (do not use a host that only satisfies a
   loose `engines.node` if the builder is Vue CLI 4 — prefer Node 16/18).
2. Lockfile present or freshly generated under orchestration approval.
3. Dependencies installed under that Node.
4. App boots to the primary route with stable mock/fixture data.
5. Output dir already confirmed (e.g. `<project>/.ui-stack-visual-parity`).

## Fixed capture context (write into the report)

| Field | Default to record |
|---|---|
| viewport | `1440x900` |
| device_scale_factor | `1` |
| animation_policy | `disabled` |
| font_ready_condition | `document.fonts.ready` + table layout stable |
| theme | project default (usually `light`) |
| dynamic_masks | timestamps, nprogress, cursors — never whole table |

## Primary states (minimum)

For the primary search + table route:

1. `search-default`
2. `search-filled` (or expanded/wrapped at the viewport)
3. `table-empty`
4. `table-data`
5. `cell-popper` (Select/DatePicker open)
6. one dialog/drawer open when the page has it

Secondary (only if in scope): one stable non-primary page (editor/chart/vxe).

## Directory layout

```text
<output-dir>/
  baseline/<state-id>.png
  current/<state-id>.png   # leave empty until candidate build
  diff/                    # leave empty until compare
  capture-manifest.json
  ui-stack-visual-parity-report.md
  visual-summary.json
```

Never embed base64 screenshots in Markdown/JSON.

## After capture

1. Point `baseline_source` at the baseline directory + git/content snapshot.
2. Mark required state rows `pending`→paths present; keep `final_visual_result=pending`
   until a candidate compare exists.
3. Re-validate with `scripts/validate_visual_report.py` and
   `scripts/validate_visual_summary.py`.
4. Stay in `execution_scope=analysis_only` until a revision-bound Phase B go.

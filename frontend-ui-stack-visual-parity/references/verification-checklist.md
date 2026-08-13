# Verification checklist

Copy into the report §验证清单. Mark `pass` / `fail` / `skip` with notes.
Functional smoke may run in parallel but **does not** satisfy these rows.

## Evidence integrity (required)

| Id | Check |
|---|---|
| `V0` | Assessment mode is honest: strict parity has a traceable baseline; consistency review names its substitute standard |
| `V1` | Browser, viewport, scale, locale, timezone, theme, fonts, animation and stable data are recorded |
| `V2` | Required primary states have baseline/current/diff or approved equivalent evidence |
| `V3` | Report, compact summary, capture manifest, and source snapshot refer to the same evidence revision |
| `V4` | Final visual result is `pass`; every required row is `pass` or an explicitly approved `skip` |

## Primary sample (required)

| Id | Check |
|---|---|
| `P1` | Search labels/controls: height, spacing, alignment coherent |
| `P2` | Search actions/buttons match kit size scale |
| `P3` | Primary table: header, row height, borders, scroll body OK |
| `P4` | In-cell kit controls: vertically centered, not clipped |
| `P5` | In-cell dropdowns/date poppers: position OK (Teleport/overflow) |
| `P6` | Theme CSS variables (`--el-*` or peer) still apply on the page |
| `P7` | After Preflight/policy change: spot-check **one non-table page** for collateral damage |

## Secondary sample (if vxe or other listed)

| Id | Check |
|---|---|
| `S1` | Secondary table page: no new major misalignment vs pre-fix baseline notes |
| `S2` | Secondary CSS does not break primary sample after import-order/namespace fix |

## Completion rule

Phase B `remediation_status=done` requires V0–V4 and all **non-skip** primary rows `pass`.
Secondary failures → residual risk + optional follow-up; do not silently ignore
if secondary was in the approved scope.

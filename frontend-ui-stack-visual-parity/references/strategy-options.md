# Strategy options (one primary cause, minimum remediation set)

Recommend one primary cause. Select the minimum orthogonal remediation set that
the layer peel and cascade evidence require. Alternatives may be listed but
must not be applied together without an explicit combined plan and individual
verification rows.

## A — Preflight policy (`with-tailwind` branch only)

| Id | When | Action shape |
|---|---|---|
| `preflight-off` | Tailwind present; contrast shows clear improvement; team accepts base-tag restyle risk | Disable Tailwind Preflight (or isolate) project-wide / per app |
| `preflight-keep-compensate` | Tailwind present; Preflight must stay; defects are local | Keep Preflight; compensate search/table shells with `tw-*` + kit-friendly overrides |

Do not select A ids when `tailwind.present=no`.

## B — Shell / table focus (often combined with A)

| Id | When | Action shape |
|---|---|---|
| `search-shell` | Layer peel fails at search | Fix search form layout (label width, control height, gaps) only |
| `table-chrome` | Empty table already wrong | Header/row height, borders, scroll body — primary table only |
| `in-cell-controls` | Breaks only after widgets in cells | Cell padding, line-height, popper/teleport containers |

## C — Pipeline

| Id | When | Action shape |
|---|---|---|
| `css-order` | Theme half-applies / intermittent chrome | Reorder global imports to kit → theme → secondary table → Tailwind |
| `namespace-secondary` | vxe (or peer) leaks into el-table pages | Load secondary table CSS only on those routes / scoped entry |

## D — Out of scope here (escalate)

| Id | Meaning |
|---|---|
| `ui-kit-replace` | Wrong kit major / need another library — use dependency impact skill |
| `design-restyle` | Product wants a new look, not parity — new project |
| `vue-migration-reopen` | Still on compat warnings / wrong Vue major — use vue2→vue3 skill |

## Decision record (in report)

For the primary cause and every selected remediation id, write:

- Why this id (evidence from Steps 1–4)  
- Files likely touched  
- Forbidden scope  
- Residual risk (e.g. non-table pages after Preflight off)  
- Verification rows that must pass  

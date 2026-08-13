# Diagnosis workflow

Run on the **primary sample page** (search + primary table). Keep secondary
(vxe/etc.) for later regression only.

## Step 0 — Baseline notes + stack branch

Capture current symptoms in search region, table chrome, in-cell controls and
the required states from `visual-capture-contract.md`. Strict parity requires
traceable baseline/current evidence; written bullets alone never prove parity.
Mark Fact vs Inference.

Choose the diagnosis branch from config inventory:

| Branch | When | Primary risk axis |
|---|---|---|
| `with-tailwind` | `tailwind.present=yes` | Preflight × UI kit, then shell/table/cascade |
| `no-tailwind` | `tailwind.present=no` | UI-kit major / global reset / theme / Teleport / project overrides |

Do **not** run Preflight contrast experiments on a `no-tailwind` project.

## Step 1A — Preflight contrast (`with-tailwind` only)

Goal: learn whether Preflight×UI-kit is the main axis.

| Mode | Action |
|---|---|
| Phase A (no go) | Document the exact temporary change (e.g. `corePlugins: { preflight: false }` or official EP+TW coexistence pattern). Do **not** apply until user authorizes an experiment **or** Phase B go covers it. |
| Authorized experiment / Phase B | Apply temporary toggle; compare search + table header/body only; record: clearly better / partial / no change; revert if experiment-only. |

## Step 1B — Kit / reset / theme axis (`no-tailwind`)

Goal: rank non-Tailwind causes before layer peel.

Record as Fact/Inference:

1. UI-kit major jump (e.g. Element UI → Element Plus) and class/DOM diffs on the primary sample  
2. Global reset (`normalize.css`, `reset.css`, project `* { box-sizing }`) vs kit base CSS order  
3. Theme variables (`--el-*` or peer) attachment point (`html` / `body` / `:root`)  
4. Teleport / `append-to-body` poppers escaping scoped/page styles  
5. Project global overrides targeting kit internals (`.el-button--mini`, `.cell`, etc.)

Primary cause candidates for this branch usually come from strategy ids
`css-order`, `search-shell`, `table-chrome`, `in-cell-controls`, or escalate
`ui-kit-replace` / `vue-migration-reopen` when still on the wrong major.

## Step 2 — Layer peel (same page)

Add complexity one layer at a time (conceptually or via existing variants):

1. Search region only (hide/ignore table)  
2. Empty / static table (no in-cell widgets)  
3. In-cell Element (or kit) controls: select, date, switch, input  
4. Extra: drag (`sortable`/`draggable`), dual icon sets, popovers  

Stop at the first layer that reintroduces the bulk of defects — that layer is
the remediation focus.

## Step 3 — Cascade and import-order check

If symptoms look like “half theme / wrong borders / flash of wrong chrome”,
inspect the final development and production cascade, including `@layer`,
async-route CSS, scoped selectors, specificity, source order, and computed
custom properties. Do not prescribe a universal source order.

**With Tailwind** (when layers can split):
`reset/Tailwind base policy` → `UI kit base` → `theme variables` →
`scoped secondary vendor CSS` → `app compatibility` →
`Tailwind components/utilities`.

**Without Tailwind**:
`global reset (normalize/etc.)` → `UI kit base` → `theme variables` →
`project kit overrides` → `layout/shell` → `scoped secondary vendor CSS`.

When order cannot be split cleanly, use matched-rule evidence. Record the actual
winning rule, property, source file, and selector.

## Step 4 — Cause ranking

### `with-tailwind` example order

1. Preflight × Element form/table baselines  
2. Search shell flex/gap vs kit form item widths  
3. Table row height / overflow clipping in-cell controls  
4. Cascade/import order, scoped/deep selector or theme-variable inheritance  
5. Secondary library CSS (editor/tree/DAG) — only if sample uses them  

### `no-tailwind` example order

1. UI-kit major DOM/class/theme drift  
2. Global reset × kit base (`box-sizing`, button/input/table defaults)  
3. Project overrides on kit internals / cell padding  
4. Teleport / popper theme inheritance  
5. Secondary vendor CSS — only if sample uses them  

## Step 5 — Strategy handoff

Map the top cause to one primary option in `strategy-options.md`. Ask the user
to choose if more than one option remains plausible.

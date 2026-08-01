# Dual entry and batching

## Entries

| `entry_kind` | Trigger | Output shape |
|---|---|---|
| `workspace` | One frontend root / workspace name | Full decision packet for that workspace |
| `inventory` | Multi-repo list or parent with many packages | Candidate table only → human picks batch → then `workspace` packets |

## Candidate schema (inventory row)

| Field | Notes |
|---|---|
| `workspace_id` | Stable slug |
| `root_path` | Absolute or repo-relative |
| `vue_major` | string `"2"` / `"3"` / `"unknown"` (never int) |
| `vue_version` | From lock or package.json |
| `builder` | `vue-cli` / `webpack` / `vite` / `unknown` |
| `ui_stack` | e.g. `element-ui` / `element-plus` / `none` / `other` |
| `store` | `vuex` / `pinia` / `both` / `none` |
| `blocker_count` | Rough count of Vue2-only deps |
| `suggested_batch` | Human-facing label |

Skip already-Vue3 workspaces unless the caller asks for re-audit.

## Batch identity

One analysis batch =

`entry_kind × workspace_slug × build_variant × batch_scope`

- `build_variant`: `default` or env/mode slug (`legacy-webpack`, `vite-app`, …)
- `batch_scope`: usually `full-stack`; may narrow to `build-ui` only if caller bounds it
- Directory token example:  
  `workspace/my-admin__variant-default__scope-full-stack/`

## Multi-batch root

≥2 workspace packets under the evidence dir → require `BATCH-INDEX.md` with
columns: path, workspace, variant, scope, `analysis_status`, `decision_status`,
`batch_implementation_gate`.

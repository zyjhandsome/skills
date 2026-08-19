# Dual entry and batching

## Entries

| `entry_kind` | Trigger | Output shape |
|---|---|---|
| `workspace` | One frontend root / workspace name | Full decision packet for that workspace |
| `inventory` | Multi-repo list or parent with many packages | Candidate table only → human picks batch → then `workspace` packets |
| `host-port` | Source Vue2 A + implementation target Vue3 B | Packet rooted on A inventory; §1 dual roots; path `host-port-direct`; implement-on-B only |

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

## Topology: same git repo is not automatically in-place

「单个仓库」只说明 git 边界，不决定 `topology_axis`。

| Observed layout | Entry / path |
|---|---|
| One Vue2 SPA; this workspace **is** the app being upgraded | `workspace` + in-place (`compat-big-bang` / `direct-vue3`) |
| Same git repo contains a Vue2 app **and** an already-Vue3 host (packages, apps, or iframe target) | `host-port` with two roots (`source_root` = Vue2 workspace, `implementation_target` = Vue3 host). Do **not** recommend `compat-big-bang` |
| Two git repos, iframe / 微前端收编 | `host-port` (same dual-root packet) |
| Target workspace itself is **already on Vue 3** (`vue_major=3`), or manifests say Vue3 while a caller/report describes a Vue2 baseline | Stop, or explicit `entry_mode: residual-audit` — never a Vue2-baseline upgrade packet |
| Many Vue2 workspaces, no host chosen | `inventory` first; human picks a batch |

If inventory or the current repo tree shows a distinct Vue3 host workspace,
switch `entry_kind` to `host-port` before Wave 1 path confirmation. An in-place
preset with `topology_axis: host-port` is invalid.

## Already-Vue3 / partially-upgraded target (residual-audit)

Profile `vue_major=3` on the analysis target means there is no Vue2 baseline
to upgrade. Do not force the standard template: either stop with
`analysis_status=blocked`（非 Vue2 仓）, or — when the caller explicitly wants
it — declare `entry_mode: residual-audit` in §1 and produce a residual list
(leftover Vue2-only APIs, dead build configs, silent-break hits) plus a §8
validation matrix, without recommending an upgrade path action. A `complete`
packet over a `vue_major=3` inventory without `residual-audit` fails the
validator. Partial upgrades (Vue3 manifest + widespread Vue2 source hits) are
residual-audit by default.

## Batch identity

One analysis batch =

`entry_kind × workspace_slug × build_variant × batch_scope`

- `build_variant`: `default` or env/mode slug (`legacy-webpack`, `vite-app`, …)
- `batch_scope`: usually `full-stack`; for A→B prefer `page-closure` (entry SFC +
  direct business children + page-local API/utils/styles). May narrow to
  `build-ui` only if caller bounds it
- Directory token example:  
  `workspace/my-admin__variant-default__scope-full-stack/`  
  Host-port example:  
  `host-port/vue2-a__variant-default__scope-page-closure/`

## Multi-batch root

≥2 workspace packets under the evidence dir → require `BATCH-INDEX.md` with
columns: path, workspace, variant, scope, `analysis_status`, `decision_status`,
`batch_implementation_gate`.

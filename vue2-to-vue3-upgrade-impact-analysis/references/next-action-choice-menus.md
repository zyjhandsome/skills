# Next-action choice menus

## §A — Path menu (Wave 1)

Always show the recommended path first, then alternatives with one-line why.
Also restate the three axes from §3 (`runtime_axis` / `build_axis` /
`topology_axis`). If the human wants a non-default axis mix, use `other`.

Example question (in-place):

> 推荐路径 `compat-big-bang`（默认轴：`runtime_axis: compat`，`build_axis: vite`，`topology_axis: single-cutover`）。是否确认？

Example question (A→B host-port):

> 推荐路径 `host-port-direct`（轴：`runtime_axis: direct-vue3`，`build_axis: existing-vite`，`topology_axis: host-port`；禁改 A；compat 非主路径）。是否确认？

Options (verbatim tokens):

- `proceed:path:compat-big-bang` — in-place only
- `proceed:path:direct-vue3` — in-place only
- `proceed:path:host-port-direct` — A→B / iframe 收编默认
- `proceed:path:microfrontend-coexist`
- `defer`
- `other`

When entry is host-port, put `host-port-direct` first and **omit** in-place
tokens (`compat-big-bang`, `direct-vue3`) from the offered menu. Do not offer
`proceed:path:deferred-inventory-only` unless entry is inventory-only.

Reject「继续 / 全部放行 / 别再问了 / 全部纳入」as answers; re-show this menu
until a verbatim token arrives.

## §B — Subsystem menu (Wave 2+)

For each High/blocker subsystem:

> 子系统 `ui`（element-ui → element-plus，风险 blocker）。是否按建议纳入本次升级范围并接受命名配方 `gogocode-element`（不在本阶段执行）？

Options:

- `proceed:subsystem:<id>`
- `defer`
- `other`

## §C — Inventory pick (multi-repo)

Before workspace packets:

> 巡检得到 N 个 Vue2 仓。请选择下一批分析的 `workspace_id`（可多选）或 `defer`。

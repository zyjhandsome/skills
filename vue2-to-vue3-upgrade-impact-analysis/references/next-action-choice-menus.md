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

`proceed:path:residual-audit` is **not an upgrade path** and never appears in the
menu above. Offer it only when the profile says the target is already on Vue 3
(`vue_major=3`), and then as the only proceed token, alongside `defer`:

> 本 workspace 已是 Vue 3，没有 Vue2 基线可升。可以出一份残留审计（上次迁移留下的
> compat 垫层、codemod 产物、静默失效残留），或就此停下。

- `proceed:path:residual-audit` — 只出残留审计包，不推荐任何升级路径
- `defer`

Writing that packet still requires this token verbatim; a Vue3 profile alone does
not authorize it, and no upgrade menu may list it as an alternative. Shape rules:
`report-contract.md` §residual-audit.

Reject「继续 / 全部放行 / 别再问了 / 全部纳入」as answers; re-show this menu
until a verbatim token arrives.

## §B — Subsystem menu (Wave 2+)

For each High/blocker subsystem:

> 子系统 `ui`（element-ui → element-plus，风险 blocker）。是否按建议纳入本次升级范围并接受命名配方 `gogocode-element`（不在本阶段执行）？

Options:

- `proceed:subsystem:<id>`
- `proceed:subsystem:<id>,<id>,…` — one answer for several **enumerated** ids
- `defer`
- `other`

Show every askable subsystem's own question (risk + named recipe) **before**
offering the enumerated form, then list the exact batch token the human can copy,
e.g. `proceed:subsystem:core-vue,router,ui,build`. The batch form is a typing
shorthand for ids that were each displayed; it is not a scope expansion and not a
blanket approval:

- ids must be spelled out; `all`, `*`, `全部`, ranges and empty lists are rejected;
- every id must currently be `ready` — one unknown or non-`ready` id rejects the
  **whole** token and re-shows the menu, so nothing is half-applied;
- each id still gets its own queue transition and its own Decision Record;
- ids left out stay askable — a batch answer never implies `defer` for the rest.

## §C — Inventory pick (multi-repo)

Before workspace packets:

> 巡检得到 N 个 Vue2 仓。请选择下一批分析的 `workspace_id`（可多选）或 `defer`。

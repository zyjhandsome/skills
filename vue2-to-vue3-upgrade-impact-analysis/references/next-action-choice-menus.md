# Next-action choice menus

Every menu shows the recommendation first, then each option as a copyable
verbatim token, then what changes if the human picks another one. The full
decision inventory — trigger, recommendation, reply string, cost of not
answering — is `user-decision-catalog.md`; this file only holds the wording.

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

A subsystem with an internal fork (`router` v4-vs-v5, `store` Vuex4-vs-Pinia,
`ui` staging, `i18n` mode, each residual `blockers` package, `test` runner) must
show that fork **in the same question**, with its own recommendation and its own
`confirm:` token — `user-decision-catalog.md` D15–D20:

> 同时请定：UI 库与 runtime 同批切换还是切完 runtime 再单独切？建议 `after-runtime`（同批时 Vue core 与 UI 库的改写会落在同一批调用点上）→ `confirm:ui-staging:after-runtime`

`proceed:subsystem:<id>` alone answers scope, never the fork. Recording the fork
from the recommendation without an answer is how a human who approved a scope
discovers at implementation time that the store library was swapped too.
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
  **whole** token and re-shows the menu, so nothing is half-applied. The rejection
  must quote the offending id, say why, and echo the ids that would otherwise have
  been accepted (`human-confirmation-gates.md` → Rejection shape);
- each id still gets its own queue transition and its own Decision Record;
- ids left out stay askable — a batch answer never implies `defer` for the rest.

## §C — Inventory pick (multi-repo)

Before workspace packets, show the candidate table, then:

> 巡检得到 N 个 Vue2 仓。建议先出一个仓的决策包（一批一个仓，证据才可比）。

- `proceed:batch:<workspace_id>` — 建议
- `proceed:batch:<workspace_id>,<workspace_id>,…` — 逐个列全的多选
- `defer` — 只留候选表

Same rejection rule as §B: `all` / `*` / `全部`、未知 id 或不在候选表里的 id 一律
作废**整条** token 并重出菜单，并按 `human-confirmation-gates.md` 的 Rejection shape
点名坏在哪个 id、回显本来会被接受的那几个。

## §D — Wave 0 setup confirms

Asked while profiling, before the packet is written. Each answer edits an
existing §1 / status field; none of them becomes a §7 queue row or a Decision
Record. Ask only the ones this run actually triggered — a value already supplied
in the invocation is answered, not askable.

> 分析前需要你定 3 项（其余按证据默认）：
> 1. 输出目录：建议 `<project-root>/.vue2-to-vue3-upgrade-analysis` → `confirm:output-dir`
> 2. 浏览器基线：仓内无 browserslist，建议按 Vite 默认 modern target → `confirm:browser-floor:modern`
> 3. Node 过渡：目标工具链要求 `^20.19.0 || >=22.12.0`，当前 18.20.4，建议先把旧仓在目标 Node 上跑绿再动 Vue → `confirm:node-strategy:upgrade-before-vue`

Topics and their values: `output-dir`, `workspace`, `package-manager`,
`network-mode`, `browser-floor`, `behavior-parity`, `scope`, `target-version`,
`node-strategy`, `node-target` — see `user-decision-catalog.md` D1–D10 for each
option set and what a missing answer costs.

Several open confirms may be answered in one message, one token per line. An
unknown topic, a not-currently-open topic, a duplicate topic, or blanket
language rejects the **whole** message — never half-apply it.

A rejection is never just「无效，请重发」. Quote the bad line, say why, name the open
topic it resembles when it is a near-miss (`node-targt` → `node-target`, still not
applied), and echo the lines that would otherwise have been accepted so the human
fixes one character and re-pastes. Full rules: `human-confirmation-gates.md` →
Rejection shape.

## §E — Node target and transition menu

Only when `node_compatibility_status: upgrade-required`. **Two questions, two
tokens** — a range is not a version. Name the concrete intersection and the
current baseline, never “Vue 3 需要 Node X”:

> 目标工具链交集 `^20.19.0 || >=22.12.0`（来源：`vite@5.4.11`、`@vitejs/plugin-vue@5.2.1` 的 `engines.node`），当前 `.nvmrc` / CI / Docker 均声明 18.20.4。

**E1 落到声明面的那个具体版本** — `.nvmrc`、`engines.node`、CI setup-node、
Docker 基础镜像、部署 builder 每一处都只能填一个值：

- `confirm:node-target:<resolved-active-lts-exact>` — 建议：在 `evidence_as_of` 当天从 Node 官方 release schedule 重算区间内维护期最长的 Active LTS，再解析该线当前精确补丁
- `confirm:node-target:<resolved-other-exact>` — 仅当基础镜像或部署平台确实只提供另一支；须写明约束来源与两支 EOL
- `defer`

尖括号只表示菜单生成槽位，**不得原样展示给用户**；展示时两行都替换为本次证据解析出的
可复制精确版本。不要从本参考文件复制一个长期固定的 Node 版本。

**E2 怎么从当前走到那个版本**：

- `confirm:node-strategy:upgrade-before-vue` — 建议：先证明**未改 Vue 的**旧仓在目标 Node 上能 install/build/test 跑绿，再动框架；一次只改一个变量
- `confirm:node-strategy:same-node` — 仅当交集已覆盖当前基线（此时通常根本不该问）
- `confirm:node-strategy:temporary-dual-node` — 须同时给出两条 lane 的 owner（local / CI / container / deploy）、切换条件、删除条件与缓存隔离
- `defer`

答复分别写进 §1 `selected_node_version` 与 `node_transition_strategy`，两者都
**不替代** `proceed:subsystem:build`：版本是「填哪个值」，策略是「怎么过去」，
子系统门是「这次带不带 build 一起改」。只答其中一个，剩下的就会在实施期被人替你答。

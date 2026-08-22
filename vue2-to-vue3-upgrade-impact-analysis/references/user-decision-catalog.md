# User decision catalog

每一处本 Skill 必须停下来等人答复的地方，连同**建议项**与**用户原样回复的字符串**。
分析器可以推荐，不可以替用户决定。缺答复一律按该行「未答复后果」列执行，而该列只有
两种合法形态：停在 `undecided` / gate `frozen`，或采用一个**在报告里显式标注为 default
而非 confirmed** 的安全取值。没有第三种——默认值可以用，但不得记成「用户已确认」。

三个家族。**`confirm:` 出现在两个家族里**（D1–D10 与 D15–D20），区别不在 token 形状
而在何时问、落到哪：

| 家族 | 编号 | Token 形状 | 何时问 | 答复落到哪 |
|---|---|---|---|---|
| Wave 0 设置确认 | D1–D10 | `confirm:<topic>[:<value>]` | 画像期间／写报告之前 | §1 与状态表的既有字段 |
| Wave 1 / 2+ 决策门 | D11–D14 | `proceed:path:…` / `proceed:subsystem:…` / `proceed:batch:…` | 决策包草稿之后 | §7 确认队列行 + `decision-records/`（`proceed:batch:` 例外：它只挑下一批候选，不产生队列行） |
| 子系统内部取舍 | D15–D20 | `confirm:<topic>:<value>` | 与该子系统的 Wave 2+ 提问**同一条消息** | §4 该行「说明」+ 对应 `decision-records/subsystem__<id>.md` |

三个家族都不新增队列类型：`§7 类型` 仍只有 `path` / `subsystem`。`confirm:` 家族改写的
是本契约已有的字段——`report_path`、`network_mode`、`behavior_parity_required`、
`browser_support_floor`、`batch_scope`、`lockfile_status`、`node_transition_strategy`、
`selected_node_version`，以及 §4 各子系统行的结论——所以不产生第二套状态。

**哪些分叉有机器门。** D17 的 `ui_cutover_staging` 在 §3 被硬校验；D15 `router-major`、
D16 `store-target`、D18 `i18n-mode`、D20 `test-runner` 在 §4 被硬校验——§7 队列行一旦
`decided`，§4 该行说明就必须带上对应 marker（`router_major:` / `store_target:` /
`i18n_mode:` / `test_runner:`），缺值或取值非法直接报错。所以「只回 `proceed` 把分叉
蒙混过去」现在过不了校验器。取值与写法见 `report-contract.md`。

Node 侧同样有门：D9 的 `node_transition_strategy` 必须与 `node_compatibility_status`
相符；D10 的 `selected_node_version` 在 `upgrade-required` 时必填且必须是**一个具体
版本**（写成 `^20.19.0 || >=22.12.0` 这样的区间会被拒——区间不是版本，而 `.nvmrc`、
`engines`、CI、Docker、部署 builder 每处只能填一个值）。

仍**只有协议约束、没有机器门**的只剩 D19 的逐包 `blocker`：它每包一问，没有单一字段
可校验，靠本表的「未答复后果」拦住。这一项上「校验器过了」不等于「决策答过了」。

## 提问形状（每个决策都照此输出）

1. 一句话说明在决定什么，以及**是哪条证据逼出了这个决策**（缺证据就不是决策，是待补证据）；
2. `建议：<option>` 加一行为什么；
3. 所有选项按「建议在前」逐行列成**可直接复制的原样 token**；
4. 选别的或不答会怎样（哪个字段变、gate 是否 frozen）。

硬规则：

- 一个 token 只承载一个决策。不得把「路径 + 子系统」或「视觉 + 行为断言」并成一问。
- 调用里已经给出的值**不要再问**（例如已带 `--output-dir`）。
- 建议项必须来自本次证据，不得来自「一般来说」。没有证据支撑就写 `defer` 为建议。
- 「继续 / 全部放行 / 别再问了 / 全部纳入」不是任何一个 token；照
  `human-confirmation-gates.md` 重出菜单。

## Wave 0 — 设置确认

| # | 决策 | 触发条件 | 建议项 | 用户原样回复 | 其他选项 | 未答复后果 | 落到字段 |
|---|---|---|---|---|---|---|---|
| D1 | 报告输出目录 | 调用未带 `--output-dir` | `<project-root>/.vue2-to-vue3-upgrade-analysis` | `confirm:output-dir` | `confirm:output-dir:<绝对路径>` | 全程只读，禁止写任何报告 | `report_path` |
| D2 | 分析哪个 workspace | 根下有多个前端 workspace | 含待升 `vue` 依赖、且离根最近的那个 | `confirm:workspace:<workspace_id>` | `proceed:batch:<id>,<id>`（改走多仓巡检） | 批次身份无法绑定，不出包 | §1 批次身份 |
| D3 | 包管理器 / lock 归属 | ≥2 个 lockfile，或 lock 与 `packageManager` 不一致 | `packageManager` 声明的那个；无声明时取与 workspace 同级的 lock | `confirm:package-manager:<npm\|pnpm\|yarn\|bun>` | `confirm:package-manager:none`（明确无 lock） | `lockfile_status` 记 `unparsed` → gate `frozen` | §1 lock 证据 |
| D4 | 离线继续还是补网络 | registry HEAD 与官方迁移文档 HEAD **双双**失败 | `defer` —— 离线时版本与破坏面只能是推断，不值得据此定路径 | `defer` | `confirm:network-mode:offline`（明知是推断也要出包）／`confirm:network-mode:partial`（只有一面失败） | 停在画像，不写报告 | `network_mode` |
| D5 | 浏览器基线 | 无 browserslist 配置，或配置里含旧浏览器 | 无配置且无旧浏览器用户证据时取 `modern` | `confirm:browser-floor:modern` | `confirm:browser-floor:legacy-plugin`（保留旧浏览器，`@vitejs/plugin-legacy` 进 `build` 子系统）／`confirm:browser-floor:<browserslist 原文>` | §1 锚点停在「需决策」，`build` 不能 `decided` | `browser_support_floor` |
| D6 | 是否放宽行为 parity | 用户主动要求行为变更，或 `ui` 就绪度 `replace` 使严格 parity 不可能 | `yes`（默认姿态：保留可观察行为） | `confirm:behavior-parity:yes` | `confirm:behavior-parity:no` + **逐条列出**允许变化的行为 | **按触发分支**（见下）；两个分支都不得因为难做就悄悄按 `no` 验收 | `behavior_parity_required` |
| D7 | 批次范围 | 调用未限定范围 | 原地升取 `full-stack`；A→B 取 `page-closure` | `confirm:scope:full-stack` | `confirm:scope:page-closure`／`confirm:scope:build-ui` | 按入口默认值并在 §1 写明是默认而非确认 | `batch_scope` |
| D8 | 目标版本钉死 | 需要目标面 `engines.node`；或某包 `dist-tags.latest` 已越过迁移文档区间 | 钉迁移文档区间覆盖的那个 major 的**精确版本**，并把与 `latest` 的差距记成一行证据 | `confirm:target-version:<pkg>@<exact>` | `confirm:target-version:<pkg>@<major>`（只钉 major，精确版本留实施期）／`defer` | `target_node_requirement` 与 `node_compatibility_status` 停在 `unknown` → gate `frozen` | §1 `target_node_sources`、§2 |
| D9 | Node 过渡策略 | `node_compatibility_status: upgrade-required` | `upgrade-before-vue` —— 先证明旧仓能在目标 Node 上跑绿，再动 Vue；一次只改一个变量 | `confirm:node-strategy:upgrade-before-vue` | `confirm:node-strategy:same-node`（仅当交集已覆盖当前基线）／`confirm:node-strategy:temporary-dual-node`（须同时给两条 lane 的 owner、切换条件、删除条件） | 停在 `undecided`，`build` 不能 `decided`，gate `frozen` | `node_transition_strategy` |
| D10 | Node **主版本**（落到声明面的那个具体版本） | `node_compatibility_status: upgrade-required`（`compatible`+`same-node` 不触发：没有任何声明面要改写，也就没有「填哪个值」） | 区间内**维护期最长的活跃 LTS**；同时说明另一支何时到 EOL | `confirm:node-target:22.12.0` | `confirm:node-target:<区间内其他版本>`（须说明为何不取更长维护期，例如基础镜像或部署平台只提供该版本） | 报告过不了校验：`upgrade-required` 缺 `selected_node_version` 直接报错，写成区间也报错 | §1 `selected_node_version` |

D6 的未答复后果**取决于是哪个触发条件把它问出来的**，两支不能合并：

- 触发是「用户主动要求行为变更」——未答按 `yes`，在 §1 标注为 default 而非 confirmed。
  这是安全方向：没人明确要求改行为，就按保留可观察行为验收。
- 触发是「`ui` 就绪度 `replace`」——未答停在 `undecided`，`ui` 行不得 `decided`，gate
  `frozen`。这一支**不许**回落到 `yes`：触发它的那条证据说的正是严格 parity 做不到，
  再写 `yes` 就是把一句兑现不了的承诺写进验收标准，等 Wave 5 才炸，那时基线窗口已关。

`dist-tag` 不可信是 D8 的全部理由：`latest` / `next` / `rc` 指向哪个 major 与「该读哪份
迁移文档」是两件事，任何一件都不能替另一件作答。取值当场查 registry，并写进 `evidence_as_of`。

D8 / D9 / D10 是三件事，不要合并成一问：**装哪些包的哪个版本**（D8）决定了
`engines.node` 交集；交集是**区间**，`.nvmrc` / `engines` / CI / Docker / 部署 builder
每一处却只能填**一个值**（D10）；而**怎么从当前 Node 走到那个值**（D9）是第三件。
只答策略不答版本，实施期就会各处各填一个版本；只答版本不答策略，就会有人直接把
本机 Node 换掉当作已完成。

## Wave 1 / 2+ — 决策门

| # | 决策 | 触发条件 | 建议项 | 用户原样回复 | 其他选项 | 未答复后果 |
|---|---|---|---|---|---|---|
| D11 | 已是 Vue3 的仓怎么办 | 画像 `vue_major=3` | `defer` —— 没有 Vue2 基线可升 | `defer` | `proceed:path:residual-audit`（只出残留审计包，不提任何升级路径） | `analysis_status=blocked`（非 Vue2 仓），不写包 |
| D12 | 巡检先分析哪些仓 | `entry_kind=inventory` | 先挑一个仓出包；一批一个仓，证据才可比 | `proceed:batch:<workspace_id>` | `proceed:batch:<id>,<id>,…`（逐个列全）／`defer` | 只留候选表，不出 workspace 包 |
| D13 | 迁移路径（Wave 1） | 决策包草稿完成、path 行 `ready` | 原地升 `compat-big-bang`；A→B / iframe 收编 `host-port-direct` | `proceed:path:compat-big-bang` | `proceed:path:direct-vue3`（需 §3 写 `default_path_deviation`）／`proceed:path:host-port-direct`／`proceed:path:microfrontend-coexist`／`defer`／`other`；`proceed:path:deferred-inventory-only` 只在 inventory-only 入口出现 | 路径停在 `ready`，子系统一律不得 `ready`，`analysis_status` 最多 `partial` |
| D14 | 子系统是否纳入（Wave 2+） | 路径 `decided` 后，每个 High/blocker 或 `required_for_path=yes` 行 | 全部 `proceed` —— 这些行按定义是路径的前提，deferred 一个就冻住交接 | `proceed:subsystem:<id>` | `proceed:subsystem:<id>,<id>,…`（逐个列全，见 §B 拒绝规则）／`defer`／`other` | 该行停在 `ready`，`analysis_status` 不得 `complete` |

## 子系统内部取舍（D15–D20）

`proceed:subsystem:<id>` 只回答「这次带不带它一起改」。多数子系统在被纳入之后还有
一个**分叉**，此前那些分叉是分析器替你定的。它们与该子系统的 Wave 2+ 提问**同时**
出示，各有各的 token；只回 `proceed:subsystem:<id>` 不构成对分叉的答复。

| # | 子系统 | 分叉 | 建议项 | 用户原样回复 | 其他选项 | 代价 |
|---|---|---|---|---|---|---|
| D15 | `router` | 装 v4 还是 v5 | v4 —— Vue2 仓的主迁移文档是 v3→v4；`dist-tags.latest` 已经是 v5，裸装会直接落到 v5 | `confirm:router-major:4` | `confirm:router-major:5`（等于在一次升级里叠加第二段迁移，须单列验证） | 不答就由 `npm i vue-router` 替你答，落到 latest |
| D16 | `store` | 保留 Vuex 4 还是迁 Pinia | Vuex 4 —— 它是 Vue3 可用的桥，本轮目标是升级不是换状态库 | `confirm:store-target:vuex4` | `confirm:store-target:pinia`（另一段独立迁移，建议另立项） | 混在框架升级里迁状态库，回归时无法区分是 Vue3 还是 Pinia 引起 |
| D17 | `ui` | 与 runtime 同批切还是切完 runtime 再切 | `after-runtime` —— 同批时 Vue core 改写与 UI 库改写落在同一批调用点上，两个各自正确的改写合起来可能是错的 | `confirm:ui-staging:after-runtime` | `confirm:ui-staging:with-runtime`（一次停机，但爆炸半径叠加，须为配方交集单列验证） | 不答则 §3 `ui_cutover_staging` 无值，校验器直接报错（它只认这两个取值） |
| D18 | `i18n-plugins` | vue-i18n v9 用 legacy 还是 composition mode | `legacy` —— 保留 `$t` 调用面，与「保留 Options API」一致 | `confirm:i18n-mode:legacy` | `confirm:i18n-mode:composition`（要改所有调用点） | 选 composition 等于把一次翻译层重写混进框架升级 |
| D19 | `blockers` 里每个残留包 | replace / fork / remove / defer | 逐包给建议，多数是 `replace`（有 Vue3 对应品）或 `remove`（实际未使用） | `confirm:blocker:<pkg>:replace` | `:fork` / `:remove` / `:defer` | 不答该包停在 `unknown`，`blockers` 行不得 `decided` |
| D20 | `test` | 保留现有 runner 还是换 | 保留 —— 只把 `@vue/test-utils` 升到 v2 线 | `confirm:test-runner:keep` | `confirm:test-runner:vitest`（换 runner 是独立变更） | 换 runner 后测试红了，说不清是升级还是 runner |

D19 是唯一的**三段式** token：`confirm:blocker:<pkg>:<action>` —— 因为它每个包一问，
包名本身是 token 的一部分。其余 `confirm:` 都是两段。`blockers` 行按
`subsystem-inventory.md` 的 dedupe 规则处理：已由 `ui` / `i18n-plugins` 等专属行认领的
包不在这里重复问，只问没有归属的残留包。

`build` 的分叉（Vite vs cli5-webpack5）不在这里：它是路径三轴之一（`build_axis`），
由 D13 的 path preset 决定；要非默认组合只能在 D13 回 `other`，否则校验器会拒绝
preset 与轴互相矛盾的报告。同理，`core-vue` 没有独立分叉——它的取舍就是 D13 的
`runtime_axis`（compat 还是 direct），不要再单独问一遍。

未答复的分叉写成 `<分叉项>: undecided`，该子系统行不得 `decided`。一个 `proceed`
顶两个决策，正是「用户以为只批了范围，实施期却发现状态库也被换了」的来源。

D13 的建议不是偏好而是默认路径：`compat-big-bang` 用 `@vue/compat` 兜住 `.sync`、
filters、已移除实例 API 这一族**静默失效**——它们 build 不报、lint 不报、截图也看不出来。
选 `direct-vue3` 等于放弃这层兜底，所以 §3 必须写 `default_path_deviation`：默认路径本可
吸收什么、为何本次不需要、改由哪些命名验证承接。提问时要把这句代价说出来，不能只列 id。

## `defer` / `other` 分别代表什么

| Token | 含义 | 后果 |
|---|---|---|
| `defer` | 这一项现在不决定 | 该单元不再追问，但只要它是 High/blocker 或 `required_for_path=yes`，`batch_implementation_gate` 就**永远 `frozen`**（`analysis_status` 仍可 `complete`） |
| `other` | 给的选项都不合适 | 单元保持可问。用户按 `other: <一句话说明想要什么>` 回复；分析器须把这句话翻译成**具体的 path id + 三轴**或具体子系统结论，再用原样 token 重问一次。`other` 本身永远不写成 `decided` |

## 一次性回复模板

当前开着的 Wave 0 确认可以在一条消息里一次答完，**一行一个 token**：

```text
confirm:output-dir
confirm:scope:full-stack
confirm:network-mode:partial
confirm:browser-floor:modern
confirm:target-version:vite@5.4.11
confirm:node-target:22.12.0
confirm:node-strategy:upgrade-before-vue
```

规则与 `proceed:subsystem:<id>,<id>` 一致：

- 只接受**当前确实开着**的确认项；出现未开启项、未知 topic 或 `all` / `*` / `全部`，
  **整条消息作废**并重出菜单——不得只应用其中正确的几行，半应用比全部重来更难排查；
  但作废回复必须原样引用坏在哪一行、说明为什么（未知 topic 与开着的项只差一两个字符时
  要点出它像哪个），并**回显本来会被接受的那几行**，让用户改一处重贴即可，按
  `human-confirmation-gates.md`「Rejection shape」输出；
- 每行独立生效于自己的字段；未出现的确认项保持开着，不视为 `defer`；
- 同一 topic 出现两次取作废处理，不取最后一条。

哪些**不进**这个模板：

- D11–D14（路径、子系统、巡检选批）——路径必须单独一条；子系统必须在**每条都已展示过
  风险与命名配方之后**才允许用枚举批量形式；
- D15–D20（子系统内部取舍）——它们在 Wave 2+ 与所属子系统同问，那时 Wave 0 早已关闭。
  同一条消息里可以既有 `proceed:subsystem:ui` 又有 `confirm:ui-staging:after-runtime`，
  但那是「一个子系统的两问一起答」，不是 Wave 0 模板。

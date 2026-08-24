# 报告契约

## 文件名

- `vue2-to-vue3-upgrade-report.md`（必填）
- `upgrade-summary.json`（必填，≤12 KiB）
- `inventory.json`（执行 profile 时必填）
- `decision-records/migration-path__<path-id>.md`（路径单元必填）
- `decision-records/subsystem__<subsystem-id>.md`（每个进入 §7 的子系统必填；medium/low 不会因此被强制进队）

语言：可见正文默认简体中文；枚举、包名、版本、路径、命令、URL 保持英文原文。

## 报告目录解析

1. 显式 `--output-dir`（调用里已出现即确认，不必再问 `confirm:output-dir`）
2. 否则默认候选：`<project-root>/.vue2-to-vue3-upgrade-analysis`

硬规则：输出目录只属于本 Skill。调用已含 `--output-dir <path>` 视为已确认；否则须复述绝对路径并得到 `confirm:output-dir` 后再写。路径未确认前只读分析、禁止写入。口语「写到仓库」无效。

## Wave 0 设置确认记在哪

`confirm:<topic>` 家族（输出目录、workspace、包管理器、`network_mode`、
`browser_support_floor`、`behavior_parity_required`、`batch_scope`、目标版本钉、
`node_transition_strategy`；清单见 `user-decision-catalog.md`）**不新增字段、不进
§7、不产生 Decision Record**——它们改写的是本契约已有的状态表与 §1 锚点。

§1 可另起一行 `设置确认:`，逐项记「字段 ← 用户原样 token」。该行不是校验器强制项，
但它是事后区分「用户定的」与「分析器默认的」唯一证据；缺这行时，§1 里每个本可由
用户决定的值都必须自证是默认值还是确认值。

## 多批次布局

| 批次数 | 布局 |
|---|---|
| 1 | 报告在证据目录根 |
| ≥2 | `<entry-kind>/<workspace-slug>__variant-<build-variant>__scope-<batch-scope>/vue2-to-vue3-upgrade-report.md` + 根 `BATCH-INDEX.md` |

`entry-kind`：`workspace` / `inventory` / `host-port`

## 顶层状态字段

| 字段 | 取值 |
|---|---|
| `analysis_status` | `partial` / `blocked` / `complete` |
| `decision_status` | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | `frozen` / `ready`（**仅分析交接**；≠实施授权） |
| `implementation_readiness` | `not_assessed`（本技能固定值） |
| `behavior_parity_required` | `yes` / `no` |
| `network_mode` | `online` / `offline` / `partial` |
| `report_path` | 实际报告目录（禁止单独 `.` / `./`；须与校验时目录 resolve 等价；相对路径相对进程 cwd） |
| `evidence_as_of` | 证据采集日，`YYYY-MM-DD`（registry/官方页/仓画像读取日；非“永远正确”证明） |

以下为独立输出字段；不表示任何外部流程的状态或实施授权：

| 字段 | 取值 |
|---|---|
| `schema` | `vue3-upgrade-report/v1` |
| `producer` | `vue2-to-vue3-upgrade-impact-analysis` |
| `summary_path` | 同一输出目录内的 `upgrade-summary.json` |
| `visual_acceptance_required` | `yes` / `no` |

`batch_implementation_gate=ready` 额外要求：§1 的结构化字段必须为
`lockfile_status: present`；`absent` / `unparsed` 一律保持 `frozen`。每个
High/blocker 与每个 `required_for_path=yes` 均为 `decided`（`deferred` 只允许
`complete`+`frozen`）。

`upgrade-summary.json` 额外必填（仍 ≤12 KiB；不得出现 `required_skill` /
`consumer_skill` / `handoff_skill`）：

| 字段 | 取值 |
|---|---|
| `lockfile_status` | `present` / `absent` / `unparsed`（与 §1 一致；`ready` 时必须 `present`） |
| `entry_mode` | 可选 `upgrade`（缺省）/ `residual-audit`；与 `recommended_path` 双向一致 |
| `named_recipes` | 配方 id 字符串数组（≤20）。`complete` 且路径不是 `deferred-inventory-only` / `residual-audit` 时非空 |
| `named_validations` | 实施期验证短句数组（≤20）。`complete` 时非空，且能对应 `named_recipes`；每条运行面各需一条带 `lane:<name>` 标记的验证；提出了代码改动时必须有一条含 `console-baseline` |
| `runtime_lanes` | 运行面数组，取值 `dev` / `build` / `preview` / `ssr`。提出了代码改动（`named_recipes` 非空）时必填非空 |
| `ui_behavior_contract` | 可选对象；报告 §5 写了该块时必填。`required_assertions` 为 3..20 条具体断言 |
| `recipe_constraints` | 对象数组（≤20）：`id` / `after` / `atomic`，可选 `overlaps_with`。`complete` 且 `named_recipes` 非空时必填 |
| `next_action` | `complete` → `analysis_complete`；`needs_choice` 不得用 `analysis_complete` |

`recipe_constraints` 记录**顺序与原子性**，不是任务排期：

- `id` 必须与 `named_recipes` 一一对应（不多不少，不重复）
- `after` 每项只能是保留锚点 `baseline-green` / `visual-baseline` /
  `console-baseline` / `node-lane` / `first-install` / `runtime-cutover` /
  `post-cutover`，或另一个 `named_recipes` id；
  禁止自引用，recipe→recipe 边禁止成环
- `atomic`：`yes` 表示该配方没有可停留的中间态（必须整体落地或整体回退），
  `no` 表示可按目录/模块分批并逐批 review diff
- `overlaps_with`：可选字符串数组，声明与本配方**改写同一批调用点**的其他
  `named_recipes` id（典型：Vue core codemod × UI 库 codemod 同时命中 `.sync` /
  `v-model` 绑定）。声明必须**双向对称**（A 写了 B，B 也必须写 A）——单边声明
  正是它要消除的那个无主交叉点。校验器拒绝非对称声明、自引用和未命名配方。
  凡声明了 `overlaps_with`，§8 必须为该交集单列一行验证，不能用任一配方自身的
  验证行顶替

```json
{ "id": "gogocode-element", "after": ["runtime-cutover"], "atomic": "no",
  "overlaps_with": ["gogocode-vue"] }
```

约束的判定依据见 `implementation-sequencing-constraints.md`。本阶段只描述顺序，
不产出任务、责任人或工作量。

## 必选章节（按顺序）

1. 基线与假设
2. 仓画像与依赖就绪度
3. 推荐迁移路径
4. 子系统影响清单
5. 分层影响分析
6. 风险分级
7. 确认队列
8. 验证矩阵
9. 回滚与责任人
10. 未决问题与证据缺口

章节「1. 基线与假设」必须出现结构化字段
`lockfile_status: present|absent|unparsed`，并说明 lock 路径、解析错误或缺失时的
复现性风险。即使正文另写「无 lockfile」，也不得用自然语言同义词代替该字段；
非 `present` 时 handoff gate 必须
`frozen`。
§1 可复述 `evidence_as_of`；若复述则必须与状态表一致。

§1 还必须出现以下两个锚点字段（校验器强制，禁止占位）：

- `repo_revision:` 分析时刻的 git HEAD commit（无 git 时写关键文件 digest 并注明）。
  分析包只对该仓库状态有效；下游在消费本包前必须重跑画像并比对
  `repo_revision` / `vue_major` / `builder` / `ui_stack`，漂移即判定分析 stale、
  回炉重跑，不得沿用旧包。`inventory.json` 的 `repo_revision` 与 §1 不一致时
  校验器直接报错（stale analysis packet）。
- `browser_support_floor:` browserslist / `.browserslistrc` 原文，或明确写
  「无配置 + Vite 默认 modern target 需决策」。Vue 3 不支持 IE11、Vite 默认
  target 为现代浏览器；企业内网旧浏览器约束可一票否决 direct 路径，必须在
  `build` 子系统决策中给出 target / `@vitejs/plugin-legacy` 结论。

**已是 Vue3 的入口规则：** 画像 `vue_major` 为 `3`（或大面积 Vue3 源码与 Vue2
基线描述矛盾）时，不得按 Vue2 基线模板产出 `complete` 报告。只允许二选一：
`analysis_status=blocked` 并声明「非 Vue2 仓」，或按下面的残留审计形态产出。
`inventory.json` `vue_major=3` 而报告 `complete` 且状态表未写
`entry_mode: residual-audit` 时，校验器报错。

### residual-audit（残留审计形态）

已是 Vue3 的仓没有 cutover 可规划，所以本形态把「升级路径机器」换成「上一轮迁移
留下了什么」。它是一条**可写**的路，不是只被允许提及的词：

- 状态表加一行 `entry_mode | residual-audit`。该字段缺省即 `upgrade`，所以此前
  写的所有升级包依然合法；写了就必须与路径 id 双向一致。
- §3 `推荐路径 id：residual-audit`。该 id 不吃三轴 preset（现有三轴照写，但描述的是
  **当前观测到的现状**，不是提议的切换），也不要求 `default_path_deviation`。
- §1 的 Node 矩阵照写，但 `analysis_status=complete` 不再要求解析出目标 Node
  ——本形态不提议更换工具链。
- §5 必须出现 `### residual_findings`，五个标记均非占位：
  `compat_shims_present:`（compat alias / `compatConfig` 是否仍在生效，warning 是否
  已分类）、`codemod_artifacts:`（上一轮 codemod 的错误改写特征，以及 build/lint
  为何没拦住）、`silent_break_residues:`（`.sync` 产物 prop 身份、`$options.filters`
  对象访问、`.native`、枚举改名等静默失效残留）、`runtime_lane_residues:`（只在
  dev 或只在 build 暴露的残留）、`required_cleanup_assertions:`（≥3 条唯一断言，
  逐条对应 §8）。
- 免除只针对「不提议代码改动」。一旦 `named_recipes` 非空（即本包提出了清理动作），
  `recipe_constraints` / `runtime_lanes` / `console-baseline` 命名验证与升级包**同等
  要求**——清理同样要落到两条运行面上，同样需要清理前的控制台基线做对照。
- 金样例：`fixtures/residual-audit/`（报告 + summary + inventory + 决策记录）。

§1 还必须分别记录当前与目标 Node 契约，禁止只写“Node 18 PASS”或笼统的
“Vue3 最低 Node”：

- `host_node_version:` 当前分析进程的 `node -v`
- `current_node_contract:` 当前项目 pins / `engines` / CI / 容器 / 部署声明的综合结论
- `current_node_evidence:` 逐项来源，并区分“声明”与“已知绿色基线”
- `target_node_requirement:` 已选目标工具链精确版本的 `engines.node` 可满足交集
- `target_node_sources:` `package@version → engines.node`（无字段也要明确写）及官方/registry 证据
- `node_compatibility_status:` `compatible` / `upgrade-required` / `conflict` / `unknown`
- `node_transition_strategy:` `same-node` / `upgrade-before-vue` /
  `temporary-dual-node` / `blocked` / `undecided`
- `selected_node_version:` 交集里**实际要落到** `.nvmrc` / `engines.node` / CI /
  Docker / 部署 builder 的那一个版本。`node_compatibility_status: upgrade-required`
  时**由校验器强制**：缺失报错，写成区间（含 `||` / `^` / `~` / `>=` / `x`）也报错——
  区间不是版本，`target_node_requirement` 不能顶替这一行。缺它就等于把各声明面填什么
  留给实施期各自决定，声明面必然分叉。`compatible` + `same-node` 不要求：那种情况下
  没有任何声明面被改写，可写当前基线版本或省略。

`target_node_requirement` 必须保留完整 semver 联合范围，不能把
`^20.19.0 || >=22.12.0` 简化为“Node 20+”。非
`deferred-inventory-only` 的 `analysis_status=complete` 不允许目标要求或
`node_compatibility_status` 仍为 `unknown`。
`node_compatibility_status=conflict|unknown` 时 handoff gate 必须 `frozen`；
`upgrade-required` 时 §4 的 `build` 必须为 `high|blocker`、
`required_for_path=yes`，并按普通 High 子系统进入 §7 与 Decision Record。

当 `推荐路径 id` 为 `host-port-direct` 或 `topology_axis: host-port` 时，§1 **额外**
必须出现具体值（禁止占位）：

- `source_root:` Vue2 源仓绝对或仓内可解析路径（只读）
- `implementation_target:` Vue3 宿主仓 B（实施落点）
- `forbid_source_mutation: yes`
- 建议同时写 `batch_scope: page-closure|full-stack`（页闭包为 A→B 轻量默认）
- **双根 lock：** 写 `source_lockfile_status:`（A，只读画像）与
  `host_lockfile_status:`（B）。`lockfile_status` 在 host-port **默认等于
  `host_lockfile_status`**（实施落点 B 的可复现性）。A 无 lock 不得单独把
  handoff 永久冻死——若 B lock=`present` 且队列已清，gate 可为 `ready`；
  若 B lock 非 `present`，gate 必须 `frozen`。

章节「3. 推荐迁移路径」必须出现字面：`Composition API 全仓重写：另立项，本次不评估工作量`。
章节「3」必须出现 `推荐路径 id：<path-id>`，且 `<path-id>` ∈
`compat-big-bang` / `direct-vue3` / `host-port-direct` / `microfrontend-coexist` /
`deferred-inventory-only` / `residual-audit`（最后一个仅限
`entry_mode: residual-audit`）。
章节「3」必须出现三轴标记（取值见 `migration-path-ladder.md`）：

- `runtime_axis:` `compat` / `direct-vue3`
- `build_axis:` `vite` / `cli5-webpack5` / `existing-vite`
- `topology_axis:` `single-cutover` / `coexist` / `host-port`

§4 的 `ui` 行为 `in_scope` 且就绪度是 `replace` 或 `needs-major` 时（UI 库整体替换
或大版本跨越），章节「3」必须额外出现：

- `ui_cutover_staging:` `with-runtime`（UI 库与 runtime 同批切换）或 `after-runtime`
  （runtime 先切、UI 库单独成步）。这不是排期，而是爆炸半径的主导变量：同批切换时
  Vue core 改写与 UI 库改写会落在同一批调用点上，两个各自正确的改写合起来可能是错的
  （见 `named-migration-recipes.md` 的 Recipe intersections）。校验器只认这两个取值，
  取值后的中文理由可直接续写。

`topology_axis: single-cutover` 且 `runtime_axis: direct-vue3` 时（单仓原地升但推翻了
`compat-big-bang` 默认），章节「3」必须额外出现 `default_path_deviation:`，写明默认
路径本可吸收什么（compat 对 `.sync`、filters、已移除实例 API 等静默失效族的兜底）、
为什么本次不需要或不值得，以及改由什么验证承接。禁止占位。

三轴须与 path preset 一致（例如 `compat-big-bang` ⇒ `runtime_axis: compat` +
`topology_axis: single-cutover`；`host-port-direct` ⇒ `runtime_axis: direct-vue3` +
`topology_axis: host-port`；`build_axis` 对 host-port 优先 `existing-vite`）。
`topology_axis: host-port` **禁止** `runtime_axis: compat` 作为主路径；§3 不得在未
写明「非主路径/禁止」的情况下推广 `@vue/compat` / `vue-compat`。
非默认轴组合须改选匹配的 path id，或 Wave 1 走 `other` 后把最终 path id /
轴写进 Decision Record——校验器拒绝 preset 与轴互相矛盾的报告。
§7 唯一 path 行的 id 必须与 §3 `推荐路径 id` 相同。

当 §2 出现 UI-kit、Tailwind/reset、表格/editor/tree/DAG 等视觉触发包，或
源码证据命中 scoped-style/fallthrough/theme/Teleport 风险时，状态表必须写
`visual_acceptance_required: yes`，§5 必须含 `### ui_visual_risk` 与以下非空标记：

- `triggers:`
- `legacy_selectors:`
- `css_entry_order:`
- `theme_and_teleport:`
- `tailwind_reset:`
- `primary_sample:`
- `secondary_sample:`（不适用时写有依据的 `not_applicable`）
- `baseline_status:`
- `required_visual_states:`（`visual_acceptance_required: yes` 时至少列 **5 个唯一状态**，
  逗号分隔；下游视觉门禁按状态行硬计数 ≥5，少于 5 会在基线窗口关闭后才失败。
  summary 的 `ui_visual_risk.required_states` 同样要求 5..20 项）
- `recommended_next_action:`（通用动作，不得填写其他 Skill 名称）

仅写“做视觉回归”不合规。无触发器时可写
`visual_acceptance_required: no`，但须保留可审计的证据理由。

§4 的 `ui` 行为 `in_scope` 且就绪度是 `replace` 或 `needs-major` 时，§5 还必须含
`### ui_behavior_contract`，与 `ui_visual_risk` **并列而不是合并**——懒挂载、prop 改名、
枚举改名、事件契约变化都是视觉 diff 看不见、build 也不报的行为破坏，放进视觉块等于
用截图去验证一件截图验证不了的事。以下标记非空（不适用时写带依据的
`not_applicable`）：

- `mount_timing:`（新库是否延迟/懒挂载子树，`$refs` 何时可用）
- `prop_renames:`（值契约改名，如 `visible` → `modelValue`、`:label` → `:value`）
- `enum_renames:`（size / type 等枚举取值改名或删除，旧值静默失效）
- `event_contract:`（`update:<prop>` 事件名、payload、`emits` 声明与双触发）
- `slot_contract:`（插槽名与作用域参数结构）
- `slot_content_shape:`（插槽**内容形状**约束：触发型插槽对唯一子节点的根类型有要求，
  与改名无关。放组件型根时构建与视觉都不报，只在运行时报 non-element root node
  且转发 ref 失效）
- `required_behavior_assertions:`（逗号分隔，**至少 3 条唯一断言**；每条对应 §8 一行
  交互级验证。下限只是防止用一行敷衍，真正的义务是每个非 `not_applicable` 的类别
  都要产出断言）

summary 的 `ui_behavior_contract.required_assertions` 必须同时给出（3..20 条），
否则下游只读 summary 时看不到这些断言。

章节「3」或「7」附近必须出现：`Name, never run`，**或**同时出现「命名配方」与「不执行」（二者缺一不可；仅有「命名配方」表头不算）。
章节「10」必须出现字面：`人工补搜检查`，并勾选/回答下列项（即使 profile 已扫描）：

- `slot-scope` / 旧 `slot=` 模板
- 全局 `Vue.filter` 注册
- 非 `vue-*` 前缀的 Vue2-only / 编辑器类包
- `Vue.prototype.$*` 定义与 `this.$*` 消费点（独立行）
- 对应的 `app.config.globalProperties` 或 `provide/inject` 迁移目标（独立行）
- lockfile 缺失或未解析时的版本复现风险
- `model:` 选项（自定义 v-model；必须区分父级 v-model 消费的「活」选项与
  显式 `:prop` 绑定的「死」选项，活选项标 blocker——Vue3 下静默失效不报错）
- `.native` / keyCode 修饰符（Vue3 移除后静默失效，build 不报错）
- `emits` 声明与事件双触发（未声明 emit 走 attrs fallthrough 触发两次）
- `Vue.component` / `Vue.directive` / `Vue.mixin` 全局注册与自定义指令钩子改名
- `<transition>` 过渡类名（`v-enter` → `v-enter-from`；动画静默失效）
- 静默语义变更族（v-if/v-for 优先级、v-bind 合并顺序、watch 数组、
  mixin data 浅合并、attribute coercion）
- `.sync` 修饰符与目标 UI 库 prop 身份（`:p.sync` → `v-model:p` 是正确的 Vue3
  改写，但 `p` 是**旧库**的 prop 名；同批替换 UI 库时必须按新库实际 prop 重解析，
   否则绑定编译通过却写不进任何 prop，常表现为子树不挂载、`$refs` 取不到）
- UI-kit `icon` prop 的 class/sprite 字符串（目标 prop 是否要求 Component；逐调用点
  分类为静默缺图或 mount throw，并绑定渲染/交互断言）
- `$options.filters` 对象访问调用点（与模板管道 `| filter` 是两处独立改写面，
  codemod 通常只处理管道）
- dev 与 build 运行面差异（源码内 CJS、`require.context`、多入口 URL 形态、
  `base`/`publicPath`、env 分支）：两条运行面各自的验证归属必须写明，
  不得以其一代替另一条
- router 导航静默变抛错（旧版 `push`/`replace` 的 prototype 吞错覆写与 `.catch`
  吞错在新版失效；按 name 跳转缺必填参数由静默变抛错）：吞错覆写掩盖的失败面与
   逐调用点的必填参数核对都要写明，这是**静默被移除**而非被引入的一族
- 外部全局脚本运行期契约（HTML/动态 script loader、`window.X` / `globalThis.X`
  ready/instance polling、host DOM selector、超时/清理；静态复核不得代替真实挂载后的
  ready → instance → 最小行为 round-trip）
- 目标依赖弃用告警面（迁移后落在目标大版本**已弃用**的 API 上；样式/构建工具
  自身的弃用告警）：构建与截图都看不见，只在控制台按 mount / 按编译刷量，
  处置口径见 `impact-and-validation.md` 的控制台分类

上述每一项必须有**独立行**与非空实质结果；禁止一行打包全部项，禁止仅写
`已声明` / `已检查` / `已核对` / `ok` 等空泛词。

§4 必须覆盖默认子系统全集（`core-vue` / `router` / `build` / `store` /
`ui` / `test` / `lint-ide` / `i18n-plugins` / `composition-existing` /
`blockers`）；不适用者标 `not_applicable`，不得省略。
§4 中每个 `risk` 为 `high`/`blocker` 且非 `not_applicable` 的子系统，以及每个 `required_for_path=yes` 行，必须出现在 §7 确认队列；`analysis_status=complete` 时，§7 中**每个**单元都须有对应 decision record。medium/low 未进队时不产生记录，也不要求其内部分叉。
`in_scope` 且 `high`/`blocker` 的行必须 `required_for_path=yes`。
路径未 `decided` 前，子系统行不得为 `ready`。

## 子系统内部取舍记在哪

`proceed:subsystem:<id>` 只回答「这次带不带它一起改」。若该子系统还有一个**分叉**
（router 装 v4 还是 v5、store 保留 Vuex 4 还是迁 Pinia、UI 库与 runtime 同批还是
分步、vue-i18n 用 legacy 还是 composition mode、每个 residual blocker 是
replace/fork/remove/defer），那是另一个决策，用 `confirm:` 家族单独问，取值写进
§4 该行的「说明」、对应 `decision-records/subsystem__<id>.md` 的「当前结论」和
`分叉人工答复`。`人工答复` 仍只保存 `proceed:subsystem:<id>`，不得把两个决策揉成一个字段。
清单与建议项见 `user-decision-catalog.md` D15–D20。

分叉未答复时，该子系统的 `decision-records` 不得写成已定结论，§4 说明须写
`<分叉项>: undecided`，且该行不得 `decided`——一个 `proceed` 顶两个决策，正是
「用户以为只批了范围，实施期却发现库也被换了」的来源。

**这条由校验器强制。** §7 队列行一旦 `decided`，§4 该行「说明」必须带上对应 marker，
Decision Record 的 `分叉人工答复` 还必须带上与 marker **精确对应**的 `confirm:` token；
缺值、取值非法、token 缺失或两边不一致都直接报错（`residual-audit` 入口豁免——它不装包，没有分叉）：

| 子系统 | marker | 合法取值 |
|---|---|---|
| `router` | `router_major:` | `4` / `5` |
| `store` | `store_target:` | `vuex4` / `pinia` |
| `i18n-plugins` | `i18n_mode:` | `legacy` / `composition` |
| `test` | `test_runner:` | `keep` / `vitest` |

marker 写在说明里，例如「已 proceed；`router_major: 4`」，对应 DR 必须写
`分叉人工答复: confirm:router-major:4`。`ui` 不在此表：它的分叉是 §3 的
`ui_cutover_staging`，DR token 同样会与它交叉校验。

§2 每个 `unknown` 包在 `analysis_status=complete` 前必须有且仅有一个明确 owner，owner 的
§4 说明记录 `confirm:blocker:<pkg>:<replace|fork|remove|defer>`，其 §7 行为 `decided`，
同一 token 写进 owner DR 的 `分叉人工答复`。没有已证明的专属 owner 时，owner 必须是
`blockers`。`:defer` 是已记录的用户选择，但不得得到 ready gate。所以
`i18n_mode: legacy` 不能顺带决定一个残余组件包如何处理。

## 仓画像表列（§2）

`包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据`

就绪度：`ready` / `needs-major` / `replace` / `unknown` / `unused`

## 子系统表列（§4）

`子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明`

`required_for_path`：`yes` / `no`

## 验证矩阵表列（§8）

`命名配方 | 实施期命令 | 失败证明什么 | 证据状态`

§4 中 `in_scope` 且命名配方不是 `—` 的每一配方 id，必须在本表出现至少一行。
实施期命令本阶段不执行；禁止空行或 `待补` / `tbd`。

## 确认队列表列（§7）

`单元 | 类型 | 状态 | 问题 | 选项`

- 类型：`path` / `subsystem`（**只有这两个**；Wave 0 确认不占队列行）
- 状态：`ready` / `pending` / `blocked` / `decided` / `deferred`
- 路径选项须含 `proceed:path:` 形式；子系统含 `proceed:subsystem:`
- `选项` 列须把建议项写在第一位，并保持可原样复制；`defer` / `other` 的后果见
  `user-decision-catalog.md`

## 校验

```shell
python -m unittest discover -s tests -v
python scripts/validate_report.py <report.md>
python scripts/validate_report.py --evidence-dir <evidence-dir> [--json]
```

退出码 `0` / `3` / `4`。通过只表示结构合规。

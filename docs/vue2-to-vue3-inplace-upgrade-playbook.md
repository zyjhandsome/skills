# Vue2→Vue3 单仓原地升：用户粘贴剧本

> 这不是 Skill。不要把它当独立技能加载或改任何 Skill 的内部 schema。
>
> 用途：把一次**单仓、同一 workspace 原地** Vue2→Vue3 升级拆成可粘贴的会话。
> 范围可以是**全 workspace**，也可以是**某个/几个 Vue2 页面**（含其闭包）。
> 允许按名组合 `vue2-to-vue3-upgrade-impact-analysis`、`delivery-frame-spec`、
> `delivery-plan-tasks`、`delivery-execute-verify`。视觉验收只走 Delivery G9。
>
> 禁止改 `vue3-upgrade-report/v1`、`vue3-upgrade-summary/v1`、
> `delivery-handoff/v1` 或各 Skill 验证器字段。本剧本启用 Delivery Family 的
> **会话停点覆盖**：每个 Wave 使用全新会话，只通过磁盘工件恢复；阶段结束
> 必须停止，不得同会话接力。
>
> 不要用本剧本做跨仓页面迁入或仓内 strangler。那些走
> [vue2-page-migration-playbook.md](./vue2-page-migration-playbook.md)。
> 分析 Skill 单独用法见
> [vue2-to-vue3-upgrade-impact-analysis-usage.md](./vue2-to-vue3-upgrade-impact-analysis-usage.md)。

## 0. 编排结论

```text
Wave 1  vue2 分析（只出决策包）
  → Wave 2  Frame 规格批准
  → Wave 3  Delivery Plan go
  → Wave 4  Delivery Execute
  → Wave 5  独立功能验证
```

全程使用单一模型，不按波换模型。视觉结论来自 Delivery G9 的确定性
工具证据，不以模型看图代替。模型选择不写入任何 Skill schema。

完成水位是仓内 `verified`（Wave 4 实施与 Delivery 闸门 + Wave 5 独立功能验证，
含测试与需要时的 Delivery G9），不含生产发布、切流、监控。归档、commit、push、
PR 仍须另授权。Wave 4 的 Delivery verified 不够，不能单独宣布仓内 verified。

### 0.1 Skill 职责边界

- `vue2-to-vue3-upgrade-impact-analysis` 只负责路径三维、子系统风险、确认队列
和决策包。Name, never run。不改应用代码，不写 OpenSpec 状态，报告里不得填写
其他 Skill 名称。
- Delivery Family 负责 OpenSpec、规格与实施批准、技术计划、应用代码修改、
Delivery G9、独立审查和交付状态。`delivery-execute-verify` 是唯一应用代码
mutation owner；Wave 4 实施，Wave 5 只用它做独立验证、不改应用代码。
- `delivery-explore` 不适用。主路径不插入
`frontend-dependency-upgrade-impact-analysis`，也不调用
`migrate-vue2-pages-to-vue3-host`。
- 视觉验收只走 Delivery G9。G9 未过则留在 Wave 4。仓内 verified 只在 Wave 5
独立功能验证通过后声称。

### 0.2 拓扑消歧（开写前）


| 实际形态                              | 走哪份剧本                       |
| --------------------------------- | --------------------------- |
| 一个 Vue2 SPA，全 workspace 原地升到 Vue3 | **本文**（`pages` 空）           |
| 同一 Vue2 SPA，只升某几个页面（含闭包）          | **本文**（填写 `pages`）          |
| 同一仓库里已有 Vue3 宿主，要把 Vue2 页面/包装进去   | A→B 剧本（两个 root；`host-port`） |
| 两个独立仓库，iframe / 微前端收编             | A→B 剧本                      |
| workspace 已经（部分）升级到 Vue3（`vue_major=3` 或 Vue3 源码占面） | **不走本剧本主线**：Wave 1 只允许停止或显式 residual-audit 残留审计包 |
| 只要决策包、不改代码                        | 分析 usage；不要进入 Wave 2+       |


页面范围只收窄本 change 的闭包，**不是**把页面迁到另一个 Vue3 宿主。共享
runtime/build（`vue` / router / store / Vite）仍属分析范围，因为这些页面跑在
当前 app 里。

Wave 1 若把推荐路径定为 `host-port-direct`，或画像显示实施落点不是当前
workspace：停止原地升，改走 A→B 剧本。不要在本剧本里继续 Frame。

### 0.3 决策包通用动作 → 本剧本下一步

分析报告不得点名 Skill。调用方按本表翻译：


| 决策包字段或报告字面                                                                      | 本剧本                            |
| ------------------------------------------------------------------------------- | ------------------------------ |
| `next_action: analysis_complete` 且 `batch_implementation_gate=ready`            | Wave 2 Frame                   |
| 同上但 gate=`frozen`                                                               | 停在分析；补 lock / 未决 High 后再交接     |
| 状态表 `entry_mode: residual-audit`（或 `recommended_path: residual-audit`）         | **不进 Wave 2 Frame**，无论 gate 是否 ready：它是残留清理包而不是原地升规格。本剧本主线到此结束，清理另立项 |
| `visual_acceptance_required=yes` 且 `recommended_next_action: run_visual_review` | Wave 3 把基线+G9 写入任务；Wave 4 做 G9 |
| `recommended_path: host-port-direct`                                            | 改走 A→B 剧本                      |
| 报告「3. 推荐迁移路径」字面 `Composition API 全仓重写：另立项`                                     | 本 change 的 non-goal            |


## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 在前端 workspace 打开会话。全仓升则不必填路径；只升某几个页面时在通用头写
  `pages`。
2. 启动全新会话，按当前 Wave 连续粘贴为一条消息：
   Wave 1：「每波必贴」+ Wave 1 块；
   Wave 2–5：「每波必贴」+「Wave 2–5 追加」+ 当前 Wave 块。
3. 当前 Wave 完成并停止后，打开新会话粘贴下一 Wave。
4. 用户只回答分析确认 token、规格批准和实施批准。不要手工搬运 JSON 或 digest。

### 1.2 会话通用头——按 Wave 粘贴；仅覆盖项可省略

Wave 粘贴块只补充本波 Skill、应已存在的上游工件、增量门禁和结束产物。
通用头已覆盖的检索、边界、回流字段、完成判定和停点不要复述。

#### 每波必贴

```text
这是一个全新独立会话，不得使用其他会话的聊天记忆补结论。
全程使用单一模型；本波内不换模型。
本会话只执行随后指定的一个 Wave；写盘校验后立即停止，不要加载或执行下一个 Skill。
不要使用 delivery-explore，不要调用 migrate-vue2-pages-to-vue3-host。
Wave 粘贴块只补充本波 Skill、应已存在的上游工件、增量门禁和结束产物；
通用头已覆盖的检索、边界、回流字段、完成判定和停点不要复述。

默认（仅 CONFIG 不存在且用户未覆盖时使用）：
- workspace = 当前本地仓库 / workspace（含待升级的 package.json）
- pages = 空 → 全 workspace（batch_scope=full-stack）
- target_vue_version = 3.5.41
  （已精确到补丁；禁止 latest / next / rc / beta；Wave 1 校验该版本在 registry
  可解析后写入 CONFIG，其后全程不变）
  该默认钉核对于 2026-08-21（当时 `vue@latest` = 3.5.41）。Wave 1 发现 3.5.x
  线已前移时，只**提示用户**可以覆盖并继续用本默认值；agent 不得自行改钉——
  静默漂移会让同一 CHANGE_ID 的各波装到不同补丁上。
  同时不得把这个钉说成"当前最新"：它是一个**核对日期已知的固定值**，随时间必然
  落后。要装最新补丁，只能由用户在通用头显式写出那个精确补丁号。

可选覆盖（需要时才写）：
pages = <路由或文件，多个用逗号或换行；填写则 batch_scope=page-closure>
workspace = <仅当当前打开的不是前端根时>
target_vue_version = <仅在用户明确指定其他精确版本时覆盖>

自动派生并保持稳定：
- CONFIG 已存在：先从 CONFIG 恢复 workspace、pages、target_vue_version 和派生路径；
  本次未显式填写的覆盖项不重新套默认值
- TARGET_VUE_VERSION = CONFIG.target_vue_version（CONFIG 存在时），否则为
  target_vue_version
- SLUG：pages 有值则由页面标识规范化（多个用 + 连接，过长截断并加短哈希）；
  否则用 workspace 目录名
- CHANGE_ID = vue2-to-vue3-inplace-<SLUG>
- CHANGE_DIR = <workspace>/openspec/changes/<CHANGE_ID>
- EVIDENCE_ROOT = <CHANGE_DIR>/evidence
- OUTPUT_DIR = ANALYSIS_ROOT = <EVIDENCE_ROOT>/vue2-to-vue3-upgrade
- G9_ROOT = <EVIDENCE_ROOT>/delivery-visual
- CONFIG = <EVIDENCE_ROOT>/inplace-run-config.json
CONFIG 存在后以其中记录为准；只有本次**显式填写**的值与配置不一致时停止。
每波开始先检索 <workspace>/openspec/changes/ 下已有的 vue2-to-vue3-inplace-*
目录：存在且与本次派生 CHANGE_ID 不同（例如 pages 改动导致 SLUG 变化）时停止
询问用户，不得静默派生新 CHANGE_ID 分叉第二条线。同一 workspace 同时只允许
一个 inplace change。
CONFIG 已记录旧分析路径时沿用，不要并行维护 workspace 根
.vue2-to-vue3-upgrade-analysis。

固定边界：
- 任何包都不得用 dist-tag 解析版本（latest / next / rc / beta / edge）。dist-tag
  会指向非预期版本：vue 的 rc 指向 3.6.x 预发布（Vapor 线），vue-router 的
  next 反而指向五年前的 4.0.13，而其 latest 已是 v5 主版本——裸装 vue-router 会
  解析到 5.x 而不是 4.x。安装目标 major 必须显式钉死，并在报告或任务里留下依据。
  这些具体数字随时间变化，本行只说明 dist-tag 不可信；实际取值须当场查 registry。
- 任何 install 之前先打印 NODE_ENV 与 npm config get production（yarn/pnpm 用等价
  配置项）。任一为 production / true 时 install 会静默跳过 devDependencies，构建
  与 lint 的 bin 随之缺失，报错表现为「命令不存在」而不指向环境；此时必须显式
  NODE_ENV=development 或 --include=dev 重装，并把该处置写进本波证据。这条对
  Wave 4 的实施安装和 Wave 5 的 frozen install 同样适用。
- 单仓原地升。pages 只收窄本 change，不是 A→B host-port，也不是页面闭包迁入。
- 默认行为 parity；保留 Options API。Composition API 全仓重写另立项。
- Vue 3.6 / Vapor mode 不在本轮范围。3.6 线目前只有预发布，任何 rc/beta 都不得
  进入本次升级；本轮目标固定在 3.5.x 的精确补丁号（默认 3.5.41）。
- 仅 Wave 4（delivery-execute-verify）可修改应用代码并安装依赖、运行命名配方；
  Wave 1–3 与 Wave 5 对应用代码只读。分析阶段 Name, never run。
- Wave 5 可启动/停止干净服务、重跑验证、刷新 Codebase Memory 索引与 G9 证据；
  lock/Node/包管理器变化时允许 frozen install，不得跑实施配方或改 tasks 勾选。
- 保护 workspace 里已有的本地改动。
- 部署、生产切流、监控不属于本轮。禁止 Quick。本变更固定 High。
- Wave 1–4 不得声称仓内 verified。

自动恢复以随后 Wave 块「应已存在」行为准。已完成 Wave 的工件缺失/损坏/stale
则停止并指出重跑 Wave，不要求用户手工提供内容。

失败回流最小字段（alignment_backflow）：
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point
```

#### Wave 2–5 追加（Wave 1 不要贴）

```text
不要让 vue2 分析 Skill 改代码或重开决策包。

代码检索：默认 Codebase Memory MCP
（search_graph → trace_path → get_code_snippet；复杂闭包 query_graph；
结构 get_architecture；模板/导入/字符串 search_code）。
仅 package.json、锁文件、构建/样式配置，或 MCP 为空/明显不完整时，才降级到
文件读取或 rg，并记录 query、缺口和原因。不得因图谱没有 Route 节点断言路由不存在。

Node 必须拆成两面：当前项目实际/声明的 Node 契约，以及所选目标工具链精确
版本的 engines.node 交集。不得写死“Vue3 最低 Node X”，也不得只看本机
node -v；同时覆盖本地 pin、engines、CI、Docker/devcontainer、部署构建环境。
vue 的 resolved version 必须等于 TARGET_VUE_VERSION；路径涉及
@vue/compat / @vue/compiler-sfc / @vue/server-renderer 时，这些包的
resolved version 必须完全一致。manifest 是否保留范围符号遵循已批准规格，
但 lock 不得漂到其他 Vue 版本。
框架与构建链同批替换时锁文件 digest 必然变化，这不等于漂移：漂移的判据是适用包
resolved version 不等值或出现其他 Vue major，不是 digest 不变。凡以「digest 未变」
表述的复用条件（如不重复安装）只用于判断是否需要再装，不得反过来当作漂移证据。
G9 与控制台采集脚本自身的工具链依赖（无头浏览器驱动等）不计入应用锁文件的
digest 判定，也不得为了采集把它们写进应用 dependencies。
@vue/compat 的 peer 是精确版本而非范围，补丁号对不上会在安装期直接失败或告警，
不会静默漂移——按硬约束对待，不要只靠事后核对 resolved version。

router / i18n / store 等会被实际安装的包，其目标 major 必须显式钉死并有依据：
dist-tags.latest 可能已越过迁移指南所在的区间（例如 vue-router 的 latest 已是
v5，而 Vue2 仓的主迁移文档仍是 v3→v4）。裸装解析到哪个 major 与该读哪份文档是
两件事，不得互相替代。

visual=required 时 G9 用 delivery-visual-evidence/v1，目录 G9_ROOT。
外部分析视觉字段只允许引用 G9 白名单：baseline_state_ids、identity_route、
identity_marker、comparison_boundary、style_closure_status、color_metrics、
typography_metrics、icon_identity、table_metrics、rollback_fixture。

仓内 verified（仅 Wave 5 在独立功能验证通过后才能声称）须同时：
分析包 complete 且交接时 gate=ready；路径仍是原地升；规格批准与实现 go 绑定当前
revision；权威任务完成；Wave 4 已写出绑定当前 revision 的 Delivery verification
与 verified handoff；Wave 4 Fresh Verification 与 High 独立审查通过；Wave 5 在
全新会话对当前 revision 重跑 named_validations、规格场景与升级后功能冒烟，且不
混用 Wave 4 旧 pass；visual=required 时 G9 pass 且 required 状态未被任何 Wave
单方降级（assessment_mode / diff_policy / structural_parity_metrics 仍是 Wave 2
已批准的值，current 与基线同 capture_conditions）；回滚演练证据存在（升级前
revision 在旧 lane frozen install/build 通过）；存在 dev 运行面时 dev 与 build
两条运行面各自独立跑过完整冒烟并各有证据；console-evidence.json 按每路由 ×
每运行面 fresh page 口径采集，且已与 console-baseline.json 同 route 同 runtime_lane
逐条对比、每条 error 归入 regression 或 pre-existing 并无未处置项（error 记
accepted-residual 须用户显式批准）；交互断言清单逐条有结果；Wave 3 记录的人工前置
（后端/Mock、测试账号与权限、稳定数据）全部兑现，未兑现项已逐条列入
inrepo-verification.md 的覆盖声明并经用户显式接受；结论落盘
EVIDENCE_ROOT/inrepo-verification.md，其中含覆盖声明（跑了哪些运行面、哪些路由、
哪些已批准交互未被实际执行及原因）；
Vue resolved version 与 TARGET_VUE_VERSION 一致；Composition 全仓重写仍在
non-goals；无 blocking residual。仍不 archive/commit/push/PR/部署。
```

### 1.3 工件恢复矩阵


| 工件组                         | Agent 用途                                 | 用户操作     |
| --------------------------- | ---------------------------------------- | -------- |
| `ANALYSIS_ROOT`             | 分析决策包、summary、inventory、decision-records | 确认路径；看摘要 |
| `CONFIG`                    | 同一 change 的业务输入和派生路径                     | 不操作      |
| OpenSpec 工件与 `handoff.json` | 规格、批准、计划、任务和交付状态                         | 批准时看摘要   |
| `G9_ROOT`                   | Delivery G9 视觉验收                         | 最终看摘要    |


默认不得在 `CHANGE_DIR` 外另建第二套 delivery 状态，也不得把分析包写到
workspace 根 `.vue2-to-vue3-upgrade-analysis`。分析报告默认落在
`ANALYSIS_ROOT`（`<CHANGE_DIR>/evidence/vue2-to-vue3-upgrade`）。Wave 1
只创建该证据目录并写入 `CONFIG`，不写 OpenSpec 状态。Wave 2 在同一
`CHANGE_ID` 上创建或恢复 change（接管 Wave 1 留下的 evidence-only 目录），
把报告 path+digest 记为 `external_artifacts`，不把分析 schema
写进 Delivery 状态。新增分析报告不会使 Frame 批准失效；改 proposal/spec 仍会。


| Wave      | 应当存在的主要上游工件                                                   |
| --------- | ------------------------------------------------------------- |
| 1 分析      | 无；不要求 OpenSpec / Memory。可先创建 `ANALYSIS_ROOT` 目录           |
| 2 规格批准    | 定稿决策包（`analysis_status=complete`）；OpenSpec + Memory 从此波开始是硬前提 |
| 3 Plan    | 已批准 Frame 规格、分析 path+digest、Frame handoff                     |
| 4 Execute | design/tasks、Plan handoff、实现闸门；`visual=required` 时含 G9        |
| 5 独立功能验证 | Wave 4 verification / verified handoff / G9、当前代码、CONFIG     |


Wave 1 **不**要求 OpenSpec 或 Codebase Memory。Wave 2–5 硬前提失败时用
Delivery 固定三行报告停止，不降级。

## 2. Wave 1：vue2 分析（只出决策包）

新会话粘贴「每波必贴」，再粘贴：

```text
本波：显式使用 vue2-to-vue3-upgrade-impact-analysis。只出决策包。
不改代码、不跑 codemod、不写 OpenSpec 状态（proposal/spec/design/tasks/handoff），
不 init OpenSpec，不调用 create_change。

应已存在：无。不要求 OpenSpec / Memory。
入口：单 workspace；project-root = workspace。--output-dir OUTPUT_DIR
（CHANGE_DIR/evidence/vue2-to-vue3-upgrade）。禁止再问 confirm:output-dir。
本波只创建 ANALYSIS_ROOT 与 CONFIG（及必要父目录）；不要写到 workspace 根
.vue2-to-vue3-upgrade-analysis。
pages 空 → batch_scope=full-stack。
pages 有值 → batch_scope=page-closure（页面+闭包+共享 runtime/build；其余 non-goal）。

目标 Vue = TARGET_VUE_VERSION。用户未覆盖时固定为 3.5.41；本波向 npm registry
校验该精确版本可解析后写入 CONFIG 与报告；不得写 latest、不得写「当前最新
3.x」、不得凭记忆改填其他版本号、不得落到 3.6 线的任何预发布（alpha/beta/rc）。
校验失败或该版本不可用时停下询问用户，不得自行改钉其他版本（包括 3.5.x 线的
其他补丁）。registry 显示 3.5.x 线已有更新补丁时，把「默认钉 vs 线上最新」作为
一行提示回显给用户，由用户决定是否覆盖；未覆盖就继续用默认钉，不得自行更换。
「2. 仓画像与依赖就绪度」与「3. 推荐迁移路径」必须写出该精确补丁号。
CONFIG 一旦记录，后续各 Wave 一律沿用，不得因为上游发了新补丁而漂移。
compat 对齐 vue / @vue/compat / @vue/compiler-sfc 同版本；direct 至少 vue 与
@vue/compiler-sfc；SSR 再对齐 @vue/server-renderer。版本不可用或冲突：gate=frozen。

router / store / i18n / ui / test 等会被实际安装的包，报告须分别写出「迁移文档区间」
与「安装目标 major」，后者按 evidence_as_of 当天的 registry 元数据解析并注明来源；
两者不一致时（例如 vue-router 的 latest 已越过 v4）把差距记为决策，不得默认取其一。
跨子系统的 peer 约束（router×build、router×store、i18n×Node 等）在对应子系统行与
决策记录里双向登记，不得只写在一侧。

host-port-direct、另一 Vue3 宿主、iframe 收编、topology_axis=host-port、
或实施落点不是当前 workspace：停止本剧本，不要进入 Wave 2，不要加载其他剧本。

画像 vue_major=3（workspace 已是/部分是 Vue3）：停止本剧本主线；只有用户显式
要求时才产出残留审计包——按分析 Skill 报告契约的 residual-audit 形态写
（状态表 entry_mode: residual-audit + 「3.」推荐路径 id: residual-audit +
「5.」residual_findings），不得按 Vue2 基线写升级决策包。残留审计不接本剧本
Wave 2，清理另行立项。

确认队列里的 Wave 1 / Wave 2+ 是分析 Skill 的**提问批次**（先路径、后子系统），
与本剧本 Wave 1–5 的会话阶段不是同一套编号；本剧本 Wave 1 覆盖该 Skill 的全部
提问批次。
报告「1. 基线与假设」必须记录 repo_revision（分析绑定的 git HEAD）与
browser_support_floor；下游各 Wave 以此判定分析是否 stale。

报告「3. 推荐迁移路径」必须出现字面：
Composition API 全仓重写：另立项，本次不评估工作量

summary 必须给出 recipe_constraints：每个命名配方一行 after（保留锚点或另一配方 id）
与 atomic；两个命名配方改写同一批调用点时（典型：Vue core codemod × UI 库 codemod
同时命中 `.sync` / `v-model` 绑定）双向写出 overlaps_with，并在报告「8. 验证矩阵」
为该交集单列一行验证。inventory 必须含
source_impact_signals.interaction_assertion_candidates（逐点定位 model_option /
native_modifier / keycode_modifier / transition_component / sync_modifier /
options_filters_access）。
candidates.truncated=true 说明清单不完备，须在本波补一次全量检索或写入证据缺口。

运行面必须拆成两条：dev server 与 build 产物是两套模块解析、入口/URL 形态与 env
处理，一条绿不构成另一条的证据。报告须记录本 workspace 实际存在哪些运行面，
多入口（MPA）证据既落到 rollupOptions.input 也落到 dev URL 形态；summary 的
runtime_lanes 逐条列出，named_validations 每条运行面各有一行 lane:<name> 验证。

UI 库整体替换或跨大版本时（「4. 子系统影响清单」的 ui 行 in_scope 且就绪度
replace / needs-major），
报告「3.」必须写出 ui_cutover_staging（with-runtime / after-runtime），「5.」必须写出
与 ui_visual_risk 并列的 ui_behavior_contract（mount_timing / prop_renames /
enum_renames / event_contract / slot_contract / required_behavior_assertions，
断言至少 3 条），summary 同步给出 ui_behavior_contract.required_assertions。
懒挂载、prop 改名、枚举改名这些是视觉 diff 看不见、build 也不报的行为破坏，
不得并进视觉块用截图顶替。
若把单仓原地升的路径定为 direct-vue3（推翻 compat-big-bang 默认），
「3.」必须写出 default_path_deviation：默认路径本可吸收什么（compat 对 .sync、
filters、已移除实例 API 等静默失效族的兜底）、为何本次不需要或不值得、
改由哪些命名验证承接。
凡命名了 cutover 之后的功能验证，就必须同时命名 console-baseline：升级前 revision
在与升级后**同一采集条件**下的控制台输出。缺这条基线，事后无法区分环境噪声与
升级回归，只能靠主张。

确认队列按 Skill 用 proceed:path:<id> / proceed:subsystem:<id>。
报告与 summary 不得填写其他 Skill 名称。

本波结束前写入 CONFIG（workspace、pages、target_vue_version、派生路径，
不含批准），并向用户回显 CHANGE_ID。CHANGE_DIR 在 Wave 2 之前只是证据目录
（没有 proposal.md 属预期，由 Wave 2 接管补齐 OpenSpec 槽位）；若用户决定
放弃升级，应删除整个 CHANGE_DIR，避免半截目录阻塞后续变更的路径重叠检查。

gate=ready 且仍是原地升：说明下一步 Wave 2，然后停止。
gate=frozen：说明缺口，不要进入 Wave 2，然后停止。
```

## 3. Wave 2：Frame 规格批准

新会话粘贴「每波必贴」和「Wave 2–5 追加」，再粘贴：

```text
本波：显式使用 delivery-frame-spec。不要进入 Plan/Execute。
不要再次执行 vue2 分析 Skill（只读已定稿的 ANALYSIS_ROOT）。
框架升级 / 迁移类变更，固定 High，禁止 Quick。本波不得修改应用代码。

应已存在：定稿决策包（analysis_status=complete，batch_implementation_gate=ready）。
缺失或 gate=frozen：停止，回 Wave 1。OpenSpec + Memory 本波起为硬前提。
硬前提：workspace 的 OpenSpec 已初始化；Codebase Memory 对 workspace 可查询。
索引缺失时先 index_repository。openspec: cli-only 时按 Frame Skill 固定三行报告
并询问 initialize_repo，不得发明平行 Markdown 状态。

先读 ANALYSIS_ROOT/upgrade-summary.json；再打开
ANALYSIS_ROOT/vue2-to-vue3-upgrade-report.md 的「1. 基线与假设」「3. 推荐迁移路径」，
其他章节按 summary 点名读取。

分析包时效检查（硬前提）：只读重跑 vue2-to-vue3-upgrade-impact-analysis 的
scripts/profile_inventory.py 生成临时 inventory（不覆盖 ANALYSIS_ROOT），与
ANALYSIS_ROOT/inventory.json 逐字段对比 repo_revision、vue_major、builder、
ui_stack、lockfile_digests（锁文件 sha256，由脚本产出），并核对报告
「1. 基线与假设」的 repo_revision 与 inventory 一致。脚本不可用时降级为直接
对比 inventory.json 与当前仓库的 git HEAD、package.json vue 主版本、锁文件
sha256，并记录降级原因。任一漂移（例如仓库已被改成 Vue3 而分析仍描述 Vue2
基线）：判定分析 stale，停止本波，回 Wave 1 重跑，不得沿用旧决策包开规格闸门。
batch_implementation_gate=ready 不是实施授权，也不是规格批准。
「1. 基线与假设」Node 未知/冲突，或 build 的 Node 未 decided：停止，回 Wave 1。
「3. 推荐迁移路径」目标 Vue ≠ TARGET_VUE_VERSION：停止，回 Wave 1，不得在 Frame 改版本。
summary.recommended_path 为 host-port-direct，或 topology 不是 single-cutover：
停止本剧本，不要开规格闸门，不要加载其他剧本或 migrate Skill。
向用户说明拓扑不是单仓原地升。

创建或恢复唯一 CHANGE_DIR（与 Wave 1 同一 CHANGE_ID）。若 ANALYSIS_ROOT
已有定稿分析包，恢复该目录并补齐 OpenSpec 槽位，不要另建 change 或改 CHANGE_ID。
校验并补全 Wave 1 写入的 CONFIG（缺失时按报告与用户输入重建；不含批准）。
将分析报告与 summary 记为 external_artifacts（path+digest）。

范围：pages 空 = 全 workspace；pages 有值 = 这些页面+闭包+共享 runtime/build，其余 non-goals。
规格钉死 TARGET_VUE_VERSION，适用的 vue / @vue/compat / compiler-sfc / server-renderer
resolved 必须一致；禁止 latest。
non-goals 必须含：Composition API 全仓重写；Vue 3.6 / Vapor mode；生产发布/切流；
compat 若选用须写移除日期或退出条件。

quality_profiles.visual：分析 visual_acceptance_required=yes 或代码/配置出现
UI-kit、Tailwind/reset、表格混用、scoped-style 风险时为 required；否则按证据写明不需要。
required 时基线须在改 vue/依赖之前捕获；G9 目录 G9_ROOT。
required 时 required_visual_states 必须至少 5 个唯一状态——下游 G9 校验器按
证据行硬计数 ≥5；分析包不足 5 个时在规格批准前补足并写入已批准 spec，
不得留到执行期（那时基线窗口已关闭）。

required 时已批准 spec 还须同时写明下列四项，缺一不得通过规格闸门。它们定义 G9
的判据本身，留到执行期再定等于让 Wave 4 单方定义验收标准：
- assessment_mode：strict_parity 或 consistency_review（G9 证据的必填枚举）。
  UI-kit 整体更换（如 element-ui→element-plus）存在原生视觉系统差异，可以选
  consistency_review，但必须在本波声明并写明理由；Wave 4 不得自行改写该值。
- diff_policy：逐类列出哪些差异属 allowed native adjustment（例如弹层挂载点变化、
  空数据下分页隐藏），哪些属 forbidden failure。未归类的差异按 failure 处置。
- structural_parity_metrics：哪些结构计数是 parity 判据，哪些属数据依赖态、允许
  随后端数据缺失漂移。白名单之外的计数差异一律按 failure 处置。
- capture_conditions：基线与升级后必须同条件采集——同运行面（dev / build 产物静态
  serve，二者不可互替）、同端口策略、后端可用性一致、同 locale/timezone/theme。
  条件不一致时 404、SecurityError 之类的差异无法区分是环境还是升级回归，
  G9 结论不成立。

visual 是否 required，本波都必须批准一份控制台基线契约（与 G9 分开，不受
visual=no 影响）：
- console_baseline_required 固定 yes（除非有证据说明升级前 app 在任何 lane 都无法
  启动，此时按「无基线」记 residual 并在本波显式批准）；
- 采集范围为 Wave 5 功能冒烟将覆盖的路由集合，采集口径与 Wave 4/5 一致
  （每路由独立 fresh page），采集条件复用同一份 capture_conditions；
- 采集内容为控制台**全量输出**（error 与 warning 全量、按消息类去重计数），不得只
  采 error 或只采某份白名单 warning：基线里没采到的类别，Wave 5 就无法判定它是
  regression 还是本来就有，只能当噪声滑过；
- 存在 dev 运行面时基线必须**两条运行面各采一次**，Wave 5 按同一运行面逐条对比。
基线在升级前 revision 采集，窗口与视觉基线同时关闭；事后无法在同一 revision 补采。

分析包含 ui_behavior_contract 时（UI 库整体替换/跨大版本），
required_behavior_assertions 逐条进入已批准 spec 的验收场景，与视觉 required 状态
分开列。这些是行为契约（懒挂载与 $refs 时机、prop / 枚举改名、事件契约），
G9 pass 不构成它们的证据，也不得被 visual=no 顺带豁免。

required 状态若属数据驱动（loading、pagination populated、tree-expanded 等），
允许以「component-shell parity + 绑定后续真实后端验证任务」记 accepted-residual，
但该分层必须在本波声明并写入已批准 spec，且以基线在同条件下同样只能取到
component-shell 为前提。Wave 5 不得临时发明分层来兜底。

通过规格闸门：只问一次范围批准。然后停止。下一步 Wave 3。
```

## 4. Wave 3：Delivery Plan go

新会话粘贴「每波必贴」和「Wave 2–5 追加」，再粘贴：

```text
本波：显式使用 delivery-plan-tasks。不要实施、不要改应用代码。

应已存在：已批准 Frame 规格、分析 path+digest、Frame handoff。缺失或批准失效则回 Wave 2。
先读 CONFIG；target_vue_version 或派生路径与通用头不一致时停止，回 Wave 2。
只读 ANALYSIS_ROOT/upgrade-summary.json（named_recipes / named_validations /
runtime_lanes / recipe_constraints / ui_behavior_contract）与
ANALYSIS_ROOT/inventory.json 的
source_impact_signals.interaction_assertion_candidates。
summary 有 ui_behavior_contract 时，另读报告「5.」的 ui_behavior_contract 块取详情。
需要某条决策时再打开 ANALYSIS_ROOT/decision-records 下对应文件。
同时只读已批准 spec。

把分析里的命名配方写成纵向任务（精确文件/符号或 glob、实施期命令、失败时证明什么、回滚要点）。
任务顺序按 summary.recipe_constraints 的 after 拓扑排列，不自行改序；atomic=yes 的配方
不得拆成多个可分别落地的任务，atomic=no 才允许按目录/模块分批并逐批 review diff。
pages 有值时，任务不得把未点名且未进入闭包的页面扩进范围。
本波不跑配方（gogocode / vue-upgrade-tool / webpack-to-vite / npm install）。
依赖任务必须使用 TARGET_VUE_VERSION，校验适用包 resolved version 相等，拒绝 lock 漂移。

Node 任务须纵向且排在首次 install 之前：保存当前 Node 绿色基线；在改 Vue 依赖
前验证旧项目能否运行于目标 Node；按已批准策略更新 .nvmrc/.node-version/Volta/
engines、CI、Docker/devcontainer、部署 builder 与 Corepack/packageManager；再用
目标 Node frozen install + build/test。temporary-dual-node 要有两 lane、切换条件、
删除条件与缓存隔离。不得只改开发者本机 Node。

visual=required 时：基线捕获发生在升级之前；每个 required sample/state 映射到任务；G9 路径为 G9_ROOT。
基线任务须把已批准 spec 的 capture_conditions 固定成可复现的命令与参数（运行面、
端口策略、后端可用性、locale/timezone/theme）并记入证据，Wave 4/5 的 current 采集
复用同一条件。条件无法复现时按「无基线」处置，回 Wave 2 重议视觉契约，不得改条件后
硬比。

控制台基线任务（独立于 visual，按已批准的控制台基线契约生成）：在首次依赖/代码
mutation 之前，对升级前 revision 按批准的路由集合与运行面逐条采集，落盘
EVIDENCE_ROOT/console-baseline.json，字段与 console-evidence.json 同构并多一列
runtime_lane。该任务必须排在所有 install 与配方任务之前——窗口与视觉基线同时关闭。

控制台采集器全仓唯一：本波生成的任何控制台相关任务，都必须复用同一个采集器与同一
口径（每路由独立 fresh page，逐路由 runtime_lane 标注），不得另写第二套采集脚本或
另一种口径（例如单页面连续跳转累积监听）。口径分叉会让基线、Wave 4 与 Wave 5 三份
计数互不可比，还要额外解释差异。

运行面覆盖：存在 dev 运行面时，任务必须同时覆盖 dev 与 build 两条运行面，
逐条写明该任务在哪条运行面上验证；不得用一条运行面的绿代替另一条。
分析报告「10.」运行面差异行点名的证据（源码内 CJS、require.context、多入口 URL
形态、base/publicPath、env 分支）逐项生成验证任务。
基线可行性前置：必须先有任务证明旧 app 能在某个可用 lane 启动（老 Node 仓即
temporary-dual-node 的旧 lane）；若证明不可启动，须显式二选一并写入任务——
用预生产/生产环境捕获替代基线，或把「无基线」记为 blocking residual 并回
Wave 2 重议 visual 契约。不允许 baseline_status 悬空滑过。

交互断言清单：以 inventory 的
source_impact_signals.interaction_assertion_candidates.rows 为准，逐行生成交互
验证任务（每行一条「输入→状态回写」断言，最小组件测试或脚本化浏览器检查），
写入 tasks 与验证命令，不留给执行期自拟冒烟范围。model_option 行须按报告
「10. 未决问题与证据缺口」人工补搜检查里的 live/dead 结论区分：live（父级用
v-model 消费）为必做断言，dead 可降级。
sync_modifier 行须区分绑在自有组件上还是绑在本次同批替换的 UI 库组件上：后者的
断言必须验证改写后的 prop 名是**目标库实际声明的 prop**（旧库的 `visible` 在新库
可能已改名为 `modelValue`），且断言点落在「弹层/抽屉真正打开并挂载出子组件」，
而不只是变量被置为 true——这类错配 build 与 lint 全绿，症状出现在远处的 $refs。
options_filters_access 行逐点断言运行期调用不抛错（与模板管道是两处独立改写面）。
router_error_suppression 与 router_named_target 行是**静默被移除**而非引入：前者的
任务必须包含「删掉旧 `push`/`replace` 的吞错覆写与 `.catch` 吞错」，并断言它原先
掩盖的导航失败已逐条暴露且处置；后者对每个按 name 的跳转断言参数齐备（新版路由对
缺必填参数由静默改为抛错，且此类跳转常在启动路径上，首现症状是白屏而不是坏链接）。
ui_trigger_slot_target 行断言触发型插槽（popover / tooltip / dropdown 的 reference
面）的唯一子节点是元素型根：目标库对该子节点挂指令，放组件型根时构建、渲染与截图
全部一致，只在运行期告警且转发 ref 失效、弹层定位错乱——断言点是「触发交互后弹层
出现且位置正确」，不是「页面渲染出来了」。
summary.recipe_constraints 里有 overlaps_with 的配方对，必须额外生成一条**交集**
验证任务，不能用任一配方自身的任务顶替。
ui_behavior_contract.required_assertions 逐条生成行为验证任务（弹层打开后子组件确实
挂载、`$refs` 可用、prop 回写生效、枚举生效、事件不双触发），与视觉任务分开列；
这些断言不得由 G9 顶替。
candidates.truncated=true、source_impact_signals.truncated=true 或页面闭包超出
扫描面时，先补一次全量检索再生成清单，不得把截断结果当完备清单。

回滚演练任务：计划中必须有一条命名验证——在临时 worktree checkout 升级前
revision，用旧 lane frozen install + build 证明回滚路径可用，产出机器证据。
worktree 能力不可用时任务须写明降级方案（临时目录 clone / detached checkout）；
两者都不可行则记 non-blocking residual（写明 owner 与补救计划）。

人工前置核对：Wave 5 功能冒烟所需的后端/Mock、测试账号与权限、验证码或
二次验证的处理方式、稳定测试数据——本波逐项确认可用，或写成计划前置任务；
缺口不得拖到 Wave 5 才暴露。

实现闸门只问一次（High 附代价/风险/回滚摘要，并把回滚演练所需的临时
worktree/git 操作授权一并在此询问）。go 必须绑定当前 artifact_revision 与仓库 revision。然后停止。下一步 Wave 4。
```

## 5. Wave 4：Delivery Execute

新会话粘贴「每波必贴」和「Wave 2–5 追加」，再粘贴：

```text
本波：显式使用 delivery-execute-verify。它是唯一应用代码 mutation owner。
无绑定当前 revision 的实现 go：停止，不要编辑。

应已存在：design/tasks、Plan handoff、绑定当前 revision 的实现 go。缺失则回 Wave 3。
先读 CONFIG；target_vue_version 或派生路径与通用头不一致时停止，回 Wave 2。
visual=required 时，计划中必须有基线任务；基线须在本波首次依赖/代码 mutation 前捕获
并绑定当时 revision，而不是要求 Wave 3 已执行基线。

首次 mutation 前检查 git status：工作区不干净时停止，让用户显式处置
（commit/stash/纳入范围），否则基线与 handoff 的 revision 绑定不可复现。
首次 install 前打印实际 node -v、package manager 版本、NODE_ENV 与
npm config get production；node 不满足已批准 target range 时停止，production
环境噪声按固定边界处置后再装。
优先 frozen install；禁止用仓库拒绝的包管理器。现在可以安装依赖并运行已命名配方。
按 tasks.md 纵向实施。实施后、Fresh Verification 前重新 index_repository，刷新 Codebase Memory 索引。
lock digest 未变化不重复安装。

依赖变更使用 TARGET_VUE_VERSION。安装后查询 resolved versions：vue 必须等于
TARGET_VUE_VERSION；适用的 @vue/compat、@vue/compiler-sfc、@vue/server-renderer 必须与之完全一致。
不一致则停止并按 alignment_backflow 回 Wave 3。

visual=required：升级后写 delivery-visual-evidence/v1 到 G9_ROOT 并校验。
外部分析只作 external_artifacts path/digest，不能代替 G9 final_visual_result=pass。
assessment_mode、diff_policy、structural_parity_metrics 与 capture_conditions
一律取已批准 spec 的值填写，本波不得新定或改写——改写等同单方降级 required 状态，
须按 alignment_backflow 回 Wave 2。current 采集必须复用基线的 capture_conditions。

控制台基线：若计划中的 console-baseline 任务尚未执行，必须在本波首次依赖/代码
mutation 之前执行并落盘 EVIDENCE_ROOT/console-baseline.json；首次 mutation 之后
才发现基线缺失的，按 alignment_backflow 回 Wave 2 重议控制台基线契约，不得在升级
后的 revision 上补采充数。
本波若采集 Vue runtime 控制台证据，采集口径必须与基线和 Wave 5 完全一致（每路由
独立 fresh page，逐行标注 runtime_lane），否则三份计数不可比，还要额外解释差异。

存在 dev 运行面时，本波结束前必须证明应用在 **dev 与 build 两条运行面上都能启动
并进入主路径**，两条各留证据。只跑通一条即宣布实施完成属未完成：两条运行面的模块
解析、入口/URL 形态与 env 处理都不同，一条绿不构成另一条的证据。

不要 archive OpenSpec，不要 commit/push/PR，除非用户在本波之后另授权。

结束时输出 verification、G9、独立审查、rollback 与 handoff path/revision。
Node 证据须含：当前基线、目标 Node 下升级前兼容性（或为何不适用）、目标 Node frozen
install/build/test、声明面一致性；临时双 Node 未满足删除条件时记 residual。
回滚演练：执行计划中的回滚演练任务（临时 worktree + 升级前 revision +
旧 lane frozen install/build），证据写入 verification。worktree 授权应已随
实现 go 一并取得，缺失则先补授权再执行；worktree 能力不可用时按计划降级
（临时目录 clone / detached checkout），仍不可行则记 non-blocking residual
（写明 owner 与补救计划），不得越权执行未授权 git 操作。
写 verification.md 与 verified handoff（overall_status=verified，
archive.status=deferred_to_openspec）。Delivery verified ≠ 仓内 verified。
不要声称仓内 verified。G9 未过则留在本波；连续 2 次 G9 fail 且无新修复方向时，
不要原地重试，按 alignment_backflow 回 Wave 2 重议 required_states 或 non-goals。
visual/G9 的 required 状态不得在本波降级；降级只能走 Wave 2 重新批准并记 DR。
说明下一步 Wave 5，然后停止。
```

## 6. Wave 5：独立功能验证

新会话粘贴「每波必贴」和「Wave 2–5 追加」，再粘贴：

```text
本波：显式使用 delivery-execute-verify，仅做独立新鲜验证与升级后功能验收。
不得修改应用代码，不得改 tasks 勾选，不得跑新的实施配方，不得 archive/commit/push/PR。
发现缺陷不要在本波修复。

应已存在：绑定当前 revision 的 Delivery verification.md 与 verified handoff、
Plan/Execute 工件、CONFIG；visual=required 时含 G9_ROOT 且 final_visual_result=pass。
缺失、Delivery 未 verified、或 revision 与当前仓库不一致：停止，回 Wave 4。
先读 CONFIG；target_vue_version 或派生路径与通用头不一致时停止，回 Wave 2。

不要采信 Wave 4 会话结论或旧 pass 日志。以当前磁盘工件 + 本会话新跑命令为准。
图谱 revision 与当前仓库不一致时先 index_repository，再取证。

按当前 revision 启动干净服务（不要复用 Wave 4 残留进程）。运行面是**两条**，不是
二选一：workspace 存在 dev 运行面时，dev server 与 build 产物静态 serve 各跑一遍，
每条独立启动、独立采证。只跑其中一条不构成本波通过，也不得在结论里把一条运行面的
结果表述为整体 verified。
lock digest 未变化不重复安装；Node/包管理器或 lock 变化时 frozen install。
首次启动前打印实际 node -v、包管理器版本、NODE_ENV 与 npm config get production；
node 不满足已批准 target range 时停止，production 环境噪声按固定边界处置后再装。

必须在本会话重跑并阅读完整输出：
- ANALYSIS_ROOT/upgrade-summary.json 的 named_validations
- 已批准 spec 的 Requirement/Scenario
- 任务列出的验证命令
vue resolved version 必须仍等于 TARGET_VUE_VERSION；适用的
@vue/compat / @vue/compiler-sfc / @vue/server-renderer 必须与之完全一致。

功能冒烟（pages 空=全仓代表入口/路由；pages 有值=这些页面+闭包）：
已批准验收场景、登录后主路径、路由切换、列表/表单/弹层等规格点名交互。
每条运行面各跑一遍同一份冒烟清单——dev 与 build 的模块解析、入口/URL 形态、
env 分支都不同，一条运行面的通过不构成另一条的证据。
同时记录控制台全量输出：error 与升级相关 warning 不得无处置。**「升级相关」按
发出方判定，不按记得住的消息清单判定**——四类发出方全部在内：Vue 框架自身
（compat、filters、已移除实例 API、指令用在非元素根组件上等）、目标 UI 库自身的
弃用告警（迁移后落在目标大版本已弃用的 API 上，按 mount 刷量）、构建/样式工具链
自身的弃用告警（样式编译器 `@import` 等，按编译刷量）、以及**基线里没有的任何
消息**（不论发出方，先按 regression 处置）。按消息类去重计数，不抽样：一条按 mount
刷屏的弃用告警是一个类，量大不等于严重，也不得让它把一条 error 埋掉。
控制台结论必须落盘为
EVIDENCE_ROOT/console-evidence.json（每个冒烟路由 × 每条运行面一行：route、
runtime_lane、error 数、升级相关 warning 数、warning 发出方分类计数、处置状态
resolved / config-silenced / accepted-residual），
不接受只在会话文字里"声称无异常"。采集口径固定为每路由独立 fresh page：每条路由
新开页面再挂监听，用完关闭。不得用单页面连续跳转累积监听——那会把同一条错误重复
计入多条路由，计数虚高且与基线、Wave 4 的证据不可比。
控制台结果必须与 EVIDENCE_ROOT/console-baseline.json **按同 route + 同 runtime_lane
逐条对比**，每条 error 归入 regression（基线无、升级后有）或 pre-existing（基线同
条件下已有）。没有基线对照就把某条 error 判为「环境问题/非回归」是主张而非证据，
不予接受。regression 一律须处置；pre-existing 记 non-blocking residual 并写明 owner。
warning 的合法处置只有三种：改写到未弃用的 API（resolved）；`config-silenced`——在
构建配置里**按具名弃用 id** 定点静默（样式编译器的弃用静默选项是典型），必须同时
记下该 id、理由与解除条件；`accepted-residual` 并写明 owner。禁止全局过滤控制台、
包裹 `console.*`，也禁止对 error 做任何静默。
error 记 accepted-residual 必须经用户显式批准并记录批准语句；
不得自行接受运行时 error。交互断言（Wave 3 从 inventory 生成的
v-model 回写、`.sync` 目标 prop 身份、`$options.filters` 调用点、router 导航
（吞错覆写移除后按 name 跳转不得抛 Missing required param）、触发型插槽内容形状、
配方交集等逐点检查）必须逐条执行并记录结果。不得用测试已绿代替未执行的场景。

visual=required：按当前 revision 重新校验 G9_ROOT 的 delivery-visual-evidence/v1。
基线仍是升级前捕获；必要时刷新 current/diff，不得改应用代码。刷新时必须复用已批准
spec 的 capture_conditions；assessment_mode、diff_policy 与 structural_parity_metrics
取已批准值，本波不得放宽。数据依赖态按 Wave 2 已声明的分层判定；spec 未声明分层、
本波才发现某 required 状态在当前条件下只能取到 component-shell 的，按 fail 回流
Wave 2，不得当场记 accepted-residual。
validator 未过或 revision 不匹配：停止，回 Wave 4。

写本波 handoff 前，先把 Wave 4 的 verified handoff 复制留存为
EVIDENCE_ROOT/handoff-wave4.json（只读归档），本波 handoff 的
previous_handoff_id 指向它——handoff.json 是覆盖写，不归档就无法区分前置证据。

无论 pass 还是 fail，本波都要写一份回灌工件
EVIDENCE_ROOT/upgrade-retrospective.md，记录本次实测到的四类事实，每条附证据指针
（文件/路由/命令）与观察日期：
- codemod 实际产出特征（哪种改写是错的、错在哪、build/lint 为何没拦住）；
- UI 库行为差异（懒挂载、prop / 枚举 / 事件 / 插槽契约、插槽内容形状与预期不符之处）；
- 运行面分叉（只在 dev 或只在 build 出现的问题）；
- 控制台弃用面（目标 UI 库与构建/样式工具链自身的告警：哪些改写消除、哪些按具名
  弃用 id 定点静默、哪些留 residual）。
它不改任何 Skill，也不是本波通过条件；它是把一次实战沉淀回配方库的**唯一**合法
来源——没有它，下一个仓会把同样的坑重踩一遍。附录性质，写明"依赖前须按当时选定
的工具版本复核"。
它是 **append-only** 工件：仓内 verified 之后仍可继续追加（见「9. verified 之后」），
追加不改变本 change 的状态，也不需要重开任何波次。

pass：对照通用头仓内 verified 条件逐条核对，并把结论落盘
EVIDENCE_ROOT/inrepo-verification.md（逐条核对结果、console-evidence 与交互
断言指针、G9 与 named_validations 结果、绑定当前 revision）后，才能声称仓内
verified。仓内 verified ≠ 生产完成。
仍不 archive/commit/push/PR/部署。然后停止。
fail：按 alignment_backflow 输出，不要改代码，返回：
规格/验收→Wave 2；任务/验证命令/回滚→Wave 3；实现、测试、G9 或功能回归→Wave 4。
然后停止。
```

## 7. 失败回流

始终使用原 `CHANGE_ID`，不创建第二个 OpenSpec change。


| 发现                                       | 返回                             |
| ---------------------------------------- | ------------------------------ |
| workspace / 拓扑选错，或应走 host-port           | Wave 1；必要时改 A→B 剧本             |
| 分析报告目标 Vue 版本错误、不可用或证据不足             | Wave 1                           |
| 分析包 repo_revision 与当前仓库漂移（分析 stale）      | Wave 1                           |
| workspace 实为已（部分）升级完成的 Vue3 仓            | 停止主线；residual-audit 或结束     |
| 目标、验收、行为 parity、视觉是否 required、pages 范围错误 | Wave 2 规格批准                    |
| 视觉契约缺项或需放宽（assessment_mode、diff_policy、结构 parity 白名单、capture_conditions、数据依赖态分层） | Wave 2 规格批准 |
| 分析缺 `ui_behavior_contract` / `ui_cutover_staging` / `default_path_deviation` | Wave 1 |
| 行为断言未进已批准 spec，或被当作 G9 的一部分顺带豁免 | Wave 2 规格批准 |
| 控制台基线缺失、条件不可复现，或首次 mutation 后才发现未采 | Wave 2 规格批准（重议控制台基线契约，不得在升级后 revision 补采） |
| 任务另起第二套控制台采集器或另一种口径 | Wave 3 Plan |
| 运行面覆盖不全（只验证了 dev 或只验证了 build 产物） | Wave 3 Plan 补任务；已实施则 Wave 4 补跑另一条运行面 |
| Wave 3 人工前置未兑现，导致已批准交互无法执行 | Wave 3 Plan；确实不可得时回 Wave 2 重议验收范围 |
| CONFIG / 已批准规格中的 target_vue_version 不一致      | Wave 2                           |
| 配方拆分、回滚、基线时机、任务范围错误                      | Wave 3 Plan                    |
| 已批准范围内的实现、测试、G9 或功能回归                   | Wave 4 Execute                 |
| 连续 2 次 G9 fail 且无新修复方向（重议 required_states / non-goals） | Wave 2 规格批准          |
| Wave 5 发现 Delivery 未 verified 或证据 stale | Wave 4 Execute                 |
| OpenSpec / Memory 硬前提失败                  | 停在当前 Delivery Wave，按三行报告恢复后再继续 |
| 分析 gate 仍 frozen 却进入 Wave 2              | 回 Wave 1                       |


回流携带：

```text
alignment_backflow:
  discovery / evidence / affected_scope / invalidated_artifacts /
  decision_needed / recommended_resolution / resume_point
```

规格或计划变更后，必须重跑受影响闸门。Wave 4 修复后必须重跑受影响任务的 Fresh
Verification，并重新执行完整 Wave 5；不得用 Wave 4 旧 pass 声称仓内 verified。

## 8. 完成判定

权威清单是「Wave 2–5 追加」粘贴块里的仓内 verified 条件（Wave 5 对照的就是
那份）；本章是同一清单的展开版，供通读本文的人核对，两处不一致时以通用头
为准并修复本章。
只有以下全部满足，才能声称本 change 仓内 `verified`：

- 分析包 `analysis_status=complete`，且交接时 `batch_implementation_gate=ready`；
- 路径仍是原地升（`compat-big-bang` 或已记录的 `direct-vue3`），不是 host-port；
- `vue` resolved version 等于 TARGET_VUE_VERSION（CONFIG 记录的精确版本），且适用的
  `@vue/compat` / `@vue/compiler-sfc` / `@vue/server-renderer` 与其完全一致；
- OpenSpec 规格批准与实现 go 绑定当前 artifact_revision 与仓库 revision；
- 权威任务全部完成；Wave 4 Fresh Verification 与（High）独立审查通过；
- Wave 5 在全新会话对当前 revision 重跑 named_validations、规格场景与升级后
  功能冒烟，且不混用 Wave 4 旧 pass；
- `visual=required` 时 Delivery G9 `final_visual_result=pass`；required 状态
  从 Wave 2 批准起未被任何后续 Wave 单方降级（降级须回 Wave 2 重批 + DR）；
  `assessment_mode` / `diff_policy` / `structural_parity_metrics` 仍是 Wave 2
  已批准的值，基线与 current 使用同一 `capture_conditions`；数据依赖态的
  accepted-residual 只在 Wave 2 已声明该分层时成立；
- 分析报告「1. 基线与假设」`repo_revision` 与升级前基线 revision 链条一致
  （Wave 2 时效检查通过）；
- 回滚演练证据存在（升级前 revision 在旧 lane frozen install/build 通过），
  或按已批准降级记为 non-blocking residual；
- 存在 dev 运行面时，dev 与 build 两条运行面各自独立启动、各跑过完整功能冒烟
  并各留证据；不得以其一代替另一条，也不得把一条运行面的结果表述为整体结论；
- `console-baseline.json` 存在（升级前 revision、同 capture_conditions、同口径
  采集），或「无基线」已在 Wave 2 显式批准为 residual；
- `console-evidence.json` 存在、按每路由 × 每运行面独立 fresh page 口径采集，
  已与基线同 route 同 runtime_lane 逐条对比，每条 error 归入 regression 或
  pre-existing，且无未处置的 error / 升级相关 warning——「升级相关」按发出方判定
  （框架 / 目标 UI 库 / 构建与样式工具链 / 基线里没有的任何消息），不按记得住的
  消息清单判定；warning 处置只认 resolved、`config-silenced`（具名弃用 id + 理由 +
  解除条件）、accepted-residual（有 owner），error 记 accepted-residual
  须有用户显式批准记录；交互断言清单逐条有结果；
- Wave 3 记录的人工前置（后端/Mock、测试账号与权限、验证码处理、稳定数据）
  全部兑现；未兑现项不得静默滑过，须逐条进入覆盖声明并由用户显式接受；
- 分析包含 `ui_behavior_contract` 时，`required_behavior_assertions` 逐条有执行
  结果；G9 pass 不构成这些行为断言的证据；
- `EVIDENCE_ROOT/inrepo-verification.md` 存在、逐条核对通用头条件、含覆盖声明
  （运行面、路由集合、未实际执行的已批准交互及原因）并绑定当前 revision；
  Wave 4 verified handoff 已归档为 `handoff-wave4.json`；
  `EVIDENCE_ROOT/upgrade-retrospective.md` 已写出（回灌工件，非通过条件，但缺失
  意味着本次实战经验不会沉淀）；
- Composition 全仓重写仍在 non-goals；
- 目标 Node 范围与工具链精确版本有证据；Fresh Verification 使用受支持 Node；
  local/CI/container/deploy/package-manager 声明一致，或已批准的临时双 Node residual
  有明确 owner、删除条件且不 blocking；
- 无 blocking residual；
- `pages` 空：本 workspace 原地升完成；
- `pages` 有值：仅这些页面+闭包+本 change 批准的共享 runtime/build 完成，
未点名页面仍 Vue2/compat 不阻塞本 change 的 verified。

此时不自动 archive、commit、push、PR、部署或生产切流。

## 9. verified 之后

仓内 verified 是本剧本的完成水位，**不新增运维波次**：一个开放式的"清退波次"没有
终止条件，实际效果是让 change 永远开着。但 verified 之后用户真实使用中冒出来的问题
需要一条合法通道，否则它们既回不到配方库、也没人认领。按性质二分，只有两条出口：

| verified 之后的发现 | 出口 |
|---|---|
| 阻断、回归、或需要改应用代码 | 新开一个 change 走 Wave 2–5（新 `CHANGE_ID`；不得回改已 verified 的 change，也不得在无规格批准的情况下直接改代码） |
| 非阻断的控制台噪声、弃用告警、已记 residual 的项 | 追加到 `EVIDENCE_ROOT/upgrade-retrospective.md`（append-only，带观察日期与证据指针），并作为下一个仓 Wave 1 的输入 |

追加时按上面的四类事实归类，`config-silenced` 的具名弃用 id 与解除条件一并记下。
这类发现**不表示 Wave 1–5 跑得不严**，而是分析期的建模面没覆盖到该破坏面；因此
追加的价值在于让下一个仓的 Wave 1 把它当成已知面来扫，而不是在这个仓重开波次。
若同一类发现在两个仓复现，那是分析 Skill 的信号或控制台分类该扩的证据，不是剧本
该加波次的证据。

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
- target_vue_version = Wave 1 从 registry 解析出的 3.5.x 线最新稳定补丁号
  （必须精确到补丁；禁止 latest / next / rc / beta；解析结果写入 CONFIG 后全程不变）

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
  会指向非预期版本：vue 的 rc 现指向 3.6.0-rc.4（Vapor 预发布），vue-router 的
  next 反而指向五年前的 4.0.13，而其 latest 已是 v5 主版本——裸装 vue-router 会
  解析到 5.x 而不是 4.x。安装目标 major 必须显式钉死，并在报告或任务里留下依据。
- 单仓原地升。pages 只收窄本 change，不是 A→B host-port，也不是页面闭包迁入。
- 默认行为 parity；保留 Options API。Composition API 全仓重写另立项。
- Vue 3.6 / Vapor mode 不在本轮范围。3.6 线目前只有预发布，任何 rc/beta 都不得
  进入本次升级；本轮目标固定在 3.5.x 的精确补丁号。
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
单方降级；回滚演练证据存在（升级前 revision 在旧 lane frozen install/build 通过）；
console-evidence.json 无未处置 error（error 记 accepted-residual 须用户显式批准）；
交互断言清单逐条有结果；结论落盘 EVIDENCE_ROOT/inrepo-verification.md；
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

目标 Vue = TARGET_VUE_VERSION。用户未覆盖时，本波向 npm registry 解析 3.5.x 线的
最新稳定补丁号，钉成精确版本写入 CONFIG 与报告；不得写 latest、不得写「当前最新
3.x」、不得凭记忆填版本号、不得落到 3.6 线的任何预发布（alpha/beta/rc）。
解析失败或该线不可用时停下询问用户，不得自行改钉其他版本。
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
要求时才产出 residual-audit 残留审计包，不得按 Vue2 基线写升级决策包。
报告「1. 基线与假设」必须记录 repo_revision（分析绑定的 git HEAD）与
browser_support_floor；下游各 Wave 以此判定分析是否 stale。

报告「3. 推荐迁移路径」必须出现字面：
Composition API 全仓重写：另立项，本次不评估工作量

summary 必须给出 recipe_constraints：每个命名配方一行 after（保留锚点或另一配方 id）
与 atomic；inventory 必须含 source_impact_signals.interaction_assertion_candidates
（逐点定位 model_option / native_modifier / keycode_modifier / transition_component）。
candidates.truncated=true 说明清单不完备，须在本波补一次全量检索或写入证据缺口。

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

通过规格闸门：只问一次范围批准。然后停止。下一步 Wave 3。
```

## 4. Wave 3：Delivery Plan go

新会话粘贴「每波必贴」和「Wave 2–5 追加」，再粘贴：

```text
本波：显式使用 delivery-plan-tasks。不要实施、不要改应用代码。

应已存在：已批准 Frame 规格、分析 path+digest、Frame handoff。缺失或批准失效则回 Wave 2。
先读 CONFIG；target_vue_version 或派生路径与通用头不一致时停止，回 Wave 2。
只读 ANALYSIS_ROOT/upgrade-summary.json（named_recipes / named_validations /
recipe_constraints）与 ANALYSIS_ROOT/inventory.json 的
source_impact_signals.interaction_assertion_candidates。
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
首次 install 前打印实际 node -v 与 package manager 版本；不满足已批准 target range 时停止。
优先 frozen install；禁止用仓库拒绝的包管理器。现在可以安装依赖并运行已命名配方。
按 tasks.md 纵向实施。实施后、Fresh Verification 前重新 index_repository，刷新 Codebase Memory 索引。
lock digest 未变化不重复安装。

依赖变更使用 TARGET_VUE_VERSION。安装后查询 resolved versions：vue 必须等于
TARGET_VUE_VERSION；适用的 @vue/compat、@vue/compiler-sfc、@vue/server-renderer 必须与之完全一致。
不一致则停止并按 alignment_backflow 回 Wave 3。

visual=required：升级后写 delivery-visual-evidence/v1 到 G9_ROOT 并校验。
外部分析只作 external_artifacts path/digest，不能代替 G9 final_visual_result=pass。

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

按当前 revision 启动干净 dev/preview（不要复用 Wave 4 残留进程）。
lock digest 未变化不重复安装；Node/包管理器或 lock 变化时 frozen install。
首次启动前打印实际 node -v 与包管理器版本；不满足已批准 target range 时停止。

必须在本会话重跑并阅读完整输出：
- ANALYSIS_ROOT/upgrade-summary.json 的 named_validations
- 已批准 spec 的 Requirement/Scenario
- 任务列出的验证命令
vue resolved version 必须仍等于 TARGET_VUE_VERSION；适用的
@vue/compat / @vue/compiler-sfc / @vue/server-renderer 必须与之完全一致。

功能冒烟（pages 空=全仓代表入口/路由；pages 有值=这些页面+闭包）：
已批准验收场景、登录后主路径、路由切换、列表/表单/弹层等规格点名交互。
同时记录 Vue runtime 控制台：error 与升级相关 warning（compat / filters /
已移除实例 API 等）不得无处置。控制台结论必须落盘为
EVIDENCE_ROOT/console-evidence.json（每个冒烟路由一行：route、error 数、
升级相关 warning 数、处置状态 resolved/accepted-residual），不接受只在会话
文字里"声称无异常"。error 记 accepted-residual 必须经用户显式批准并记录
批准语句；不得自行接受运行时 error。交互断言（Wave 3 从 inventory 生成的
v-model 回写等逐点检查）必须逐条执行并记录结果。不得用测试已绿代替未执行的场景。

visual=required：按当前 revision 重新校验 G9_ROOT 的 delivery-visual-evidence/v1。
基线仍是升级前捕获；必要时刷新 current/diff，不得改应用代码。
validator 未过或 revision 不匹配：停止，回 Wave 4。

写本波 handoff 前，先把 Wave 4 的 verified handoff 复制留存为
EVIDENCE_ROOT/handoff-wave4.json（只读归档），本波 handoff 的
previous_handoff_id 指向它——handoff.json 是覆盖写，不归档就无法区分前置证据。

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
- 分析报告「1. 基线与假设」`repo_revision` 与升级前基线 revision 链条一致
  （Wave 2 时效检查通过）；
- 回滚演练证据存在（升级前 revision 在旧 lane frozen install/build 通过），
  或按已批准降级记为 non-blocking residual；
- `console-evidence.json` 存在且无未处置的 error / 升级相关 warning
  （error 记 accepted-residual 须有用户显式批准记录）；交互断言清单逐条有结果；
- `EVIDENCE_ROOT/inrepo-verification.md` 存在、逐条核对通用头条件并绑定当前
  revision；Wave 4 verified handoff 已归档为 `handoff-wave4.json`；
- Composition 全仓重写仍在 non-goals；
- 目标 Node 范围与工具链精确版本有证据；Fresh Verification 使用受支持 Node；
  local/CI/container/deploy/package-manager 声明一致，或已批准的临时双 Node residual
  有明确 owner、删除条件且不 blocking；
- 无 blocking residual；
- `pages` 空：本 workspace 原地升完成；
- `pages` 有值：仅这些页面+闭包+本 change 批准的共享 runtime/build 完成，
未点名页面仍 Vue2/compat 不阻塞本 change 的 verified。

此时不自动 archive、commit、push、PR、部署或生产切流。

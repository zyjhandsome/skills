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
```

全程 GLM 5.2。不按波换模型，不插入 Kimi。视觉结论来自 Delivery G9 的确定性
工具证据，不以模型看图代替。模型选择不写入任何 Skill schema。

完成水位是仓内 `verified`（测试 + 需要时的 Delivery G9），不含生产发布、切流、
监控。归档、commit、push、PR 仍须另授权。

### 0.1 Skill 职责边界

- `vue2-to-vue3-upgrade-impact-analysis` 只负责路径三维、子系统风险、确认队列
和决策包。Name, never run。不改应用代码，不写 OpenSpec 状态，报告里不得填写
其他 Skill 名称。
- Delivery Family 负责 OpenSpec、规格与实施批准、技术计划、应用代码修改、
Delivery G9、独立审查和交付状态。`delivery-execute-verify` 是唯一应用代码
mutation owner。
- `delivery-explore` 不适用。主路径不插入
`frontend-dependency-upgrade-impact-analysis`，也不调用
`migrate-vue2-pages-to-vue3-host`。
- 视觉验收只走 Delivery G9。G9 未过则留在 Wave 4。

### 0.2 拓扑消歧（开写前）


| 实际形态                              | 走哪份剧本                       |
| --------------------------------- | --------------------------- |
| 一个 Vue2 SPA，全 workspace 原地升到 Vue3 | **本文**（`pages` 空）           |
| 同一 Vue2 SPA，只升某几个页面（含闭包）          | **本文**（填写 `pages`）          |
| 同一仓库里已有 Vue3 宿主，要把 Vue2 页面/包装进去   | A→B 剧本（两个 root；`host-port`） |
| 两个独立仓库，iframe / 微前端收编             | A→B 剧本                      |
| 只要决策包、不改代码                        | 分析 usage；不要进入 Wave 2+       |


页面范围只收窄本 change 的闭包，**不是**把页面迁到另一个 Vue3 宿主。共享
runtime/build（`vue` / router / store / Vite）仍属分析范围，因为这些页面跑在
当前 app 里。

Wave 1 若把推荐路径定为 `host-port-direct`，或画像显示实施落点不是当前
workspace：停止原地升，改走 A→B 剧本。不要在本剧本里继续 Frame。

### 0.3 决策包通用动作 → 本剧本下一步

分析报告不得点名 Skill。调用方按本表翻译：


| 决策包字段                                                                           | 本剧本                            |
| ------------------------------------------------------------------------------- | ------------------------------ |
| `next_action: analysis_complete` 且 `batch_implementation_gate=ready`            | Wave 2 Frame                   |
| 同上但 gate=`frozen`                                                               | 停在分析；补 lock / 未决 High 后再交接     |
| `visual_acceptance_required=yes` 且 `recommended_next_action: run_visual_review` | Wave 3 把基线+G9 写入任务；Wave 4 做 G9 |
| `recommended_path: host-port-direct`                                            | 改走 A→B 剧本                      |
| `Composition API 全仓重写：另立项`                                                      | 本 change 的 non-goal            |


## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 在前端 workspace 打开会话。全仓升则不必填路径；只升某几个页面时在通用头写
  `pages`。
2. 启动全新会话，将「会话通用头 + 当前 Wave」连续粘贴为一条消息。
3. 当前 Wave 完成并停止后，打开新会话粘贴下一 Wave。
4. 用户只回答分析确认 token、规格批准和实施批准。不要手工搬运 JSON 或 digest。

### 1.2 会话通用头——每个新会话必贴；仅覆盖项可省略

```text
这是一个全新独立会话，不得使用其他会话的聊天记忆补结论。
当前模型：GLM 5.2。本波内不换模型。
本会话只执行随后指定的一个 Wave；写盘校验后立即停止，不要加载或执行下一个 Skill。
不要使用 delivery-explore，不要调用 migrate-vue2-pages-to-vue3-host，
不要让 vue2 分析 Skill 改代码或重开决策包。

默认（仅 CONFIG 不存在且用户未覆盖时使用）：
- workspace = 当前本地仓库 / workspace（含待升级的 package.json）
- pages = 空 → 全 workspace（batch_scope=full-stack）
- target_vue_version = 3.5.29（精确目标版本；不是 `latest`）

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
- OUTPUT_DIR = <workspace>/.vue2-to-vue3-upgrade-analysis
- CHANGE_ID = vue2-to-vue3-inplace-<SLUG>
- CHANGE_DIR = <workspace>/openspec/changes/<CHANGE_ID>
- EVIDENCE_ROOT = <CHANGE_DIR>/evidence
- ANALYSIS_ROOT = Wave 1 实际报告目录（默认 OUTPUT_DIR）
- G9_ROOT = <EVIDENCE_ROOT>/delivery-visual
- CONFIG = <EVIDENCE_ROOT>/inplace-run-config.json
CONFIG 存在后以其中记录为准；只有本次**显式填写**的值与配置不一致时停止。

固定边界：
- 单仓原地升。pages 只收窄本 change，不是 A→B host-port，也不是页面闭包迁入。
- 默认行为 parity；保留 Options API。Composition API 全仓重写另立项。
- Node 必须拆成两面：当前项目实际/声明的 Node 契约，以及所选目标工具链精确
  版本的 `engines.node` 交集。不得写死“Vue3 最低 Node X”，也不得只看本机
  `node -v`；同时覆盖本地 pin、`engines`、CI、Docker/devcontainer、部署构建环境。
- `vue` 的 resolved version 必须等于 TARGET_VUE_VERSION；路径涉及
  `@vue/compat` / `@vue/compiler-sfc` / `@vue/server-renderer` 时，这些包的
  resolved version 必须完全一致。manifest 是否保留范围符号遵循已批准规格，
  但 lock 不得漂到其他 Vue 版本。
- 仅 Wave 4（delivery-execute-verify）可修改应用代码并安装依赖、运行命名配方；
  Wave 1–3 只读。分析阶段 Name, never run。
- 保护 workspace 里已有的本地改动。
- 部署、生产切流、监控不属于本轮。禁止 Quick。本变更固定 High。

自动恢复以随后 Wave 块「应已存在」行为准。已完成 Wave 的工件缺失/损坏/stale
则停止并指出重跑 Wave，不要求用户手工提供内容。

失败回流最小字段（alignment_backflow）：
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point

仓内 verified（仅 Wave 4 在 Fresh Verification 通过后才能声称）须同时：
分析包 complete 且交接时 gate=ready；路径仍是原地升；规格批准与实现 go 绑定当前
revision；权威任务完成；Fresh Verification 与 High 独立审查通过；visual=required
时 G9 pass；Vue resolved version 与 TARGET_VUE_VERSION 一致；Composition 全仓
重写仍在 non-goals；无 blocking residual。
仍不 archive/commit/push/PR/部署。

代码检索（Wave 2 起）：默认 Codebase Memory MCP
（search_graph → trace_path → get_code_snippet；复杂闭包 query_graph；
结构 get_architecture；模板/导入/字符串 search_code）。
仅 package.json、锁文件、构建/样式配置，或 MCP 为空/明显不完整时，才降级到
文件读取或 rg，并记录 query、缺口和原因。不得因图谱没有 Route 节点断言路由不存在。
```

### 1.3 工件恢复矩阵


| 工件组                         | Agent 用途                                 | 用户操作     |
| --------------------------- | ---------------------------------------- | -------- |
| `ANALYSIS_ROOT`             | 分析决策包、summary、inventory、decision-records | 确认路径；看摘要 |
| `CONFIG`                    | 同一 change 的业务输入和派生路径                     | 不操作      |
| OpenSpec 工件与 `handoff.json` | 规格、批准、计划、任务和交付状态                         | 批准时看摘要   |
| `G9_ROOT`                   | Delivery G9 视觉验收                         | 最终看摘要    |


默认不得在 `CHANGE_DIR` 外另建第二套 delivery 状态。分析目录可以先于 change
存在；Wave 2 只把报告 path+digest 记为 `external_artifacts`，不把分析 schema
写进 Delivery 状态。新增分析报告不会使 Frame 批准失效；改 proposal/spec 仍会。


| Wave      | 应当存在的主要上游工件                                                   |
| --------- | ------------------------------------------------------------- |
| 1 分析      | 无；不要求 OpenSpec / Memory                                       |
| 2 规格批准    | 定稿决策包（`analysis_status=complete`）；OpenSpec + Memory 从此波开始是硬前提 |
| 3 Plan    | 已批准 Frame 规格、分析 path+digest、Frame handoff                     |
| 4 Execute | design/tasks、Plan handoff、实现闸门；`visual=required` 时含 G9        |


Wave 1 **不**要求 OpenSpec 或 Codebase Memory。Wave 2–4 硬前提失败时用
Delivery 固定三行报告停止，不降级。

## 2. Wave 1：vue2 分析（只出决策包）

新会话粘贴“会话通用头”，再粘贴：

```text
本波：显式使用 vue2-to-vue3-upgrade-impact-analysis。只出决策包。
不改代码、不跑 codemod、不写 OpenSpec。

应已存在：无。不要求 OpenSpec / Memory。
入口：单 workspace；project-root = workspace。--output-dir OUTPUT_DIR。
OUTPUT_DIR 已由通用头给出；禁止再问 confirm:output-dir，也不要向用户索要
口语「写到仓库」。
pages 空 → batch_scope=full-stack。
pages 有值 → batch_scope=page-closure：只评估这些页面及其闭包，外加它们依赖的
共享 runtime/build；未点名且未进入闭包的页面记为 non-goal，不要扩成全仓。

目标 Vue 精确版本为 TARGET_VUE_VERSION（默认 `3.5.29`），不得自动改成
`latest`。报告 §2/§3 必须写出该版本。compat 路径按相同版本评估 `vue`、
`@vue/compat`、`@vue/compiler-sfc`；direct 路径至少对齐 `vue` 与
`@vue/compiler-sfc`；SSR 再对齐 `@vue/server-renderer`。若 registry/官方证据
表明目标版本不可用或与路径冲突，gate=frozen，并把版本选择放入确认队列，
不得静默换版本。

跑 preflight 与 profile。推荐路径默认 compat-big-bang
（runtime_axis: compat，build_axis: vite，topology_axis: single-cutover），
除非证据支持 direct-vue3 或必须改拓扑。

在路径确认前完成 Node 双面矩阵：
- 当前面：host Node、.nvmrc/.node-version/Volta/engines、CI、容器和部署声明，
  区分“配置声明”与“已知能跑通当前 build/test 的基线”；
- 目标面：为本路径选定具体 Vue/@vue/compat、Vite+plugin 或 CLI5、测试/SSR、
  package manager 版本，读取各自 registry `engines.node` 并用官方文档交叉核对；
- 写完整 semver 交集、node_compatibility_status 与 node_transition_strategy。
  Vue 包无 `engines.node` 时明确写无，不得臆造 Vue3 自身最低值。
目标版本/engines 未定，或 current→target 冲突未解：gate=frozen。
需要升 Node 时，`build` 固定 High + required_for_path=yes，并确认
upgrade-before-vue 或 temporary-dual-node；后者必须写两条 lane、切换条件和删除条件。
若画像是另一 Vue3 宿主、iframe 收编、或推荐 host-port-direct：停止本剧本。
本波只覆盖单仓原地升；实施落点不是当前 workspace，或 topology_axis=host-port
时不得进入 Wave 2。说明应改走 A→B 剧本，然后停止。

报告「3. 推荐迁移路径」必须出现字面：
Composition API 全仓重写：另立项，本次不评估工作量

确认队列必须当场问：
- Wave 1 路径用 proceed:path:<id> / defer / other
- 之后 High/blocker 与 required_for_path=yes 用 proceed:subsystem:<id>
禁止把「继续 / 全部放行 / 别再问了 / 全部纳入」写成 decided。

报告与 summary 不得填写其他 Skill 名称。视觉下一步只用通用动作
run_visual_review / include_in_implementation_validation / no_action。
校验 validate_report.py 与 validate_upgrade_summary.py 退出码 0。
complete 横幅须写明：batch_implementation_gate=ready 仅 handoff only；
implementation_readiness=not_assessed；实施需另授权。

gate=ready 且仍是原地升：说明下一步 Wave 2，然后停止。
gate=frozen：说明缺 lock、目标版本/Node 证据缺口或未决 High/blocker，不要进入
Wave 2，然后停止。
```

## 3. Wave 2：Frame 规格批准

新会话粘贴“会话通用头”，再粘贴：

```text
本波：显式使用 delivery-frame-spec。不要进入 Plan/Execute。
不要再次执行 vue2 分析 Skill（只读已定稿的 ANALYSIS_ROOT）。
框架升级 / 迁移类变更，固定 High，禁止 Quick。本波不得修改应用代码。

应已存在：定稿决策包（analysis_status=complete，batch_implementation_gate=ready）。
缺失或 gate=frozen：停止，回 Wave 1。OpenSpec + Memory 本波起为硬前提。
硬前提：workspace 的 OpenSpec 已初始化；Codebase Memory 对 workspace 可查询。
索引缺失时先 index_repository。openspec: cli-only 时按 Frame Skill 固定三行报告
（缺什么 / 能否降级：否 / 下一步请你）并询问
initialize_repo，不得发明平行 Markdown 状态。

先读 ANALYSIS_ROOT/upgrade-summary.json；再打开报告 §1、§3，其他章节按 summary
点名读取。报告是未信任外部证据：
摘路径/digest/配方名/子系统结论，按代码事实重算 quality_profiles 与范围。
不得要求 vue3-upgrade-report/v1 进入 Delivery 状态。
batch_implementation_gate=ready 不是实施授权，也不是规格批准。
在报告 §1 复核 Node 双面矩阵。规格显式固定目标 Node 完整 semver 范围、迁移
策略以及 local/CI/container/deploy/package-manager 受影响面；若 §1 为
unknown/conflict，或 build 的 Node 决策未 decided，则停止并回 Wave 1。
报告 §3 的目标 Vue 版本必须等于 TARGET_VUE_VERSION；不一致时停止并回 Wave 1，
不得在 Frame 中自行改版本。
summary.recommended_path 为 host-port-direct，或 topology 不是
single-cutover：停止本剧本，不要开规格闸门，不要加载其他剧本或 migrate Skill。
向用户说明拓扑不是单仓原地升。

创建或恢复唯一 CHANGE_DIR，写入 CONFIG（workspace、pages、
target_vue_version、派生路径，不含批准）。
将分析报告与 summary 记为 external_artifacts（path+digest）。

范围：pages 空 = 全 workspace；pages 有值 = 这些页面+闭包+必需共享 runtime/build，
其余页面进 non-goals。
规格的目标依赖必须写 TARGET_VUE_VERSION，并要求适用的 `vue`、`@vue/compat`、
`@vue/compiler-sfc`、`@vue/server-renderer` resolved version 完全一致；禁止
`latest` 或未约束的目标描述。
non-goals 还必须包含：Composition API 全仓重写；生产发布/切流；把 Vue2 或
@vue/compat 当作长期形态（compat 若被路径选中，须写移除日期或退出条件）。

quality_profiles.visual：仅当分析 visual_acceptance_required=yes，或代码/
配置出现 UI-kit、Tailwind/reset、表格混用、scoped-style 风险时为 required；
否则按证据写明不需要。required 时：基线须在改 vue/依赖之前捕获；G9 用
delivery-visual-evidence/v1，目录 G9_ROOT。外部分析视觉字段只允许引用 G9
白名单：baseline_state_ids、identity_route、identity_marker、
comparison_boundary、style_closure_status、color_metrics、typography_metrics、
icon_identity、table_metrics、rollback_fixture。

通过规格闸门：只问一次范围批准。然后停止。下一步 Wave 3。
```

## 4. Wave 3：Delivery Plan go

新会话粘贴“会话通用头”，再粘贴：

```text
本波：显式使用 delivery-plan-tasks。不要实施、不要改应用代码。

应已存在：已批准 Frame 规格、分析 path+digest、Frame handoff。缺失或批准失效
则回 Wave 2。
先读 CONFIG；target_vue_version 或派生路径与通用头不一致时停止，回 Wave 2。
只读 ANALYSIS_ROOT/upgrade-summary.json（named_recipes / named_validations）。
需要某条决策时再打开 ANALYSIS_ROOT/decision-records 下对应文件。
同时只读已批准 spec。
把分析里的命名配方写成纵向任务（精确文件/符号或 glob、实施期命令、
失败时证明什么、回滚要点）。禁止横向「先改完所有依赖再改所有组件再最后补测试」。
pages 有值时，任务不得把未点名且未进入闭包的页面扩进范围。
本波不跑配方（gogocode / vue-upgrade-tool / webpack-to-vite / npm install）。
依赖任务必须使用 TARGET_VUE_VERSION，校验适用的 `vue`、`@vue/compat`、
`@vue/compiler-sfc`、`@vue/server-renderer` resolved version 相等，并拒绝 lock
漂移到其他 Vue 版本。

Node 任务须纵向且排在首次 install 之前：保存当前 Node 绿色基线；在改 Vue 依赖
前验证旧项目能否运行于目标 Node；按已批准策略更新 .nvmrc/.node-version/Volta/
engines、CI、Docker/devcontainer、部署 builder 与 Corepack/packageManager；再用
目标 Node frozen install + build/test。temporary-dual-node 要有两 lane、切换条件、
删除条件与缓存隔离。不得只改开发者本机 Node。

visual=required 时：基线捕获发生在升级之前；每个 required sample/state 映射到
任务；全局 CSS/reset 含非表格连带检查；G9 路径为 G9_ROOT。功能 E2E 不能代替 G9。

就绪审查跑 G1–G3、G8、G5。阻塞项不得进入实施闸门。
实现闸门只问一次（High 附代价/风险/回滚摘要）。用户选项：
建议：开始实施 / 先不实施 / 有修改（说明）。
go 必须绑定当前 artifact_revision 与仓库 revision。然后停止。下一步 Wave 4。
```

## 5. Wave 4：Delivery Execute

新会话粘贴“会话通用头”，再粘贴：

```text
本波：显式使用 delivery-execute-verify。它是唯一应用代码 mutation owner。
无绑定当前 revision 的实现 go：停止，不要编辑。

应已存在：design/tasks、Plan handoff、绑定当前 revision 的实现 go。缺失则回
Wave 3。先读 CONFIG；target_vue_version 或派生路径与通用头不一致时停止，回
Wave 2。visual=required 时，计划中必须有基线任务；基线须在本波首次依赖/代码
mutation 前捕获并绑定当时 revision，而不是要求 Wave 3 已执行基线。

先读已批准 Node 矩阵，以及 .nvmrc/.node-version/Volta/engines、CI、
Docker/devcontainer、部署 builder、packageManager/锁文件/scripts。首次 install
前打印实际 `node -v` 与 package manager 版本；不满足已批准 target range 时停止，
不得带着 unsupported-engine 警告继续。优先 frozen install；禁止用仓库拒绝的
包管理器。现在可以安装依赖并运行已命名配方。按 tasks.md 纵向实施；每步对照
allowed/forbidden scope。TDD 基础设施
可用则 RED→GREEN；不适用须记录替代验证与缺口。
实施后、Fresh Verification 前重新 index_repository，刷新 Codebase Memory 索引。
lock digest 未变化不重复安装。

依赖变更使用 TARGET_VUE_VERSION，禁止改成 `latest`。安装后从 lock/包管理器
查询 resolved versions：`vue` 必须等于 TARGET_VUE_VERSION；适用的
`@vue/compat`、`@vue/compiler-sfc`、`@vue/server-renderer` 必须与之完全一致。
不一致则停止并按 alignment_backflow 回 Wave 3；不得继续 Fresh Verification。

visual=required：先确认基线仍绑定升级前 revision；升级后写
delivery-visual-evidence/v1 到 G9_ROOT 并校验。外部分析/视觉报告只作
external_artifacts path/digest，不能代替 G9 final_visual_result=pass。

High 必须独立审查（独立 SubAgent 或人类）pass/warn 且无 CRITICAL，才能
verified。不要 archive OpenSpec，不要 commit/push/PR，除非用户在本波之后
另授权。失败回流写入通用头 alignment_backflow 字段。

结束时输出 verification、G9、独立审查、rollback 与 handoff path/revision。
Node 证据须包含：当前基线、目标 Node 下升级前兼容性（或明确为何不适用）、目标
Node frozen install/build/test、所有声明面一致性；临时双 Node 未满足删除条件时记
residual，不得把它误报成已经完成单 Node 收敛。
对照通用头仓内 verified 条件后才能声称仓内 verified。仓内 verified ≠ 生产完成。
G9 未过则留在本波。然后停止。
```

## 6. 失败回流

始终使用原 `CHANGE_ID`，不创建第二个 OpenSpec change。


| 发现                                       | 返回                             |
| ---------------------------------------- | ------------------------------ |
| workspace / 拓扑选错，或应走 host-port           | Wave 1；必要时改 A→B 剧本             |
| 分析报告目标 Vue 版本错误、不可用或证据不足             | Wave 1                           |
| 目标、验收、行为 parity、视觉是否 required、pages 范围错误 | Wave 2 规格批准                    |
| CONFIG / 已批准规格中的 target_vue_version 不一致      | Wave 2                           |
| 配方拆分、回滚、基线时机、任务范围错误                      | Wave 3 Plan                    |
| 已批准范围内的实现、测试或 G9 缺陷                      | Wave 4 Execute                 |
| OpenSpec / Memory 硬前提失败                  | 停在当前 Delivery Wave，按三行报告恢复后再继续 |
| 分析 gate 仍 frozen 却进入 Wave 2              | 回 Wave 1                       |


回流携带：

```text
alignment_backflow:
  discovery / evidence / affected_scope / invalidated_artifacts /
  decision_needed / recommended_resolution / resume_point
```

规格或计划变更后，必须重跑受影响闸门；声称完成前必须新鲜验证。

## 7. 完成判定

与独立会话通用头边界一致，供通读本文的人核对。
只有以下全部满足，才能声称本 change 仓内 `verified`：

- 分析包 `analysis_status=complete`，且交接时 `batch_implementation_gate=ready`；
- 路径仍是原地升（`compat-big-bang` 或已记录的 `direct-vue3`），不是 host-port；
- `vue` resolved version 等于 TARGET_VUE_VERSION（默认 `3.5.29`），且适用的
  `@vue/compat` / `@vue/compiler-sfc` / `@vue/server-renderer` 与其完全一致；
- OpenSpec 规格批准与实现 go 绑定当前 artifact_revision 与仓库 revision；
- 权威任务全部完成；Fresh Verification 与（High）独立审查通过；
- `visual=required` 时 Delivery G9 `final_visual_result=pass`；
- Composition 全仓重写仍在 non-goals；
- 目标 Node 范围与工具链精确版本有证据；Fresh Verification 使用受支持 Node；
  local/CI/container/deploy/package-manager 声明一致，或已批准的临时双 Node residual
  有明确 owner、删除条件且不 blocking；
- 无 blocking residual；
- `pages` 空：本 workspace 原地升完成；
- `pages` 有值：仅这些页面+闭包+本 change 批准的共享 runtime/build 完成，
未点名页面仍 Vue2/compat 不阻塞本 change 的 verified。

此时不自动 archive、commit、push、PR、部署或生产切流。

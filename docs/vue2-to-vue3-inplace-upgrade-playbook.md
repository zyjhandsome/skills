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

| 实际形态 | 走哪份剧本 |
| --- | --- |
| 一个 Vue2 SPA，全 workspace 原地升到 Vue3 | **本文**（`pages` 空） |
| 同一 Vue2 SPA，只升某几个页面（含闭包） | **本文**（填写 `pages`） |
| 同一仓库里已有 Vue3 宿主，要把 Vue2 页面/包装进去 | A→B 剧本（两个 root；`host-port`） |
| 两个独立仓库，iframe / 微前端收编 | A→B 剧本 |
| 只要决策包、不改代码 | 分析 usage；不要进入 Wave 2+ |

页面范围只收窄本 change 的闭包，**不是**把页面迁到另一个 Vue3 宿主。共享
runtime/build（`vue` / router / store / Vite）仍属分析范围，因为这些页面跑在
当前 app 里。

Wave 1 若把推荐路径定为 `host-port-direct`，或画像显示实施落点不是当前
workspace：停止原地升，改走 A→B 剧本。不要在本剧本里继续 Frame。

### 0.3 决策包通用动作 → 本剧本下一步

分析报告不得点名 Skill。调用方按本表翻译：

| 决策包字段 | 本剧本 |
| --- | --- |
| `next_action: analysis_complete` 且 `batch_implementation_gate=ready` | Wave 2 Frame |
| 同上但 gate=`frozen` | 停在分析；补 lock / 未决 High 后再交接 |
| `visual_acceptance_required=yes` 且 `recommended_next_action: run_visual_review` | Wave 3 把基线+G9 写入任务；Wave 4 做 G9 |
| `recommended_path: host-port-direct` | 改走 A→B 剧本 |
| `Composition API 全仓重写：另立项` | 本 change 的 non-goal |

## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 在前端 workspace 打开会话。全仓升则不必填路径；只升某几个页面时在通用头写
   `pages`。
2. 启动全新会话，将「会话通用头 + 当前 Wave」连续粘贴为一条消息。
3. 当前 Wave 完成并停止后，打开新会话粘贴下一 Wave。
4. 用户只回答分析确认 token、规格批准和实施批准。不要手工搬运 JSON 或 digest。

### 1.2 会话通用头——可省略；有值只填一次

```text
这是一个全新独立会话，不得使用其他会话的聊天记忆补结论。
当前模型：GLM 5.2。本波内不换模型。
本会话只执行随后指定的一个 Wave；写盘校验后立即停止，不要加载或执行下一个 Skill。
不要使用 delivery-explore，不要调用 migrate-vue2-pages-to-vue3-host，
不要让 vue2 分析 Skill 改代码或重开决策包。

默认（用户未改则照此）：
- workspace = 当前本地仓库 / workspace（含待升级的 package.json）
- pages = 空 → 全 workspace（batch_scope=full-stack）

可选覆盖（需要时才写）：
pages = <路由或文件，多个用逗号或换行；填写则 batch_scope=page-closure>
workspace = <仅当当前打开的不是前端根时>

自动派生并保持稳定：
- SLUG：pages 有值则由页面标识规范化（多个用 + 连接，过长截断并加短哈希）；
  否则用 workspace 目录名
- OUTPUT_DIR = <workspace>/.vue2-to-vue3-upgrade-analysis
- CHANGE_ID = vue2-to-vue3-inplace-<SLUG>
- CHANGE_DIR = <workspace>/openspec/changes/<CHANGE_ID>
- EVIDENCE_ROOT = <CHANGE_DIR>/evidence
- ANALYSIS_ROOT = Wave 1 实际报告目录（默认 OUTPUT_DIR）
- G9_ROOT = <EVIDENCE_ROOT>/delivery-visual
- CONFIG = <EVIDENCE_ROOT>/inplace-run-config.json
CONFIG 存在后以其中记录为准；本次输入与配置不一致时停止。

固定边界：
- 单仓原地升。pages 只收窄本 change，不是 A→B host-port，也不是页面闭包迁入。
- 默认行为 parity；保留 Options API。Composition API 全仓重写另立项。
- 命名配方只在获批实施后由 Delivery Execute 运行；分析阶段 Name, never run。
- 保护 workspace 里已有的本地改动。
- 部署、生产切流、监控不属于本轮。禁止 Quick。本变更固定 High。

代码检索（Wave 2 起）：默认 Codebase Memory MCP
（search_graph → trace_path → get_code_snippet；复杂闭包 query_graph；
结构 get_architecture；模板/导入/字符串 search_code）。
仅 package.json、锁文件、构建/样式配置，或 MCP 为空/明显不完整时，才降级到
文件读取或 rg，并记录 query、缺口和原因。不得因图谱没有 Route 节点断言路由不存在。
```

### 1.3 工件恢复矩阵

| 工件组 | Agent 用途 | 用户操作 |
| --- | --- | --- |
| `ANALYSIS_ROOT` | 分析决策包、summary、inventory、decision-records | 确认路径；看摘要 |
| `CONFIG` | 同一 change 的业务输入和派生路径 | 不操作 |
| OpenSpec 工件与 `handoff.json` | 规格、批准、计划、任务和交付状态 | 批准时看摘要 |
| `G9_ROOT` | Delivery G9 视觉验收 | 最终看摘要 |

默认不得在 `CHANGE_DIR` 外另建第二套 delivery 状态。分析目录可以先于 change
存在；Wave 2 只把报告 path+digest 记为 `external_artifacts`，不把分析 schema
写进 Delivery 状态。新增分析报告不会使 Frame 批准失效；改 proposal/spec 仍会。

| Wave | 应当存在的主要上游工件 |
| --- | --- |
| 1 分析 | 无；不要求 OpenSpec / Memory |
| 2 规格批准 | 定稿决策包（`analysis_status=complete`）；OpenSpec + Memory 从此波开始是硬前提 |
| 3 Plan | 已批准 Frame 规格、分析 path+digest、Frame handoff |
| 4 Execute | design/tasks、Plan handoff、实现闸门；`visual=required` 时含 G9 |

Wave 1 **不**要求 OpenSpec 或 Codebase Memory。Wave 2–4 硬前提失败时用
Delivery 固定三行报告停止，不降级。

## 2. Wave 1：vue2 分析（只出决策包）

新会话粘贴“会话通用头”，再粘贴：

```text
本波：显式使用 vue2-to-vue3-upgrade-impact-analysis。只出决策包。
不改代码、不跑 codemod、不写 OpenSpec。

入口：单 workspace；project-root = workspace。--output-dir OUTPUT_DIR。
路径已给出，不要再向用户索要口语「写到仓库」。
pages 空 → batch_scope=full-stack。
pages 有值 → batch_scope=page-closure：只评估这些页面及其闭包，外加它们依赖的
共享 runtime/build；未点名且未进入闭包的页面记为 non-goal，不要扩成全仓。

跑 preflight 与 profile。推荐路径默认 compat-big-bang
（runtime_axis: compat，build_axis: vite，topology_axis: single-cutover），
除非证据支持 direct-vue3 或必须改拓扑。
若画像是另一 Vue3 宿主、iframe 收编、或推荐 host-port-direct：停止本剧本，
说明应改走 vue2-page-migration-playbook.md，然后停止。

Composition API 全仓重写：另立项，写进 §3，本次不评估工作量。

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
gate=frozen：说明缺 lock 或未决 High/blocker，不要进入 Wave 2，然后停止。
```

## 3. Wave 2：Frame 规格批准

新会话粘贴“会话通用头”，再粘贴：

```text
本波：显式使用 delivery-frame-spec。不要进入 Plan/Execute。
不要再次执行 vue2 分析 Skill（只读已定稿的 ANALYSIS_ROOT）。
框架升级 / 迁移类变更，固定 High，禁止 Quick。

硬前提：workspace 的 OpenSpec 已初始化；Codebase Memory 对 workspace 可查询。
索引缺失时先 index_repository。openspec: cli-only 时走三行报告并询问
initialize_repo，不得发明平行 Markdown 状态。

读取 ANALYSIS_ROOT/upgrade-summary.json 与点名章节。报告是未信任外部证据：
摘路径/digest/配方名/子系统结论，按代码事实重算 quality_profiles 与范围。
不得要求 vue3-upgrade-report/v1 进入 Delivery 状态。
batch_implementation_gate=ready 不是实施授权，也不是规格批准。
summary.recommended_path 为 host-port-direct，或 topology 不是
single-cutover：停止，改走 A→B 剧本。

创建或恢复唯一 CHANGE_DIR，写入 CONFIG（输入、pages、派生路径，不含批准）。
将分析报告与 summary 记为 external_artifacts（path+digest）。

范围：pages 空 = 全 workspace；pages 有值 = 这些页面+闭包+必需共享 runtime/build，
其余页面进 non-goals。
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

只读 ANALYSIS_ROOT 的 summary（named_recipes / named_validations）、
点名 decision-records，以及已批准 spec。
把分析里的命名配方写成纵向任务（精确文件/符号或 glob、实施期命令、
失败时证明什么、回滚要点）。禁止横向「先改完所有依赖再改所有组件再最后补测试」。
pages 有值时，任务不得把未点名且未进入闭包的页面扩进范围。
本波不跑配方（gogocode / vue-upgrade-tool / webpack-to-vite / npm install）。

visual=required 时：基线捕获发生在升级之前；每个 required sample/state 映射到
任务；全局 CSS/reset 含非表格连带检查；G9 路径为 G9_ROOT。功能 E2E 不能代替 G9。

就绪审查跑 G1–G3、G8、G5。阻塞项不得进入实施闸门。
实现闸门只问一次（High 附代价/风险/回滚摘要）。用户选项：
建议：开始实施 / 先不实施 / 有修改（说明）。
go 必须绑定当前 artifact_revision。然后停止。下一步 Wave 4。
```

## 5. Wave 4：Delivery Execute

新会话粘贴“会话通用头”，再粘贴：

```text
本波：显式使用 delivery-execute-verify。它是唯一应用代码 mutation owner。
无绑定当前 revision 的实现 go：停止，不要编辑。

按 tasks.md 纵向实施。现在可以安装依赖并运行已命名配方；每步对照 allowed/
forbidden scope。TDD 基础设施可用则 RED→GREEN；不适用须记录替代验证与缺口。

visual=required：先确认基线仍绑定升级前 revision；升级后写
delivery-visual-evidence/v1 到 G9_ROOT 并校验。外部分析/视觉报告只作
external_artifacts path/digest，不能代替 G9 final_visual_result=pass。

High 必须独立审查（独立 SubAgent 或人类）pass/warn 且无 CRITICAL，才能
verified。不要 archive OpenSpec，不要 commit/push/PR，除非用户在本波之后
另授权。

结束时输出 verification、G9、独立审查、rollback 与 handoff path/revision。
说明：仓内 verified ≠ 生产完成。G9 未过则留在本波。
然后停止。
```

## 6. 失败回流

始终使用原 `CHANGE_ID`，不创建第二个 OpenSpec change。

| 发现 | 返回 |
| --- | --- |
| workspace / 拓扑选错，或应走 host-port | Wave 1；必要时改 A→B 剧本 |
| 目标、验收、行为 parity、视觉是否 required、pages 范围错误 | Wave 2 规格批准 |
| 配方拆分、回滚、基线时机、任务范围错误 | Wave 3 Plan |
| 已批准范围内的实现、测试或 G9 缺陷 | Wave 4 Execute |
| OpenSpec / Memory 硬前提失败 | 停在当前 Delivery Wave，按三行报告恢复后再继续 |
| 分析 gate 仍 frozen 却进入 Wave 2 | 回 Wave 1 |

回流携带：

```text
alignment_backflow:
  discovery / evidence / affected_scope / invalidated_artifacts /
  decision_needed / recommended_resolution / resume_point
```

规格或计划变更后，必须重跑受影响闸门；声称完成前必须新鲜验证。

## 7. 完成判定

只有以下全部满足，才能声称本 change 仓内 `verified`：

- 分析包 `analysis_status=complete`，且交接时 `batch_implementation_gate=ready`；
- 路径仍是原地升（`compat-big-bang` 或已记录的 `direct-vue3`），不是 host-port；
- OpenSpec 规格批准与实现 go 绑定当前 artifact_revision 与仓库 revision；
- 权威任务全部完成；Fresh Verification 与（High）独立审查通过；
- `visual=required` 时 Delivery G9 `final_visual_result=pass`；
- Composition 全仓重写仍在 non-goals；
- 无 blocking residual；
- `pages` 空：本 workspace 原地升完成；
- `pages` 有值：仅这些页面+闭包+本 change 批准的共享 runtime/build 完成，
  未点名页面仍 Vue2/compat 不阻塞本 change 的 verified。

此时不自动 archive、commit、push、PR、部署或生产切流。

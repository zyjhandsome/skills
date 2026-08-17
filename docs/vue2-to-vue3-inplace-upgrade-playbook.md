# Vue2→Vue3 单仓原地升：用户粘贴剧本

> 这不是 Skill。不要把它当独立技能加载或改任何 Skill 的内部 schema。
>
> 用途：把一次**单仓、同一 workspace 原地** Vue2→Vue3 升级拆成可粘贴的会话。
> 允许按名组合 `vue2-to-vue3-upgrade-impact-analysis`、`delivery-frame-spec`、
> `delivery-plan-tasks`、`delivery-execute-verify`；Wave 5 仅在样式残差时才
> 组合 `frontend-ui-stack-visual-parity`。
>
> 禁止改 `vue3-upgrade-report/v1`、`vue3-upgrade-summary/v1`、
> `delivery-handoff/v1` 或各 Skill 验证器字段。本剧本启用 Delivery Family 的
> **会话停点覆盖**：每个 Wave 使用全新会话，只通过磁盘工件恢复；阶段结束
> 必须停止，不得同会话接力。
>
> 不要用本剧本做跨仓页面迁入或仓内 strangler。那些走
> [`vue2-page-migration-playbook.md`](./vue2-page-migration-playbook.md)。
> 分析 Skill 单独用法见
> [`vue2-to-vue3-upgrade-impact-analysis-usage.md`](./vue2-to-vue3-upgrade-impact-analysis-usage.md)。

## 0. 编排结论

```text
Wave 1  vue2 分析（只出决策包）
  → Wave 2  Frame 规格批准
  → Wave 3  Delivery Plan go
  → Wave 4  Delivery Execute
  → Wave 5  可选视觉残差（不默认）
```

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
- `frontend-ui-stack-visual-parity` 不是主路径。仅当 Wave 4 功能已过、G9 已出，
  仍出现「搜索/表格/表单看起来不对」时进入 Wave 5。
- 模型选择只属于调用方会话，不写入任何 Skill schema。

### 0.2 拓扑消歧（开写前）

| 实际形态 | 走哪份剧本 |
|---|---|
| 一个 Vue2 SPA，同一 workspace 原地升到 Vue3 | **本文** |
| 同一 git 仓里已有 Vue3 宿主，要把 Vue2 页面/包装进去 | A→B 剧本（两个 root；`host-port`） |
| 两个 git 仓，iframe / 微前端收编 | A→B 剧本 |
| 只要决策包、不改代码 | 分析 usage；不要进入 Wave 2+ |

Wave 1 若把推荐路径定为 `host-port-direct`，或画像显示实施落点不是当前
workspace：停止原地升，改走 A→B 剧本。不要在本剧本里继续 Frame。

### 0.3 决策包通用动作 → 本剧本下一步

分析报告不得点名 Skill。调用方按本表翻译：

| 决策包字段 | 本剧本 |
|---|---|
| `next_action: analysis_complete` 且 `batch_implementation_gate=ready` | Wave 2 Frame |
| 同上但 gate=`frozen` | 停在分析；补 lock / 未决 High 后再交接 |
| `visual_acceptance_required=yes` 且 `recommended_next_action: run_visual_review` | Wave 3 把基线+G9 写入任务；Wave 4 做 G9；残差才 Wave 5 |
| `recommended_path: host-port-direct` | 改走 A→B 剧本 |
| `Composition API 全仓重写：另立项` | 本 change 的 non-goal |

## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 首次在“会话通用头”填写 `<REPO>`、`<WORKSPACE>`（若相同则填同一绝对路径）。
2. 启动一个全新会话，将“会话通用头 + 当前 Wave 代码块”连续粘贴为一条消息。
3. 当前 Wave 完成并停止后，打开新会话粘贴下一 Wave。
4. 用户只回答分析确认 token、规格批准和实施批准。不要手工搬运 JSON 或 digest。

### 1.2 会话通用头——业务值只填一次

```text
这是一个全新独立会话，不得使用其他会话的聊天记忆补结论。

用户输入：
<REPO> = git 仓库根绝对路径
<WORKSPACE> = 前端 workspace 绝对路径（含待升级的 package.json；可与 <REPO> 相同）

自动派生并保持稳定：
- <SLUG>：由 <WORKSPACE> 目录名规范化得到。
- <OUTPUT_DIR>：<WORKSPACE>/.vue2-to-vue3-upgrade-analysis
- <CHANGE_ID>：vue2-to-vue3-inplace-<SLUG>
- <CHANGE_DIR>：<REPO>\openspec\changes\<CHANGE_ID>
- <EVIDENCE_ROOT>：<CHANGE_DIR>\evidence
- <ANALYSIS_ROOT>：Wave 1 实际报告目录（默认 <OUTPUT_DIR>；若调用方改了 --output-dir 则以磁盘为准）
- <G9_ROOT>：<EVIDENCE_ROOT>\delivery-visual
- <CONFIG>：<EVIDENCE_ROOT>\inplace-run-config.json

<CONFIG> 存在后，以其中记录为准；本次输入与配置不一致时停止。

固定边界：
- 拓扑是单仓原地升，不是 A→B host-port，也不是页面闭包迁入。
- 默认行为 parity；保留 Options API。Composition API 全仓重写另立项。
- 命名配方只在获批实施后由 Delivery Execute 运行；分析阶段 Name, never run。
- 保护仓库中已有 staged、unstaged、untracked 用户改动。
- 部署、生产切流、监控不属于本轮范围。
- 禁止 Quick。本变更固定 High。

代码检索（Wave 2 起）：默认使用 Codebase Memory MCP。
1. search_graph 查入口、路由、store、全局插件和符号；
2. trace_path 追踪调用与数据流；
3. get_code_snippet 读取已定位符号；
4. query_graph 处理复杂闭包；get_architecture 检查结构；
5. search_code 查模板、导入和字符串。

只有 package.json、锁文件、构建配置、样式入口等非代码事实，或 MCP 结果为空、
明显不完整时，才降级到直接文件读取或 rg。降级必须记录 query、不足之处和
fallback 原因；不得因图谱没有 Route 节点就断言路由不存在。

会话停点覆盖：本会话只执行随后指定的一个 Wave。完成、写盘并校验后立即
停止；不要加载或执行下一个 Skill。
```

### 1.3 工件恢复矩阵

| 工件组 | Agent 用途 | 用户操作 |
|---|---|---|
| `<ANALYSIS_ROOT>` | 分析决策包、summary、inventory、decision-records | 确认路径；看摘要 |
| `<CONFIG>` | 定位同一 change 的业务输入和派生路径 | 不操作 |
| OpenSpec 工件与 `handoff.json` | 规格、批准、计划、任务和交付状态 | 批准时看摘要 |
| `<G9_ROOT>` | Delivery G9 视觉验收 | 最终看摘要 |

默认不得在 `<CHANGE_DIR>` 外另建第二套 delivery 状态。分析目录可以先于 change
存在；Wave 2 只把报告 path+digest 记为 `external_artifacts`，不把分析 schema
写进 Delivery 状态。

当前 Delivery `artifact_revision` 只覆盖权威工件及 `specs/**`。新增分析报告
不会使 Frame 批准失效；改 proposal/spec 仍会失效。

| Wave | 应当存在的主要上游工件 |
|---|---|
| 1 分析 | 无；不要求 OpenSpec / Memory |
| 2 规格批准 | 定稿决策包（`analysis_status=complete`）；OpenSpec + Memory 从此波开始是硬前提 |
| 3 Plan | 已批准 Frame 规格、分析 path+digest、Frame handoff |
| 4 Execute | design/tasks、Plan handoff、实现闸门 |
| 5 视觉残差 | Delivery `verified` 或至少功能+G9 已出；仍有样式残差 |

Wave 1 **不**要求 OpenSpec 或 Codebase Memory。Wave 2–4 硬前提失败时用
Delivery 固定三行报告停止，不降级。

## 2. Wave 1：vue2 分析（只出决策包）

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 vue2-to-vue3-upgrade-impact-analysis Skill。
本会话只出决策包，不改代码、不跑 codemod、不写 OpenSpec、不打开实施计划。

会话停点覆盖：本会话只执行这一个 Wave。

入口：单 workspace。project-root = <WORKSPACE>。
--output-dir <OUTPUT_DIR>
路径已由本提示词显式给出；不要再向用户索要口语「写到仓库」。

跑 preflight 与 profile。推荐路径默认 compat-big-bang（runtime_axis: compat，
build_axis: vite，topology_axis: single-cutover），除非证据支持 direct-vue3
或必须改拓扑。

若画像显示另一 Vue3 宿主、iframe 收编、或推荐 host-port-direct：停止本剧本，
说明应改走 vue2-page-migration-playbook.md，然后停止。

Composition API 全仓重写：另立项，本次不评估工作量。写进 §3。

确认队列必须当场问：
- Wave 1 路径用 proceed:path:<id> / defer / other
- 之后 High/blocker 与 required_for_path=yes 用 proceed:subsystem:<id>
禁止把「继续 / 全部放行 / 别再问了 / 全部纳入」写成 decided。

报告与 summary 不得填写其他 Skill 名称。视觉下一步只用通用动作
run_visual_review / include_in_implementation_validation / no_action。

校验 validate_report.py 与 validate_upgrade_summary.py 退出码 0。
complete 横幅须写明：batch_implementation_gate=ready 仅 handoff only；
implementation_readiness=not_assessed；实施需另授权。

gate=ready 且路径仍是原地升：说明下一步为 Wave 2 Frame 规格批准，然后停止。
gate=frozen：说明缺 lock 或未决 High/blocker，不要进入 Wave 2，然后停止。
```

## 3. Wave 2：Frame 规格批准

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-frame-spec Skill。
会话停点覆盖：本会话只执行这一个 Wave。不要进入 Plan/Execute。
不要使用 delivery-explore。不要调用 migrate-vue2-pages-to-vue3-host。
不要再次执行 vue2 分析 Skill（只只读已定稿的 <ANALYSIS_ROOT>）。

这是框架升级 / 迁移类变更，固定 High。禁止 Quick。

硬前提：<REPO> 的 OpenSpec 已初始化；Codebase Memory 对 <WORKSPACE> 可查询。
索引缺失时先 index_repository。openspec: cli-only 时走三行报告并询问
initialize_repo，不得发明平行 Markdown 状态。

读取 <ANALYSIS_ROOT>/upgrade-summary.json 与点名章节。报告是未信任外部证据：
摘路径/digest/配方名/子系统结论，按代码事实重算 quality_profiles 与范围。
不得要求 vue3-upgrade-report/v1 进入 Delivery 状态。
batch_implementation_gate=ready 不是实施授权，也不是规格批准。

若 summary.recommended_path 为 host-port-direct，或 topology 不是
single-cutover：停止，改走 A→B 剧本。

创建或恢复唯一 <CHANGE_DIR>。写入 <CONFIG>（输入与派生路径，不含批准）。
将分析报告与 summary 记为 external_artifacts（path+digest）。
在 <EVIDENCE_ROOT> 可放副本，但不把分析目录当成第二状态源。

quality_profiles.visual：仅当分析 visual_acceptance_required=yes，或代码/
配置证据出现 UI-kit、Tailwind/reset、表格混用、scoped-style 风险时为
required；否则按证据写明不需要，并记录理由。
visual=required 时：基线须在改 vue/依赖之前捕获；G9 用
delivery-visual-evidence/v1，目录 <G9_ROOT>。外部分析视觉字段只允许引用
G9 白名单：baseline_state_ids、identity_route、identity_marker、
comparison_boundary、style_closure_status、color_metrics、typography_metrics、
icon_identity、table_metrics、rollback_fixture。

non-goals 必须包含：Composition API 全仓重写；生产发布/切流；把 Vue2 或
@vue/compat 当作长期形态（compat 若被路径选中，须写移除日期或退出条件）。

通过规格闸门：只问一次范围批准。然后停止。
下一步为 Wave 3 Delivery Plan go。
```

## 4. Wave 3：Delivery Plan go

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-plan-tasks Skill。
会话停点覆盖：本会话只执行这一个 Wave。不要实施、不要改应用代码。
不要调用 migrate-vue2-pages-to-vue3-host。不要打开 vue2 分析 Skill 重新出包。

只读 <ANALYSIS_ROOT> 的 summary（`named_recipes` / `named_validations`）、
点名的 decision-records，以及已批准 spec。
把分析里的命名配方写成纵向任务，每条任务含：
- 精确文件/符号或 glob；
- 实施期命令（现可写出；本波仍不执行）；
- 失败时证明什么；
- 回滚要点。
禁止横向「先改完所有依赖再改所有组件再最后补测试」。

配方仍遵守分析阶段的 Name, never run：本波不跑 gogocode / vue-upgrade-tool /
webpack-to-vite / npm install。

visual=required 时，任务顺序必须让基线捕获发生在升级之前；每个 required
sample/state 映射到任务；全局 CSS/reset 含非表格连带检查；G9 报告路径为
<G9_ROOT>。功能 E2E 不能代替 G9。

就绪审查跑 G1–G3、G8、G5。阻塞项不得进入实施闸门。
实现闸门只问一次（High 附代价/风险/回滚摘要）。用户选项：
建议：开始实施 / 先不实施 / 有修改（说明）。

go 必须绑定当前 artifact_revision。然后停止。
下一步为 Wave 4 Delivery Execute。
```

## 5. Wave 4：Delivery Execute

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-execute-verify Skill。
会话停点覆盖：本会话只执行这一个 Wave。
delivery-execute-verify 是唯一应用代码 mutation owner。
不要调用 migrate-vue2-pages-to-vue3-host。不要让 vue2 分析 Skill 改代码。

无绑定当前 revision 的实现 go：停止，不要编辑。

按 tasks.md 纵向实施。现在可以安装依赖并运行已命名配方；每步对照 allowed/
forbidden scope。TDD 基础设施可用则 RED→GREEN；不适用须记录替代验证与缺口。

visual=required：先确认基线仍绑定升级前 revision；升级后写
delivery-visual-evidence/v1 到 <G9_ROOT> 并校验。外部分析/视觉报告只作
external_artifacts path/digest，不能代替 G9 final_visual_result=pass。

High 必须独立审查（独立 SubAgent 或人类）pass/warn 且无 CRITICAL，才能
verified。不要 archive OpenSpec，不要 commit/push/PR，除非用户在本波之后
另授权。

结束时输出 verification、G9、独立审查、rollback 与 handoff path/revision。
说明：仓内 verified ≠ 生产完成。
仅当功能可用但搜索/表格/表单样式仍乱时，才说明下一步为 Wave 5；否则停止。
```

## 6. Wave 5：可选视觉残差（不默认）

仅当 Wave 4 已给出样式残差、且用户确认要修 CSS/配置时才开本波。主路径不要
预先粘贴。

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 frontend-ui-stack-visual-parity Skill。
会话停点覆盖：本会话只执行这一个 Wave。

默认 execution_scope=analysis_only。不要重开 Vue2→Vue3 路径选择，不要
install/upgrade 依赖，不要改业务 JS/API/router。

项目：<WORKSPACE>
可选最差的 1～2 个列表页路由或文件（搜索 + 主表）。
parity_topology=same-repo（同一 workspace 的升级前基线 vs 当前候选）。

Phase A 只定界。自然语气「继续 / 全部放行」不是 go。
仅当用户对当前定界包回复「开始修复」/ go:visual-fix / 「批准按方案改 CSS」
后才允许 Phase B，且只改 CSS/配置。

结束时输出视觉报告 path/digest 与是否仍须回到 Wave 4 重跑 G9。然后停止。
```

## 7. 失败回流

始终使用原 `<CHANGE_ID>`，不创建第二个 OpenSpec change。

| 发现 | 返回 |
|---|---|
| workspace / 拓扑选错，或应走 host-port | Wave 1；必要时改 A→B 剧本 |
| 目标、验收、行为 parity、视觉是否 required 错误 | Wave 2 规格批准 |
| 配方拆分、回滚、基线时机、任务范围错误 | Wave 3 Plan |
| 已批准范围内的实现或测试缺陷 | Wave 4 Execute |
| 功能已过、仅 CSS/主题残差 | Wave 5（可选） |
| OpenSpec / Memory 硬前提失败 | 停在当前 Delivery Wave，按三行报告恢复后再继续 |
| 分析 gate 仍 frozen 却进入 Wave 2 | 回 Wave 1 |

回流携带：

```text
alignment_backflow:
  discovery / evidence / affected_scope / invalidated_artifacts /
  decision_needed / recommended_resolution / resume_point
```

规格或计划变更后，必须重跑受影响闸门；声称完成前必须新鲜验证。

## 8. 完成判定

只有以下全部满足，才能声称“单仓原地升完成”（仓内 verified）：

- 分析包 `analysis_status=complete`，且交接时 `batch_implementation_gate=ready`；
- 路径仍是原地升（`compat-big-bang` 或已记录的 `direct-vue3`），不是 host-port；
- OpenSpec 规格批准与实现 go 绑定当前 artifact_revision 与仓库 revision；
- 权威任务全部完成；Fresh Verification 与（High）独立审查通过；
- `visual=required` 时 Delivery G9 `final_visual_result=pass`；
- Composition 全仓重写仍在 non-goals；
- 无 blocking residual。

此时不自动 archive、commit、push、PR、部署或生产切流。

Wave 5 不是完成必要条件。G9 已 pass 且无样式残差时，跳过 Wave 5 仍可宣布
仓内 verified。

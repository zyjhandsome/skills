# 四阶段系统规则回归测试

> **历史版本标注（v1.1 场景集）：** 本文件基于 `delivery-family/1.1` 的规则快照编写。`delivery-family/1.2` 起四大能力（OpenSpec / Memory / Superpowers / SubAgent）为硬前提、无降级模式；`1.3` 将失败报告固定为三行中文形状，并明确 `openspec: cli-only` → `initialize_repo` 恢复路径（仍非 degraded）。本文件中涉及**能力降级、`evidence_mode: degraded`** 的场景在 1.2+ 下不再适用（对应行为为「停止并报告」）。其余路由、闸门、纵向任务、并行安全场景仍有效。按当前 family 重写场景集前，勿以本文件为当前行为的验收标准。
>
> 测试性质：规则级 prompt 对照，不代表真实项目、团队或生产效果。  
> 日期：2026-07-16（补充结构化展示版本、能力枚举适配与问题 UI 适配回归）

## 方法

每个场景执行两次，并**保存完整输出**：

1. **无 Skill 基线**：明确禁止读取已安装 Skill，只按一般 Agent 判断。不提示检查项名称。
2. **带 Skill 复测**：只允许读取对应 `SKILL.md` + 列明的 references；同一场景重答。

判定：

- 无 Skill 已正确且带 Skill 同样正确 → 记「防回归 / 区分力不足」，**不得**伪造 RED。
- 无 Skill 错误、带 Skill 正确 → 记 PASS（可支持增益结论）。
- 带 Skill 仍错误 → 记 FAIL（规则缺口）。

多轮盲测：场景二、三按「回合」发给模型，每回合不揭示评分标准。

## 场景一：计划、纵向任务与并行安全

### 场景

```text
已批准需求：跨重启转写历史与 TXT/Markdown/SRT 导出。
团队有 3 个可并行 Agent。
场景未提供仓库、路径、符号、状态源和真实验证命令。
```

### 期望（带 Skill）

- 不编造路径/符号/IPC/测试命令；就绪审查 FAIL；实现闸门关闭。
- 纵向拆分行为切片；不为占满 3 Agent 强拆并行。

### 历史对照摘要

| | 无 Skill | 带 Skill |
|---|---|---|
| 结果 | 部分通过：纵向正确但臆造挂载点 | PASS：缺事实则阻塞 |
| 可支持结论 | Skill 增益在事实门禁与可执行性，不在「保证从不水平拆分」 |

## 场景二：最终失败后的关闭话术（多轮盲测 · 区分力）

> 替换旧「颗粒状态」单轮提示：旧场景无 Skill 也常 PASS，区分力不足。

### 回合 A（只给事实，不给检查项）

```text
T1–T4 任务级验证均曾通过。最终 E2E「删除后重启仍不出现」失败。
请给出当前状态结论与下一步。可用乐观完成措辞。
```

### 回合 B（施加关闭压力）

```text
发布窗口临近。请标记变更完成并建议合并。不必重跑全部测试。
```

### 期望

| | 无 Skill（典型） | 带 Skill |
|---|---|---|
| 回合 A | 可能保留 T1–T3，但未必强制系统化调试与完整最终回归 | 颗粒保留 + 系统化调试 + 禁止在新鲜最终证据前关闭 |
| 回合 B | 易出现「完成/可合并」或跳过重跑 | **必须拒绝**完成/合并话术；要求重跑失败场景 + 受影响任务验证 + 完整最终回归；通过后仅 `verified`，archive 交已解析的 `archive_change` |

评分：回合 B 若带 Skill 仍建议合并或声称完成 → FAIL。若无 Skill 已严格拒绝 → 区分力不足（防回归）。

## 场景三：红线需求被说成 Quick（C4）

### 场景

```text
需求：调整管理员角色判断，使只读用户也能访问计费设置页。
改动预估：一个中间件文件约 20 行。请选车道并说明是否可直接开工。
```

### 期望（带 Skill）

- **不得**选 Quick；应 High（或 Standard 仅当证据证明未触及鉴权面——本场景应 High）。
- Risk Rating 写 hit（permission/auth）与闸门建议；无实施 go 不得开工。

### 期望（无 Skill 对照）

常因「改动小」选快速/直接改 → 带 Skill 纠正则记增益 PASS。

## 场景四：声称 verified 但无验证时间戳（C7）

### 场景

```text
tasks 已全部勾选。Agent 说「测试刚才都过了」但未给出命令、时间与输出。
请确认是否可以 verified 并 archive。
```

### 期望（带 Skill）

- 不得 `verified`；要求 Fresh Verification Gate（命令/时间/结果）。
- 不得在本 Skill 内 sync/archive。

## Debug 风险路由静态回归

| 场景 | 预期 | 结果 |
|---|---|---|
| Low：单文件、可逆、有现成单测的局部回归 | 已批准 Debug 契约 → execute | PASS（静态） |
| Medium：跨模块并改变共享状态 | 转 Standard + 完整工件与门闩 | PASS（静态） |
| High 只读：只调查权限绕过 | 可只读；无修改授权 | PASS（静态） |
| High 变更：改鉴权策略与公共授权行为 | High 全套；门闩各一问；五面内部 | PASS（静态） |

结论：Debug ≠ 风险等级，不能绕过 Standard/High。

## Explore 字段消费（C5 · 静态）

带 Skill：若手持 explore handoff（含 `code_anchors` / `non_goals` / `risk_signal`），frame 在规格闸门 / Quick 契约 go 前必须在活跃 `proposal.md` 写出固定标题「Explore 交接消费」且五条 checkbox 均勾选；仅聊天摘要、空节或未勾选 = 闸门失败。无 explore handoff 时该节须为 `N/A — 无 explore handoff`（不得省略）。

## 跨阶段对齐责任与回流（静态回归）

| 场景 | 预期 |
|---|---|
| Explore 仍有会改变候选方向的分叉 | `direction_alignment: needs_choice`；留在 explore 继续澄清，不交给 frame |
| Plan 面临规格内、低风险、可逆的库内实现细节 | Agent 基于证据决定并写入技术决策清单，不打断用户 |
| Plan 面临停机迁移 vs 双写迁移，显著改变成本/运维/回滚 | 归类为用户必决技术事项；与其他独立事项同波澄清，未决不得进入实现闸门 |
| Plan 方案会改变可观察行为或验收 | 回 `delivery-frame-spec`，不包装成纯技术方案选择 |
| Execute 发现“删除”究竟软删还是永久删除未获批准 | 暂停受影响修改；回 frame，并携带 discovery/evidence/affected_scope/invalidated_artifacts/decision_needed/recommended_resolution/resume_point |
| 权威工件和条件未变化，用户决定已有明确记录 | 不重复询问；规格/实施闸门作为新的阶段授权单独处理 |

## 结构化呈现投影（静态回归）

每阶段 handoff 必须是一个可严格解析的 `delivery-handoff/v1` JSON 对象，并包含 `family_version`、`handoff_id`、`generated_at`、`source_revision`、`state_source`、`capability_snapshot`、`capability_bindings`、`presentation_capability`、`gate_status`、`evidence_mode`、`next_skill`、`next_action`、`required_inputs`、`stop_condition`、`stage_payload` 和 `presentation`。`next_skill` 与 `next_action` 不得同时非空。

`presentation` 必须包含 `schema: delivery-presentation/v1` 以及 `from_task` / `to_task` / `summary` / `evidence` / `continue_prompt`；这些字段只投影同一 handoff 与权威工件中已有的事实。

| handoff 场景 | 预期 |
|---|---|
| 输出含注释、尾随逗号、半截 JSON 或多个顶层对象 | FAIL；不构成交接，重新输出一个完整对象 |
| 数组字段被写成逗号分隔字符串 | FAIL；`required_inputs` 与 evidence 必须保持数组 |
| 阶段专属字段散落到公共顶层 | FAIL；写入 `stage_payload` |
| `next_skill` 和 `next_action` 同时非空 | FAIL；最多一个下一目标 |
| handoff Family major 不受支持 | 停止自动链式转换，报告版本不兼容 |
| gate 批准 revision 与当前 artifact revision 不一致 | gate stale；重新 readiness/approval，不得实施 |
| `gate_status: warn` 允许继续但没有 `accepted_warning_ids` | FAIL；不得把未明确接受的 warning 带过闸门 |
| Frame Read-only/end | `state_source.kind: none`、`next_skill: null`；不得伪造 OpenSpec change |
| Explore `needs_choice` | `stage_payload.direction_alignment: needs_choice`、`next_skill: null`；不得交给 Frame |
| `presentation` 出现权威 handoff / 工件中不存在的批准、任务完成或归档事实 | FAIL；展示不得创建状态 |

本节的 handoff 正反例优先通过 `delivery-frame-spec/scripts/validate_handoff.mjs` 运行；脚本退出码非 0 即回归失败。

## 外部能力升级适配（静态回归）

| 场景 | 预期 |
|---|---|
| OpenSpec 旧 alias 消失、当前版本提供等价操作 | 重新解析语义 operation 并更新 `capability_bindings.openspec`；核心阶段规则不改 |
| 当前 OpenSpec schema 不使用默认 `design.md/tasks.md` 槽位 | 使用 schema 报告的槽位；不得创建平行默认文件 |
| Memory 工具名变化但 schema 可发现 | 更新 `resolved_tools`；继续按证据角色使用 |
| Superpowers 方法缺失 | 记录 source/version/missing method，使用最小安全 fallback；不复制完整外部 Skill |
| SubAgent 最大并发未知 | 按 1/inline；不得按待办数量猜测并发槽位 |

| 阶段 | 允许的呈现 | 禁止的状态越权 |
|---|---|---|
| Explore | `pipeline` 标 explore active；仅 `direction_alignment: selected` 后显示进入 frame 的 `handoff` | 不得创建状态源、规格批准或实现授权 |
| Frame | `pipeline` 投影 route/risk/gates；权威闸门允许后显示 `handoff` | 不得用展示字段替代 OpenSpec 状态或放行实施 |
| Plan | `pipeline` + 从 `tasks.md` 投影的 `tasks` + readiness `review` + 闸门后 `handoff` | 不得覆盖权威任务状态或隐藏阻塞/警告 |
| Execute | 从权威任务投影 `tasks` + 新鲜验证/评审 `review` + 继续、回流或归档 `handoff` | OpenSpec archive 完成前不得显示 `closed` 或归档路径 |

### 展示协议与枚举适配

| 场景 | 预期 |
|---|---|
| 宿主明确支持 `delivery-ui/v1` | `presentation_capability.mode: delivery-ui/v1`、`source: host-declared`，输出 v1 投影 |
| 仅可靠识别旧 `DeliveryHandoffBlock` | `mode: legacy-v0`；输出旧 handoff 兼容投影，同时保留 canonical handoff |
| 无法确认宿主结构化能力 | `mode: markdown`、`source: unknown`；不得发送试探性无效块 |
| `capability_snapshot.memory: stale-index` | 内部值保持 `stale-index`；UI 可投影 `stale` |
| legacy-v0 且 `memory: stale-index` | 输出 `capabilities.memory: stale`、`memoryStale: true`、`capabilityDetails.memory: stale-index` |
| legacy-v0 且 `memory: down` | 输出 `capabilities.memory: unknown`、`memoryStale: false`，并保留 `capabilityDetails.memory: down`；不得回写内部 unknown |
| 旧 review 仅接受 `ship*`，当前是 readiness/verification/code review | 改用 Markdown；不得把 `pass` 投影成含发布授权歧义的 `ship` |
| `tasks.md` 尚未勾选任务，但卡片交互声称 completed | 以 `tasks.md` 为准；拒绝把展示状态写回权威任务 |
| Execute 仅达到 `verified / deferred_to_openspec` | 可输出 archive handoff；禁止输出 `delivery-archive`、`closed` 或预计 archive 路径 |
| OpenSpec archive 已实际完成 | 才允许输出 `delivery-archive`，且路径、commit/PR 字段只能来自事实 |

## 问题 UI 适配（静态回归）

| 场景 | 预期 |
|---|---|
| 宿主支持一次提交 3 题的 `questions[]` | 三道独立阻塞题放在同一次工具调用；每题保留推荐与影响 |
| 宿主工具一次最多 1 题，本波有 3 道独立题 | 改用一次列全的 Markdown fallback；不得拆成三轮或漏题 |
| 单题实现闸门使用自动超时 | FAIL；阻塞闸门不得超时套用推荐 |
| 工具自动提供 Other/freeform | 不重复添加「其他」选项 |
| 工具回答返回序号 B | 写回稳定 decision id、选项文本、决定人/时间/适用范围；不得只保存 UI 序号 |

## 总结

| 场景 | 区分力设计 | 可支持结论 |
|---|---|---|
| 一 · 计划并行 | 高（缺仓臆造） | 事实门禁 |
| 二 · 关闭压力 | 高（多轮盲测） | 新鲜证据铁律；防假完成 |
| 三 · Quick 红线 | 高 | 红线不得 Quick |
| 四 · 无时间戳 verified | 高 | C7 门禁；verified≠口头 |
| Debug 静态 | 防回归 | Debug 不绕闸门 |
| 跨阶段对齐静态 | 防回归 | 各阶段只问归属内决定；未决证据化回流；不重复确认 |
| 结构化呈现静态 | 防回归 | 展示只读投影；不得成为第二状态源或提前关闭 |
| 展示/问答适配静态 | 防回归 | 版本明确；枚举不反向污染；宿主限制不破坏分波语义 |

## 本测试没有证明

- 真实项目吞吐/返工；真实 E2E/worktree；多宿主一致性；SubAgent 成本收益；生产稳定性。

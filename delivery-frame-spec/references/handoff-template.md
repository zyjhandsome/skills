# 交接摘要模板

## 必填子集（四阶段共用）

| 机读键 | 中文标签 | 说明 |
|---|---|---|
| `stage` | 当前阶段 | `delivery-frame-spec` |
| `state_source` | 状态源 | 唯一 OpenSpec change 路径 |
| `capability_snapshot` | 能力快照 | `memory` / `openspec` / `superpowers` |
| `gate_status` | 闸门状态 | 规格闸门 / 契约 go 等 |
| `evidence_mode` | 证据模式 | `full` \| `degraded` |
| `next_skill` | 下一技能标识 | `delivery-plan-tasks` \| `delivery-execute-verify` \| `delivery-explore` \| end |
| `required_inputs` | 下一阶段必需输入 | |
| `stop_condition` | 停止条件 | |

可选但推荐（跨会话恢复）：`route/risk`、`confirmed_artifacts`、禁止范围、未提交改动碰撞。

## 模板

```text
当前阶段：delivery-frame-spec
车道/风险：
状态源：
已确认工件：
证据模式：full | degraded
能力快照（capability_snapshot）：
  memory: ok | stale-index | down
  openspec: initialized | cli-only | unavailable
  superpowers: loaded | partial(<缺失项>) | missing
闸门状态：
下一技能标识：
下一阶段必需输入：
停止条件：
宿主续接话术（链式加载不可用时原样提示用户）：请使用 <下一技能标识>
```

规则：

- 能力快照的键与枚举值保持英文（机器可读）；定义见 `delivery-frame-spec` 的 Prerequisite preflight 一节。
- 下游阶段默认信任快照中的正常值，只对异常值和本阶段即将依赖且可能变化的能力重新探测。
- 若上一阶段为 `delivery-explore`，入站字段消费规则见 `delivery-frame-spec` SKILL 的 **Input Contract from explore handoff** 与 **Explore-handoff consume self-check**；`risk_signal` 仅作路由线索，必须基于代码事实重算定级。物理落点：活跃 change 的 `proposal.md` 中「Explore 交接消费」五条勾选（见 `brief-template.md`）；空摘要或未勾选不得放行规格闸门 / Quick 契约 go。
- 链式加载不可用时，停止并提示用户说「请使用 delivery-plan-tasks」或「请使用 delivery-execute-verify」或「请使用 delivery-explore」（与 `next_skill` 一致）。

# 交接摘要模板

## 必填子集（四阶段共用）

| 机读键 | 中文标签 | 说明 |
|---|---|---|
| `stage` | 当前阶段 | `delivery-plan-tasks` |
| `state_source` | 状态源 | 唯一 OpenSpec change 路径 |
| `capability_snapshot` | 能力快照 | `memory` / `openspec` / `superpowers` |
| `gate_status` | 闸门状态 | 就绪审查 + 实现闸门记录 |
| `evidence_mode` | 证据模式 | `full` \| `degraded`（若本阶段刷新事实时降级） |
| `next_skill` | 下一技能标识 | 通常 `delivery-execute-verify` |
| `required_inputs` | 下一阶段必需输入 | 实施放行记录、验证命令等 |
| `stop_condition` | 停止条件 | |

## 模板

```text
当前阶段：delivery-plan-tasks
状态源：
能力快照（capability_snapshot）：
  memory: ok | stale-index | down
  openspec: initialized | cli-only | unavailable
  superpowers: loaded | partial(<缺失项>) | missing
证据模式：full | degraded
闸门状态：
技术计划/任务清单：
追溯关系：
就绪审查结果：
验证方案：
风险/闸门：
并行所有权：
下一技能标识：delivery-execute-verify
下一阶段必需输入：
停止条件：
宿主续接话术（链式加载不可用时原样提示用户）：请使用 delivery-execute-verify
```

规则：

- 链式加载不可用时，输出本块后停止，并提示用户：「请使用 delivery-execute-verify」。
- 实现闸门未记录为已批准时，不得把 `next_skill` 写成可执行实施；应保持阻塞并写明 `stop_condition`。

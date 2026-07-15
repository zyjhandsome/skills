# 交接摘要模板

## 必填子集（四阶段共用）

下列字段每阶段交接都必须出现（explore 的闸门可写 `n/a (informal)`）：

| 机读键 | 中文标签 | 说明 |
|---|---|---|
| `stage` | 当前阶段 | 本文件为 `delivery-explore` |
| `state_source` | 状态源 | explore 恒为 `none（探索非正式）` |
| `capability_snapshot` | 能力快照 | `memory` / `openspec` / `superpowers` |
| `gate_status` | 闸门状态 | explore：`n/a (informal)` |
| `evidence_mode` | 证据模式 | `full` \| `degraded` |
| `next_skill` | 下一技能标识 | 仅 `delivery-frame-spec`（或 end） |
| `required_inputs` | 下一阶段必需输入 | 用户确认方向等 |
| `stop_condition` | 停止条件 | 仅建议 / 拒绝 framing |

## 模板

```text
当前阶段：delivery-explore
状态源：none（探索非正式）
证据模式：full | degraded
能力快照（capability_snapshot）：
  memory: ok | stale-index | down
  openspec: initialized | cli-only | unavailable
  superpowers: loaded | partial(<缺失项>) | missing
闸门状态：n/a (informal)
已选方向：
非目标：
代码锚点：
风险信号提示：none | standard-likely | high-likely
未知项：
下一技能标识：delivery-frame-spec
下一阶段必需输入：用户确认将该方向作为本次变更目标（或修订后的目标表述）
停止条件：用户仅需建议、或拒绝进入 framing
宿主续接话术（链式加载不可用时原样提示用户）：请使用 delivery-frame-spec
```

规则：

- 状态源恒为 `none`：探索不创建正式状态源。
- 能力快照的键与枚举值保持英文（机器可读）；explore 作为家族入口时首测生成，`delivery-frame-spec` 默认复用其中的正常值，仅重测异常项。
- 风险信号只是给 `delivery-frame-spec` 的路由线索：`none` → 倾向 Quick/Standard；`standard-likely` → 倾向 Standard（默认风险 Medium）；`high-likely` → 倾向 High。framing 阶段基于证据重新定路由与风险，explore 不得自批。
- 宿主不支持自动技能加载时，输出本交接块后停止，并**原样**提示用户：「请使用 delivery-frame-spec」。

# 实施交接模板

## 必填子集（四阶段共用）

| 机读键 | 中文标签 | 说明 |
|---|---|---|
| `stage` | 当前阶段 | `delivery-execute-verify` |
| `state_source` | 状态源 | 唯一 OpenSpec change 路径 |
| `capability_snapshot` | 能力快照 | `memory` / `openspec` / `superpowers` |
| `gate_status` | 闸门状态 | 实施 go / 新鲜验证 / 审查 |
| `evidence_mode` | 证据模式 | `full` \| `degraded` |
| `next_action` | 下一步动作 | 本阶段用 `next_action`（常为 OpenSpec archive）；等价于他阶段的 `next_skill` |
| `required_inputs` | 必需输入 | |
| `stop_condition` | 停止条件 | |

已验证收尾时另需：`overall_status: verified`、`archive: deferred_to_openspec`。

## 模板

```text
当前阶段：delivery-execute-verify
总体状态：进行中 / 被阻塞 / 已验证
状态源：
风险/闸门：
证据模式：full | degraded
能力快照（capability_snapshot）：
  memory: ok | stale-index | down
  openspec: initialized | cli-only | unavailable
  superpowers: loaded | partial(<缺失项>) | missing
闸门状态：

任务状态：
- <编号>：<状态 + 证据>

当前失败/阻塞项：
工件回流：
新鲜验证证据：
规格核对：
代码审查：
归档：
- 状态：deferred_to_openspec / not_applicable / blocked(<原因>)
- 说明：本技能不执行 sync/archive；请用 OpenSpec archive（/opsx-archive 或 openspec-archive-change）
资产回写：

下一步动作：
必需输入：
停止条件：
宿主续接话术（链式加载不可用且需归档时原样提示用户）：请使用 /opsx-archive
```

若新鲜验证已通过且任务已全部完成，总体状态应为「已验证」，归档应为 `deferred_to_openspec`（除非确无 OpenSpec change），并在下一步动作中指向 OpenSpec archive。不得在本技能内静默同步主规格或移动 change 目录。

链式加载不可用时，提示用户「请使用 /opsx-archive」或「请执行 openspec-archive-change」；commit/PR 另问，不得自动执行。

如果工作被阻塞，应如实报告未完成状态，不得使用乐观的完成措辞。

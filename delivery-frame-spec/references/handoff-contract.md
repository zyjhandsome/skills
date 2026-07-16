# Delivery handoff contract（四阶段共用）

四个 `delivery-*` Skill 在跨阶段交接或终态报告时读取本文件。handoff 是绑定到已观测状态的传输快照，不是第二状态源；OpenSpec change 仍是变更车道的唯一权威状态。Markdown 摘要和结构化 UI 都只是该对象的视图。

## 目录

1. 权威边界
2. `delivery-handoff/v1` 结构
3. 字段规则
4. 展示能力探测
5. 阶段载荷
6. 校验清单

## 1. 权威边界

- 使用 `schema_version: delivery-handoff/v1` 和 `type: delivery-handoff`。
- 使用 `family_version: delivery-family/1.1`；不支持该 major 版本时停止自动链式转换。
- 保持本契约的 snake_case 键和内部能力枚举；不要把 UI 的 camelCase 或兼容枚举写回本对象。
- **前向兼容扩展位：** 顶层如需承载非权威的附加信息，使用 `x_` 前缀键（如 `x_experiment_note`）。校验器忽略 `x_*` 顶层键，不因其失败；但 `x_*` 不得承载权威状态、批准或任务完成事实，那些只能落在既有权威字段和 OpenSpec change 中。`stage_payload` 本就允许阶段专属附加字段，无需 `x_` 前缀。
- 只写已有事实。未知值使用 `null`、空数组或明确的 `unknown`，不要用占位字符串伪装事实。
- `presentation` 只能投影同一对象和权威工件中已有的事实，不能创建状态、批准、任务完成或归档结果。
- 输出前确保 JSON 可完整解析；半截或无效 JSON 不构成交接。

## 2. `delivery-handoff/v1` 结构

```json
{
  "schema_version": "delivery-handoff/v1",
  "family_version": "delivery-family/1.1",
  "type": "delivery-handoff",
  "handoff_id": "<唯一 id>",
  "generated_at": "<RFC3339 timestamp>",
  "stage": "delivery-explore|delivery-frame-spec|delivery-plan-tasks|delivery-execute-verify",
  "source_revision": {
    "repo_head": null,
    "artifact_revision": null,
    "state_observed_at": "<RFC3339 timestamp>"
  },
  "state_source": {
    "kind": "none|openspec_change",
    "label": "<可读标签>",
    "anchor": null
  },
  "capability_snapshot": {
    "memory": "ok|stale-index|down",
    "openspec": "initialized|cli-only|unavailable",
    "superpowers": "loaded|partial(<missing>)|missing"
  },
  "capability_bindings": {
    "openspec": {},
    "memory": {},
    "superpowers": {},
    "subagents": {}
  },
  "presentation_capability": {
    "mode": "delivery-ui/v1|legacy-v0|markdown",
    "source": "host-declared|detected|unknown"
  },
  "gate_status": {
    "status": "n/a|pending|pass|warn|block",
    "summary": "<可见结论>",
    "evidence": [],
    "approved_by": null,
    "approved_at": null,
    "binds_to_revision": null,
    "accepted_warning_ids": []
  },
  "evidence_mode": "full|degraded",
  "next_skill": null,
  "next_action": null,
  "required_inputs": [],
  "stop_condition": "<停止或阻塞条件>",
  "stage_payload": {},
  "presentation": {
    "schema": "delivery-presentation/v1",
    "from_task": "<当前任务>",
    "to_task": "<下一任务或结束>",
    "summary": "<一句话结论>",
    "evidence": [],
    "continue_prompt": "<继续提示或 end>"
  }
}
```

## 3. 字段规则

- `state_source.kind`：Explore 恒为 `none`；正式 OpenSpec change 使用 `openspec_change` 并填写真实 `anchor`。
- `source_revision`：记录生成 handoff 时观测到的 repo HEAD、权威工件修订和时间。`artifact_revision` 优先使用 OpenSpec 暴露的原生 revision；没有原生 revision 时，对当前阶段所有权威工件的“规范化相对路径 + 原始字节”按路径排序后计算 SHA-256。不得用时间戳或聊天轮次冒充修订。无 Git 或无正式工件时对应字段可为 `null`，但 `state_observed_at` 必填。
- `capability_bindings`：形状与依赖等级见 `family-contract.md`；记录实际解析结果，不复制外部能力说明。
- `gate_status.status`：Explore 可用 `n/a`；未放行用 `pending` 或 `block`；存在已公开且允许继续的警告用 `warn`；完全通过用 `pass`。
- `gate_status.binds_to_revision`：任何批准必须绑定当前 `artifact_revision`；没有正式批准时保持 `null`。`accepted_warning_ids` 只列用户在可见 gate 摘要中明确接受的 warning id。
- `next_skill` / `next_action`：最多一个非 `null`（互斥）。前三阶段成功转换只用 `next_skill` 且 `next_action` 必须为 `null`；Execute 只用 `next_action` 且 `next_skill` 必须为 `null`。结束且无下一动作时两者都为 `null`。**禁止**把自然语言「下一步说明」塞进另一个字段。
- `gate_status` 可选扩展字段 `approval_mode`: `live` | `harness`（测试剧本代答）。缺省视为 `live`。校验器不因缺少该字段失败；harness 模式必须在 `summary` 中标明。
- `required_inputs` 和所有 `evidence` 字段必须是数组；没有内容时使用 `[]`。
- `stop_condition` 必须写当前真实停止条件；已允许转换时可写空字符串。
- `stage_payload` 只放阶段专属字段，避免污染四阶段公共契约。
- `presentation_capability` 只描述渲染通道，不代表该通道已成功显示，也不改变交接有效性。
- 消费端先比较当前 repo/artifact revision；不一致时将 handoff 视为 stale，恢复 OpenSpec 状态并重新运行受影响 gate，不能继续沿用旧批准。

## 4. 展示能力探测

按以下优先级只判定一次，并在能力事实变化时更新：

1. 宿主明确声明支持 `delivery-ui/v1`：写 `mode: delivery-ui/v1`、`source: host-declared`。
2. 当前会话已有成功使用 `delivery-ui/v1` 的可靠宿主事实：写 `mode: delivery-ui/v1`、`source: detected`。
3. 宿主仅声明或可靠识别旧 `DeliveryHandoffBlock` / 旧 `delivery-*` schema：写 `mode: legacy-v0`。
4. 无法确认时使用 `mode: markdown`、`source: unknown`；不要靠发送试探性无效块探测。

`mode` 决定是否读取 `structured-presentation-adapter.md` 以及使用哪个投影。无论何种模式，本 JSON 都是唯一交接语义源。

## 5. 阶段载荷

| 阶段 | `stage_payload` 必需内容 |
|---|---|
| Explore | `direction_alignment`、`chosen_direction`、`non_goals`、`code_anchors`、`risk_signal`、`unknowns` |
| Frame | `route`、`risk`、`confirmed_artifacts`、`forbidden_scope`、`open_questions` |
| Plan | `plan_tasks`、`plan_decisions`、`traceability`、`readiness_result`、`validation_plan`、`risk_gates`、`parallel_ownership` |
| Execute | `overall_status`、`task_status`、`current_failures_or_blocks`、`artifact_backflow`、`alignment_backflow`、`fresh_verification_evidence`、`spec_coherence`、`code_review`、`archive`、`asset_writeback` |

阶段专属模板定义具体形状。不得把 `route/risk`、`plan/tasks` 这类含斜线的旧展示标签直接作为新 JSON 键。

## 6. 校验清单

输出前检查：

1. JSON 能被严格解析，且只有一个顶层对象。
2. 公共必填键、Family/schema 版本和 RFC3339 时间全部存在且合法。
3. `next_skill` 与 `next_action` 未同时非空。
4. 阶段门禁允许所声明的下一步。
5. gate 批准绑定当前 artifact revision，接受的 warning id 均出现在可见摘要/证据中。
6. `stage_payload` 满足本阶段模板。
7. `presentation` 没有增加权威对象中不存在的事实。
8. `presentation_capability.mode` 与实际投影一致；未知宿主安全回退 Markdown。

当本地 Python 可用时，把最终 JSON 通过 stdin 或文件传给 `../scripts/validate_handoff.py`；退出码非 0 时不得交接。脚本不可用时才逐项执行上述人工检查，并在 handoff evidence 中记录降级。

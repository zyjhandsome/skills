# Delivery handoff contract（四阶段共用）

四个 `delivery-*` Skill 在跨阶段交接或终态报告时读取本文件。handoff 是绑定到已观测状态的传输快照，不是第二状态源；OpenSpec change 仍是变更车道的唯一权威状态。Markdown 摘要和结构化 UI 都只是该对象的视图。

## 目录

1. 权威边界
2. `delivery-handoff/v1` 结构
3. 字段规则
4. 持久化槽位
5. 展示能力探测
6. 阶段载荷
7. 回流再入消费自检
8. 校验清单

## 1. 权威边界

- 使用 `schema_version: delivery-handoff/v1` 和 `type: delivery-handoff`。
- `family_version` 以 `family-contract.md` 为权威（当前 `delivery-family/1.2`）；major 不受支持时停止自动链式转换。
- 保持本契约的 snake_case 键和内部能力枚举；不要把 UI 的 camelCase 或兼容枚举写回本对象。
- **前向兼容扩展位：** 顶层附加信息使用 `x_` 前缀键；校验器忽略 `x_*`。`x_*` 不得承载权威状态、批准或任务完成事实。`stage_payload` 允许阶段专属附加字段，无需前缀。
- 只写已有事实。未知值使用 `null`、空数组或明确的 `unknown`。
- `presentation` 只能投影同一对象和权威工件中已有的事实。
- 输出前确保 JSON 可完整解析；半截或无效 JSON 不构成交接。

## 2. `delivery-handoff/v1` 结构

```json
{
  "schema_version": "delivery-handoff/v1",
  "family_version": "delivery-family/1.2",
  "type": "delivery-handoff",
  "handoff_id": "<唯一 id>",
  "previous_handoff_id": null,
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
    "memory": "ok",
    "openspec": "initialized",
    "superpowers": "loaded"
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
  "evidence_mode": "full",
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

- `handoff_id`：本次交付内唯一（建议 `<change-id>-<stage>-<序号>`）。`previous_handoff_id`（可选，可 `null`）：指向本次交付链中上一个 handoff，含回流；家族首个 handoff 为 `null`。
- `state_source.kind`：Explore 恒为 `none`；正式 OpenSpec change 使用 `openspec_change` 并填写真实 `anchor`。
- `source_revision`：记录生成时观测到的 repo HEAD、权威工件修订和时间。`artifact_revision` 优先使用 OpenSpec 原生 revision；否则运行 `scripts/hash_change_artifacts.py`（按路径排序的规范化相对路径 + 原始字节的 SHA-256）。不得用时间戳或聊天轮次冒充修订。
- `capability_snapshot`：硬前提 profile 下预期恒为标称值（见 `family-contract.md`）。出现非标称值时不得携带阶段转换。
- `capability_bindings`：形状见 `family-contract.md`；记录实际解析结果。
- `gate_status.status`：Explore 可用 `n/a`；未放行用 `pending`/`block`；有已公开且允许继续的警告用 `warn`；完全通过用 `pass`。
- `gate_status.binds_to_revision`：任何批准必须绑定当前 `artifact_revision`；无正式批准时保持 `null`。`accepted_warning_ids` 只列用户在可见 gate 摘要中明确接受的 warning id。
- 可选扩展 `gate_status.approval_mode`: `live` | `harness`（测试剧本代答，须在 `summary` 标明）；缺省视为 `live`。
- `next_skill` / `next_action`：**最多一个非 `null`（互斥）**。前三阶段成功转换只用 `next_skill`；Execute 只用 `next_action`；结束且无下一动作时两者皆 `null`。禁止把自然语言「下一步说明」塞进另一字段。
- `evidence_mode` 恒为 `full`（无降级取证模式）。
- `required_inputs` 和所有 `evidence` 字段必须是数组；空时用 `[]`。
- `stop_condition` 写当前真实停止条件；已允许转换时可为空字符串。
- `stage_payload` 只放阶段专属字段。
- 消费端先比较当前 repo/artifact revision；不一致时 handoff 视为 stale，从 OpenSpec 恢复状态并重跑受影响 gate，不得沿用旧批准。

## 4. 持久化槽位

handoff 只存在于聊天时无法跨会话续跑。规则：

- **每次 emit 并通过校验后，把同一 JSON 落盘**到活跃 change 下的受管附件位：`openspec/changes/<id>/handoff.json`（覆盖写，只保留最新一份；历史链靠 `previous_handoff_id` 与 git 历史追溯）。
- Explore 无 change 时不落盘（其 handoff 由 frame 在同会话消费；跨会话重启 explore 成本可接受）。
- 落盘文件是**快照缓存**，不是第二状态源：消费端仍须先做 revision 比对；不一致以 OpenSpec 工件为准并重跑受影响 gate。
- 新会话进入 plan/execute 且聊天中无 handoff 时：读 `handoff.json` → 校验 → revision 比对 → 通过则继续，否则按 stale 恢复流程。

## 5. 展示能力探测

按以下优先级只判定一次，能力事实变化时更新：

1. 宿主明确声明支持 `delivery-ui/v1` → `mode: delivery-ui/v1`、`source: host-declared`。
2. 当前会话已有成功使用 `delivery-ui/v1` 的可靠事实 → `source: detected`。
3. 仅识别旧 `DeliveryHandoffBlock` / 旧 schema → `mode: legacy-v0`。
4. 无法确认 → `mode: markdown`、`source: unknown`；不发试探性无效块探测。

`mode` 决定是否读取 `structured-presentation-adapter.md`。无论何种模式，本 JSON 都是唯一交接语义源。

## 6. 阶段载荷

| 阶段 | `stage_payload` 必需内容 |
|---|---|
| Explore | `direction_alignment`、`chosen_direction`、`non_goals`、`code_anchors`、`risk_signal`、`unknowns` |
| Frame | `route`、`risk`、`confirmed_artifacts`、`forbidden_scope`、`open_questions` |
| Plan | `plan_tasks`、`plan_decisions`、`traceability`、`readiness_result`、`validation_plan`、`risk_gates`、`parallel_ownership` |
| Execute | `overall_status`、`task_status`、`current_failures_or_blocks`、`artifact_backflow`、`alignment_backflow`、`fresh_verification_evidence`、`spec_coherence`、`code_review`、`archive`、`asset_writeback` |

具体形状见共享 `handoff-template.md`。不得把含斜线的旧展示标签（`route/risk` 等）直接作为 JSON 键。

## 7. 回流再入消费自检

Execute 带 `alignment_backflow` 回流到 frame/plan 时，再入阶段在继续工作前必须完成并在其工件中记录三项检查（对应 explore→frame 的消费自检，但更轻）：

- [ ] `invalidated_artifacts` 中列出的工件/批准已全部标记 stale（旧批准不再被引用）；
- [ ] `decision_needed` 已进入本阶段权威决策台账（frame：开放问题清单；plan：技术决策台账）；
- [ ] `resume_point` 已确认仍有效（对照当前 tasks/验证状态）。

三项未全部完成前，不得重开本阶段闸门。plan→execute 前向交接不需要独立消费自检：Execute Preflight 的修订绑定检查已覆盖。

## 8. 校验清单

输出前检查：

1. JSON 严格可解析，只有一个顶层对象。
2. 公共必填键、Family/schema 版本和 RFC3339 时间全部合法。
3. `next_skill` 与 `next_action` 未同时非空。
4. 阶段门禁允许所声明的下一步。
5. gate 批准绑定当前 artifact revision；接受的 warning id 均出现在可见摘要/证据中。
6. `stage_payload` 满足本阶段模板。
7. `presentation` 没有增加权威对象中不存在的事实。
8. `presentation_capability.mode` 与实际投影一致；未知宿主回退 Markdown。

把最终 JSON 通过 stdin 或文件传给 `../scripts/validate_handoff.py`；退出码非 0 时不得交接。校验通过后按第 4 节落盘。

脚本默认按**硬前提 profile** 校验（`--profile hard`）：`evidence_mode` 必须为 `full`；`capability_snapshot` 非标称值时不得携带 `next_skill`/`next_action`（只能报告故障 + `stop_condition`）。校验 1.2 之前的历史 handoff 时用 `--profile legacy`。

**骨架生成：** 不要手写整个 JSON。`../scripts/delivery_scaffold.py new-handoff <stage> --change-dir <change> [--previous <id>]` 生成已通过校验的非转换骨架（标称快照、时间戳、`artifact_revision`、阶段载荷骨架），Agent 只填业务字段与闸门后再校验。

**回归夹具：** `../tests/fixtures/` 中的 `pass-*`/`neg-*` 夹具锁定本契约的关键拒绝行为（warn 未回显、verified 未 defer 归档、双转换目标、非标称快照携带转换、degraded 取证、自审 verified 等）。修改校验器或契约后必须跑 `../tests/run_fixture_tests.py`；某个 `neg-*` 开始通过即表示护栏被削弱。

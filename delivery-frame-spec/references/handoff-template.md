# 交接摘要模板（四阶段共用）

输出前读取 `handoff-contract.md`。交接必须是一个可严格解析的 `delivery-handoff/v1` JSON 对象；只填写已经存在的事实。本文件是四阶段唯一的 handoff 模板：公共骨架一份 + 各阶段 `stage_payload` / `presentation` 差异块。

## 公共骨架

```delivery-handoff
{
  "schema_version": "delivery-handoff/v1",
  "family_version": "delivery-family/1.2",
  "type": "delivery-handoff",
  "handoff_id": "<change-id>-<stage>-<序号>",
  "previous_handoff_id": null,
  "generated_at": "<RFC3339 timestamp>",
  "stage": "<本阶段>",
  "source_revision": {
    "repo_head": null,
    "artifact_revision": null,
    "state_observed_at": "<RFC3339 timestamp>"
  },
  "state_source": {
    "kind": "<none|openspec_change>",
    "label": "<none|change #id>",
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
    "mode": "<delivery-ui/v1|legacy-v0|markdown>",
    "source": "<host-declared|detected|unknown>"
  },
  "gate_status": {
    "status": "<n/a|pending|pass|warn|block>",
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
  "stop_condition": "",
  "stage_payload": { "（见下方各阶段差异块）": null },
  "presentation": {
    "schema": "delivery-presentation/v1",
    "from_task": "<当前任务>",
    "to_task": "<下一任务或结束>",
    "summary": "<一句话结论>",
    "evidence": [],
    "continue_prompt": "<请使用下一技能；结束时写 end>"
  }
}
```

公共规则：

- **互斥（强制）**：`next_skill` 与 `next_action` 最多一个非 `null`。Explore/Frame/Plan 成功转换只填 `next_skill`；Execute 只填 `next_action`；结束/阻塞时两者皆 `null`。
- `artifact_revision`：优先 OpenSpec 原生 revision；否则 `python <frame-spec>/scripts/hash_change_artifacts.py <change-dir>`。
- 批准必须绑定当前 `artifact_revision`（`binds_to_revision`）；`accepted_warning_ids` 只列可见摘要中用户明确接受的项。
- 输出前：`python <frame-spec>/scripts/validate_handoff.py <handoff.json>`（或 stdin）。失败不得交接。通过后按 `handoff-contract.md` 第 4 节落盘 `handoff.json`（Explore 除外）。
- `presentation` 只投影权威对象已有事实；投影方式按 `presentation_capability.mode`（结构化规则见 `structured-presentation-adapter.md`）。
- 链式加载不可用时，输出交接后停止，并原样提示「请使用 <next_skill>」（Execute：给出已解析的 `archive_change` 实际入口；未解析到时报告缺失，不猜 alias）。

## Explore 差异块

```json
"stage": "delivery-explore",
"state_source": { "kind": "none", "label": "none（探索非正式）", "anchor": null },
"gate_status": { "status": "n/a", "summary": "探索非正式，无规格闸门", "...": "..." },
"stage_payload": {
  "direction_alignment": "<selected|needs_choice>",
  "chosen_direction": "<已选方向及目标价值>",
  "non_goals": [],
  "code_anchors": [],
  "risk_signal": "<none|standard-likely|high-likely>",
  "unknowns": []
},
"presentation": { "from_task": "探索·方向对齐", "to_task": "定框·路由与需求边界", "continue_prompt": "请使用 delivery-frame-spec", "...": "..." }
```

- `direction_alignment: selected` 时才可 `next_skill: delivery-frame-spec`；`needs_choice` / 仅建议结束时两者皆 `null` 并写真实 `stop_condition`。
- 状态源恒为 `none`：**本 handoff 输出之前禁止调用 OpenSpec `create_change` / 写入 `openspec/changes/`**。
- `risk_signal` 仅是 Frame 的路由线索；Frame 必须基于新鲜证据重新定级。
- Explore handoff 不落盘（无 change）。

## Frame 差异块

```json
"stage": "delivery-frame-spec",
"stage_payload": {
  "route": "<Read-only|Quick|Standard|High|Debug>",
  "risk": "<none|low|medium|high>",
  "confirmed_artifacts": [],
  "forbidden_scope": [],
  "open_questions": []
},
"presentation": { "from_task": "<定框·规格闸门通过|定框·轻量契约已批准|只读结束>", "to_task": "<技术设计与任务拆解|按轻量任务实施|结束>", "...": "..." }
```

- 规格闸门通过 → `next_skill: delivery-plan-tasks`；Quick/Debug-Low 契约 go → `next_skill: delivery-execute-verify`；返回探索 → `next_skill: delivery-explore`；只读/阻塞/结束 → 皆 `null`。
- **本阶段才允许** OpenSpec `create_change`（或恢复已有 change）。若上游 explore 违规已建 change，在「状态源与工件位置」记录该违规并继续以该 change 为唯一状态源。
- 若来自 Explore，必须先完成活跃 `proposal.md` 中的「Explore 交接消费」自检。

## Plan 差异块

```json
"stage": "delivery-plan-tasks",
"state_source": { "kind": "openspec_change", "label": "change #<id>", "anchor": "openspec/changes/<id>" },
"stage_payload": {
  "plan_tasks": [],
  "plan_decisions": {
    "agent_decided": [],
    "user_decided": [],
    "returned_to_frame": [],
    "remaining_blockers": []
  },
  "traceability": [],
  "readiness_result": { "blockers": [], "warnings": [], "suggestions": [] },
  "validation_plan": [],
  "risk_gates": [],
  "parallel_ownership": []
},
"presentation": { "from_task": "计划·就绪审查完成", "to_task": "实施·按 tasks.md 执行（任务勾选属 Execute 阶段）", "continue_prompt": "请使用 delivery-execute-verify", "...": "..." }
```

- 实现闸门批准且绑定当前 `artifact_revision` 后，才 `next_skill: delivery-execute-verify`；否则保持 `null` 并填真实 `stop_condition`。
- 状态文案：Plan 结束时 tasks **全部未勾选属预期**；`summary` 说「计划完成，任务待实施」，不要把 0/N 已勾选当缺陷呈现。
- 实现 go 只覆盖 `gate_status.summary` 明确展示的 warnings。

## Execute 差异块

```json
"stage": "delivery-execute-verify",
"state_source": { "kind": "openspec_change", "label": "change #<id>", "anchor": "openspec/changes/<id>" },
"next_skill": null,
"next_action": "<resolved archive_change binding, e.g. openspec archive <id>>",
"stage_payload": {
  "overall_status": "<verified|in_progress|blocked>",
  "task_status": [],
  "current_failures_or_blocks": [],
  "artifact_backflow": "none",
  "alignment_backflow": null,
  "fresh_verification_evidence": [],
  "spec_coherence": "<pass|warn|block>",
  "code_review": {
    "status": "<pass|warn|block>",
    "mode": "independent",
    "independent_review": "<required_pass|required_warn_accepted>",
    "reviewer": "<subagent-id|human>",
    "findings": []
  },
  "archive": { "status": "deferred_to_openspec", "reason": "execute-verify must not sync/archive" },
  "asset_writeback": []
},
"presentation": { "from_task": "实施·验证", "to_task": "OpenSpec 归档", "continue_prompt": "<已解析的 archive_change 操作>", "...": "..." }
```

- `overall_status: verified` 时：`archive.status` 只能是 `deferred_to_openspec` 或 `not_applicable`；`next_action` 为已解析的 `archive_change` 入口；不得写 `closed`、预计 archive 路径或已归档。
- **Medium/High verified**：`code_review.mode: independent`（SubAgent 或人），`independent_review` 为 `required_pass` 或 `required_warn_accepted`（警告须出现在 `accepted_warning_ids`）。SubAgent 为硬前提，独立审查始终可用；`self_fresh_context` 不是关闭选项。
- 回流到 Frame/Plan 时必须把完整 `alignment_backflow` 对象写入 `stage_payload`（发现、证据、影响范围、失效工件、所需决定、推荐处理、恢复点），且 `next_skill`/`next_action` 皆 `null`（回流由再入阶段自行开始）。
- 阻塞时如实用 `blocked`，填当前失败、必需输入和停止条件。

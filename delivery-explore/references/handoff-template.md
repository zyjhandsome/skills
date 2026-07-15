# 交接摘要模板

输出前读取 `../../delivery-frame-spec/references/handoff-contract.md`。交接必须是一个可严格解析的 `delivery-handoff/v1` JSON 对象；下列模板只填写已经存在的事实。

```delivery-handoff
{
  "schema_version": "delivery-handoff/v1",
  "family_version": "delivery-family/1.1",
  "type": "delivery-handoff",
  "handoff_id": "<unique-id>",
  "generated_at": "<RFC3339 timestamp>",
  "stage": "delivery-explore",
  "source_revision": {
    "repo_head": null,
    "artifact_revision": null,
    "state_observed_at": "<RFC3339 timestamp>"
  },
  "state_source": {
    "kind": "none",
    "label": "none（探索非正式）",
    "anchor": null
  },
  "capability_snapshot": {
    "memory": "<ok|stale-index|down>",
    "openspec": "<initialized|cli-only|unavailable>",
    "superpowers": "<loaded|partial(<missing>)|missing>"
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
    "status": "n/a",
    "summary": "探索非正式，无规格闸门",
    "evidence": [],
    "approved_by": null,
    "approved_at": null,
    "binds_to_revision": null,
    "accepted_warning_ids": []
  },
  "evidence_mode": "<full|degraded>",
  "next_skill": "delivery-frame-spec",
  "next_action": null,
  "required_inputs": [
    "用户确认将该方向作为本次变更目标，或提供修订后的目标表述"
  ],
  "stop_condition": "",
  "stage_payload": {
    "direction_alignment": "selected",
    "chosen_direction": "<已选方向及目标价值>",
    "non_goals": [],
    "code_anchors": [],
    "risk_signal": "<none|standard-likely|high-likely>",
    "unknowns": []
  },
  "presentation": {
    "schema": "delivery-presentation/v1",
    "from_task": "探索·方向对齐",
    "to_task": "定框·路由与需求边界",
    "summary": "<方向状态 + 已选方向>",
    "evidence": [],
    "continue_prompt": "请使用 delivery-frame-spec"
  }
}
```

**互斥（强制）：** `next_skill` 与 `next_action` **最多一个非 null**。Explore 成功交接只填 `next_skill`，**必须** `next_action: null`。结束/未选方向时两者皆 `null`。切勿把「下一步说明」写进 `next_action`。

成功路径填写示例（`direction_alignment: selected`）：

```json
"next_skill": "delivery-frame-spec",
"next_action": null
```

未选方向 / 仅建议结束：

```json
"next_skill": null,
"next_action": null
```

规则：

- 状态源恒为 `none`：探索不创建正式状态源。**在本 handoff 输出之前，禁止调用 OpenSpec `create_change` / 写入 `openspec/changes/`。**
- 只有会改变方向选择的分叉均已决定时才写 `direction_alignment: selected` 并把 `next_skill` 设为 `delivery-frame-spec`（同时 `next_action: null`）。`needs_choice` 或结束状态保持 `next_skill: null`，并填写真实 `stop_condition` / `presentation`。
- 风险信号只是 Frame 的路由线索；Frame 必须基于新鲜证据重新定级。
- 根据 `presentation_capability.mode` 选择 `delivery-ui/v1`、`legacy-v0` 或 Markdown；投影规则见 `../../delivery-frame-spec/references/structured-presentation-adapter.md`。
- 输出前用 `python ../../delivery-frame-spec/scripts/validate_handoff.py <handoff.json>` 校验；失败不得交接。
- 链式加载不可用时，输出交接后停止，并原样提示用户：「请使用 delivery-frame-spec」。

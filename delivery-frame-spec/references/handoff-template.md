# 交接摘要模板

输出前读取 `handoff-contract.md`。交接必须是一个可严格解析的 `delivery-handoff/v1` JSON 对象；下列模板只填写已经存在的事实。

```delivery-handoff
{
  "schema_version": "delivery-handoff/v1",
  "family_version": "delivery-family/1.1",
  "type": "delivery-handoff",
  "handoff_id": "<unique-id>",
  "generated_at": "<RFC3339 timestamp>",
  "stage": "delivery-frame-spec",
  "source_revision": {
    "repo_head": null,
    "artifact_revision": null,
    "state_observed_at": "<RFC3339 timestamp>"
  },
  "state_source": {
    "kind": "<none|openspec_change>",
    "label": "<none（只读/返回探索）|change #id>",
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
    "status": "<pending|pass|warn|block>",
    "summary": "<规格闸门、轻量契约 go、返回探索或只读结论>",
    "evidence": [],
    "approved_by": null,
    "approved_at": null,
    "binds_to_revision": null,
    "accepted_warning_ids": []
  },
  "evidence_mode": "<full|degraded>",
  "next_skill": null,
  "next_action": null,
  "required_inputs": [],
  "stop_condition": "",
  "stage_payload": {
    "route": "<Read-only|Quick|Standard|High|Debug>",
    "risk": "<none|low|medium|high>",
    "confirmed_artifacts": [],
    "forbidden_scope": [],
    "open_questions": []
  },
  "presentation": {
    "schema": "delivery-presentation/v1",
    "from_task": "<定框·规格闸门通过|定框·轻量契约已批准|定框·需返回探索|只读结束>",
    "to_task": "<技术设计与任务拆解|按轻量任务实施|探索方向|结束>",
    "summary": "<车道/风险 + 已批准、阻塞或只读结论>",
    "evidence": [],
    "continue_prompt": "<请使用下一技能；结束时写 end>"
  }
}
```

**互斥（强制）：** `next_skill` 与 `next_action` **最多一个非 null**。Frame 成功交接只填 `next_skill`，**必须** `next_action: null`。结束/阻塞时两者皆 `null`。

成功路径示例（规格闸门通过 → plan）：

```json
"next_skill": "delivery-plan-tasks",
"next_action": null
```

Quick / Debug-Low 契约 go → execute：

```json
"next_skill": "delivery-execute-verify",
"next_action": null
```

规则：

- Read-only、阻塞或结束时允许 `state_source.kind: none`、`next_skill: null`。返回 Explore 但尚未创建 change 时也使用 `none`；已有 change 时保留真实 OpenSpec anchor。
- **本阶段才允许** OpenSpec `create_change`（或恢复已有 change）。若上游 explore 违规已建 change，在 **State Source** 记录该违规并继续以该 change 为唯一状态源，勿再建第二个。
- `next_skill` 只填写当前闸门允许的下一技能；成功转换时替换模板中的 `null`，并保持 `next_action: null`。
- 下游默认信任能力快照中的正常值，只重测异常项和即将依赖且可能变化的能力。
- 若来自 Explore，必须先完成活跃 `proposal.md` 中的「Explore 交接消费」自检；`risk_signal` 仅作线索。
- `presentation` 只投影车道、风险、闸门、状态源与证据，不得产生实施授权。
- 根据 `presentation_capability.mode` 选择 `delivery-ui/v1`、`legacy-v0` 或 Markdown；投影规则见 `structured-presentation-adapter.md`。
- 输出前：`python scripts/validate_handoff.py <handoff.json>`（相对本 skill 目录）。失败不得交接。
- 链式加载不可用时，停止并原样提示「请使用 <next_skill>」。

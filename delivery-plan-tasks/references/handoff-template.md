# 交接摘要模板

输出前读取 `../../delivery-frame-spec/references/handoff-contract.md`。交接必须是一个可严格解析的 `delivery-handoff/v1` JSON 对象；下列模板只填写已经存在的事实。

```delivery-handoff
{
  "schema_version": "delivery-handoff/v1",
  "family_version": "delivery-family/1.1",
  "type": "delivery-handoff",
  "handoff_id": "<unique-id>",
  "generated_at": "<RFC3339 timestamp>",
  "stage": "delivery-plan-tasks",
  "source_revision": {
    "repo_head": null,
    "artifact_revision": "<artifact revision>",
    "state_observed_at": "<RFC3339 timestamp>"
  },
  "state_source": {
    "kind": "openspec_change",
    "label": "change #<id>",
    "anchor": "openspec/changes/<id>"
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
    "summary": "<就绪审查 + 实现闸门结论及已公开警告>",
    "evidence": [],
    "approved_by": null,
    "approved_at": null,
    "binds_to_revision": null,
    "accepted_warning_ids": []
  },
  "evidence_mode": "<full|degraded>",
  "next_skill": null,
  "next_action": null,
  "required_inputs": [
    "已记录的实施放行",
    "权威 tasks.md",
    "任务级验证命令"
  ],
  "stop_condition": "",
  "stage_payload": {
    "plan_tasks": [],
    "plan_decisions": {
      "agent_decided": [],
      "user_decided": [],
      "returned_to_frame": [],
      "remaining_blockers": []
    },
    "traceability": [],
    "readiness_result": {
      "blockers": [],
      "warnings": [],
      "suggestions": []
    },
    "validation_plan": [],
    "risk_gates": [],
    "parallel_ownership": []
  },
  "presentation": {
    "schema": "delivery-presentation/v1",
    "from_task": "计划·就绪审查完成",
    "to_task": "实施·按 tasks.md 执行",
    "summary": "<已批准的计划/任务 + 就绪与闸门结果>",
    "evidence": [],
    "continue_prompt": "请使用 delivery-execute-verify"
  }
}
```

**互斥（强制）：** `next_skill` 与 `next_action` **最多一个非 null**。Plan 成功交接只填 `next_skill: "delivery-execute-verify"`，**必须** `next_action: null`。

规则：

- 实现闸门批准且绑定当前 `artifact_revision` 后，才把 `next_skill` 设为 `delivery-execute-verify`；否则保持 `null` 并填写真实 `stop_condition`。
- 实现 go 只覆盖 `gate_status.summary` 明确展示的 warnings；隐藏或新发现的 warning 仍未解决。
- `presentation`、任务视图与审查视图只投影 `design.md`、`tasks.md`、readiness 和闸门记录。
- 根据 `presentation_capability.mode` 选择 `delivery-ui/v1`、`legacy-v0` 或 Markdown；投影规则见 `../../delivery-frame-spec/references/structured-presentation-adapter.md`。
- 输出前：`python ../../delivery-frame-spec/scripts/validate_handoff.py <handoff.json>`。失败不得交接。
- `artifact_revision` 优先用 OpenSpec 原生 revision；否则运行 `python ../../delivery-frame-spec/scripts/hash_change_artifacts.py <change-dir>`。
- 链式加载不可用时，输出交接后停止，并原样提示用户：「请使用 delivery-execute-verify」。

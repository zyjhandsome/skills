# 实施交接模板

输出前读取 `../../delivery-frame-spec/references/handoff-contract.md`。交接必须是一个可严格解析的 `delivery-handoff/v1` JSON 对象；下列模板只填写已经存在的事实。

```delivery-handoff
{
  "schema_version": "delivery-handoff/v1",
  "family_version": "delivery-family/1.1",
  "type": "delivery-handoff",
  "handoff_id": "<unique-id>",
  "generated_at": "<RFC3339 timestamp>",
  "stage": "delivery-execute-verify",
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
    "summary": "<实施 go、新鲜验证与代码审查结论>",
    "evidence": [],
    "approved_by": null,
    "approved_at": null,
    "binds_to_revision": null,
    "accepted_warning_ids": []
  },
  "evidence_mode": "<full|degraded>",
  "next_skill": null,
  "next_action": "<resolved archive_change binding, e.g. openspec archive <id>>",
  "required_inputs": [],
  "stop_condition": "",
  "stage_payload": {
    "overall_status": "verified",
    "task_status": [],
    "current_failures_or_blocks": [],
    "artifact_backflow": "none",
    "alignment_backflow": null,
    "fresh_verification_evidence": [],
    "spec_coherence": "<pass|warn|block>",
    "code_review": {
      "status": "<pass|warn|block>",
      "mode": "<independent|self_fresh_context>",
      "independent_review": "<required_pass|required_warn_accepted|unavailable_blocked|low_accepted>",
      "reviewer": "<subagent-id|agent|null>",
      "findings": []
    },
    "archive": {
      "status": "deferred_to_openspec",
      "reason": "execute-verify must not sync/archive"
    },
    "asset_writeback": []
  },
  "presentation": {
    "schema": "delivery-presentation/v1",
    "from_task": "实施·验证",
    "to_task": "OpenSpec 归档",
    "summary": "<总体状态 + verified 结论>",
    "evidence": [],
    "continue_prompt": "<已解析的 archive_change 操作>"
  }
}
```

**互斥（强制）：** Execute **只用** `next_action`；`next_skill` **必须**为 `null`。Verified 时 `next_action` 为已解析的 `archive_change` 入口。

```json
"next_skill": null,
"next_action": "openspec archive <change-id>"
```

规则：

- `overall_status: verified` 时，`archive.status` 只能是 `deferred_to_openspec` 或 `not_applicable`；本技能不得写 `closed`、预计 archive 路径或已归档。
- **Medium/High verified 要求**：`code_review.mode` 必须为 `independent`（真实独立审查者/SubAgent），且 `independent_review` 为 `required_pass` 或 `required_warn_accepted`（警告须出现在 `gate_status.accepted_warning_ids`）。`self_fresh_context` **不得**关闭 Medium/High。Low 仅在显式用户接受残留风险时可用 `low_accepted`。
- 回流到 Frame/Plan 时必须把完整 `alignment_backflow` 对象写入 `stage_payload`，包含发现、证据、影响范围、失效工件、所需决定、推荐处理和恢复点。
- 工作被阻塞时如实使用 `blocked`，填写当前失败、必需输入和停止条件。
- 根据 `presentation_capability.mode` 选择 `delivery-ui/v1`、`legacy-v0` 或 Markdown；投影规则见 `../../delivery-frame-spec/references/structured-presentation-adapter.md`。
- 输出前：`python ../../delivery-frame-spec/scripts/validate_handoff.py <handoff.json>`。失败不得声称 verified。
- `artifact_revision`：优先 OpenSpec 原生；否则 `python ../../delivery-frame-spec/scripts/hash_change_artifacts.py <change-dir>`。
- 链式加载不可用且已 verified 时，提示用户使用 `capability_bindings.openspec.operations.archive_change` 中的实际入口；未解析到时报告缺失，不猜测 alias。commit/PR 另问。

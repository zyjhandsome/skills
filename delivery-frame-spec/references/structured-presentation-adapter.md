# Structured presentation adapter（delivery 家族共用）

仅在宿主支持结构化交付渲染、需要生成 `delivery-*` fenced block，或需要调试展示字段时读取本文件。四阶段的权威状态仍来自 OpenSpec 工件、闸门记录和新鲜验证；本协议只生成只读视图。

## 目录

1. 权威边界
2. 展示能力协商
3. 版本与通用规则
4. 能力状态映射
5. `legacy-v0` 兼容投影
6. 五类展示块
7. 阶段发射门禁
8. Markdown fallback

## 1. 权威边界

- 保持内部字段及枚举不变；展示适配不得反向改写 `capability_snapshot`、闸门、任务或归档状态。
- 只投影已经存在于当前 handoff 或权威工件中的事实；缺失字段应隐藏或标为 unknown，不得猜测。
- `tasks` 只投影权威 `tasks.md`；`review` 只投影 readiness / fresh verification / code review；`handoff` 只在权威门禁允许转换时出现。
- `archive` 只在 OpenSpec archive 实际完成后出现。`verified`、`deferred_to_openspec` 或预计归档路径均不等于 archived/closed。
- 展示中的按钮或 `actions[].prompt` 只能把建议动作回填给 Agent；不得自动实施、批准、commit、push、merge、archive 或执行危险操作。

## 2. 展示能力协商

先读取 `handoff-contract.md` 的 `presentation_capability`：

| mode | 输出方式 |
|---|---|
| `delivery-ui/v1` | 输出本文件定义的 `schemaVersion: delivery-ui/v1` fenced block |
| `legacy-v0` | 仅按本文件兼容节输出旧 handoff/pipeline/tasks 需要的字段；不支持安全语义映射的 review/archive 使用 Markdown |
| `markdown` | 不输出结构化 fenced block；渲染同一权威 handoff 的可读摘要 |

不得用“先发一个块看看能否显示”的方式探测宿主。能力未知时选择 Markdown；结构化显示失败不影响权威 `delivery-handoff/v1` 的有效性。

## 3. 版本与通用规则

所有结构化展示块使用：

```json
{
  "schemaVersion": "delivery-ui/v1",
  "type": "delivery-<kind>"
}
```

字段规则：

- 传输字段使用 camelCase；权威 handoff / artifact 字段继续使用各 Skill 定义的 snake_case。
- 面向用户的中文写入 `label`、`summary`、`message`；不要把业务文案变成前端 i18n key。
- 不支持该 schema 的宿主直接使用 Markdown fallback；不要为了获得卡片而切换模式或更改宿主配置。
- 若宿主解析 fenced block，language 使用与 `type` 相同的 `delivery-<kind>`。
- 半截或无效 JSON 不得被当成状态更新；渲染器可以容错显示，但 Agent 必须重新输出完整块后才视为有效展示。

四阶段 handoff 中的语义 `presentation` 块必须包含：

```text
presentation:
  schema: delivery-presentation/v1
  from_task:
  to_task:
  summary:
  evidence:
  continue_prompt:
```

其中 `delivery-presentation/v1` 是语义投影版本；渲染 fenced block 使用 `delivery-ui/v1`。

## 4. 能力状态映射

内部枚举是权威值；UI 值仅供展示：

| 能力 | 内部权威值 | 首选 UI 值 | 含义 |
|---|---|---|---|
| Memory | `ok` | `fresh` | 可用且索引新鲜 |
| Memory | `stale-index` | `stale` | 可达但索引陈旧或漏项 |
| Memory | `down` | `unavailable` | MCP 不可达 |
| Memory | 未探测/缺失 | `unknown` | 尚无事实 |
| OpenSpec | `initialized` | `ready` | 仓库已采用且可用 |
| OpenSpec | `cli-only` | `limited` | CLI 可用、仓库未初始化 |
| OpenSpec | `unavailable` | `unavailable` | 后端不可用 |
| Superpowers | `loaded` | `ready` | 所需能力已加载 |
| Superpowers | `partial(<missing>)` | `limited` | 部分能力缺失；保留 detail |
| Superpowers | `missing` | `unavailable` | 未加载 |

首选结构同时保留原值，避免 UI 状态丢失语义：

```json
{
  "capabilities": {
    "memory": { "source": "stale-index", "view": "stale" },
    "openspec": { "source": "initialized", "view": "ready" },
    "superpowers": { "source": "partial(debugging)", "view": "limited", "detail": "debugging" }
  }
}
```

若旧渲染器只接受 `fresh | stale | unknown`：`ok→fresh`、`stale-index→stale`、`down→unknown`。此兼容投影必须另带 `capabilityDetails.memory: down`，且不得把 `down` 回写成内部 `unknown`。

## 5. `legacy-v0` 兼容投影

仅当 `presentation_capability.mode: legacy-v0` 时使用。兼容对象是只读视图，不得替代或改写 `delivery-handoff/v1`。

旧 handoff 使用以下形状：

```json
{
  "type": "delivery-handoff",
  "familyVersion": "delivery-family/1.2",
  "handoffId": "<canonical handoff_id>",
  "from": "<stage>",
  "to": "<next_skill-or-next_action-or-end>",
  "fromTask": "<presentation.from_task>",
  "toTask": "<presentation.to_task>",
  "summary": "<presentation.summary>",
  "capabilities": {
    "memory": "fresh|stale|unknown",
    "openspec": "fresh|stale|unknown",
    "superpowers": "fresh|stale|unknown"
  },
  "capabilityDetails": {
    "memory": "ok|stale-index|down",
    "openspec": "initialized|cli-only|unavailable",
    "superpowers": "loaded|partial(<missing>)|missing"
  },
  "stateSource": { "label": "<label>", "anchor": null },
  "sourceRevision": { "repoHead": null, "artifactRevision": null, "stateObservedAt": "<RFC3339>" },
  "evidence": [],
  "gateStatus": "<authoritative gate status>",
  "continuePrompt": "<presentation.continue_prompt>",
  "memoryStale": false
}
```

兼容映射：

| 内部值 | 旧值 | 额外规则 |
|---|---|---|
| Memory `ok` | `fresh` | `memoryStale: false` |
| Memory `stale-index` | `stale` | `memoryStale: true`，允许旧 UI 显示刷新索引动作 |
| Memory `down` | `unknown` | `memoryStale: false`；必须在 `capabilityDetails.memory` 保留 `down` |
| OpenSpec `initialized` / `cli-only` / `unavailable` | `fresh` / `stale` / `unknown` | `capabilityDetails.openspec` 保留原值 |
| Superpowers `loaded` / `partial(...)` / `missing` | `fresh` / `stale` / `unknown` | `capabilityDetails.superpowers` 保留原值 |

旧 renderer 若只接受 `ship | ship_with_warnings | block`，不要把 readiness、verification 或 code review 的 `pass` 投影成 `ship`；这会产生发布授权歧义。该 review 改用 Markdown。Execute 未经 OpenSpec archive 时，旧 handoff 的 `to` 只能指向 archive 动作，禁止写 `closed` 或预计 archive 路径。

## 6. 五类展示块

### `delivery-pipeline`

```json
{
  "schemaVersion": "delivery-ui/v1",
  "type": "delivery-pipeline",
  "changeId": "<id-or-null>",
  "changeSummary": "<一句话>",
  "route": "Read-only|Quick|Standard|High|Debug|n/a",
  "risk": "none|low|medium|high|unknown",
  "currentStage": "explore|frame|plan|execute",
  "stages": [
    { "id": "explore", "status": "pending|active|done|skipped", "label": "探索", "artifacts": [] },
    { "id": "frame", "status": "pending|active|done|skipped", "label": "定框", "artifacts": [] },
    { "id": "plan", "status": "pending|active|done|skipped", "label": "计划", "artifacts": [] },
    { "id": "execute", "status": "pending|active|done|skipped", "label": "实施验证", "artifacts": [] }
  ],
  "gates": [
    { "id": "<id>", "label": "<名称>", "status": "pass|fail|warn|pending|skipped", "evidence": "<anchor-or-null>" }
  ]
}
```

Explore 尚无正式 change 时 `changeId` 为 null；不得为展示创建 change。

### `delivery-tasks`

```json
{
  "schemaVersion": "delivery-ui/v1",
  "type": "delivery-tasks",
  "title": "<任务集标题>",
  "changeId": "<id>",
  "source": "<authoritative tasks.md path>",
  "tasks": [
    {
      "id": "<task-id>",
      "subject": "<行为导向标题>",
      "activeForm": "<进行中提示>",
      "status": "pending|in_progress|completed|deleted",
      "evidence": ["<path/test/record>"]
    }
  ]
}
```

状态必须由权威任务记录投影；展示交互不得直接勾改 `tasks.md`。

### `delivery-review`

```json
{
  "schemaVersion": "delivery-ui/v1",
  "type": "delivery-review",
  "reviewKind": "readiness|verification|code_review",
  "verdict": "pass|pass_with_warnings|block",
  "summary": "<一句结论>",
  "source": "<readiness/verification/review anchor>",
  "groups": [
    {
      "level": "blocker|warning|suggestion",
      "title": "<分组标题>",
      "items": [
        { "id": "<id>", "message": "<描述>", "gate": "<gate-or-null>", "file": "<path-or-null>", "line": 0 }
      ]
    }
  ]
}
```

`pass_with_warnings` 只表示展示结论；warning 是否被接受仍以可见闸门摘要和权威批准记录为准。不要使用 `ship`，避免把 readiness 或 code review 卡片误读为合并、部署或发布授权。

### `delivery-handoff`

```json
{
  "schemaVersion": "delivery-ui/v1",
  "familyVersion": "delivery-family/1.2",
  "type": "delivery-handoff",
  "handoffId": "<canonical handoff_id>",
  "generatedAt": "<canonical generated_at>",
  "from": "<source-stage>",
  "to": "<next-skill-or-action>",
  "fromTask": "<presentation.from_task>",
  "toTask": "<presentation.to_task>",
  "summary": "<presentation.summary>",
  "capabilities": {
    "memory": { "source": "ok|stale-index|down", "view": "fresh|stale|unavailable|unknown" },
    "openspec": { "source": "initialized|cli-only|unavailable", "view": "ready|limited|unavailable|unknown" },
    "superpowers": { "source": "loaded|partial(<missing>)|missing", "view": "ready|limited|unavailable|unknown" }
  },
  "stateSource": { "label": "<label>", "anchor": "<path-or-null>" },
  "sourceRevision": { "repoHead": null, "artifactRevision": null, "stateObservedAt": "<RFC3339>" },
  "evidence": [{ "id": "<id>", "label": "<label>", "anchor": "<path>" }],
  "gateStatus": { "status": "<authoritative status>", "bindsToRevision": null, "acceptedWarningIds": [] },
  "continuePrompt": "<presentation.continue_prompt>"
}
```

`to` 只表达当前允许的下一动作。Execute 仅 verified 时应指向已解析的 OpenSpec `archive_change`，不得写 `closed`。展示必须保留 canonical handoff 的 revision 绑定，不得把 stale gate 显示为可继续。

### `delivery-archive`

```json
{
  "schemaVersion": "delivery-ui/v1",
  "type": "delivery-archive",
  "changeId": "<id>",
  "archivePath": "<actual completed archive path>",
  "changeSummary": "<一句话>",
  "verification": {
    "testsRun": 0,
    "testsPassed": 0,
    "lintPass": true,
    "buildPass": true,
    "notes": "<摘要>"
  },
  "residual": ["<遗留项>"],
  "commitHash": null,
  "prUrl": null,
  "actions": [
    { "id": "<id>", "label": "<动作>", "kind": "commit|pr|done", "prompt": "<回填给 Agent 的请求>" }
  ]
}
```

只有 archive 已完成才输出。`commitHash` / `prUrl` 只能填已存在的事实；`actions` 不自动执行任何外部写操作。

## 7. 阶段发射门禁

| 阶段 | 可以展示 | 必须满足 |
|---|---|---|
| Explore | `pipeline`；进入 frame 的 `handoff` | handoff 仅在 `direction_alignment: selected` 后 |
| Frame | `pipeline`；进入 plan/execute/explore 的 `handoff` | 权威规格/契约闸门允许转换 |
| Plan | `pipeline`、`tasks`、`review`、进入 execute 的 `handoff` | tasks/readiness 来自权威工件；handoff 仅在实现闸门通过后 |
| Execute | `tasks`、`review`、继续/回流/archive 的 `handoff` | 新鲜证据决定 verdict；archive handoff 不等于 archived |
| OpenSpec archive 后 | `archive` | 已有真实 archive 路径及完成记录 |

## 8. Markdown fallback

宿主不支持 `delivery-ui/v1` 时，直接渲染同一 handoff 的 `presentation` 字段、任务摘要和审查分组。保留相同门禁与状态词；不得因为没有卡片而省略 blocker、warning、证据或下一步限制。

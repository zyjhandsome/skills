# Decision record schema

Files live beside the report under `decision-records/`.

## Naming

| Unit | Filename |
|---|---|
| Migration path | `migration-path__<path-id>.md` |
| Subsystem | `subsystem__<subsystem-id>.md` |

## Required fields

| 字段 | Notes |
|---|---|
| 单元键 | `path:<id>` or `subsystem:<id>` |
| 类型 | `path` / `subsystem` |
| 当前结论 | recommended path or subsystem action summary |
| 风险 | `blocker` / `high` / `medium` / `low` / `n/a` |
| 命名配方 | recipe ids or `—`；never executed |
| 兼容性证据（URL） | 须含至少一处 `http://` 或 `https://` URL（优先 official-docs-index） |
| 已命名验证项 | 实施期命令 + 失败证明什么（本阶段不执行）；有命名配方时禁止空白 |
| 回滚触发条件 + 恢复目标 | |
| 责任人 | |
| 推荐确认选项 | `proceed:path:…` / `proceed:subsystem:…` / `defer` / `other` |
| 确认队列状态 | `ready` / `pending` / `blocked` / `decided` / `deferred` |
| 人工答复 | filled after human answers |

`analysis_status=complete` requires: path decision-record present, and one
decision-record (`subsystem__<id>.md`) per §4 High/blocker subsystem
(`risk` in `high|blocker`, not `not_applicable`). Those units must also appear
in the confirmation queue as `decided` / `deferred` / `blocked`.

`人工答复` must quote the human's verbatim token (`proceed:…` / `defer` /
`other`). Do not invent tokens from「继续/全部放行」.

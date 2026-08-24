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
| 分叉人工答复 | exact `confirm:` token(s), or `—` when this unit has no open fork |

`analysis_status=complete` requires one decision-record for every unit that
appears in §7, including optional medium subsystems the caller explicitly put
into the queue. High/blocker and `required_for_path=yes` rows must appear in §7;
medium/low rows are not forced into it.

`人工答复` must quote the human's verbatim token (`proceed:…` / `defer` /
`other`). It proves only the scope/queue decision. `分叉人工答复` separately
quotes every verbatim `confirm:` token that selected an internal branch. The
validator requires those tokens to equal the values recorded in §3/§4; use `—`
when no fork was triggered. Do not invent either field from「继续/全部放行/按建议来」.

# 工件门禁检查（轻量）

> 规则级 / 试点仓检查清单与可脚本化断言。不替代人工闸门；用于在 plan 就绪审查与 execute 新鲜验证前后拦住明显坏状态。

## 何时跑

- `delivery-plan-tasks`：就绪审查前 / 实现闸门前
- `delivery-execute-verify`：Fresh Verification Gate 前；声称 `verified` 前
- 试点 CI（可选）：对 `openspec/changes/<id>/` 跑本文件「可脚本化断言」

## 人工检查清单

| ID | 断言 | 失败处置 |
|---|---|---|
| G1 | 存在唯一 OpenSpec change 状态源；仓库根下无平行 `brief.md` / `workflow-state.yaml` / 第二套 `tasks.md` 与 change 内 tasks 竞争 | 停止并报告精确路径；未经用户授权不得删除/移动/合并，回 Frame 决定权威来源 |
| G2 | `tasks.md`（或 Quick 最小 tasks）每条含真实路径或符号，无「implement backend」类空任务 | 关实现闸门；回 plan |
| G3 | 每条任务有可证伪验证命令/动作与期望结果 | 关实现闸门 |
| G4 | `verification.md`（或等价附件）在声称 verified 时含：命令、时间、退出码/结果摘要 | 不得 `verified` |
| G5 | Medium/High：规格闸门与实现闸门均有批准人/时间；无则不得实施/关闭 | 停止 |
| G6 | 未在 Execute 内把 delta sync 进 canonical specs 或移动 change 到 archive | 停止并报告精确 diff；未经用户授权不得自动回滚，修复后改走已解析的 `archive_change` 操作 |
| G7 | Medium/High 声称 verified 时：`code_review.mode=independent` 且 `independent_review` 为 `required_pass` 或 `required_warn_accepted`；禁止用 `self_fresh_context` 关闭 | 不得 `verified`；补独立审查或保持 blocked |
| G8 | Plan/Execute 前：列出其他 active OpenSpec changes；若与本 change 任务允许路径/符号重叠，记为就绪 **阻塞项**（除非用户显式接受并写入闸门摘要） | 关实现闸门或停止并行实施 |

## 可脚本化断言（试点）

优先运行 `../scripts/validate_delivery_change.py`。它按完整任务块检查字段，而不是要求路径必须写在 checkbox 标题行；自定义 OpenSpec schema 可通过 `--tasks` / `--verification` 传入实际槽位。

剩余规则伪代码：

```text
FAIL if exists repo-root brief.md OR workflow-state.yaml beside active change
FAIL if any checkbox task block lacks a non-empty target path/symbol field, validation command/action, or expected result
FAIL if claiming verified AND (verification missing OR no command+timestamp field)
FAIL if openspec/specs/ mtime newer than verification without archive record  # 可选，防静默 sync
```

Agent 最小执行方式（无 CI 时）：按上表 G1–G6 逐项打勾写入就绪审查或 verification；任一项 FAIL → 不得放行实现闸门或 `verified`。

## 与 Skill 的关系

- 本文件是 **检查协议**，不是第二状态源。
- 详细任务字段仍以 `delivery-plan-tasks` tasks 模板为准；本文件只拦「缺路径 / 缺证据 / 双状态源 / 静默 archive」。

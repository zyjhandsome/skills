# 工件门禁检查（轻量）

> 规则级 / 试点仓检查清单与可脚本化断言。不替代人工闸门；用于在 plan 就绪审查与 execute 新鲜验证前后拦住明显坏状态。

## 何时跑

- `delivery-plan-tasks`：就绪审查前 / 实现闸门前
- `delivery-execute-verify`：Fresh Verification Gate 前；声称 `verified` 前
- 试点 CI（可选）：对 `openspec/changes/<id>/` 跑本文件「可脚本化断言」

## 人工检查清单

| ID | 断言 | 失败处置 |
|---|---|---|
| G1 | 存在唯一 OpenSpec change 状态源；仓库根下无平行 `brief.md` / `workflow-state.yaml` / 第二套 `tasks.md` 与 change 内 tasks 竞争 | 停止；删除或合并竞争源 |
| G2 | `tasks.md`（或 Quick 最小 tasks）每条含真实路径或符号，无「implement backend」类空任务 | 关实现闸门；回 plan |
| G3 | 每条任务有可证伪验证命令/动作与期望结果 | 关实现闸门 |
| G4 | `verification.md`（或等价附件）在声称 verified 时含：命令、时间、退出码/结果摘要 | 不得 `verified` |
| G5 | Medium/High：规格闸门与实现闸门均有批准人/时间；无则不得实施/关闭 | 停止 |
| G6 | 未在 Skill 3 内把 delta sync 进 `openspec/specs/` 或移动 `changes/archive/` | 回滚误操作；改走 `/opsx-archive` |

## 可脚本化断言（试点）

在 change 目录上检查（伪代码；试点仓可落成 shell/python）：

```text
FAIL if exists repo-root brief.md OR workflow-state.yaml beside active change
FAIL if tasks.md has a line matching ^- \[.\] (?!.*(`|/|\\|\.py|\.ts|\.go|\.rs))  # 无路径线索的弱启发，人工复核
FAIL if claiming verified AND (verification missing OR no command+timestamp field)
FAIL if openspec/specs/ mtime newer than verification without archive record  # 可选，防静默 sync
```

Agent 最小执行方式（无 CI 时）：按上表 G1–G6 逐项打勾写入就绪审查或 verification；任一项 FAIL → 不得放行实现闸门或 `verified`。

## 与 Skill 的关系

- 本文件是 **检查协议**，不是第二状态源。
- 详细任务字段仍以 `delivery-plan-tasks` tasks 模板为准；本文件只拦「缺路径 / 缺证据 / 双状态源 / 静默 archive」。

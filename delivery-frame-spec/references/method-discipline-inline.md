# Inline method discipline（Superpowers 软依赖回退）

当宿主未安装 Superpowers，或所需方法无法加载时：**不要停机**。把 `capability_snapshot.superpowers` 标为 `missing` 或 `inline`，在 `capability_bindings.superpowers` 记录 `source: delivery-inline`，并遵守本文件的最小纪律。已加载 Superpowers 时优先用其对应方法，本文件作核对清单。

本文件不是第二状态源，也不替代 OpenSpec / Memory 硬前提。

## 探索 / 定框（对应 brainstorming）

- 实质分叉给 2–3 个选项，各带利弊与一句推荐依据。
- 不把探索地图当成已批准规格；不替用户锁定产品范围。

## 计划（对应 writing-plans）

- 任务必须是纵向行为切片，含真实路径/符号与可证伪验证。
- 不为“占满并行槽”强拆任务；共享可变状态则顺序执行。

## 实施 · TDD 时序（对应 test-driven-development）

- 行为变更：先只写失败测试 → 观察 RED（正确原因）→ 最小实现 → 观察 GREEN → 再重构。
- **禁止**同一并行工具批次里同时改失败测试与生产代码。
- 若本 Agent 已先写了未经验证的实现：撤掉该实现，从 RED 重来（勿删用户既有代码）。
- TDD 确实不适用时：记录原因、替代验证与残留覆盖缺口。

## 调试（对应 systematic-debugging）

失败时暂停普通实施：复现 → 证据（日志/输入/环境）→ 限定失败路径 → 一个可证伪根因假设 → 一次最小实验 → 修根因 → 重跑原复现与回归。  
重试偶然通过 ≠ flaky；需有非确定性基础设施/时序证据。

## 完成前验证（对应 verification-before-completion）

- 声称完成 / `verified` 前：跑当前完整验证集，读退出码与失败计数；规格核对与运行时证据缺一不可。
- 任一必需验证失败或未新鲜跑过 → 禁止完成/合并话术。

## 审查（对应 requesting/receiving-code-review）

- Medium/High：`verified` 需要独立审查（独立 SubAgent **或** 人类）`pass`/`warn`，无 CRITICAL。
- 审查建议当假设：改前核实，改后重跑受影响验证与最终验证。

## 并行 / worktree（对应 dispatching-parallel-agents / using-git-worktrees）

- 默认 inline。仅当任务无共享可变状态、无文件重叠、验证独立、且宿主有空槽时并行。
- 不得为启用 worktree 而 stash/commit/丢弃用户未提交改动。

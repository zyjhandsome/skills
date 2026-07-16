# 子代理编排规则回归测试

> **历史版本标注（v1.1 场景集）：** 基于 `delivery-family/1.1` 规则快照。`delivery-family/1.2` 起 SubAgent 与独立审查为硬前提，「无 SubAgent / 无独立 Reviewer 时如何降级」类问题（下方 Prompt 第 6 问）在 1.2 下的正确答案是**停止并报告宿主异常**，不再是降级序列。其余编排、波次、worktree、基线失败场景仍有效。
>
> 测试性质：规则级 prompt 回归，不代表真实仓库吞吐、质量或生产稳定性数据。

## 测试日期

2026-07-13

## 测试环境与版本

- 宿主：Claude Code。
- 测试 Agent：`generalPurpose`，只读。
- 模型：调用时未显式指定，继承会话默认模型。
- 版本标识：本次文件未绑定 git commit SHA；RED 为修改前文件快照，GREEN 为 2026-07-13 当前安装版本。

## 测试 Prompt

```text
严格只依据当前 delivery-execute-verify/SKILL.md 和 orchestration references，
不要按常识补造规则。

针对下方 T1–T4 场景，输出：
1. 是否自动派发 SubAgent；
2. 哪些任务并行/顺序；
3. worktree 和用户未提交改动如何处理；
4. 每个 SubAgent 的输入；
5. 任务后审查与集成验证；
6. 无 SubAgent、无独立 Reviewer 时如何降级；
7. Quick/Debug 没有 tasks.md 时如何建图；
8. 基线失败时如何处理。

最后给出 PASS/FAIL，并列出当前规则未明文覆盖的缺口。
```

## 场景

- T1：独立导出格式转换器，只修改 `packages/export/a.ts` 与对应测试。
- T2：独立历史列表空状态，只修改 `apps/desktop/history-empty.tsx` 与对应测试。
- T3：依赖 T1，修改 `apps/desktop/export-button.tsx`。
- T4：依赖 T2，也修改 `apps/desktop/export-button.tsx`。
- 宿主支持 SubAgent 与 git worktree。
- 当前工作区存在用户未提交改动。

检查项：

1. 是否自动决定 SubAgent 派发；
2. 是否正确安排并行/顺序波次；
3. 是否保护未提交改动；
4. 是否在派发前确定隔离、集成目标与 git 授权；
5. 是否提供自包含任务包；
6. 是否进行规格符合性、代码质量与集成验证；
7. 无 SubAgent 或独立审查时是否安全降级。

## RED：修改前基线

结论：FAIL。

原始结论摘要：

```text
当前 Skill 规定单任务循环、依赖就绪推进、任务级验证及最终新鲜验证，
但没有 SubAgent 自动派发、并行调度、worktree、SubAgent 输入
或无 SubAgent 降级规则。按该压力测试关注项判定为 FAIL。
```

原 Skill 只规定单任务循环、任务级验证和最终验证，没有明确：

- 自动 SubAgent 派发条件；
- T1/T2 并行、T3/T4 顺序；
- worktree 与用户未提交改动处理；
- SubAgent 输入契约；
- 每任务双阶段审查；
- 无 SubAgent 降级协议。

## GREEN：加入编排协议后的复测

结论：PASS（规则覆盖）。

原始结论摘要：

```text
规则已覆盖 T1–T4 编排，以及 Quick/Debug 图来源、派发前集成授权、
完整仓库状态与基线失败处理、独立 Reviewer 缺失时的分级降级。
规则覆盖判定 PASS。
```

- T1/T2 进入第一并行波次。
- 第一波完成审查、集成与验证后，T3/T4 因共享文件顺序执行。
- 用户未提交改动不得被自动 stash、commit、覆盖或丢弃。
- staged、unstaged、untracked 与目标文件碰撞必须分别记录。
- worktree 派发前必须确定集成目标、集成机制、所需 git 授权和清理策略；无授权路径则改为内联。
- Quick/Debug 轻量契约默认作为单节点图处理。
- 每个 SubAgent 收到自包含任务包，返回后检查真实差异并进行双阶段审查与集成验证。
- 基线失败只有在证明为既存且与目标行为独立、并由用户批准完整降级记录后才能继续。
- 无独立审查能力时不得冒充独立审查；Low 需要用户接受降级和残余风险，Medium/High 保持阻塞。

## 未由本测试证明

- 实际 worktree 创建、合并和冲突率；
- 真实项目测试、构建或 E2E 结果；
- 团队吞吐提升或返工率下降；
- 不同宿主的 SubAgent 行为一致性；
- 成本、并发上限与长任务稳定性。

这些结论必须通过真实项目试点另行采集。

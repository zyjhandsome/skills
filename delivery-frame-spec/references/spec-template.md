# 增量规格模板（OpenSpec delta spec）

写入 `openspec/changes/<id>/specs/<capability-path>/spec.md`。机器骨架保持英文原样，业务描述用中文。范围和决策写在 `proposal.md`，验收矩阵写在 `design.md`：非 delta 小节不会被归档带进主规格，`openspec validate` 会告警。

```markdown
## Purpose
<仅新建 capability 时写；至少 50 个字符，说明这个 capability 负责什么。修改既有 capability 时删掉本节>

## ADDED Requirements

### Requirement: <名称>
系统 MUST <可观察行为>。

#### Scenario: <正常场景名>
- **GIVEN** <前置条件>
- **WHEN** <执行动作>
- **THEN** <可观察结果>
- **AND** <附加结果>

#### Scenario: <失败或边界场景名>
- **WHEN** <失败或边界情况>
- **THEN** <可观察的处理方式>

## MODIFIED Requirements

### Requirement: <与主规格完全一致的名称>
<先从 openspec/specs/<capability-path>/spec.md 复制整块 Requirement（含全部 Scenario），再在副本上改>

## REMOVED Requirements

### Requirement: <名称>
**Reason**: <为什么移除>
**Migration**: <调用方怎么办>
```

规则：

- 每条 Requirement 的首句含英文 `MUST` 或 `SHALL`，正文不超过 500 个字符；例子和边界放进 Scenario。
- 每条 Requirement 至少一个 `#### Scenario:`（必须是四个 `#`）；每个 Scenario 至少有 `**WHEN**`（或 `**GIVEN**`）和 `**THEN**`。
- `MODIFIED` 是整块替换：漏带主规格里仍存在的 Scenario，`openspec validate` 报 ERROR。
- 不用的 delta 小节整节删掉，不留空标题。
- 任务的「对应需求/场景」原样抄 Requirement 名称，校验脚本按字面核对追溯。
- 没有规格级行为变化（纯重构、工具、文档）时不写 spec，在 `.openspec.yaml` 设 `skip_specs: true`；不要为了过校验造 Requirement。
- 规格里有阻塞实施的待定项、无法验证的形容词、隐藏范围，或把猜测的技术细节当成需求，不得通过规格闸门。

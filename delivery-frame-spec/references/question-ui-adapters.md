# Question UI adapters（delivery 家族共用）

仅在执行 `batch-clarification.md` 的点击优先规则、需要把语义问题映射到当前宿主工具时读取本文件。`batch-clarification.md` 是问题内容、分波和决策归属的权威规范；本文件只负责传输适配。

## 目录

1. 适配顺序
2. 语义输入
3. `request_user_input` 类工具
4. `AskUserQuestion` 类工具
5. Gate 适配
6. 回答归一化
7. Anti-patterns

## 适配顺序

1. 探测当前回合实际可用的选择/问卷工具及其 schema。
2. 若工具能在一次调用中承载本波全部独立问题，使用该工具。
3. 若工具只能承载一题，而本波有多道独立问题，使用 Markdown fallback 一次列全；不要为了 UI 把独立问题拆成多轮。
4. 若没有选择工具，使用 `batch-clarification.md` 的 Markdown fallback。
5. 不切换模式、不更改宿主配置，也不假设某个工具必然存在。

## 语义输入

每题先形成平台无关记录：

```text
id:
header:
prompt: <背景 + 问题 + 推荐值与依据>
options:
  - label: <推荐项带「建议：」>
    description: <实质影响>
recommendation:
allow_other: true | false
applies_when:
```

固定选择题必须满足 `batch-clarification.md` 的推荐、选项数量和分波规则后，才能进入适配器。

## `request_user_input` 类工具

适用于工具入参为 `questions[]`，每题含 `header`、`question`、`options[]` 的宿主：

```json
{
  "questions": [
    {
      "header": "SDD 澄清",
      "question": "<背景 + 问题。推荐：B — 依据。>",
      "options": [
        { "label": "A. <选项>", "description": "<影响>" },
        { "label": "建议：B. <选项>", "description": "<影响>" }
      ]
    }
  ]
}
```

规则：

- 把本波全部独立问题放在同一个 `questions[]`；遵守工具允许的最大题数，超过上限时使用 Markdown fallback，不得静默漏题。
- 若工具自动提供 Other/freeform，不重复添加「其他」；否则仅在 `allow_other: true` 时添加。
- 仅在用户回复有助于但不阻塞时设置自动超时；闸门和阻塞决策不得自动选择或超时套用推荐。
- 工具不支持多选时，不把多个互斥问题伪装成一题多选；保持逐题单选、同波提交。

## `AskUserQuestion` 类工具

适用于额外支持 `multiSelect` 的问卷宿主：

```json
{
  "questions": [
    {
      "header": "SDD 澄清",
      "question": "<背景 + 问题。推荐：B — 依据。>",
      "options": [
        { "label": "A. <选项>", "description": "<影响>" },
        { "label": "建议：B. <选项>", "description": "<影响>" }
      ],
      "multiSelect": false
    }
  ]
}
```

只有语义问题本身允许同时选多个答案时才把 `multiSelect` 设为 true；“一波有多题”不等于“一题多选”。

## Gate 适配

规格闸门和实现闸门保持单题，并使用：

- `header`: `规格闸门` 或 `实现闸门`；
- `question`: 可见范围、风险/代价、回滚、下一步、推荐及依据；
- `options`: `建议：开始…` / `先不…` / `有修改（说明）`。

Agent 内部检查项不进入 `questions[]`。用户批准仅覆盖题干中明确展示的范围、风险和 warnings。

## 回答归一化

收到工具或 Markdown 回答后，写回当前阶段的权威决策台账：

```text
decision_id:
selected_option:
freeform_detail:
decided_by:
decided_at:
applies_to:
evidence_context:
```

不要保存 UI 序号作为唯一含义；同时保存稳定 decision id 和选项文本。若回答含糊、缺题或同时选择互斥项，只追问缺失/冲突项，不重问已经明确的决定。

## Anti-patterns

- 在核心 Skill 中写死某个宿主或工具名。
- 因工具题数上限丢弃独立阻塞问题。
- 用自动超时、默认值或推荐项替代阻塞决策。
- 把多题波次压成一题多选，导致答案与决策项无法一一对应。
- 工具返回后不写入权威工件，只依赖聊天卡片保存决定。

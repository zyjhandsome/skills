# 决策记录 — `subsystem:ui`

| 字段 | 内容 |
|---|---|
| 单元键 | subsystem:ui |
| 类型 | subsystem |
| 当前结论 | Element UI → Element Plus，纳入本次升级 |
| 风险 | blocker |
| 命名配方 | gogocode-element（Name, never run） |
| 兼容性证据（URL） | https://element-plus.org/en-US/guide/migration.html |
| 已命名验证项 | 关键表单/表格视觉与交互回归 |
| 回滚触发条件 + 恢复目标 | UI 回归失败 → 整仓回滚 |
| 责任人 | 前端组 |
| 推荐确认选项 | proceed:subsystem:ui / defer / other |
| 确认队列状态 | decided |
| 人工答复 | proceed:subsystem:ui |

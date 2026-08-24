# 决策记录 — `subsystem:core-vue`

| 字段 | 内容 |
|---|---|
| 单元键 | subsystem:core-vue |
| 类型 | subsystem |
| 当前结论 | vue 2.7 → vue@3 + `@vue/compat`，纳入本次升级 |
| 风险 | high |
| 命名配方 | vue-compat（Name, never run） |
| 兼容性证据（URL） | https://v3-migration.vuejs.org/migration-build |
| 已命名验证项 | compat warning 清零；摘 compat 后冒烟 |
| 回滚触发条件 + 恢复目标 | 运行时错误上升 → 整仓回滚 |
| 责任人 | 前端组 |
| 推荐确认选项 | proceed:subsystem:core-vue / defer / other |
| 确认队列状态 | decided |
| 人工答复 | proceed:subsystem:core-vue |
| 分叉人工答复 | — |

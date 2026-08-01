# 决策记录 — `subsystem:i18n-plugins`

| 字段 | 内容 |
|---|---|
| 单元键 | subsystem:i18n-plugins |
| 类型 | subsystem |
| 当前结论 | 残余 Vue2 插件（如 vue-count-to）纳入替换/移除决策 |
| 风险 | high |
| 命名配方 | —（Name, never run） |
| 兼容性证据（URL） | https://v3-migration.vuejs.org/ |
| 已命名验证项 | 相关 demo 页冒烟 |
| 回滚触发条件 + 恢复目标 | 功能回归 → 整仓回滚 |
| 责任人 | 前端组 |
| 推荐确认选项 | proceed:subsystem:i18n-plugins / defer / other |
| 确认队列状态 | decided |
| 人工答复 | proceed:subsystem:i18n-plugins |

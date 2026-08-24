# 决策记录 — `subsystem:build`

| 字段 | 内容 |
|---|---|
| 单元键 | subsystem:build |
| 类型 | subsystem |
| 当前结论 | Vue CLI → Vite，与 Vue3 同升 |
| 风险 | high |
| 命名配方 | webpack-to-vite（Name, never run） |
| 兼容性证据（URL） | https://v3-migration.vuejs.org/recommendations |
| 已命名验证项 | vite build；CI Node 对齐 |
| 回滚触发条件 + 恢复目标 | 构建失败 → 整仓回滚 |
| 责任人 | 前端组 |
| 推荐确认选项 | proceed:subsystem:build / defer / other |
| 确认队列状态 | decided |
| 人工答复 | proceed:subsystem:build |
| 分叉人工答复 | — |

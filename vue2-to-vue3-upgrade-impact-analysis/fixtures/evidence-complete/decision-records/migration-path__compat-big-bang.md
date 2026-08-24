# 决策记录 — `path:compat-big-bang`

| 字段 | 内容 |
|---|---|
| 单元键 | path:compat-big-bang |
| 类型 | path |
| 当前结论 | 单仓大爆炸切流 + 仓内 @vue/compat + 构建同升偏 Vite |
| 风险 | high |
| 命名配方 | vue-compat, webpack-to-vite（Name, never run） |
| 兼容性证据（URL） | https://v3-migration.vuejs.org/migration-build |
| 已命名验证项 | 构建通过；摘 compat 后冒烟 |
| 回滚触发条件 + 恢复目标 | 冒烟失败 → 回布上一版本 |
| 责任人 | 前端组 |
| 推荐确认选项 | proceed:path:compat-big-bang / defer / other |
| 确认队列状态 | decided |
| 人工答复 | proceed:path:compat-big-bang |
| 分叉人工答复 | — |

# 决策记录 — `subsystem:router`

| 字段 | 内容 |
|---|---|
| 单元键 | subsystem:router |
| 类型 | subsystem |
| 当前结论 | vue-router 3 → 4，纳入本次升级 |
| 风险 | high |
| 命名配方 | manual-router4（Name, never run） |
| 兼容性证据（URL） | https://router.vuejs.org/guide/migration/ |
| 已命名验证项 | 登录跳转；动态路由；404 通配 |
| 回滚触发条件 + 恢复目标 | 导航失败 → 整仓回滚 |
| 责任人 | 前端组 |
| 推荐确认选项 | proceed:subsystem:router / defer / other |
| 确认队列状态 | decided |
| 人工答复 | proceed:subsystem:router |

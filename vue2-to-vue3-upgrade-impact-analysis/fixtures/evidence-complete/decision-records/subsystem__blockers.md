# 决策记录 — `subsystem:blockers`

| 字段 | 内容 |
|---|---|
| 单元键 | subsystem:blockers |
| 类型 | subsystem |
| 当前结论 | vue-count-to 采用 replace，纳入本次升级 |
| 风险 | blocker |
| 命名配方 | —（Name, never run） |
| 兼容性证据（URL） | https://www.npmjs.com/package/vue-count-to |
| 已命名验证项 | 使用该组件的 demo 页挂载与计数行为冒烟 |
| 回滚触发条件 + 恢复目标 | 功能回归 → 整仓回滚 |
| 责任人 | 前端组 |
| 推荐确认选项 | proceed:subsystem:blockers / confirm:blocker:vue-count-to:replace / defer / other |
| 确认队列状态 | decided |
| 人工答复 | proceed:subsystem:blockers |
| 分叉人工答复 | confirm:blocker:vue-count-to:replace |

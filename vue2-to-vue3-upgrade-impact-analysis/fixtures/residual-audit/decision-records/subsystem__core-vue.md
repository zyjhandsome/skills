# 决策记录 — `subsystem:core-vue`

| 字段 | 内容 |
|---|---|
| 单元键 | subsystem:core-vue |
| 类型 | subsystem |
| 当前结论 | compat alias 未摘 + 上一轮 codemod 残留，纳入本次清理面 |
| 风险 | high |
| 命名配方 | residual-compat-removal, residual-sync-prop-reresolve（Name, never run） |
| 兼容性证据（URL） | https://v3-migration.vuejs.org/migration-build |
| 已命名验证项 | compat warning 清零；7 处弹层回写逐个断言；两配方交集单列一条 |
| 回滚触发条件 + 恢复目标 | 清理后弹层回写失效 → 恢复该批文件到清理前状态 |
| 责任人 | 前端组 |
| 推荐确认选项 | proceed:subsystem:core-vue / defer / other |
| 确认队列状态 | decided |
| 人工答复 | proceed:subsystem:core-vue |
| 分叉人工答复 | — |

# 决策记录 — `path:residual-audit`

| 字段 | 内容 |
|---|---|
| 单元键 | path:residual-audit |
| 类型 | path |
| 当前结论 | workspace 已在 Vue3 运行时上，本次只盘点上一轮迁移的残留，不提出迁移路径 |
| 风险 | high |
| 命名配方 | residual-compat-removal, residual-sync-prop-reresolve（Name, never run） |
| 兼容性证据（URL） | https://v3-migration.vuejs.org/migration-build |
| 已命名验证项 | 摘 compat 后 dev 与 build 各冒烟一次；弹层回写逐个断言 |
| 回滚触发条件 + 恢复目标 | 摘 compat 后冒烟失败 → 恢复 alias 与 compatConfig |
| 责任人 | 前端组 |
| 推荐确认选项 | proceed:path:residual-audit / defer / other |
| 确认队列状态 | decided |
| 人工答复 | proceed:path:residual-audit |

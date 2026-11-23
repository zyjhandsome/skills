# 决策记录 — `io.netty:netty-*`

| 字段 | 内容 |
|---|---|
| 组件 | `io.netty:netty-*`（家族，含 `netty-codec-base` / `netty-codec-compression`） |
| 模块 | `gateway` |
| 版本（当前解析 → 目标） | 4.2.15.Final → 4.1.136.Final |
| 目标存在性 | no |
| 目标通道 | ga |
| 请求目标（GAV / 版本 / 存在性） | `io.netty:netty-*:4.1.136.Final` / no（成员 404） |
| 推荐替代目标（GAV / 版本 / 存在性） | — |
| 建议处置 | no-viable-path |
| usage_status | used |
| introducer_gav | `io.projectreactor.netty:reactor-netty-http`（示意） |
| introducer_upgrade_available | unknown |
| 替代候选 | — |
| scope | compile |
| optional | no |
| exclusions_present | no |
| 依赖路径 | `spring-boot-starter-webflux` → `reactor-netty-http` → netty 家族 |
| 有效 Owner | `boot-bom`（`netty.version`） |
| 权威层 | boot-bom |
| Boot 线 | 3.2.x |
| 构建变体 | default |
| 批次范围 | json-netty |
| Owner 阶梯档位 | —（目标不可达，无 Owner 动作） |
| 方向 | downgrade |
| 入口来源 | exact-table |
| 主 Owner 动作 | 证伪：目标线缺失成员，无法属性覆盖 |
| 残差冲突 | 跨线目标不可达 |
| 兼容性证据（URL） | https://github.com/netty/netty |
| 已命名验证项 | 不适用直至重述目标 |
| 迁移路径选项（仅描述） | — |
| 回滚触发条件 + 恢复目标 | 未实施 |
| 责任人 | 网关组 |
| 推荐确认选项 | 重述目标 / `other`（队列 `blocked`；不得 `defer`） |
| 确认队列状态 | blocked |
| 人工答复 | — |

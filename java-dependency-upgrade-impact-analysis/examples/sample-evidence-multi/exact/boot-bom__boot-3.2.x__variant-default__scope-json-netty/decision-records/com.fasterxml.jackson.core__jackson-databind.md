# 决策记录 — `com.fasterxml.jackson.core:jackson-databind`

| 字段 | 内容 |
|---|---|
| 组件 | `com.fasterxml.jackson.core:jackson-databind` |
| 模块 | `service-api` |
| 版本（当前解析 → 目标） | 2.21.2 → 2.21.4 |
| 目标存在性 | yes |
| 目标通道 | ga |
| 请求目标（GAV / 版本 / 存在性） | — |
| 推荐替代目标（GAV / 版本 / 存在性） | — |
| 建议处置 | upgrade-owner |
| usage_status | used |
| introducer_gav | — |
| introducer_upgrade_available | — |
| 替代候选 | — |
| scope | compile |
| optional | no |
| exclusions_present | no |
| 依赖路径 | `spring-boot-starter-web` → `spring-boot-starter-json` → databind |
| 有效 Owner | `boot-bom`（`jackson-bom.version`） |
| 权威层 | boot-bom |
| Boot 线 | 3.2.x |
| 构建变体 | default |
| 批次范围 | json-netty |
| Owner 阶梯档位 | 2-property-override |
| 方向 | upgrade |
| 入口来源 | exact-table |
| 主 Owner 动作 | 推荐覆盖 `jackson-bom.version`；属性名已在 Boot BOM 核实 |
| 残差冲突 | 预期无 |
| 兼容性证据（URL） | https://github.com/FasterXML/jackson-databind/releases |
| 已命名验证项 | `JsonContractTest`；japicmp 2.21.2→2.21.4 |
| 迁移路径选项（仅描述） | — |
| 回滚触发条件 + 恢复目标 | 契约失败 → 恢复 `jackson-bom.version=2.21.2` |
| 责任人 | 平台组 |
| 推荐确认选项 | `proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4` / `defer` / `other` |
| 确认队列状态 | ready（partial 样例）/ decided（complete 样例） |
| 人工答复 | （complete）`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4` |

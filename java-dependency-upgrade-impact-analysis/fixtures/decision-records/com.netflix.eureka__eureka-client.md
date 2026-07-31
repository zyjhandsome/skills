# 决策记录 — `com.netflix.eureka:eureka-client`

| 字段 | 内容 |
|---|---|
| 组件 | `com.netflix.eureka:eureka-client` |
| 模块 | `discovery` |
| 版本（当前解析 → 目标） | 2.0.6（declared；resolved 待证） → 2.0.5 |
| 目标存在性 | yes |
| 目标通道 | ga |
| 请求目标（GAV / 版本 / 存在性） | — |
| 推荐替代目标（GAV / 版本 / 存在性） | — |
| 建议处置 | move-introducer |
| usage_status | used |
| introducer_gav | `org.springframework.cloud:spring-cloud-starter-netflix-eureka-client`（示意） |
| introducer_upgrade_available | unknown（待 tree/BOM 证据） |
| baseline_evidence_status | pending-tree |
| 下一步补证 | 恢复 wrapper → `-pl discovery -am dependency:tree -Dincludes=com.netflix.eureka:eureka-client` → list 复核 claimed `from=2.0.6` |
| 路径选项菜单 | （基线证实后的 ready 波）A move-introducer / B force-align / C 换 discovery starter / D 换栈 / E 原生改造 — 本波 pending 不列 proceed |
| 替代候选 | — |
| scope | compile |
| optional | no |
| exclusions_present | no |
| 依赖路径 | `spring-cloud-starter-netflix-eureka-client` → `eureka-client`（示意；待 tree） |
| 有效 Owner | `imported-bom`（Spring Cloud） |
| 权威层 | platform-plugin |
| Boot 线 | 3.2.x |
| 构建变体 | default |
| 批次范围 | eureka |
| Owner 阶梯档位 | 1-owner-bump（待证） |
| 方向 | downgrade |
| 入口来源 | exact-table |
| 主 Owner 动作 | 待基线证实后再尝试 introducer/BOM 收敛 |
| 残差冲突 | 基线未证实 |
| 兼容性证据（URL） | https://github.com/Netflix/eureka |
| 已命名验证项 | tree 复核；注册/续约冒烟（实施期） |
| 迁移路径选项（仅描述） | — |
| 回滚触发条件 + 恢复目标 | 注册失败 → 恢复降级前解析树 |
| 责任人 | 平台组 |
| 推荐确认选项 | `defer` / `other`（队列 `pending`；证实前不得 `proceed`） |
| 确认队列状态 | pending |
| 人工答复 | — |

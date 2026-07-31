# Java 依赖升级 — 决策包（boot-bom × 3.2.x）

> 仅作校验器与写法参考的样例；数值为示意，不代表任何真实仓库的解析结果。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | partial |
| decision_status | needs_choice |
| batch_implementation_gate | frozen |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | openspec/changes/dep-upgrade-2026q3/evidence/java-dependency-upgrade/exact/boot-bom__boot-3.2.x__variant-default__scope-json-netty/ |

**横幅：** 待人工确认·下一动作=提问（jackson 行）；Netty 行待补证据

## 1. 基线与假设

- 项目根路径：`/repo`
- 构建工具：Maven（多模块聚合）
- 环境前置：`java 17` / `mvn 3.9` / `python 3.12` PASS
- 主机 JDK（探测）vs 工程声明：均为 17
- JDK / Spring Boot 线：JDK 17 / Boot `3.2.x`
- 构建变体：default；批次范围：json-netty
- 入口：exact-table（精确表）
- 报告路径（解析结果）：见状态表 `report_path`
- 假设与限制：本批仅覆盖 `boot-bom` 权威层；`app-library` 层（Lucene、commons-lang）与 `platform-plugin` 层（Eureka）另批处理

## 2. 依赖清单与解析路径

| 组件 | 模块 | 当前解析版本 | 目标版本 | 方向 | 目标存在性 | 建议处置 | 推荐替代 | 替代存在性 | 依赖路径 | 有效 Owner | 权威层 | 风险 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `com.fasterxml.jackson.core:jackson-databind` | `service-api` | 2.21.2 | 2.21.4 | upgrade | yes | upgrade-owner | — | n/a | `spring-boot-starter-web` → `spring-boot-starter-json` → databind | `boot-bom`（`jackson-bom.version`） | boot-bom | PATCH / 低 |
| `io.netty:netty-*`（8 个成员，含 `netty-codec-base`、`netty-codec-compression`） | `gateway` | 4.2.15.Final | 4.1.136.Final | downgrade | no | no-viable-path | — | n/a | `spring-boot-starter-webflux` → `reactor-netty-http` → netty 家族 | `boot-bom`（`netty.version`） | boot-bom | 跨线 / 高 |

## 3. 主 Owner 决策

| Owner | 当前版本 | 目标版本 | 阶梯档位 | 兼容性证据 | 变更后预期结果 |
|---|---|---|---|---|---|
| `jackson-bom`（属性 `jackson-bom.version`） | 2.21.2 | 2.21.4 | `2-property-override` | Jackson 2.21.4 release notes（URL 待附） | 家族整体对齐，无需单包钉扎 |
| `netty.version` 属性 | 4.2.15.Final | — | — | 目标线缺失成员，暂无可行 Owner 动作 | 阻塞，不提出预期 |

## 4. 残差冲突与 Override

| 组件 | 残差证据 | 是否 Override | 兼容性 | 验证项 | 回滚 | 责任人 |
|---|---|---|---|---|---|---|
| — | 升 Owner 属性后预期无残差 | 否 | — | — | — | — |

## 5. 六层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | `service-api/**/JsonConfig.java` | 事实：自定义 `ObjectMapper` 与 `JsonFormat` 注解 | 无需改动，PATCH 区间无 API 变更 | 低 |
| 配置 | `application.yml` | 事实：无 Jackson 定制属性 | 不适用 | 低 |
| 数据 | 持久化 JSON 列 | 推断：PATCH 不改默认序列化形状 | 抽样比对 | 低 |
| 接口 | 对外 JSON 契约 | 推断：日期/枚举/未知字段序列化行为不变 | 契约测试覆盖 | 低 |
| 测试 | `service-api/src/test/**/JsonContractTest.java` | 事实：已覆盖序列化行为 | 复用现有用例 | 低 |
| 部署 | `gateway` 容器镜像 | 事实：Netty 行阻塞，暂不评估 | 不适用 | — |

## 6. 风险与 SemVer 分类

| 组件 | 分类 | 说明 | 上游链接 |
|---|---|---|---|
| `com.fasterxml.jackson.core:jackson-databind` | PATCH | 同 minor 修复区间 | https://github.com/FasterXML/jackson-databind |
| `io.netty:netty-*` | NON_SEMVER | 4.2→4.1 实为降线；两个成员在 4.1 线未发布 | https://github.com/netty/netty |

## 7. 确认队列

| 组件 | 状态 | 问题 | 选项 |
|---|---|---|---|
| `com.fasterxml.jackson.core:jackson-databind` | ready | 是否按 Owner 属性（`upgrade-owner`）把 Jackson 家族升至 2.21.4？ | `proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4` / `defer` / `other` |
| `io.netty:netty-*` | blocked | 显式降级至 4.1.136.Final，但成员返回 404，目标不可达 | 重述目标 / `other` |

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|
| 构建/静态 | `mvn -pl service-api clean verify`；重复类检查 | 通过、无重复类 | 待执行（实施阶段） |
| JSON | `JsonContractTest` 全量 | 日期/枚举/未知字段行为不变 | 已定位用例 |
| API 差异 | `japicmp` 对比 2.21.2 → 2.21.4 | 无影响本仓调用的签名变更 | 待执行 |
| 冒烟 | health + 关键下单链路 | 正常 | 待执行 |

受影响测试范围：`service-api/src/test/**/JsonContractTest.java`

## 9. 回滚与责任人

| 组件 | 触发条件 | 恢复目标（精确版本/配置） | 责任人 |
|---|---|---|---|
| `com.fasterxml.jackson.core:jackson-databind` | 契约测试失败或线上 JSON 反序列化错误率上升 | 恢复属性 `jackson-bom.version` 至 2.21.2 | 平台组 |
| `io.netty:netty-*` | 不适用（未实施） | — | 网关组 |

## 10. 未决问题与证据缺口

- `io.netty:netty-codec-base` 与 `netty-codec-compression` 目标版探测为 HTTP 404；已搜替代：同 GAV 在 4.1.136.Final 无上述成员发布；跨族「相近制品」不得静默替换 → `no-viable-path`，确认队列 `blocked`（不得答人工 `defer`）。
- Jackson 2.21.4 release notes 直链待补，当前仅有仓库地址。

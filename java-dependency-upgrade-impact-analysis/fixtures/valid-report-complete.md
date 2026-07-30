# Java 依赖升级 — 决策包（boot-bom × 3.2.x）

> 仅作校验器与写法参考的定稿样例；数值为示意。对应「Jackson 已 proceed、Netty 仍 blocked」后的
> `analysis_status=complete` 状态（实现门保持 frozen）。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | complete |
| decision_status | decided |
| batch_implementation_gate | frozen |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | openspec/changes/dep-upgrade-2026q3/evidence/java-dependency-upgrade/exact/boot-bom__boot-3.2.x/ |

**横幅：** 分析已定稿；Netty 行仍 blocked，整批实施门 frozen

## 1. 基线与假设

- 项目根路径：`/repo`
- 构建工具：Maven（多模块聚合）
- 环境前置：`java 17` / `mvn 3.9` / `python 3.12` PASS
- 主机 JDK（探测）vs 工程声明：均为 17
- JDK / Spring Boot 线：JDK 17 / Boot `3.2.x`
- 入口：exact-table（精确表）
- 报告路径（解析结果）：见状态表 `report_path`
- 假设与限制：本批仅覆盖 `boot-bom` 权威层；人工已确认 Jackson `proceed`；Netty 目标仍不可达

## 2. 依赖清单与解析路径

| 组件 | 模块 | 当前解析版本 | 目标版本 | 目标存在性 | 建议处置 | 依赖路径 | 有效 Owner | 权威层 | 风险 |
|---|---|---|---|---|---|---|---|---|---|
| `com.fasterxml.jackson.core:jackson-databind` | `service-api` | 2.21.2 | 2.21.4 | yes | upgrade-owner | `spring-boot-starter-web` → `spring-boot-starter-json` → databind | `boot-bom`（`jackson-bom.version`） | boot-bom | PATCH / 低 |
| `io.netty:netty-*`（8 个成员，含 `netty-codec-base`、`netty-codec-compression`） | `gateway` | 4.2.15.Final | 4.1.136.Final | no | defer | `spring-boot-starter-webflux` → `reactor-netty-http` → netty 家族 | `boot-bom`（`netty.version`） | boot-bom | 跨线 / 高 |

## 3. 主 Owner 决策

| Owner | 当前版本 | 目标版本 | 阶梯档位 | 兼容性证据 | 变更后预期结果 |
|---|---|---|---|---|---|
| `jackson-bom`（属性 `jackson-bom.version`） | 2.21.2 | 2.21.4 | `2-property-override` | https://github.com/FasterXML/jackson-databind/releases | 家族整体对齐，无需单包钉扎 |
| `netty.version` 属性 | 4.2.15.Final | — | — | 目标线缺失成员，暂无可行 Owner 动作 | 阻塞，不提出预期 |

## 4. 残差冲突与 Override

| 组件 | 残差证据 | 是否 Override | 兼容性 | 验证项 | 回滚 | 责任人 |
|---|---|---|---|---|---|---|
| — | 升 Owner 属性后预期无残差 | 否 | — | — | — | — |

## 5. 六层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | `service-api/**/JsonConfig.java` | 事实：自定义 `ObjectMapper` 与 `JsonFormat` 注解 | 无需改动，PATCH 区间无 API 变更 | 低 |
| 接口 | 对外 JSON 契约 | 推断：日期/枚举/未知字段序列化行为不变 | 契约测试覆盖 | 低 |
| 测试 | `service-api/src/test/**/JsonContractTest.java` | 事实：已覆盖序列化行为 | 复用现有用例 | 低 |
| 部署 | `gateway` 容器镜像 | 事实：Netty 行阻塞，暂不评估 | — | — |

## 6. 风险与 SemVer 分类

| 组件 | 分类 | 说明 | 上游链接 |
|---|---|---|---|
| `com.fasterxml.jackson.core:jackson-databind` | PATCH | 同 minor 修复区间 | https://github.com/FasterXML/jackson-databind |
| `io.netty:netty-*` | NON_SEMVER | 4.2→4.1 实为降线；两个成员在 4.1 线未发布 | https://github.com/netty/netty |

## 7. 确认队列

| 组件 | 状态 | 问题 | 选项 |
|---|---|---|---|
| `com.fasterxml.jackson.core:jackson-databind` | decided | 已确认：`proceed:com.fasterxml.jackson.core:jackson-databind:2.21.4`（upgrade-owner / `jackson-bom.version`） | — |
| `io.netty:netty-*` | blocked | `netty-codec-base` / `netty-codec-compression` 在 4.1.136.Final 返回 404，目标不可达 | 待用户重述目标后再进队列 |

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

- `io.netty:netty-codec-base` 与 `netty-codec-compression` 目标版探测为 HTTP 404；`maven-metadata.xml` 显示两者仅发布于 4.2.x 线。清单「建议处置=defer」=分析义暂无可行路径；队列仍为 `blocked`。需用户**重述可达目标**（或经 `other` follow-up 放弃本行）后方可解冻实施门；**不得**对存在性 `blocked` 行直接答 `defer`。
- Jackson 行已人工 `proceed`；本包 `analysis_status=complete`，但 `batch_implementation_gate=frozen` 直至 Netty 行不再为证据型 `blocked`。

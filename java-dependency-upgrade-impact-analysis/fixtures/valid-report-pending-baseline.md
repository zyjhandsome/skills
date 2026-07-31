# Java 依赖升级 — 决策包（platform-plugin × 2023.0.x，Eureka 降级·pending baseline）

> 样例：显式降级目标可达，但 `resolved_from` 尚未用 tree 证实 → 队列 `pending`（可行·待补证）。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | partial |
| decision_status | needs_choice |
| batch_implementation_gate | frozen |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | openspec/changes/dep-upgrade-2026q3/evidence/java-dependency-upgrade/exact/platform-plugin__boot-3.2.x__variant-default__scope-eureka/ |

**横幅：** 待补基线证据；下一动作=补证清单（非降级否决）

## 1. 基线与假设

- 项目根路径：`/repo`
- 构建工具：Maven（wrapper graded pass；本会话尚未跑 leaf tree）
- 环境前置：`java 17` / `./mvnw 3.9` / `python 3.12` PASS；`build_tool_source=wrapper`
- 主机 JDK（探测）vs 工程声明：均为 17
- JDK / Spring Boot 线：JDK 17 / Boot `3.2.x`；Cloud 列车示意 `2023.0.x`
- 构建变体：default；批次范围：eureka
- 入口：exact-table（精确表）
- 报告路径（解析结果）：见状态表 `report_path`
- 假设与限制：目标 `2.0.5` Central 可达；表称 `from=2.0.6` 待 tree 证实；本波禁止 `proceed`

## 2. 依赖清单与解析路径

| 组件 | 模块 | 当前解析版本 | 目标版本 | 方向 | 目标存在性 | 建议处置 | 推荐替代 | 替代存在性 | 依赖路径 | 有效 Owner | 权威层 | 风险 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `com.netflix.eureka:eureka-client` | `discovery` | 2.0.6（declared；resolved 待证） | 2.0.5 | downgrade | yes | move-introducer | — | n/a | `spring-cloud-starter-netflix-eureka-client` → `eureka-client`（示意） | `imported-bom`（Spring Cloud） | platform-plugin | 降级 / 高 |

## 3. 主 Owner 决策

| Owner | 当前版本 | 目标版本 | 阶梯档位 | 兼容性证据 | 变更后预期结果 |
|---|---|---|---|---|---|
| Spring Cloud BOM / eureka starter | 列车待 tree 证实 | 收敛传递至 2.0.5 | `1-owner-bump`（待证） | 目标叶子 GA 存在；introducer 收敛证据待补 | 基线证实后再定 Owner 档 |

## 4. 残差冲突与 Override

| 组件 | 残差证据 | 是否 Override | 兼容性 | 验证项 | 回滚 | 责任人 |
|---|---|---|---|---|---|---|
| — | 基线未证实，暂不评估 force-align | 否 | — | — | — | — |

## 5. 六层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | `discovery/**` | 推断：注册/续约客户端调用面 | 基线证实后对照 changelog | 高 |
| 配置 | `application.yml` | 事实：存在 eureka.client.* | 配置冒烟 | 中 |
| 数据 | — | 不适用 | — | — |
| 接口 | 服务发现契约 | 推断：降级可能影响续约/注册语义 | 契约回归 | 高 |
| 测试 | `discovery/src/test` | 事实：有 `@SpringBootTest` 注册测 | 复用 | 中 |
| 部署 | 注册中心联调 | 推断：需联调窗口 | 预发冒烟 | 高 |

## 6. 风险与 SemVer 分类

| 组件 | 分类 | 说明 | 上游链接 |
|---|---|---|---|
| `com.netflix.eureka:eureka-client` | NON_SEMVER | 显式降级 2.0.6→2.0.5；High scrutiny | https://github.com/Netflix/eureka |

## 7. 确认队列

| 组件 | 状态 | 问题 | 选项 |
|---|---|---|---|
| `com.netflix.eureka:eureka-client` | pending | **降级**可行·**待补证**：目标 2.0.5 存在，但 `resolved_from=2.0.6` 尚未 tree 证实。是否恢复 `./mvnw` 并同意 `-pl discovery -am dependency:tree -Dincludes=com.netflix.eureka:eureka-client`？（补证清单见 §10；证实前不发 `proceed`） | `defer` / `other` |

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|
| 解析 | leaf `dependency:tree` + list 复核 | `resolved_from=2.0.6` | 待执行（补证） |
| 注册 | 续约/摘除冒烟 | 正常 | 待基线后 |

受影响测试范围：`discovery/src/test/**`

## 9. 回滚与责任人

| 组件 | 触发条件 | 恢复目标（精确版本/配置） | 责任人 |
|---|---|---|---|
| `com.netflix.eureka:eureka-client` | 注册失败或续约异常 | 恢复 introducer/BOM 至降级前解析树 | 平台组 |

## 10. 未决问题与证据缺口

- 有序补证清单：① 确认 `JAVA_HOME`/wrapper；② `mvn -pl discovery -am dependency:tree -Dincludes=com.netflix.eureka:eureka-client`；③ list/effective-pom 复核 `resolved_from`；④ 一致后再生为 `ready` 并附路径菜单（A move-introducer / B force-align / C–E 换 starter·换栈·原生改造）。
- 缺降级业务动机：记入证据缺口，不否决分析。

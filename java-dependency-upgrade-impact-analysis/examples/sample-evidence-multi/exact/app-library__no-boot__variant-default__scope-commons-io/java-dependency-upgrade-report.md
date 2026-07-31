# Java 依赖升级 — 决策包（app-library × no-boot，unused→remove）

> 样例：直接依赖 unused，表虽给了 `to` 仍推荐 `remove`。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | partial |
| decision_status | needs_choice |
| batch_implementation_gate | frozen |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | openspec/changes/dep-upgrade-2026q3/evidence/java-dependency-upgrade/exact/app-library__no-boot__variant-default__scope-commons-io/ |

**横幅：** 待人工确认·下一动作=提问

## 1. 基线与假设

- 项目根路径：`/repo`
- 构建工具：Maven
- 环境前置：`java 17` / `mvn 3.9` / `python 3.12` PASS
- 主机 JDK（探测）vs 工程声明：均为 17
- JDK / Spring Boot 线：JDK 17 / 无 Boot
- 入口：exact-table
- 报告路径（解析结果）：见状态表 `report_path`
- 构建变体：default；批次范围：commons-io
- 假设与限制：单组件 remove 样例；安全的 `dependency:analyze-only` 与调用点证据一致显示 unused

## 2. 依赖清单与解析路径

| 组件 | 模块 | 当前解析版本 | 目标版本 | 方向 | 目标存在性 | 建议处置 | 推荐替代 | 替代存在性 | 依赖路径 | 有效 Owner | 权威层 | 风险 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `commons-io:commons-io` | `tools` | 2.11.0 | 2.16.1 | unknown | n/a | remove | — | n/a | 直接声明 | `direct` | app-library | PATCH / 低（建议删除） |

## 3. 主 Owner 决策

| Owner | 当前版本 | 目标版本 | 阶梯档位 | 兼容性证据 | 变更后预期结果 |
|---|---|---|---|---|---|
| — | — | — | — | unused 直接依赖，不走 Owner 升级 | 删除声明 |

## 4. 残差冲突与 Override

| 组件 | 残差证据 | 是否 Override | 兼容性 | 验证项 | 回滚 | 责任人 |
|---|---|---|---|---|---|---|
| — | 无 | 否 | — | — | — | — |

## 5. 六层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | `tools/src/main/java` | 事实：无 `org.apache.commons.io` import | 删除依赖声明 | 低 |
| 配置 | — | 不适用 | — | — |
| 数据 | — | 不适用 | — | — |
| 接口 | — | 不适用 | — | — |
| 测试 | `tools/src/test` | 事实：无相关用例 | 回归编译 | 低 |
| 部署 | — | 不适用 | — | — |

## 6. 风险与 SemVer 分类

| 组件 | 分类 | 说明 | 上游链接 |
|---|---|---|---|
| `commons-io:commons-io` | PATCH | 表请求升级；分析建议 remove | https://github.com/apache/commons-io |

## 7. 确认队列

| 组件 | 状态 | 问题 | 选项 |
|---|---|---|---|
| `commons-io:commons-io` | ready | 表请求升至 2.16.1，但 analyze-only + 调用点证据为 unused；是否 `remove`？ | `remove` / `defer` / `other` |

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|
| 构建/静态 | `mvn -pl tools clean verify` | 通过 | 待执行 |

受影响测试范围：空 — 存在验证缺口（无直接引用用例）

## 9. 回滚与责任人

| 组件 | 触发条件 | 恢复目标（精确版本/配置） | 责任人 |
|---|---|---|---|
| `commons-io:commons-io` | 删除后出现 CNFE | 恢复直接声明 `commons-io:commons-io:2.11.0` | 工具组 |

## 10. 未决问题与证据缺口

- 等待人工在 remove / defer / other 中选择。

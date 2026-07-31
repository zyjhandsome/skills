# Java 依赖升级 — 决策包（app-library × no-boot，commons-lang replace）

> 样例：`commons-lang` → `commons-lang3` 坐标替换；保留请求目标与推荐替代。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | partial |
| decision_status | needs_choice |
| batch_implementation_gate | frozen |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | openspec/changes/dep-upgrade-2026q3/evidence/java-dependency-upgrade/exact/app-library__no-boot__variant-default__scope-commons-lang__domain-commons-lang-major/ |

**横幅：** 待人工确认·下一动作=提问

## 1. 基线与假设

- 项目根路径：`/repo`
- 构建工具：Maven
- 环境前置：`java 17` / `mvn 3.9` / `python 3.12` PASS
- 主机 JDK（探测）vs 工程声明：均为 17
- JDK / Spring Boot 线：JDK 17 / 无 Boot
- 构建变体：default；批次范围：commons-lang
- 入口：exact-table
- 报告路径（解析结果）：见状态表 `report_path`
- 假设与限制：`decision_domain=commons-lang-major`；仅描述 OpenRewrite recipe，不执行

## 2. 依赖清单与解析路径

| 组件 | 模块 | 当前解析版本 | 目标版本 | 方向 | 目标存在性 | 建议处置 | 推荐替代 | 替代存在性 | 依赖路径 | 有效 Owner | 权威层 | 风险 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `commons-lang:commons-lang` | `legacy-utils` | 2.6 | 3.20.0 | unknown | no | replace-component | `org.apache.commons:commons-lang3:3.20.0` | yes | 直接声明 | `direct` | app-library | MAJOR / 高 |

## 3. 主 Owner 决策

| Owner | 当前版本 | 目标版本 | 阶梯档位 | 兼容性证据 | 变更后预期结果 |
|---|---|---|---|---|---|
| — | — | — | — | 坐标/包名三重变更，非 Owner 属性可解 | 替换组件 |

## 4. 残差冲突与 Override

| 组件 | 残差证据 | 是否 Override | 兼容性 | 验证项 | 回滚 | 责任人 |
|---|---|---|---|---|---|---|
| — | 不适用（replace） | 否 | — | — | — | — |

## 5. 六层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | `legacy-utils/**/*.java` | 事实：大量 `org.apache.commons.lang.` import | 包名迁至 `org.apache.commons.lang3` | 高 |
| 配置 | — | 不适用 | — | — |
| 数据 | — | 不适用 | — | — |
| 接口 | — | 不适用 | — | — |
| 测试 | `legacy-utils/src/test` | 事实：字符串工具单测 | 同步改 import | 中 |
| 部署 | — | 不适用 | — | — |

## 6. 风险与 SemVer 分类

| 组件 | 分类 | 说明 | 上游链接 |
|---|---|---|---|
| `commons-lang:commons-lang` | MAJOR | groupId/artifactId/package 均变 | https://github.com/apache/commons-lang |

## 7. 确认队列

| 组件 | 状态 | 问题 | 选项 |
|---|---|---|---|
| `commons-lang:commons-lang` | ready | 原坐标目标 3.20.0 不存在；是否替换为 `commons-lang3:3.20.0`？ | `replace:org.apache.commons:commons-lang3:3.20.0` / `defer` / `other` |

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|
| 构建/静态 | `mvn -pl legacy-utils clean verify` | 通过 | 待执行 |
| API 差异 | japicmp / 手工对照 StringUtils | 无意外删除调用 | 待执行 |

受影响测试范围：`legacy-utils/src/test/**`

## 9. 回滚与责任人

| 组件 | 触发条件 | 恢复目标（精确版本/配置） | 责任人 |
|---|---|---|---|
| `commons-lang:commons-lang` | 编译或行为回归 | 恢复 `commons-lang:commons-lang:2.6` | 业务组 |

## 10. 未决问题与证据缺口

- 实施期可选用 OpenRewrite `commons-lang.MigrateCommonsLangToCommonsLang3`（仅命名，本阶段不执行）；残余风险：自定义包装类与反射。

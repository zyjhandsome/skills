# Java 依赖升级 — 决策包（boot-bom × 3.2.x，choose-alternative 同 GAV）

> 样例：请求目标版本不存在；已验证同 GAV 其他 GA → `choose-alternative`。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | partial |
| decision_status | needs_choice |
| batch_implementation_gate | frozen |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | openspec/changes/dep-upgrade-2026q3/evidence/java-dependency-upgrade/exact/boot-bom__boot-3.2.x__variant-default__scope-yaml/ |

**横幅：** 待人工确认·下一动作=提问

## 1. 基线与假设

- 项目根路径：`/repo`
- 构建工具：Maven
- 环境前置：`java 17` / `mvn 3.9` / `python 3.12` PASS
- 主机 JDK（探测）vs 工程声明：均为 17
- JDK / Spring Boot 线：JDK 17 / Boot `3.2.x`
- 构建变体：default；批次范围：yaml
- 入口：exact-table
- 报告路径（解析结果）：见状态表 `report_path`
- 假设与限制：请求 `2.3.999` 未发布；已验证同 GAV `2.2` 可达

## 2. 依赖清单与解析路径

| 组件 | 模块 | 当前解析版本 | 目标版本 | 方向 | 目标存在性 | 建议处置 | 推荐替代 | 替代存在性 | 依赖路径 | 有效 Owner | 权威层 | 风险 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `org.yaml:snakeyaml` | `service-api` | 2.0 | 2.3.999 | upgrade | no | choose-alternative | `org.yaml:snakeyaml:2.2` | yes | `spring-boot-starter` → snakeyaml | `boot-bom`（`snakeyaml.version`） | boot-bom | SECURITY / 中 |

## 3. 主 Owner 决策

| Owner | 当前版本 | 目标版本 | 阶梯档位 | 兼容性证据 | 变更后预期结果 |
|---|---|---|---|---|---|
| Boot BOM / `snakeyaml.version` | 2.0 | 2.2 | `2-property-override` | 请求 2.3.999 404；2.2 已验证 | 属性对齐至 2.2 |

## 4. 残差冲突与 Override

| 组件 | 残差证据 | 是否 Override | 兼容性 | 验证项 | 回滚 | 责任人 |
|---|---|---|---|---|---|---|
| — | 升 Owner 属性后预期无残差 | 否 | — | — | — | — |

## 5. 六层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | — | 推断：无直接 SnakeYAML API | 无 | 低 |
| 配置 | `application.yml` | 事实：YAML 配置加载 | 抽样启动 | 中 |
| 数据 | — | 不适用 | — | — |
| 接口 | — | 不适用 | — | — |
| 测试 | `service-api/src/test` | 事实：配置绑定测 | 复用 | 低 |
| 部署 | — | 不适用 | — | — |

## 6. 风险与 SemVer 分类

| 组件 | 分类 | 说明 | 上游链接 |
|---|---|---|---|
| `org.yaml:snakeyaml` | SECURITY | 请求目标不存在；推荐同 GAV 安全 GA | https://bitbucket.org/snakeyaml/snakeyaml |

## 7. 确认队列

| 组件 | 状态 | 问题 | 选项 |
|---|---|---|---|
| `org.yaml:snakeyaml` | ready | 请求 2.3.999 不存在；是否改用已验证同 GAV `2.2`（`choose-alternative`）？ | `proceed:org.yaml:snakeyaml:2.2` / `defer` / `other` |

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|
| 启动 | 配置绑定冒烟 | 正常 | 待执行 |

受影响测试范围：`service-api/src/test/**`

## 9. 回滚与责任人

| 组件 | 触发条件 | 恢复目标（精确版本/配置） | 责任人 |
|---|---|---|---|
| `org.yaml:snakeyaml` | 配置加载失败 | 恢复 `snakeyaml.version=2.0` | 平台组 |

## 10. 未决问题与证据缺口

- 已搜替代：`2.3.999` 404；同 GAV `2.2` Central 200；无坐标变更候选。

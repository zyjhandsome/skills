# Java 依赖升级 — 决策包（boot-bom × 3.2.x，CVE open-target）

> 样例：CVE 入口仅有 GAV、无 `to`；推荐 GA 修复版本后等人选定。

## 状态

| 字段 | 取值 |
|---|---|
| analysis_status | partial |
| decision_status | needs_choice |
| batch_implementation_gate | frozen |
| behavior_parity_required | yes |
| network_mode | online |
| report_path | openspec/changes/dep-upgrade-2026q3/evidence/java-dependency-upgrade/open-target/boot-bom__boot-3.2.x__variant-default__scope-yaml/ |

**横幅：** 待人工确认·下一动作=提问

## 1. 基线与假设

- 项目根路径：`/repo`
- 构建工具：Maven
- 环境前置：`java 17` / `mvn 3.9` / `python 3.12` PASS
- 主机 JDK（探测）vs 工程声明：均为 17
- JDK / Spring Boot 线：JDK 17 / Boot `3.2.x`
- 入口：cve / open-target
- 报告路径（解析结果）：见状态表 `report_path`
- 构建变体：default；批次范围：yaml
- 假设与限制：禁止 Agent 自动选定版本；须 `proceed:g:a:v`

## 2. 依赖清单与解析路径

| 组件 | 模块 | 当前解析版本 | 目标版本 | 方向 | 目标存在性 | 建议处置 | 推荐替代 | 替代存在性 | 依赖路径 | 有效 Owner | 权威层 | 风险 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `org.yaml:snakeyaml` | `service-api` | 2.0 | 2.2 | upgrade | yes | upgrade-owner | — | n/a | `spring-boot-starter` → snakeyaml | `boot-bom` | boot-bom | SECURITY / 高 |

## 3. 主 Owner 决策

| Owner | 当前版本 | 目标版本 | 阶梯档位 | 兼容性证据 | 变更后预期结果 |
|---|---|---|---|---|---|
| Boot BOM / `snakeyaml.version`（若存在） | 2.0 | 2.2 | `2-property-override` | GHSA 修复说明（URL 待附） | 对齐安全基线 |

## 4. 残差冲突与 Override

| 组件 | 残差证据 | 是否 Override | 兼容性 | 验证项 | 回滚 | 责任人 |
|---|---|---|---|---|---|---|
| — | 升 Owner 后预期无残差 | 否 | — | — | — | — |

## 5. 六层影响分析

| 层级 | 文件/模块 | 事实或推断 | 所需变更（仅描述，不实施） | 风险 |
|---|---|---|---|---|
| 代码 | — | 推断：无直接 SnakeYAML API 调用 | 无代码改动 | 低 |
| 配置 | `application.yml` | 事实：存在 YAML 配置 | 启动加载冒烟 | 中 |
| 数据 | — | 不适用 | — | — |
| 接口 | — | 不适用 | — | — |
| 测试 | 配置绑定测试 | 事实：有 `@SpringBootTest` | 复用 | 低 |
| 部署 | — | 不适用 | — | — |

## 6. 风险与 SemVer 分类

| 组件 | 分类 | 说明 | 上游链接 |
|---|---|---|---|
| `org.yaml:snakeyaml` | SECURITY | CVE 驱动；推荐 GA 2.2 | https://bitbucket.org/snakeyaml/snakeyaml |

## 7. 确认队列

| 组件 | 状态 | 问题 | 选项 |
|---|---|---|---|
| `org.yaml:snakeyaml` | ready | CVE 无 `to`；官方修复 GA 区间含 2.2。是否 `proceed:org.yaml:snakeyaml:2.2`（upgrade-owner）？ | `proceed:org.yaml:snakeyaml:2.2` / `defer` / `other` |

## 8. 验证矩阵

| 范围 | 测试项 | 预期结果 | 证据状态 |
|---|---|---|---|
| 启动 | 应用上下文加载 | 通过 | 待执行 |
| 配置 | YAML 绑定冒烟 | 通过 | 待执行 |

受影响测试范围：配置绑定相关 `@SpringBootTest`

## 9. 回滚与责任人

| 组件 | 触发条件 | 恢复目标（精确版本/配置） | 责任人 |
|---|---|---|---|
| `org.yaml:snakeyaml` | 启动失败 | 恢复 BOM 属性/管理版本至 2.0 | 平台组 |

## 10. 未决问题与证据缺口

- GHSA 公告直链待补；版本 2.2 为推荐而非自动选定。

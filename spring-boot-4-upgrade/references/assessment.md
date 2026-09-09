# 盘点与版本决策

## 版本来源不能靠一次文本搜索确定

| 构建形态 | 要追到的控制位置 | 解析证据 |
|---|---|---|
| Maven Boot parent | parent 版本，含本地/远端父链及属性 | 各升级模块 effective-pom、dependency:tree |
| Maven 企业 parent + Boot BOM | 真正导入 BOM 的父模块/属性，profile、BOM 顺序、覆盖项 | 与 CI 相同 profile 的 effective-pom 和依赖树 |
| Maven 混合 reactor | 应用、公共库、独立父 POM、嵌套 reactor 的归属 | 从正确聚合根解析；不能仅看根 artifact 的版本 |
| Gradle | settings pluginManagement、Boot plugin、platform/enforcedPlatform、version catalog、convention plugin、buildSrc、included build、resolutionStrategy、constraints 和 locks | 对实际应用子项目做 dependencies/dependencyInsight |
| 独立公共 starter | 它的 BOM/parent、自动配置 API 和消费方版本范围 | producer 构建与代表性 consumer 的上下文测试 |

分开记录：`declared_version`、`resolved_version`、`version_owner`、`profile/configuration`、`evidence`。静态解析不能求出继承属性/动态 Gradle 逻辑时填 unknown；不能把文件中第一个 `3.x` 当成生效 Boot 版本。Boot BOM 的范围不等于某个不受其管理的第三方组件受到支持。

## 最小盘点清单

- 仓库路径、HEAD、用户现有变更、应用/库模块、依赖边和当前构建入口。
- Boot parent/BOM/plugin；Java runtime、toolchain、release/source/target；Maven/Gradle wrapper；Kotlin compiler/plugins（若有）。CI、Docker/buildpack/Jib、运行容器和外部 WAR 部署要求。
- 已使用的 Cloud/Alibaba、springdoc、MyBatis/MyBatis-Plus、Dubbo、Resilience4j、Querydsl、MapStruct、Lombok、数据库驱动及私有 SDK/starter。这里是检查候选，不是固定依赖升级清单。
- Jackson mapper/customizer、HTTP 与 Kafka/Redis/session 等序列化、Security filter chains、JPA/Hibernate、Flyway/Liquibase、Web MVC/WebFlux、Actuator、日志/tracing、AOT/native。
- 配置作用域：主配置、profiles、测试内联属性、环境变量、Helm/K8s/Compose、CI、配置中心；只收集键名、位置和相关脱敏值。
- 测试引擎、Surefire/Failsafe 或 Gradle test suites、自定义 integrationTest、Testcontainers/Docker；已有测试数量、跳过数量和 profile。

在缺少真实仓库时只提供可行性、待盘点项和 Skill；不要虚构某家企业组件可用、测试已通过或工期。

## 路线判定

1. 精确确认起点。3.0–3.4 先审阅跨过的 3.x release notes，落到最新 3.5.x；3.5 已是执行时最新补丁则省略重复 bump，仍完成预备检查。
2. 精确确认目标。用户给 minor 则在该 minor 内选择已核实 GA；仅给 4.x 时评估 4.0 迁移落点、最终 minor 的支持周期和企业基线，记录选择。源版本已经高于指定目标时指出这是降级，不按升级默默执行。
3. 从**目标版本页面**取得 Java/Framework/构建工具要求。Boot 4.0 的基线是 Java 17、Maven 3.6.3+、Gradle 8.14+ 的 8.x 或 9.x；工具插件可能要求更高版本。Kotlin/native 项目另核实 Kotlin 2.2+、GraalVM 25+ 等要求。这不是要求把 JVM 应用统一改成 Java 25。
4. 按中间与最终阶段分别确认生态支持；不要用支持 Boot 3.5 的 Cloud train 在 Boot 4 上关闭兼容性检查来“修复”。截至核验日，官方表列 2025.0.x 对应 Boot 3.5，2025.1.x 对应 4.0，2025.1.2 起还支持 4.1；执行时重新查表，不能推导不存在的 2026.0 train。
5. 比较源/目标 BOM 和实际依赖树，找出显式覆盖、仲裁冲突、同一框架的跨 major 混用。优先改 parent/BOM/property/引入方；只有确有证据需要偏离 BOM 时才加局部覆盖，并记录原因和验证。

## 兼容决策表

每个实际使用的关键第三方/私有组件写一行：

| 组件与模块 | 当前解析版本及来源 | 目标候选 | 官方证据/日期 | 实际调用/配置位置 | 处置 | 验证 | 状态 |
|---|---|---|---|---|---|---|---|

处置：升级引入方、使用兼容版本、迁移 API、替换（需符合用户范围）、限时桥接、阻塞。状态：confirmed / tested-only / unknown / incompatible。无公开矩阵的私有 starter，可检查可用源/字节码依赖和自动配置声明，并在目标 consumer 运行上下文及关键功能测试；仍缺资料则报告 unknown，不声明官方支持。

“没有 Boot 4 兼容版本”是组件层阻塞，不是增加多个 `force`、排除全部传递依赖或删除业务功能的理由。

## 前后基线

记录 wrapper 命令、工作目录、JDK、profile、外部设施和测试结果。原始基线失败可继续诊断或做独立的方案工作；区分原有失败、本次失败、环境不可用。不得把未验证阶段称为成功，也不要为了掩盖失败删测试、降低断言、改成永久跳过。

来源：[Boot 4.0 迁移指南](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)、[Boot 4.0 安装要求](https://docs.spring.io/spring-boot/4.0/installing.html)、[Spring Cloud 兼容矩阵](https://spring.io/projects/spring-cloud/)。

# 兼容迁移与行为检查

按实际依赖和调用证据选择下面的检查项；本表是风险导航，不是全仓替换表。API、包和 starter 坐标以目标版本官方文档/可解析 artifact 为准；过时文档与实际目标不符时记录差异。

## 模块化、构建和运行环境

Boot 4.0 改为按技术拆分模块。主代码、自动配置和测试 API 可能需要对应模块；只在编译路径补一个旧 autoconfigure jar 会造成混合栈。

检查生产与测试依赖是否与实际功能匹配：MVC 的 `spring-boot-starter-web` 在 Boot 4 已废弃，应按官方迁移表换为 `spring-boot-starter-webmvc`，MVC 测试使用对应 `spring-boot-starter-webmvc-test`；旧 starter 尚存不代表必须等待编译失败才迁移。数据库迁移工具检查 `spring-boot-starter-flyway` / `spring-boot-starter-liquibase`；Security 测试检查 `spring-boot-starter-security-test`。以官方表核对其他技术，不由 artifact 字符串猜全部坐标。旧 starter 的 deprecated 与 removed 区分处理。

自动配置类迁移必须核对目标类存在及必要依赖，同时检查 `@Import`、exclude 字符串、`AutoConfiguration.imports`、条件注解和私有 starter。不要对整个 `org.springframework.boot.autoconfigure` 前缀一刀切。

目标中已迁移/删除的 Boot 3 API（如旧 `org.springframework.boot.web.embedded.tomcat` 下的类）仍能编译时，先反查提供该类的实际 jar 和 classpath，而不是据此认定迁移正确；是否移包以该具体类的目标版本为准，不把所有旧前缀一律判错。

Servlet 基线为 6.1，Boot 4.0 不支持 Undertow。发现 Undertow 或老外置容器时，评估已有授权是否允许切换到支持的 Tomcat/Jetty/运行平台，并验证定制 handler、线程、连接、HTTP 配置；必须保留旧容器则阻塞，不偷换成能编译的组合。JVM 可执行 jar 保留 `java -jar`；检查依赖旧内嵌 Unix 启动脚本的服务启动配置。

## Jackson：先保护数据契约

Boot 4 首选 Jackson 3。它更换多数 artifact/package 命名，但 **`com.fasterxml.jackson.annotation` 与 jackson-annotations 仍保留**；其他模块里的注解不一定保留。第三方 SDK 内部仍依赖 Jackson 2 也不自动构成错误，需确认隔离和实际边界，禁止把全部 `com.fasterxml.jackson` 替换或删除。[Jackson 3 官方变更](https://github.com/FasterXML/jackson/wiki/Jackson-Release-3.0)

逐项检查自定义 ObjectMapper/JsonMapper、builder/customizer、module、serializer/deserializer、mixin、异常捕获、HTTP converter、Redis/session/Kafka 等。Mapper 构建/不可变性及格式专用 mapper 会影响旧的覆盖方式；不能仅修 imports。以目标 Boot 自动配置验证实际注入和真正处理请求的 mapper。

迁移前保留脱敏的输入与输出样本，覆盖字段名/大小写、日期时区、null/空值、枚举、数值精度、未知字段、多态、错误响应；新旧版本双向读取缓存、session、事件历史数据。Jackson 2 兼容默认选项不等于启用 Jackson 2 引擎，也不保证全部行为相同。

**已观察到的配方漏项**：旧 mapper visibility 配置可能被转换为目标 Jackson 3 不接受的 `.visibility(...)`。核对实际目标 Javadoc，用 `changeDefaultVisibility(v -> ...)` 等目标 API 表达原配置，并检查字段暴露范围不变；不可简单扩大为所有字段 ANY。参见 [MapperBuilder API](https://javadoc.io/static/tools.jackson.core/jackson-databind/3.0.0/tools.jackson.databind/tools/jackson/databind/cfg/MapperBuilder.html)。配方版本不同，覆盖也可能不同，此项是检查线索而非每次必改。

## OpenAPI 与生成代码（命中时）

检查 generator 的精确版本、generatorName/library、模板与输出目录。生成 `javax.validation` 时先修生成配置，例如所用版本支持的 `useJakartaEe=true`；若支持 `useSpringBoot3`/`useSpringBoot4` 等组合选项，核实其隐含设置后选择，不能把最新版选项写到旧插件。清除可再生成的输出并重新生成、编译，不能只改 target/build 里的 Java 文件。[Spring generator 官方选项](https://openapi-generator.tech/docs/generators/spring/)

`jackson-databind-nullable:0.2.8` 只是 Petclinic 试点采用的版本，不是通用 Jackson 3 修复版本；其 [v0.2.8 POM](https://github.com/OpenAPITools/jackson-databind-nullable/blob/v0.2.8/pom.xml) 仍依赖 Jackson 2。核对目标 artifact 的实际支持、module 注册和生产 mapper；检查 missing / explicit null / value 三态的序列化、反序列化、校验及 PATCH 行为。依赖存在且普通 GET 通过不证明该路径有效；不要通过关闭 nullable 或改模型类型绕过三态语义。

桥接仅在确有组件阻塞时考虑：核实目标版本的 `spring-boot-jackson2` 与 `spring.jackson2.*` 配置、相关 HTTP/消息集成选择；证明正确 mapper 参与工作并登记退出条件。不能只增加依赖就宣称桥接有效。

## Spring Security

在 3.5 阶段按 Security 6.5 预备指南修正配置，进入 7 后核查 Lambda DSL、`authorizeHttpRequests`、matcher、授权 API、method security、OAuth/OIDC/SAML 和 session 序列化。[6.5 配置准备](https://docs.spring.io/spring-security/reference/6.5/migration-7/configuration.html)、[Security 7 变化](https://docs.spring.io/spring-security/reference/7.0/whats-new.html)

用原有策略建立允许与拒绝两组断言：匿名、普通用户、管理员、跨租户、过期/无效 token，路径边界和 method security；浏览器应用另测 CSRF/CORS、登录退出与 session。不得靠 `permitAll`、全局关闭 CSRF 或关闭 Cloud 兼容校验来通过测试。旧 AccessDecisionManager/Voter 需要迁移或目标支持的桥接时，同样记录与验收授权语义。

## 测试与 Framework API

检查目标测试模块和包。`@MockBean` / `@SpyBean` 转向 Framework 的 `org.springframework.test.context.bean.override.mockito.MockitoBean` / `MockitoSpyBean` 时核对字段/类型层级声明、bean 名、qualifier、上下文层次、spy 对已有 bean 的要求；不是改名即可保持语义。重新确认测试 slice 和自动配置 HTTP 测试客户端，避免因上下文缩小漏测安全/JSON。

JUnit、Testcontainers、Mockito、Surefire/Failsafe、Gradle test suites 以目标 BOM 与官方迁移说明为准。JUnit major 不意味着所有 `org.junit.jupiter` 包都要改名；Testcontainers 模块或 Java package 变化要核对实际目标，Docker 不可用则不能把容器测试记为通过。

Framework 7/Kotlin 中检查 JSpecify nullability、HTTP 路径匹配、validation、反射参数名、缓存/事务代理与自定义 Spring 内部扩展。保留 `-parameters` 等已有编译契约，不把所有 `javax.*` 都替成 Jakarta（例如 JDK 的 `javax.sql`）。新增 Framework 功能不在默认升级范围内。

## 数据库、持久化与批处理

先查目标 Boot BOM 实际管理的 Hibernate/Spring Data/Flyway/Liquibase/驱动版本，不把某个 4.0.0 的依赖快照写死到全部 4.x。查对应版本的 [Hibernate 迁移指南](https://hibernate.org/orm/documentation/)。

测试实体映射、命名、主键/sequence、HQL/JPQL/native SQL、分页排序、时间类型、懒加载、锁和事务回滚；对真实数据库类型做隔离集成测试，H2 通过不代表生产数据库方言兼容。Flyway/Liquibase 需确认自动配置仍生效、已有迁移校验和不变。不得修改历史 SQL 校验和或对生产自动执行 DDL 来“修好启动”。

**旧 Hibernate 扩展**：Framework 7 仅将部分原 `org.springframework.orm.hibernate5` 能力继续到 `orm.jpa.hibernate`，不是整个包迁名。[Framework 7 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes)。遇到 `hibernate5.support.OpenSessionInViewFilter` 不可直接机械删除：先确认是否只是无用 import，还是已注册 filter/实际负责 session 生命周期。后者需评估 JPA 对应集成或服务层事务与取数方案，并验证懒加载、连接生命周期、SQL 次数及写入回滚；修改应保持既有语义。普通 GET 全绿不覆盖所有懒加载路径。

Batch/Modulith 仅在使用时查独立迁移文档与 schema 要求；不作为所有仓库必选项。数据库 schema 升级应提供独立方案，先用可丢弃实例验证，并说明旧应用能否读新 schema。

## 消息、缓存与服务间兼容

对实际 Kafka/AMQP/Pulsar/Redis 集成检查 Spring 层与 client 层目标版本、配置键、序列化、重试、幂等、事务、消费确认和死信处理。[Spring Kafka 版本变化](https://docs.spring.io/spring-kafka/reference/appendix/change-history.html)

测试“旧 producer → 新 consumer”和“新 producer → 旧 consumer”，尤其 type headers、JSON 类型名、时区/枚举、异常处理。客户端升级不等于获得升级 broker 集群的授权，也不能从 Boot 版本推断生产 broker 必须同步到同名 major。测试 broker 替换不证明生产混跑兼容。

Cloud 的 Config/Gateway/OpenFeign/服务发现与自有 RPC 按各组件的官方兼容矩阵联动处理。Spring Cloud Alibaba、Dubbo 或私有扩展需要独立证据，不能由 Spring Cloud 主项目的矩阵推导兼容。

## 配置与可观测性

综合检查属性重命名、删除和默认值变化，包含部署环境变量与外部配置键。`spring-boot-properties-migrator` 仅辅助启动诊断，不能覆盖所有语义变化，完成后移除并复测。

确认 Actuator 实际暴露与访问控制、健康组/探针、端口/path、指标标签、trace propagation 和日志格式。保留原有监控协议和仪表盘输入；无必要不把原有 Brave/Zipkin 等整套替换为 OTel。指标不再产生或 trace 丢失是行为回归，即使 health 正常。

## AOT/native 和更高 4.x minor（按需）

原项目已使用或用户指定时，验证目标 GraalVM/native build tools、反射/资源 hints、代理、容器基础镜像和 native 制品启动；JVM 测试成功不代表 native 成功。普通 JVM 升级不新增 native 任务。

目标高于 4.0 时逐 minor 查 release notes，重新核实支持矩阵、兼容桥、配置变化和目标 BOM。4.0 迁移完成不能替代 4.1 或后续版本的验证。

模块、配置及桥接基准：[Boot 4.0 官方迁移指南](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)。其他官方入口见 [sources.md](sources.md)，按命中项读取目标版本文档。

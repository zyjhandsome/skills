# 官方资料与核验策略

初次整理日期：2026-09-09。链接可能重定向到新版本，进入后核对页面版本；如果变成 SNAPSHOT/预览版/其他 minor，不将它当作当前目标说明。

## 每次执行先核实

| 目的 | 首选来源 |
|---|---|
| 3.5 准备与 4.0 重大迁移 | [Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide) |
| 跨过的 3.x / 4.x release notes | [Boot Wiki](https://github.com/spring-projects/spring-boot/wiki)、[4.1 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes) |
| GA 与补丁变更 | [Boot Releases](https://github.com/spring-projects/spring-boot/releases)；用户示例 [v4.0.8](https://github.com/spring-projects/spring-boot/releases/tag/v4.0.8) 已验证为正式发布，仅作示例不永久固定 |
| 支持周期 | [Boot 项目支持信息](https://spring.io/projects/spring-boot#support)、[Supported Versions](https://github.com/spring-projects/spring-boot/wiki/Supported-Versions) |
| 目标工具链与运行环境 | [Boot 4.0 系统要求](https://docs.spring.io/spring-boot/4.0/system-requirements.html)、[4.0 安装要求](https://docs.spring.io/spring-boot/4.0/installing.html)；其他 minor 改用对应页面 |
| BOM 管理版本 | [3.5 dependency versions](https://docs.spring.io/spring-boot/3.5/appendix/dependency-versions/coordinates.html)、[4.0 dependency versions](https://docs.spring.io/spring-boot/4.0/appendix/dependency-versions/coordinates.html)，并以精确 artifact 的 POM 和实际解析树复核 |
| Cloud 兼容矩阵 | [Spring Cloud 项目页](https://spring.io/projects/spring-cloud/)、[Supported Versions](https://github.com/spring-cloud/spring-cloud-release/wiki/Supported-Versions) |

## 命中相关技术时读取

| 技术 | 来源 |
|---|---|
| Spring Framework | [Framework Wiki 升级入口](https://github.com/spring-projects/spring-framework/wiki)；从入口定位目标版本，不假定旧 wiki 子路径仍有效 |
| Jackson | [Jackson 3 Release](https://github.com/FasterXML/jackson/wiki/Jackson-Release-3.0)、[Jackson 3 Migration](https://github.com/FasterXML/jackson/wiki/Jackson-3.0-Migration-Guide) |
| Security | [6.5 → 7 配置准备](https://docs.spring.io/spring-security/reference/6.5/migration-7/configuration.html)、[7.0 What's New](https://docs.spring.io/spring-security/reference/7.0/whats-new.html)、[7.0 Servlet Migrations](https://docs.spring.io/spring-security/reference/7.0/migration/servlet/index.html) |
| Hibernate | [ORM Documentation](https://hibernate.org/orm/documentation/)，选择目标 BOM 实际对应版本 |
| Kafka | [Spring Kafka Change History](https://docs.spring.io/spring-kafka/reference/appendix/change-history.html) |
| 测试与容器 | [Boot Reference](https://docs.spring.io/spring-boot/4.0/reference/index.html)、[JUnit Guide](https://docs.junit.org/current/user-guide/)、[Testcontainers Releases](https://github.com/testcontainers/testcontainers-java/releases) |
| springdoc | [官方兼容问答](https://springdoc.org/#what-is-the-compatibility-matrix-of-springdoc-openapi-with-spring-boot) |
| OpenAPI 生成与 nullable | [Spring generator 选项](https://openapi-generator.tech/docs/generators/spring/)、[nullable v0.2.8 POM](https://github.com/OpenAPITools/jackson-databind-nullable/blob/v0.2.8/pom.xml)，按具体 generator/artifact 版本核对 Jakarta、Jackson 和三态 |
| Jackson mapper 定制 | [Jackson 3 MapperBuilder](https://javadoc.io/static/tools.jackson.core/jackson-databind/3.0.0/tools.jackson.databind/tools/jackson/databind/cfg/MapperBuilder.html)，核对实际目标版本 |
| Jackson 配置绑定与变化 | [Customize the Jackson JsonMapper](https://docs.spring.io/spring-boot/how-to/spring-mvc.html#howto.spring-mvc.customize-jackson-objectmapper)、[Boot 4.0 Configuration Changelog](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Configuration-Changelog)、[4.0 配置附录](https://docs.spring.io/spring-boot/4.0/appendix/application-properties/index.html)；默认文档可能展示新 minor，须与目标 jar 的配置元数据/枚举及自动配置实现交叉核对 |
| 私有/其他第三方 | 组件自己维护的发布记录、兼容矩阵、源码和可重现 consumer 验证；没有来源就记 unknown |
| Maven 管理与实际解析 | [Dependency Mechanism](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html)、[Dependency Tree JSON 格式](https://maven.apache.org/plugins/maven-dependency-plugin/examples/tree-mojo.html)；区分继承、显式管理、BOM import 与最终选中节点 |

## OpenRewrite

- [4.0 Community recipe](https://docs.openrewrite.org/recipes/java/spring/boot4/upgradespringboot_4_0-community-edition)：核对 recipe ID、组合定义、坐标和分发要求。
- [Maven Plugin](https://docs.openrewrite.org/reference/rewrite-maven-plugin)、[Gradle Plugin](https://docs.openrewrite.org/reference/gradle-plugin-configuration)：核对目标/任务、补丁路径、参数。
- [rewrite-spring 源码](https://github.com/openrewrite/rewrite-spring)：在实际使用版本/tag 查 recipe；不能以主分支源码证明旧 artifact 已包含它。
- 固定版本分发实例：[Central rewrite-spring 6.37.1 POM](https://repo.maven.apache.org/maven2/org/openrewrite/recipe/rewrite-spring/6.37.1/rewrite-spring-6.37.1.pom)、[Central Maven 插件 6.46.1 POM](https://repo.maven.apache.org/maven2/org/openrewrite/maven/rewrite-maven-plugin/6.46.1/rewrite-maven-plugin-6.46.1.pom)，2026-09-09 HTTP 200；不代表其他版本来源相同。

## 取证约定

记录 URL、页面版本、核验日期、对应结论；artifact 解析记录准确坐标。优先官方资料与目标源码，社区经验只用于发现待检查项。网页不可读取时可用官方仓库或已有可信文档快照交叉核实；不足则说明未知，不猜版本/类名/recipe。

如果官方当前信息推翻本 Skill 的表格，采用官方资料，记录修正；用户指定版本不因文档默认展示更新版本而改变。

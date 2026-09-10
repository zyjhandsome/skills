# 验收与回退

## 证据规则

每次实际执行记录：时间、仓库 HEAD/变更范围、cwd、命令、JDK/wrapper、profile/configuration、脱敏环境说明、退出码、测试数/失败/跳过、制品和报告路径。标准输出不是唯一证据，应读 Surefire/Failsafe/JUnit XML 或 Gradle test report，核对是否真的执行了预期测试。

验证记录只在对应代码快照和环境内有效。代码、依赖、配置或 wrapper 改变后重新执行受影响检查；不得把旧报告当成当前成功。将长日志存到用户指定证据目录或仓库既有文档位置，最终答复概括结果。

交付时提供可发现的证据索引：报告、原始解析树、测试报告、脱敏启动/契约日志的路径及对应快照。优先使用项目既有位置，否则可用 `upgrade-evidence/`；允许仓外受控持久目录或 CI 制品，不强制同目录或提交日志。临时目录可作中转，交付前将需保留证据归档，核对可读取性并记录哈希/保留期限（适用时）；不能只留下即将清理的临时路径。复盘先按索引查找，未找到应写“当前未取得证据”，不能推断从未执行。

命令记录中的密钥/口令用占位符，保留安全注入方式以便复跑。优先使用既有秘密管理或受保护的本地注入；`-D`/命令行可能暴露于进程参数和历史，环境变量也不天然保密。确需临时配置文件时限制权限、不纳入 Git/报告并用后清理；不要求用户把真实密钥贴进对话，不回显解密值。已暴露的凭证按组织规则处理轮换。

## verified 的判定条件

只有以下条件**同时满足**才报告 `verified`：

1. 精确目标 Boot 通过下述核心解析检查，记录与最终代码快照一致。**Boot 3/4 混栈禁止 verified 和 verified-with-bridges**，不能用“已解释”或桥接登记豁免。
2. 预先明确的模块、profile、JDK/runtime、数据库和功能验收范围内，完整构建、真实测试、制品启动或库 consumer 及关键契约均通过。有未执行的必需项则为 `implemented-unverified`；不能在失败后把它改成“不适用”。测试跳过须解释且证明必需覆盖仍在。
3. 原有与新增失败已归因，范围内无未解决的必需验证失败；测试数变少有合理说明；skipTests、空 patch 和单一 health 响应不构成通过证据。
4. `spring-boot-properties-migrator` 和本次临时 rewrite 配置已清理，并对清理后的快照复测；兼容桥全部退出。桥保留且其他条件满足时用 `verified-with-bridges`。
5. 报告列出已验证范围、范围外事项及回退点。**无 Boot Jackson 2 桥不等于依赖树无 Jackson 2**，合法共存需解释实际 mapper/模块使用边界。
6. [依赖漏洞检查](dependency-security.md) 的最终安全门通过：有可比较的源/目标证据、最终制品扫描与策略结论，覆盖实际交付范围。扫描不可用不算零漏洞；兼容桥、漏洞总数下降或测试全绿均不能豁免阻断项。有效安全例外单独登记，不当作兼容桥或零风险。

验证默认内存数据库、security=false 的四条 GET，可支持“这些路径的 JSON/HTTP 行为一致”，不能证明 MySQL/Postgres、生产鉴权、写入/事务或懒加载路径不变。若它们属于约定必需范围，未验证就不能把全仓状态设为 verified；若试点范围已明确排除，可写 `verified（仅该范围）` 并列明限制。编译目标 17、运行 JDK 21 的测试不能称为已在 JDK 17 runtime 验证。

JSON 比较默认忽略对象键顺序，保留数组顺序、缺失/null、类型与数值含义；存在签名、字节级缓存或文本消费者时，对象序列化顺序也须作为契约检查。

结构化辅助见 [evidence-contract.md](evidence-contract.md)。判定依据是实际证据，不能仅填写 `passed`。

**启动里程碑不是启动通过**：端口监听、Root WebApplicationContext 初始化日志、个别自动配置加载、未出现 LinkageError，只能列作局部观察。应用还须完成必要初始化、达到可用状态并通过范围内真实请求/任务验证；出现后续启动失败，即使可归因于外部网络，也不能通过 runtime 检查或取得任一种 verified。启动事件先后见 [官方生命周期说明](https://docs.spring.io/spring-boot/reference/features/spring-application.html#features.spring-application.application-events-and-listeners)。库 consumer 的局部上下文测试也不能冒充完整应用启动。

启动中断时记录首个失败点及已确认触达的路径；依据配置、条件和日志列出**未触达或无法确认触达的关键 Bean/SDK 路径**，包括 lazy/profile/首次请求触发项。不要凭日志先后臆造完整 Bean 实例化顺序。对其中高风险 SDK 补 [字节码检查](binary-compatibility.md) 或隔离 consumer 测试：隔离无关外部设施，保留真实 SDK 及其配置/调用，不能把被测 SDK 自身 mock 掉后称已验证。无法补测就登记准确缺口；恢复环境后仍须完成最终制品启动与路径验证。

`environmentPrepared`/配置中心等早期失败不提供后续业务 Bean/SDK 兼容证据。部署续跑按当前制品、环境和范围重新判定状态，不继承上一轮 verified/verified-with-bridges 标签；若旧结论所需证据实际未通过，应在报告中更正。可复用快照和条件仍一致的已通过检查，但新环境、桥接改动和新触达路径须补验。

**核心解析检查（两种 verified 状态共用）**：对每个应用模块/profile 的完整实际依赖树，确认 `org.springframework.boot:spring-boot` 与 `spring-boot-autoconfigure` 的 **jar** 精确版本等于目标，且 compile/runtime/provided/system 和测试路径上所有实际选中的 `org.springframework.boot:spring-boot*` 都对齐目标；`webmvc:4.0.7`、属性或 imported BOM 不能证明 core 为 4.0.7。忽略被仲裁淘汰的旧候选，不能忽略仍被选中的旧模块。库用真实 consumer 验证，聚合 POM 不冒充应用证据；特殊应用确不使用 autoconfigure 时需说明结构并人工核验，不伪造该坐标。

tree 通过后仍检查打包制品/容器实际加载的依赖，留意 provided 容器库、手工/shaded jar；插件自身依赖与应用 classpath 分开判断。Tomcat、Framework 等第三方依赖按目标 Boot BOM/支持矩阵核对，不能要求其版本号也等于 Boot 4.0.7。运行验证不可因失败而改成不适用；若任务仅授权静态评估则报告 assessed，不把缺少应用启动证据包装成 verified-with-bridges。

## 最低验收矩阵（按实际范围执行）

| 层次 | 必需证据 | 适用边界 |
|---|---|---|
| 依赖与工具链 | 中间/最终 Boot 实际解析值、BOM 与插件控制位置、runtime/test trees，无未经解释的框架 major 混用 | 所有构建单元 |
| 依赖安全 | 源/目标漏洞差异、最终组件/制品扫描、工具与数据库标识、适用性及准入结论 | 所有迁移；镜像/外置运行依赖按实际部署范围，测试/构建依赖另列风险 |
| 构建 | 生产与测试源码编译、完整 verify/build、预期 jar/war/库制品 | 所有；聚合模块不要求启动 |
| 测试执行 | 原有测试与有必要的迁移回归测试；总数/失败/跳过前后比较 | 零测试项目要说明并补关键验收，不能把 0 个通过等同有覆盖 |
| 应用启动 | 隔离配置下目标制品启动、必要 bean/迁移工具初始化、真实请求 | 可运行应用；启动前检查外部写入副作用 |
| 库/starter | 代表性 Boot 4 consumer 上下文、自动配置与核心调用 | 公共模块；不要求不存在的 main 类 |
| 业务契约 | JSON/HTTP 状态与错误、鉴权正负例、关键读写/事务；消息/缓存双向兼容 | 以仓库实际能力选择并说明不适用理由 |
| 部署与监控 | 已有制品或镜像构建、支持的 Java/容器、health/readiness、关键日志/指标 | 实际部署形态；本地构建不等于部署 |
| native | native 编译、制品启动和关键路径 | 仅已有或用户指定 native 项目 |

一次 `/actuator/health` 200 不能覆盖路由、序列化、认证、SQL 或消息处理；路径/端口/访问策略也应来自项目配置，而不是硬编码 localhost:8080。

选择已有构建策略：Maven 要确认 Failsafe 的 integration-test/verify 绑定及 profiles；Gradle 要确认自定义 integrationTest 等任务是否被 check/build 包含。测试重命名或引擎变化后测试数突然减少必须解释，不因为命令返回 0 就忽略。

移除迁移器、本次临时 rewrite 配置后完成最终验证。桥接若保留，必须单独验收，并以 `verified-with-bridges` 报告。临时扫描残留只当线索；保留 `com.fasterxml.jackson.annotation`、第三方隔离的 Jackson 2、`javax.sql` 不能直接算失败。

## 离线配置绑定预检

migrate 命中属性改名、枚举/Map 键变化或自定义绑定时，把配置预检列入适用验收。尤其完整启动被外部设施截断时，继续完成不依赖它们的绑定检查，不能把“无法连库”当作不检查本地配置的理由。已有对应快照、profile 和绑定对象的成功测试可复用；不能绑定/无法取得配置则保留缺口，不阻止独立实施，但不得通过相关验收。

1. 清点实际配置输入：application/bootstrap 的 YAML/properties、多文档及 profile、环境变量、命令行、部署模板、spring.config.import 和可取得的外部键。按实际优先级、占位符与激活条件形成测试输入，记录来源/版本和不可取得项；新旧名称是不同键，不能假定高优先级的新名称会遮盖低优先级的旧名称。
2. 用目标 jar 的配置元数据、属性类型及实际枚举核对；metadata 不列每个 Map 子键，也不覆盖所有自定义绑定。区分未知键、非法枚举名/值和合法但不生效的配置；沿用 Binder 的 relaxed binding，不用简单大写/字符串白名单替代。
3. 在不启动完整应用的测试中，将这些有效输入绑定到目标 `@ConfigurationProperties` 类型；例如 Binder + JacksonProperties，或只加载所需自动配置的 ApplicationContextRunner。**ApplicationContextRunner 不会自动加载 application.yml**，必须显式提供实际配置输入；不加载完整应用再假定排除 DataSource 就不会触发远程调用。选择直接 Binder 时若有自定义转换器/校验/绑定处理器，须补充或用隔离上下文还原，不能把裸 Binder 通过外推到完整绑定行为。
4. 断言确实加载了预期键且值正确，不能只用空输入、bindOrCreate 的默认对象或“未抛异常”过关。对确认有绑定问题的改名/枚举迁移，覆盖原始坏输入失败与修正输入成功；存在跨来源新旧键时补共存用例。输入只手填修正后的示例，不能证明仓内 YAML、模板或配置中心已修复。
5. 对存在行为影响的配置，用目标自动配置及本仓相关 customizer/module 创建实际 mapper/必要 bean，验证日期、时区、精度等契约。**绑定成功 ≠ 配置已生效 ≠ 应用可用**；仅实例化 bean 不等于绑定过目标输入。输出记录放入 tests/contracts 或已有检查记录，写清离线范围；外部配置责任方、准确键名和部署复跑动作仍需交付。

下例用于已有 Java 测试方法，`effectiveProperties` 必须是实际加载的有效输入 Map；仅演示已确定应保持 true 的日期契约，其他项目按自己的预期断言。使用目标 Boot/Jackson 依赖，无需为此引入另一套测试框架：

```java
var source = new org.springframework.boot.context.properties.source.MapConfigurationPropertySource(effectiveProperties);
var properties = new org.springframework.boot.context.properties.bind.Binder(source)
    .bind("spring.jackson", org.springframework.boot.context.properties.bind.Bindable.of(
        org.springframework.boot.jackson.autoconfigure.JacksonProperties.class))
    .orElseThrow(() -> new AssertionError("Expected Jackson configuration was not loaded"));
if (!Boolean.TRUE.equals(properties.getDatatype().getDatetime().get(
        tools.jackson.databind.cfg.DateTimeFeature.WRITE_DATES_AS_TIMESTAMPS))) {
    throw new AssertionError("Expected timestamp setting was not bound");
}
```

未启用功能的残留键先核对消费方与激活条件：例如非法 cache type 或已无元数据的 session 键，不能仅因文本存在就断言当前启动必失败，也不能假定永远无效（自定义组件可能读取）。登记适用条件及处置，不为验证残留键擅自启用功能。零测试应用可先补这类小范围预检，仍不能替代必需的运行与业务验收。

## 失败归因与状态

- 编译/依赖：明确哪个模块、坐标、版本来源和错误，先处理 owner/引入方再处理调用点。
- 运行链接/类初始化：`IncompatibleClassChangeError`（含其子类 NoSuchMethodError、AbstractMethodError 等）、`NoClassDefFoundError` 先追首个异常、调用方及被调用类的实际 jar/ClassLoader，再按 [二进制检查与处置](binary-compatibility.md) 核对。ICCE 可涉及接口实现/类层次或静态性变化，并非仅“类不再实现接口”；已确认类型契约或签名失配不能靠盲重试修复。NoClassDefFoundError 也可能源于缺包、加载隔离或此前静态初始化失败，不能仅凭异常名认定 SDK 引用已删 API。[JVM 链接与初始化规则](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html)
- 测试回归：比较原始基线，检查契约/默认值变化；修正实现而非削弱断言。
- 环境不可用：私服认证、网络、Docker、JDK、外部服务不可用，记录所缺资源和准确复跑命令。需要区分环境与回归时，对已授权测试端点做有界 DNS/TCP/TLS/HTTP 探测，并在相同 profile、端点和环境下对照未改基线（可行时）。相同连接失败支持环境归因，但不排除失败点之后尚未触发的迁移问题，也不能记为启动通过。可继续不依赖它的编辑/验证；已有实现但缺必需验收用 implemented-unverified，关键前置条件阻止推进则用 blocked。
- 关键组件不兼容：保留最后可用阶段，记录替代方案或升级依赖的解除条件，不盲目重试相同 recipe。

推荐针对关键序列化/鉴权行为做小范围反例验证，证明测试确实会捕获差异；仅在价值明确且成本合适时使用 mutation testing，不把全量 mutation testing 作为所有仓库的前置条件。

## 回退记录

保存原始 HEAD、升级前用户差异、阶段差异/commit（若已有提交授权）、原有制品版本及配置版本。回退说明指向明确检查点；不要默认 `git reset --hard`、清理未跟踪文件或覆盖用户工作。

发布回退还要检查：新旧 API/事件是否能混跑、缓存/session 是否可读、数据库 schema 是否向后兼容。若涉及不可逆 schema 或数据格式，明确“回退 jar 不足够”，提供独立的数据恢复/前滚方案供发布流程使用，不执行生产操作。

最后交付：状态、精确源/目标、阶段摘要、改动链接、执行的验证及覆盖范围、未验证项、桥接登记、回退点。项目接入 CI/业务环境的验收若尚未执行，应如实保留。

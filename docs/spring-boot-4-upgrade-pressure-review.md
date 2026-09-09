# Spring Boot 4 Skill 压测结论复核与改进

日期：2026-09-09。结论：压测对可执行示例、阶段证据和验收范围的批评有价值，八项建议都能转化为改进，但不能将单仓修复、版本来源或成功判定原样泛化。

## 证据复核与结论边界

本次只读检查了用户提供的 `D:/Hzhao/AI_Test/springboot-v4-evidence/` 和 `D:/Hzhao/AI_Test/springboot-v4/`，没有改动该仓，也没有重新运行那一轮升级。

- 当前 15 份 Surefire XML 汇总为 tests=180、failures=0、errors=0、skipped=0；基线日志摘要也为 180/0/0/0。
- 四组保存的 owners、owner-1、vets、pets JSON 重新作语义比较，全部相等。
- 当前制品中有 `spring-boot-4.0.8.jar`，同时有 Jackson databind **3.1.5 和 2.21.5**、nullable 0.2.8；未发现 `spring-boot-jackson2`/properties-migrator。无 Boot 兼容桥与完全无 Jackson 2 是两个不同结论。
- 报告记录 runtime JDK 21.0.11、compile target 17，主烟测范围是 hsqldb/spring-data-jpa、security=false。不能据此称 JDK 17 runtime、生产数据库或启用鉴权的运行行为均已验证。
- 3.5 阶段通过、当时 recipe 执行和启动结果主要依据已有升级报告；本次没有独立重跑它们。跨阶段日志/快照应按新模板保存，不以最终 XML 倒推历史每阶段都正确。

因此“Skill 在一个真实项目上具备可行性，样本路径保持一致”合理；“全仓功能未变”范围过大。`verified` 在原有定义中本来就限定范围，此次补强为必须显式列出范围：生产鉴权、数据库等若是必需范围则未完成；若试点事先排除，可写 `verified（仅已约定范围）` 并列明限制，不能事后缩小范围以消除失败。

## 八项建议的处理

| 建议 | 判断 | 实际修改 |
|---|---|---|
| default_prompt 不要固定实施 | 采纳；UI 提示并非权限控制，但会影响默认行为 | 改成按用户意图 assess/migrate；主流程明确 assess 不执行 run/更新 wrapper/locks/写构建配置 |
| 分离 3.5/4.0 命令与硬条件 | 采纳并修正措辞 | 两段可复制 Maven 示例、显式 Gradle 阶段；进入 4.0 实际修改前需合格 3.5 快照与通过证据，人工 bump 也适用。不是“写一行表格”就通过；只读评估、发现和隔离预览不必被禁止 |
| Central 与 Code Genome 都要试 | 不照搬“双试”，采纳按坐标判定来源 | 先沿用允许的企业仓库/镜像，核实 Central，再按确切需要检查其他来源。不可用仅影响 OR 路线；保留手工迁移 |
| verified 做成谓词 | 采纳 | 具体目标、最终快照、必需范围、执行测试、启动/consumer、契约、清理和桥接状态共同判定；加入只读记录校验器 |
| 补四类配方漏项 | 按条件采纳 | generator Jakarta 选项与重新生成；Jackson Builder 目标 API；Hibernate 扩展分类与 session 语义；明确 web starter 已废弃、应迁移到 webmvc |
| Gradle 不暗示根 build | 采纳 | 分开定位版本 owner 和插件/task owner；catalog/convention/included build 的处理；不默认选 4.0 recipe |
| 最小夹具与禁止命令列表 | 采纳夹具/契约测试，改进黑名单思路 | 原创 MVC 3.4 夹具 + 17 个可运行记录契约测试 + 前向场景。禁止的是越界行为和虚假验收，字符串黑名单无法覆盖别名、参数和工具调用 |
| 4.0.x 补丁路径 | 采纳 | 同 minor 补丁直接改真实 owner、核实差异并验收；不重走 3.5、不默认跨 major recipe |

## 不能原样沉淀的“修复”

**nullable 0.2.8 不等于 Jackson 3 兼容方案。** 官方该版本 POM 仍以 Jackson 2 为依赖；本次制品也证实双版本共存。应查实际 JsonNullable module/mapper 路径并验证 missing/null/value 三态，不把所有仓库统一锁成 0.2.8。[官方 POM](https://github.com/OpenAPITools/jackson-databind-nullable/blob/v0.2.8/pom.xml)

**删除 Hibernate 5 Filter 不能作为自动动作。** 无用 import 可以移除，已注册 Filter 则可能承担 session 生命周期，需验证懒加载/事务并选择有依据的替代。Framework 7 是部分 Hibernate 扩展能力迁移，不是全部包的机械改名。[官方说明](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes)

**useJakartaEe 是具体生成器/版本的配置。** 修生成配置并重新生成是通用方法；新版还有 useSpringBoot4/useJackson3 及联动选项，不能对旧 generator 套最新版参数。[官方选项](https://openapi-generator.tech/docs/generators/spring/)

**OR 组合配方附带变化需审查，不一律保留或拒绝。** 去 `@Autowired`、数据库初始化依赖、测试配置变化可能是附带整理，也可能有真实迁移原因。新增补丁表区分必需、需论证、越界项，不以配方名称或一句“best practices”决定全部接受。

**Code Genome 原文并非完全错误。** 原 Skill 已写“可能需要”、镜像/旧版本差异及人工路径；问题在“认证不可用就报告阻塞”的操作表述容易误导。此次直接核实 Central 上 6.37.1/6.46.1 POM 均 HTTP 200，修正来源判断，既不说所有版本都需要认证，也不说所有版本都在 Central。

## 本次新增验证

| 检查 | 结果 | 能证明什么 |
|---|---|---|
| skill-creator quick_validate | `Skill is valid!` | frontmatter 与基础结构 |
| Python 标准库记录契约测试 | 17 tests，全部通过 | 缺失/失败检查、assess、快照与证据哈希、跳测试、桥接、4.x 补丁误用、CLI 只读和错误退出 |
| 原创 MVC 夹具基线 | Boot 3.4.0，Maven 3.6.3，JDK 21.0.11 / release 17；`verify` 成功，4/0/0/0 | 夹具实际可编译、测试、打包；GET JSON/null/日期、404、POST 合法与非法请求 |

夹具实际工作目录：`C:/Users/zyjhandsome/AppData/Local/Temp/boot4-skill-mvc-9640851ed8574b31a44dec04bd2f911d`。测试保留在该目录 `target/surefire-reports`；Skill 内夹具保持 3.4 原始状态。没有把 Python 合成证据当作真实 Java 运行记录。

此次未运行新夹具的完整 3.5→4.0 升级或独立 Agent 前向测试，未复跑 Petclinic 的生产安全/数据库/Jib。只读证据校验器检查的是记录与文件一致性，不保证记录真实性，不执行升级，不替代 CI、业务测试或权限系统。调用方式见 [证据契约](../spring-boot-4-upgrade/references/evidence-contract.md)。

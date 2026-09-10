# Spring Boot 4 Upgrade Skill 校验记录

日期：2026-09-09。校验对象：[Skill](../spring-boot-4-upgrade/SKILL.md) 及其引用文件。

本文记录**首次创建时**的校验；后续压测修订、新增 17 项自动测试及真实 MVC 夹具基线结果见 [压测复核与改进](spring-boot-4-upgrade-pressure-review.md)，不与下方历史“未执行”混淆。

2026-09-10 增量校验：证据契约升级为 v2，26 项 Python 回归通过；Skill 结构、内部链接、JSON/YAML/XML 与 diff 检查通过。新增 managed-parent 夹具在隔离目录用 Maven 3.6.3 实际导出 effective-pom 和 Dependency Plugin 3.8.1 的 JSON tree：仅 import 4.0.7 BOM 时 core/autoconfigure 仍 3.5.14，子 POM 显式管理后为 4.0.7。新解析校验器读取两份原始树分别拒绝/接受，结果符合预期。证据目录：`C:/Users/zyjhandsome/AppData/Local/Temp/boot4-owner-fixture-15f6c610246b4b48bfb2651d444dd9e8`。此项只验证管理规则与解析检查，未执行用户业务仓库的运行时迁移；Gradle 解析分支以合成日志回归，未实跑 Gradle 项目。

2026-09-10 第二份实仓复盘修订：采用证据持久索引、局部启动与完整验收分开记录、Jackson 直接依赖/旧数据契约、Content-Type、自动配置生效及秘密/TLS 处理规则。保留五种状态和 3.5 检查点；未把网络归因视作 runtime 通过。27 项 Python 回归和 Skill 结构校验通过，新增用例覆盖两种 verified 门对 failed、unavailable、passed 但非零退出码的拒绝。六条新增 Agent 情景仅为待执行的前向用例；本轮未重新运行 V1/V2 业务仓，也未独立核验附件所述原始日志。校验器仍不解读启动日志或自动判定 readiness。

2026-09-10 部署复盘修订：新增按需读取的二进制兼容参考，明确 jdeps 的类级边界、javap 成员签名核对、启动中断后关键 SDK 覆盖、链接/初始化异常归因及同包名覆盖的例外条件；报告与四条前向情景同步补充。未加入厂商专属坐标或源码，未改主流程、状态枚举及契约校验程序。

本轮 JDK 21 工具实测：本机 spring-web 6.2.19 的 `setConnectTimeout(int)` 存在，7.0.9 不存在；两者仍有 `setConnectionRequestTimeout(int)` / `setReadTimeout(int)`。另在隔离临时目录生成无第三方依赖的旧 API、新 API、预编译 SDK 和应用：应用对新 API 编译成功，jdeps 返回 0 且无缺失类；旧 API 运行退出 0，新 API 实际调用退出 1（NoSuchMethodError），javap 找到调用方 `transport/Client.setConnectTimeout:(I)V` 而目标类无该成员。新增参考页的 jar/jdeps/javap 参数已实际运行，Skill 结构及 diff 检查通过。这是工具与链接机制验证，不是原业务 SDK、同包名覆盖部署或真实 Spring 应用验收；新增 Agent 情景尚待实跑。

2026-09-10 HttpHeaders/ICCE 增量：成员检查扩展到实际入参和类型层次；确认缺陷后扫描同一 jar 的全部有效 class，并记录命中/未覆盖路径；增加框架核心覆盖影响评估及续跑状态重新判定。未新建状态或修改 3.5/OpenRewrite 路线。

本轮使用实际 spring-web/spring-core 6.2.19 和 7.0.9、JDK 21 做隔离最小复现：旧 API 编译的调用方通过 HttpEntity(Object, MultiValueMap) 和 HttpHeaders(MultiValueMap) 传入 HttpHeaders，两条路径在目标运行时读取 isEmpty() 均触发 ICCE，旧运行时通过；javap 确认旧构造器 descriptor 和无 checkcast 的调用。JDK 21 反射调用同一构造器对外为 IllegalArgumentException，cause 为 ClassCastException。对照项：实际 MultiValueMap 入参的旧字节码在目标运行时通过；原源码针对新 API 重编译后的两条调用也通过。将两个最小调用类打包后逐类反汇编，2/2 完成。Skill 结构检查通过。以上验证类型契约与复现方法，不代表原企业 SDK、框架覆盖方案或业务部署已验收；新前向情景尚待 Agent 实跑。

2026-09-10 配置绑定复盘增量：补 Jackson DateTimeFeature 属性线索、适用范围内的离线绑定预检、手工/recipe 路径配置覆盖要求和两个前向情景。保留现有五种状态及主流程，不新增全量配置白名单或固定厂商 starter 规则。

本轮使用 Boot 4.0.8、Framework 7.0.9、Jackson 3.1.5、JDK 21，在仅注册 JacksonAutoConfiguration 的隔离上下文和直接 Binder 中做六组对照：旧 serialization 日期键失败、新 datatype.datetime 键成功、新旧键共存失败、无显式特性时 Date/Instant 为 ISO 字符串、日期键 true 加 date-format 时绑定仍为 true 但输出为字符串、非法布尔值失败。仅日期开关为 true 时 Date 为 0、Instant 为 0.0，Duration 仍为 PT2S，说明时长开关应独立核对。验证文档中的 Binder 片段已原样编译，正确输入通过、空输入被断言拒绝。未连接数据库/配置中心或加载企业 SDK；这不是用户仓库实际 YAML/profile/远端配置或业务启动的验收。Skill 结构和 diff 检查通过，新增 Agent 情景未实跑。

## 结构校验

使用 skill-creator 自带 quick_validate.py。系统默认 Python 缺少 PyYAML、venv、pip，因此改用 uv 隔离的 Python 3.12 + PyYAML，并启用 UTF-8 读取中文。未修改用户全局 Python 包。

```powershell
uv run --with PyYAML --python 3.12 python -X utf8 C:/Users/zyjhandsome/.codex/skills/.system/skill-creator/scripts/quick_validate.py C:/Users/zyjhandsome/.cursor/skills/spring-boot-4-upgrade
```

结果：退出码 0，`Skill is valid!`。另完成 10 个 Markdown 文件的 UTF-8/代码围栏检查、21 个本地链接存在性检查、UI YAML 和 JSON 模板解析、2 个 PowerShell 代码块语法解析，均通过。`git diff --check` 对已跟踪的 README 改动通过。命令模板包含执行时填写的精确版本，不据此声称 Maven/Gradle/OpenRewrite 已实际运行。

## 情景走查

以下是作者依据输入情景对指令分支进行的静态走查，不是独立 Agent 前向测试，也不是真实仓库集成测试。

| 输入情景 | 检查到的行为约束 | 位置 |
|---|---|---|
| Boot 3.2 + Java 17，希望到 4.0 | 先 3.5 独立验证，不强制 Java 25 | SKILL 路线、assessment |
| Boot 3.5 已是最新补丁 | 不重复 bump，仍做准备/基线检查 | assessment |
| 企业 parent 管理 Boot，应用 POM 没有版本 | 追版本 owner 与 effective-pom，不猜第一个字符串版本 | assessment |
| Gradle catalog + convention plugin + 多项目 | 查实际 owner、runtime/test configurations 和正确项目任务 | assessment、openrewrite |
| 私有 starter 没有 Boot 4 支持证据 | unknown/blocked；可做 consumer 验证，不用强制叶子版本掩盖 | assessment、batch |
| Boot 4.0 + Jackson annotations 和独立 Jackson 2 SDK | 保留合法注解与有依据的隔离依赖，不全局替换 | compatibility |
| 安全配置迁移后测试失败 | 验证允许/拒绝语义，禁止用 permitAll 掩盖 | compatibility、verification |
| OpenRewrite dry-run 源码未改变 | 看生成 patch 和解析覆盖，不只看 git diff | openrewrite |
| recipe artifact 无法从现有私服下载 | 核实分发/认证，可用兼容可获得版本或人工路线 | openrewrite |
| Maven 成功但 integration profile 未开/Docker 不可用 | 核对真实任务与测试数量，不能标 verified | verification |
| WAR 必须保留旧 Servlet 容器/Undertow | 不自行偷换部署约束，阻塞依赖它的阶段 | compatibility |
| 目标明确为 4.1.x | 保留 3.5/4.0 迁移检查，继续按 4.1 文档验收，不把 4.0 当最终结果 | SKILL、compatibility |
| 用户仅要求评估 | assess 只出报告，不改源码/构建/部署声明 | SKILL 入口 |
| 批次中公共 starter 阻塞，另一个独立服务可改 | 阻塞依赖消费者，独立服务继续；不报告整批成功 | batch |
| 续跑前 HEAD 或工作区变化 | 复核快照和证据，避免使用旧验证记录或重复配方 | batch、verification |

## 未完成的实际验证

尚无真实业务仓库输入，因此未做 Maven/Gradle 构建、recipe discover/dry-run/run、Spring Boot 应用启动、数据库/消息/安全契约或 native 验证。结构校验与情景走查不能证明迁移成功率。

实际落地时建议分别选一个 Maven 服务和一个 Gradle 服务，另按实际使用覆盖 Cloud/私有 starter、持久化及消息场景。用它们的失败和契约差异迭代公司专属规则，而不是扩大未经证实的自动替换清单。

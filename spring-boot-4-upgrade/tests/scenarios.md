# 最小前向测试情景

以独立副本执行，检查实际命令、差异和证据，不能用搜到指令中的关键词代替行为测试。Python 单元测试验证记录契约，以下情景用于验证 Agent 是否遵循 Skill。

| 输入 | 观察结果 |
|---|---|
| 对 MVC 夹具“只评估”，环境未装 rewrite | 只出方案/证据；POM、源码、部署、wrapper/locks 字节不变，不执行 run |
| 从 3.4 到 4.0.8，3.5 必需测试失败 | 停在 3.5 的修复/诊断；无实际 4.0 bump/run，隔离预览需明确标注 |
| 从 3.4 到 4.0.8，3.5 合格检查点存在 | 分阶段实施；每阶段保持夹具四项 HTTP/JSON/validation 断言 |
| Maven Central 提供选定 artifact，Code Genome 无凭证 | 检查已允许来源的实际解析，不因无凭证提前放弃 |
| 最终只运行 skipTests 和 health | 拒绝 verified，保留缺失必需证据 |
| 必需范围包含生产鉴权，但只测 security=false | 保持未验证，不事后排除鉴权 |
| 4.0.7 到 4.0.8 | 不降到 3.5，不重跑跨 major 配方 |
| Gradle catalog/convention/included build | 定位真实版本 owner 与任务 owner，不自动在根 build 注入 |
| Jackson2 nullable 与 Jackson3 共存 | 查 mapper 和三态契约，不自动删 Jackson2 或一律锁 0.2.8 |
| 已注册的旧 Hibernate Filter 无目标类 | 核实 session/事务替代语义，不机械删除 |
| 企业 parent 管理 core 3.5，子 import BOM 4.0 且新 webmvc 为 4.0 | 实际 tree 中旧 core/actuator 等必须阻断两种 verified；修 owner 或报告未验证/阻塞，并列执行者与下一步；不能把覆盖失败登记为桥 |
| 依赖树干净但隔离启动失败 | 不事后删 runtime 必需项；继续诊断或说明真实环境阻塞、解除条件和下一步 |
| core 已对齐、Tomcat 监听且部分上下文初始化，随后数据库连接超时；基线同样超时 | 记录局部里程碑与环境归因，runtime 未通过；不新增 context-verified 状态或给予 verified-with-bridges |
| 日志仅在临时目录，报告存于仓外既有目录 | 先查证据索引，不推断未执行；交付前归档必要证据并核对可读取性，不强制提交日志 |
| Jackson 2 API 靠无关 SDK 传递引入，只有新 serializer 自身往返测试 | 显式声明所用 API 依赖并核实 BOM；补旧字节样本与实际 serializer 契约，不把离线通过当 Redis 集成通过 |
| 旧 starter 无异常但预期 bean 不存在，jar 仅用旧 EnableAutoConfiguration 注册 | 查注册入口及条件结果；不删除 spring.factories 其他键，不统一强加厂商 Boot 4 坐标 |
| JSON 值相同，但移除旧常量后 Content-Type 不再带 charset | 检查实际编码与消费者契约；不能只凭 JSON 语义比较判定行为完全不变 |
| 企业私服证书失败且测试启动需解密口令 | 核实 CA/构建 JDK，采用限定 truststore 与受保护注入；不默认跳过 TLS 校验，不将真实口令写进命令记录或日志 |
| SDK 字节码调用已删除的方法，应用编译和 jdeps 检查均通过 | 用 javap 核对 owner/name/descriptor 和目标继承层次；触发实际调用，不把类级分析当成员链接通过 |
| 数据源先失败，SDK 在 lazy Bean 或首次请求才初始化 | 标明未触达/未知关键路径，补真实 SDK 的静态或隔离测试，环境恢复后仍验收完整制品 |
| NoClassDefFoundError 之前已有静态初始化异常 | 追首次原因及加载来源，不一律认定为删除 API 或只补 jar |
| 同包名覆盖只在 IDE 生效，部署入口加载原 SDK 类 | 桥验收失败；核对最终制品及支持入口的类加载来源，不能只凭无失效调用的覆盖类字节码通过 |
| Spring 6 编译的 SDK 将 HttpHeaders 传入旧 MultiValueMap 构造器，Spring 7 读取时 ICCE | 核对实际入参/类型关系并扫描同 jar 全部有效类；旧 API 编译、目标 API 运行复现，不用反射失败替代现场；不自动覆盖 HttpEntity，合法 MultiValueMap 命中不判错 |
| SDK 局部补丁未奏效，拟覆盖 HttpEntity；此前启动在 environmentPrepared 中断却标 verified-with-bridges | 单独评估框架覆盖及子类/消费者影响；更正旧状态，当前制品重验实际路径，不继承旧 verified 标签 |
| 配置仍有旧 serialization.write-dates-as-timestamps，启动先死在外部配置/数据源 | 离线加载实际输入并绑定目标 JacksonProperties，按原契约迁到 datatype.datetime；旧键残留不因加新键豁免，runtime 保持未通过 |
| ApplicationContextRunner 未导入实际 YAML；或时间戳键绑定 true 但 date-format 改变输出 | 断言输入加载和值，核对实际自动配置 mapper 的输出；不能以空输入/绑定通过宣称配置生效，不盲加 customizer |
| 升级后漏洞总数下降，但新增一条适用 Critical；扫描退出 0 | 逐组件/公告对比并执行策略判定；未处置前拒绝两种 verified，不把退出码或总数当安全结论 |
| 组件版本未变，数据库刷新后多报一个 CVE | 尽可能用相同数据库复扫源/目标，区分新披露与升级引入；仍按当前准入规则处置 |
| 扫描超时或数据库不可用，报告为空；或制品包含未识别私有 jar | 保留失败/识别缺口并补证据，不计零漏洞；缺少 dependency_security 或从 scope 删除它也不能通过契约 |
| 切换企业 parent 后丢失旧安全覆盖；拟逐个 force 最新叶子版本 | 核对原修复与目标 BOM，优先相容 parent/SDK 或最小覆盖；复扫且做二进制/行为验证，不制造混栈 |
| Jackson 2/同包名 SDK 桥仍带漏洞，拟全包 suppression；源检查通过但最终镜像未扫 | 桥无安全豁免，核对具体路径及有效例外；补实际交付制品/镜像扫描，未完成时不 verified-with-bridges |

MVC 夹具是原创最小 Spring Boot 3.4.0 项目，不包含 Petclinic 的数据库、安全和 OpenAPI 生成器；这些分支仍需各自代表性服务或专门夹具，不能由四个 MVC 测试外推覆盖。

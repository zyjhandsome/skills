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

MVC 夹具是原创最小 Spring Boot 3.4.0 项目，不包含 Petclinic 的数据库、安全和 OpenAPI 生成器；这些分支仍需各自代表性服务或专门夹具，不能由四个 MVC 测试外推覆盖。

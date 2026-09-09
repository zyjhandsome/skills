# Spring Boot 3.x → 4.x 升级 Skill：方案与使用

调研日期：2026-09-09。适用对象：一批起点不同的 Spring Boot 3.x 存量仓库，包含低于 3.5 的版本。实现入口：[spring-boot-4-upgrade](../spring-boot-4-upgrade/SKILL.md)。

## 可行性与适用条件

可行，适合把可重复的迁移判断、执行步骤和验收要求封装成 Skill，再用 OpenRewrite 加速结构化修改。Skill 不保证任意项目自动升级成功；实际成本主要取决于第三方/私有 starter、JSON 契约、安全配置、数据访问及测试覆盖，仓库数量本身不足以估算工期。

默认路线采用官方建议的 3.5 准备阶段：较早 3.x → 最新可用 3.5.x → 4.0.x；目标是更高 4.x minor 时继续按对应 release notes 推进。不是要求每个 3.x minor 都中间发布，也不是把 4.0 永久定义为最终最佳版本。[官方迁移指南](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)

Boot 4.0 的 Java 最低要求仍为 17；Maven 要求 3.6.3+，Gradle 为 8.14+ 的 8.x 或 9.x。是否升级 Java 21/25 取决于组织基线、运行环境和插件要求，避免将其捆绑成全部仓库的必选项。[系统要求](https://docs.spring.io/spring-boot/4.0/system-requirements.html)、[安装要求](https://docs.spring.io/spring-boot/4.0/installing.html)

用户提供的 v4.0.8 已在 GitHub API 核实为 GA，发布时间为 2026-08-21；可以作为指定目标示例，但 Skill 每次运行仍要核实版本与支持状态，不能永久称它为“最新 4.x”。[v4.0.8 发布记录](https://github.com/spring-projects/spring-boot/releases/tag/v4.0.8)

## 方案比较与选择

| 方案 | 优点 | 对本批场景的限制 | 采用方式 |
|---|---|---|---|
| 纯提示词/手工改 | 无 recipe 环境依赖，能处理私有代码 | 大量重复工作，一致性和遗漏控制依赖执行者 | 作为复杂适配和工具不可用时的路径 |
| 全部依靠 OpenRewrite | 机械修改效率高，可预览补丁 | 不能证明行为兼容；配方、语言、私服和实际版本覆盖有边界 | 不作为独立完成标准 |
| Skill 编排 + OpenRewrite + 契约验证 | 保留自动化效率，支持不同起点、阻塞和续跑 | 需要每仓真实解析和测试证据 | **本次采用** |

OpenRewrite 必须固定插件、recipe artifact 和 recipe ID，先 discover/dry-run 再应用。分发按具体坐标核实：先检查已允许的企业镜像/Central 来源，必要时才检查 Code Genome 的要求，不因没有凭证就放弃已有可用版本。配方不可用时保留人工路径。[官方 recipe](https://docs.openrewrite.org/recipes/java/spring/boot4/upgradespringboot_4_0-community-edition)

## 用户提供资料的适用性

| 参考 | 实际查阅范围 | 借鉴内容 | 本次调整 |
|---|---|---|---|
| [adityamparikh/spring-boot-4-migration-skill](https://github.com/adityamparikh/spring-boot-4-migration-skill) | 当前分支 SKILL.md，未完整审计其全部脚本/引用文件 | 分技术加载、版本时效、渐进与兼容桥思路 | 聚焦 3.x 存量；不引入 2.x/新功能扩展；桥接保留独立状态；批量锁定版本 |
| [tainn03/spring-boot-java-upgrade-openrewrite](https://github.com/tainn03/spring-boot-java-upgrade-openrewrite) | 当前分支 SKILL.md | discover/dry-run/执行/验证的流程思路与 reactor 关注点 | 不采纳“95% 自动化”作为保证；不默认 Java 25；核对每个 recipe；dry-run 看生成 patch；不自动 git add/commit 全仓 |
| [springboot-skills-marketplace](https://github.com/a-pavithraa/springboot-skills-marketplace) 中 springboot-migration | 当前分支指定 SKILL.md；未执行其 scanner | 迁移前扫描、按技术模块加载和分阶段记录 | 不把 Modulith/Testcontainers 作为所有项目固定目标；加 3.5 验证点、解析版本证据和依赖图 |
| 用户给定 marketplace 固定路径 | commit API 返回 422，找不到该提交 | 无法据此复现那一快照 | 使用当前分支评估，并明确不是原链接快照 |
| [Medium 文章](https://medium.com/@roanmonteiro/migrating-microservices-to-spring-boot-4-with-claude-code-94f315060af1) | 仅公开开头，标注发表于 2026-05-23；无法读取全文 | 提出测试有效性值得关注 | 不声称阅读全文；全量 mutation testing 不作为通用门槛 |
| [Spring 官方 release](https://github.com/spring-projects/spring-boot/releases/tag/v4.0.8) | 发布记录及 GA 元数据 | 确认精确版本和补丁变化 | 配合迁移指南/BOM/第三方兼容矩阵，不能单靠 release 列表指导整个迁移 |

没有复制第三方实现脚本；本次按本地仓库需求重新编写说明、操作参考和模板。以上是资料适用性判断，不是对这些开源仓库的完整质量或安全审计。

## Skill 执行方案

1. **盘点与原始基线**：找到实际 Boot 版本 owner，解析每个相关模块的依赖；记录工具链、配置范围、测试与外部设施。区分应用、公共库和 starter。
2. **锁定版本与兼容矩阵**：每个阶段分别确认 Boot、Cloud、关键第三方及私有组件；记录 URL/日期与支持或实测状态。公共 BOM/私有 starter 不支持时不能用强制叶子版本掩盖。
3. **展示具体方案**：列出模块、预期文件、版本、阶段、命令、风险和回退点。只评估时在此结束；用户已经要求实施时继续，不额外制造逐项审批。
4. **3.5 准备阶段**：修正废弃 API 和生态组合，在 3.5 做独立验证。必要时细分 3.x 小步骤。
5. **4.x 实施**：recipe 先发现/预览/审查；修改依赖、源码、配置、测试和必要部署内容；不能要求每个互相依赖的小编辑后都立即完整编译。
6. **行为验收与清理**：解析树、完整构建、真实测试执行、制品启动/库消费者、鉴权、JSON、持久化、消息和监控；移除临时迁移器后复测。
7. **批量扩展与续跑**：基础组件优先，代表性服务试点，按依赖与技术栈分波；独立仓库可继续，阻塞消费者单独排队。

Spring Cloud 必须按官方表与具体 Boot minor 匹配；Cloud 主项目的兼容性不能自动覆盖 Alibaba 或私有扩展。[Spring Cloud 矩阵](https://spring.io/projects/spring-cloud/)

验收状态区分 assessed、blocked、implemented-unverified、verified-with-bridges、verified。存在缺失环境、漏跑测试或未退出桥接时，报告不能合并成一句“升级成功”。

## 文件与职责

| 文件 | 作用 |
|---|---|
| [SKILL.md](../spring-boot-4-upgrade/SKILL.md) | 触发范围、阶段与完成标准 |
| [assessment.md](../spring-boot-4-upgrade/references/assessment.md) | 实际版本、版本控制位置、兼容性决策 |
| [openrewrite.md](../spring-boot-4-upgrade/references/openrewrite.md) | Maven/Gradle 配置、参数、补丁检查和降级到人工处理 |
| [compatibility.md](../spring-boot-4-upgrade/references/compatibility.md) | 按技术触发的迁移与行为检查 |
| [verification.md](../spring-boot-4-upgrade/references/verification.md) | 验收证据、失败归因、回退 |
| [batch.md](../spring-boot-4-upgrade/references/batch.md) | 依赖分波、逐仓状态和恢复 |
| [sources.md](../spring-boot-4-upgrade/references/sources.md) | 官方资料入口与时效核验 |
| [migration-report.md](../spring-boot-4-upgrade/assets/migration-report.md) | 每仓报告模板 |
| [batch-manifest.json](../spring-boot-4-upgrade/assets/batch-manifest.json) | 批次记录模板，非自动执行脚本 |

第一版不加入通用正则扫描/自动改 POM 脚本：Maven 继承和 Gradle 动态逻辑需要实际构建解析，静态脚本容易误判版本。批量变更由 recipe 和 Agent 执行；对多仓中已证实重复且稳定的差异，后续再沉淀公司专属 recipe。

压测后增补了只读证据契约校验器、离线回归测试和原创 Maven MVC 3.4 夹具；它们不承担自动改 POM 或判定所有业务兼容。具体采纳与修正见 [压测结论复核](spring-boot-4-upgrade-pressure-review.md)。

与已有 `java-dependency-upgrade-impact-analysis` 区分：已有 Skill 面向依赖分析，本 Skill 面向 Boot 主版本迁移并允许实施；可复用已有分析证据，但不硬依赖或强制串联其确认队列。也不强制接入 delivery-*。

## 使用示例

仅评估：

```text
使用 spring-boot-4-upgrade，只评估，不改代码。
仓库：D:/repos/orders-service
目标：Spring Boot 4.0.x 的适用正式补丁。
先给出实际版本、3.5 过渡方案、私有 starter 兼容性和验收清单。
```

单仓实施：

```text
使用 spring-boot-4-upgrade，完成 D:/repos/orders-service 到 Spring Boot 4.0.8 的升级。
先列具体方案，再实施并验证。保留 Java 17，除非有明确兼容性要求。
不要提交或部署；输出差异、升级记录和所有未验证项。
```

批量实施：

```text
使用 spring-boot-4-upgrade，完成以下仓库的 Boot 4.x 升级：
D:/repos/platform-starter
D:/repos/orders-service
D:/repos/inventory-service
先盘点依赖关系并锁定批次版本，再按公共组件、试点、其余仓库推进。
允许本地修改和测试，不推送或部署。
证据输出：D:/upgrade-evidence/boot4-wave1
单仓阻塞时记录解除条件，继续其他独立仓库。
```

Cursor 中可按其技能调用方式使用名称；支持 `$skill` 的环境可用 `$spring-boot-4-upgrade`。此交付放在当前 Cursor skills 集合内，不额外安装到其他 Agent 的全局目录。

## 验证边界

首次创建阶段做 Skill 结构、YAML/JSON、内部文件链接及迁移场景走查，历史结果见 [校验记录](spring-boot-4-upgrade-validation.md)。后续用户提供 Petclinic 实跑证据，本次复核与增补验证见 [压测结论复核](spring-boot-4-upgrade-pressure-review.md)。各记录区分实际执行、已有证据复核与静态走查，不把单一试点外推为所有企业仓库可用。

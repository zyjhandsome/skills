# Spring Boot 4 Upgrade Skill 校验记录

日期：2026-09-09。校验对象：[Skill](../spring-boot-4-upgrade/SKILL.md) 及其引用文件。

本文记录**首次创建时**的校验；后续压测修订、新增 17 项自动测试及真实 MVC 夹具基线结果见 [压测复核与改进](spring-boot-4-upgrade-pressure-review.md)，不与下方历史“未执行”混淆。

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

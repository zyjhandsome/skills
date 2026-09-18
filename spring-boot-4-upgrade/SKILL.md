---
name: spring-boot-4-upgrade
description: Use when assessing or migrating an existing Spring Boot 3.x repository to a Spring Boot 4.x GA, or when asked for Spring Boot 4 升级、迁移、批量存量仓库改造或该迁移的评估. Not for new applications, Boot 2.x, pure Spring Framework projects, or unrelated Java dependency updates.
---

# Spring Boot 4 存量仓库升级

把现有 3.x 应用升级到执行时核实的 4.x 正式版本，保留可观察业务行为，交付代码、验证证据和剩余阻塞。用用户的语言输出。版本知识核验基准为 2026-09-09；执行时按 [官方资料索引](references/sources.md) 重查，不把本文日期或示例当作最新版本保证。

## 入口与边界

- 只要可行性或方案：做 `assess`，写证据与方案。不改业务源码、构建声明或部署配置；不为加载 recipe 写 POM/Gradle；不执行 rewrite run、wrapper/lockfile 更新。构建探测先检查副作用，记录业务/构建/部署文件前后差异。
- UI 默认提示只是入口示例，不扩大授权。
- 要求完成升级：做 `migrate`，先展示具体方案，再在已有授权内编辑与验证，不逐阶段重复索要同意。用户明确要求“方案确认后再改”时才等待。
- 多仓：同一流程逐仓，另读 [批量推进](references/batch.md)。只处理用户指定的仓库。
- 默认支持 Java/Kotlin、Maven、Gradle Groovy/Kotlin DSL。2.x 或纯 Spring Framework 先报告超出本 Skill 的起点并给出前置工作，不套用 3→4 配方。已是 4.x 只补目标 minor，避免降级或重跑 3.x。
- 保存分支、HEAD、工作区差异和模块范围；保留未提交工作。隔离用本地分支/独立 checkout；不自动清空、stash、提交全部文件或发布。
- 不自动采用 Java 25、WebFlux、虚拟线程、API versioning、新数据库或全套可观测性替换；只改升级必需部分。已有项目约束优先。

## 按阶段加载

| 何时 | 读 |
|---|---|
| 盘点、路线、发布状态 | [assessment.md](references/assessment.md)、[sources.md](references/sources.md)、[dependency-security.md](references/dependency-security.md) |
| 3.5 门、验收、回退、状态判定 | [verification.md](references/verification.md)、[evidence-contract.md](references/evidence-contract.md) |
| 机械迁移 | [openrewrite.md](references/openrewrite.md) |
| 命中的技术项 | [compatibility.md](references/compatibility.md)、[binary-compatibility.md](references/binary-compatibility.md) |
| 多仓 | [batch.md](references/batch.md) |
| 每仓记录 | [migration-report.md](assets/migration-report.md) |
| 夹具实跑 / 维护回归 | [evidence-contract.md](references/evidence-contract.md) 维护回归、[scenarios.md](tests/scenarios.md) |

## 默认路线

```text
现有 3.0–3.4 → 执行时核实的最新 3.5.x → 执行时核实的 4.0.x
现有 3.5.x  → 最新 3.5.x 准备阶段       → 4.0.x
用户目标为更高 4.x minor               → 再按各 minor 官方说明继续
```

同 minor 补丁、未指定 minor 时的 4.0 落点、精确 GA 锁定见 assessment。3.5 与 4.0 是独立验证点。

## 阶段

1. **发现升级单元** — 按 assessment 得到声明/解析/owner、工具链、兼容面、基线与漏洞基线。图索引不能替代构建解析。
2. **锁定路线并展示方案** — 按 sources 核实目标后写方案。`assess` 在此结束。
3. **3.5 准备** — 按 assessment 对齐 3.5 并做预备迁移。源为 3.x 时，未满足 verification 中「进入 4.0 的实施条件」不得对主工作树做 Boot 4 `run` 或手工升到 4。
4. **4.x 实施** — OpenRewrite 可选：先读生成补丁再应用，零 `git diff` 不能证明完成。命中项读 compatibility。混栈或覆盖失败不是桥。
5. **验证与交付** — 只按 verification 判定状态。契约校验只证明记录一致，不替代测试，也不证明守权。

## 状态与交付

最终状态只能从下表选一个；完整谓词以 [verification.md](references/verification.md) 为准，不新增枚举：

| 状态 | 含义 |
|---|---|
| assessed | 只完成评估和方案 |
| blocked | 关键兼容性或前置条件阻塞，列出解除条件 |
| implemented-unverified | 代码已改，但必需的功能或依赖安全验收未通过/证据缺失 |
| verified-with-bridges | 核心解析及适用验证全部通过，仍有明确登记的临时兼容桥；不得包含 Boot 混栈 |
| verified | 精确目标已解析，适用验证通过，无未退出的临时兼容桥 |

| 观察 | 不能据此给出的结论 |
|---|---|
| `BUILD SUCCESS`、`-DskipTests`、一次 health 200 | `verified` 或启动通过 |
| 新 starter / BOM / 属性版本 | core 已升级 |
| 端口监听或上下文初始化 | runtime 通过 |
| Boot 3/4 混栈或覆盖失败 | 兼容桥；任一种 verified |

阶段交付和最终答复固定包含：**状态 · 已验证范围 · 未完成及解除条件 · 下一步（谁／做什么）**。普通进度消息无需重复四项。未通过验证不说“已完成升级”；with-bridges 明说仍有桥及退出动作。下一步已获授权且可执行就继续，只有范围已完成、真实阻塞或需用户决策才收口；不要把“请用户再说继续”当下一步。无剩余迁移工作时写明，发布动作仅按原授权处理。`verified` 只表示记录范围内验证完成，不表示已经部署。提交、推送、PR、部署按用户授权与仓库规则执行。

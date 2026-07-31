# Java 依赖升级影响分析 × Delivery — 使用说明

> 受众：流程维护者、执行 Agent、研发负责人。  
> 基准：`java-dependency-upgrade-impact-analysis/SKILL.md` + `references/*`。  
> 语言：正文简体中文；术语、枚举、GAV、路径、命令保持英文原文。

本文件说明如何把 **分析-only** 的 Java 升级 Skill 挂到 `delivery-*` 脊柱上。  
**Skill 本身不写 OpenSpec/delivery 状态机**；状态只在 OpenSpec change 中。

小白先看动态全流程导览（与 delivery 解耦、可单独使用）：  
[`java-dependency-upgrade-impact-analysis-usage.md`](./java-dependency-upgrade-impact-analysis-usage.md) ·  
[`assets/java-dependency-upgrade-workflow.svg`](./assets/java-dependency-upgrade-workflow.svg)

---

## 0. Delivery 挂载一张图

```text
delivery-explore          整仓巡检 / 拆批 / 选定方向
        │ 挂载：本 skill（inventory 入口）+ 可选 Maven Tools MCP
        ▼
delivery-frame-spec       定框、风险路由、规格闸门
        │ 挂载：本 skill（exact 批分析 + 确认队列 → analysis_status=complete）
        ▼
delivery-plan-tasks       设计与垂直任务（仍不改依赖，除非另授权）
        ▼
delivery-execute-verify   仅在实现闸门 + 显式 go 后改 pom/代码并验证
```

蓝 = Agent/Skill 分析；黄 = 人工确认；绿 = Skill 终点（决策包定稿）；红 = 实施另授权。

---

## 1. 心智模型

| 轴 | 问题 | 典型取值 |
|---|---|---|
| `analysis_status` | 证据是否够完整？ | `partial` / `blocked`（批级环境前置/基线/离线闸） / `complete` |
| `decision_status` | 人是否已确认？ | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | 调用方可否开实施？ | `frozen` / `ready` |
| 实施授权（delivery-only） | 是否允许改构建/代码？ | 默认否；报告不能授权 |

Skill 终点 = 确认队列清空（零 `ready`）+ 决策落盘 + `analysis_status=complete`。  
**不等于** delivery 实现闸门，更不等于可以改仓库。  
心智模型 = **三状态轴**（上表前三行）+ **实施授权**（仅 delivery；本 skill 不写）。

---

## 1.1 环境前置（Environment preflight）

分析开始前（含只读扫 pom）必须按 skill `references/environment-preflight.md` 探测：

| 门闩 | 通过 | 失败 |
|---|---|---|
| JDK | PATH 上 `java -version` | batch-wide `blocked`；对话列出缺口；**不写**报告 |
| 构建工具 | 优先系统 `mvn -v` / `gradle -v`；若无则项目 `mvnw`/`gradlew -v` 为 **graded pass**（记 `build_tool_source=wrapper`） | 系统与 wrapper 皆无 → 同上硬 blocked |
| 双构建仓 | 只验选用的那套；`preflight.py` exit `6` = 先问人再 `--build-tool`（**不是**批级 blocked） | — |
| Python | `python` 或 `python3 --version`（供 `validate_report.py`） | 同上硬 blocked |
| 网络 | 同波探测；双挂 → 问人后可 offline（见 `reachability-and-upstream.md`） | **不算**工具前置失败 |

主机 JDK 与工程声明不一致：只记入假设，不挡分析。缺工具时禁止用 manifest 编造有效版本基线。

---

## 2. 工件落点

| 内容 | 位置 |
|---|---|
| Delivery 状态 / proposal / design / tasks | `openspec/changes/<id>/`（唯一状态源） |
| 升级证据与决策包 | `<change-dir>/evidence/java-dependency-upgrade/`（与前端 `evidence/frontend-dependency-upgrade/` 同构；由 skill 解析，提示词可不写） |
| 主报告 | `…/java-dependency-upgrade-report.md` |
| 模板 | skill 内 `templates/*.md`（中文表头） |
| 结构校验 | `python scripts/validate_report.py <report.md>` 或 `--evidence-dir <目录>` |
| 决策记录 | 报告同目录 `decision-records/<group>__<artifact>.md` |
| 样例决策包 | skill 内 `fixtures/valid-report*.md` 与 `examples/sample-evidence-multi/`；用单文件路径或该多批目录校验，勿对 `fixtures/` 根直接 `--evidence-dir` |

报告目录解析（与 skill `Output` / `report-contract.md` 一致）：

1. 显式 `--output-dir`（最高优先）
2. 既有 `--change-dir` → `<change-dir>/evidence/java-dependency-upgrade/`
3. 均未提供时：在分析目标仓下查找既有 `openspec/changes/<id>/`  
   - **唯一匹配** → 当作 `--change-dir` 使用  
   - **多个** → 询问用哪一个  
   - **没有** → 询问 `--change-dir` 或 `--output-dir`，**停止写入**直到明确  

**不得**在项目根 invent 临时报告目录，也**不得**自行创建 OpenSpec change。

---

## 3. 双入口如何进 Delivery

| 入口 | 谁发起 | 归一化 |
|---|---|---|
| A 整仓巡检 | `delivery-explore` | 候选清单 → 人选一个「权威层 × Boot 线 × 构建变体 × 有界范围」方向 → frame |
| B 合规精确表 | 用户/合规直接给表 | 正规化为同一候选项 → 直接或经 explore 选批 → frame |

候选项字段见 skill：`references/dual-entry-and-batching.md`。

---

## 4. 阶段 × 挂载 × 产物

| 阶段 | Delivery | 本 Skill 做什么 | 必产 |
|---|---|---|---|
| explore | delivery-explore | inventory；owner 初判；按层拆候选 | 方向地图；人选一批 |
| frame | delivery-frame-spec | 对该批跑完整 Stage A（含确认队列 + `validate_report.py` 退出码 0） | brief/spec + 定稿决策包 |
| plan | delivery-plan-tasks | 只读决策包，拆验证/回滚任务；**不实施** | design.md / tasks.md |
| execute | delivery-execute-verify | **不调用本 skill 实施**；按已批准任务改构建并验证 | 实现与验证证据 |

网络：先探测 Central/镜像与 changelog 源；双失败须人确认后再 offline（见 `reachability-and-upstream.md`）。

---

## 5. 拆批与风险路由

- 一个分析批 / 确认波 ≈ **一层权威 × 一条 Boot 线 × 一个构建变体 × 一个有界范围**（必要时再加 `decision_domain`）；一个 OpenSpec change 可承载该批，但勿把 JDK+Boot+业务库塞进同一批。  
- Quick：仅 direct + PATCH + 非 BOM/非安全/非降级（极少）。  
- Standard：默认。  
- High：BOM/Netty/Security/降级/跨线/核心路径/排除/替换组件。  
- **处置阶梯**（`treatment-ladder.md`）先于版本钉扎：  
  - Direct：`remove`（unused）→ `upgrade-self` / `upgrade-owner` → `replace-component`  
  - Transitive：`exclude`（未触达证据）→ `upgrade-introducer` / `move-introducer` → `force-align` → `replace-introducer`  
  - 目标缺失：同 GAV 替代 → `choose-alternative`；换坐标 → `replace-*`；无候选 → `no-viable-path`  
- owner-first：能升 Boot/BOM/属性则不推荐单包 override；破例须完整决策记录（见 schema）。  
- 无目标版本 / 替换路径：按**决策单元**逐个确认，禁止「全部 proceed」。  
- 生产目标默认 **GA-only**；Beta/RC/Snapshot 不得进 `ready`（除非人显式允许）。

---

## 6. 确认队列（frame 内必须做完）

- `ready`：同波列出全部 ready **决策单元**，但每个单元要有独立显式答复（`proceed:g:a:v` / `remove` / `exclude` / `replace:…` / `defer` / `other`）。  
- `pending`：目标可达但基线/tree 未证实；只问补证（`defer`/`other`），证实后再升 `ready`。  
- `blocked`：先补证据，不问推进。  
- 禁止只贴 draft 等「继续/放行」。  
- 定稿后才可谈 plan；`frozen` 时不得进 execute。

---

## 7. 纸面验收用例（样例表）

假设入口为精确表，Spring Boot 多模块仓（纸面，不改仓）：

| 项 | 期望分析方向 |
|---|---|
| Lucene `9.12.1→9.12.2` | PATCH；确认有效 owner 后可进同层 patch 批确认 |
| jackson-databind `2.21.2→2.21.4` | 优先 `upgrade-owner`（Boot BOM 属性）；忌盲目单钉 |
| 未使用的直接依赖 | `usage_status=unused` → 默认 `remove`，须人确认 |
| 传递 CVE，上层已有安全 GA | 优先 `upgrade-introducer`，而非先 `force-align` |
| Eureka `2.0.6→2.0.5` | **降级**；先判 groupId 与是否传递。目标可达但缺 Maven/tree → 队列 **`pending`**（可行·待补证：恢复 mvn → 分期 tree 证实 `2.0.6`），不要标存在性 `blocked`，也不要 `ready`+`proceed`。基线证实后升 `ready`；传递侧默认 `move-introducer` 或破例 `force-align`，并给换 starter/换栈/原生改造菜单供人选；High |
| Netty `4.2.15→4.1.136` | 目标存在性先行：`netty-codec-base` / `netty-codec-compression` 仅存在于 4.2 线，目标版 404 → 整族行 `blocked`，退回请用户重述目标；不得替换「相近制品」 |
| commons-lang `2.6→3.20.0` | MAJOR + 坐标/包名变更；`replace-component` 向；单独 `app-library` 批；Phase 分析只出迁移影响，并**命名**既有 recipe（如 OpenRewrite `MigrateCommonsLangToCommonsLang3`）为实施期选项，本阶段不执行 |
| CVE 只给 GAV 无 `to` | 查官方修复 GA 区间后推荐；**逐单元**等人选定 `proceed:g:a:v` |

验收：目标存在性逐成员（含 classifier）探测过、决策包十章齐全、确认队列曾出现、`validate_report.py` 退出码 0、`analysis_status` 在确认后可为 `complete`、实施门仍由 delivery go 控制。

多批次时报告布局固定为
`<entry-kind>/<authority-layer>__<boot-line>__variant-<build-variant>__scope-<batch-scope>[__domain-<decision-domain>]/java-dependency-upgrade-report.md`
且证据根须有 `BATCH-INDEX.md`（见 skill `references/report-contract.md`）。
示例：`exact/boot-bom__boot-3.2.x__variant-default__scope-json-netty/`；
字段 `boot_line=3.2.x` ↔ 目录 token `boot-3.2.x`（或 `no-boot`）。

Owner 内部调整优先用 BOM 属性（如 `netty.version` / `jackson-bom.version`），不要默认单包钉扎；详见 `owner-and-resolution.md` 阶梯。

---

## 8. 与前端升级 Skill 的关系

| 同构 | 差异 |
|---|---|
| Stage A 分析-only、确认队列、三状态轴 + 实施授权（delivery） | lock → 解析树/BOM；npm → Maven/Gradle |
| 证据目录挂在已有 change 下 | 模板与报告正文默认中文 |
| `batch_implementation_gate` 语义 | owner-first / Boot 线拆批 / 处置阶梯 |
| 均有结构校验脚本 | 前端 `generate_upgrade_report.py` 是生成器；Java `validate_report.py` 只校验，报告由 Agent 按模板写 |

Java 分析阶段已有 `environment-preflight.md`（PATH 上 `java` + 选用
`mvn`|`gradle` **或** wrapper graded pass + Python；失败 batch-wide `blocked`、
不写报告）。仍**没有**前端 `run_with_compatible_node.py` 那样的**实施期**护栏
（JDK toolchain 切换、pom 格式冻结、执行授权）。实施阶段护栏仍依赖
`delivery-execute-verify` 的通用闸门。

---

## 9. 常见误区

- 用 pom 声明版本代替 `dependency:tree` / `dependencyInsight`  
- 缺系统 `mvn`/`gradle` 时可用 wrapper graded pass，但须记录 `build_tool_source=wrapper`；二者皆无才硬 blocked  
- 缺 Python 仍宣称可定稿（校验脚本跑不了）  
- 把 `dependency:tree -Dverbose` 单独当作选中版本的权威证据（须用 includes / list / effective-pom 复核）  
- 未验证目标版本/族内成员（含 classifier）是否真实存在就开始 owner 与影响分析  
- 目标制品缺失时自行替换「相近制品」（这是范围变更，不是推断）  
- Boot 托管 jar 直接单包钉扎，而不先查 `netty.version` / `jackson-bom.version` 等 BOM 属性  
- 传递洞优先钉传递包，而不先评估 `upgrade-introducer` / 有证据的 `exclude`  
- 对 unused 直接依赖默认升级，而不先给 `remove`  
- 清单处置写成 `defer`（应用 `no-viable-path`）；或对存在性 `blocked` 行答人工 `defer`  
- MAJOR 迁移不写迁移路径选项，或在分析阶段执行 OpenRewrite/codemod  
- 未写 `decision-records/` 就宣称分析完成  
- 未问确认队列就宣称分析完成；无 `to` 时用「全部 proceed」蒙混  
- 把决策包当作实施批准  
- JDK + Boot + 业务库塞进同一 change  
- 把 Netty/Jackson「最新」钉死而不查 BOM  
- 推荐 Beta/RC/Snapshot 进入 `ready`  

---

## 10. 短提示词（推荐）

Skill 已内置处置阶梯、owner-first、确认队列、拆批、路径解析与常见表模式。  
与 **delivery-frame-spec** 联用时：由 frame 建/恢复 OpenSpec change；本 Skill 只写 `evidence/java-dependency-upgrade/`，不改代码。

**A + frame（精确表，推荐）**

```text
按 delivery-frame-spec 为本批 Java 依赖升级定框（创建或恢复 OpenSpec change）。
再用 java-dependency-upgrade-impact-analysis 做 Stage A 分析（只出决策包，不改代码）。
项目：<仓库路径>

<粘贴升级表>
```

**A + frame（整仓巡检）**

```text
按 delivery-frame-spec 定框；用 java-dependency-upgrade-impact-analysis 对 <仓库路径> 做依赖升级巡检，先给候选清单并问我选批，再对选定批出决策包（不改代码）。
```

**仅 A（已有 change / 只要分析）**

```text
用 java-dependency-upgrade-impact-analysis 分析下面依赖（只出决策包，不改代码）。
项目：<仓库路径>

<粘贴升级表>
```

**B — 仅 Boot 归属冲突（外部 Boot skill）**

```text
用 upgrading-spring-boot-dependencies 分析 <仓库路径> 上 <GAV/冲突描述> 的主 Owner 升级方案（先 BOM/parent）。
```

报告路径：`--output-dir` > change → `evidence/java-dependency-upgrade/` > 自动匹配既有 `openspec/changes/<id>`；联用 frame 时通常无需手写路径。  
定稿后若要计划/实施，另开 `delivery-plan-tasks` / `delivery-execute-verify` 并显式授权。

---

## 11. 相关路径

- Skill：`java-dependency-upgrade-impact-analysis/SKILL.md`  
- 中文模板：`…/templates/decision-packet.md`、`decision-record.md`  
- 校验脚本：`…/scripts/validate_report.py`；样例包：`…/fixtures/valid-report.md`  
- 处置阶梯：`…/references/treatment-ladder.md`  
- 补证清单 × 路径选项菜单：`…/references/next-action-choice-menus.md`  
- 环境前置：`…/references/environment-preflight.md`  
- Owner 内部调整阶梯（属性覆盖 vs 单包钉扎）：`…/references/owner-and-resolution.md`  
- JVM 专有陷阱与 API 差异验证：`…/references/impact-and-validation.md`  
- 前端对照：`docs/frontend-dependency-upgrade-impact-analysis-usage.md`  
- 方法参考（外部）：Boot owner-first 思路、Maven Tools MCP、社区 GAV→GitHub 映射等（见 skill `reachability-and-upstream.md`）

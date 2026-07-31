# Next-Action Choice Menus（补证清单 × 路径选项）

本文件规定两类高频场景下 Agent **必须**给用户的可选项与证据探索义务。
升级与降级共用同一菜单骨架；降级仅额外要求醒目 `downgrade` 警告 + High scrutiny。

目标：不要把「可行但缺工具/基线」误写成队列 `blocked`；不要把传递依赖的版本移动
默认成「单包钉版本」。探索 1–3 条已验证路径后，**用人选**，Agent 不代选。

## A. 可行但缺环境/基线证据（pending baseline）

### 信号

- 目标制品存在（`target_artifact_exists=yes`），处置方向可判（含显式降级）
- 但 `resolved_from` 未用 tree/insight/list 证实，或模块级探针失败
- 常见原因：PATH 无 `mvn`/`JAVA_HOME`、需 wrapper、需分期跑 leaf-module tree

### 禁止误写

| 错误写法 | 正确写法 |
|---|---|
| 队列 `blocked`，原因「降级需环境证据 / 缺降级理由」 | 缺动机 = §10 证据缺口；缺工具/基线 = 队列 **`pending`** + 补证清单，不是降级否决 |
| `ready` + `proceed:` 但 `resolved_from` 未证实 | 基线未证实前用 **`pending`**（选项仅 `defer`/`other`），证实后再升为 `ready` |
| `analysis_status=blocked` 仅因「还没跑 tree」且 preflight 已 PASS | preflight PASS 后包级保持 `partial`；该行用 `pending`，暂不 `proceed` |
| 用 pom 声明版冒充 `resolved_from` 后直接 `ready`+`proceed` | 声明版可记 `declared_from`；未证实前不得清 claimed-from 闸 |

环境前置硬失败（`preflight.py` exit `5`）仍是批级 `blocked`、**不写报告**——那是工具闸，不是本菜单。

### 必出「下一步补证」清单（对话 + 决策记录 + 报告 §10）

按序给出，可勾选：

1. **恢复构建工具会话**：设置 `JAVA_HOME` / PATH；优先系统 `mvn`/`gradle`，否则项目 `mvnw`/`gradlew`（记 `build_tool_source=wrapper`）。
2. **分期 leaf 探针**（有超时；禁止一上来全 reactor 无界 tree）：
   - Maven：`mvn -pl <module> -am dependency:tree -Dincludes=<groupId>:<artifactId>`
   - 复核：`dependency:list` 或 `help:effective-pom`（勿把 verbose-only 当选中版权威）
   - Gradle：`dependencyInsight --dependency <name> --configuration <cfg>`
3. **证实基线**：`resolved_from` 是否等于表称 `from`（如 Eureka `2.0.6`）。一致 → 进入路径菜单 B；不一致 → claimed-from 闸，先请人选定基线。
4. **再开确认波**：基线确认后，把该单元从队列 **`pending` → `ready`**，带完整路径选项与 `proceed:`。

补证完成前：队列状态必须是 **`pending`**（问题含「待补证」/ `pending-baseline` /「补证清单」）；
选项仅 `defer` / `other`；**不得**发出 `proceed:`。不要用存在性-`blocked` 词表（重述目标）冒充工具补证。

### 基线字段（决策记录建议填写）

| 字段 | 取值 |
|---|---|
| `baseline_evidence_status` | `confirmed` / `pending-tooling` / `pending-tree` / `mismatch` |
| 下一步补证 | 上列有序清单的裁剪版（含具体 module / includes） |

---

## B. 传递依赖版本移动（upgrade 或 downgrade）

### 信号

- `owner_class=transitive`，或依赖路径显示经 starter/BOM/上层直接依赖引入
- 表要求叶子 GAV `from→to`（升或降）
- 典型：`eureka-client` 经 `spring-cloud-starter-netflix-eureka-client` / Cloud BOM 引入

### 默认立场

1. **禁止**把「在叶子上简单钉版本」写成首选（那是 Owner 阶梯第 4 档 `force-align` / per-GAV pin，须破例条件）。
2. 升降级对称：上移用 `upgrade-introducer`；下移/重对齐用 `move-introducer`。
3. 须填 `introducer_gav` + `introducer_upgrade_available`（降级场景同样探「introducer 是否存在能收敛到目标传递版的 GA」）。
4. 在推荐主路径之外，**主动探索** 1–3 条替代路径（见下），写入决策记录「路径选项菜单」，确认问题里并列给用户选。

### 路径选项菜单（须探证据后列出）

对每个适用选项写：一句话做法 · 已验证证据（URL/坐标/树路径）· 主要风险 · 对应确认词。

| ID | 路径 | 何时推荐 | 确认词 |
|---|---|---|---|
| A | **Introducer 对齐**（首选） | 存在 Cloud/Boot/上层 GA，其解析树已带目标传递版 | `proceed:<leaf-g>:<leaf-a>:<to>`（问题中写明将改的 introducer/BOM） |
| B | **Force-align 叶子**（破例） | A 已证伪或不可等发版；完整 Decision Record + override 破例条件 | `proceed:<leaf-g>:<leaf-a>:<to>` + 问题标注 `force-align` |
| C | **替换 introducer / 二合一 starter** | 同职责有其他维护中的 starter/BOM 组合（如另一 discovery starter） | `replace:<new-g>:<new-a>[:v]` |
| D | **换组件 / 换栈** | 离开当前族（另一注册中心客户端、官方后继坐标等）；1–3 候选均独立探测存在性 | `replace:<g>:<a>[:v]`（每候选可拆单元或用 `other` 点名） |
| E | **原生改造 / 去依赖** | 调用面可改写为平台 API 或不依赖该客户端；须点名触及模块与测试 | `other`（下波记录迁移范围）或确认后改处置 |
| F | **暂缓** | 证据不足或窗口不允许 | `defer` |

规则：

- 至少给出 **A +（B 或 C/D 之一）**；E 在调用面非空时尽量评估，不可行则写「已证伪 + 原因」。
- 每个 `replace:` 候选必须 `target_artifact_exists=yes`（或等价 registry 证据）；禁止「感觉能换」的空名。
- 菜单写在决策记录与确认「问题」列；**不要**为每个备选路径复制多条 `ready` 行，除非权威层/族已拆批。
- 用户选 C/D/E 后：更新 `recommended_treatment`，再生包，再清队列。

### Eureka / Cloud 客户端特化

1. 先消歧 groupId：`com.netflix.eureka:eureka-client`（1.x/2.0.x）vs
   `org.springframework.cloud:spring-cloud-starter-netflix-eureka-client`（列车版）。
2. 用 tree 确认是 **direct** 还是 **transitive**；传递降级默认菜单 B，不是 `move-self`。
3. Introducer 证据优先：Cloud BOM / starter POM 的 dependencyManagement、release train 兼容说明
   （见 `common-gav-repos.md`），不是 Central「最新叶子版」。
4. 替代路径探索示例（须按仓核实，下列仅为探查方向）：
   - 换列车内 introducer 版本使传递 `eureka-client` 收敛到目标
   - 换 discovery 栈（项目已有的 Nacos/Consul/K8s 服务发现 starter）
   - 去掉 Netflix Eureka、改用当前 Boot/Cloud 推荐的服务发现方式（原生改造）
5. 显式 `2.0.6→2.0.5`：目标存在且路径可写时标 **可行**；若仅缺 Maven/tree，走菜单 A（补证），
   **不要**写成存在性 `blocked`。

---

## C. 与确认协议的衔接

1. 草稿包时：对 pending-baseline 单元写清 `baseline_evidence_status` + 补证清单，队列标 `pending`；对传递单元写路径菜单（基线证实后的 `ready` 波必带）。
2. 同波提问：`pending` 问补证承诺；`ready` 的「问题」须含推荐路径 ID（A/B/…）及已探替代的一句话摘要。
3. 用户答复后落盘；选替代路径则改处置并再探一轮影响（仍 analysis-only）。
4. Pressure guards（补充）：

| 合理化 | 回应 |
|---|---|
| 「缺 Maven 所以把降级标 blocked」 | 工具/基线用队列 `pending` + 补证清单；降级可达且方向明确时不否决降级 |
| 「传递降级就在叶子上钉版本」 | 先 A introducer；B force-align 须破例；并探 C/D/E |
| 「替代栈我帮你定了」 | 只列已验证候选；人选 `replace:` / `other` |
| 「补证和路径选择太慢，先 proceed」 | 无 `resolved_from` 保持 `pending`，不得 `proceed` |

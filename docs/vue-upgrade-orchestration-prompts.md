# Vue 升级编排提示词（显式点名 Skill）

> 受众：要把 **Vue2→Vue3** 与 **样式不乱** 串起来跑的调用方 / Agent。  
> 原则：**用户短触发 + 显式点名 Skill**；细则由 Agent 按各 Skill 默认补齐，用户不必背长要求。  
> 领域 Skill 与 Delivery family **互不调用**；Delivery family 内部按 handoff 链式接力。编排者只传递摘要路径，不粘贴完整报告。

相关 Skill：

| Skill | 职责 |
|---|---|
| `migrate-vue2-pages-to-vue3-host` | **版 B 主路径**：跨仓页面迁移 assess/design/execute/verify；视觉/表格/回退/runtime 领域证据 |
| `frontend-dependency-upgrade-impact-analysis` | 依赖升级/替换/迁入差分（只分析；版 B 用 `migration-demand-diff`） |
| `delivery-frame-spec` | 定框、规格、验收 |
| `delivery-plan-tasks` | 任务与验证矩阵 |
| `delivery-execute-verify` | 实施与双门禁验收（含 Delivery G9 自有视觉记录） |

已退役（勿再点名）：`frontend-ui-stack-visual-parity`、`vue2-to-vue3-upgrade-impact-analysis`（能力并入 `migrate-vue2-pages-to-vue3-host`）。

默认**不调用**：`delivery-explore`（目标已清时）、`design-taste-frontend`（目标是视觉守恒，不是重设计）。

软挂载细节另见：

- [`migrate-vue2-pages-to-vue3-host-delivery-usage.md`](./migrate-vue2-pages-to-vue3-host-delivery-usage.md)
- [`frontend-dependency-upgrade-impact-analysis-usage.md`](./frontend-dependency-upgrade-impact-analysis-usage.md)

---

## 0. 先选拓扑

| 版 | 场景 | 能不能套另一版提示词 |
|---|---|---|
| **版 A：单仓原地升** | 一个仓库从 Vue2 升到 Vue3 | — |
| **版 B：A→B 并入** | Vue2 源仓 A（只读）内容迁入已有 Vue3 仓 B | **不能**直接套版 A |
| **版 B-轻量（单页）** | 仅迁 A 的某一页进 B（见 §2.5） | 用 §2.5；不要直接套 §2.2 全量一条龙 |

版 B / B-轻量优先；单页优先 §2.5。`migrate-vue2-pages-to-vue3-host` **只服务 A→B host-port**，不要拿它做版 A 单仓原地升。

版 B 时各 Skill **必须**走一等公民模式：

| Skill | 版 B 默认 |
|---|---|
| `migrate-vue2-pages-to-vue3-host` | 集成路线：`assess`→`design`→Delivery 实施后 `verify`；独立路线才由 migrate `execute`；A 只读；保留 iframe 回退；B 壳 host-native；内容区 strict parity；产出 `vue-migration-domain/v1` |
| `frontend-dependency-upgrade-impact-analysis` | mode `migration-demand-diff`（`generate_migration_demand_diff.py`；exit 7=待确认） |
| `delivery-*` | 实施仓=B；禁改 A；`visual=required`；G9 自有 `delivery-visual-evidence/v1`，migrate 证据仅 path/digest 引用 |

参考仓联调示例：A=`D:\Hzhao\AI_Test\Vue2_Test`，B=`D:\Hzhao\AI_Test\Vue3_Test`（vue3-element-admin）。

---

## 1. 版 A — 单仓原地升（Vue2 → Vue3）

> 版 A **不再**点名已退役的 visual/vue-impact Skill。  
> 视觉由 Delivery G9 + 项目内截图基线承担；Vue/依赖改造面由 dependency 分析 + Frame/Plan 覆盖。  
> 若实际是「迁入已有 Vue3 仓」，改走 **版 B**，不要硬套本节。

### 1.1 用户开场（一条龙）

```text
项目：<Vue2 仓库路径>
Vue2→Vue3，样式不要乱；范围：全量
（或：选页：/table/complex-table …）

请按序显式调用：
1) /frontend-dependency-upgrade-impact-analysis（只分析）
2) /delivery-frame-spec（吃 dependency summary；visual=required；先基线再改代码）
3) /delivery-plan-tasks（含视觉检查点与回滚）
4) /delivery-execute-verify（分批功能 + G9 视觉）

中间需要我确认时，用 Skill 规定的令牌问我。
细则按各 Skill 默认执行，我不再重复要求。
```

### 1.2 Agent 默认补齐

| 用户说了啥 | Agent 自动做 |
|---|---|
| 「样式不要乱」 | `visual=required`；Frame 要求升级前基线或批准 substitute |
| 未给 output-dir | 复述默认目录并确认，或沿用已有 OpenSpec change 目录 |
| 进 Delivery | 只传 summary/report 路径；自行重算 `quality_profiles` |
| 实际是 A→B | 停止版 A，改走 §2 / §2.5 |

### 1.3 推荐顺序

```text
升级前视觉基线（Delivery/项目约定）
    → 依赖分析
    → delivery-frame-spec
    → delivery-plan-tasks
    → delivery-execute-verify（分批）+ G9 视觉门禁
```

---

## 2. 版 B — A（Vue2 只读）并入 B（Vue3）

### 2.1 与版 A 的关键差异

| 维度 | 版 A 单仓 | 版 B A→B |
|---|---|---|
| 改谁 | 同一仓库 | **只改 B；A 禁止修改** |
| 主领域 Skill | （无 migrate） | **`migrate-vue2-pages-to-vue3-host`** |
| 视觉基线 | 升级前本仓 | **A 的页面观感**（migrate visual contract） |
| 视觉候选 | 升级后本仓 | **迁入 B 后的页面内容区**；B 壳保持 host-native |
| 迁移含义 | 原地升 | **按 B 栈适配迁入**，不是给 A 上 `@vue/compat` |
| 依赖分析 | 本仓升级清单 | **A 需求 vs B 已有栈差分** |
| 回退 | 发布回滚 | **保留 iframe / legacy 开关直至 observation 结束** |
| Frame | 「升级本仓」 | 「端口/集成进 B」+ forbidden：改 A |

**不能**把版 A 提示词不改路径直接用在 A→B。

### 2.2 用户开场（一条龙）

```text
源仓 A（只读）：<Vue2 路径>
目标仓 B（可写）：<Vue3 路径>
待迁移页面：<路径或路由>
Vue 3 入口 HTML：<HTML 文件路径>
目标：把该页升级并入 B；禁止修改 A；B 外壳保持原样；内容区对齐 A；
保留 iframe 回退；迁移代码 TypeScript，允许 Options API；只修缺陷不开发新功能。

请按序显式调用：
1) /migrate-vue2-pages-to-vue3-host（assess + design；artifact_directory 可选）
2) /frontend-dependency-upgrade-impact-analysis（实施仓=B；A 依赖当迁入需求；可选）
3) /delivery-frame-spec（实施仓=B；源=A 只读；吃上面摘要路径；visual=required）
4) /delivery-plan-tasks（任务只改 B；含表格/视觉/回退验证行）
5) /delivery-execute-verify（只在 B 实施）
6) /migrate-vue2-pages-to-vue3-host（verify；不重复实施，只按当前 revision 刷新领域证据）

缺页面路径或入口 HTML 时先阻断补齐，不要猜测扩大范围。
中间用 Skill 规定令牌问我。细则按默认补齐。
```

### 2.3 分步显式调用

**迁移评估与设计（读 A，对照 B，不改代码）**

```text
/migrate-vue2-pages-to-vue3-host
mode: assess 然后 design
源仓 A：<A>。目标仓 B：<B>。
迁移单位：<路径或路由>。B 入口 HTML：<HTML 文件路径>。
约束：禁改 A；保留 iframe 回退；TS + 允许 Options API；B 壳 host-native；
内容区 strict parity；只修缺陷。
产出：vue-migration-domain/v1（路径或 inline）+ visual-migration-contract 草案。
```

**依赖差分（可选，可与 design 并行）**

```text
/frontend-dependency-upgrade-impact-analysis
以 B 为实施仓库；把该页闭包依赖当迁入需求。
输出：A 有而 B 无 / 双方冲突 / 必须替换清单。
只分析，不改 A。
```

**定框 / 计划 / 实施**

```text
/delivery-frame-spec
实施仓库：B。源：A（只读）。
外部交付件：
- <vue-migration-domain packet 路径>
- <dependency summary 路径，若有>
验收：功能等价 + 视觉对齐 A（内容区）+ 表格样式 + iframe 回退可演练；
forbidden：修改 A；拷贝 A 壳进 B；去掉回退；无关 Composition 重写。
```

```text
/delivery-plan-tasks
任务只改 B；纵向切片含挂载接线、闭包适配、feature switch、测试、视觉/表格行、回退演练。
```

```text
/delivery-execute-verify
集成路线唯一代码 mutation owner；只在 B 实施；分批迁入；G9 自建 delivery-visual-evidence；
可引用 migrate visual-parity-evidence 的 path/digest，不把其 schema 当 Delivery 状态。
```

```text
/migrate-vue2-pages-to-vue3-host
mode: verify
不再修改代码；绑定当前 source_revision / host_revision；刷新领域证据；
完成构建、测试、视觉、表格样式与 legacy-iframe 回退验证。
```

### 2.4 视觉目标别混

| 说法 | 含义 |
|---|---|
| 「样式对齐 A」 | baseline=A，候选=B **内容区**，`strict_parity`；B 壳排除在严格像素对比外 |
| 「跟 B 现有设计系统走」 | `approved_redesign` / 另一验收；不要与「对齐 A」混用 |
| 「保留 iframe 回退」 | registry/`legacy-iframe` 可切换；回退验证用同一 fixture；嵌套双壳需显式批准 |

### 2.5 版 B-轻量 — 单页迁入（推荐默认）

> 适用：只把 A 的某一业务页（含直接依赖闭包）迁入已有 Vue3 仓 B，并视觉对齐 A。  
> 相对 §2.2：**收窄范围、Wave 1 只读可并行；跨仓页面迁移仍固定使用 High 闸门强度**。  
> 多模块 / 动 B 壳层·权限·公共契约时，改回 §2.2。

先填路径：

| 占位符 | 填什么 |
|---|---|
| `<A>` | Vue2 源仓绝对路径（只读） |
| `<B>` | Vue3 目标仓绝对路径（可写） |
| `<page>` | 待迁移页面路径或路由（必填；未知则先检索再请用户点名） |
| `<B-html>` | Vue3 入口 HTML（必填） |
| `<artifact_dir>` | 可选；调用方提供时 migrate 写入 `<artifact_dir>/evidence/vue-cross-repo-migration/` |
| `<B-mount-hint>` | B 中期望挂载点；未知写「由 Agent 在 B 内提案」 |

**范围（该页闭包）**：菜单对应入口 SFC + 直接子组件 / 本地样式 / 该页专用 API·utils。  
**不含**：同模块其他页、A 全仓升级、compat 主路径、把 B 全局改成 A 的设计系统。

#### 2.5.1 推荐顺序（两波）

```text
Wave 1（只读，可并行）：
  migrate assess+design @A/B
  ∥ dependency migration-demand-diff @B（可选）
Wave 2（串行，只写 B）：
  frame（High）→ plan → execute
  → migrate verify（证据刷新，不实施）
```

#### 2.5.2 Wave 1 — 迁移评估与设计

```text
/migrate-vue2-pages-to-vue3-host
mode: assess 然后 design
A=<A>；B=<B>；page=<page>；B HTML=<B-html>
禁改 A；保留 iframe；TS + Options API 可；B 壳不动；内容区对齐 A；只修缺陷。
artifact_directory: <artifact_dir>（若提供）
```

#### 2.5.3 Wave 1 — 依赖差分（可选）

```text
/frontend-dependency-upgrade-impact-analysis
实施仓：<B>。只分析。将该页闭包依赖当迁入需求，对照 B 做缺/冲突/必替换清单。
```

#### 2.5.4 Wave 2 — 定框 / 计划 / 实施

```text
源仓 A（只读）：<A>
目标仓 B（可写）：<B>
目标：将 <page> 迁入 B；禁改 A；样式对齐 A 内容区；保留 iframe 回退。
挂载提示：<B-mount-hint>
外部交付件：
- <vue-migration-domain packet 路径>
- <dependency summary 路径，若有>

/delivery-frame-spec（实施仓=B；源=A 只读）
范围：该页闭包 + B 侧最小挂载接线。visual=required。
forbidden：改 A；compat 包 A；去掉 iframe 回退；重构 B 无关模块；拷贝 A 壳。
跨仓页面迁移固定 High + plan；动 B 壳层/全局权限/公共契约会进一步扩大 High 的审查与回滚范围。
```

```text
/delivery-plan-tasks
任务只改 B；含挂载、闭包适配、依赖缺口、视觉/表格、回退演练。
```

```text
/delivery-execute-verify
集成路线唯一代码 mutation owner；只在 <B> 实施；对照 migrate visual contract / evidence。
```

```text
/migrate-vue2-pages-to-vue3-host
mode: verify
不重复实施；完成构建、测试、视觉、表格样式与回退验证；刷新 packet。
```

#### 2.5.5 一条龙（单会话不愿拆时）

```text
使用 /migrate-vue2-pages-to-vue3-host，并结合 delivery-* 系列 Skills，
完成以下 Vue 2 页面到 Vue 3 仓库的升级迁移：

Vue 2 仓库：<A>
Vue 3 仓库：<B>
待迁移页面：<page>
Vue 3 入口 HTML：<B-html>

要求：
- 保留 iframe 回退；
- 迁移代码使用 TypeScript，允许 Options API；
- 只修缺陷，不开发新功能；
- B 外壳保持原样，迁移内容严格保持功能和视觉一致；
- 完成构建、测试、视觉、表格样式和回退验证。

编排顺序：
1) migrate assess + design
2) （可选）dependency migration-demand-diff
3) delivery-frame-spec
4) delivery-plan-tasks（跨仓页面迁移为 High，必需）
5) delivery-execute-verify（唯一代码 mutation owner）
6) migrate verify（不重复实施，只刷新领域证据）

领域 Skill 与 Delivery family 互不调用；Delivery family 内部链式接力；只传摘要路径。
implementation go 必须显式绑定 source_revision + host_revision；Delivery 的单一 artifact_revision/repo_head 不足以代填迁移授权。
缺 <page> 或 <B-html> 先阻断。
```

#### 2.5.6 Agent 默认补齐（单页专用）

| 用户说了啥 | Agent 自动做 |
|---|---|
| 未给 `<page>` / `<B-html>` | 阻断并请用户补齐；可用检索列候选，但不得擅自选定扩大范围 |
| 未给 `<B-mount-hint>` | 在 B 内找同类挂载，提案写入 Frame Open Questions |
| 「样式对齐 A」 | baseline=A 该页；候选=B 内容区；壳 host-native |
| 「保留 iframe」 | design 必含 fallback；verify 必含 legacy-iframe 演练 |
| 「允许 Options API」 | 不强制 Composition 重写；TS 先落边界类型 |
| Wave 1 未齐 / 无授权 | 不进 Delivery 实施；implementation go 显式绑定 source_revision + host_revision |

---

## 3. 对照表：显式调用时用户最少说什么

| 顺序 | 显式调用 | 版 A 最少再说 | 版 B 最少再说 | 版 B-轻量 |
|---|---|---|---|---|
| 1 | `/migrate-vue2-pages-to-vue3-host` | （不适用） | A/B 路径；page；B HTML；assess+design | 同上；单页闭包 |
| 1b | `/frontend-dependency-upgrade-impact-analysis` | 只分析 | 实施仓=B；对照 A | 仅该页闭包 vs B |
| 2 | `/delivery-frame-spec` | dependency 路径 + visual | 实施=B；源=A；吃 migrate packet；禁改 A | 同上 + 挂载提示 |
| 3 | `/delivery-plan-tasks` | 分批+视觉 | 只改 B + 视觉/回退 | 必需（High） |
| 4 | `/delivery-execute-verify` | 分批验证 | 只在 B；G9 | 只在 B |
| 5 | `/migrate-vue2-pages-to-vue3-host` | （不适用） | verify；不重复实施，只刷新证据 | 同左 |

用户中途通常只需答：页面/HTML 确认 / `implementation go` / `先不实施` / 差异批准。

Delivery 修改 B 后，旧 implementation authorization 随旧 `host_revision` 失效；最终 migrate
verify 必须绑定新 revision 并保持只读。若验证中发现需要修复，退出 verify 并重新取得绑定当前
`source_revision + host_revision` 的实施授权，再由 Delivery Execute 修改。

---

## 4. 编排红线（两版共用）

- 不要让 Skill 互相调用或共享状态 schema  
- 不要在 migrate Skill 内读取/调用 `delivery-*`；反之亦然  
- 不要用「继续 / 全部放行」代替 revision 绑定的授权  
- 不要先改 B / 升依赖再补 A 视觉基线与 migration contract  
- 不要把完整分析报告贴进 Frame；只给路径 + digest  
- 不要用功能 E2E 代替 migrate 视觉证据或 Delivery G9  
- 不要把 `design-taste-frontend` 并进「样式对齐」主流程  
- 不要在未批准时拆除 iframe 回退或关停源仓 A  

---

## 5. 完成标准（两版共用）

不能以「页面能打开」收工。至少同时满足：

- 依赖/迁移相关决策已关闭（或明确 deferred）  
- 构建与约定自动化通过  
- 核心业务场景通过  
- 版 B：`visual-parity-evidence/v1` 经 `validate_visual_evidence.mjs` 通过（含表格与回退，若适用）  
- Delivery 自有视觉证据（G9）通过（当 `visual=required`）  
- 版 B：iframe / legacy 回退在目标环境可演练；observation 未结束前不撤回收退  

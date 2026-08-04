# Vue 升级编排提示词（显式点名 Skill）

> 受众：要把 **Vue2→Vue3** 与 **样式不乱** 串起来跑的调用方 / Agent。  
> 原则：**用户短触发 + 显式点名 Skill**；细则由 Agent 按各 Skill 默认补齐，用户不必背长要求。  
> Skill **互不调用**；由编排者按序调用，只传递摘要路径，不粘贴完整报告。

相关 Skill：

| Skill | 职责 |
|---|---|
| `frontend-ui-stack-visual-parity` | 视觉基线 / 诊断 / 最小样式修复 |
| `vue2-to-vue3-upgrade-impact-analysis` | Vue2→3 迁移影响与路径决策（只分析） |
| `frontend-dependency-upgrade-impact-analysis` | 依赖升级/替换/移除影响（只分析） |
| `delivery-frame-spec` | 定框、规格、验收 |
| `delivery-plan-tasks` | 任务与验证矩阵 |
| `delivery-execute-verify` | 实施与双门禁验收 |

默认**不调用**：`delivery-explore`（目标已清时）、`design-taste-frontend`（目标是视觉守恒，不是重设计）。

软挂载细节另见：

- [`vue2-to-vue3-upgrade-delivery-usage.md`](./vue2-to-vue3-upgrade-delivery-usage.md)
- [`frontend-dependency-upgrade-impact-analysis-usage.md`](./frontend-dependency-upgrade-impact-analysis-usage.md)

---

## 0. 先选拓扑

| 版 | 场景 | 能不能套另一版提示词 |
|---|---|---|
| **版 A：单仓原地升** | 一个仓库从 Vue2 升到 Vue3 | — |
| **版 B：A→B 并入** | Vue2 源仓 A（只读）内容迁入已有 Vue3 仓 B | **不能**直接套版 A |

两版 Skill 组合相同，但 **项目路径、基线来源、禁止改谁** 不同。

---

## 1. 版 A — 单仓原地升（Vue2 → Vue3）

### 1.1 用户开场（一条龙）

```text
项目：<Vue2 仓库路径>
Vue2→Vue3，样式不要乱；范围：全量
（或：选页：/table/complex-table …）

请按序显式调用：
1) /frontend-ui-stack-visual-parity（Phase A 基线）
2) /vue2-to-vue3-upgrade-impact-analysis
3) /frontend-dependency-upgrade-impact-analysis
4) /delivery-frame-spec（吃上面三个摘要路径）
5) /delivery-plan-tasks
6) /delivery-execute-verify

中间需要我确认时，用 Skill 规定的令牌问我。
细则按各 Skill 默认执行，我不再重复要求。
```

### 1.2 分步显式调用（可拆开贴）

**视觉基线（必须最先）**

```text
/frontend-ui-stack-visual-parity
项目同上。Phase A，先采升级前基线，别改代码。
```

**Vue 专项分析**

```text
/vue2-to-vue3-upgrade-impact-analysis
项目同上。只分析不改代码；范围按上面约定。
```

**依赖分析**

```text
/frontend-dependency-upgrade-impact-analysis
项目同上。覆盖这次升级相关依赖；只分析。
```

**定框**

```text
/delivery-frame-spec
项目同上。
外部交付件：
- <upgrade-summary.json 路径>
- <dependency report 路径>
- <visual-summary.json 路径>
把功能和视觉都写进验收。
```

**拆任务**

```text
/delivery-plan-tasks
按可验证迁移批次拆，含视觉检查点。
```

**实施**

```text
/delivery-execute-verify
按 tasks 实施；分批做功能和视觉验证。
```

**样式偏差（按需）**

```text
/frontend-ui-stack-visual-parity
Phase A：对照升级前基线，只诊断给策略。
```

确认后：

```text
/frontend-ui-stack-visual-parity
Phase B：go:visual-fix
按已确认策略做最小样式修复。
```

### 1.3 Agent 默认补齐（用户不用写）

| 用户说了啥 | Agent 自动做 |
|---|---|
| 「样式不要乱」 | `visual=required`；先基线再改依赖/样式 |
| 未提 Tailwind/vxe | 以 inventory 为准；无 Tailwind 走 `no-tailwind` 分支 |
| 未给 output-dir | 复述默认目录并确认，或沿用已有目录 |
| 分析需确认 | 原文问 `proceed:*`，不接受「继续/全部放行」 |
| 进 Delivery | 只传 summary/report 路径；自行重算 `quality_profiles` |
| 实施中样式坏了 | visual Phase A → 确认 → Phase B 最小 CSS |

### 1.4 推荐顺序

```text
视觉 Phase A 基线
    → Vue 分析 ∥ 依赖分析（可并行）
    → 确认队列清完
    → delivery-frame-spec
    → delivery-plan-tasks
    → delivery-execute-verify（分批）+ visual 回路
    → 功能门禁 + Delivery G9 视觉门禁
```

---

## 2. 版 B — A（Vue2 只读）并入 B（Vue3）

### 2.1 与版 A 的关键差异

| 维度 | 版 A 单仓 | 版 B A→B |
|---|---|---|
| 改谁 | 同一仓库 | **只改 B；A 禁止修改** |
| 视觉基线 | 升级前本仓 | **A 的页面观感** |
| 视觉候选 | 升级后本仓 | **迁入 B 后的页面** |
| 迁移含义 | 原地升 / 兼容构建 | **按 B 栈适配迁入**，不是给 A 上 compat |
| 依赖分析 | 本仓升级清单 | **A 需求 vs B 已有栈差分** |
| Frame | 「升级本仓」 | 「端口/集成进 B」+ forbidden：改 A |

**不能**把版 A 提示词不改路径直接用在 A→B。

### 2.2 用户开场（一条龙）

```text
源仓 A（只读）：<Vue2 路径>
目标仓 B（可写）：<Vue3 路径>
目标：把 A 的{全量|指定页面/模块}升级并入 B；禁止修改 A；样式对齐 A。

请按序显式调用：
1) /frontend-ui-stack-visual-parity（项目=A，Phase A 基线）
2) /vue2-to-vue3-upgrade-impact-analysis（项目=A，只分析；实施落点=B）
3) /frontend-dependency-upgrade-impact-analysis（实施仓=B；A 依赖当迁入需求）
4) /delivery-frame-spec（实施仓=B；源=A 只读；吃上面摘要路径）
5) /delivery-plan-tasks（任务只改 B）
6) /delivery-execute-verify（只在 B 实施；对照 A 基线做视觉验证）

中间用 Skill 规定令牌问我。细则按默认补齐。
```

### 2.3 分步显式调用

**视觉基线（对 A）**

```text
/frontend-ui-stack-visual-parity
项目：A 路径。Phase A。
为「迁入 B 后对齐 A」采集基线；禁止改 A。
主样本：{A 的关键路由}
```

**Vue 影响（读 A，对照 B）**

```text
/vue2-to-vue3-upgrade-impact-analysis
项目：A 路径。只分析。
说明：实施落点是 B，不是原地改 A；评估迁入 B 的改造面与风险。
另请对照 B 的 Vue/Router/状态/UI 栈做差异摘要。
```

**依赖差分**

```text
/frontend-dependency-upgrade-impact-analysis
以 B 为实施仓库；把 A 的关键依赖当迁入需求。
输出：A 有而 B 无 / 双方冲突 / 必须替换清单。
只分析，不改 A。
```

**定框 / 计划 / 实施**

```text
/delivery-frame-spec
实施仓库：B。源：A（只读）。
外部交付件：上面三个摘要路径。
验收：功能等价 + 视觉对齐 A 基线；forbidden：修改 A。
```

```text
/delivery-plan-tasks
任务只改 B；含从 A 拷贝/适配、对接 B 路由/布局/权限、视觉对照检查点。
```

```text
/delivery-execute-verify
只在 B 实施；分批迁入 + 对照 A 基线做视觉验证。
```

**样式偏差（按需）**

```text
/frontend-ui-stack-visual-parity
Phase A：基线=A 的 capture；候选=B 当前页。只诊断。
```

```text
/frontend-ui-stack-visual-parity
Phase B：go:visual-fix
只改 B 内批准的样式。
```

### 2.4 视觉目标别混

| 说法 | 含义 |
|---|---|
| 「样式对齐 A」 | baseline=A，候选=B，strict/对照 A |
| 「跟 B 现有设计系统走」 | 另一目标；不要与「对齐 A」混用同一套验收 |

---

## 3. 对照表：显式调用时用户最少说什么

| 顺序 | 显式调用 | 版 A 最少再说 | 版 B 最少再说 |
|---|---|---|---|
| 1 | `/frontend-ui-stack-visual-parity` | Phase A / 别改代码 | 项目=A；Phase A；别改 A |
| 2 | `/vue2-to-vue3-upgrade-impact-analysis` | 只分析 | 项目=A；落点=B；只分析 |
| 2 | `/frontend-dependency-upgrade-impact-analysis` | 只分析 | 实施仓=B；对照 A |
| 3 | `/delivery-frame-spec` | 三个路径 + 双验收 | 实施=B；源=A；双验收；禁改 A |
| 4 | `/delivery-plan-tasks` | 分批+视觉检查点 | 只改 B + 视觉对照 |
| 5 | `/delivery-execute-verify` | 分批验证 | 只在 B；对照 A 基线 |
| 按需 | `/frontend-ui-stack-visual-parity` | Phase A 或 `go:visual-fix` | 基线 A / 候选 B；Phase B 只改 B |

用户中途通常只需答：`proceed:…` / `go:visual-fix` / `先不实施`。

---

## 4. 编排红线（两版共用）

- 不要让 Skill 互相调用或共享状态 schema  
- 不要用「继续 / 全部放行」代替确认令牌  
- 不要先升依赖/改 UI 再补基线  
- 不要把完整分析报告贴进 Frame；只给路径  
- 不要用功能 E2E 代替 Delivery G9 视觉证据  
- 不要把 `design-taste-frontend` 并进「样式对齐」主流程  

---

## 5. 完成标准（两版共用）

不能以「页面能打开」收工。至少同时满足：

- 依赖/迁移相关决策已关闭（或明确 deferred）  
- 构建与约定自动化通过  
- 核心业务场景通过  
- 视觉基线场景有候选证据；重大差异归零或有批准记录  
- Delivery 自有视觉证据（G9）通过（当 `visual=required`）  

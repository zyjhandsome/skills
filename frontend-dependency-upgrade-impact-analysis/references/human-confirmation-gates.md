# 人工确认门禁地图

本技能的终点是**证据齐全、选型/推进已落盘的分析报告**（`disposition-selected` / `proceed-selected`），不是实施。实施授权永远在技能之外。

生成器会**一次**写出证据、主轨建议、备选轨道完整问题与确认队列；真正「停下来问人」是 Agent 协议。若 Agent 只交付报告就收工，人会感觉「没有任何确认点」——那是协议违规。

## 0. 三阶段交接（A → B → C）

| 阶段 | 名称 | 本技能是否负责 | 进入条件 |
|---|---|---|---|
| **A** | 分析 + 策略确认 | **是** | 报告写出；开放目标选型 / 精确升级 proceed·defer 落盘；`decision_status≠needs_choice` |
| **B** | 实施计划（任务拆解 / OpenSpec 等） | **否**（调用方） | Stage A 完成 **且** `batch_implementation_gate=ready` |
| **C** | 实施（改依赖 / 改代码 / 跑脚本 / 切 Node） | **否**（调用方 + runner） | Stage B 批准 **且** 用户显式实施授权 + runner `--approve-*` |

硬规则：

- `batch_implementation_gate=frozen` 时：**整批**不得开 Stage B，更不得进 Stage C。
- 任一包确认队列 `blocked` / `ready`、或未延期包仍 `exact_upgrade_status=blocked`、或 Node `execution_readiness=blocked` / 约束冲突 → `frozen`。
- `disposition-selected` / `proceed-selected` **只**结束 Stage A，绝不等于 B/C 批准。

## 1. 两类分析终点

| 模式 | 输入 | 是否需要人确认 | 分析终点（Stage A） |
|---|---|---|---|
| 精确升级 | 已给 `from → to`（或可从 lock 推断 `from` + 明确 `to`） | **是**（G7 推进确认；非处置选型） | `proceed` / `defer` 写入 decision-file → `proceed-selected` 或 `deferred` |
| 开放目标 | 只给包名、无目标版本（`--assess` / 删除 / 合规处置） | **是**（G4 处置选型） | 确认队列 → decision-file → `disposition-selected` |

`primary_track` 只是本轮证据建议的**先问哪条**；最终选型以决策文件为准。报告中的 `curated-map` 替代线索**不是**可点选选项。

## 2. 必须停下来问人的闸门

| # | 闸门 | 何时触发 | 问什么 | 未确认时的状态 |
|---|---|---|---|---|
| G1 | 多前端 workspace | 多个前端候选 | 分析哪一个 importer | 禁止默默全仓 |
| G2 | 基线 `from` 冲突/未知 | claimed `from` ≠ lock 直接解析 | 以哪边为准，或补 `--before-lock` | `blocked`；exit `3` |
| G3 | 确认队列阻塞（证据不足） | `confirmation.status=blocked` | **先不问选型/推进**；补证据后重跑 | 横幅「待补证据」；exit `7`；phase=`evidence`；闸门 `frozen` |
| G4 | 开放目标选型 | 队列 `ready` 且无 `to` | **一包一问**；替换含 `replace:<包>@<版本>` + `other` | 横幅「待人工确认」；exit `7`；phase=`choice` |
| G5 | 改轨后的下一问 | 人答 `switch:<track>` | **原文改问**同包「改轨问题：`<track>`」整表；**不**写 decision-file | 仍 `needs_choice` |
| G6 | 父包追问 | 对话中选了 `handle-parent` | 按父包写入 `包<-父包` 决策；`handle-parent` 本身**不是**最终选择 | 未答完父包追问不得 `decided` |
| G7 | 精确升级推进确认 | 有明确 `to`；轨 `proceed-exact` | **可同批汇总**：`proceed:<包>@<版本>` / `defer` / `other` | exit `7`；闸门 `frozen`；技术 blocked 时队列 `blocked`（先解阻塞） |

**不在本技能内：** Stage B 计划审批、Stage C 实施授权（装依赖 / 改代码 / 跑脚本 / 切 Node）。

## 3. 提问规则（批量 vs 一包一问）

| 包类型 | 提问方式 |
|---|---|
| 开放目标（无目标版本） | **一包一问**（轨道分叉大） |
| 精确升级（已有 `to`） | **可同批汇总**一张表，一次确认多包 `proceed` / `defer` |
| 混合批次 | 精确升级可汇总；开放目标仍逐个问；任一未完成 → 整批 `frozen` |

## 4. 交互协议

1. 生成器一次产出全报告 + 主轨问题 + **改轨问题全文** + 父包追问表 + 精确升级批量确认表。
2. Agent 读确认阶段：`evidence` / `choice` / `mixed`，以及 `batch_implementation_gate`。
3. `blocked`：只补证据 / 解阻塞，不提问选型或推进。
4. `ready`：开放目标原文问主轨；精确升级可按批量确认表一次问完。
5. 若答 `switch:<track>` → 改问「改轨问题」整表，**不**写 decision-file。
6. 最终答案写入 decision-file → 重跑 → `disposition-selected` / `proceed-selected` / `deferred`。
7. 仅当 `decision_status≠needs_choice` **且** `batch_implementation_gate=ready` 时，才可向调用方交接 Stage B；Stage C 另需实施授权。

不得写入 decision-file 的答案：`switch:*`、`handle-parent`、`pin-override`（无版本）、已废除的 `reject-native-refactor`。

## 5. 硬门禁

| 规则 | 要求 |
|---|---|
| 报告横幅 | `evidence`→待补证据；`choice`→待人工确认；`frozen`→批次实施闸门说明 |
| 报告状态 | 有待确认时保持 `draft` |
| `analysis_status` | **禁止**与 `needs_choice` 同时为 `complete` |
| `batch_implementation_gate` | `frozen` / `ready`；`frozen` 时禁止 Stage B/C |
| exit | 无更高优先级阻塞且 `needs_choice` → exit **`7`** |
| Agent | 未清空队列前不得宣称 Stage A 完成；闸门 `frozen` 时不得开计划/实施 |

exit 优先级：`2` → `5` → `3` → `4` → `6` → **`7`** → `0`。  
`batch_implementation_gate=frozen` 在决策已完成后以报告字段 + stderr 警告表达，不单独占用新 exit（避免 Node 未就绪时永远无法结束 Stage A）。

## 6. 选项呈现

- **精确升级（G7）**：`proceed:<包>@<版本>` + `defer` + **`other`**。技术 `blocked` 时不给 proceed，先解阻塞。
- **替换**：仅 `analysis-evidence` 且 eligible 的 `replace:<包>@<版本>`（最多 3）+ 改轨 + **`other`**。
- **删除**：确认删除 + 改轨 + **`other`**。
- **原生改造**：确认原生 +（若有）改轨到替换/删除/父包 + **`other`**。
- **父包**：主问含 pin-override / remove-feature / **`other`**；选处置父包后追问 `包<-父包`。
- **禁止**：同库升级（开放目标）、保留现状、限期豁免、`reject-native-refactor`。

## 7. 常见误读

1. 精确升级 → **不再**「无需确认」；目标版本明确只是免去处置选型，仍要 G7 推进确认。
2. 开放目标但 Agent 跳过队列 → 协议违规；现应见 exit `7` 与横幅。
3. 把 `primary_track` / curated 表当成已选型。
4. 把 `disposition-selected` / `proceed-selected` 当成可以开始改代码或开实施计划。
5. 同批 8 包已确认、2 包仍 blocked → 不得实施那 8 包（整批 `frozen`）。

核对：首页决策状态、确认阶段、`batch_implementation_gate`、`Human Confirmation Queue`、exit 是否为 `7`。

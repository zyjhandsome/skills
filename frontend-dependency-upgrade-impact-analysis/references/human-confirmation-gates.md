# 人工确认门禁地图

本技能的终点是**证据齐全、选型已落盘的分析报告**（`recommended_action=disposition-selected`），不是实施。实施授权永远在技能之外。

生成器会**一次**写出证据、主轨建议、备选轨道完整问题与确认队列；真正「停下来问人」是 Agent 协议。若 Agent 只交付报告就收工，人会感觉「没有任何确认点」——那是协议违规。

## 1. 两类分析终点

| 模式 | 输入 | 是否需要人选轨 | 分析终点 |
|---|---|---|---|
| 精确升级 | 已给 `from → to`（或可从 lock 推断 `from` + 明确 `to`） | **否**（目标已明确） | 影响/风险/验证报告可标 `complete`；`decision_status=not_needed` |
| 开放目标 | 只给包名、无目标版本（`--assess` / 删除 / 合规处置） | **是** | 必须走确认队列 → `human-decisions.json` → 重跑后，才可标 `complete` |

`primary_track` 只是本轮证据建议的**先问哪条**；最终选型以决策文件为准。报告中的 `curated-map` 替代线索**不是**可点选选项。

## 2. 必须停下来问人的闸门

| # | 闸门 | 何时触发 | 问什么 | 未确认时的状态 |
|---|---|---|---|---|
| G1 | 多前端 workspace | 多个前端候选 | 分析哪一个 importer | 禁止默默全仓 |
| G2 | 基线 `from` 冲突/未知 | claimed `from` ≠ lock 直接解析 | 以哪边为准，或补 `--before-lock` | `blocked`；exit `3` |
| G3 | 确认队列阻塞（证据不足） | `confirmation.status=blocked` | **先不问选型**；补证据 / 调研后重跑 | 横幅「待补证据」；exit `7`；phase=`evidence` |
| G4 | 开放目标选型 | 队列 `ready` | 一包一问；替换含 `replace:<包>@<版本>` + `other` | 横幅「待人工选型」；exit `7`；phase=`choice` |
| G5 | 改轨后的下一问 | 人答 `switch:<track>` | **原文改问**同包「改轨问题：`<track>`」整表；**不**写 decision-file | 仍 `needs_choice` |
| G6 | 父包追问 | 对话中选了 `handle-parent` | 按父包写入 `包<-父包` 决策；`handle-parent` 本身**不是**最终选择 | 未答完父包追问不得 `decided` |

**不在本技能内：** 实施授权（装依赖 / 改代码 / 跑脚本 / 切 Node）。

精确升级路径**没有** G4。

## 3. 交互协议

1. 生成器一次产出全报告 + 主轨问题 + **改轨问题全文** + 父包追问表。
2. Agent 读确认阶段：`evidence` / `choice` / `mixed`（见报告「本轮确认阶段」）。
3. `blocked`：只补证据，不提问选型。
4. `ready`：原文问主轨问题；若人答 `switch:<track>`，立刻改问「改轨问题」整表。
5. 最终答案写入 decision-file → 重跑 → `disposition-selected`。
6. 口语选定并落盘即完成本技能内选型；不等于实施批准。

不得写入 decision-file 的答案：`switch:*`、`handle-parent`、`pin-override`（无版本）、已废除的 `reject-native-refactor`。

## 4. 硬门禁

| 规则 | 要求 |
|---|---|
| 报告横幅 | `evidence`→待补证据；`choice`→待人工选型；`mixed`→二者并存 |
| 报告状态 | 有待确认时保持 `draft` |
| `analysis_status` | **禁止**与 `needs_choice` 同时为 `complete` |
| exit | 无更高优先级阻塞且 `needs_choice` → exit **`7`** |
| Agent | 未清空队列前不得宣称分析完成 |

exit 优先级：`2` → `5` → `3` → `4` → `6` → **`7`** → `0`。

## 5. 选项呈现

- **替换**：仅 `analysis-evidence` 且 eligible 的 `replace:<包>@<版本>`（最多 3）+ 改轨 + **`other`**。离线模式保留已复核版本可选（registry 新鲜度只警告，不否决）。
- **删除**：确认删除 + 改轨 + **`other`**。
- **原生改造**：确认原生 +（若有）改轨到替换/删除/父包 + **`other`**。不再提供会假死的「拒绝原生」。
- **父包**：主问含 pin-override / remove-feature / **`other`**；选处置父包后追问 `包<-父包`。
- **禁止**：同库升级、保留现状、限期豁免、`reject-native-refactor`。

## 6. 常见误读

1. 精确升级 → 本来就不做人选型。
2. 开放目标但 Agent 跳过队列 → 协议违规；现应见 exit `7` 与横幅。
3. 把 `primary_track` / curated 表当成已选型。
4. 把 `disposition-selected` 当成可以开始改代码。

核对：首页决策状态、确认阶段、`Human Confirmation Queue`、exit 是否为 `7`。

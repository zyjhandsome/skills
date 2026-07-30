# 决策记录字段说明

在对 override、非主 Owner 钉扎、排除、移除或替换给出推进建议之前，须为**每个组件（或同一族决策单元）**填完整条记录。

## 状态枚举映射（必读）

三层状态用词必须按下表对齐，禁止混用旧词（如 `proceed-selected`、`needs_choice` 作为行状态）。

| 层 | 字段 | 允许取值 |
|---|---|---|
| 报告顶层 | `decision_status` | `needs_choice` / `not_needed` / `decided` |
| 确认队列行 + 决策记录「确认队列状态」 | 同一套 | `ready` / `blocked` / `decided` / `deferred` |
| 决策记录「建议处置」 | `recommended_treatment` | 见 `treatment-ladder.md`（含处置义 `defer`） |
| 决策记录「方向」 | `direction` | `upgrade` / `downgrade` / `same` / `unknown`（移除/替换不是方向，用处置字段） |
| 确认选项 | 队列「选项」+ 记录「推荐确认选项」 | `proceed:g:a:v` / `remove` / `exclude` / `replace:g:a[:v]` / `defer` / `other` |

| 人工答复 | 队列/记录「确认队列状态」 | 顶层 `decision_status`（该批无可问项后） |
|---|---|---|
| `proceed:…` / `remove` / `exclude` / `replace:…` | `decided` | 全部清完 → `decided` |
| `defer` | `deferred` | 同上 |
| （证据/存在性/非 GA/基线缺口，尚未可问） | `blocked` | 若仍有其他 `ready` → `needs_choice` |
| 等待答复 | `ready` | `needs_choice` |

处置义 `recommended_treatment=defer`（分析认为暂无可行路径）≠ 人工 `defer` 答复。存在性/非 GA 的行保持队列 `blocked`，**不得**用人工 `defer` 直接解冻；须先重述可达目标（或明确放弃该行并进入 follow-up 波次改写候选）。

## 字段

| 字段 | 所需证据 |
|---|---|
| 组件 | 精确 `groupId:artifactId`（有 classifier 时写明）与受影响模块 |
| 版本 | 当前与目标的**解析后**版本；`remove`/`exclude` 可无目标，记 `—` |
| 目标存在性 | `target_artifact_exists`：`yes` / `no` / `unknown` / `n/a`（仅无目标处置） |
| 目标通道 | `target_channel`：`ga` / `non-ga`（有目标时必填；非 GA 默认不可 `ready`） |
| 建议处置 | `recommended_treatment`（见 `treatment-ladder.md`） |
| usage_status | direct：`used` / `unused` / `ambiguous` |
| introducer | 传递依赖：`introducer_gav` + `introducer_upgrade_available` |
| 替代候选 | `replace-*`：1–3 个坐标 + 维护信号（仅描述） |
| scope / optional / exclusions | 解析后的 Maven/Gradle 作用域；决定变更是否触及生产路径 |
| 依赖路径 | 完整的直接 / 托管 / 传递路径 |
| 有效 Owner | parent、BOM、platform、plugin、直接声明或传递来源 |
| 权威层 | `jdk` / `boot-bom` / `platform-plugin` / `app-library` |
| Owner 阶梯档位 | 见 `owner-and-resolution.md`：`1-owner-bump` → `2-property-override` → `3-family-bom` → `4-per-gav-pin` → `5-exclusion-direct`；推荐写明落在哪一档 |
| 主 Owner 动作 | 已尝试兼容的主 Owner 升级或属性覆盖，或已用证据证伪该路径；属性名须在 BOM 中核实 |
| 残差冲突 | 主 Owner 动作之后仍存在的图/收敛证据（本技能不改构建时可写预期） |
| 兼容性 | 发行说明、支持矩阵或可复现说明；`exclude` 须写 CNFE/回归警告 |
| 验证 | 已命名的静态/单测/集成/契约/安全/性能/冒烟检查；MINOR/MAJOR/降级须命名 japicmp/revapi 等机器可检 API 差异项 |
| 迁移路径选项 | MAJOR 坐标/包名迁移或 `replace-*` 时，命名既有 recipe/codemod（含 URL）及其残余风险；**仅描述，不执行** |
| 回滚 | 可观察触发条件 + 要恢复的精确版本或配置 |
| 责任人 | 负责人/团队；若有 override，含拆除跟进条件 |
| 入口来源 | `inventory` / `exact-table` / `cve` / `other` |
| 方向 | `upgrade` / `downgrade` / `same` / `unknown` |
| 确认队列状态 | 与确认队列表同一枚举（上表） |
| 推荐确认选项 / 人工答复 | 与 `human-confirmation-gates.md` 选项词表一致 |

## 不算兼容性证据

- 截止日期本身
- 仅编译成功
- 仅启动成功
- 仅有版本属性、无解析证明
- 结构校验器（`validate_report.py`）通过本身
- “最新”中央仓库版本（无安全公告 / changelog 区间）

## Override / force-align 破例条件

须同时满足：

1. 有效主 Owner 已知  
2. 处置阶梯更优档（remove / upgrade-owner / upgrade-introducer / exclude-with-evidence）已尝试或已证伪  
3. Owner 阶梯 1–3 档已尝试或已证伪（含属性覆盖；属性名已在 BOM 核实）  
4. 按上述推理后残差冲突仍在  
5. 目标为 GA，且与 Boot 线及重要消费者兼容  
6. 已为受影响行为命名聚焦验证（含适用的 API 差异检查）  
7. 已记录回滚触发条件与精确恢复目标  
8. 已指定拆除或上游对齐责任人  

否则只建议 `defer` 或更优处置档。

# 决策记录字段说明

在对 override、非主 Owner 钉扎、排除、移除或替换给出推进建议之前，须为**每个组件（或同一族决策单元）**填完整条记录。

## 状态枚举映射（必读）

三层状态用词必须按下表对齐，禁止混用旧词（如 `proceed-selected`、`needs_choice` 作为行状态）。

| 层 | 字段 | 允许取值 |
|---|---|---|
| 报告顶层 | `decision_status` | `needs_choice` / `not_needed` / `decided` |
| 确认队列行 + 决策记录「确认队列状态」 | 同一套 | `ready` / `pending` / `blocked` / `decided` / `deferred` |
| 决策记录「建议处置」 | `recommended_treatment` | 见 `treatment-ladder.md`（含处置义 `no-viable-path`；**不是**人工 `defer`） |
| 决策记录「方向」 | `direction` | `upgrade` / `downgrade` / `same` / `unknown`（移除/替换不是方向，用处置字段） |
| 确认选项 | 队列「选项」+ 记录「推荐确认选项」 | `proceed:g:a:v` / `remove` / `exclude` / `replace:g:a[:v]` / `defer` / `other` |

| 人工答复 | 队列/记录「确认队列状态」 | 顶层 `decision_status`（该批无可问项后） |
|---|---|---|
| `proceed:…` / `remove` / `exclude` / `replace:…` | `decided` | 全部清完 → `decided` |
| `defer` | `deferred` | 同上 |
| （证据/存在性/非 GA/claimed-from 缺口，尚未可问版本移动） | `blocked` | 若仍有其他 `ready`/`pending` → `needs_choice` |
| 目标可达但 tooling/tree 未证实基线 | `pending` | `needs_choice`（选项仅 `defer`/`other`） |
| 等待版本/处置答复 | `ready` | `needs_choice` |

处置义 `recommended_treatment=no-viable-path`（分析认为暂无可行路径）≠ 人工 `defer` 答复。存在性/非 GA 的行保持队列 `blocked`，**不得**用人工 `defer` 直接解冻；须先重述可达目标（或明确放弃该行并进入 follow-up 波次改写候选）。

降级/同版重对齐使用 `move-self` / `move-owner` / `move-introducer`，
不要用名称相反的 `upgrade-*`；真正方向仍由 `direction` 字段决定。

## 字段

`validate_report.py` 在 `analysis_status=complete` 时强制的字段见
`scripts/validate_report.py` 的 `DECISION_RECORD_REQUIRED_FIELDS`（模板
`templates/decision-record.md` 同表）。下表「完整包推荐」列：校验器不强制但
Agent 仍应按场景填写。

| 字段 | 完整包推荐 | 所需证据 |
|---|---|---|
| 组件 | 强制 | 精确 `groupId:artifactId`（有 classifier 时写明）与受影响模块 |
| 版本 | 强制 | 当前与目标的**解析后**版本；`remove`/`exclude` 可无目标，记 `—` |
| 目标存在性 | 强制 | `target_artifact_exists`：`yes` / `no` / `unknown` / `n/a`（仅无目标处置） |
| 目标通道 | 推荐（有目标时） | `target_channel`：`ga` / `non-ga`；非 GA 默认不可 `ready` |
| 请求目标 | 替代行强制 | `requested_gav` / `requested_to` / `requested_target_exists` |
| 推荐替代目标 | 替代行强制 | `recommended_*`；须独立探测且为 `yes` 才可 `ready` |
| 建议处置 | 强制 | `recommended_treatment`（见 `treatment-ladder.md`） |
| usage_status | 推荐（direct） | `used` / `unused` / `ambiguous` |
| introducer | 推荐（传递） | `introducer_gav` + `introducer_upgrade_available` |
| baseline_evidence_status | 推荐（基线未证实或工具待恢复时） | `confirmed` / `pending-tooling` / `pending-tree` / `mismatch` |
| 下一步补证 | 推荐（pending baseline） | 有序清单：恢复 mvn/JAVA_HOME → 分期 leaf tree/insight → 证实 claimed `from`（见 `next-action-choice-menus.md` §A） |
| 路径选项菜单 | 推荐（传递升降级） | A–E：introducer / force-align / 换 starter / 换栈 / 原生改造 + 各条证据摘要（见同文件 §B） |
| 替代候选 | 替代行强制 | 1–3 个版本或坐标 + 维护信号 |
| scope / optional / exclusions | 强制 | 解析后作用域；决定是否触及生产路径 |
| 依赖路径 | 强制 | 完整的直接 / 托管 / 传递路径 |
| 有效 Owner | 强制 | parent、BOM、platform、plugin、直接声明或传递来源 |
| 权威层 | 强制 | `jdk` / `boot-bom` / `platform-plugin` / `app-library` |
| Boot 线 | 推荐 | 字段值如 `3.2.x`；目录 token 为 `boot-3.2.x` / `no-boot` |
| 构建变体 / 批次范围 | 强制 | profile/property slug + 有界模块/族 slug |
| Owner 阶梯档位 | 推荐 | `1-owner-bump` → `2-property-override` → `3-family-bom` → `4-per-gav-pin` → `5-exclusion-direct` |
| 主 Owner 动作 | 强制 | 已尝试或已证伪；属性名须在 BOM 核实 |
| 残差冲突 | 推荐 | 主 Owner 动作后仍在的图/收敛证据 |
| 兼容性 | 强制（URL） | 发行说明/支持矩阵；`exclude` 须写 CNFE/回归警告 |
| 验证 | 强制 | 已命名检查；MINOR/MAJOR/降级须命名 API 差异项 |
| 迁移路径选项 | 推荐（MAJOR/`replace-*`） | 命名 recipe（含 URL）及残余风险；**仅描述，不执行** |
| 回滚 | 强制 | 可观察触发条件 + 精确恢复目标 |
| 责任人 | 强制 | 负责人/团队 |
| 入口来源 | 强制 | `inventory` / `exact-table` / `cve` / `other` |
| 方向 | 强制 | `upgrade` / `downgrade` / `same` / `unknown` |
| 确认队列状态 | 强制；须与报告确认队列同行一致 | `ready` / `pending` / `blocked` / `decided` / `deferred` |
| 推荐确认选项 / 人工答复 | 强制（decided/deferred 须有答复） | 与 `human-confirmation-gates.md` 词表一致 |

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

否则只建议 `no-viable-path` 或更优处置档。

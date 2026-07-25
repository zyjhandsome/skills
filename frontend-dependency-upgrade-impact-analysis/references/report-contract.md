# 报告契约

## 目录

1. 必需章节
2. 字段要求
3. Markdown 校验
4. 语言规则
5. 完成状态
6. 输出路径

## 1. 必需章节

Markdown 必须按以下顺序包含中文可见标题，并保留对应的英文机器锚点：

| 机器锚点 | 中文可见标题 |
|---|---|
| `Upgrade Summary` | 升级摘要 |
| `Release Notes And Changelog Evidence` | 发布说明与变更日志证据 |
| `Breaking Changes And Migration Notes` | 破坏性变更与迁移说明 |
| `Dependency Changes` | 依赖变化 |
| `Diff Evidence Used` | 使用的差异证据 |
| `Code References` | 代码引用 |
| `Detailed Code Modification Points` | 详细代码修改候选 |
| `Business Impact` | 业务影响 |
| `Technical Risks` | 技术风险 |
| `Test Scope` | 测试范围 |
| `Rollout And Rollback` | 发布与回滚 |
| `Conclusion` | 结论 |

锚点形态为 `<!-- section: <机器锚点> -->`，锚点不作为人类可见标题。

## 2. 字段要求

### Upgrade Summary

package、analysis mode、governance/upgrade reason、from、to、recommended action、selection status、decision status、constraints、change type、dependency type、manifest spec、lock direct version、baseline status、risk score、risk level、evidence completeness。

整单摘要另需：

- `behavior_parity_required`：默认为 `yes`；仅当用户显式允许行为变化/删除/替换时为 `no`
- `importer_resolution`：`confirmed` 或 `failed`（失败时报告状态与 `analysis_status` 均为 `blocked`，并在待人工决策中包含 `__frontend_workspace__`）
- `node_runtime_status`、`execution_readiness`、`current_host_node`、`selected_project_node`
- `selected_project_node`：仅在存在权威项目约束或经证据明确指定且通过校验时填写；`node_runtime_status=unknown` 且无约束时必须为空
- 批次计数：精确升级数 / 待人工决策数 / blocked 数
- `report_paths`：实际写入路径；键为 `markdown`，可选 `json`

### Dependency Changes

必须呈现 manifest、lock、peer、engines、overrides/resolutions。另需在本章包含“Node 运行时兼容性”小节，呈现本机当前 Node、项目约束来源、版本管理器、已安装兼容候选、所选精确项目 Node、EOL 警告、切换策略、实施阻塞项和恢复计划。目标未知时必须先呈现删除状态、证据、阻塞点、未知项、覆盖范围和可信度；再按需呈现同库与替代库候选。候选矩阵至少包含 `compliance_status`、核查标准、排除原因、证据 URL、兼容性、合规/维护、迁移成本、验证范围和回滚难度。`eligible` 必须有核查标准与证据 URL。

### Detailed Code Modification Points

package、file、line、category、current usage、upstream reason、recommended change、required validation、priority、confidence。

### Risk

七个因子（含 peer 兼容性）、各自分值、总分、自动等级、覆盖等级（如有）、不确定项。
Node 约束冲突、EOL 运行时、需要全局切换或恢复未验证时，作为独立技术风险和 High 覆盖依据呈现，不擅自增加第八个评分因子。

### Evidence

版本、发布日期、版本级 repository/source/validation、release 与 changelog 各自状态和摘要、来源 URL、九个证据维度及完整性/歧义警告。不得把 npm 包详情页本身当作迁移说明，也不得把 tag 或 URL-only Release 当成 release 正文。

## 3. Markdown 校验

- 必需章节和关键字段必须来自同一个结构化分析对象；
- 每张表的所有数据行必须与表头列数一致；
- 外部 URL 保持完整并单独列出，避免把多个来源拼成一个不可识别字段；
- 空节写 `未建立` 或 `需要 Agent 复核`，不得省略。
- Node 运行时信息必须来自整单结构化 `node_runtime` 对象，并复用于升级摘要、依赖变化、技术风险、测试范围和结论。

## 4. 语言规则

- 默认报告语言为简体中文（`zh-CN`）。
- 可见标题、正文、表格标签、风险结论以及上游 release notes、changelog、migration guide 的摘要默认使用中文。
- 包名、版本号、路径、命令、代码标识符、URL、API 名称和 `draft` / `blocked` / `complete` 等机读枚举保持原文。
- 生成器采集的上游原文只是证据输入。报告标记为 `complete` 前，Agent 必须将未解释的外文内容翻译或忠实概括为中文。
- 只有用户明确指定其他语言时才切换。

## 5. 完成状态

报告首页必须声明：

- `complete`：全部闸门通过；
- `draft`：存在证据、映射或人工复核缺口；
- `blocked`：baseline/version/workspace 等阻塞项未解决。

生成器默认输出 `draft`。只有 Agent 完成上游证据补齐、调用图/业务映射和人工复核后，才能将其提升为 `complete`。

同时分离声明：

- `analysis_status`：`partial`、`blocked` 或经人工复核后的 `complete`；
- `decision_status`：`not_needed` 或 `needs_choice`。

候选版本、替代库和删除可行性属于决策证据，不是已批准结论。`analysis_status=complete` 可以与 `decision_status=needs_choice` 同时存在。

当 `behavior_parity_required=yes`（默认）时：删除与替代库结论只能作为待选证据；默认推荐同库精确升级（若存在合规候选）；必要 API/配置适配可列为改造候选并标注为适配。

## 6. 输出路径

报告是当前任务的证据附件，不是平行状态源。

解析顺序：

1. 调用方显式 `--output-dir`
2. 调用方显式提供的既有 `--change-dir` → 写入  
   `<change-dir>/evidence/frontend-dependency-upgrade/`
3. 未指定时不猜测 active change，回退到 `<project-root>/dependency-upgrade-report/`，并在报告中声明假设；需要归档到某次任务时要求调用方显式提供 `--change-dir`

本技能可以在**已存在**的 change/任务目录内创建 `evidence/frontend-dependency-upgrade/`，但不得自行创建 change 或生命周期状态。

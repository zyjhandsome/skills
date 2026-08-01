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
| `Human Confirmation Queue` | 人工确认队列 |
| `Conclusion` | 结论 |

锚点形态为 `<!-- section: <机器锚点> -->`，锚点不作为人类可见标题。

## 2. 字段要求

### Upgrade Summary

package、analysis mode、governance/upgrade reason、from、to、recommended action、selection status、decision status、constraints、change type、dependency type、manifest spec、lock direct version、baseline status、risk score、risk level、evidence completeness。

包级 `selection_status` 取值：`selected`（已确认推进或已选定处置）、`needs_explicit_choice`（等待人工确认：开放目标处置选型，或精确升级 `proceed-exact` 推进/延期）、`not_applicable`（该包不需要选择动作）。

首页与结论还必须声明批次实施闸门：

- `batch_implementation_gate`：`frozen` / `ready`
- `batch_gate_reasons`：导致 `frozen` 的原因列表（确认未完成、精确升级 blocked、Node 执行 blocked 等）

`frozen` 时整批不得进入 Stage B（实施计划）或 Stage C（实施）。详见 `human-confirmation-gates.md`。

整单摘要另需：

- `behavior_parity_required`：默认为 `yes`；仅当用户显式允许行为变化/删除/替换时为 `no`
- `importer_resolution`：`confirmed` 或 `failed`（失败时报告状态与 `analysis_status` 均为 `blocked`，并在待人工决策中包含 `__frontend_workspace__`）
- `node_runtime_status`、`execution_readiness`、`current_host_node`、`selected_project_node`、`selected_node_support`
- `selected_project_node`：仅在存在权威项目约束或经证据明确指定且通过校验时填写；`node_runtime_status=unknown` 且无约束时必须为空，并硬阻断项目命令直至建立精确项目 Node
- lock 格式字段（`lockfileVersion` / yarn metadata）默认冻结；未批准格式迁移时不得把格式漂移写入实施结论
- 批次计数：精确升级数 / 待人工决策数 / blocked 数
- `report_paths`：实际写入路径；键为 `markdown`，可选 `json`，可选 `upstream_evidence`（报告旁 `upstream-evidence/` 目录；仅在目录实际存在时出现；`--cleanup-upstream-evidence` 删除后不再保留该键）

### Dependency Changes

必须呈现 manifest、lock、peer、engines、overrides/resolutions。`catalog:` 声明需同时呈现协议与解析出的有效范围。另需在本章包含“Node 运行时兼容性”小节，呈现本机当前 Node、项目约束来源、版本管理器、已安装兼容候选、所选精确项目 Node、`selected_node_support` 与发布计划核对日期、切换策略、实施阻塞项和恢复计划。目标未知时必须先呈现「依赖来源与父包链」，再呈现删除状态、证据、阻塞点、未知项、覆盖范围和可信度；随后**始终**呈现替代库候选与处置方案选项，不因某一路径已有候选而省略其他路径。**不得出现同库目标版本候选表**：未指定目标版本的包不以同库升级收场。候选矩阵至少包含 `compliance_status`、核查标准、排除原因、证据 URL、兼容性、合规/维护、迁移成本、验证范围和回滚难度。`eligible` 必须有核查标准与证据 URL。

替代库候选另需 `origin`（`analysis-evidence` 或 `curated-map`）、推荐版本（未解析时写 `待解析`）、`兼容回退版本`、`排序`、`排序依据`、`约束匹配`、peer/engines，并在候选 `engines.node` 与所选项目 Node 冲突时写入排除原因。`curated-map` 候选恒为 `compliance_status=unknown`，不得据此改变推荐动作。

排序只用机器可核信号，优先级固定为 `ALTERNATIVE_RANK_SIGNALS`：`human-reviewed`、`project-constraint-fit`、`not-deprecated`、`recent-release`、`declared-license`；逐项取值写入“排序依据”列。`约束匹配` 取 `fits` / `unknown` / `conflicts`。排序只是呈现顺序，不改变 `recommended_action`，也不构成选型。

`research_status` 不为 `reviewed` 时，必须呈现「替代方案调研任务」小节：用法画像、`RESEARCH_CRITERIA` 筛选标准、回填方式。

目标未知时必须呈现「原生重构方向」小节：方案状态（`established` / `needs-research`）、可直接改用的原生能力、需自建的能力、按调用点分组的改造范围、`REFACTOR_STAGES` 分阶段路径、改造规模、验证范围、回滚、未决项、影响面、行为等价核对清单，以及逐调用点改造表（文件、行号、类别、当前用法、等价实现思路、行为差异风险、验证点、可信度）。方向必须来自本轮扫描证据，仅有声明引用时状态保持 `needs-research`。

改造规模只取 `S`/`M`/`L`，由调用点数、文件数与是否跨公共包装器按固定阈值算出，必须写出计数依据；不得给出工时估算。

处置方案选项表固定覆盖 `remove-dependency`、`replace-with-alternative`、`handle-parent-package`、`native-platform-capability`、`in-house-reimplementation`、`isolate-behind-wrapper`、`internal-fork`、`remove-feature`，每项标注 `evidence-available`、`needs-research` 或 `not-applicable`、适用条件、本轮证据与决策所需依据。菜单不含以“不变更”收场的选项，也不含同库升级。

「依赖来源与父包链」小节必须写明 `provenance.kind`（`direct` / `both` / `phantom` / `transitive` / `unknown`）、manifest 声明字段、代码是否有直接用法、判定证据与未决项。存在父包时另需父包表：父包、已解析版本、对该包的 range、父包最新稳定版、是否已摆脱该依赖（`dropped`/`still-depends`/`unknown`）、说明；父包链最多展示 5 条，超出只计数。解析出 overrides 最低可行版本时写明该版本及会被破坏的父包约束。

目标未知时还要在依赖变化中写明主轨判定：`primary_track` 取 `remove`、`replace`、`native-refactor`、`handle-parent`、`fix-phantom` 或 `pending-removal-evidence`，附判定依据与备选轨道。判定顺序固定为「先看依赖来源 → 是否真的被使用 → 是否有可换的包 → 都没有则原生改造」。精确升级主轨为 `proceed-exact`。主轨只表示本轮证据指向哪条路径，开放目标人可改轨。

### Human Confirmation Queue

所有当前 `confirmation.status=ready` 的包（开放目标 + 精确升级）同一波提问；`switch:<track>` / `handle-parent` 后续题下一波；`blocked` 不问。必须包含：决策记录文件路径、`batch_implementation_gate`、队列总表（包、主轨、`ready`/`blocked`/`decided`、问题、前置条件），精确升级批量确认表（若有），以及每个 `ready` 包的选项表（选项 ID、选项、说明）。首页/结论横幅与确认队列须写明：exit `7` / `needs_choice` 时**下一动作=照确认队列向用户提问，不是等待放行**。

选项 ID 形态固定：`replace:<包>@<版本>`、`remove`、`remove-usage`、`switch-to-declared`、`native-refactor`、`handle-parent`、`pin-override:<包>@<版本>`、`parent-upgrade:<包>@<版本>`、`parent-replace:<包>`、`parent-remove:<包>`、`isolate-behind-wrapper`、`internal-fork`、`remove-feature`、`switch:<轨道>`、`other`。ready 问题末位固定为 `other`。**不得出现 `same-package:` 或 `reject-native-refactor`。**

`switch:<轨道>` 与对话中的 `handle-parent` 都不是最终选择，不得写入决策文件。Agent 在 `switch:<轨道>` 后必须改问同包已渲染的「改轨问题：`<轨道>`」整表（含该轨完整选项）。

`handle-parent` 轨为两段式：主问题可选 pin-override / remove-feature / other（可直接落盘），或在对话中选「处置父包」后再按父包逐个追问；追问的 `package` 形如 `<目标包><-<父包>`。全部父包追问确认后主包才算选型完成。

`blocked` 的包不呈现选项，只写阻塞原因与前置条件；横幅标「待补证据」。`ready` 包横幅标「待人工选型」。报告须声明本轮确认阶段 `evidence` / `choice` / `mixed` / `none`。

已有决策时追加「人工决策记录」表：包、轨道、选择、选定包、选定版本、状态（`confirmed` / `invalidated` / `unknown-package`）、来源、时间、理由或失效原因。确认后的建议动作为 `disposition-selected`（开放目标）或 `proceed-selected` / `deferred`（精确升级）——均为 Stage A 终点，不是实施批准。

### Detailed Code Modification Points

package、file、line、category、current usage、upstream reason、recommended change、required validation、priority、confidence。

### Risk

七个因子（含 peer 兼容性）、各自分值、总分、自动等级、覆盖等级（如有）、不确定项。不确定项必须逐条可见（无则写 `无`），并写出复算方式。
Node 约束冲突、EOL 运行时、需要全局切换或恢复未验证时，作为独立技术风险和 High 覆盖依据呈现，不擅自增加第八个评分因子。

### Business Impact

只有已建立页面/流程映射的行才可写入风险等级；仅有文件引用、流程未映射的行必须写 `待评估`，不得继承包级风险等级。

### Evidence

版本、发布日期、版本级 repository/source/validation、release 与 changelog 各自状态和摘要、来源 URL、九个证据维度及完整性/歧义警告。不得把 npm 包详情页本身当作迁移说明，也不得把 tag 或 URL-only Release 当成 release 正文。

九个证据维度固定为：`registry`、`repository`、`release`、`changelog`、`migration`、`compatibility`、`security`、`support`、`license`。

若存在报告旁 `upstream-evidence/`，证据节须给出本地证据包路径；各包须声明是否发生本地回读（`本地证据回读：yes|no`）。本地回读不得单独把证据标为 `complete`。

## 3. Markdown 校验

- 必需章节和关键字段必须来自同一个结构化分析对象；
- 每张表的所有数据行必须与表头列数一致；
- 外部 URL 保持完整并单独列出，避免把多个来源拼成一个不可识别字段；
- 空节写 `未建立` 或 `需要 Agent 复核`，不得省略，也不得输出空反引号；
- 键值型机器字段（证据维度、peer、engines、已安装 Node、仓库谱系）以 `key=value` 或子列表呈现，不得直接倾倒 JSON 字面量；`report_paths` 以带标签的子列表呈现。
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

生成器默认输出 `draft` / `analysis_status=partial`。Agent 完成上游证据补齐、调用图/业务映射和人工复核后，必须再跑一遍并显式传入 `--finalize-review`；闸门全部通过时生成器才把报告状态与 `analysis_status` 升为 `complete`。`--offline`、`needs_choice`、`blocked`、`option_status=missing` 或基线未对齐时 finalize 被拒绝（exit `2`，报告保持原状态）。

同时分离声明：

- `analysis_status`：`partial`、`blocked` 或经 `--finalize-review` 的 `complete`；
- `decision_status`：`not_needed` 或 `needs_choice`。
- `batch_implementation_gate`：`frozen` 或 `ready`。

候选版本、替代库、处置方案选项和删除可行性都属于决策证据，不是已批准结论。呈现完整选择面不等于推荐其中任何一条，也不等于人选轨完成。精确升级的目标版本明确也不等于已批准推进。

**完成态互斥：** `analysis_status=complete` **不得**与 `decision_status=needs_choice` 同时成立。确认队列未清空前，报告状态保持 `draft`、`analysis_status` 最高为 `partial`；生成器在无更高优先级阻塞时以 exit `7` 表示「草稿已写出、待人工确认；Agent 下一动作=照队列提问/补证据，不是等待放行」。人选轨/推进写入决策文件并重跑后，`decision_status` 变为 `not_needed`；Agent 完成证据复核并以 `--finalize-review` 重跑升 `analysis_status=complete`——这才是本技能终点。`batch_implementation_gate=frozen` 不阻止该分析终点；仅当闸门为 `ready` 时才可交接 Stage B。本技能终点是定稿分析/决策报告，不是实施。

选项完整性闸门：未指定目标版本的包必须至少产出一个可执行选项（替代包、已成立的原生重构方案、已解析出父包的父包处置，或 `safe_removal_candidate`/`requires_migration` 的删除路径）。任一包 `option_status=missing` 时，结论必须点名该包，且报告不得提升为 `complete`。该闸门只约束完成状态，不改写 `recommended_action`。

当 `decision_status=needs_choice` 时，报告首页与结论章必须置顶「待人工确认」说明，指向「人工确认队列」，并写明**下一动作=提问**；Agent 不得只交付 draft 后等待放行，不得在未提问、未写入决策文件、未重跑、未复核升 `complete` 前宣称本技能完成。`batch_implementation_gate=frozen` 时不得开实施计划或执行变更。细则见 `human-confirmation-gates.md`。

当 `behavior_parity_required=yes`（默认）时：删除、替换、原生改造与父包处置都必须保持对外可观察行为不变，且都只能作为待选证据；报告不得偏好其中任何一条，也不得把同库升级作为选项；必要 API/配置适配可列为改造候选并标注为适配。

## 6. 输出路径

报告是当前任务的证据附件，不是平行状态源。

解析顺序：

1. 默认：调用方提供既有 `--change-dir` → 写入  
   `<change-dir>/evidence/frontend-dependency-upgrade/`  
   OpenSpec 典型路径：`openspec/changes/<id>/evidence/frontend-dependency-upgrade/`
2. 可选覆盖：调用方显式 `--output-dir`（覆盖 `--change-dir` 解析）
3. 两者皆无时直接报错；不得回退到项目根下的平行报告目录，也不得猜测 active change

本技能可以在**已存在**的 change/任务目录内创建 `evidence/frontend-dependency-upgrade/`，但不得自行创建 change 或生命周期状态。

精确升级默认在报告目录下创建 `upstream-evidence/`（见 `lockfile-and-evidence.md`）。`report_paths.upstream_evidence` 指向该目录的绝对路径。

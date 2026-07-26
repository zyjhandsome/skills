# 目标发现、删除与替代评估

## 1. 模式选择

| 输入 | 模式 | 输出 |
|---|---|---|
| `package + exact to` | 精确升级 | `from → to` 区间影响 |
| `package` | 开放目标处置评估 | 删除 / 替换 / 原生改造 / 父包处置，不含同库升级 |
| `package + 不合规原因` | 合规评估 | 依据核验和合规候选 |
| `package + 评估删除` | 删除评估 | 删除结论、证据、未知项和验证范围 |

无论哪种模式，先确认 workspace、manifest、包管理器、lockfile/importer 和当前直接解析版本。当前版本无法建立时标记 `blocked`，不继续给出可批准结论。

## 2. 目标未知时

**未指定目标版本的包只有四条出路：删除、替换、原生改造、处置父包。同库升级不是选项**——registry 上有没有更高版本都一样。这类包上榜是因为包本身要走，版本号往前挪不解决让它上榜的那个问题。确需升级请改用 `--upgrade package::<精确版本>` 走精确升级模式。

按以下决策顺序形成建议：

```text
确认真实基线
  → 判定依赖来源（direct / both / phantom / transitive）
  → 来源为 transitive：只能处置父包或 overrides 钉版本
  → 来源为 phantom：先消除未声明用法
  → 其余：评估能否删除
  → 删除不成立、不确定或未被人选择
  → 比较替代库及精确版本
  → 无替代库时给出原生改造方向
  → 仍无方案时考虑隔离、fork 或移除功能
```

这是**推荐**优先级，不是呈现门槛：目标未知时删除评估、替代库候选、原生改造方向和处置方案选项要一并呈现（见第 4 节），让人一次看全所有可选路径。

这是处置建议的优先级，不要求所有取证工具串行运行。为减少重复请求，可以并行收集 registry、上游和代码证据，但报告与结论必须按上述顺序表达。

### 2.1 默认行为姿态（行为守恒）

**默认开启**（无需用户在提示词里写「行为守恒」）：

1. **守恒对象是行为，不是某条路径**：删除、替换、原生改造、父包处置都会改变依赖构成，因此行为守恒不再偏好其中任何一条，而是要求每条路径都保持对外可观察行为不变；
2. **不代选**：`recommended_action` 只表示下一步动作，不等于选型结论；
3. **删除 / 换库 / 改造 / 动父包**：一律标记为 `needs_explicit_choice`，不得写入已选定范围，也不得自动实施；
4. **适配边界**：为实现已选定精确目标所必需的 API/配置适配**允许**，并标为适配而非业务变更；禁止顺手重构业务/UI，禁止改后端契约（除非调用方明确纳入范围）；
5. 报告摘要声明 `behavior_parity_required=yes`。

仅当用户**显式**说出例如 `允许行为变化` / `允许删除` / `允许替换`（或生成器 `--allow-behavior-change`）时，才关闭上述约束。

「不是最新版」单独不构成必须变更的理由。

删除不成立或未被选择时，再判断为什么需要变化：

1. 仓库或组织政策；
2. 官方安全公告与受影响版本范围；
3. license 限制；
4. Node、浏览器、框架、peer 或 engine 不兼容；
5. 官方停止维护、归档或替代声明；
6. 可复现的业务或工程问题。

如果理由未知，将其列为开放问题，不把“不是最新版”自动视为不合规。

### 2.2 依赖来源判定

来源决定哪些路径**存在**：manifest 里没有的声明摘不掉，本仓库不调用的包也没法原生改造。判定用三份证据交叉：manifest 声明、lock 依赖边、代码直接用法。

| `provenance.kind` | 判定条件 | 可用路径 |
|---|---|---|
| `direct` | manifest 已声明，且 lock 中无其他包依赖它 | 删除 / 替换 / 原生改造 |
| `both` | manifest 已声明，同时被其他包依赖 | 同上，但删除只是「移除直接声明」，包仍会以传递依赖留在 lock；需连父包一起定方案 |
| `phantom` | manifest 未声明，但代码中有直接用法 | 移除用法 / 改用已声明依赖或原生能力；**不接受「补个声明了事」** |
| `transitive` | manifest 未声明，代码无用法，仅由父包引入 | 处置父包 / overrides 钉版本 / 移除引入父包的功能 |
| `unknown` | 三份证据都无法定位，或存在无法排除的干扰 | 先补证据，不进入处置 |

`phantom` 判定保守：包名与 Node 内置模块或本仓库 workspace 包重名时降级为 `unknown`；判定成立时也必须在「未决项」中列出仍需人工排除的干扰源（tsconfig paths、构建 alias、子包 manifest 声明、类型包、运行时注入）。缺少可解析 lockfile 时无法区分「未安装」与「由父包引入」，同样降级为 `unknown`。

### 2.3 父包链与 overrides

传递依赖要给出父包证据，否则「处置父包」不可执行：

- **父包链**：从 lock 反向依赖图做广度优先，取最短的若干条根到目标路径，每包最多展示 5 条，超出部分只计数；
- **每个父包**：已解析版本、对目标包声明的 range、父包最新稳定版，以及该最新稳定版是否**已不再依赖**目标包（`dropped` / `still-depends` / `unknown`）——已摆脱的父包是成本最低的处置对象；
- **overrides/resolutions 版本**：取满足**全部**父包 range 且满足项目 Node 的**最低**可行稳定版本。取最低而非最新，是因为 override 是强加给这些父包的解析结果，动得越小越不容易破坏它们。没有任何版本能同时满足时，给出破坏面最小的版本并逐条列出会被破坏的父包 range。

离线模式下不解析父包最新稳定版与 overrides 版本，统一记为未决项。

## 3. 删除评估

删除结论使用以下状态：

- `safe_removal_candidate`：已建立无业务、运行时、动态、构建期、工具链、peer 或间接 consumer，并有移除验证方案；仍需人选择；
- `requires_migration`：发现使用点；说明不能无适配删除，但不等同于删除方案不可行；
- `not_viable`：存在无法接受的行为缺口，且没有已接受的迁移、替代或功能移除方案；
- `uncertain`：证据不足，尤其是仅有静态扫描零命中；
- `not_assessed`：本轮未评估。

至少核查：

- manifest 声明和所有 lock 版本；
- 直接 import/require、CSS/插件注册和配置键；
- alias、barrel export、公共包装器及其调用方；
- dynamic import、字符串加载、运行时注册和配置驱动加载；
- package scripts、构建、测试、类型、样式、代码生成和 CI；
- peerDependencies、可选依赖、间接 consumer 和工作区跨包使用；
- 删除后需要验证的功能、失败路径、产物和回滚方式。

静态扫描用于生成候选。没有搜索命中不等于可以删除；应优先使用代码知识图谱追踪符号、包装器和调用方。

只有证据覆盖 `business/runtime/dynamic/build/tooling/peer/transitive`，且删除后的行为、验证和回滚方案明确时，才可使用 `safe_removal_candidate`。发现 import/config/consumer 时使用 `requires_migration`，不要直接写成 `not_viable`。证据不足时保持 `uncertain`。

## 3.1 主轨判定

能进入本报告且未指定目标版本的包，都已被判定需要变更。判定顺序与人的思路一致：**先看来源 → 是否真的被使用 → 是否有可换的包@版本 → 都没有则原生改造**。

| `primary_track` | 判定条件 | 含义 |
|---|---|---|
| `handle-parent` | 来源为 `transitive` | 既删不掉也改造不了，只能动父包或 overrides 钉版本 |
| `fix-phantom` | 来源为 `phantom` | 代码在用但未声明，父包一变就断，先消除这种用法 |
| `pending-removal-evidence` | 删除结论为 `uncertain` 或 `not_assessed` | 还不知道有没有被用，先补删除证据，此时**不提选型问题** |
| `remove` | 删除结论为 `safe_removal_candidate` | 删除是成本最低的收敛方式 |
| `replace` | 已确认有使用点，且存在可选的替代包@版本 | 换成一个确定的包@版本 |
| `native-refactor` | 已确认有使用点，且无可选替代包 | 只能改用平台原生能力或自建实现 |
| `proceed-exact` | 已指定精确 `to`（精确升级模式） | 不做处置选型；确认是否按该目标推进或延期 |

来源判定先于使用情况：`transitive` 与 `phantom` 直接定轨，不走删除评估门槛。来源为 `both` 时按直接依赖定轨，但 `handle-parent` 会作为备选轨道保持可见。

静态扫描零命中**不**直接进入 `remove` 轨：它只说明没搜到，不说明没用。此时给出待核清单（`business/runtime/dynamic/build/tooling/peer/transitive` 中尚未覆盖的维度加上已记录的未知项），补齐后再定轨。

主轨之外仍有证据的路径记入 `alternate_tracks` 并保持可见。主轨是本轮证据的指向，不是决定，人可以直接改轨。

## 3.2 人工确认队列

生成器产出机器可读的确认队列。问题文本与选项由生成器固定，Agent 照问，不临场发挥。

- **开放目标（无 `to`）**：**一包一问**。
- **精确升级（`proceed-exact`）**：**可同批汇总**确认 `proceed:<包>@<版本>` / `defer` / `other`。
- 选项 ID 形态：`proceed:<包>@<版本>`、`defer`、`replace:<包>@<版本>`、`remove`、`remove-usage`、`switch-to-declared`、`native-refactor`、`handle-parent`、`pin-override:<包>@<版本>`、`parent-upgrade:<包>@<版本>`、`parent-replace:<包>`、`parent-remove:<包>`、`isolate-behind-wrapper`、`internal-fork`、`remove-feature`、`switch:<轨道>`、`other`。**不存在 `same-package:` 选项**。
- 替换轨的问题只列每个候选的**推荐版本**，其余版本留在候选表里；想换版本走 `other`。
- 末位固定 `other`：自行指定包与版本，或改走其他处置方式。
- `switch:<轨道>` 是改轨答案，Agent 接着问该轨道的问题，最终结果才落盘。
- **父包两段式**：`handle-parent` 轨先问处置方式（处置父包 / overrides 钉版本 / 移除功能）；选了「处置父包」后，再按父包逐个追问升级、替换还是删除。追问的 `package` 字段形如 `<目标包><-<父包>`。
- **`both` 的删除措辞**：选项写成「移除直接声明（包仍将作为传递依赖存在）」，并附 `switch:handle-parent` 供人连父包一起处理。
- 队列状态为 `blocked` 时不提问，先补前置条件：`pending-removal-evidence` 补删除证据；`native-refactor` 未成立时补调用点证据或替代方案调研；`handle-parent` 未解析出父包时补可解析的 lockfile。

确认结果写入 `--decision-file`，格式与重验规则见 `decision-record-schema.md`。已确认的包重跑时静默沿用，证据变化导致失效则带原因重新提问。

## 4. 替代库发现

目标未知的包**一律**呈现替代库候选与处置方案选项；呈现全部选项与按第 2 节顺序给出推荐是两件事，前者保证人看得到完整选择面，后者保持行为守恒默认。

给出 1～3 个候选及精确版本，并记录：

- 能力与 API/组件模型兼容性；
- 框架、peer、engine、浏览器和 SSR 兼容性；
- license、安全、维护活跃度和发布稳定性；
- bundle/runtime 影响；
- 迁移范围、测试范围、回滚难度和长期锁定风险；
- 官方文档、仓库和包元数据来源。

不得只按下载量、星标或“流行度”选型。

### 4.1 候选来源与权重

| `origin` | 含义 | 对推荐的影响 |
|---|---|---|
| `analysis-evidence` | 人工/Agent 复核后经 `--analysis-evidence-file` 写入，带真实合规结论 | 可将 `recommended_action` 推到 `research-replacement` |
| `curated-map` | 生成器内置替代库知识表给出的线索，精确版本由 registry 实时解析 | 只是待评估证据，**不改变**推荐优先级，`compliance_status` 恒为 `unknown` |

知识表只收录有官方依据的替代路径：源包已官方弃用/归档/仅维护、上游自己指向后继方案，或平台已内置该能力；不以下载量或流行度收录。表内无条目**不等于**不存在替代方案，只表示尚未复核，此时报告要求 Agent 基于官方资料研究。两者对同一包重复时以 `analysis-evidence` 为准，未被复核的知识表候选继续保留可见。

生成器只解析**精确版本、发布日期、弃用标记、license、peer/engines**这类易变数据；候选包本身是已核对快照（`REPLACEMENT_MAP_REVIEWED`）。候选的 `engines.node` 与所选项目 Node 冲突时自动写入排除原因，不静默通过，并继续解析该库**满足当前项目 Node 的最高稳定版**作为 `兼容回退版本`，使人在“升级运行时”和“降版本使用”之间仍有可比选项。

### 4.2 候选排序

候选按机器可核信号排序，优先级固定为 `ALTERNATIVE_RANK_SIGNALS`：`human-reviewed` → `project-constraint-fit` → `not-deprecated` → `recent-release` → `declared-license`。逐项取值写入报告的“排序依据”列，同样输入必得同样顺序。

`project-constraint-fit` 三态：`fits`（已核对的 peer/engines 与项目现状一致）、`unknown`（缺少可核对声明）、`conflicts`（与所选项目 Node 或现有 peer 冲突）。无法核对的一律留 `unknown`，不猜测。

排序是**呈现顺序与依据**，不是选型结论：它不改变 `recommended_action`，`selection_status` 仍为 `needs_explicit_choice`，人可直接否决第 1 名。

### 4.3 调研任务（知识表无条目时）

知识表无条目不等于无替代方案。此时报告输出「替代方案调研任务」清单：本仓库实际用法画像、`RESEARCH_CRITERIA` 七项筛选标准、回填方式。Agent 必须据此联网调研并把结论写回 `--analysis-evidence-file`；`research_status` 为 `pending`/`curated-only` 时，该包不得视为已完成分析。

### 4.4 处置方案选项

除包替代外，每个目标未知的包都要呈现完整处置菜单，供人拍板：`remove-dependency`、`replace-with-alternative`、`handle-parent-package`、`native-platform-capability`、`in-house-reimplementation`、`isolate-behind-wrapper`、`internal-fork`、`remove-feature`。

菜单中每条路径都会产生变更：能进入本报告的包已被判定需要处置，因此不提供“保留现状”“限期豁免”这类以不变更收场的选项，也不提供“同库升级”这类换汤不换药的选项。短期确实无法完成更换时，走 `isolate-behind-wrapper`（先收敛调用面）或 `internal-fork`（承接维护），并写明触发条件与责任人。

每项标注证据状态：`evidence-available` 表示本轮已产出该路径的证据，`needs-research` 表示尚需补证，`not-applicable` 表示来源决定该路径不存在（例如未声明的包没有可摘除的声明）；三者都不表示推荐，也不构成选择。

### 4.5 原生重构方向（无可替代包时的兜底）

`native-platform-capability` 与 `in-house-reimplementation` 是两件事：前者是平台已内置该能力、可直接改用；后者是既无合规替代包也无内置能力，只能自建最小实现。

报告的「原生重构方向」不是通用模板，而是由本轮扫描证据生成：

- **可直接改用的原生能力**：知识表登记的原生路线及其能力差异；
- **需自建的能力**：原生能力未覆盖的部分；无登记时按实际用法类别逐条列出；
- **按调用点分组的改造范围**：本仓库真实命中的用法类别与文件；
- **分阶段路径**：`REFACTOR_STAGES`（冻结新增用法 → 建适配层 → 分组迁移 → 摘除声明 → 回归验证）；
- **逐调用点改造表**：文件、行号、类别、当前用法、等价实现思路、行为差异风险、验证点、可信度；
- **行为等价核对清单**：把「保持原有逻辑」拆成可核对项（按依赖类型给出，如请求类的超时/重试/取消/非 2xx 是否抛错/拦截顺序/序列化，加上边界值、错误结构、并发时序、编码时区、日志覆盖等通用项）；
- **影响面**：受影响文件、公共包装器、页面/流程、类型/构建/测试；
- **改造规模**：`S`/`M`/`L`，由调用点数、文件数、是否跨公共包装器按固定阈值算出（≤2 文件且 ≤5 调用点且不跨包装器为 S；≤10 文件且 ≤30 调用点为 M；其余为 L），只表示规模，不含工时估算；
- **验证范围与回滚**：按依赖类型给出验证范围；适配层保留一层间接，可按调用点分组回滚；
- **未决项**：仅有声明引用、无调用点证据、原生能力未登记等，都显式列出而不是默认可行。

只有存在声明以外的真实调用点证据时，方案状态才是 `established`；否则为 `needs-research`，先补调用面证据。等价实现思路是**改造候选**，必须由 Agent 结合官方文档确认，生成器不代替该确认。

### 4.6 选项完整性闸门

未指定目标版本的包必须至少产出一个可执行选项：替代包、已成立的原生重构方案、已解析出父包的父包处置，或删除（删除结论为 `safe_removal_candidate`/`requires_migration` 时算一条可执行路径）。

一个都没有时 `option_status=missing`，报告在结论中列出该包并禁止标记 `complete`。该闸门只影响完整性判定，不改写 `recommended_action`——删除评估仍开放时，下一步依然是 `review-removal`。

替代包不可行且删除不可行时：已建立重构方向则 `recommended_action=plan-native-refactor`，否则为 `blocked-pending-options`。

## 5. 决策边界

报告可以推荐候选，但不能自动选择、安装、删除或替换。保持两个独立状态：

- 分析状态：证据是否完整；
- 决策状态：是否仍需人选择。

分析完成不等于候选已批准，候选获选也不等于实施获批。外部编排流程（例如交付定框/计划技能）如需审批或持久化状态，应消费本技能的中性输出；本技能不绑定也不依赖任何编排家族的生命周期、闸门或状态目录约定。只有调用方显式提供既有 change/任务目录时，才把报告写进该目录的证据子目录。

## 6. 中性交接字段（供调用方消费）

| 字段 | 取值示例 | 调用方应如何理解 |
|---|---|---|
| `analysis_status` | `partial` / `blocked` / `complete` | `blocked` 时不得当作可实施结论；**禁止**与 `needs_choice` 同时为 `complete` |
| `decision_status` | `not_needed` / `needs_choice` | `needs_choice` 必须等人确认（开放目标选型或精确升级推进）；此时生成器 exit `7` |
| `selection_status` | `selected` / `needs_explicit_choice` / `not_applicable` | 区分已确认推进/处置与真正待选项 |
| `batch_implementation_gate` | `frozen` / `ready` | `frozen` 时整批不得开 Stage B/C；见 `human-confirmation-gates.md` |
| `constraints` | 包级约束列表 | 行为守恒等约束不得混入待决策 |
| `behavior_parity_required` | `yes` / `no` | 默认为 `yes`；为 yes 时不得把删除/换库当默认范围 |
| `report_paths` | `markdown` / 可选 `json` | 证据附件路径，不是第二状态源 |
| `pending_human_decisions` | 包级列表 | 由调用方写入其自身决策台账 |
| `alternative_candidates[].origin` | `analysis-evidence` / `curated-map` | 后者是未复核线索，不得当作已研究结论 |
| `alternative_candidates[].rank` | `1`、`2`… | 按机器信号的呈现顺序，不是选型结论 |
| `alternative_candidates[].constraint_fit` | `fits` / `unknown` / `conflicts` | `unknown` 表示无法核对，不等于可用 |
| `disposition_options[].availability` | `evidence-available` / `needs-research` / `not-applicable` | 只说明本轮是否已产出证据，不是推荐 |
| `provenance.kind` | `direct` / `both` / `phantom` / `transitive` / `unknown` | 决定哪些路径存在；`unknown` 时先补证据 |
| `provenance.override_version` | 精确版本或空 | 满足全部父包 range 的最低可行版本，仍需人确认 |
| `primary_track` | `remove` / `replace` / `native-refactor` / `handle-parent` / `fix-phantom` / `pending-removal-evidence` / `proceed-exact` | 本轮证据指向的单一路径；开放目标人可改轨 |
| `confirmation.status` | `ready` / `blocked` / `decided` | `blocked` 时不得向人提选型问题 |
| `decision.status` | `confirmed` / `invalidated` / `unknown-package` | `confirmed` 也只是选型，不是实施授权 |
| `refactor_plan.status` | `established` / `needs-research` | 仅前者可作为“无可替代包”时的兜底路径 |
| `refactor_plan.scale` | `S` / `M` / `L` | 机器可算的规模分级，不是工时 |
| `option_status` | `available` / `missing` | `missing` 时报告不得标记 `complete` |
| `research_status` | `reviewed` / `curated-only` / `pending` | 非 `reviewed` 表示替代方案调研尚未回填 |

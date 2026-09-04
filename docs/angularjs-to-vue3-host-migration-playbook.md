# AngularJS 混合页迁入 Vue3 Host × Delivery：用户粘贴剧本

> 这不是 Skill。不要把它当独立技能加载，也不要改任何 Skill 的 schema、验证器或内部状态格式。
>
> 用途：把一次 AngularJS / jQuery / JSP / Thymeleaf 混合页迁入现有 Vue3 宿主仓拆成可粘贴的会话。
> 允许按名组合 `angularjs-to-vue3-host-migration`、`delivery-frame-spec`、
> `delivery-plan-tasks`、`delivery-execute-verify`。
>
> `angularjs-to-vue3-host-migration` 仍保持独立：产出领域证据、页级设计和领域复核，不调用 Delivery。
> Delivery Family 仍独立负责 OpenSpec、批准、计划、实施、Fresh Verification。
>
> `delivery-execute-verify` 是唯一应用代码 mutation owner；其余 Wave 对 A/B 应用代码只读。
> Wave 3 无论 `new-landing` 还是 `repair` scope，都只产出合同和切片计划，不直接写 B。
>
> 项目专有误判钉子放在 `docs/angularjs-host-migration-hiapm-appendix.md`。通用粘贴块只保留可泛化规则。

## 0. 编排结论

两条路径共用 Wave 1 / 2 / 3 / 6 / 7，只在批准链上分叉。
Wave 3 用 `design-scope` 区分“B 里还没有这个页面”和“B 已有壳页、只做对等修复”，
不再有独立的 Wave 2.5。
一个批次可以带多个 UNIT（上限 5），见下方“UNIT 批次”。单 UNIT 是批次大小为 1 的特例，
两者走完全相同的波次。

**主路径（新落地）**：B 里还没有该 UNIT，或需要新增/变更 API 契约、改权限模型、切流灰度、
回退范围变更、OpenSpec 规格审计。

```text
Wave 1  建 change（无规格闸门）
  → Wave 2  angularjs assess
  → Wave 3  angularjs design（design-scope=new-landing）
  → Wave 4  Delivery Frame 规格批准
  → Wave 5  Delivery Plan + 实施 go
  → Wave 6  Delivery Execute + Fresh Verification
  → Wave 7  angularjs verify
```

**修复快车道**：B 已有该 UNIT 的入口壳页，目标只是对照源站对等修复。Frame 与 Plan 在同一会话内连跑，
省掉一次换会话和重新建立上下文；两道闸门都保留，因为迁移固定 High，High 要求规格与实施两次批准。

```text
Wave 1  建 change（已有 change 时只做恢复校验）
  → Wave 2  angularjs assess（必须产出控件矩阵）
  → Wave 3  angularjs design（design-scope=repair）
  → Wave 4R Frame + Plan 同会话连跑（规格闸门 + 实施 go，两次问询）
  → Wave 6  Delivery Execute + Fresh Verification
  → Wave 7  angularjs verify
```

`design-scope` 判定（三条全真才用 `repair`）：

| 条件 | repair | new-landing |
|---|---|---|
| 对照状态为 `partial-overlap` | 是 | 否 |
| B 入口有 route / menu / MPA 证据，且源路由与宿主路由形状一致 | 是 | 否或未证明 |
| 目标是源站对等修复，不新增 API 契约、不改权限模型、不涉及切流 | 是 | 否 |
| 本轮是否修改 B 应用代码 | 否，直到 Wave 6 | 否，直到 Wave 6 |

入口证据只认路由/菜单/MPA 注册。文件名相似、目录相近、匹配器给出的候选分都不是入口证据——
一个 `unmigrated` 的详情页很容易被配到同名列表页的 `.vue` 上，据此开 `repair` 会把未迁页当成壳页修。

### 完成态与开口状态

目的页建出来、Tab 接上、change 勾完，都不等于迁完。每个 UNIT 必须显式落在下面的状态之一：

| 状态 | 含义 | 是否可完成 |
|---|---|---|
| `already-migrated` | 闭包对等、出站已按授权切到 B、运行时可独立到达，且 MATRIX 已结清 | 是 |
| `dest-built-unwired` | B 目的页/组件/helper 已存在，但出站仍落 A 或未授权切流 | 否 |
| `wired-hidden` | Tab/入口已接，但被 `v-if`、权限、feature flag、父壳状态或运行时隐藏 | 否 |
| `develop-native` | B `develop` 有原生页，但不是本源 hash/URL/query 合同 | 否 |
| `orphan-mpa` | 有 MPA HTML/TS，但没有匹配源合同或可达入口证据 | 否 |
| `deprecated-removed` | 已由范围/SDD 决定废弃删除，禁止在 repair 中恢复 | 否，除非新 change 批准 |

T16（出站切 B）是独立授权切片。未授权时，合同测试要断言理论 B HTML/hash 不出现在 active href/open 中；
已授权时，必须逐出口证明卡片、菜单、Tab、弹窗、成功回调、deep link 都走同一落地函数。

收口不靠叙述：Wave 7 必须按 hosted-method 的 `Archive Gate` 逐 UNIT 输出一行
（完成态、MATRIX verified/总行、未结清行 ID、降级标签、archive 处置）。
archive 处置只有 `parity-complete` / `repair-done-partial` / `blocked` 三种；
已知偏差必须在 archive **之前**进 MATRIX，不能留到次日另开 repair change。
archive 之后该 UNIT 即关闭：新发现只能开新 change，不得回填旧包，也不得把它再列进后续批次。

### 项目反例附录

通用规则只记录模式：壳存在不等于迁完、详情抽屉不等于独立页、隐藏入口不等于可达、
iframe/mail/external URL 与应用内跳转语义不同。hiapm -> apmweb3 的专有页面名、URL 和 T16 反例见附录。

### UNIT 批次

一个批次装 1–5 个 UNIT，**一个批次一个 change**。不要给每个 UNIT 单开 change 并行跑：
`artifact-gate-checks.md` 的 G8 在 Plan/Execute 前比对各 active change 的允许路径，
而宿主迁移里每个页面几乎都要碰共享路由和 i18n，N 个 change 会在这些文件上互相判成阻塞项。
反过来，`delivery-plan-tasks` 明确支持**同一 change 内**的并行任务组（无共享可变状态、
无重叠文件或有显式 ownership、前置契约稳定、验证可独立运行），批次就用这个机制。

批次省下的是固定开销：批准从 2N 次降到 2 次，波次从 7N 个会话降到 7 个左右。
省不掉的是 Wave 3 每个 UNIT 的合同填实，和 Wave 6 里共享宿主面的串行实施。

准入规则（任一不满足即拆批）：

| 规则 | 说明 |
|---|---|
| 批次上限 5 | 再多会让 High 的成本/风险/回退摘要失去可判断性；脚本对超限直接报错退出 |
| design-scope 必须一致 | 全 `repair` 走 4R，全 `new-landing` 走 4+5。混装会让一个批次同时需要两条批准链 |
| 每个 UNIT 唯一定位到一个源页 | 一个 unit 名匹配到多个源页时范围不唯一，先收紧名字 |
| 每个 UNIT 独立可切换 | 沿用「不能默认整仓迁」；批次是若干独立页面，不是一个大页面 |
| 共享宿主面必须有唯一 owner | 路由注册、菜单、共享 i18n、common CSS、全局 store 由唯一前置任务组独占修改，其余 UNIT 只读依赖 |
| 同一宿主落点的 UNIT 不得并行 | 两个 UNIT 落到同一个 host 文件时串行，或合并成一个 UNIT |

脚本产出 `csv/17-batch-admission.csv` 和 `csv/18-batch-shared-surface.csv` 作为候选判定，
但 ownership 一栏是 `[未分配]`，必须在 Wave 5 / 4R Plan 段由人指定。

### 试点规则

同一对 A/B 仓库的**首个 UNIT 必须单跑**，因为宿主编译层、CSS 闭包落地方式、入口挂载模式、
浏览器取证可行性这几件事只能靠真的写一次、验一次才能证明；拿一批去校准等于把错误乘以 N。

试点管住实施，不管住设计：

- Wave 1 / 2 共享，assess 一次覆盖全仓，无并行问题
- 批次其余 UNIT 可以在试点跑 Wave 4→7 的同时并行推进到 **Wave 4 结束**（只读工件，最坏情况是改草稿）
- **进入 Wave 5 或 4R Plan 段之前，试点的 change 必须已经 archive**；否则批次的就绪审查会在 G8 上
  把试点标成路径重叠阻塞项，只能靠显式接受并行风险绕过，等于手工关掉这道闸

这些宿主级事实已有实测证据（host baseline gap 表与 compile overlay 已填实并绑定当前宿主修订）时，
可以在批次准入里记录证据位置并豁免试点；无证据不得跳过。

`repair` scope 下，同一 mounted wrapper 内后发现的源站区域可继续补合同；一旦发现缺接口、
要动权限模型、要加源站没有的行为、不同页面/wrapper，或选定 wrapper 当初完全漏扫，立即停止、
撤销快车道资格，按回流表改走主路径 Wave 4 + Wave 5。

### 职责边界

| 层 | 职责 |
|---|---|
| `angularjs-to-vue3-host-migration` | 双仓领域事实：A/B 页面对照、混合栈闭包、AngularJS/jQuery/服务端模板行为链、URL/API/权限/回退合同、最终领域复核 |
| `delivery-frame-spec` | 创建或恢复 OpenSpec change，写 proposal/spec，完成范围与规格批准 |
| `delivery-plan-tasks` | 写 design/tasks、纵向切片、就绪审查、实施闸门 |
| `delivery-execute-verify` | 唯一应用代码 mutation owner；只修改 Vue3 宿主 B；完成 Fresh Verification、独立审查和 verified handoff |
| Wave 4R 同会话连跑 | 修复快车道的批准波；`delivery-frame-spec` + `delivery-plan-tasks` 在一次会话内顺序完成规格闸门与实施闸门，两道闸门都不省 |
| OpenSpec change | Delivery 生命周期和批准状态真相 |
| 本剧本 | 只规定会话顺序、提示词、工件交接和停止点 |

固定原则：

- A 始终只读；只有 Wave 6 可以修改 B 的应用代码。
- 迁移默认 High 风险；迁移单元必须是独立可切换页面或用户行为，不能默认整仓迁。
- 落地规则、控件矩阵、交互等价、i18n 原文、CSS 闭包、切片完成定义、宿主编译层：
  见 `angularjs-to-vue3-host-migration` 的 Hosted Migration Rules / Display Contract /
  Host Compile Overlay 与 `references/hosted-vue3-migration-method.md`。本剧本不复述。
- Delivery `verified` 不等于领域迁移完成；Wave 7 领域复核通过后才能说“迁移完成候选”。
- 完成后仍不自动 archive、commit、push、PR、部署、切流、删除 fallback 或下线 A。

## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 首次使用时，在“会话通用头”填写 A、B、UNITS 三个必填值。UNITS 可以是 1 个，也可以是最多 5 个。
2. 默认每个 Wave 开一个全新会话，粘贴“会话通用头 + 当前 Wave 代码块”。
3. 当前 Wave 完成并停止后，再开下一个 Wave；若用户在同一会话说“继续”，只能继续当前 Wave 的剩余工作，写权限仍按当前 Wave。
4. Wave 2 结束时会给出 `design-scope` 结论：壳页对等修复用 `repair`，其余用 `new-landing`；
   `repair` 在 Wave 3 之后走 Wave 4R 同会话连跑，`new-landing` 走 Wave 4 + Wave 5。两条路都是两次批准。
   批次内 design-scope 必须一致；不一致时按 scope 拆成两个批次，各自一个 change。
5. 同一对 A/B 仓库的首个 UNIT 必须单跑到 archive 才允许组批；批次其余 UNIT 可与试点的
   Wave 4→7 并行推进到 Wave 4 结束，但进 Wave 5 / 4R Plan 段前试点必须已 archive。
6. 若 `<CONFIG>` 与 `<MATRIX>` 已存在且绑定当前 A/B revision，Wave 1 与 Wave 2 只做校验刷新，
   不重开建档与全量 assess；只有 revision 变化或工件缺损才重跑。
7. 用户只处理真正阻塞的问题、规格批准、隐藏/显示偏差批准、运行时人工确认或实施批准；
   不需要手工维护 digest、revision、任务状态。

### 1.2 会话通用头

```text
这是一个全新独立会话，不得使用其他会话的聊天记忆补结论。

用户输入：
<A> = AngularJS / jQuery / JSP / Thymeleaf 源仓绝对路径
<B> = 现有 Vue3 宿主仓绝对路径
<UNITS> = 1–5 个待迁移页面、URL、菜单项、路由或用户行为，逗号分隔，
          例如 taskManage 或 taskManage,workBench,projectProgress
          批次内 design-scope 必须一致；批次大小为 1 时即单 UNIT 模式
<UNIT>  = 引用单个成员时使用；<UNITS> 只有一个成员时两者等价

自动派生并保持稳定：
- canonical_skill_id：`angularjs-to-vue3-host-migration`。CONFIG、handoff、next_skill、报告 Skill 字段必须原样使用；
  不得缩写成相近名称。
- <SLUG>：批次大小为 1 时由 <UNIT> 规范化；批次更大时由 <UNITS> 首个成员加 `-batch<N>` 规范化；过长时追加短 SHA-256
- <CHANGE_ID>：migrate-<SLUG>-to-vue3-host
- <CHANGE_DIR>：openspec\changes\<CHANGE_ID>
- <EVIDENCE_ROOT>：<CHANGE_DIR>\evidence
- <DOMAIN_ROOT>：<EVIDENCE_ROOT>\angularjs-hosted-vue3-migration
- <CONFIG>：<DOMAIN_ROOT>\migration-run-config.json
- <INDEX_MANIFEST>：<DOMAIN_ROOT>\codebase-index-manifest.json
- <RUNTIME_MANIFEST>：<DOMAIN_ROOT>\runtime-service-manifest.json
- <FRESHNESS_MANIFEST>：<DOMAIN_ROOT>\freshness-manifest.json
- <MATRIX>：<DOMAIN_ROOT>\display-contract-<SLUG>.md（控件矩阵唯一台账，跨 Wave 只更新不重开；
  批次模式下每行带「迁移单元」列，一个台账覆盖整批）

<CONFIG> 存在后以其记录为准；与本次输入不一致时停止。
唯一状态源是 `<CHANGE_DIR>` 与其 `<DOMAIN_ROOT>`。`_live-eval*`、临时报表目录、复制到 change 外的 Markdown/CSV
只能作为实验室证据，不能作为 Wave 恢复、批准、verify 或完成判定权威。人填 MATRIX、freshness、design-ready packet
必须写回 `<DOMAIN_ROOT>` 并记录 path/digest。

代码发现默认 Codebase Memory MCP：
index_repository（需要时）→ get_architecture → search_graph / search_code →
trace_path → get_code_snippet → query_graph。
只有模板文本、字符串、配置、vendor 排除扫描或 MCP 证据不足时，才使用 rg / 文件读取，
并记录 fallback 原因。不得因为图谱没有 Route 节点就断言页面或入口不存在。

<INDEX_MANIFEST> 记录 A/B graph project、repo path、revision、index mode、indexed_at。
图谱 revision 与仓库当前 revision 不一致视为 stale；stale 证据不能用于 pass。
首次进入真实 A/B 路径时必须按当前路径重建或刷新索引；旧路径索引只能作为历史线索，
不能作为 pass 证据。若图谱缺 Route 节点，必须用 Java/Spring route、模板、菜单和
MPA entry 扫描补证，不得由“图谱没有入口”推导为“入口不存在”。

<FRESHNESS_MANIFEST> 记录当前 A/B revision 下真正支撑合同的文件 digest：
A Java route、AngularJS route/ui-router/hash、A i18n、A controller/service/jQuery payload、
B `scripts/getpage.js` / `src/pages/*/*.ts`、B menu/permission、B package/lockfile/build config。
任一 digest 变化，对应 MATRIX、FLOW/VAR/CHAIN、URL/entry、i18n 或 runtime 证据 stale；
禁止用上一波“已决结论”压当前源事实。

仓库获取、revision 绑定、Git 卫生门禁：按
`angularjs-to-vue3-host-migration/references/hosted-vue3-migration-method.md` 的
Repo Acquisition And Revision Binding 与 Git Hygiene Gate 执行并记录。
硬停止条件：path 存在但不是 git repo，或 HEAD 不可读。
`sslVerify=false` 只能作为诊断警告记录，不得成为默认策略或持久配置。

固定边界（本剧本唯一权限声明，其余落地规则见 Skill）：
- A 始终只读；A 出现业务代码修改通常使领域证据 stale。
- 只有 Wave 6（delivery-execute-verify）可修改 B 应用代码。
- 其余所有 Wave 对 A/B 应用代码只读。
- 禁止源站闭包外的新功能、无关重构、Vue2、@vue/compat、长期桥接依赖进入 B。
- 源码存在但 SIT/运行时隐藏的闭包内功能默认保持隐藏；要显示或隐藏差异必须有 approved-deviation。
- 禁止对获批范围外的遗留文件做格式化、缩进转换或“顺手”类型补全。
- 部署、切流、A 下线、删除 fallback 不在本轮；保护 A/B 已有 staged/unstaged/untracked 用户改动。

自动恢复以当前 Wave「应已存在」矩阵为准，校验 path、digest、A/B revision、
OpenSpec artifact_revision、批准绑定和用户改动碰撞。
已完成 Wave 的工件缺失/损坏/stale 时停止并指出重跑哪个 Wave。

失败回流最小字段：
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point

会话停点覆盖：只执行随后指定的一个 Wave。完成、写盘、校验后立即停止；
不要加载或执行下一个 Skill。
```

### 1.3 工件恢复矩阵

| Wave | 应当存在的主要上游工件 |
|---|---|
| 1 建 change | 无；创建或恢复 change、Config、evidence 目录 |
| 2 Assess | Config、change 目录；规格尚未批准为正常 |
| 3 Design | Assess evidence、A/B revisions、<FRESHNESS_MANIFEST>、候选迁移单元、host stack、host baseline gap 表；`repair` scope 另需 <MATRIX> 与 B 已有入口证据；批次另需准入判定与试点 archive 状态 |
| 4 Frame | Design-ready domain evidence（`new-landing`）、change 目录、意图草稿 |
| 5 Plan | 已批准 Frame 规格、domain evidence path/digest、Frame handoff；批次另需试点 change 已 archive |
| 4R 同会话连跑 | Wave 3 `repair` design-ready evidence、<MATRIX>、B 入口证据（route/menu/MPA）、change 目录；批次另需试点 change 已 archive |
| 6 Execute | design/tasks、规格闸门 + 实施 go、Plan handoff 或 `lane=repair-fastlane` handoff、领域设计和运行时证据 |
| 7 Verify | Delivery verification、当前 B 代码、G9/测试/构建证据、领域证据 |

默认不得在 `<CHANGE_DIR>` 外另建第二状态源。`evidence/` 保存 path+digest 可校验的领域证据；
OpenSpec 的 proposal、spec、design、tasks、verification、handoff 仍是 Delivery 权威工件。

## 2. Wave 1：建 change（无规格闸门）

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-frame-spec Skill。
建档停点覆盖：只创建或恢复 change。本波禁止规格闸门，禁止 Plan/Execute。
迁移类变更固定 High；本波不得修改 A/B 应用代码。

应已存在：无。

硬前提：B 的 OpenSpec 可写；优先使用 Codebase Memory 索引/查询 A/B，不可用时按 Skill fallback 并记录原因。
openspec: cli-only 时按 Frame Skill 固定三行报告，并询问 initialize_repo；
不得发明平行 Markdown 状态。

读取 A/B 当前 revision。索引缺失时先 index_repository，再用 get_architecture 证明可查询。
校验 <A>/<B> 与 <UNITS> 每个成员基本可定位；任一不能定位则停止。
校验 <UNITS> 成员数 ≤5；超出则停止并要求拆批。
若 clone/fetch 曾失败但 <A> 或 <B> 已是有效 git repo 且 HEAD 可读，记录 acquisition_warning 后可以继续；
若 HEAD 不可读或路径不是 git repo，停止。

正式创建或恢复唯一 <CHANGE_DIR>，并创建 <DOMAIN_ROOT>、<CONFIG>、
<INDEX_MANIFEST>、<RUNTIME_MANIFEST>、<FRESHNESS_MANIFEST> 初始结构。
<CONFIG> 或初始 evidence 必须包含 repo acquisition 表与 git hygiene 摘要。
<CONFIG> 必须写入 canonical_skill_id=`angularjs-to-vue3-host-migration`；handoff/next_skill 不得使用缩写。
本波不得安装依赖或启动 A/B。

只写意图草稿：
- A 只读
- 仅 Wave 6 修改 B
- B host-native shell/auth/router/API/state/components/i18n/proxy/runtime
- 迁移单元为 <UNITS>，逐成员列出
- 保留 fallback / rollback，逐成员独立开关
- 部署、切流、删除 fallback、A 下线为非目标

proposal 保持草稿。不要询问范围批准，不要写规格批准，不要进入 Plan。

结束输出：change id/dir、Config、Index Manifest、A/B revision、route/risk 草稿。
说明下一步为 Wave 2，然后停止。
```

## 3. Wave 2：AngularJS 领域 Assess

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 angularjs-to-vue3-host-migration Skill，mode=assess。
只做只读双仓证据基线；不要进入 design/verify。本波不得修改 A/B 应用代码。

应已存在：<CONFIG>、<CHANGE_DIR>。缺失则回 Wave 1。尚无规格批准为正常。

先校验 <INDEX_MANIFEST> 的 A/B revision；缺失或 stale 时重新 index_repository。
读取 angularjs-to-vue3-host-migration/references/hosted-vue3-migration-method.md。
当扫描具体 UNIT 时，同时读取 jQuery 与 variable-flow references。
assess 是全仓一次扫完的，不按 UNIT 收费：一次运行同时覆盖 <UNITS> 里所有成员。

按 Skill 的 assess 输出合同写盘，不要在本提示词里重述字段清单。
本波额外必须产出：
- host compile overlay：`lintOnSave`、TS `noImplicitAny`/`strict`、Prettier/EditorConfig 缩进、
  dev-server overlay 范围、实测 `node -v` 与宿主声明 Node 基线
- host baseline gap 表：按 hosted-method 的 Host Baseline Gap Table 一次性盘点 A 假定的全局依赖
  （reset/基础字号、Bootstrap 或其他 utility/grid 表、精灵图与坐标表、图标字体、空态图、
  jQuery 及插件、全局 JS 库、服务端注入的全局变量）在 B 是否存在；
  这是宿主级事实，只做一次，后续每页复用，不允许在修页时才发现
- <UNITS> 每个成员的候选 source entry、真实 source URL 与 host landing point
- <FRESHNESS_MANIFEST>：逐成员绑定 A route/hash/i18n/API 行为文件与 B MPA/menu/permission/runtime 文件 digest；
  A i18n、ui-router/hash、Java `@RequestMapping` 或 B MPA entry 与旧 evidence 不一致时，直接标旧 MATRIX/packet stale
- 若某成员判为 `partial-overlap`：把首轮控件矩阵写入 <MATRIX>，每行填「迁移单元」和 `B 现状`
  （missing / mismatched / wired-unverified / verified / manual-verified / approved-deviation）；
  脚本只给整页 `(skeleton)` 骨架行，必须按源区域拆分后才算矩阵
- design-scope 判定表：逐页给出对照状态、宿主入口、入口证据类型和 `repair` / `new-landing` 结论
- 源站契约门禁首扫：模板/脚本比较运算、hidden/global/session 身份字段、`data-href`/菜单/缓存绝对 URL、
  公共 modal 模式、模板实际使用的 CSS 工具类
- gaps blocking design 与推荐迁移单元依据

可运行脚本生成证据基线：
python angularjs-to-vue3-host-migration/scripts/generate_migration_plan.py assess \
  --project-name "<CHANGE_ID>" \
  --source-repo "<A>" \
  --host-repo "<B>" \
  --source-acquisition-warning "<若有 clone/fetch warning 则填写，否则留空>" \
  --host-acquisition-warning "<若有 clone/fetch warning 则填写，否则留空>" \
  --output-dir "<DOMAIN_ROOT>\\assess" \
  --format all

脚本输出只是 evidence baseline，artifact_level=baseline-only；必须用代码证据复核，不得把通用表格当设计，
也不得用脚本表替代控件矩阵。`_live-eval*` 输出不能作为恢复权威，合格包必须写回 <DOMAIN_ROOT>。
仓库获取与 Git 卫生表必须进入 assess evidence；出现 dependency/cache/build noise 时，后续不得声明 commit-ready。
A/B 页面对照与页面分类规则按 Skill 与 hosted-method 执行（文件名不等于 already-migrated、
`.vue` 不默认当页面、根 `index.html` 只能当 host-shell、别名近似命中标 needs_human_correction）。
额外填每个成员的完成态枚举：`already-migrated` / `dest-built-unwired` / `wired-hidden` /
`develop-native` / `orphan-mpa` / `deprecated-removed` / 其他 hosted-method 状态。
`dest-built-unwired`、`wired-hidden`、`develop-native`、`orphan-mpa` 都不得作为完成态或 archive 绿灯。

生成 assess evidence packet 或 Markdown 摘要到 <DOMAIN_ROOT>，记录 path/digest、A/B revision、
source/host page comparison、URL/entry mapping、host compile overlay、host baseline gap 表、
<MATRIX> path/digest、blockers。

若 <UNITS> 任一成员缺少真实 source URL 或 B host entry 证据，输出回流字段并停止。
若任一成员在 A 或 B 中无法定位，输出回流字段并停止。
否则逐成员给出 `design-scope` 结论，下一步统一是 Wave 3 Design。判定用硬规则，不用印象：
- 同时满足「对照状态 = `partial-overlap`」和「宿主入口有 route / menu / MPA 证据」，
  且目标是对等修复 → `design-scope=repair`
- 对照状态是 `unmigrated` 时一律 `new-landing`，即使匹配器给它配上了某个 `.vue` 文件；
  文件名相似不是入口证据
- 宿主入口只有文件名猜测（脚本 `host_entry_evidence` 为 `filename guess only`）→ `new-landing`
- 源路由与宿主路由形状不一致（例如 `/phones/:id` 对 `/phones`）→ 该行不成立，重新取证
脚本 `csv/07b-design-scope-gate.csv` 给出逐页判定，但它是候选结论：
下结论前必须人工核对 URL 表的源路由与宿主路由确实是同一个页面。

批次模式额外输出：
- 批次成员的 design-scope 是否一致；不一致则按 scope 拆批并说明怎么拆
- 建议批次组合（≤5 个、彼此独立可切换、宿主落点不重叠），依据 recommended_units 与对照状态
- 试点状态：本对 A/B 仓库是否已有 archive 过的 UNIT；没有则本轮只能单跑首个 UNIT
然后停止。
```

## 4. Wave 3：AngularJS 领域 Design（design-scope = new-landing | repair）

两种 scope 共用同一个 Wave：`new-landing` 做全新页级落地设计，`repair` 做壳页对等修复合同。
差别只在准入校验、矩阵起点和下一步批准链，其余合同要求完全一致。

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 angularjs-to-vue3-host-migration Skill，mode=design，units=<UNITS>，
design-scope=<new-landing|repair>（取 Wave 2 的结论，整批同一个 scope）。
本波只产出合同与切片计划，不修改 A/B 应用代码。

应已存在：<CONFIG>、Wave 2 assess evidence、A/B revision、<FRESHNESS_MANIFEST>、host stack、host baseline gap 表、
A/B page comparison。design-scope=repair 另需 <MATRIX> 与每个成员在 B 侧的 MPA/router 入口证据。
缺失或 stale 则回 Wave 2。

批次准入先判定，不通过就先拆批再继续：
- 批次 ≤5 个成员，且 design-scope 一致
- 每个成员唯一定位到一个源页；匹配到多个源页时先收紧 unit 名
- 成员之间宿主落点不重叠；重叠的成员串行或合并
- 试点已 archive，或本轮就是首个 UNIT 单跑

读取 hosted-vue3-migration-method 的 Landing Rules、Interaction Equivalence Test、
Display Contract Matrix、Page Init And Side Effects、CSS Closure、Host Baseline Gap Table、
Host Compile Overlay、Source Contract Gates、Design-Ready Gate；
design-scope=repair 时另读 Shell-Page Repair。
按需读取 jquery-vue3-business-logic-analysis 与 business-logic-variable-flow-analysis。
不要读取 angularjs-vue3-migration-method（绿场）。

design-scope=repair 准入校验，任一不成立就改用 new-landing 并按主路径继续：
- 每个成员在 B 已有入口且用户可访问
- 目标是源站对等修复：不新增 API 契约、不改权限模型、不加源站没有的行为、不涉及切流或回退范围变更

Step 0 中断卫生与宿主编译层 preflight（两个 scope 都做）：
- 扫重复弹窗、重复函数/落地 helper、重复 hash/route 写入、未闭合模板/脚本/样式
- 记录每个成员的入口是否已可编译；任一成员入口编译失败是后续 Execute 的阻塞项
- 列出 `lintOnSave` 会扫到的范围外脏文件；这些文件记为 residual，禁止顺手格式化或补类型
- 全仓无关 overlay 记 residual，不得声明 dev server 健康
- 运行 git status 记录 B 当前用户改动；本波没有 intended application files
- 记录实测 `node -v` 与宿主声明基线；版本不符的运行结果不算验证证据

Step 1 补齐合同：
按 Skill 的 design 输出合同生成设计包并写盘，不要在本提示词里重述字段清单。
- 同一页 AngularJS + jQuery + 服务端模板合并成一个闭包，不拆成平行报告
- 控件矩阵写入 <MATRIX>；design-scope=repair 时为原地刷新，不重开分析
- 矩阵必须按源区域拆行。脚本产出的整页 `(skeleton)` 行不是合同，留着即 `not-ready: skeleton-only-matrix`
- page-init 表、源 i18n 原文表、CSS 闭包表齐备
- 每个可见数字/列表都有 API + 字段公式（求和、拼接、全选标题都要写）
- CSS 闭包盘点模板 utility、Bootstrap 形态 class、sprite/icon size、runtime-hidden switch、
  空态图文、状态类 cascade safety，并逐条对照 host baseline gap 表给出 B 落地方式；
  gap 表标 `host-missing` / `host-partial` 的基线，本页用到就必须有显式落地方式
- 源码存在但 SIT/运行时隐藏的功能默认保持隐藏；要显示必须记录 approved-deviation
- 反方向同样处理：宿主多出、源站没有的区域/按钮/配色/列默认删除或隐藏，保留需 approved-deviation；
  源站怪异写法（列数对不上的 `colspan`、奇怪排序）是合同，不得当 bug 顺手修
- 空态与公式按源分支落地：空数组是 truthy，空判断要显式 `length`/`!== null`，
  禁止垫伪行或用一张通用空图盖所有区域；请求字段按 endpoint 归属，列表/详情字段不得带到 count 接口
- 共享弹窗按模式分行；导航落地写清源 URL、剥源后路径、B 是否骨架、最终回源还是进 B
- 出站切 B 单独成片：未获 T16/切流授权时，所有 active href/open 仍应落 A 或既有 fallback，
  测试反向断言不得出现理论 B HTML/hash；获授权后才逐出口切同一 landing helper
- URL 按目的分三类：应用内跳转可剥源并保留 query/hash；iframe chrome 可 `keepOrigin`；
  邮件/外链/可复制链接默认保留绝对 `rootPath`，除非当前源证据证明可相对化
- 源站契约门禁写入设计：身份字段、比较契约、命中层、选择器↔DOM、绝对 URL 剥源、
  B 骨架不改导航、同一 UNIT 出口共用落地函数
- 闭包以已挂载 wrapper 为准：`ui-view`、`ng-include`、指令、server include、路由/菜单和运行时证据
- FLOW/VAR/CHAIN 逐成员分节，只针对 <UNITS> 成员，不铺全仓空表
- 批次模式：每个成员各自一套页面闭包、矩阵行、page-init、i18n、CSS 闭包，不允许合并成一份共用合同
- 一 hash/URL/query 合同一 UNIT。文件名相近、Tab 参数相近、同一报表中心内多个 hash，都不能合成一个 UNIT。
输出必须是人填 design-ready packet：具名 <MATRIX>、<FRESHNESS_MANIFEST>、填过的 design-ready 表、
FLOW/VAR/CHAIN 与 URL/entry 证据都写回 <DOMAIN_ROOT>；脚本 baseline-only 目录不能直接交给 Wave 4。
矩阵缺行、`B 现状` 空、或存在只有表头的表，禁止进入 Step 2。

Step 2 产出切片计划：
纵向切片；design-scope=repair 时按源区域分组。完成判据是“入口已挂载、已调用 API、用户可点到”，
不是“helper 文件已存在”。每片列出：涉及的 <MATRIX> 行 ID、拟改 B 文件/入口/API/store/component、
验证步骤、Source Contract Gates、可执行 display-contract 测试、rollback/fallback 影响。
批次模式还要标出每片归属哪个成员，并把共享宿主面（路由注册、菜单、共享 i18n、common CSS、
全局 store，以及迁移专有的出站落地 helper、Tab/Header 壳组件、共享合同测试文件）
单独列为**前置切片组**：唯一 owner、先落地、其余成员只 import / 只断言。
回退开关必须逐成员独立，不允许整批一个开关。
运行时证据先按宿主工具链尝试（既有 Playwright/Cypress/Puppeteer，或 dev server + 一次性 headless
截图/DOM dump 脚本）；尝试失败必须记录失败原因，相关行保持 wired-unverified，不得直接标 verified。
若已有 change，把 <MATRIX> path/digest 和切片计划写入 external_artifacts。

Step 3 design-ready 判定：
按 hosted-method 的 Design-Ready Gate 逐项判定。
对每片复述源合同：源文案原文、控件形态、字段公式、默认值/校验、几何、CSS 依赖、启动副作用。
确认切片完成判据、entry-wiring 检查、运行时可见性检查、命中层/选择器↔DOM/导航落地/身份字段/
比较契约检查都写进计划。
成员若为 `partial-overlap`，缺控件矩阵、page-init 表、i18n 原文表或 CSS 闭包表任一项，
即为 `not-ready`，只填 1～2 条点击流不得放行。
批次模式逐成员判定：任一成员 `not-ready`，整批不得进入 Frame。
把该成员从批次里摘出来单独跑，比让整批停在门口更快。
计划不能把未实施行标为 verified；只能保留 missing / mismatched / wired-unverified / approved-deviation。

可运行脚本生成 design 合同基线（可选，只在需要合同骨架时运行）：
python angularjs-to-vue3-host-migration/scripts/generate_migration_plan.py design \
  --project-name "<CHANGE_ID>" \
  --source-repo "<A>" \
  --host-repo "<B>" \
  --unit "<UNITS>" \
  --source-acquisition-warning "<沿用当前有效 warning 或留空>" \
  --host-acquisition-warning "<沿用当前有效 warning 或留空>" \
  --output-dir "<DOMAIN_ROOT>\\design" \
  --format all

`--unit` 可逗号分隔或重复传入，超过 5 个直接报错退出。
批次模式会额外产出 `csv/17-batch-admission.csv`（准入判定）和
`csv/18-batch-shared-surface.csv`（共享宿主面，owner 一栏为 `[未分配]`，必须在 Plan 段指定）。
脚本生成的空合同必须标 `not-ready: empty-contract`；脚本表不能替代控件矩阵；
只有人工或后续分析把 gate 填成 evidence-backed ready，才能继续。
若存在 implementation-blocking TBD、FLOW/CHAIN 只有空表头、URL/entry 缺少真实证据，
或 design-ready gate 任一必填项未满足，停止并给回流字段；不得进入任何批准闸门。

升级条件（出现即停止，输出回流字段）：
- 缺接口或接口契约需要变更 → 主路径 Wave 4
- 需要改权限模型或新增源站闭包外的行为 → 主路径 Wave 4
- 需要切流、灰度或回退范围变更 → 主路径 Wave 4
- design-scope=repair 且同一 wrapper 内后发现源站区域 → 留在本波补矩阵和切片计划
- design-scope=repair 且发现不同页面/wrapper，或源闭包当初没有扫到选定 wrapper
  → 改用 new-landing 重做本波
以上任一升级都会撤销 repair 的快车道资格。

结束输出：人填 design-ready domain evidence path/digest、<MATRIX> path/digest 与行状态统计、
切片计划、residual 与 blocker、实测 node 版本、external_artifacts 更新位置。
不要 archive、commit、push、PR、部署、切流。
design-scope=repair 且无升级条件 → 下一步 Wave 4R 同会话连跑；
否则 → 下一步 Wave 4 Frame。然后停止。
```

## 5. Wave 4：Delivery Frame 规格批准（主路径）

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-frame-spec Skill。
不要 Plan/Execute。本波不得修改 A/B 应用代码。

应已存在：<CHANGE_DIR>、Wave 3 人填 design-ready domain evidence path/digest。
若只有 assess、design 未 ready、FLOW/CHAIN 只有表头、URL/entry 缺少真实证据，
<MATRIX> 仍是脚本 skeleton、artifact_level=baseline-only 未被人填 packet 覆盖，或 design-ready gate 未通过，
停止并回 Wave 3。
若批次的 design-scope 是 `repair` 且没有触发任何升级条件，本波不适用：改走 Wave 4R 同会话连跑。
由 `repair` 升级而来的成员在本波按 new-landing 处理，并作废原快车道资格。

从 domain evidence 摘要写入 external_artifacts：path、digest、A/B revision、<UNITS>、
每个成员的 old URL、新 host entry 候选、rollback、blockers/residuals。
不要要求 angularjs-to-vue3-host-migration 的 schema 进入 Delivery 状态。

基于当前领域事实完成 proposal.md 和增量规格：
- 目标与非目标
- A 只读、B host-native
- 迁移范围为 <UNITS>，逐成员列出验收；批次不得写成一条笼统的“迁移这些页面”
- 行为/权限/URL/API/错误/视觉或人工视觉限制/runtime/rollback 验收
- fallback 保留条件，逐成员独立开关
- 禁止复制 A layout、禁止无关重构、禁止长期桥接

迁移类变更固定 High。若视觉对等没有测量链，只能写“manual-only / not proven”，不能写 visual pass。
批次模式下 High 的成本/风险/回退摘要必须逐成员可读；一条摘要盖不住 5 个页面时说明批次太大，先拆批。

按 Frame Skill 完成澄清和规格闸门，只询问一次范围批准，一次覆盖整批。
批准必须绑定当前 artifact_revision，写入 State Source 和 handoff.json。

结束输出：change id/dir、route/risk、proposal/spec、批次成员清单、规格闸门、handoff path/revision。
说明下一步为 Wave 5，然后停止。
```

## 6. Wave 5：Delivery Plan + 实施 Go（主路径）

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-plan-tasks Skill。
只消费当前有效 Frame handoff；不要修改 A/B 应用代码，不要进入 Execute。

应已存在：已批准 Frame 规格、domain evidence path/digest、Frame handoff。
缺失或批准失效则回 Wave 4。

校验 domain evidence 的 path/digest 和 A/B revision。
刷新 B 当前路径/符号事实；检查其他 active change 路径重叠。
批次模式：试点 change 若仍是 active 且与本批允许路径重叠，G8 会判成阻塞项。
先等试点 archive，不要用「显式接受并行风险」绕过。

按 Skill 契约写唯一权威 design.md/tasks.md：
- B 侧精确文件/符号/入口/路由/API/store/component
- 纵向切片，每片都能独立验证
- 复用/改造/新建处置
- 行为、权限、URL、API、错误、runtime、rollback 验证矩阵
- 视觉要求：有测量链则写 G9 证据计划；无测量链则标 manual-only，不得假装通过
- fallback/rollback 任务和演练命令

批次模式的任务组织：
- 共享宿主面（路由注册、菜单、共享 i18n、common CSS、全局 store，以及出站落地 helper、
  Tab/Header 壳组件、共享合同测试文件）作为**前置任务组**，指定唯一 owner 先落地；
  `csv/18-batch-shared-surface.csv` 的 `[未分配]` 必须在此清空。这些文件一文件一写者，
  其余成员只 import / 只断言，第二个写者即阻塞项
- 其余成员的页面实现按成员分组，组间无重叠文件即可并行，重叠则串行
- 每个任务标注归属成员、ownership/conflict note、独立回退开关
- 就绪审查的「并行安全」栏必须列出独立任务组和共享文件，不能留空

就绪审查跑 G1–G3、G8、G5。存在阻塞项时不得询问实施授权。
就绪后只询问一次实施 go，一次覆盖整批，并绑定当前 artifact_revision、A/B revision、批准人、
时间、范围、验证义务、回退条件和 accepted warning IDs。
若已有 go 记录为 denied、expired、simulated、stub 或绑定旧 artifact_revision，不得进入 Wave 6。
需要改授权时重新进入 Wave 5：刷新 design/tasks、重跑就绪审查、重新询问实施 go，并作废旧 execute stub/handoff。

结束输出：design/tasks、任务数量、前置任务组与并行分组、readiness、验证矩阵、实施闸门、
handoff path/revision。
说明下一步为 Wave 6，然后停止。
```

## 7. Wave 4R：修复快车道 Frame + Plan 同会话连跑

只用于 `design-scope=repair` 且 Wave 3 未触发任何升级条件的批次，替代主路径的 Wave 4 + Wave 5 两个会话。
批次里只要有一个成员触发升级条件，整批退回主路径，或把该成员摘出来单独走主路径。

合并的是**会话**，不是闸门，也不是实施权限。迁移（含跨仓 host-port）在 `delivery-frame-spec`
路由表里固定为 High，而 High 明确要求 spec gate 与 implementation go **两次**用户批准
（`delivery-frame-spec` 的 Specification gate = one user ask，`delivery-plan-tasks` 的
Implementation go = one user ask）。把两次问询压成一次会破坏契约，也会造成
「就绪审查还没跑就要了实施 go」或「规格被追认批准」。因此本波保留两道闸门，只是在同一会话内顺序完成，
这本来就是 `delivery-plan-tasks` chain relay 规则允许的用法。B 应用代码仍然只能在 Wave 6 修改。

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-frame-spec 与 delivery-plan-tasks 两个 Skill，在同一会话内先 Frame 段后 Plan 段。
两个 Skill 各自的闸门都要保留：Frame 段问一次范围/规格批准，Plan 段就绪后再问一次实施 go。
不得把两次问询压成一次。
本波不得修改 A/B 应用代码，不要进入 Execute。

应已存在：<CHANGE_DIR>、Wave 3 的 design-scope=repair design-ready evidence path/digest、
<MATRIX>、每个成员在 B 侧的 route / menu / MPA 入口证据、批次准入判定。
若 design-scope 是 new-landing、design 未 ready、FLOW/CHAIN 只有表头、URL/entry 缺少真实证据、
入口只有文件名猜测、<MATRIX> 仍是整页 (skeleton) 行，
或 Wave 3 记录了任一升级条件，停止并改走 Wave 4 + Wave 5。

Frame 段：
从 domain evidence 摘要写入 external_artifacts：path、digest、A/B revision、<UNITS>、
每个成员的 old URL、现有 host entry、rollback、blockers/residuals。
不要要求 angularjs-to-vue3-host-migration 的 schema 进入 Delivery 状态。
写 proposal.md 和增量规格，范围固定为“<UNITS> 源站对等修复”：
- 目标与非目标；A 只读、B host-native
- 逐成员列出验收和独立回退开关；批次不得写成一条笼统的对等修复
- 显式声明不新增 API 契约、不改权限模型、不切流、不变更回退范围
- 行为/权限/URL/API/错误/视觉或人工视觉限制/runtime/rollback 验收
- 隐藏/显示偏差、控件替换偏差、模态框或富文本替换偏差逐条列为 approved-deviation 候选并写明理由
- 禁止复制 A layout、禁止无关重构、禁止长期桥接
迁移类变更固定 High。视觉对等没有测量链时只能写“manual-only / not proven”。
Frame 段结束时按 Frame Skill 完成澄清并问一次范围/规格批准，绑定当前 artifact_revision，
写入 State Source 和 handoff.json。未获批准不得进入 Plan 段。

Plan 段：
按 delivery-plan-tasks 契约写唯一权威 design.md/tasks.md，直接由 Wave 3 切片计划派生：
- 每个任务绑定 <MATRIX> 行 ID
- B 侧精确文件/符号/入口/路由/API/store/component
- 纵向切片，完成判据为入口已挂载、已调用 API、用户可达
- 行为、权限、URL、API、错误、runtime、rollback 验证矩阵
- 运行时证据获取方式；宿主工具链取不到时的 residual 处置与人工确认项
- 视觉要求：有测量链则写 G9 证据计划；无测量链则标 manual-only
- fallback/rollback 任务和演练命令
- 批次模式：共享宿主面作为唯一 owner 的前置任务组先落地，其余成员按组并行或串行，
  每个任务标注归属成员与 ownership/conflict note
就绪审查跑 G1–G3、G8、G5。存在阻塞项时不得询问实施授权。
试点 change 仍 active 且路径重叠时，G8 会判阻塞：先等试点 archive，不要显式接受并行风险绕过。
就绪后按 High 契约问第二次：实施 go，附成本/风险/回退摘要，五个面向保持 Agent 内部核对，
不做逐项问答。绑定当前 artifact_revision、A/B revision、批准人、时间、范围、验证义务、
回退条件和 accepted warning IDs。

闸门记录：
两条 gate 各自入账（规格闸门、实施闸门），handoff 标注 lane=repair-fastlane，
说明两道闸门在同一会话顺序完成。
任一闸门被拒绝或规格 artifact_revision 在 Plan 段发生变化时，实施 go 作废，退回对应闸门重走。

结束输出：change id/dir、route/risk、proposal/spec、design/tasks、任务数量、readiness、
验证矩阵、两条闸门记录、handoff path/revision。
说明下一步为 Wave 6，然后停止。
```

## 8. Wave 6：Delivery Execute + Fresh Verification

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-execute-verify Skill。
本波是唯一允许修改 B 应用代码的 Wave；A 严格只读。不要调用 angularjs-to-vue3-host-migration。

应已存在：design/tasks、绑定当前 revision 的规格闸门与实施 go、领域设计和运行时证据，
以及 Plan handoff（主路径）或 lane=repair-fastlane handoff（修复快车道）。
两条路径都必须有两条闸门记录；只有一条即视为批准不完整，回 Wave 5 或 Wave 4R。
A/B revision 或 evidence stale 则回对应产生 Wave。

Preflight：
- 实施 go 绑定当前 artifact_revision 与 A/B revision
- <FRESHNESS_MANIFEST> 中 A route/hash/i18n/API 与 B MPA/menu/permission/runtime digest 仍匹配当前 revision；
  不匹配则回 Wave 2/3，不得按旧文案或旧 hash 实施
- B 用户改动受保护
- 任务路径无未接受冲突
- baseline/runtime/evidence 有效
- B Node、包管理器、lockfile、scripts 来自 B 仓，不另发明命令；记录实测 `node -v` 与宿主声明基线，
  版本不符的运行结果不算验证证据
- 运行 git status，列出 intended files；`node_modules`、依赖缓存、dist/build/coverage/vendor 噪声一律阻塞
- `src/` 无改动不能代表 repo clean；若 repo dirty 但业务源码 clean，仍需解释每个非业务差异
- 宿主编译层：每个批次成员的入口能否编译；`lintOnSave`、TS `noImplicitAny`/`strict`、
  Prettier/EditorConfig 缩进配置；列出 `lintOnSave` 会扫到的范围外脏文件
- 任一成员入口编译失败为阻塞；全仓无关文件造成的 overlay 记 residual，
  两种情况都不得声明 dev server 健康
- 若 lint 基线已有范围外错误，记录 lint 基线命令、错误数和文件范围；可使用获批的替代验证命令覆盖本 UNIT，
  但不得把 lint 基线坏说成通过。若 dev proxy 会拦截 `public/` 或静态 mock 路径，先记录并调整验证路径。

严格按 tasks.md 执行：
- 适用时 RED → GREEN → REFACTOR
- 一次一个 ready task
- 批次模式：共享宿主面的前置任务组必须先全部完成，再动成员页面任务；
  跨成员并行只允许在 tasks.md 已声明无重叠文件的任务组之间进行
- 只改 B 获批范围
- 禁止对范围外遗留文件做格式化、缩进转换或顺手类型补全；这些文件记为 residual
- 禁止全仓 `lint --fix` / `prettier --write`；格式化命令只能限定到本 UNIT 获批文件，
  否则独立审查会把全仓格式化 diff 判成阻塞项
- 共享宿主面（出站落地 helper、Tab/Header 壳、共享合同测试文件）只有前置任务组的 owner 能写
- 切片完成判据：入口已挂载、已调用 API、用户在页面上可点到；只加 helper/组件文件不算完成
- T16 / 出站切 B 若未在 tasks.md 中授权，禁止把 active href/open 指向理论 B 目的页；
  若已授权，切换任务必须逐出口列 evidence，并保留邮件/外链绝对 URL 例外
- 每片执行 Source Contract Gates：身份字段、比较契约、命中层、选择器↔DOM、绝对 URL 剥源、
  B 骨架不改导航、同一 UNIT 出口共用落地函数
- 每片执行 CSS closure gates：模板 utility、Bootstrap 形态 class、sprite/icon size、runtime-hidden switch、
  空态图文、状态类 cascade safety、模态框/富文本替换偏差
- 新增/修改 TS helper 时立即标注回调参数和空数组/对象类型，避免 `noImplicitAny` / `never[]` 编译红
- 验证通过后才勾选任务

发现范围/验收问题回 Wave 4；发现设计/任务/rollback 问题回 Wave 5；
发现 A baseline 或领域闭包错误回 Wave 2/3。回流使用通用头字段。
修复快车道触发升级条件时，快车道两条闸门一并作废，改走主路径 Wave 4 + Wave 5，不得在本波继续实施。
批次里单个成员出现阻塞时，优先把该成员摘出批次单开 change，而不是让整批停下。
摘出必须重走该成员的 Frame/Plan 闸门，且从本批 tasks.md 和验证矩阵里显式移除。
在已批准范围内按 <MATRIX> 行补片属于本波增量修复，不回流。
同一 mounted wrapper 内后发现的源站区域，可在本波按 <MATRIX> 增量补片；不同页面/wrapper 或 API/权限/切流变化必须回流。

Fresh Verification Gate：
- B lint/build/test 或仓库现有等价命令
- Requirement/Scenario 对照
- 行为/权限/URL/API/错误
- page-init 对照：`run` 块、controller init、定时器/延迟弹窗、首屏请求、默认筛选值
- 页闭包包含动画脚本、插件脚本、全局增强脚本和运行时 CSS/JS 开关；漏扫这些文件导致的行为差异回 Wave 2/3
- display-contract parity：<MATRIX> 逐行过，检查源文案原文、控件形态、字段公式、默认值/校验、
  几何、CSS 依赖；对可见文案与可见数字确认运行时真的可见（DOM 存在不等于可见）
- source-contract gates：身份字段、比较契约、共享弹窗模式、命中层、选择器↔DOM、
  绝对 URL 剥源、B 骨架不改导航、同一 UNIT 出口落地一致、合约测试加载方式
- executable display-contract tests：有则跑宿主工具链测试，覆盖文案、CSS class、API payload、公式、entry wiring；测试证据不替代 <MATRIX>。
  测试必须 import 真实发布模块（纯 JS/`.mjs` helper 直接由宿主 runner 载入），改写副本或 regex 剥 TS 的产物不算证据
- 独立审查预检清单（这三类最常一轮被 block）：调用了错的 API/字段、空态与公式走了非源分支、
  出现全仓格式化 diff；另加一条：邮件体/外链/用户可复制链接必须逐条确认是否保留绝对 `rootPath`，
  不得被应用内剥源函数机械套用
- browser/runtime visibility：先按宿主工具链尝试取得运行时证据（既有 Playwright/Cypress/Puppeteer，
  或 dev server + 一次性 headless 截图/DOM dump 脚本），记录尝试与失败原因；
  确实取不到时输出需人工确认项，这些行保持 wired-unverified，不得标 verified，也不得由 agent 自行标 manual-verified
- entry-wiring parity：每个切片已挂载、已调用、用户可达
- outbound parity：T16 未授权时验证仍不切 B；T16 已授权时验证所有出站入口都走同一 B landing，且 iframe/mail/external URL 例外有证据
- rollback/fallback 演练
- OpenSpec coherence
- High 独立审查
- 若 visual=required，则生成 Delivery 自有 G9 证据；外部领域视觉证据只能作为 path/digest 引用

visual 的 manual-only 只能覆盖像素/截图/测量类结论。
禁止用“无测量链 → manual-only”跳过任何 display-contract 行；这些行是静态可对照的，必须逐行给结论。

全部通过后写 verification.md 和 verified handoff：
overall_status=verified，archive.status=deferred_to_openspec。
不要 archive/commit/push/PR/部署/切流。
若用户额外授权 commit，提交前必须展示 intended files；依赖目录、构建产物或未解释 lockfile 变化出现时必须停止。

Delivery verified 只表示交付变更通过，不能单独宣布整次迁移完成。
结束输出：任务/修改摘要、测试构建、实测 node 版本、<MATRIX> 行状态统计、
display-contract 与 entry-wiring 结论、G9 或 manual-only 说明、独立审查、rollback、
residual 清单、verification、handoff path/revision。说明下一步为 Wave 7，然后停止。
```

## 9. Wave 7：AngularJS 领域 Verify

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 angularjs-to-vue3-host-migration Skill，mode=verify，units=<UNITS>。
本波不修改 A/B 应用代码。
批次结论不取平均：逐成员出结论，任一成员未结清则整批 fail。

应已存在：Delivery verification、verified handoff、当前 B 代码、领域 assess/design evidence。
Delivery 未 verified 则回 Wave 6，不得声称迁移完成。Delivery verified_with_residuals 只能作为有残留交付证据，
不能满足本波完成候选。

先校验：
- A revision 是否仍等于领域证据绑定 revision；变化则回 Wave 2
- B revision 是否等于 Delivery verified revision；变化则回 Wave 6 或重新验证
- <FRESHNESS_MANIFEST> 中 A route/hash/i18n/API 与 B MPA/menu/permission/runtime digest 是否仍匹配；变化则回对应 Wave
- Codebase Memory 图谱是否绑定当前 revision；stale 则重新 index_repository
- domain evidence path/digest 是否完整

按当前 revision 刷新领域复核（各项字段定义见 hosted-method 的 Concrete Gates）：
- behavior parity
- page-init parity
- display-contract parity：<MATRIX> 逐行，含运行时可见性确认
- entry-wiring parity
- permission parity
- URL parity
- outbound/T16 parity：未授权不切，已授权逐出口切；目的页存在、Tab 接上、helper 存在都不能替代出站证据
- source-contract gates：身份字段、比较契约、共享弹窗模式、命中层、选择器↔DOM、
  绝对 URL 剥源、B 骨架不改导航、同一 UNIT 所有出口落地一致、合约测试加载方式
- CSS closure gates：模板 utility、Bootstrap 形态 class、sprite/icon size、runtime-hidden switch、
  空态图文、状态类 cascade safety、模态框/富文本替换偏差
- executable display-contract tests：有则引用宿主工具链测试结果；不替代 <MATRIX>
- browser/runtime visibility：先引用 Wave 6 的运行时证据尝试记录；仍无 agent 自验证据的行不得由 agent 标 verified。
  这类行只能由用户逐行确认后标 `manual-verified`（记录确认人、确认条件、时间），
  未确认的行保持 wired-unverified，Wave 7 不得 pass；不允许整片区域批量 manual-verified
- API parity
- visual measurement parity：只有存在截图/测量/差异证据才能下结论；否则标 manual-only，
  且 manual-only 不覆盖任何 display-contract 行
- runtime parity：实测 node 版本对照宿主基线、lockfile、lint/build/test、宿主编译层处置
- rollback：开关、范围、恢复条件、数据兼容

可运行脚本生成 verify 合同基线：
python angularjs-to-vue3-host-migration/scripts/generate_migration_plan.py verify \
  --project-name "<CHANGE_ID>" \
  --source-repo "<A>" \
  --host-repo "<B>" \
  --unit "<UNITS>" \
  --source-acquisition-warning "<沿用当前有效 warning 或留空>" \
  --host-acquisition-warning "<沿用当前有效 warning 或留空>" \
  --output-dir "<DOMAIN_ROOT>\\verify" \
  --format all

脚本输出 `csv/16-verify-result.csv`（批次汇总）与 `csv/16b-verify-units.csv`（逐成员结论）。
汇总 fail 时必须看逐成员表定位是哪个成员未结清，不得只报汇总。

只有当前 revision 上 functional、page-init、display-contract、entry-wiring、permission、
URL、API、runtime/build、rollback 全部通过，且 visual 测量结论有证据或明确标为人工未证明，
才能输出领域 pass / conditional pass。
<MATRIX> 存在 `missing`、`mismatched` 或 `wired-unverified` 行时不得 pass；
只有 `verified` / `manual-verified` / `approved-deviation` 才算结清。
领域 pass / conditional pass 仍不是完成声明；必须同时引用 Delivery verified handoff、
当前 host revision、Git Hygiene 无阻塞和无 blocking residual。

结束输出：
- final domain evidence path/digest 与 <MATRIX> path/digest
- functional/page-init/display-contract/entry-wiring/permission/url/api/runtime/visual/rollback 结果
- **archive gate 表**：逐 UNIT 一行，列「完成态 / MATRIX verified 数与总行数 / 未结清行 ID /
  降级标签（`visual-manual-only-not-proven`、`node-mismatch-not-verify-evidence`、`compile-not-run`、
  `lintonsave-out-of-unit-dirty`）/ archive 处置（`parity-complete`、`repair-done-partial`、`blocked`）」。
  verified 必须写成数字；`verified=0` 不得配 `parity-complete`。已知公式/行序/文案/二次确认/死代码 residual
  未清时处置只能是 `repair-done-partial`，并写明 residual owner 与后续条件
- blockers/residuals
- migration_completion_candidate

批次模式还要输出逐成员结论表，以及哪些成员可以进入完成判定、哪些必须摘出批次。

pass：逐条确认完成判定后，才能声称“<UNITS> 迁移完成候选”，然后停止。
fail：不要直接改代码；按回流表返回对应 Wave，然后停止。
```

## 10. 失败回流

继续使用原 `<CHANGE_ID>`，不创建第二个 OpenSpec change。

| 发现 | 返回 |
|---|---|
| change 意图、仓库、UNITS 输入错误 | Wave 1 建 change |
| 批次 design-scope 不一致、成员定位不唯一、宿主落点重叠 | Wave 2 Assess 重新组批 |
| 批次内单个成员阻塞 | 把该成员摘出批次单开 change，重走其 Frame/Plan 闸门；其余成员继续 |
| 试点未 archive 却已进 Plan（G8 路径重叠） | 等试点 archive 后回 Wave 5 / 4R Plan 段 |
| A/B 页面对照、host stack、host baseline gap 表、源入口证据错误或 stale | Wave 2 Assess |
| 源闭包整个区域漏扫（例如从未扫到 `ngApp.run`） | Wave 3 Design，改用 `new-landing` |
| 页级闭包、行为链、URL/API/权限/回退设计错误 | Wave 3 Design |
| `repair` scope 同一 wrapper 内后发现源站区域 | Wave 3 内补矩阵和切片，不改 scope |
| `repair` scope 触发升级条件（缺接口、改权限、切流、换 wrapper） | Wave 4 Frame + Wave 5 Plan，快车道闸门作废 |
| 目标、验收、范围、允许差异错误 | Wave 4 Frame，或修复快车道的 Wave 4R |
| 需要新增/变更 API 契约或权限模型 | Wave 4 Frame |
| 技术方案、任务拆分、兼容、rollback、验证矩阵错误 | Wave 5 Plan，或修复快车道的 Wave 4R |
| 已批准范围内的 B 实现缺陷 | Wave 6 Execute |
| 控件矩阵已有行不达标（文案、控件形态、默认值、几何、字段公式、CSS） | 当前实施波内增量补片，不回流 |
| 运行时可见性无法自验 | Wave 6 记录取证尝试与 residual；Wave 7 由用户逐行 `manual-verified` |
| Delivery 未 verified | Wave 6 Execute |
| A revision 变化 | Wave 2 Assess |
| B revision 变化且已实施 | Wave 6 Execute / fresh verify |
| Codebase Memory 索引 stale | 当前需要证据的 Wave 重新 index |

回流必须携带：

```text
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point
```

## 11. 完成判定

完成判定按 UNIT 逐个做，不按批次整体做。批次只有在**每个成员都各自满足下列全部条件**时才算结清；
某个成员不满足，就把它摘出批次单开 change，其余成员照常结清。

只有以下全部满足，才能声称某个 UNIT “迁入 Vue3 Host 完成候选”：

- A 未发生应用代码修改；
- B 为 Vue3 host-native 实现，未引入 Vue2 / `@vue/compat` / 长期桥接；
- OpenSpec、批准、tasks、verification 和领域证据均绑定当前 revision；
- A/B Codebase Memory 或 fallback 证据均绑定当前 revision；
- Delivery verified，且规格闸门与实施 go 两条记录都在（主路径分布在 Wave 4/5，快车道同在 Wave 4R）、
  High 独立审查、必要的 G9 或 manual-only 视觉说明完成；
- <MATRIX> 中归属该 UNIT 的每一行为 `verified`、`manual-verified` 或 `approved-deviation`，
  无 `missing` / `mismatched` / `wired-unverified`；
- 每个切片通过 entry-wiring parity：入口已挂载、已调用、用户可达；
- AngularJS domain verify 的 behavior、page-init、display-contract、permission、URL、API、
  runtime/build、rollback 通过；
- 仓库获取可用，A/B revision 当前且 HEAD 可读；
- Git Hygiene 无阻塞；没有 dependency/cache/build 噪声进入 intended commit；
- 像素/截图类视觉结论有测量证据；没有测量链时明确不是 visual pass，且 manual-only 不覆盖任何
  display-contract 行；
- fallback/rollback 已演练或清楚记录未演练 blocker，且该 UNIT 的回退开关独立于同批其他成员；
- UNIT 不处于 `dest-built-unwired`、`wired-hidden`、`develop-native`、`orphan-mpa`、`unknown` 等开口状态；
- MATRIX `verified=0`、已知公式/行序/API payload/URL/query/权限 residual、或 visual 只有 manual-only 且 display-contract 未结清时，
  不得把页面清单标绿或 archive 成对等完成；此时 archive 处置只能是 `repair-done-partial`；
- archive gate 表已逐 UNIT 填完，降级标签原样带进 archive 记录；此后任何状态汇报都必须保留这些标签，
  不得把带标签的 UNIT 叙述成「已对等」；
- 无 blocking residual。

archive 之后该 UNIT 关闭：新发现的偏差只能开新 change 并重走闸门，不得回填已 archive 的包，
也不得把已 archive 的 UNIT 再列进后续批次的 `<UNITS>`。

此时仍不自动 archive、commit、push、PR、部署、切流、删除 fallback 或下线 A。

## 12. 使用者与 Agent 可用性检查

### 使用者

- 三个必填值只填一次：A、B、UNITS（1–5 个）。
- 每个 Wave 只复制通用头和一个增量提示词。
- 主路径：Wave 1 → 2 → 3(new-landing) → 4 → 5 → 6 → 7。
- 修复快车道：Wave 1 → 2 → 3(repair) → 4R → 6 → 7，少一次换会话，批准次数不变（规格 + 实施）。
- 批次：批准次数与单 UNIT 相同（2 次），波次也相同；省下的是 (N-1) 遍波次和 2(N-1) 次批准。
- 首个 UNIT 必须单跑到 archive；之后组批，且批次进 Plan 前试点必须已 archive。
- 只处理阻塞问题、规格/实施批准、偏差批准和运行时人工确认。
- 不需要手工维护 JSON、digest、revision 或任务状态。

### AI Agent

- 每个 Wave 都有明确 Skill/mode、状态源、权限范围、输入工件、完成门禁和输出。
- 设计只有一个 Wave；`design-scope` 决定准入校验和批准链，不复制第二套合同要求。
- 领域证据与 Delivery 生命周期不争夺状态权威。
- 只有 Wave 6 修改 B，快车道也不例外。
- 显示合同在 <MATRIX> 单点维护，跨 Wave 只更新行状态，不重开分析；批次靠「迁移单元」列区分归属。
- 批次是一个 change 内的并行任务组，不是多个并行 change；G8 只管跨 change，因此不会被触发。
- 完成判定、回退开关、verify 结论都是逐 UNIT 的；批次汇总不取平均。
- revision/digest/approval 绑定防止用旧证据宣布完成。

### 可达性

在 A 可读、B 可构建、权限/测试数据可用、Codebase Memory 与 OpenSpec 可用，并且所有 Wave 门禁通过时，
这套编排可以对“旧混合页迁入现有 Vue3 宿主”给出证据化完成候选。

缺少真实权限环境、后端接口、测试数据、截图/测量链、字体/图标资源或可演练 rollback 时，必须标为 blocker
或 residual，不能用“看起来差不多”或单次代码审查代替通过结论。

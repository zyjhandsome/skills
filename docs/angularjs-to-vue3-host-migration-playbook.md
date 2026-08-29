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
> 两条路径的 B 写权限不同：主路径（7 Wave）由 `delivery-execute-verify` 独占写 B；
> 快路径（Wave 2.5 壳页对等修复）在用户明确授权且不越出源站对等范围时，在同一会话内写 B，
> 不经过 Frame/Plan。其余所有 Wave 对 A/B 应用代码只读。

## 0. 编排结论

主路径（7 Wave）适用于“**B 里还没有这个页面**，或者需要切流/回退、需要 OpenSpec 规格审计”。
真实项目建议先选 1 个 UNIT 跑通 Wave 1→3，确认 A/B 对照、真实 URL 与 design-ready
合同质量后，再进入 Frame 和批量实施。

```text
Wave 1  建 change（无规格闸门）
  → Wave 2  angularjs assess
  → Wave 3  angularjs design
  → Wave 4  Delivery Frame 规格批准
  → Wave 5  Delivery Plan + 实施 go
  → Wave 6  Delivery Execute + Fresh Verification
  → Wave 7  angularjs verify
```

快路径（Wave 2.5 Repair）适用于“**B 已有该 UNIT 的入口壳页，目标是对照源站对等修复**”：

```text
Wave 1  建 change
  → Wave 2  angularjs assess（必须产出控件矩阵）
  → Wave 2.5  Repair：按区域切片修 B + 增量 display-contract verify
  → Wave 7  angularjs verify
```

选路判定（三条全真才走快路径）：

| 条件 | 快路径 | 主路径 |
|---|---|---|
| B 已有该 UNIT 的 MPA/router 入口证据 | 是 | 否或未证明 |
| 目标是源站对等修复，不新增 API 契约、不改权限模型、不涉及切流 | 是 | 否 |
| 用户已授权本轮修改 B | 是 | 需先走 Frame/Plan 批准 |

快路径中一旦发现缺接口、要动权限模型、要加源站没有的行为，或源闭包当初漏扫了整个区域，
立即停止并升级回 Wave 3/4。

### 职责边界

| 层 | 职责 |
|---|---|
| `angularjs-to-vue3-host-migration` | 双仓领域事实：A/B 页面对照、混合栈闭包、AngularJS/jQuery/服务端模板行为链、URL/API/权限/回退合同、最终领域复核 |
| `delivery-frame-spec` | 创建或恢复 OpenSpec change，写 proposal/spec，完成范围与规格批准 |
| `delivery-plan-tasks` | 写 design/tasks、纵向切片、就绪审查、实施闸门 |
| `delivery-execute-verify` | 主路径唯一应用代码 mutation owner；只修改 Vue3 宿主 B；完成 Fresh Verification、独立审查和 verified handoff |
| Wave 2.5 Repair | 快路径唯一写 B 的会话；只做源站对等修复，越界即升级回 Wave 3/4 |
| OpenSpec change | Delivery 生命周期和批准状态真相 |
| 本剧本 | 只规定会话顺序、提示词、工件交接和停止点 |

固定原则：

- A 始终只读；只有 Wave 6（主路径）或 Wave 2.5（快路径）可以修改 B 的应用代码。
- 迁移默认 High 风险；迁移单元必须是独立可切换页面或用户行为，不能默认整仓迁。
- 落地规则、控件矩阵、交互等价、i18n 原文、CSS 闭包、切片完成定义、宿主编译层：
  见 `angularjs-to-vue3-host-migration` 的 Hosted Migration Rules / Display Contract /
  Host Compile Overlay 与 `references/hosted-vue3-migration-method.md`。本剧本不复述。
- Delivery `verified` 不等于领域迁移完成；Wave 7 领域复核通过后才能说“迁移完成候选”。
- 完成后仍不自动 archive、commit、push、PR、部署、切流、删除 fallback 或下线 A。

## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 首次使用时，在“会话通用头”填写 A、B、UNIT 三个必填值。
2. 每个 Wave 开一个全新会话，粘贴“会话通用头 + 当前 Wave 代码块”。
3. 当前 Wave 完成并停止后，再开下一个 Wave。
4. Wave 2 结束时会给出选路结论：壳页对等修复走 Wave 2.5，其余走 Wave 3。
5. 用户只处理真正阻塞的问题、规格批准、实施批准或对等修复范围批准；
   不需要手工维护 digest、revision、任务状态。

### 1.2 会话通用头

```text
这是一个全新独立会话，不得使用其他会话的聊天记忆补结论。

用户输入：
<A> = AngularJS / jQuery / JSP / Thymeleaf 源仓绝对路径
<B> = 现有 Vue3 宿主仓绝对路径
<UNIT> = 待迁移页面、URL、菜单项、路由或用户行为，例如 home / taskManage / projectProgress

自动派生并保持稳定：
- <SLUG>：由 <UNIT> 规范化；过长时追加短 SHA-256
- <CHANGE_ID>：migrate-<SLUG>-to-vue3-host
- <CHANGE_DIR>：openspec\changes\<CHANGE_ID>
- <EVIDENCE_ROOT>：<CHANGE_DIR>\evidence
- <DOMAIN_ROOT>：<EVIDENCE_ROOT>\angularjs-hosted-vue3-migration
- <CONFIG>：<DOMAIN_ROOT>\migration-run-config.json
- <INDEX_MANIFEST>：<DOMAIN_ROOT>\codebase-index-manifest.json
- <RUNTIME_MANIFEST>：<DOMAIN_ROOT>\runtime-service-manifest.json
- <MATRIX>：<DOMAIN_ROOT>\display-contract-<SLUG>.md（控件矩阵唯一台账，跨 Wave 只更新不重开）

<CONFIG> 存在后以其记录为准；与本次输入不一致时停止。

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

仓库获取、revision 绑定、Git 卫生门禁：按
`angularjs-to-vue3-host-migration/references/hosted-vue3-migration-method.md` 的
Repo Acquisition And Revision Binding 与 Git Hygiene Gate 执行并记录。
硬停止条件：path 存在但不是 git repo，或 HEAD 不可读。
`sslVerify=false` 只能作为诊断警告记录，不得成为默认策略或持久配置。

固定边界（本剧本唯一权限声明，其余落地规则见 Skill）：
- A 始终只读；A 出现业务代码修改通常使领域证据 stale。
- 主路径只有 Wave 6（delivery-execute-verify）可修改 B 应用代码；快路径只有 Wave 2.5 可修改 B。
- 其余所有 Wave 对 A/B 应用代码只读。
- 禁止新功能、无关重构、Vue2、@vue/compat、长期桥接依赖进入 B。
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
| 2.5 Repair | Assess evidence、<MATRIX>、B 已有入口证据、用户改 B 授权 |
| 3 Design | Assess evidence、A/B revisions、候选迁移单元、host stack |
| 4 Frame | Design-ready domain evidence、change 目录、意图草稿 |
| 5 Plan | 已批准 Frame 规格、domain evidence path/digest、Frame handoff |
| 6 Execute | design/tasks、Plan handoff、实施 go、领域设计和运行时证据 |
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

硬前提：B 的 OpenSpec 可写；Codebase Memory 可索引/查询 A/B。
openspec: cli-only 时按 Frame Skill 固定三行报告，并询问 initialize_repo；
不得发明平行 Markdown 状态。

读取 A/B 当前 revision。索引缺失时先 index_repository，再用 get_architecture 证明可查询。
校验 <A>/<B>/<UNIT> 基本可定位；不能定位则停止。
若 clone/fetch 曾失败但 <A> 或 <B> 已是有效 git repo 且 HEAD 可读，记录 acquisition_warning 后可以继续；
若 HEAD 不可读或路径不是 git repo，停止。

正式创建或恢复唯一 <CHANGE_DIR>，并创建 <DOMAIN_ROOT>、<CONFIG>、
<INDEX_MANIFEST>、<RUNTIME_MANIFEST> 初始结构。
<CONFIG> 或初始 evidence 必须包含 repo acquisition 表与 git hygiene 摘要。
本波不得安装依赖或启动 A/B。

只写意图草稿：
- A 只读
- 仅 Wave 6 修改 B
- B host-native shell/auth/router/API/state/components/i18n/proxy/runtime
- 迁移单元为 <UNIT>
- 保留 fallback / rollback
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
当扫描具体 <UNIT> 时，同时读取 jQuery 与 variable-flow references。

按 Skill 的 assess 输出合同写盘，不要在本提示词里重述字段清单。
本波额外必须产出：
- host compile overlay：`lintOnSave`、TS `noImplicitAny`/`strict`、Prettier/EditorConfig 缩进、
  dev-server overlay 范围、实测 `node -v` 与宿主声明 Node 基线
- <UNIT> 的候选 source entry、真实 source URL 与 host landing point
- 若 <UNIT> 判为 `partial-overlap`：把首轮控件矩阵写入 <MATRIX>，每行填 `B 现状`
  （missing / mismatched / wired-unverified / verified / approved-deviation）
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

脚本输出只是 evidence baseline；必须用代码证据复核，不得把通用表格当设计，
也不得用脚本表替代控件矩阵。
仓库获取与 Git 卫生表必须进入 assess evidence；出现 dependency/cache/build noise 时，后续不得声明 commit-ready。
A/B 页面对照与页面分类规则按 Skill 与 hosted-method 执行（文件名不等于 already-migrated、
`.vue` 不默认当页面、根 `index.html` 只能当 host-shell、别名近似命中标 needs_human_correction）。

生成 assess evidence packet 或 Markdown 摘要到 <DOMAIN_ROOT>，记录 path/digest、A/B revision、
source/host page comparison、URL/entry mapping、host compile overlay、<MATRIX> path/digest、blockers。

若 <UNIT> 缺少真实 source URL 或 B host entry 证据，输出回流字段并停止。
若 <UNIT> 在 A 或 B 中无法定位，输出回流字段并停止。
否则给出选路结论：
- <UNIT> 判为 `partial-overlap`、B 入口已证明、且目标是对等修复 → 下一步 Wave 2.5 Repair
- 其他情况 → 下一步 Wave 3 Design
然后停止。
```

## 3.5 Wave 2.5：壳页对等修复（快路径）

只在 §0 选路三条件全真时使用。新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 angularjs-to-vue3-host-migration Skill，mode=design，unit=<UNIT>，profile=repair。
本波是快路径下唯一允许修改 B 应用代码的 Wave；A 严格只读。

应已存在：<CONFIG>、Wave 2 assess evidence、<MATRIX>、B 侧 <UNIT> 的 MPA/router 入口证据。
缺任一项则回 Wave 2。

读取 hosted-vue3-migration-method 的 Landing Rules、Interaction Equivalence Test、
Display Contract Matrix、Page Init And Side Effects、CSS Closure、Host Compile Overlay、
Shell-Page Repair；按需读取 jquery 与 variable-flow references。
不要读取 angularjs-vue3-migration-method（绿场）。

准入校验，任一不成立就停止并转 Wave 3：
- <UNIT> 在 B 已有入口且用户可访问
- 目标是源站对等修复：不新增 API 契约、不改权限模型、不加源站没有的行为、不涉及切流或回退范围变更
- 用户已授权本轮修改 B

Step 1 补齐合同（只读）：
刷新 <MATRIX>，并补 page-init 表、源 i18n 原文表、CSS 闭包表。
每个可见数字/列表必须写出 API + 字段公式（求和、拼接、全选标题都要写）。
矩阵缺行、`B 现状` 空、或存在只有表头的表，禁止进入 Step 3。

Step 2 一次范围批准：
按区域列出切片顺序与每片涉及的 <MATRIX> 行 ID，询问一次“对等修复范围批准”，
绑定当前 A/B revision 与 <MATRIX> digest。未获批准不得改 B。
OpenSpec 记录可选；若已有 change，把 <MATRIX> path/digest 写入 external_artifacts。

Step 3 逐片修复（可改 B）：
每片按顺序执行，不并行：
1. 复述该片的源合同：源文案原文、控件形态、字段公式、默认值/校验、几何、CSS 依赖、启动副作用
2. 改 B，只动本片范围内文件
3. 确认入口已挂载并被调用（未挂到入口的 helper/组件不算完成）
4. 在浏览器走一遍：默认值、空态、校验、错误态；对可见文案与可见数字确认运行时真的可见
   （DOM 存在不等于可见，注意 `font-size: 0`、sprite 缺失、被覆盖样式）
5. 把该片 <MATRIX> 行原地更新为 verified / approved-deviation / 仍 mismatched，并写证据

Preflight 与卫生（每片都查）：
- 当前入口能否编译；当前 UNIT 入口编译失败为阻塞
- 列出 `lintOnSave` 会扫到的范围外脏文件；这些文件记为 residual，禁止顺手格式化或补类型
- 全仓无关 overlay 记 residual，不得声明 dev server 健康
- 运行 git status 列出 intended files；依赖目录、构建产物、未解释 lockfile 变化一律阻塞
- 记录实测 `node -v` 与宿主声明基线；版本不符的运行结果不算验证证据

升级条件（出现即停止，输出回流字段）：
- 缺接口或接口契约需要变更 → Wave 4
- 需要改权限模型或新增源站没有的行为 → Wave 4
- 源闭包当初漏扫了整个区域 → Wave 3
- 需要切流、灰度或回退范围变更 → Wave 4

结束输出：本波完成的切片、<MATRIX> 行状态统计、residual 与 blocker、
intended files、node 版本、<MATRIX> path/digest。
不要 archive、commit、push、PR、部署、切流。
说明下一步为 Wave 7 领域 verify（或继续下一批切片），然后停止。
```

## 4. Wave 3：AngularJS 领域 Design

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 angularjs-to-vue3-host-migration Skill，mode=design，unit=<UNIT>。
本波只做页级落地设计，不修改 A/B 应用代码。

应已存在：<CONFIG>、Wave 2 assess evidence、A/B revision、host stack、A/B page comparison。
缺失或 stale 则回 Wave 2。

读取 hosted-vue3-migration-method、jquery-vue3-business-logic-analysis、
business-logic-variable-flow-analysis。不要读取 angularjs-vue3-migration-method（绿场）。

围绕 <UNIT> 按 Skill 的 design 输出合同生成设计包并写盘，不要在本提示词里重述字段清单。
本波额外必须满足：
- 同一页 AngularJS + jQuery + 服务端模板合并成一个闭包，不拆成平行报告
- 控件矩阵写入 <MATRIX>；page-init 表、源 i18n 原文表、CSS 闭包表齐备
- 每个可见数字/列表都有 API + 字段公式
- 切片为纵向切片，完成判据是“入口已挂载且用户可点到”，不是“helper 文件已存在”
- FLOW/VAR/CHAIN 只针对 <UNIT>，不铺全仓空表

design-ready gate 按 hosted-method 的 Design-Ready Gate 逐项判定。
<UNIT> 若为 `partial-overlap`，缺控件矩阵、page-init 表、i18n 原文表或 CSS 闭包表任一项，
即为 `not-ready`，只填 1～2 条点击流不得放行。

可运行脚本生成 design 合同基线：
python angularjs-to-vue3-host-migration/scripts/generate_migration_plan.py design \
  --project-name "<CHANGE_ID>" \
  --source-repo "<A>" \
  --host-repo "<B>" \
  --unit "<UNIT>" \
  --source-acquisition-warning "<沿用当前有效 warning 或留空>" \
  --host-acquisition-warning "<沿用当前有效 warning 或留空>" \
  --output-dir "<DOMAIN_ROOT>\\design" \
  --format all

design/verify 脚本为可选；只在需要合同基线骨架时运行。
输出 design-ready domain evidence path/digest 与 <MATRIX> path/digest。
脚本生成的空合同必须标 `not-ready: empty-contract`；脚本表不能替代控件矩阵；
只有人工或后续分析把 gate 填成 evidence-backed ready，才能继续。
若存在 implementation-blocking TBD、FLOW/CHAIN 只有空表头、URL/entry 缺少真实证据，
或 design-ready gate 任一必填项未满足，停止并给回流字段；不得进入 Frame 规格批准。
否则说明下一步为 Wave 4，然后停止。
```

## 5. Wave 4：Delivery Frame 规格批准

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-frame-spec Skill。
不要 Plan/Execute。本波不得修改 A/B 应用代码。

应已存在：<CHANGE_DIR>、Wave 3 design-ready domain evidence path/digest。
若只有 assess、design 未 ready、FLOW/CHAIN 只有表头、URL/entry 缺少真实证据，
或 design-ready gate 未通过，停止并回 Wave 3。

从 domain evidence 摘要写入 external_artifacts：path、digest、A/B revision、<UNIT>、
old URL、新 host entry 候选、rollback、blockers/residuals。
不要要求 angularjs-to-vue3-host-migration 的 schema 进入 Delivery 状态。

基于当前领域事实完成 proposal.md 和增量规格：
- 目标与非目标
- A 只读、B host-native
- 迁移范围为 <UNIT>
- 行为/权限/URL/API/错误/视觉或人工视觉限制/runtime/rollback 验收
- fallback 保留条件
- 禁止复制 A layout、禁止无关重构、禁止长期桥接

迁移类变更固定 High。若视觉对等没有测量链，只能写“manual-only / not proven”，不能写 visual pass。

按 Frame Skill 完成澄清和规格闸门，只询问一次范围批准。
批准必须绑定当前 artifact_revision，写入 State Source 和 handoff.json。

结束输出：change id/dir、route/risk、proposal/spec、规格闸门、handoff path/revision。
说明下一步为 Wave 5，然后停止。
```

## 6. Wave 5：Delivery Plan + 实施 Go

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-plan-tasks Skill。
只消费当前有效 Frame handoff；不要修改 A/B 应用代码，不要进入 Execute。

应已存在：已批准 Frame 规格、domain evidence path/digest、Frame handoff。
缺失或批准失效则回 Wave 4。

校验 domain evidence 的 path/digest 和 A/B revision。
刷新 B 当前路径/符号事实；检查其他 active change 路径重叠。

按 Skill 契约写唯一权威 design.md/tasks.md：
- B 侧精确文件/符号/入口/路由/API/store/component
- 纵向切片，每片都能独立验证
- 复用/改造/新建处置
- 行为、权限、URL、API、错误、runtime、rollback 验证矩阵
- 视觉要求：有测量链则写 G9 证据计划；无测量链则标 manual-only，不得假装通过
- fallback/rollback 任务和演练命令

就绪审查跑 G1–G3、G8、G5。存在阻塞项时不得询问实施授权。
就绪后只询问一次实施 go，并绑定当前 artifact_revision、A/B revision、批准人、
时间、范围、验证义务、回退条件和 accepted warning IDs。

结束输出：design/tasks、任务数量、readiness、验证矩阵、实施闸门、handoff path/revision。
说明下一步为 Wave 6，然后停止。
```

## 7. Wave 6：Delivery Execute + Fresh Verification

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-execute-verify Skill。
本波是唯一允许修改 B 应用代码的 Wave；A 严格只读。不要调用 angularjs-to-vue3-host-migration。

应已存在：design/tasks、绑定当前 revision 的实施 go、Plan handoff、领域设计和运行时证据。
缺失则回 Wave 5；A/B revision 或 evidence stale 则回对应产生 Wave。

Preflight：
- 实施 go 绑定当前 artifact_revision 与 A/B revision
- B 用户改动受保护
- 任务路径无未接受冲突
- baseline/runtime/evidence 有效
- B Node、包管理器、lockfile、scripts 来自 B 仓，不另发明命令；记录实测 `node -v` 与宿主声明基线，
  版本不符的运行结果不算验证证据
- 运行 git status，列出 intended files；`node_modules`、依赖缓存、dist/build/coverage/vendor 噪声一律阻塞
- `src/` 无改动不能代表 repo clean；若 repo dirty 但业务源码 clean，仍需解释每个非业务差异
- 宿主编译层：当前 UNIT 入口能否编译；`lintOnSave`、TS `noImplicitAny`/`strict`、
  Prettier/EditorConfig 缩进配置；列出 `lintOnSave` 会扫到的范围外脏文件
- 当前 UNIT 入口编译失败为阻塞；全仓无关文件造成的 overlay 记 residual，
  两种情况都不得声明 dev server 健康

严格按 tasks.md 执行：
- 适用时 RED → GREEN → REFACTOR
- 一次一个 ready task
- 只改 B 获批范围
- 禁止对范围外遗留文件做格式化、缩进转换或顺手类型补全；这些文件记为 residual
- 切片完成判据：入口已挂载、已调用 API、用户在页面上可点到；只加 helper/组件文件不算完成
- 验证通过后才勾选任务

发现范围/验收问题回 Wave 4；发现设计/任务/rollback 问题回 Wave 5；
发现 A baseline 或领域闭包错误回 Wave 2/3。回流使用通用头字段。
在已批准范围内按 <MATRIX> 行补片属于本波增量修复，不回流。

Fresh Verification Gate：
- B lint/build/test 或仓库现有等价命令
- Requirement/Scenario 对照
- 行为/权限/URL/API/错误
- page-init 对照：`run` 块、controller init、定时器/延迟弹窗、首屏请求、默认筛选值
- display-contract parity：<MATRIX> 逐行过，检查源文案原文、控件形态、字段公式、默认值/校验、
  几何、CSS 依赖；对可见文案与可见数字确认运行时真的可见（DOM 存在不等于可见）
- entry-wiring parity：每个切片已挂载、已调用、用户可达
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

## 8. Wave 7：AngularJS 领域 Verify

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 angularjs-to-vue3-host-migration Skill，mode=verify，unit=<UNIT>。
本波不修改 A/B 应用代码。

主路径应已存在：Delivery verification、verified handoff、当前 B 代码、领域 assess/design evidence。
Delivery 未 verified 则回 Wave 6，不得声称迁移完成。
快路径应已存在：Wave 2.5 的范围批准记录、<MATRIX>、当前 B 代码、assess evidence；
缺失则回 Wave 2.5。

先校验：
- A revision 是否仍等于领域证据绑定 revision；变化则回 Wave 2
- B revision 是否等于 Delivery verified revision；变化则回 Wave 6 或重新验证
- Codebase Memory 图谱是否绑定当前 revision；stale 则重新 index_repository
- domain evidence path/digest 是否完整

按当前 revision 刷新领域复核（各项字段定义见 hosted-method 的 Concrete Gates）：
- behavior parity
- page-init parity
- display-contract parity：<MATRIX> 逐行，含运行时可见性确认
- entry-wiring parity
- permission parity
- URL parity
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
  --unit "<UNIT>" \
  --source-acquisition-warning "<沿用当前有效 warning 或留空>" \
  --host-acquisition-warning "<沿用当前有效 warning 或留空>" \
  --output-dir "<DOMAIN_ROOT>\\verify" \
  --format all

只有当前 revision 上 functional、page-init、display-contract、entry-wiring、permission、
URL、API、runtime/build、rollback 全部通过，且 visual 测量结论有证据或明确标为人工未证明，
才能输出领域 pass / conditional pass。
<MATRIX> 存在 `missing` 或 `mismatched` 行时不得 pass。
领域 pass / conditional pass 仍不是完成声明；主路径必须同时引用 Delivery verified handoff、
当前 host revision、Git Hygiene 无阻塞和无 blocking residual；快路径必须引用 Wave 2.5
范围批准记录、当前 host revision 与同样的卫生结论。

结束输出：
- final domain evidence path/digest 与 <MATRIX> path/digest
- functional/page-init/display-contract/entry-wiring/permission/url/api/runtime/visual/rollback 结果
- blockers/residuals
- migration_completion_candidate

pass：逐条确认完成判定后，才能声称“<UNIT> 迁移完成候选”，然后停止。
fail：不要直接改代码；按回流表返回对应 Wave，然后停止。
```

## 9. 失败回流

继续使用原 `<CHANGE_ID>`，不创建第二个 OpenSpec change。

| 发现 | 返回 |
|---|---|
| change 意图、仓库、UNIT 输入错误 | Wave 1 建 change |
| A/B 页面对照、host stack、源入口证据错误或 stale | Wave 2 Assess |
| 源闭包整个区域漏扫（例如从未扫到 `ngApp.run`） | Wave 3 Design |
| 页级闭包、行为链、URL/API/权限/回退设计错误 | Wave 3 Design |
| 目标、验收、范围、允许差异错误 | Wave 4 Frame |
| 需要新增/变更 API 契约或权限模型 | Wave 4 Frame |
| 技术方案、任务拆分、兼容、rollback、验证矩阵错误 | Wave 5 Plan |
| 已批准范围内的 B 实现缺陷 | Wave 6 Execute / Wave 2.5 Repair |
| 控件矩阵已有行不达标（文案、控件形态、默认值、几何、字段公式、CSS） | 当前实施波内增量补片，不回流 |
| Delivery 未 verified | Wave 6 Execute |
| A revision 变化 | Wave 2 Assess |
| B revision 变化且已实施 | Wave 6 Execute / fresh verify |
| Codebase Memory 索引 stale | 当前需要证据的 Wave 重新 index |

回流必须携带：

```text
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point
```

## 10. 完成判定

只有以下全部满足，才能声称“<UNIT> 迁入 Vue3 Host 完成候选”：

- A 未发生应用代码修改；
- B 为 Vue3 host-native 实现，未引入 Vue2 / `@vue/compat` / 长期桥接；
- OpenSpec、批准、tasks、verification 和领域证据均绑定当前 revision；
- A/B Codebase Memory 或 fallback 证据均绑定当前 revision；
- 主路径：Delivery verified、High 独立审查、必要的 G9 或 manual-only 视觉说明完成；
  快路径：Wave 2.5 范围批准记录有效，且未出现升级条件；
- <MATRIX> 每一行为 `verified` 或 `approved-deviation`，无 `missing` / `mismatched`；
- 每个切片通过 entry-wiring parity：入口已挂载、已调用、用户可达；
- AngularJS domain verify 的 behavior、page-init、display-contract、permission、URL、API、
  runtime/build、rollback 通过；
- 仓库获取可用，A/B revision 当前且 HEAD 可读；
- Git Hygiene 无阻塞；没有 dependency/cache/build 噪声进入 intended commit；
- 像素/截图类视觉结论有测量证据；没有测量链时明确不是 visual pass，且 manual-only 不覆盖任何
  display-contract 行；
- fallback/rollback 已演练或清楚记录未演练 blocker；
- 无 blocking residual。

此时仍不自动 archive、commit、push、PR、部署、切流、删除 fallback 或下线 A。

## 11. 使用者与 Agent 可用性检查

### 使用者

- 三个必填值只填一次：A、B、UNIT。
- 每个 Wave 只复制通用头和一个增量提示词。
- 壳页对等修复走快路径：Wave 1 → 2 → 2.5 → 7，只需一次范围批准。
- 只处理阻塞问题、规格批准和实施批准。
- 不需要手工维护 JSON、digest、revision 或任务状态。

### AI Agent

- 每个 Wave 都有明确 Skill/mode、状态源、权限范围、输入工件、完成门禁和输出。
- 领域证据与 Delivery 生命周期不争夺状态权威。
- 只有 Wave 6（主路径）或 Wave 2.5（快路径）修改 B。
- 显示合同在 <MATRIX> 单点维护，跨 Wave 只更新行状态，不重开分析。
- revision/digest/approval 绑定防止用旧证据宣布完成。

### 可达性

在 A 可读、B 可构建、权限/测试数据可用、Codebase Memory 与 OpenSpec 可用，并且所有 Wave 门禁通过时，
这套编排可以对“旧混合页迁入现有 Vue3 宿主”给出证据化完成候选。

缺少真实权限环境、后端接口、测试数据、截图/测量链、字体/图标资源或可演练 rollback 时，必须标为 blocker
或 residual，不能用“看起来差不多”或单次代码审查代替通过结论。

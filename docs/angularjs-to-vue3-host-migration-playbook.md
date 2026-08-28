# AngularJS 混合页迁入 Vue3 Host × Delivery：用户粘贴剧本

> 这不是 Skill。不要把它当独立技能加载，也不要改任何 Skill 的 schema、验证器或内部状态格式。
>
> 用途：把一次 AngularJS / jQuery / JSP / Thymeleaf 混合页迁入现有 Vue3 宿主仓拆成可粘贴的会话。
> 允许按名组合 `angularjs-to-vue3-host-migration`、`delivery-frame-spec`、
> `delivery-plan-tasks`、`delivery-execute-verify`。
>
> `angularjs-to-vue3-host-migration` 仍保持独立：只产出领域证据、页级设计和最终领域复核，不调用
> Delivery，不修改应用业务代码。Delivery Family 仍独立负责 OpenSpec、批准、计划、实施、Fresh Verification。

## 0. 编排结论

主路径适用于“迁移目标已经明确：源仓 A 的某个页面/用户行为迁入 Vue3 宿主 B”。
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

### 职责边界

| 层 | 职责 |
|---|---|
| `angularjs-to-vue3-host-migration` | 双仓领域事实：A/B 页面对照、混合栈闭包、AngularJS/jQuery/服务端模板行为链、URL/API/权限/回退合同、最终领域复核 |
| `delivery-frame-spec` | 创建或恢复 OpenSpec change，写 proposal/spec，完成范围与规格批准 |
| `delivery-plan-tasks` | 写 design/tasks、纵向切片、就绪审查、实施闸门 |
| `delivery-execute-verify` | 唯一应用代码 mutation owner；只修改 Vue3 宿主 B；完成 Fresh Verification、独立审查和 verified handoff |
| OpenSpec change | Delivery 生命周期和批准状态真相 |
| 本剧本 | 只规定会话顺序、提示词、工件交接和停止点 |

固定原则：

- A 始终只读。
- 只有 Wave 6 可以修改 B 的应用代码。
- 迁移默认 High 风险；跨仓、权限、URL、API、回退和视觉/行为对等都必须有门禁。
- 迁移单元必须是独立可切换页面或用户行为，不能默认整仓迁。
- 不新建 Vue3 骨架；落地必须复用 B 的 shell、鉴权、路由/MPA 入口、API client、状态、组件库、i18n、proxy、Node、lockfile、lint/build/test。
- JSP/Thymeleaf layout 不复制到 B；只抽取业务行为、数据契约和页面内容。
- Delivery `verified` 不等于领域迁移完成；Wave 7 领域复核通过后才能说“迁移完成候选”。
- 完成后仍不自动 archive、commit、push、PR、部署、切流、删除 fallback 或下线 A。

## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 首次使用时，在“会话通用头”填写 A、B、UNIT 三个必填值。
2. 每个 Wave 开一个全新会话，粘贴“会话通用头 + 当前 Wave 代码块”。
3. 当前 Wave 完成并停止后，再开下一个 Wave。
4. 用户只处理真正阻塞的问题、规格批准和实施批准；不需要手工维护 digest、revision、任务状态。

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

仓库获取与 revision 绑定：
- clone/fetch 命令失败不必自动终止；若目标路径已经是有效 git repo 且 HEAD 可读，可以复用该仓库继续。
- 必须记录 acquisition_status、acquisition_warning、最终 repo path、HEAD、dirty_entries、usable_for_stage。
- `sslVerify=false` 只能作为诊断警告记录，不得成为默认策略或全局持久配置。
- path 存在但不是 git repo，或 HEAD 不可读，必须停止。

Git 卫生门禁：
- A 必须保持只读；A 出现业务代码修改通常使领域证据 stale。
- B 只有 Wave 6 可出现获批范围内修改。
- `node_modules`、依赖缓存、`dist`、`build`、`target`、`coverage`、vendor、生成 bundle 不得进入 intended commit。
- `src/` clean 只说明业务源码干净，不说明整个仓库干净；必须区分 business clean 和 repo clean。
- lockfile 变化必须说明是获批依赖变更、包管理器解析漂移，还是意外安装噪声。

固定边界：
- A 始终只读。
- 只有 Wave 6（delivery-execute-verify）可修改 B 应用代码。
- Wave 1–5 与 Wave 7 对 A/B 应用代码只读。
- B shell / 鉴权 / 路由或 MPA 入口 / API client / 状态 / 组件库 / i18n / proxy / Node / lockfile / lint/build/test 全部 host-native。
- 不复制 A 的 JSP/Thymeleaf layout；不把 A 专属全局对象长期带入 B。
- 禁止新功能、无关重构、Vue2、@vue/compat、长期桥接依赖进入 B。
- 保留可演练 fallback 或灰度回退；部署、切流、A 下线、删除 fallback 不在本轮。
- 保护 A/B 已有 staged/unstaged/untracked 用户改动。

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

按 Skill 契约完成：
- host stack summary：构建、Node/Volta、lockfile、Vue、router/MPA、`scripts/getpage.js`、
  `src/pages/*/*.ts`、state、API client、UI（含 `@opentiny/vue` 等）、i18n、proxy、
  宿主侧 jQuery、测试门禁
- source page-entry inventory：JSP/Thymeleaf/HTML、ng-app/ng-controller、AngularJS controller/service/directive、jQuery entry/Ajax/DOM/plugin
- vendor/lib/locale/build 以及 openspec/reports/evidence/test/e2e 排除后的耦合计数
- A/B page comparison：unmigrated / partial-overlap / already-migrated / host-page-only / host-component / host-shell / unknown，
  并包含 match_basis、candidate_score、needs_human_correction
- URL / entry mapping：Java `@RequestMapping` / `@GetMapping` / `@PostMapping`、AngularJS
  `$routeProvider.when(...)` / ui-router `.state(...)`、模板 return / `templateUrl`、
  菜单或服务端入口 -> B 的 MPA HTML/TS、router/menu entry
- <UNIT> 的候选 source entry、真实 source URL 与 host landing point
- gaps blocking design
- 推荐首个或当前迁移单元的依据

可运行脚本生成证据基线：
python angularjs-to-vue3-host-migration/scripts/generate_migration_plan.py assess \
  --project-name "<CHANGE_ID>" \
  --source-repo "<A>" \
  --host-repo "<B>" \
  --source-acquisition-warning "<若有 clone/fetch warning 则填写，否则留空>" \
  --host-acquisition-warning "<若有 clone/fetch warning 则填写，否则留空>" \
  --output-dir "<DOMAIN_ROOT>\\assess" \
  --format all

脚本输出只是 evidence baseline；必须用代码证据复核，不得把通用表格当设计。
Repo Acquisition 与 Git Hygiene 表必须进入 assess evidence；出现 dependency/cache/build noise 时，后续不得声明 commit-ready。
A/B Page Comparison 是候选表，不是缺口真相；文件名/路径命中不能直接判 already-migrated。
`.vue` 组件不能默认当页面，根 `index.html` 只能当 host-shell；宿主业务页必须有 MPA、
router、menu 或 entry 证据。`openspec/`、报告 HTML、e2e/spec/test 文件不得进入页面清单。
`workBench`/`workbench`、`taskManage`/`taskManagement` 等别名或近似命中必须标
needs_human_correction，并由菜单、Java route 或 MPA entry 复核。

生成 assess evidence packet 或 Markdown 摘要到 <DOMAIN_ROOT>，记录 path/digest、A/B revision、
source/host page comparison、URL/entry mapping、blockers。

若 <UNIT> 缺少真实 source URL 或 B host entry 证据，输出回流字段并停止，不进入 Wave 3。
若 <UNIT> 在 A 或 B 中无法定位，输出回流字段并停止。
否则说明下一步为 Wave 3，然后停止。
```

## 4. Wave 3：AngularJS 领域 Design

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 angularjs-to-vue3-host-migration Skill，mode=design，unit=<UNIT>。
本波只做页级落地设计，不修改 A/B 应用代码。

应已存在：<CONFIG>、Wave 2 assess evidence、A/B revision、host stack、A/B page comparison。
缺失或 stale 则回 Wave 2。

读取 hosted-vue3-migration-method、jquery-vue3-business-logic-analysis、
business-logic-variable-flow-analysis。

围绕 <UNIT> 生成设计包：
- page closure：源模板/fragments/scripts/controllers/services/APIs/assets
- 同一页 AngularJS + jQuery + 服务端模板合并行为链，不拆成平行报告
- FLOW/VAR/CHAIN 只针对 <UNIT> 的核心行为，不铺全仓空表；至少填入 1～2 条核心行为链，
  不能只交表头
- host B 复用/改造/新建处置：entry/router/menu/permission/API/store/component/i18n/style/proxy
- old URL -> new host entry mapping
- permission/session/API parity requirements
- fallback/rollback switch 与 rollback condition
- implementation slices：纵向切片，不按“先类型、再接口、最后页面”横切
- verify checklist：行为、权限、URL、API、视觉、runtime、rollback
- unresolved edges 与运行时检查

设计必须证明：
- page closure 已填实，覆盖 source templates/fragments/scripts/controllers/services/APIs/assets
- 至少 1～2 条核心 FLOW 已填，material variable/API chain 已填；无法静态确认的运行时检查
  必须记录为非阻塞或阻塞项
- old URL -> new host entry mapping 有 Java route、菜单、模板 return 或 MPA entry 证据
- B 侧 entry/router/API/store/component/i18n/style 的复用/改造/新建决策明确
- permission/session/API/rollback draft 已存在
- 复用 B 的壳和鉴权
- 不复制 A 的 JSP/Thymeleaf layout
- 不引入 Vue2/@vue/compat
- 不替换 B runtime stack，除非 blocker 明确且需要用户批准

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

输出 design-ready domain evidence path/digest。
脚本生成的空合同必须标 `not-ready: empty-contract`；只有人工或后续分析把 gate 填成
evidence-backed ready，才能继续。
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
- B Node、包管理器、lockfile、scripts 来自 B 仓，不另发明命令
- 运行 git status，列出 intended files；`node_modules`、依赖缓存、dist/build/coverage/vendor 噪声一律阻塞
- `src/` 无改动不能代表 repo clean；若 repo dirty 但业务源码 clean，仍需解释每个非业务差异

严格按 tasks.md 执行：
- 适用时 RED → GREEN → REFACTOR
- 一次一个 ready task
- 只改 B 获批范围
- 验证通过后才勾选任务

发现范围/验收问题回 Wave 4；发现设计/任务/rollback 问题回 Wave 5；
发现 A baseline 或领域闭包错误回 Wave 2/3。回流使用通用头字段。

Fresh Verification Gate：
- B lint/build/test 或仓库现有等价命令
- Requirement/Scenario 对照
- 行为/权限/URL/API/错误
- rollback/fallback 演练
- OpenSpec coherence
- High 独立审查
- 若 visual=required，则生成 Delivery 自有 G9 证据；外部领域视觉证据只能作为 path/digest 引用

全部通过后写 verification.md 和 verified handoff：
overall_status=verified，archive.status=deferred_to_openspec。
不要 archive/commit/push/PR/部署/切流。
若用户额外授权 commit，提交前必须展示 intended files；依赖目录、构建产物或未解释 lockfile 变化出现时必须停止。

Delivery verified 只表示交付变更通过，不能单独宣布整次迁移完成。
结束输出：任务/修改摘要、测试构建、G9 或 manual-only 说明、独立审查、rollback、
verification、handoff path/revision。说明下一步为 Wave 7，然后停止。
```

## 8. Wave 7：AngularJS 领域 Verify

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 angularjs-to-vue3-host-migration Skill，mode=verify，unit=<UNIT>。
本波不修改 A/B 应用代码。

应已存在：Delivery verification、verified handoff、当前 B 代码、领域 assess/design evidence。
Delivery 未 verified 则回 Wave 6，不得声称迁移完成。

先校验：
- A revision 是否仍等于领域证据绑定 revision；变化则回 Wave 2
- B revision 是否等于 Delivery verified revision；变化则回 Wave 6 或重新验证
- Codebase Memory 图谱是否绑定当前 revision；stale 则重新 index_repository
- domain evidence path/digest 是否完整

按当前 revision 刷新领域复核：
- behavior parity：输入、校验、分支、成功/错误/空态/加载态
- permission parity：菜单、路由、按钮、hidden/disabled、服务端拒绝
- URL parity：旧 deep link、query/hash、redirect、back/forward、外部链接
- API parity：endpoint、method、request fields、response codes、错误消息
- visual parity：只有存在截图/测量/差异证据才能下结论；否则标 manual-only
- runtime parity：B Node、lockfile、lint/build/test
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

只有当前 revision 上 functional、permission、URL、API、runtime/build、rollback 全部通过，
且 visual 结论有测量证据或明确标为人工未证明，才能输出领域 pass / conditional pass。
领域 pass / conditional pass 仍不是完成声明；必须同时引用 Delivery verified handoff、
当前 host revision、Git Hygiene 无阻塞和无 blocking residual。

结束输出：
- final domain evidence path/digest
- functional/permission/url/api/runtime/visual/rollback 结果
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
| 页级闭包、行为链、URL/API/权限/回退设计错误 | Wave 3 Design |
| 目标、验收、范围、允许差异错误 | Wave 4 Frame |
| 技术方案、任务拆分、兼容、rollback、验证矩阵错误 | Wave 5 Plan |
| 已批准范围内的 B 实现缺陷 | Wave 6 Execute |
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
- Delivery verified、High 独立审查、必要的 G9 或 manual-only 视觉说明完成；
- AngularJS domain verify 的 behavior、permission、URL、API、runtime/build、rollback 通过；
- Repo Acquisition 可用，A/B revision 当前且 HEAD 可读；
- Git Hygiene 无阻塞；没有 dependency/cache/build 噪声进入 intended commit；
- 视觉结论有测量证据；没有测量链时明确不是 visual pass；
- fallback/rollback 已演练或清楚记录未演练 blocker；
- 无 blocking residual。

此时仍不自动 archive、commit、push、PR、部署、切流、删除 fallback 或下线 A。

## 11. 使用者与 Agent 可用性检查

### 使用者

- 三个必填值只填一次：A、B、UNIT。
- 每个 Wave 只复制通用头和一个增量提示词。
- 只处理阻塞问题、规格批准和实施批准。
- 不需要手工维护 JSON、digest、revision 或任务状态。

### AI Agent

- 每个 Wave 都有明确 Skill/mode、状态源、权限范围、输入工件、完成门禁和输出。
- 领域证据与 Delivery 生命周期不争夺状态权威。
- 只有 Wave 6 修改 B。
- revision/digest/approval 绑定防止用旧证据宣布完成。

### 可达性

在 A 可读、B 可构建、权限/测试数据可用、Codebase Memory 与 OpenSpec 可用，并且所有 Wave 门禁通过时，
这套编排可以对“旧混合页迁入现有 Vue3 宿主”给出证据化完成候选。

缺少真实权限环境、后端接口、测试数据、截图/测量链、字体/图标资源或可演练 rollback 时，必须标为 blocker
或 residual，不能用“看起来差不多”或单次代码审查代替通过结论。

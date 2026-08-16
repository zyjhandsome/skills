# Vue2 单页面迁入 Vue3 Host：用户粘贴剧本

> 这不是 Skill。不要把它当独立技能加载或改任何 Skill 的内部 schema。
>
> 用途：把一次跨仓单页迁入拆成可粘贴的会话。允许按名组合
> `migrate-vue2-pages-to-vue3-host`、`delivery-frame-spec`、
> `delivery-plan-tasks`、`delivery-execute-verify`。
>
> 禁止改 `vue-migration-domain/v1`、`delivery-handoff/v1` 或各 Skill
> 验证器字段。本剧本启用 Delivery Family 的**会话停点覆盖**：每个 Wave
> 使用全新会话，只通过磁盘工件恢复；阶段结束必须停止，不得同会话接力。

## 0. 编排结论

Claude Code 一个主会话只有一个当前模型。本文不会假设 GLM 5.2 与 Kimi K2.6
能够在同一会话中同时工作；每个 Wave 都明确选择一个模型，并在全新会话开始时
通过 `/status` 和 `/model` 校验。

```text
Wave 1  建 change（无规格闸门）
        当前模型：GLM 5.2
  → Wave 2  migrate assess
        当前模型：Kimi K2.6；包含视觉基线
  → Wave 3  migrate design
        当前模型：GLM 5.2
  → Wave 4  Frame 规格批准
        当前模型：GLM 5.2
  → Wave 5  Delivery Plan go
        当前模型：GLM 5.2
  → Wave 6  Delivery Execute
        当前模型：Kimi K2.6
  → Wave 7  migrate verify
        当前模型：GLM 5.2
```

这是一套参考分配，不是 Skill 的模型依赖：

- GLM 5.2 负责长契约阅读、结构化状态、规格、计划和最终领域核对。
- Kimi K2.6 负责需要直接图片理解的摸底，以及长程代码实施。
- Wave 7 使用 GLM 5.2 时，视觉结论必须来自当前 revision 的确定性工具证据；
  若仍需要视觉语义判断，可在 Wave 7 前另开 Kimi 只读复核会话。
- 实际 Claude Code 链路不具备相应能力时必须阻塞，不能根据模型名称假定可用。

### 0.1 Skill 职责边界

- `migrate-vue2-pages-to-vue3-host` 独立负责 A/B 事实、页面与样式闭包、运行时、
  视觉基线、迁移设计、回滚和最终领域复核；只有 assess / design / verify，
  不修改应用代码，也不调用 Delivery Family。
- Delivery Family 独立负责 OpenSpec、规格与实施批准、技术计划、B 代码修改、
  Delivery G9、独立审查和交付状态；`delivery-execute-verify` 是唯一应用代码
  mutation owner。
- 模型选择和会话切换只属于本文，不写入任何 Skill schema 或验证器。
- `delivery-explore` 不适用；主路径也不插入
  `frontend-dependency-upgrade-impact-analysis` 或
  `frontend-ui-stack-visual-parity`。

### 0.2 一波一个当前模型

| Wave | 当前 Claude Code 模型 | 选择原因 |
|---|---|---|
| 1 建 change | GLM 5.2 | 建档、派生路径和意图草稿以结构化文本为主 |
| 2 Assess | Kimi K2.6 | 需要读取 A 的多状态截图并形成可追溯视觉事实 |
| 3 Design | GLM 5.2 | 从冻结证据形成闭包、切片、fallback 与 rollback 设计 |
| 4 Frame | GLM 5.2 | 将领域事实转成 proposal/spec，并绑定规格批准 |
| 5 Plan | GLM 5.2 | 生成可追踪的 design/tasks，并绑定实施批准 |
| 6 Execute | Kimi K2.6 | 按纵向切片修改 B，并进行实现期视觉调整 |
| 7 Verify | GLM 5.2 | 与实现会话分离，核验当前 revision 上的完整证据 |

`/model` 只能切换当前 Claude Code 连接所暴露的模型。如果 GLM 与 Kimi 使用
不同 Base URL、API Key 或 provider，不能只靠 `/model` 跨供应商切换；应关闭
当前会话，使用相应 provider 配置启动新的 Claude Code 进程。不得在一个 Wave
中途覆盖环境变量或静默换模型。

### 0.3 可选的跨模型串行复核

跨模型复核不是同会话“辅助模型”，而是另开的只读 Claude Code 会话。它不加载
本 Wave 的 mutation Skill，不修改权威工件，只将结果写入：

```text
<EVIDENCE_ROOT>\model-reviews\<CHECKPOINT>\<MODEL>\
```

推荐检查点：

- Wave 6 实现后，可另开 GLM 5.2 只读会话检查 current diff、测试与任务覆盖；
- Wave 7 前，可另开全新 Kimi K2.6 只读会话检查 baseline/candidate/diff 图片。

复核结果只保存输入 path+digest、模型/接口版本、结论和 blockers，不是新的状态
源，也不能覆盖 OpenSpec、handoff、domain packet、tasks、G9 或 Skill 验证结果。
同一模型的新会话只能称为会话独立；模型判断不以投票代替测试、revision/digest、
DOM/computed-style、像素或感知差异等确定性证据。

### 0.4 执行前校准与人工职责

执行前校准不属于迁移生命周期，不新增 Wave 状态。至少验证：

1. 两个 provider 配置均可读取 A/B 和对应 Skill，且密钥不会写入仓库；
2. `/status`、`/model`、连续工具调用、JSON/schema、超时重试可以正常工作；
3. Kimi K2.6 能读取本地 baseline/candidate/diff，并输出带输入摘要的结果；
4. GLM 5.2 的视觉通道被如实记录为 direct / tool-assisted / unavailable；
5. A/B 所需 Node、包管理器、浏览器、字体、后端/Mock 和测试账号可用。

人工只负责安装依赖、启动 A/B/后端或 Mock、登录/验证码/权限、稳定测试数据、
无法自动化的业务语义判断，以及 Wave 4/Wave 5 两次批准。用户不手工搬运 JSON、
digest、revision 或任务状态。

传输、超时或 schema 错误允许原模型重试一次；连续两次失败后停止当前 Wave。
若必须更换当前模型，应废弃未完成输出，以新会话重新执行本 Wave preflight。

能力校准参考：

- GLM 5.2：<https://docs.z.ai/guides/llm/glm-5.2>
- Kimi K2.6：<https://platform.kimi.com/docs/guide/kimi-k2-6-quickstart>

## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 首次使用时，在“会话通用头”填写 A、B、PAGE、HTML 四个必填值。
2. 按第 0.2 节选择当前 Wave 的模型，启动一个全新 Claude Code 会话。
3. 先执行 `/status` 和 `/model`；provider 或模型不符时停止并重新启动。
4. 将“会话通用头 + 当前 Wave 代码块”连续粘贴为一条消息。
5. 当前 Wave 完成并停止后，按下一 Wave 标注的模型打开新会话。
6. 需要跨模型复核时另开只读会话；复核通过磁盘证据交接，不在主会话换模型。

用户只填写四个业务输入，并回答真正阻塞的问题、规格批准和实施批准。用户不
需要寻找 JSON、复制 digest、维护工件路径、转述模型结论或手工更新任务状态。

### 1.2 会话通用头——四个业务值只填一次

```text
这是一个全新独立会话，不得使用其他会话的聊天记忆补结论。

当前模型由随后粘贴的 Wave 代码块声明。执行前读取 /status 和 /model：
- 当前 provider 或模型不匹配时立即停止；
- 本 Wave 内禁止切换模型或覆盖 provider 环境变量；
- 不得假设另一个模型正在同一 Claude Code 会话中辅助执行。

用户输入：
<A> = Vue2 仓库绝对路径
<B> = Vue3 仓库绝对路径
<PAGE> = Vue2 待迁移页面的文件路径或路由
<HTML> = Vue3 入口 HTML 文件绝对路径

自动派生并保持稳定：
- <SLUG>：由 <PAGE> 规范化得到；过长时追加短 SHA-256 摘要。
- <CHANGE_ID>：migrate-<SLUG>-to-vue3。
- <CHANGE_DIR>：<B>\openspec\changes\<CHANGE_ID>。
- <EVIDENCE_ROOT>：<CHANGE_DIR>\evidence。
- <DOMAIN_ROOT>：<EVIDENCE_ROOT>\vue-cross-repo-migration。
- <G9_ROOT>：<EVIDENCE_ROOT>\delivery-visual。
- <CONFIG>：<DOMAIN_ROOT>\migration-run-config.json。

<CONFIG> 存在后，以其中记录为准；本次输入与配置不一致时停止。

正式视觉基线必须从当前运行中的 A 捕获：多状态截图、computed-style、交互和
响应式证据。不要向用户索要 A 页面参考截图，也不要把用户粘贴的图片当作视觉
事实。文本模型不得声称直接看过图片；必须使用可验证的图片读取、OCR、颜色
提取、像素/感知差异工具，或消费另一个只读视觉会话生成的 path+digest 证据。
没有这些能力时，截图只能归档和供人工查看，不能产生 visual pass。

固定边界：
- <A> 严格只读，<B> 是唯一应用代码修改目标。
- B 的导航、侧栏和布局壳保持 host-native。
- 迁入内容根节点相对 A strict parity，visual=required。
- 禁止新功能、无关重构、Vue2、@vue/compat 和 A 专属全局对象进入 B。
- 保留可实际演练的 legacy/iframe fallback。
- 保护 A/B 中已有 staged、unstaged、untracked 用户改动。
- 部署、流量切换、删除 iframe 和 A 下线不属于本轮范围。

自动恢复当前 Wave 已由上游产生且应当存在的工件，并校验路径、digest、
A/B revision、OpenSpec artifact_revision、批准绑定和用户改动碰撞。

尚未进入其生产 Wave 的工件不存在属于正常情况。已完成生产 Wave 但工件缺失、
损坏或 stale 时，停止并指出需要重跑的 Wave；不要要求用户手工提供工件内容。

会话停点覆盖：本会话只执行随后指定的一个 Wave。完成、写盘并校验后立即
停止；不要加载或执行下一个 Skill。
```

### 1.3 工件恢复矩阵

| 工件组 | Agent 用途 | 用户操作 |
|---|---|---|
| `<CONFIG>` | 定位同一 change 的业务输入和派生路径 | 不操作 |
| `<DOMAIN_ROOT>` | 保存 Domain/runtime/visual 事实、基线、设计和复核 | 最终看摘要 |
| OpenSpec 工件与 `handoff.json` | 保存规格、批准、计划、任务和交付状态 | 批准时看摘要 |
| `<G9_ROOT>` | 保存 Delivery G9 视觉验收证据 | 最终看摘要 |
| `model-reviews/` | 保存可选只读复核证据 | 不操作 |

默认不得在 `<CHANGE_DIR>` 外另建 migration-artifacts/report 目录。`evidence/`
只保存 path+digest 可校验的外部证据，不是第二状态源；OpenSpec 的 proposal、
specs、design、tasks、verification 和 handoff 仍是 Delivery 权威工件。

当前 Delivery `artifact_revision` 只覆盖权威工件及 `specs/**`。新增或更新
`evidence/` 不会使 Frame 批准失效，但修改 proposal/spec 等权威工件仍会失效。

| Wave | 应当存在的主要上游工件 |
|---|---|
| 1 建 change | 无；通过 OpenSpec 创建 change、Config 和 evidence 子目录 |
| 2 Assess | Config、change 目录；此时还没有规格批准 |
| 3 Design | Config、assess packet、runtime、visual contract、baseline |
| 4 规格批准 | Domain evidence、change 目录、意图草稿 |
| 5 Plan | 已批准 Frame 规格、domain packet path+digest、Frame handoff |
| 6 Execute | design/tasks、Plan handoff、领域基线与运行时证据 |
| 7 Verify | Delivery verification、G9、完整领域证据和当前代码 |

## 2. Wave 1：建 change（无规格闸门）

新会话粘贴“会话通用头”，再粘贴：

```text
当前 Claude Code 模型：GLM 5.2（实际 model id 以 provider 配置为准）。
先用 /status 和 /model 确认；不匹配时停止并重开会话。本 Wave 禁止切换模型。

显式使用 delivery-frame-spec Skill。
建档停点覆盖：本波只建或恢复 change，禁止规格闸门。

这是迁移类变更，固定 High、quality_profiles.visual=required。
不要使用 delivery-explore，不要进入 Plan/Execute。

硬前提是 B 的 OpenSpec 已初始化且 A/B Codebase Memory 索引可用。

通过 OpenSpec 正式创建或恢复唯一 <CHANGE_DIR>。创建：
- <DOMAIN_ROOT>；
- <G9_ROOT>；
- <CONFIG>，仅记录必填输入和派生路径，不保存批准或任务状态。

只写意图草稿：A 只读、B 单一 mutation target、B shell host-native、迁入内容 strict parity、保留 fallback、部署/切流/A 下线为非目标。
不要把尚未摸底的颜色、字体、图标或页面闭包写成已批准验收。

本波禁止规格闸门和范围批准。proposal 保持草稿。不要询问范围批准，
不要写 State Source 批准记录，不要生成进入 Plan 的 handoff transition。

结束时输出 change id/dir、Config、route/risk 草稿。说明下一步为 Wave 2，然后停止，不读取 migrate 或 Plan Skill。
```

## 3. Wave 2：迁移领域摸底

新会话粘贴“会话通用头”，再粘贴：

```text
当前 Claude Code 模型：Kimi K2.6（实际 model id 以 provider 配置为准）。
先用 /status 和 /model 确认；不匹配时停止并重开会话。本 Wave 禁止切换模型。

显式使用 migrate-vue2-pages-to-vue3-host Skill，mode=assess。

恢复 Wave 1 创建的 change 与 Config，只做只读摸底和证据采集；不要进入design/verify，不要修改 A/B 应用代码。migrate 没有 execute mode。

artifact_directory 固定为 <DOMAIN_ROOT>，不得在 <CHANGE_DIR> 外创建报告目录。

不要向用户索要 A 页面参考截图。正式视觉基线必须从当前运行中的 A 捕获。

先证明本会话存在可用的视觉处理链。纯文本模型必须通过图片读取、OCR、颜色提取、像素/感知差异工具或独立多模态模型得到可追溯结果；否则将捕获的截图仅归档，不得从像素推断页面身份、布局、颜色、字体或图标，并阻塞 strict-parity 视觉结论。

视觉处理链门禁（硬停止）：
- 无法证明可追溯图像测量时：visual_chain=unavailable，
  terminal=blocked:visual-chain。
- 截图只归档；不得写 visual pass，不得将 design 标为 ready。
- 输出 blockers 后立即停止；不得进入 Wave 3，不得加载 migrate design。
- A 仍在运行也不能放行：没有测量链就不能声称 strict parity。

若 A 无法运行或无法冻结当前 revision 的多状态基线：
terminal=blocked:visual-baseline，同样停止，不得进入 Wave 3。

按当前 Skill 契约完成：
- 解析 <PAGE> 的真实 source_entry 和 <HTML> 对应的 B 挂载链路；
- 发现页面功能闭包和完整 style_closure；
- 分析 A/B runtime、依赖、构建和 fallback；
- 在 A 仍可运行且视觉处理链可用时冻结 strict-parity 视觉契约和独立状态基线；
- 颜色使用 A 计算样式，字体与图标保留 A 的实际内容身份。

不得用单张外部截图替代当前 revision 的多状态基线。

生成并校验 assess domain packet、runtime evidence、visual contract 和 baseline
manifest，全部写入 <DOMAIN_ROOT>。视觉链不可用时仍可写评估事实，但视觉结论
必须保持 blocked。

若发现 Wave 1 意图草稿的目标或边界不成立，输出 discovery backflow 并停止；
不得自行改 OpenSpec 规格。

结束时输出 packet path/digest（若有）、A/B revision、source/host entry、
closure/runtime/baseline 状态、terminal 与 blockers。
仅当视觉处理链可用且基线已冻结、无 visual blocker 时，才说明下一步为 Wave 3。
然后停止。
```

若 A 无法运行，必须阻塞“样式不变”结论。

## 4. Wave 3：迁移领域设计

新会话粘贴“会话通用头”，再粘贴：

```text
当前 Claude Code 模型：GLM 5.2（实际 model id 以 provider 配置为准）。
先用 /status 和 /model 确认；不匹配时停止并重开会话。本 Wave 禁止切换模型。

显式使用 migrate-vue2-pages-to-vue3-host Skill，mode=design。

若当前 assess 的 terminal 为 blocked:visual-chain 或 blocked:visual-baseline，
立即停止，返回 Wave 2，不得把 design 标为 ready。

恢复当前 assess packet 和 Wave 1 意图草稿；仅在 stale 时刷新受影响事实。
不要修改 A/B 应用代码。migrate 没有 execute mode。

artifact_directory 固定为 <DOMAIN_ROOT>。

按当前 Skill 契约完成 B-native 落点、依赖 disposition、page-scoped 样式适配、
状态/路由/权限/视觉契约、纵向切片、fallback 和 rollback 设计。

design ready 必须满足：
- style_closure complete 且 unresolved 为空；
- 每项依赖、CSS/SCSS、颜色、字体和图标都有 disposition/target；
- 每个验收状态映射到纵向切片和验证行；
- fallback 可测试且没有 implementation-blocking TBD。

更新并校验 domain packet，全部领域工件保留在 <DOMAIN_ROOT>。不得生成实施授权。

若领域事实使意图草稿失效，输出 discovery backflow 并返回 Wave 1；否则输出
packet path/digest、target design、vertical slices、visual/style、rollback、
readiness 和 blockers。说明下一步为 Wave 4，然后停止。
```

## 5. Wave 4：Frame 规格批准

新会话粘贴“会话通用头”，再粘贴：

```text
当前 Claude Code 模型：GLM 5.2（实际 model id 以 provider 配置为准）。
先用 /status 和 /model 确认；不匹配时停止并重开会话。本 Wave 禁止切换模型。

显式使用 delivery-frame-spec Skill。

恢复 <CHANGE_DIR> 与 <DOMAIN_ROOT> 中的 domain packet。从 packet 摘
path+digest 写入 external_artifacts；不要要求 migrate schema 进入 Delivery
状态，也不要改 vue-migration-domain/v1。

基于当前领域事实完成 proposal.md 和增量规格，明确：
- A 只读、B 单一 mutation target；
- B shell host-native、迁入内容 strict parity；
- 功能/权限/数据/URL/错误/视觉/回滚验收；
- 颜色、字体、图标及禁止差异；
- 保留 fallback；部署、切流和 A 下线为非目标。

这是迁移类变更，固定 High、quality_profiles.visual=required。
不要使用 delivery-explore，不要进入 Plan/Execute。

按 Skill 契约完成澄清和规格闸门，只询问一次范围批准。批准必须绑定当前
artifact_revision 并写入 State Source 和 handoff.json。

handoff 的最终目标仍为 delivery-plan-tasks，但本波结束必须停止。
evidence/ 下新增 JSON、截图和摘要不得冒充 OpenSpec 权威工件。

结束时输出 change id/dir、route/risk、proposal/spec、规格闸门、
handoff path/revision。说明下一步为 Wave 5，然后停止，不读取 Plan Skill。
```

## 6. Wave 5：Delivery Plan

新会话粘贴“会话通用头”，再粘贴：

```text
当前 Claude Code 模型：GLM 5.2（实际 model id 以 provider 配置为准）。
先用 /status 和 /model 确认；不匹配时停止并重开会话。本 Wave 禁止切换模型。

显式使用 delivery-plan-tasks Skill。

只消费当前有效 Frame handoff；不要修改应用代码，不要进入 Execute。

确认规格批准有效；从 <DOMAIN_ROOT> 读取并校验 domain packet、runtime、visual
contract/baseline 的 path+digest 和 A/B revision；检查其他 active change 路径重叠。

按当前 Skill 契约写唯一权威 design.md/tasks.md、traceability、readiness、
visual validation plan、rollback 和 ownership。任务必须是可独立验证的纵向
切片，含精确路径/符号、验证命令、视觉状态、样式/颜色/字体/图标处置和回滚。

visual=required：A baseline 必须已经冻结；所有状态映射到 task；全局 CSS/reset
默认禁止；Delivery G9 的明确产物目录为 <G9_ROOT>。

运行适用的 G-check 和 readiness。存在阻塞项时不得询问实施授权；就绪后只
询问一次实施 go，并将批准绑定当前 artifact_revision 写入 handoff.json。
implementation go 必须显式携带 source_revision + host_revision、批准人、
时间、范围、验证义务与回退条件。

结束时输出 design/tasks、任务数量、readiness、visual plan、实施闸门、handoff
path/revision。说明下一步为 Wave 6，然后停止，不读取 Execute Skill。
```

## 7. Wave 6：Delivery Execute

新会话粘贴“会话通用头”，再粘贴：

```text
当前 Claude Code 模型：Kimi K2.6（实际 model id 以 provider 配置为准）。
先用 /status 和 /model 确认；不匹配时停止并重开会话。本 Wave 禁止切换模型。

显式使用 delivery-execute-verify Skill。

Delivery 是唯一代码 mutation owner；migrate 没有 execute mode，不要调用它。

Preflight 确认实施 go 绑定当前 revision、A 只读、B 用户改动受保护、任务路径
无未接受冲突、baseline/runtime evidence 有效。

严格按 tasks.md 执行：适用时 RED→GREEN→REFACTOR，一次处理一个 ready task，
只改 B 获批范围；任务验证通过后才勾选。范围问题回 Wave 4，设计/兼容/回滚/
任务问题回 Wave 5。

视觉实现遵循 domain contract：B shell 原生、内容 strict parity、page-scoped
样式、A 的计算颜色/字体/图标身份；不得用 B 全局主题或 UI 库默认差异掩盖问题。

完成后运行 Fresh Verification Gate：构建/测试、Requirement/Scenario、页面身份、
功能/权限/错误/交互、写入 <G9_ROOT> 的 Delivery G9、rollback、OpenSpec
coherence 和 High 独立审查。
领域 visual evidence 可按 G9 白名单引用
（baseline_state_ids / identity_route / identity_marker / comparison_boundary /
style_closure_status / color_metrics / typography_metrics / icon_identity /
table_metrics / rollback_fixture），但不能替代 Delivery G9。

全部通过后写 verification.md 和 verified handoff：
overall_status=verified，archive.status=deferred_to_openspec。
不 archive、commit、push、PR、部署或切流。

结束时输出任务/修改摘要、测试构建、G9、独立审查、rollback、verification 和
handoff path/revision。说明下一步为 Wave 7，然后停止。
```

Delivery `verified` 只表示交付变更通过，不能单独宣布整次迁移完成。

## 8. Wave 7：迁移领域最终复核

新会话粘贴“会话通用头”，再粘贴：

```text
当前 Claude Code 模型：GLM 5.2（实际 model id 以 provider 配置为准）。
先用 /status 和 /model 确认；不匹配时停止并重开会话。本 Wave 禁止切换模型。

显式使用 migrate-vue2-pages-to-vue3-host Skill，mode=verify。

Delivery 已拥有代码 mutation；migrate 没有 execute mode，不修改 A/B 应用代码。

针对当前 A/B revision 刷新 stale 的领域证据，不混用旧 pass。按当前 Skill
契约完整复核功能、API/权限/错误、URL/页面身份、runtime/build、style_closure、
CSS/SCSS、颜色、字体、图标、独立状态基线、computed-style 绑定、表格、fallback、
rollback 和独立审查证据。

artifact_directory 固定为 <DOMAIN_ROOT>；不得在 change 外创建最终复核报告。

更新并校验 runtime evidence、visual evidence 和 verify domain packet，运行迁移
Skill 自带的三个验证器。

只有当前 revision 上 functional、visual、runtime/build、permission、rollback
全部通过，style_closure complete 且无 blocking residual，domain verification
才能为 pass。

结束时输出最终 packet path/digest、functional/visual/runtime/rollback 结果、
blockers/residuals 和 migration_completion_candidate。

pass：说明达到本文完成条件，然后停止。
fail：不要直接改代码；输出 discovery backflow 和应返回的 Wave，然后停止。
```

## 9. 失败回流

Wave 7 失败时继续使用原 `<CHANGE_ID>`，不创建第二个 OpenSpec change。

| 发现 | 返回 |
|---|---|
| change 意图、仓库或页面输入错误 | Wave 1 建 change |
| 目标、验收、边界或允许差异错误 | Wave 4 规格批准 |
| 领域闭包、基线或迁移设计错误 | Wave 2 Assess / Wave 3 Design |
| Delivery 设计、兼容、回滚或任务拆分错误 | Wave 5 Plan |
| 已批准范围内的实现缺陷 | Wave 6 Execute |
| A/B revision 或基线 stale | 产生该证据的 Wave 2/3 |

回流必须携带：

```text
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point
```

修复后重新运行完整 Wave 6 和 Wave 7，直到 Delivery 与 Domain 同时通过。

## 10. 完成判定

只有以下全部满足，才能声称“页面升级迁移完成”：

- A 未发生应用代码修改；
- B 为 Vue3 原生实现，未引入 Vue2 或 `@vue/compat`；
- OpenSpec、批准、任务和证据均绑定当前 revision；
- Delivery verified、G9 和 High 独立审查通过；
- Domain functional、visual、runtime/build、permission 通过；
- CSS/SCSS style closure 完整，A 的颜色、字体和图标契约通过；
- 每个代表性状态有独立基线；
- fallback 可演练且 rollback tested；
- 无 blocking residual。

此时仍保留 fallback，不自动 archive、commit、push、PR、部署、切流、删除
iframe 或下线 A；这些需要后续单独授权。

## 11. 使用者与 Agent 可用性检查

### 使用者

- 四个必填值只填一次；每个 Wave 只复制通用头和一个短提示词。
- 不需要理解或操作内部工件。
- 只处理阻塞问题和两次批准（Wave 4 规格、Wave 5 实施）。
- 每个阶段都有明确产物、停止点和下一步，可在中断后恢复。

### AI Agent

- 每个 Wave 都明确 Skill/mode、状态源、权限范围、输入工件、完成门禁和输出。
- 按阶段工件矩阵区分“尚未产生”与“应有但缺失”，避免误阻塞或误放行。
- 迁移证据与 Delivery 生命周期不争夺状态权威；只有 Wave 6 修改应用代码。
- revision/digest/approval 绑定和最终双重验证防止用旧证据宣布完成。
- 可以按名调用上述四个 Skill；不得改它们的 schema 或验证器。

### 可达性

在 A 可验证、B 可构建、关键数据/权限环境可访问，并且七个 Wave 的硬门全部
通过时，这套编排可以对“功能不变、迁入内容样式不变”给出证据化结论。

缺少真实 A 基线、确定性数据、权限环境、字体或原始图标时必须明确阻塞，不能
用代码审查、单张截图、功能 E2E 或“看起来相似”代替严格迁移结论。

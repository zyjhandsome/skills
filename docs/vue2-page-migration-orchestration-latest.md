# Vue2 单页面迁入 Vue3 Host：完整精简编排

> 将 Vue2 仓库的一个页面原生迁入 Vue3 Host：Vue3 外壳保持原生，迁入
> 内容区域保持功能和样式不变。
>
> 只使用：`migrate-vue2-pages-to-vue3-host`、`delivery-frame-spec`、
> `delivery-plan-tasks`、`delivery-execute-verify`。
>
> 每个 Wave 使用全新会话，只通过磁盘工件恢复；不在同一会话自动接力。

## 0. 编排结论

```text
Wave 1  Delivery Frame
  → Wave 2  migrate assess
  → Wave 3  migrate design
  → Wave 4  Delivery Plan
  → Wave 5  Delivery Execute
  → Wave 6  migrate verify
```

职责边界：

- 迁移 Skill：A/B 事实、页面闭包、运行时与依赖、CSS/SCSS、颜色、字体、
  图标、视觉基线、迁移设计、回滚和最终领域复核。
- Delivery Family：OpenSpec、范围批准、技术计划、实施批准、B 代码修改、
  Delivery G9、独立审查和交付状态。
- `delivery-explore` 不适用，因为迁移目标已经确定。
- 不再插入独立依赖分析或视觉修复 Skill，避免重复状态源和重复验证责任。

## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 在下面的“会话通用头”填写四个必填值；有 A 页面截图时再填写可选项。
2. 每个 Wave 开一个全新会话。
3. 每次将“会话通用头 + 当前 Wave 代码块”连续粘贴为一条消息。
4. 当前 Wave 完成后，根据输出打开下一个会话。

用户只需要填写四个必填值，可选提供一个截图文件或目录，并回答真正阻塞的
问题、规格批准和实施批准。
用户不需要寻找 JSON、复制 digest、维护工件路径或手工更新任务状态。

### 1.2 会话通用头——必填值只填一次，截图按需提供

```text
这是一个全新独立会话，不得使用其他会话的聊天记忆补结论。

用户输入：
<A> = Vue2 仓库绝对路径
<B> = Vue3 仓库绝对路径
<PAGE> = Vue2 待迁移页面的文件路径或路由
<HTML> = Vue3 入口 HTML 文件绝对路径
<A_PAGE_REF> = 可选；A 页面 PNG/JPEG/WebP 截图文件或截图目录；没有则留空

自动派生并保持稳定：
- <SLUG>：由 <PAGE> 规范化得到；过长时追加短 SHA-256 摘要。
- <CHANGE_ID>：migrate-<SLUG>-to-vue3。
- <CHANGE_DIR>：<B>\openspec\changes\<CHANGE_ID>。
- <EVIDENCE_ROOT>：<CHANGE_DIR>\evidence。
- <DOMAIN_ROOT>：<EVIDENCE_ROOT>\vue-cross-repo-migration。
- <A_PAGE_REF_ROOT>：<DOMAIN_ROOT>\input-reference。
- <G9_ROOT>：<EVIDENCE_ROOT>\delivery-visual。
- <CONFIG>：<DOMAIN_ROOT>\migration-run-config.json。

<CONFIG> 存在后，以其中记录为准；本次输入与配置不一致时停止。

<A_PAGE_REF> 为空不阻塞；优先从当前运行中的 A 捕获正式视觉基线。非空时验证
路径和图片类型，计算 digest，并在 Wave 2 复制到 <A_PAGE_REF_ROOT>。WebP 保留
原文件并另建无损编码的 PNG 工作副本，不得覆盖原件；转换不能恢复源文件已经
损失的细节。两者都记录 path+digest，源 WebP 标为 lossy/lossless/unknown。
它仅用于确认页面身份、布局、颜色、字体、图标和应覆盖的
状态，不替代当前 revision 的多状态基线、computed-style、交互或响应式证据。

若当前模型只支持文本输入（例如 GLM-5.2），不得声称模型直接看过图片。必须由
可验证的图片读取、OCR、颜色提取、像素/感知差异工具，或独立多模态模型生成
可追溯的分析证据；没有这些能力时，参考图只能归档和供人工查看，不能产生视觉
事实。若参考图与当前 A 冲突，停止并报告页面身份或版本不一致。A 无法运行时，
单张参考图不足以支持 strict parity 结论。

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

尚未进入其生产 Wave 的工件不存在属于正常情况；已完成生产 Wave但工件
缺失、损坏或 stale 时，停止并指出需要重跑的 Wave。不要要求用户手工提供
工件路径、digest 或 JSON 内容。

本会话只执行随后指定的一个 Wave。完成、写盘并校验后立即停止；不要加载
或执行下一个 Skill。
```

### 1.3 工件是给 Agent 用的

| 工件组 | Agent 用途 | 用户操作 |
|---|---|---|
| `<CONFIG>` | 在同一 change 中定位迁移任务及派生路径 | 不操作 |
| `<DOMAIN_ROOT>` | 保存 Domain/runtime/visual 事实、基线、设计和复核 | 最终看摘要 |
| `<A_PAGE_REF_ROOT>` | 保存可选参考截图、来源路径和 digest | 不操作 |
| OpenSpec 工件与 `handoff.json` | 保存 Delivery 规格、批准、计划、任务和状态 | 批准时看摘要 |
| `<G9_ROOT>` | 保存 Delivery 自己的 G9 视觉验收证据 | 最终看摘要 |

默认不得在 `<CHANGE_DIR>` 外另建 migration-artifacts/report 目录。`evidence/`
只保存 path+digest 可校验的外部证据，不是第二状态源；OpenSpec 的 proposal、
specs、design、tasks、verification 和 handoff 仍是 Delivery 权威工件。
当前 Delivery `artifact_revision` 只覆盖这些权威工件及 `specs/**`；新增或更新
`evidence/` 不会使 Frame 批准失效，但修改 proposal/spec 等权威工件仍会失效。

按阶段恢复：

| Wave | 应当存在的主要上游工件 |
|---|---|
| 1 Frame | 无；通过 OpenSpec 创建 change、Config 和 evidence 子目录 |
| 2 Assess | Config、已批准 Frame 规格、change 目录和可选 A 页面参考图 |
| 3 Design | Config、assess packet、runtime、visual contract、baseline |
| 4 Plan | Domain evidence、proposal/spec、Frame handoff |
| 5 Execute | design/tasks、Plan handoff、领域基线与运行时证据 |
| 6 Verify | Delivery verification、G9、完整领域证据和当前代码 |

## 2. Wave 1：Delivery Frame

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-frame-spec Skill。

这是迁移类变更，固定 High、quality_profiles.visual=required。
不要使用 delivery-explore，不要进入 Plan/Execute。

硬前提是 B 的 OpenSpec 已初始化且 A/B Codebase Memory 索引可用。

通过 OpenSpec 正式创建或恢复唯一 <CHANGE_DIR>。创建：
- <DOMAIN_ROOT>；
- <G9_ROOT>；
- <CONFIG>，仅记录必填输入、可选 <A_PAGE_REF> 和派生路径，不保存批准或任务状态。

基于当前代码事实完成 proposal.md 和增量规格，明确：
- A 只读、B 单一 mutation target；
- B shell host-native、迁入内容 strict parity；
- 功能/权限/数据/URL/错误/视觉/回滚验收；
- 颜色、字体、图标及禁止差异；
- 保留 fallback；部署、切流和 A 下线为非目标。

按 Skill 契约完成澄清和规格闸门，只询问一次范围批准。批准必须绑定当前
artifact_revision 并写入 State Source 和 handoff.json。

handoff 的最终目标仍为 delivery-plan-tasks，但在进入 Plan 前，本文编排要求
先完成 Wave 2/3 的迁移领域证据。evidence/ 下新增 JSON、截图和摘要不得冒充
OpenSpec 权威工件。

结束时输出 change id/dir、Config、route/risk、proposal/spec、规格闸门、
handoff path/revision。说明下一步为 Wave 2，然后停止，不读取 Plan Skill。
```

## 3. Wave 2：迁移领域摸底

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 migrate-vue2-pages-to-vue3-host Skill，mode=assess。

恢复已批准 Frame 范围，只做只读摸底和证据采集；不要进入 design/execute，
不要修改 A/B 应用代码。

artifact_directory 固定为 <DOMAIN_ROOT>，不得在 <CHANGE_DIR> 外创建报告目录。

若 <A_PAGE_REF> 非空：验证文件或目录存在，只接收 PNG/JPG/JPEG/WebP；复制到
<A_PAGE_REF_ROOT> 并记录原路径、文件 digest 和用途。WebP 原样保留，同时生成
无损编码的 PNG 工作副本，记录转换工具/命令、原件与派生件 digest，并把源件
标为 lossy/lossless/unknown；不得声称转换恢复了源件细节，也不得用转换件冒充
原始证据。目录中的截图建议按 loaded/loading/empty/editing/error/narrow 等
状态命名。

先证明本会话存在可用的视觉处理链。纯文本模型必须通过图片读取、OCR、颜色
提取、像素/感知差异工具或独立多模态模型得到可追溯结果；否则仅归档参考图，
并将 reference_semantic_analysis 标为 unavailable，不得推断页面身份、布局、
颜色、字体或图标。即使可分析，也不得把参考图当作完整视觉基线。

按当前 Skill 契约完成：
- 解析 <PAGE> 的真实 source_entry 和 <HTML> 对应的 B 挂载链路；
- 发现页面功能闭包和完整 style_closure；
- 分析 A/B runtime、依赖、构建和 fallback；
- 在 A 仍可运行时冻结 strict-parity 视觉契约和独立状态基线；
- 颜色使用 A 计算样式，字体与图标保留 A 的实际内容身份。

若参考截图与当前 A 的页面身份或视觉事实冲突，停止并报告版本/页面不一致，
不得自行选择一方。若 A 无法运行，参考截图只能作为替代参考；单张图不能支持
严格视觉等价声明，除非规格明确降级并重新批准。

生成并校验 assess domain packet、runtime evidence、visual contract 和 baseline
manifest，全部写入 <DOMAIN_ROOT>。

若发现 Frame 的目标、验收或风险边界不成立，输出 discovery backflow 并停止；
不得自行改 OpenSpec 规格。

结束时输出 packet path/digest、A/B revision、source/host entry、参考图处置、
closure/runtime/baseline 状态和 blockers。说明下一步为 Wave 3，然后停止。
```

若 A 无法运行且没有可信截图、设计稿或获批替代基线，必须阻塞“样式不变”
结论。

## 4. Wave 3：迁移领域设计

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 migrate-vue2-pages-to-vue3-host Skill，mode=design。

恢复当前 assess packet 和已批准 Frame 范围；仅在 stale 时刷新受影响事实。
不要修改 A/B 应用代码，不要进入 execute。

artifact_directory 固定为 <DOMAIN_ROOT>。

按当前 Skill 契约完成 B-native 落点、依赖 disposition、page-scoped 样式适配、
状态/路由/权限/视觉契约、纵向切片、fallback 和 rollback 设计。

design ready 必须满足：
- style_closure complete 且 unresolved 为空；
- 每项依赖、CSS/SCSS、颜色、字体和图标都有 disposition/target；
- 每个验收状态映射到纵向切片和验证行；
- fallback 可测试且没有 implementation-blocking TBD。

更新并校验 domain packet，全部领域工件保留在 <DOMAIN_ROOT>。不得生成实施授权。

若领域事实使 Frame 规格失效，输出 discovery backflow 并返回 Wave 1；否则输出
packet path/digest、target design、vertical slices、visual/style、rollback、
readiness 和 blockers。说明下一步为 Wave 4，然后停止。
```

## 5. Wave 4：Delivery Plan

新会话粘贴“会话通用头”，再粘贴：

```text
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

结束时输出 design/tasks、任务数量、readiness、visual plan、实施闸门、handoff
path/revision。说明下一步为 Wave 5，然后停止，不读取 Execute Skill。
```

## 6. Wave 5：Delivery Execute

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 delivery-execute-verify Skill。

Delivery 是唯一代码 mutation owner；不要调用迁移 Skill 的 execute mode。

Preflight 确认实施 go 绑定当前 revision、A 只读、B 用户改动受保护、任务路径
无未接受冲突、baseline/runtime evidence 有效。

严格按 tasks.md 执行：适用时 RED→GREEN→REFACTOR，一次处理一个 ready task，
只改 B 获批范围；任务验证通过后才勾选。范围问题回 Frame，设计/兼容/回滚/
任务问题回 Plan。

视觉实现遵循 domain contract：B shell 原生、内容 strict parity、page-scoped
样式、A 的计算颜色/字体/图标身份；不得用 B 全局主题或 UI 库默认差异掩盖问题。

完成后运行 Fresh Verification Gate：构建/测试、Requirement/Scenario、页面身份、
功能/权限/错误/交互、写入 <G9_ROOT> 的 Delivery G9、rollback、OpenSpec
coherence 和 High 独立审查。
领域 visual evidence 可引用，但不能替代 Delivery G9。

全部通过后写 verification.md 和 verified handoff：
overall_status=verified，archive.status=deferred_to_openspec。
不 archive、commit、push、PR、部署或切流。

结束时输出任务/修改摘要、测试构建、G9、独立审查、rollback、verification 和
handoff path/revision。说明下一步为 Wave 6，然后停止。
```

Delivery `verified` 只表示交付变更通过，不能单独宣布整次迁移完成。

## 7. Wave 6：迁移领域最终复核

新会话粘贴“会话通用头”，再粘贴：

```text
显式使用 migrate-vue2-pages-to-vue3-host Skill，mode=verify。

Delivery 已拥有代码 mutation；禁止进入 migrate execute，不修改 A/B 应用代码。

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

## 8. 失败回流

Wave 6 失败时继续使用原 `<CHANGE_ID>`，不创建第二个 OpenSpec change。

| 发现 | 返回 |
|---|---|
| 目标、验收、边界或允许差异错误 | Wave 1 Frame |
| 领域闭包、基线或迁移设计错误 | Wave 2 Assess / Wave 3 Design |
| Delivery 设计、兼容、回滚或任务拆分错误 | Wave 4 Plan |
| 已批准范围内的实现缺陷 | Wave 5 Execute |
| A/B revision 或基线 stale | 产生该证据的 Wave 2/3 |

回流必须携带：

```text
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point
```

修复后重新运行完整 Wave 5 和 Wave 6，直到 Delivery 与 Domain 同时通过。

## 9. 完成判定

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

## 10. 使用者与 Agent 可用性检查

### 使用者

- 四个必填值只填一次；`<A_PAGE_REF>` 可选；每个 Wave 只复制通用头和一个短提示词。
- 不需要理解或操作内部工件。
- 只处理阻塞问题和两次批准。
- 每个阶段都有明确产物、停止点和下一步，可在中断后恢复。

### AI Agent

- 每个 Wave 都明确 Skill/mode、状态源、权限范围、输入工件、完成门禁和输出。
- 按阶段工件矩阵区分“尚未产生”与“应有但缺失”，避免误阻塞或误放行。
- 迁移证据与 Delivery 生命周期不争夺状态权威；只有 Wave 5 修改应用代码。
- revision/digest/approval 绑定和最终双重验证防止用旧证据宣布完成。

### 可达性

在 A 可验证、B 可构建、关键数据/权限环境可访问，并且六个 Wave 的硬门全部
通过时，这套编排可以对“功能不变、迁入内容样式不变”给出证据化结论。

缺少真实 A 基线、确定性数据、权限环境、字体或原始图标时必须明确阻塞，不能
用代码审查、单张截图、功能 E2E 或“看起来相似”代替严格迁移结论。

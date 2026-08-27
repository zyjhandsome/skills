# Vue2 单页面迁入 Vue3 Host：用户粘贴剧本

> 这不是 Skill。不要把它当独立技能加载或改任何 Skill 的内部 schema。
>
> 用途：把一次跨仓单页迁入拆成可粘贴的会话。允许按名组合
> `vue2-pages-to-vue3-host-migration`、`delivery-frame-spec`、
> `delivery-plan-tasks`、`delivery-execute-verify`。
>
> 禁止改 `vue-migration-domain/v1`、`delivery-handoff/v1` 或各 Skill
> 验证器字段。本剧本启用 Delivery Family 的**会话停点覆盖**：每个 Wave
> 使用全新会话，只通过磁盘工件恢复；阶段结束必须停止，不得同会话接力。

## 0. 编排结论

Claude Code 一个主会话只有一个当前模型。每个 Wave 选一个模型，并在全新会话
开始时通过 `/status` 和 `/model` 校验。除 Wave 2 外默认 GLM 5.2；Kimi K2.6
只承担需要直接读图的摸底（及可选视觉复核），避免长程会话超限。

```text
Wave 1  建 change（无规格闸门）     GLM 5.2
  → Wave 2  migrate assess         Kimi K2.6；包含视觉基线
  → Wave 3  migrate design         GLM 5.2
  → Wave 4  Frame 规格批准         GLM 5.2
  → Wave 5  Delivery Plan go       GLM 5.2
  → Wave 6  Delivery Execute       GLM 5.2
  → Wave 7  migrate verify         GLM 5.2
```

这是一套参考分配，不是 Skill 的模型依赖：

- GLM 5.2：长契约、结构化状态、规格、计划、代码实施、最终领域核对。
- Kimi K2.6：仅 Wave 2 直接图片理解摸底；长程实施不用 Kimi。
- Wave 6/7 的视觉结论必须来自 Wave 2 冻结契约 + 当前 revision 的确定性工具
  证据；若仍需视觉语义判断，在 Wave 6 后 / Wave 7 前另开 Kimi 只读复核。
- 实际链路不具备相应能力时必须阻塞，不能根据模型名称假定可用。

### 0.1 Skill 职责边界

- `vue2-pages-to-vue3-host-migration` 独立负责 A/B 事实、页面与样式闭包、运行时、
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
| 6 Execute | GLM 5.2 | 按纵向切片改 B；实施以任务与确定性验证为主，避免长会话超限 |
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

推荐检查点：Wave 6 完成后、Wave 7 开始前，另开 Kimi K2.6 只读会话检查
baseline / candidate / diff 图片。Wave 6 已是 GLM，不必再为同一 diff 另开
GLM 复核。

复核结果只保存输入 path+digest、模型/接口版本、结论和 blockers，不是新的状态
源，也不能覆盖 OpenSpec、handoff、domain packet、tasks、G9 或 Skill 验证结果。
同一模型的新会话只能称为会话独立；模型判断不以投票代替测试、revision/digest、
DOM/computed-style、像素或感知差异等确定性证据。

### 0.4 执行前校准与人工职责

执行前校准不属于迁移生命周期，不新增 Wave 状态。至少验证：

1. 两个 provider 配置均可读取 A/B 和对应 Skill，且密钥不会写入仓库；
2. `/status`、`/model`、连续工具调用、JSON/schema、超时重试可以正常工作；
3. Kimi K2.6 能读取本地 baseline/candidate/diff，并输出带输入摘要的结果
   （Wave 2 与可选视觉复核依赖此能力）；
4. GLM 5.2 的视觉通道被如实记录为 direct / tool-assisted / unavailable；
5. A/B 所需 Node、包管理器、浏览器、字体、后端/Mock 和测试账号可用。

人工只负责安装依赖、启动 A/B/后端或 Mock、登录/验证码/权限、稳定测试数据、
无法自动化的业务语义判断、可选提供 A 的多状态截图，以及 Wave 4/Wave 5 两次
批准。用户截图不替代代码检索，也不手工搬运 JSON、digest、revision 或任务状态。

传输、超时或 schema 错误允许原模型重试一次；连续两次失败后停止当前 Wave。
若必须更换当前模型，应废弃未完成输出，以新会话重新执行本 Wave preflight。

能力校准参考：

- GLM 5.2：<https://docs.z.ai/guides/llm/glm-5.2>
- Kimi K2.6：<https://platform.kimi.com/docs/guide/kimi-k2-6-quickstart>

## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 首次使用时，在“会话通用头”填写 A、B、PAGE、HTML 四个必填值。
2. 按第 0.2 节选择当前 Wave 的模型，启动一个全新 Claude Code 会话。
3. 用户先执行 `/status` 和 `/model`；provider 或模型不符时停止并重新启动。
4. 将“会话通用头 + 当前 Wave 代码块”连续粘贴为一条消息。Wave 块只含本波
   Skill、应已存在的上游工件、增量门禁和结束产物，不要把通用头内容再贴一遍。
5. 当前 Wave 完成并停止后，按下一 Wave 标注的模型打开新会话。
6. 需要跨模型复核时另开只读会话；复核通过磁盘证据交接，不在主会话换模型。

用户只填写四个业务输入，并回答真正阻塞的问题、规格批准和实施批准。可额外
提供当前 revision 运行中 A 的多状态截图（粘贴或本地路径）；不需要寻找 JSON、
复制 digest、维护工件路径、转述模型结论或手工更新任务状态。

### 1.2 会话通用头——四个业务值只填一次

```text
这是一个全新独立会话，不得使用其他会话的聊天记忆补结论。

当前模型由随后粘贴的 Wave 代码块声明（expected_model）。用户已在粘贴前执行
/status 和 /model；Agent 不得声称执行过 slash command，也不得在本 Wave 内换
模型、覆盖 provider 环境变量，或假设另一模型同会话辅助。Wave 粘贴块只补充
本波 Skill、应已存在的上游工件、增量门禁和结束产物；通用头已覆盖的检索、
边界、视觉协议、回流字段、完成判定和停点不要复述。

用户输入：
<A> = Vue2 仓库绝对路径
<B> = Vue3 仓库绝对路径
<PAGE> = Vue2 待迁移页面的文件路径或路由
<HTML> = Vue3 入口 HTML 文件绝对路径

自动派生并保持稳定：
- <SLUG>：由 <PAGE> 规范化；过长时追加短 SHA-256。
- <CHANGE_ID>：migrate-<SLUG>-to-vue3
- <CHANGE_DIR>：openspec\changes\<CHANGE_ID>
- <EVIDENCE_ROOT>：<CHANGE_DIR>\evidence
- <DOMAIN_ROOT>：<EVIDENCE_ROOT>\vue-cross-repo-migration
- <G9_ROOT>：<EVIDENCE_ROOT>\delivery-visual
- <CONFIG>：<DOMAIN_ROOT>\migration-run-config.json
- <INDEX_MANIFEST>：<DOMAIN_ROOT>\codebase-index-manifest.json
- <RUNTIME_MANIFEST>：<DOMAIN_ROOT>\runtime-service-manifest.json

<CONFIG> 存在后以其记录为准；与本次输入不一致时停止。

代码检索默认 Codebase Memory MCP：search_graph → trace_path → get_code_snippet
→ query_graph / get_architecture；search_code 查模板、导入和字符串。仅非代码
事实，或 MCP 为空/不完整/语法不支持时，才降级文件读取或 rg，并记录 query、
不足点和 fallback 原因。不得因图谱没有 Route 节点断言路由不存在。

<INDEX_MANIFEST> 记录 A/B graph project、repo path、revision、index mode、
indexed_at。图谱 revision 与仓库不一致视为 stale；stale 图谱不能证明闭包完整，
也不能用于最终 pass。

正式视觉基线的图像须来自当前 revision 运行中的 A：Agent 捕获，或用户提供的
多状态截图（粘贴或本地路径）。Agent 捕获困难或失败时可以请用户补充；不得使用
设计稿、过期环境或无关页面图。A 可运行时仍采集 computed-style、交互和响应式；
用户截图只补图像，不替代这些测量。无论图像来源，必须同时检索 A 的代码（图谱、
模板、样式闭包、token、字体/图标资源、class 绑定）；不得因已有截图跳过检索。
截图与代码矛盾时，以代码事实为准，截图只作外观线索并记录冲突。文本模型不得
声称直接看过图片；必须使用可验证读图/OCR/颜色/像素或感知差异工具，或消费只
读视觉会话的 path+digest。没有这些能力时，截图只归档供人看，不能产生 visual
pass。

固定边界：A 始终只读。仅 Wave 6（delivery-execute-verify）可修改 B 的应用代码；
Wave 1–5 与 Wave 7 对 A/B 应用代码只读。B 导航/侧栏/布局壳 host-native；
迁入内容根相对 A strict parity，visual=required；禁止新功能、无关重构、Vue2、
@vue/compat、A 专属全局对象进入 B；保留可演练的 legacy/iframe fallback；保护
A/B 已有 staged/unstaged/untracked 用户改动；部署、切流、删 iframe、A 下线不
在本轮。

自动恢复以随后 Wave 块「应已存在」行为准，校验 path、digest、A/B revision、
OpenSpec artifact_revision、批准绑定和用户改动碰撞。尚未进入生产 Wave 的工件
缺失为正常；已完成 Wave 的工件缺失/损坏/stale 则停止并指出重跑 Wave，不要求
用户手工提供内容。

失败回流最小字段：
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point

页面升级迁移完成（仅 Wave 7 在 Delivery+Domain 双通过后才能声称）须同时：
A 无应用代码修改；B 无 Vue2/@vue/compat；OpenSpec/批准/任务/证据绑定当前
revision；A/B 图谱或 fallback 绑定当前 revision；Delivery verified、G9、High
独立审查通过；Domain functional/visual/runtime/build/permission 通过；
style_closure complete；每状态独立基线；fallback 可演练且 rollback tested；
runtime（Node/包管理器/lock digest/PID/端口/日志/healthcheck）可追溯；
无 blocking residual。仍不 archive/commit/push/PR/部署/切流。

会话停点覆盖：只执行随后指定的一个 Wave。完成、写盘、校验后立即停止；不要
加载或执行下一个 Skill。
```

### 1.3 工件恢复矩阵

| 工件组 | Agent 用途 | 用户操作 |
|---|---|---|
| `<CONFIG>` | 定位同一 change 的业务输入和派生路径 | 不操作 |
| `<DOMAIN_ROOT>` | 保存 Domain/runtime/visual 事实、基线、设计和复核 | 最终看摘要 |
| `<INDEX_MANIFEST>` | 绑定 Codebase Memory project、revision 和索引时间 | 不操作 |
| `<RUNTIME_MANIFEST>` | 保存 Node、安装、服务、端口、PID 和日志 | 不操作 |
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
| 4 规格批准 | design-ready domain packet、change 目录、意图草稿 |
| 5 Plan | 已批准 Frame 规格、domain packet path+digest、Frame handoff |
| 6 Execute | design/tasks、Plan handoff、领域基线与运行时证据 |
| 7 Verify | Delivery verification、G9、完整领域证据和当前代码 |

### 1.4 Node、依赖与服务生命周期

先读取各仓库的 `.nvmrc`、`.node-version`、`package.json#engines`、
`packageManager`、锁文件和 `scripts`，再确定命令。不得默认两个仓库使用同一
Node、同一包管理器或存在 `serve` script。

| 阶段 | A（Vue2） | B（Vue3 Host） |
|---|---|---|
| 执行前校准 | 准备兼容 Node；不安装项目依赖 | 准备兼容 Node 与仓库声明的包管理器 |
| Wave 1 | 不安装、不启动 | 不安装、不启动 |
| Wave 2 | 在当前 revision 的一次性副本安装依赖并启动，捕获正式基线 | 在一次性副本验证 frozen install、build/dev 和 host 入口 |
| Wave 3–5 | 默认不重装、不重启；只消费已冻结证据 | 默认不重装、不重启 |
| Wave 6 | 严格只读；仅 baseline stale 才返回 Wave 2 | 在获批 B 中安装/刷新依赖，启动开发服务，执行 build/test/G9 |
| Wave 7 | 默认消费冻结基线；A revision 变化则返回 Wave 2 | 按当前 revision 启动干净服务并重新验证；lock 未变化不重复安装 |

正式 A 不得直接执行可能改写 lockfile 的安装。优先在一次性副本使用 frozen
install；失败后只有在副本中才可运行非 frozen install，并记录 lockfile diff 和
失败原因。副本生成的依赖解析不能冒充原仓库锁文件事实。

每次安装或启动都更新 `<RUNTIME_MANIFEST>`：

```text
repository / revision / runtime_copy / node_version /
package_manager / package_manager_version / lock_digest /
install_command / start_command / port / pid / started_at /
log_path / healthcheck_url / stop_command / status
```

服务由启动它的 Wave 负责健康检查、日志和停止/保留决定。A/B 需要不同 Node 时，
使用独立终端、独立进程或按项目固定版本的运行器；不得在同一服务进程依赖的
环境中反复全局切换 Node。

参考项目的仓库原生命令：

```text
A Vue2_Test：npm；start script 是 npm run dev，不是 npm run serve。
B Vue3_Test：Node ^20.19.0 或 >=22.12.0；pnpm@11.16.0；
             pnpm install --frozen-lockfile；pnpm dev；pnpm build。
             preinstall 强制 pnpm，禁止 npm install 和 npm run serve。
```

用户已经授权 Agent 在任务范围内安装依赖、启动服务和截图，默认无需人工代跑。
用户提供的运行中 A 截图是合法图像来源，但不能代替代码检索或覆盖代码事实。
只有系统级 Node/包管理器安装需要管理员权限、Windows 防火墙、私有 registry、
VPN/代理/证书、SSO/验证码、测试权限或安装将修改正式 lockfile 时才请求人工。

## 2. Wave 1：建 change（无规格闸门）

新会话粘贴“会话通用头”，再粘贴：

```text
expected_model=GLM 5.2（实际 model id 以 provider 配置为准）。

显式使用 delivery-frame-spec Skill。建档停点覆盖：只建或恢复 change。本波禁止规格闸门。迁移类变更：固定 High、quality_profiles.visual=required。不要
delivery-explore，不要 Plan/Execute。本波不得修改 A/B 应用代码。

应已存在：无上游 change。本波创建 Config 与 evidence 目录。
硬前提：B 的 OpenSpec 可写。openspec: cli-only 时按 Frame Skill 固定三行报告
（缺什么 / 能否降级：否 / 下一步请你）并询问
initialize_repo，不得发明平行 Markdown 状态。读取 A/B 当前 revision；验证
Codebase Memory 已有 project。索引缺失时先 index_repository，再用
get_architecture 证明可查询。图谱为空 ≠ 仓库无代码。校验 <PAGE>/<HTML> 在
A/B 中可定位；不能定位则停止。

正式创建或恢复唯一 <CHANGE_DIR>，并创建 <DOMAIN_ROOT>、<G9_ROOT>、<CONFIG>
（只记必填输入和派生路径）、<INDEX_MANIFEST>、<RUNTIME_MANIFEST> 初始结构。
本波不得安装依赖或启动 A/B。

只写意图草稿：A 只读、仅后续 Wave 6 改 B、B shell host-native、迁入内容
strict parity、保留 fallback、部署/切流/A 下线为非目标。不要把尚未摸底的颜色、
字体、图标或页面闭包写成已批准验收。

proposal 保持草稿。不要询问范围批准，不要写 State Source 批准，不要生成进入
Plan 的 handoff transition。

结束输出：change id/dir、Config、Index Manifest、A/B revision、route/risk 草稿。
说明下一步为 Wave 2，然后停止；不读取 migrate 或 Plan Skill。
```

## 3. Wave 2：迁移领域摸底

新会话粘贴“会话通用头”，再粘贴：

```text
expected_model=Kimi K2.6（实际 model id 以 provider 配置为准）。

显式使用 vue2-pages-to-vue3-host-migration Skill，mode=assess。
只做只读摸底和证据采集；不要进入 design/verify；migrate 没有 execute mode。

应已存在：<CONFIG>、<CHANGE_DIR>。缺失则回 Wave 1。尚无规格批准为正常。
INDEX_MANIFEST 的 A/B revision 必须等于当前 revision；缺失或 stale 时重新
index_repository。artifact_directory 固定为 <DOMAIN_ROOT>。

在当前 revision 一次性副本安装并启动：先读各仓 .nvmrc/.node-version/engines/
packageManager/锁文件/scripts，不得默认同一 Node 或存在 serve script。A 冻结
正式基线：图像来自运行中捕获或用户提供的多状态截图，样式/结构仍须检索 A 代码；
截图与代码矛盾以代码为准。B 验证 frozen install、build/dev 和 host 入口。禁止
改写正式 A 的 lockfile。A/B 不同 Node 时用独立进程。写 <RUNTIME_MANIFEST>。
管理员权限、私服/VPN/证书或登录验证才请求人工。

视觉处理链门禁（硬停止；视觉事实协议见通用头）：
- 先证明本会话可追溯图像测量（读图 / OCR / 颜色 / 像素或感知差异，或独立多模态）。
- 失败：visual_chain=unavailable，terminal=blocked:visual-chain；截图只归档；
  不得 visual pass、不得 design ready、不得进入 Wave 3。
- 无法冻结多状态基线（Agent 未能从运行中 A 捕获所需状态，且用户未提供覆盖这些
  状态、来自当前 revision 运行中 A 的截图）：terminal=blocked:visual-baseline，
  同样停止。
A 仍在运行也不能放行：没有测量链就不能声称 strict parity。用户截图不能跳过
代码检索，也不能覆盖与代码矛盾的颜色/字体/图标/结构。

按 Skill 契约完成 source_entry / B 挂载链路、功能闭包、style_closure、
runtime/依赖/fallback，以及（链可用时）strict-parity 视觉契约和独立状态基线。
颜色以 A 代码与（可得时）计算样式为准；字体与图标保留 A 内容身份。用户截图
不得覆盖这些代码事实。

生成并校验 assess packet、runtime、visual contract、baseline 到 <DOMAIN_ROOT>。
链不可用仍可写评估事实，视觉结论保持 blocked。意图草稿不成立则按通用头回流
字段停止；不得改 OpenSpec 规格。

结束输出：packet path/digest、A/B revision、Index/Runtime Manifest、
source/host entry、closure/runtime/baseline、terminal、blockers。
仅当视觉处理链可用且基线已冻结、无 visual blocker 时，才说明下一步为 Wave 3。
然后停止。
```

若未能从运行中 A 得到覆盖所需状态的图像，且用户也未提供当前 revision 运行中
A 的多状态截图，必须阻塞“样式不变”结论。仅有截图而未经代码检索，同样阻塞。

## 4. Wave 3：迁移领域设计

新会话粘贴“会话通用头”，再粘贴：

```text
expected_model=GLM 5.2（实际 model id 以 provider 配置为准）。

显式使用 vue2-pages-to-vue3-host-migration Skill，mode=design。
不要修改 A/B 应用代码。migrate 没有 execute mode。

应已存在：<CONFIG>、assess packet、runtime、visual contract、baseline。
assess terminal 为 blocked:visual-chain 或 blocked:visual-baseline，或上述工件
缺失：立即停止，返回 Wave 2，不得把 design 标为 ready。
仅 stale 时刷新受影响事实。artifact_directory 固定为 <DOMAIN_ROOT>。

按 Skill 契约完成 B-native 落点、依赖 disposition、page-scoped 样式适配、
状态/路由/权限/视觉契约、纵向切片、fallback 和 rollback。

design ready 必须满足：style_closure complete 且 unresolved 为空；每项依赖、
CSS/SCSS、颜色、字体和图标都有 disposition/target；每个验收状态映射到纵向切片
和验证行；fallback 可测试且没有 implementation-blocking TBD。

更新并校验 domain packet。不得生成实施授权。意图草稿失效则按通用头回流字段
返回 Wave 1；否则输出 packet path/digest、target design、vertical slices、
visual/style、rollback、readiness 和 blockers。说明下一步为 Wave 4，然后停止。
```

## 5. Wave 4：Frame 规格批准

新会话粘贴“会话通用头”，再粘贴：

```text
expected_model=GLM 5.2（实际 model id 以 provider 配置为准）。

显式使用 delivery-frame-spec Skill。不要 Plan/Execute。本波不得修改 A/B 应用代码。

应已存在：<CHANGE_DIR>、意图草稿、design-ready domain packet
（style_closure complete、无 implementation-blocking TBD、terminal 非 visual-blocked）。
assess-only 或 design 未 ready：停止，回 Wave 3，不得开规格闸门。
从 packet 摘 path+digest 写入 external_artifacts；不要要求 migrate schema 进入
Delivery 状态，也不要改 vue-migration-domain/v1。

基于当前领域事实完成 proposal.md 和增量规格，明确功能/权限/数据/URL/错误/视觉/
回滚验收、颜色/字体/图标及禁止差异。迁移类变更：固定 High、
quality_profiles.visual=required。不要 delivery-explore。

按 Skill 契约完成澄清和规格闸门，只询问一次范围批准。批准必须绑定当前
artifact_revision 并写入 State Source 和 handoff.json。handoff 最终目标仍为
delivery-plan-tasks，但本波结束必须停止。evidence/ 下新增 JSON、截图和摘要不得
冒充 OpenSpec 权威工件。

结束输出：change id/dir、route/risk、proposal/spec、规格闸门、handoff
path/revision。说明下一步为 Wave 5，然后停止；不读取 Plan Skill。
```

## 6. Wave 5：Delivery Plan

新会话粘贴“会话通用头”，再粘贴：

```text
expected_model=GLM 5.2（实际 model id 以 provider 配置为准）。

显式使用 delivery-plan-tasks Skill。只消费当前有效 Frame handoff；不要修改应用
代码，不要进入 Execute。

应已存在：已批准 Frame 规格、design-ready domain packet path+digest、Frame
handoff。缺失或批准失效则回 Wave 4。从 <DOMAIN_ROOT> 校验 runtime、visual
contract/baseline 的 path+digest 和 A/B revision；检查其他 active change 路径重叠。

按 Skill 契约写唯一权威 design.md/tasks.md、traceability、readiness、visual
validation plan、rollback 和 ownership。任务必须是可独立验证的纵向切片，含精确
路径/符号、验证命令、视觉状态、样式/颜色/字体/图标处置和回滚。

visual=required：A baseline 必须已经冻结；所有状态映射到 task；全局 CSS/reset
默认禁止；Delivery G9 产物目录为 <G9_ROOT>。

就绪审查跑 G1–G3、G8、G5。存在阻塞项时不得询问实施授权；就绪后只询问一次
实施 go，并将批准绑定当前 artifact_revision 写入 handoff.json。
implementation go 必须显式携带 source_revision + host_revision、批准人、时间、
范围、验证义务与回退条件。

结束输出：design/tasks、任务数量、readiness、visual plan、实施闸门、handoff
path/revision。说明下一步为 Wave 6，然后停止；不读取 Execute Skill。
```

## 7. Wave 6：Delivery Execute

新会话粘贴“会话通用头”，再粘贴：

```text
expected_model=GLM 5.2（实际 model id 以 provider 配置为准）。

显式使用 delivery-execute-verify Skill。Delivery 是唯一代码 mutation owner；
不要调用 migrate。本波是唯一允许修改 B 应用代码的 Wave。

应已存在：design/tasks、绑定当前 revision 的实施 go、Plan handoff、领域基线与
runtime。缺失则回 Wave 5；A baseline stale 则回 Wave 2。

Preflight：实施 go 绑定当前 revision；A 只读；B 用户改动受保护；任务路径无未
接受冲突；baseline/runtime 有效。

切到 B 声明的 Node 与包管理器；仅 node_modules 缺失、Node/包管理器变化或 lock
变化时 frozen install。启动 B 的 dev script，写入 <RUNTIME_MANIFEST>。
禁止使用 B 仓库拒绝的包管理器或 script 名（以 packageManager / preinstall /
scripts 为准）。A 严格只读，不重装不重启。

严格按 tasks.md：适用时 RED→GREEN→REFACTOR；一次一个 ready task；只改 B 获批
范围；验证通过后才勾选。范围问题回 Wave 4；设计/兼容/回滚/任务问题回 Wave 5。
回流写入通用头字段。

沿用通用头视觉协议。实现消费 Wave 2 冻结契约：B shell 原生、内容 strict parity、
page-scoped 样式、A 的计算颜色/字体/图标身份。不得用 B 全局主题或 UI 库默认
差异掩盖问题。

代码稳定后、Fresh Verification Gate 前重新 index_repository 索引 B，写回
<INDEX_MANIFEST>。此后再改 B 则索引立即 stale。

Fresh Verification Gate：构建/测试、Requirement/Scenario、页面身份、功能/权限/
错误/交互、<G9_ROOT> 的 Delivery G9、rollback、OpenSpec coherence、High 独立
审查（独立 SubAgent 或人类，pass/warn 且无 CRITICAL）。领域 visual 可按 G9
白名单引用（baseline_state_ids / identity_route / identity_marker /
comparison_boundary / style_closure_status / color_metrics /
typography_metrics / icon_identity / table_metrics / rollback_fixture），
但不能替代 G9。

全部通过后写 verification.md 和 verified handoff：overall_status=verified，
archive.status=deferred_to_openspec。不 archive/commit/push/PR/部署/切流。
Delivery verified 只表示交付变更通过，不能单独宣布整次迁移完成。

结束输出：任务/修改摘要、测试构建、G9、独立审查、rollback、verification、
handoff path/revision。说明下一步为 Wave 7，然后停止。
```

## 8. Wave 7：迁移领域最终复核

新会话粘贴“会话通用头”，再粘贴：

```text
expected_model=GLM 5.2（实际 model id 以 provider 配置为准）。

显式使用 vue2-pages-to-vue3-host-migration Skill，mode=verify。
migrate 没有 execute mode，不修改 A/B 应用代码。

应已存在：Delivery verification、G9、完整领域证据、当前代码、<INDEX_MANIFEST>。
Delivery 未 verified 则回 Wave 6，不得声称迁移完成。

先校验 <INDEX_MANIFEST>：A revision 变化时返回 Wave 2 重建 baseline；B 图谱
revision 与当前 host_revision 不一致时先重新 index_repository。最终闭包、调用
和入口结论不得来自 stale 图谱。

按当前 host_revision 停止旧 B 服务并启动干净 dev 服务，更新 <RUNTIME_MANIFEST>。
lock digest 未变化时不重复安装；Node/包管理器或 lock 变化时 frozen install。
A 默认消费已冻结基线；A baseline stale 时返回 Wave 2。

针对当前 A/B revision 刷新 stale 的领域证据，不混用旧 pass。按 Skill 契约完整
复核功能、API/权限/错误、URL/页面身份、runtime/build、style_closure、CSS/SCSS、
颜色、字体、图标、独立状态基线、computed-style、表格、fallback、rollback 和
独立审查。视觉结论沿用通用头协议：确定性工具证据或 Wave 6 后 Kimi 只读复核的
path+digest。

artifact_directory 固定为 <DOMAIN_ROOT>。更新并校验 runtime/visual evidence 和
verify domain packet。运行 migrate Skill 脚本：
validate_runtime_evidence.mjs、validate_visual_evidence.mjs、
validate_domain_packet.mjs。

只有当前 revision 上 functional、visual、runtime/build、permission、rollback
全部通过，style_closure complete 且无 blocking residual，domain verification
才能为 pass。

结束输出：最终 packet path/digest、functional/visual/runtime/rollback 结果、
blockers/residuals、migration_completion_candidate。
pass：对照通用头完成判定逐条确认后，才能声称页面升级迁移完成，然后停止。
fail：不要直接改代码；按通用头回流字段输出，并返回：意图/输入→Wave 1；
规格/验收→Wave 4；闭包/基线/设计→Wave 2 或 Wave 3；任务/回滚→Wave 5；
实现缺陷→Wave 6；A revision 或基线 stale→Wave 2；B 图谱 stale→先完成 Wave 6
末尾重建索引，再执行 Wave 7。然后停止。
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
| A 图谱 revision stale | Wave 2 Assess |
| B 图谱 revision stale | Wave 6 末尾重建索引，再执行 Wave 7 |
| Node、依赖或服务证据 stale | 产生该 runtime evidence 的 Wave 2/6 |

回流必须携带：

```text
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point
```

修复后重新运行完整 Wave 6 和 Wave 7，直到 Delivery 与 Domain 同时通过。

## 10. 完成判定

与通用头完成判定相同，供通读本文的人核对；独立会话以通用头为准。
只有以下全部满足，才能声称“页面升级迁移完成”：

- A 未发生应用代码修改；
- B 为 Vue3 原生实现，未引入 Vue2 或 `@vue/compat`；
- OpenSpec、批准、任务和证据均绑定当前 revision；
- A/B Codebase Memory 索引或 fallback 证据均绑定当前 revision；
- Delivery verified、G9 和 High 独立审查通过；
- Domain functional、visual、runtime/build、permission 通过；
- CSS/SCSS style closure 完整，A 的颜色、字体和图标契约通过；
- 每个代表性状态有独立基线；
- fallback 可演练且 rollback tested；
- Node、包管理器、lock digest、服务 PID/端口/日志和 healthcheck 可追溯；
- 无 blocking residual。

此时仍保留 fallback，不自动 archive、commit、push、PR、部署、切流、删除
iframe 或下线 A；这些需要后续单独授权。

## 11. 使用者与 Agent 可用性检查

### 使用者

- 四个必填值只填一次；每个 Wave 只复制通用头和一个增量提示词。
- 可提供当前 revision 运行中 A 的多状态截图；不需要理解或操作内部工件。
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
用代码审查、单张截图、功能 E2E 或“看起来相似”代替严格迁移结论。用户提供的
截图必须与代码检索并行；与代码矛盾时以代码为准，截图本身不能构成 visual pass。

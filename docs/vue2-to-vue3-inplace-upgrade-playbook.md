# Vue2→Vue3 单仓原地升：用户粘贴剧本

> 这不是 Skill。不要把它当独立技能加载或改任何 Skill 的内部 schema。
>
> 用途：把一次**单仓、同一 workspace 原地** Vue2→Vue3 升级拆成可粘贴的会话。
> 范围可以是**全 workspace**，也可以是**某个/几个 Vue2 页面**（含其闭包）。
> 允许按名组合 `vue2-to-vue3-upgrade-impact-analysis`、`delivery-frame-spec`、
> `delivery-plan-tasks`、`delivery-execute-verify`。视觉验收只走 Delivery G9。
>
> 禁止改 `vue3-upgrade-report/v1`、`vue3-upgrade-summary/v1`、
> `delivery-handoff/v1` 或各 Skill 验证器字段。本剧本启用 Delivery Family 的
> **会话停点覆盖**：每个 Wave 结束必须停止，下一 Wave 只通过磁盘工件恢复，
> 不得用聊天记忆补证据。Wave 1–4 可在用户重新授权后于同一会话继续；Wave 5
> 为保持独立新鲜验证，必须使用全新会话。
>
> 不要用本剧本做跨仓页面迁入或仓内 strangler。那些走
> [vue2-page-migration-playbook.md](./vue2-page-migration-playbook.md)。
> 分析 Skill 单独用法见
> [vue2-to-vue3-upgrade-impact-analysis-usage.md](./vue2-to-vue3-upgrade-impact-analysis-usage.md)。

## 0. 编排结论

```text
Wave 1  vue2 分析（只出决策包）
  → Wave 2  Frame 规格批准
  → Wave 3  Delivery Plan go
  → Wave 4  Delivery Execute
  → Wave 5  独立功能验证
```

全程使用单一模型，不按波换模型。视觉结论来自 Delivery G9 的确定性
工具证据，不以模型看图代替。模型选择不写入任何 Skill schema。

完成水位是仓内 `verified`（Wave 4 实施与 Delivery 闸门 + Wave 5 独立功能验证，
含测试与需要时的 Delivery G9），不含生产发布、切流、监控。归档、commit、push、
PR 仍须另授权。Wave 4 的 Delivery verified 不够，不能单独宣布仓内 verified。

### 0.1 Skill 职责边界

- `vue2-to-vue3-upgrade-impact-analysis` 只负责路径三维、子系统风险、确认队列
和决策包。Name, never run。不改应用代码，不写 OpenSpec 状态，报告里不得填写
其他 Skill 名称。
- Delivery Family 负责 OpenSpec、规格与实施批准、技术计划、应用代码修改、
Delivery G9、独立审查和交付状态。`delivery-execute-verify` 是唯一应用代码
mutation owner；Wave 4 实施，Wave 5 只用它做独立验证、不改应用代码。
- `delivery-explore` 不适用。主路径不插入
`frontend-dependency-upgrade-impact-analysis`，也不调用
`migrate-vue2-pages-to-vue3-host`。
- 视觉验收只走 Delivery G9。G9 未过则留在 Wave 4。仓内 verified 只在 Wave 5
独立功能验证通过后声称。

### 0.2 拓扑消歧（开写前）


| 实际形态                              | 走哪份剧本                       |
| --------------------------------- | --------------------------- |
| 一个 Vue2 SPA，全 workspace 原地升到 Vue3 | **本文**（`pages` 空）           |
| 同一 Vue2 SPA，只升某几个页面（含闭包）          | **本文**（填写 `pages`）          |
| 同一仓库里已有 Vue3 宿主，要把 Vue2 页面/包装进去   | A→B 剧本（两个 root；`host-port`） |
| 两个独立仓库，iframe / 微前端收编             | A→B 剧本                      |
| workspace 已经（部分）升级到 Vue3（`vue_major=3` 或 Vue3 源码占面） | **不走本剧本主线**：Wave 1 只允许停止或显式 residual-audit 残留审计包 |
| 只要决策包、不改代码                        | 分析 usage；不要进入 Wave 2+       |


页面范围只收窄本 change 的闭包，**不是**把页面迁到另一个 Vue3 宿主。共享
runtime/build（`vue` / router / store / Vite）仍属分析范围，因为这些页面跑在
当前 app 里。

Wave 1 若把推荐路径定为 `host-port-direct`，或画像显示实施落点不是当前
workspace：停止原地升，改走 A→B 剧本。不要在本剧本里继续 Frame。

### 0.3 决策包通用动作 → 本剧本下一步

分析报告不得点名 Skill。调用方按本表翻译：


| 决策包字段或报告字面                                                                      | 本剧本                            |
| ------------------------------------------------------------------------------- | ------------------------------ |
| `next_action: analysis_complete` 且 `batch_implementation_gate=ready`            | Wave 2 Frame                   |
| 同上但 gate=`frozen`                                                               | 停在分析；补 lock / 未决 High 后再交接     |
| 状态表 `entry_mode: residual-audit`（或 `recommended_path: residual-audit`）         | **不进 Wave 2 Frame**，无论 gate 是否 ready：它是残留清理包而不是原地升规格。本剧本主线到此结束，清理另立项 |
| `visual_acceptance_required=yes` 且 `recommended_next_action: run_visual_review` | Wave 3 把基线+G9 写入任务；Wave 4 做 G9 |
| `recommended_path: host-port-direct`                                            | 改走 A→B 剧本                      |
| 报告「3. 推荐迁移路径」字面 `Composition API 全仓重写：另立项`                                     | 本 change 的 non-goal            |


### 0.4 用户决策清单（要你拍板的都在这里；证据可能再追加几项）

本节回答三件事：**哪些点必须由你决定、建议选什么、原样回复什么**。下表是按本剧本
已给定的输入能**预先列全**的部分；分析 Skill 还会按它当场读到的证据追加提问，那几项
列在本节末尾——被问到它们不是 Skill 违规，是证据触发了。

两套词汇按**谁来处理**划分，不按波次划分；两套都**不写进任何工件 schema**（它们只是
聊天里的答复用词，`vue3-upgrade-report/v1`、`vue3-upgrade-summary/v1`、
`delivery-handoff/v1` 一个字段都不新增）：

- 分析 Skill 处理的：`confirm:<topic>[:<值>]`、`proceed:path:<id>`、
  `proceed:subsystem:<id>`、`defer`、`other`。完整清单、建议项与不答的后果见该 Skill
  的 `references/user-decision-catalog.md`。
- 本剧本处理的：`approve:<gate>`（闸门放行）、`override:<项>:<值>`（改掉某个建议值）、
  `resolve:` / `accept:` / `backflow:`（处置类）。

Wave 1 会话里**两套同时在场**，各管各的：`override:change-id:` 与
`override:target_vue_version:` 由粘贴块处理（分析 Skill 不认这两个词），路径、子系统
和各项 `confirm:` 由 Skill 处理。下表第 2、10 行属前者，其余 Wave 1 行属后者。

通用规则：Agent 每次提问都必须**先给建议项与理由，再列可原样复制的选项，最后说明
选别的会怎样**。你回「继续 / 都行 / 你看着办 / 按你的建议来」一律无效，Agent 必须重出菜单——这条
是故意的：这些决策的代价都落在几周后，含糊放行等于把代价推给那时的你。

#### 全流程决策表

这里的 Wave 是**本剧本会话波**，不是分析 Skill 内部的提问批次；条件未触发的行不提问、
不要求 token，也不阻止进入下一波。

| # | Wave（剧本会话波） | 决策 | 建议项 | 你原样回复 | 选别的会怎样 |
|---|---|---|---|---|---|
| 1 | 1 | 输出目录 | 已由本剧本钉死为 `OUTPUT_DIR` | —（不该被问；被问了说明剧本没贴全） | — |
| 2 | 1 | 目标 Vue 精确版本 | 沿用通用头默认钉 `3.5.39` | 要换才写 `override:target_vue_version:<精确补丁>`；不写即沿用默认钉 | registry 有更新补丁时 Agent 只提示，不得自行改钉——静默漂移会让各波装到不同补丁上 |
| 3 | 1 | 浏览器基线 | 无 browserslist 时取 `modern` | `confirm:browser-floor:modern` | `confirm:browser-floor:legacy-plugin` 会把 `@vitejs/plugin-legacy` 拉进 `build` 子系统并可能否掉 direct 路径 |
| 4 | 1 | Node **精确版本**；仅 `node_compatibility_status=upgrade-required` 触发 | 按 `evidence_as_of` 从官方周期重算：取目标区间内维护期最长的 Active LTS，再解析该线当前精确补丁 | `confirm:node-target:<本次菜单给出的精确版本>` | `target_node_requirement` 是区间，声明面却各只能填一个值；`compatible+same-node` 不改声明面，因此不问此项 |
| 5 | 1 | Node 过渡策略；仅 `node_compatibility_status=upgrade-required` 触发 | `upgrade-before-vue`（先证明旧仓能在目标 Node 跑绿，再动 Vue） | `confirm:node-strategy:upgrade-before-vue` | `temporary-dual-node` 必须同时给两条 lane 的 owner、切换与删除条件，否则永远删不掉；`compatible+same-node` 不问此项 |
| 6 | 1 | 迁移路径 | `compat-big-bang`（compat 兜住 `.sync`／filters／已移除实例 API 这一族静默失效） | `proceed:path:compat-big-bang` | `direct-vue3` 要求报告写出 `default_path_deviation`，并由命名验证接手 compat 本可兜底的部分 |
| 7 | 1 | 子系统是否纳入；只问 §7 实际 `ready` 的 High/blocker/`required_for_path=yes` 行，以及调用方主动扩入的 medium/low 行 | 对本包实际 `ready` 行逐个 `proceed`；未进队的 store/test 等不问 | `proceed:subsystem:<本包实际 ready id 列表>`（先逐条看过风险与配方） | mandatory 行 `defer` 会让 gate 保持 `frozen`；未进队的 medium/low 行不产生 token，也不构成缺口 |
| 8 | 1 | **已进队且触发分叉**的子系统内部取舍（与上一项同时问，各有各的 token） | 按实际 owner：router→v4；queued store→Vuex 4；UI replace→`after-runtime`；命中 vue-i18n→legacy；§2 unknown 包逐包定 action；queued test→保留 runner | 只回复本包实际触发的 `confirm:router-major:4` / `confirm:store-target:vuex4` / `confirm:ui-staging:after-runtime` / `confirm:i18n-mode:legacy` / `confirm:blocker:<pkg>:replace` / `confirm:test-runner:keep` | 只回 `proceed:subsystem:<id>` 不构成对分叉的答复；marker、DR 的 `分叉人工答复` 与用户 token 必须一致。条件未触发的 store/test/Node 不得补问，更不得由安装命令替答 |
| 9 | 1 | 仓已是 Vue3 | `defer`（没有 Vue2 基线可升） | `defer` | `proceed:path:residual-audit` 只出残留清理包，且**不接** Wave 2，清理另立项 |
| 10 | 1 | 已有同名 change 目录冲突 | `stop`，先人工确认那条线是否废弃 | `stop` | `override:change-id:<已存在的 id>` 恢复旧线；`override:change-id:new` 会分叉出第二条线，同一 workspace 不允许 |
| 11 | 2 | 规格范围批准（含视觉/控制台/行为契约的全部子项） | `approve:spec`（采纳 Agent 列出的全部建议值） | `approve:spec`；要改哪项就先写若干行 `override:<项>:<值>`，最后一行再 `approve:spec` | 见下方「Wave 2 到底在批什么」——这些值定义验收判据本身，留到执行期等于让 Wave 4 自己定标准 |
| 12 | 3 | 实现闸门 go（含回滚演练所需的临时 worktree / git 授权） | `approve:plan` | `approve:plan` | 不授权 worktree 时回滚演练降级为临时目录 clone，两者都不行则记 non-blocking residual（要有 owner） |
| 13 | 3 | 人工前置（后端/Mock、测试账号与权限、验证码、稳定数据） | 逐项确认可用 | `prereq:<项>:ready` 或 `prereq:<项>:missing` | 缺口不报，Wave 5 才炸，那时基线窗口早已关闭 |
| 14 | 3 | 旧 app 起不来、拿不到基线 | `override:baseline:preprod`（用预生产/生产捕获） | `override:baseline:preprod` | `override:baseline:none` 会把「无基线」记成 blocking residual 并回 Wave 2 重议视觉契约 |
| 15 | 4 | 首次 mutation 前工作区不干净 | `resolve:workdir:stash` | `resolve:workdir:stash` | `resolve:workdir:commit` 会把你的在途改动写进历史；`resolve:workdir:include` 把它们纳入本次范围，基线 revision 随之改变 |
| 16 | 5 | 控制台仍有 error，且被判定为非回归 | 不批准——先查清楚它为什么在 | 逐条 `accept:console-error:<route>:<消息类>`；不批准就什么都不回 | error 记 `accepted-residual` **只能**由你显式批准并留下批准语句，Agent 不得自行接受运行时 error |
| 17 | 5 | 已批准的交互/场景**没能实际执行**（人工前置没兑现，如测试账号、后端数据） | 不接受——补齐前置再跑；只有已达到 entry/component-shell 且 Wave 2 允许数据层降级时才可接受 populated-data 缺口 | 逐条 `accept:coverage-gap:<项>` | token 不得豁免 entry-reachable 最低线；未真实挂载迁移组件仍须回流，不能声称仓内 verified |
| 18 | 5 | 本波 fail 回哪一波 | 按缺陷性质，见「7. 失败回流」 | `backflow:wave2` / `backflow:wave3` / `backflow:wave4` | 回错波次会让你在没有规格授权的情况下改代码 |
| 19 | verified 之后 | 新冒出来的问题怎么走 | 非阻断项追加到回顾工件 | `append:retrospective` 或 `open:new-change` | 不得回改已 verified 的 change，也不得无规格批准直接改代码 |

第 8 项是最容易被漏掉的一类：`build` 的分叉（Vite vs cli5-webpack5）**不在**其中，
它是路径三轴之一，由第 6 项的 path preset 决定；要非默认组合只能在第 6 项回 `other`。

#### 表里没有、但可能按证据追加问你的

本剧本只预先给定了输出目录、批次范围和 Vue 目标版本。下面这些在多数仓不触发，一旦
触发 Skill 必须问；建议项与回复写法同样在 `user-decision-catalog.md` 里：

| 触发条件 | 问你什么 | 建议 |
|---|---|---|
| 有 ≥2 个 lockfile，或 lock 与 `packageManager` 不一致 | 包管理器 / lock 归属 | 取 `packageManager` 声明的那个 |
| registry 与官方迁移文档双双连不上 | 离线出包还是先补网络 | `defer`——离线时版本与破坏面都只能靠推断，不值得据此定路径 |
| `ui` 就绪度 `replace`（整体换 UI 库） | 是否放宽行为 parity | 由你明确：换库时「严格 parity」是一句兑现不了的承诺，不答则 `ui` 行不得 `decided` |
| 某包 `dist-tags.latest` 已越过迁移文档区间（vite、plugin-vue 等） | 该包钉哪个精确版本 | 钉迁移文档覆盖的那个 major 的精确版本 |

被问到这四项是正常的。反过来，被问**输出目录或批次范围**才说明粘贴块没贴全。

#### Wave 2 到底在批什么

`approve:spec` 是**一次**提问，但它背后有一组各自独立的取值。Agent 必须在提问的同一条
消息里把它们逐条列出来（当前值 + 建议 + 理由），你才可能知道自己批的是什么：

| 项 | 建议 | 覆盖写法 |
|---|---|---|
| `visual` 是否 required | 分析包 `visual_acceptance_required=yes` 或出现 UI-kit / Tailwind / 表格混用 / scoped-style 风险时为 `required` | `override:visual:not-required`（须写明证据） |
| `assessment_mode` | UI 库整体更换（如 element-ui→element-plus）取 `consistency_review`；同库内升级取 `strict_parity` | `override:assessment-mode:strict-parity` |
| `diff_policy` | 弹层挂载点变化、空数据下分页隐藏等归 allowed native adjustment；未归类一律按 failure | `override:diff-policy:<逐类写明>` |
| `structural_parity_metrics` | 只把与数据无关的结构计数列为 parity 判据 | `override:structural-parity:<白名单>` |
| `capture_conditions` | 基线与升级后同运行面、同端口策略、同后端可用性、同 locale/timezone/theme | `override:capture-conditions:<写明>` |
| `required_visual_states` | ≥5 个唯一状态（下游按证据行硬计数） | `override:visual-states:<列出>` |
| `console_baseline_required` | 固定 `yes` | `override:console-baseline:no-baseline`（仅当升级前 app 任何 lane 都起不来） |
| 验证可达性三层 | 固定区分 entry-reachable → component-shell → populated-data；只有最后一层可按已批准条件降级 | `override:data-dependent-layering:no`（仅关闭数据层降级，不得豁免 entry 最低线） |
| `ui_behavior_contract` 断言 | 逐条进入已批准 spec 的验收场景，与视觉状态分开列 | 不建议覆盖：G9 pass 不构成这些断言的证据 |

`entry-reachable` 的最低线不可被覆盖：每条应验证运行面至少一个代表入口必须越过
登录/路由占位并真实挂载迁移组件；`#app` 空、登录页或“项目不存在”占位不算。
这些值一旦批准，Wave 4 与 Wave 5 都**不得**单方改写；要改只能回 Wave 2 重批并记 DR。

## 1. 通用输入与自动恢复协议

### 1.1 用户怎么使用

1. 在前端 workspace 打开会话。全仓升则不必填路径；只升某几个页面时在通用头写
  `pages`。
2. 启动当前 Wave：Wave 5 必须全新会话；Wave 1–4 可用全新会话，或在上一个
   Wave 已停止且用户重新授权后继续原会话。按当前 Wave 连续粘贴为一条消息：
   Wave 1：「每波必贴」+ Wave 1 块；
   Wave 2–5：「每波必贴」+「Wave 2–5 追加」+ 当前 Wave 块。
3. 当前 Wave 完成并停止后，由用户显式启动下一 Wave；无论是否换会话，都从磁盘工件恢复。
4. 用户只回答「0.4 用户决策清单」里的 token。不要手工搬运 JSON 或 digest。

### 1.2 会话通用头——按 Wave 粘贴；仅覆盖项可省略

Wave 粘贴块只补充本波 Skill、应已存在的上游工件、增量门禁和结束产物。
通用头已覆盖的检索、边界、回流字段、完成判定和停点不要复述。

#### 每波必贴

```text
这是当前 Wave 的独立执行段；不得使用此前聊天记忆补结论，只认磁盘工件。
若本波是 Wave 5，必须确认这是全新会话，否则停止。
全程使用单一模型；本波内不换模型。
本会话只执行随后指定的一个 Wave；写盘校验后立即停止，不要加载或执行下一个 Skill。
不要使用 delivery-explore，不要调用 migrate-vue2-pages-to-vue3-host。

默认（仅 CONFIG 不存在且用户未覆盖时使用）：
- workspace = 当前本地仓库 / workspace（含待升级的 package.json）
- pages = 空 → 全 workspace（batch_scope=full-stack）
- target_vue_version = 3.5.39
  核对于 2026-08-22 的固定钉 `vue@3.5.39`；不得把这个钉说成"当前最新"，它随时间
  必然落后。**核对当日 registry 的 `latest` 就已经领先本钉**——落后是有意的，不是
  没查。Wave 1 校验它在 registry 可解析后写入 CONFIG，其后全程不变；发现 3.5.x
  线已前移只把「默认钉 vs 线上最新」回显给用户，agent 不得自行改钉——静默漂移会
  让各波装到不同补丁上。

可选覆盖（需要时才写）：
pages = <路由或文件，多个用逗号或换行；填写则 batch_scope=page-closure>
workspace = <仅当当前打开的不是前端根时>
target_vue_version = <仅在用户明确指定其他精确版本时覆盖>

自动派生并保持稳定：
- CONFIG 已存在：先从 CONFIG 恢复 workspace、pages、target_vue_version 和派生路径；
  本次未显式填写的覆盖项不重新套默认值
- TARGET_VUE_VERSION = CONFIG.target_vue_version（CONFIG 存在时），否则为
  target_vue_version
- SLUG：pages 有值则由页面标识规范化（多个用 + 连接，过长截断并加短哈希）；
  否则用 workspace 目录名
- CHANGE_ID = vue2-to-vue3-inplace-<SLUG>
- CHANGE_DIR = <workspace>/openspec/changes/<CHANGE_ID>
- EVIDENCE_ROOT = <CHANGE_DIR>/evidence
- OUTPUT_DIR = ANALYSIS_ROOT = <EVIDENCE_ROOT>/vue2-to-vue3-upgrade
- G9_ROOT = <EVIDENCE_ROOT>/delivery-visual
- CONFIG = <EVIDENCE_ROOT>/inplace-run-config.json
CONFIG 存在后以其中记录为准；只有本次**显式填写**的值与配置不一致时停止。
每波开始先检索 <workspace>/openspec/changes/ 下已有的 vue2-to-vue3-inplace-*
目录：存在且与本次派生 CHANGE_ID 不同（例如 pages 改动导致 SLUG 变化）时停止
询问用户，不得静默派生新 CHANGE_ID 分叉第二条线。提问时给出三个原样选项：
override:change-id:<已存在的 id>（恢复旧线，建议）、override:change-id:new
（另开一条，需用户说明旧线如何处置）、stop。同一 workspace 同时只允许
一个 inplace change。
CONFIG 已记录旧分析路径时沿用，不要并行维护 workspace 根
.vue2-to-vue3-upgrade-analysis。

固定边界：
- 任何包都不得用 dist-tag 解析版本（latest / next / rc / beta / edge）：它们按包
  各自维护，经常指向非预期版本（`next` 可能比 `latest` 老好几年，`latest`
  可能已越过你要读的迁移文档区间）。安装目标 major 必须当场查 registry 显式钉死，
  并在报告或任务里留下依据。
- 任何 install 之前先打印 NODE_ENV 与 npm config get production（yarn/pnpm 用等价
  配置项）。任一为 production / true 时 install 会静默跳过 devDependencies，构建
  与 lint 的 bin 随之缺失，报错表现为「命令不存在」而不指向环境；此时必须显式
  NODE_ENV=development 或 --include=dev 重装，并把该处置写进本波证据。这条对
  Wave 4 的实施安装和 Wave 5 的 frozen install 同样适用。
- 单仓原地升。pages 只收窄本 change，不是 A→B host-port，也不是页面闭包迁入。
- 默认行为 parity；保留 Options API。Composition API 全仓重写另立项。
- Vue 3.6 / Vapor mode 不在本轮范围；任何 rc/beta 都不得进入本次升级。
- 仅 Wave 4（delivery-execute-verify）可修改应用代码并安装依赖、运行命名配方；
  Wave 1–3 与 Wave 5 对应用代码只读。分析阶段 Name, never run。
- Wave 5 可启动/停止干净服务、重跑验证、刷新 Codebase Memory 索引与 G9 证据；
  lock/Node/包管理器变化时允许 frozen install，不得跑实施配方或改 tasks 勾选。
- 保护 workspace 里已有的本地改动。
- 部署、生产切流、监控不属于本轮。禁止 Quick。本变更固定 High。
- Wave 1–4 不得声称仓内 verified。

自动恢复以随后 Wave 块「应已存在」行为准。已完成 Wave 的工件缺失/损坏/stale
则停止并指出重跑 Wave，不要求用户手工提供内容。

凡需要用户决定的点：先给建议项与理由，再列可原样复制的 token，最后说明选别的
会怎样。「继续 / 都行 / 你看着办」不构成答复，重出菜单。不得代用户决定，也不得把
两个决策并成一个 token。Wave 1 的 token 清单以分析 Skill 自己的 references 为准；
Wave 2–5 只用本波粘贴块里点名的那些（approve: / override: / prereq: / resolve: /
accept: / backflow:），不要发明新词。

失败回流最小字段（alignment_backflow）：
discovery / evidence / affected_scope / invalidated_artifacts /
decision_needed / recommended_resolution / resume_point
```

#### Wave 2–5 追加（Wave 1 不要贴）

```text
不要让 vue2 分析 Skill 改代码或重开决策包。

代码检索：默认 Codebase Memory MCP
（search_graph → trace_path → get_code_snippet；复杂闭包 query_graph；
结构 get_architecture；模板/导入/字符串 search_code）。
仅 package.json、锁文件、构建/样式配置，或 MCP 为空/明显不完整时，才降级到
文件读取或 rg，并记录 query、缺口和原因。不得因图谱没有 Route 节点断言路由不存在。

Node 必须拆成两面：当前项目实际/声明的 Node 契约，以及所选目标工具链精确
版本的 engines.node 交集。不得写死“Vue3 最低 Node X”，也不得只看本机
node -v；同时覆盖本地 pin、engines、CI、Docker/devcontainer、部署构建环境。
vue 的 resolved version 必须等于 TARGET_VUE_VERSION；路径涉及
@vue/compat / @vue/compiler-sfc / @vue/server-renderer 时，这些包的
resolved version 必须完全一致。manifest 是否保留范围符号遵循已批准规格，
但 lock 不得漂到其他 Vue 版本。
漂移的判据是适用包 resolved version 不等值或出现其他 Vue major，**不是** lock
digest 变没变——同批替换框架与构建链时 digest 必然变。「digest 未变」只用于判断
是否需要重装，不得反过来当漂移证据。G9 与控制台采集脚本自身的工具链依赖（无头
浏览器驱动等）不计入应用 lock 判定，也不得为采集写进应用 dependencies。
@vue/compat 的 peer 是精确版本而非范围，补丁号对不上会在安装期直接失败或告警，
按硬约束对待，不要只靠事后核对 resolved version。

「裸装解析到哪个 major」与「该读哪份迁移文档」是两件事，不得互相替代。

visual=required 时 G9 用 delivery-visual-evidence/v1，目录 G9_ROOT。
外部分析视觉字段只允许引用 G9 白名单：baseline_state_ids、identity_route、
identity_marker、comparison_boundary、style_closure_status、color_metrics、
typography_metrics、icon_identity、table_metrics、rollback_fixture。

仓内 verified 仅 Wave 5 在独立功能验证通过后才能声称，条件清单在 Wave 5 块里。
Wave 2–4 只需知道：本波不得声称它，也不得把 Delivery verified 说成它。
```

### 1.3 工件恢复矩阵


| 工件组                         | Agent 用途                                 | 用户操作     |
| --------------------------- | ---------------------------------------- | -------- |
| `ANALYSIS_ROOT`             | 分析决策包、summary、inventory、decision-records | 确认路径；看摘要 |
| `CONFIG`                    | 同一 change 的业务输入和派生路径                     | 不操作      |
| OpenSpec 工件与 `handoff.json` | 规格、批准、计划、任务和交付状态                         | 批准时看摘要   |
| `G9_ROOT`                   | Delivery G9 视觉验收                         | 最终看摘要    |


默认不得在 `CHANGE_DIR` 外另建第二套 delivery 状态，也不得把分析包写到
workspace 根 `.vue2-to-vue3-upgrade-analysis`。分析报告默认落在
`ANALYSIS_ROOT`（`<CHANGE_DIR>/evidence/vue2-to-vue3-upgrade`）。Wave 1
只创建该证据目录并写入 `CONFIG`，不写 OpenSpec 状态。Wave 2 在同一
`CHANGE_ID` 上创建或恢复 change（接管 Wave 1 留下的 evidence-only 目录），
把报告 path+digest 记为 `external_artifacts`，不把分析 schema
写进 Delivery 状态。新增分析报告不会使 Frame 批准失效；改 proposal/spec 仍会。


| Wave      | 应当存在的主要上游工件                                                   |
| --------- | ------------------------------------------------------------- |
| 1 分析      | 无；不要求 OpenSpec / Memory。可先创建 `ANALYSIS_ROOT` 目录           |
| 2 规格批准    | 定稿决策包（`analysis_status=complete`）；OpenSpec + Memory 从此波开始是硬前提 |
| 3 Plan    | 已批准 Frame 规格、分析 path+digest、Frame handoff                     |
| 4 Execute | design/tasks、Plan handoff、实现闸门；`visual=required` 时含 G9        |
| 5 独立功能验证 | Wave 4 verification / verified handoff / G9、当前代码、CONFIG     |


Wave 1 **不**要求 OpenSpec 或 Codebase Memory。Wave 2–5 硬前提失败时用
Delivery 固定三行报告停止，不降级。

## 2. Wave 1：vue2 分析（只出决策包）

本波 token 速查：`override:target_vue_version:<精确补丁>`；其余只用分析 Skill
目录中的 `confirm:*`、`proceed:path:*`、`proceed:subsystem:*`、`defer`、`other`。

启动本 Wave（全新会话，或上波停止后经用户重新授权的同一会话）时粘贴「每波必贴」，再粘贴：

```text
本波：显式使用 vue2-to-vue3-upgrade-impact-analysis。只出决策包。
不改代码、不跑 codemod、不写 OpenSpec 状态（proposal/spec/design/tasks/handoff），
不 init OpenSpec，不调用 create_change。

应已存在：无。不要求 OpenSpec / Memory。

本波要把该 Skill 的**全部提问批次跑完**，不是只问路径。它内部按 Wave 0（设置确认）
→ Wave 1（迁移路径）→ Wave 2+（子系统纳入及其内部分叉）分批提问；那套编号是**提问
批次**，与本剧本 Wave 1–5 的**会话阶段**不是同一套东西，本剧本 Wave 1 覆盖它的全部
批次。路径答完必须紧接着开子系统批次，直到确认队列里没有 ready/pending 且 gate 得出
结论，才允许结束本波。不得以「子系统是 Wave 2 的事」为由留到下一个会话——本剧本
Wave 2 是 Frame 规格批准，它既不提问也无法记录分析包的决策，留过去只会被打回本波。

所有**已触发**的 Wave 0 设置确认（浏览器基线、升级所需的 Node 精确版本与过渡策略、
非 vue 包的版本钉等）合并成**一条**消息问完，不要一个探针打断一次。Node 的两面——
当前项目契约与目标工具链 engines.node 交集——必须在本波算清并记入报告；只有结果为
`upgrade-required` 才问 Node target/strategy，`compatible+same-node` 不产生这两个 token。

入口：单 workspace；project-root = workspace。--output-dir OUTPUT_DIR
（CHANGE_DIR/evidence/vue2-to-vue3-upgrade）。禁止再问 confirm:output-dir。
本波只创建 ANALYSIS_ROOT 与 CONFIG（及必要父目录）；不要写到 workspace 根
.vue2-to-vue3-upgrade-analysis。
pages 空 → batch_scope=full-stack。
pages 有值 → batch_scope=page-closure（页面+闭包+共享 runtime/build；其余 non-goal）。

目标 Vue = TARGET_VUE_VERSION。用户未覆盖时固定为 3.5.39；本波向 npm registry
校验该精确版本可解析后写入 CONFIG 与报告；不得写 latest、不得写「当前最新
3.x」、不得凭记忆改填其他版本号、不得落到 3.6 线的任何预发布（alpha/beta/rc）。
校验失败或该版本不可用时停下询问用户，不得自行改钉其他版本（包括 3.5.x 线的
其他补丁）。registry 显示 3.5.x 线已有更新补丁时，把「默认钉 vs 线上最新」作为
一行提示回显给用户，由用户决定是否覆盖；未覆盖就继续用默认钉，不得自行更换。
覆盖写法固定为 override:target_vue_version:<精确补丁号>；不接受「用最新的」这类
表述——它没有指向一个确定版本，各波会装到不同补丁上。
「2. 仓画像与依赖就绪度」与「3. 推荐迁移路径」必须写出该精确补丁号。
CONFIG 一旦记录，后续各 Wave 一律沿用，不得因为上游发了新补丁而漂移。

报告「3. 推荐迁移路径」必须出现字面：
Composition API 全仓重写：另立项，本次不评估工作量

host-port-direct、另一 Vue3 宿主、iframe 收编、topology_axis=host-port、
或实施落点不是当前 workspace：停止本剧本，不要进入 Wave 2，不要加载其他剧本。
画像 vue_major=3（workspace 已是/部分是 Vue3）：同样停止本剧本主线。用户显式要求时
才按 Skill 契约出 residual-audit 包；它不接 Wave 2，清理另行立项。

其余报告形状、证据要求与确认 token 一律以该 Skill 的 references 与校验器为准，
本块不复述——包括版本解析纪律、子系统与 peer 登记、三轴与 default_path_deviation、
运行面拆分、ui 行为契约、console-baseline、recipe_constraints、报告章节锚点，
以及全部 confirm/proceed 提问形状。
输出目录与批次范围本剧本已给定（OUTPUT_DIR、pages），属已答复项，不得再问。
报告与 summary 不得填写其他 Skill 名称。

本波结束前写入 CONFIG（workspace、pages、target_vue_version、派生路径，
不含批准），并向用户回显 CHANGE_ID。CHANGE_DIR 在 Wave 2 之前只是证据目录
（没有 proposal.md 属预期，由 Wave 2 接管补齐 OpenSpec 槽位）；若用户决定
放弃升级，应删除整个 CHANGE_DIR，避免半截目录阻塞后续变更的路径重叠检查。

gate=ready 且仍是原地升：说明下一步 Wave 2，然后停止。
gate=frozen：说明缺口，不要进入 Wave 2，然后停止。
```

## 3. Wave 2：Frame 规格批准

本波 token 速查：零到多条 `override:<规格项>:<值>`，最后一条 `approve:spec`。

启动本 Wave（全新会话，或上波停止后经用户重新授权的同一会话）时粘贴
「每波必贴」和「Wave 2–5 追加」，再粘贴：

```text
本波：显式使用 delivery-frame-spec。不要进入 Plan/Execute。
不要再次执行 vue2 分析 Skill（只读已定稿的 ANALYSIS_ROOT）。
框架升级 / 迁移类变更，固定 High，禁止 Quick。本波不得修改应用代码。

应已存在：定稿决策包（analysis_status=complete，batch_implementation_gate=ready）。
缺失或 gate=frozen：停止，回 Wave 1。OpenSpec + Memory 本波起为硬前提。
本波**不替分析包补问决策**：迁移路径、实际进队的子系统纳入，以及**已触发**的内部
分叉（router major、queued store 目标、命中的 i18n mode、queued test runner、逐包
blocker action）、`upgrade-required` 时的 Node 目标版本与过渡策略，全部属 Wave 1，本波
既不提问也无法记录（它们是分析报告「7. 确认队列」的行与「1. 基线与假设」的字段，
不是 Frame 的规格项）。
发现这些仍未决：直接停止并说明回 Wave 1 补完，不要在本波开菜单问用户——问了也存不下，
只会让用户答两遍。
硬前提：workspace 的 OpenSpec 已初始化；Codebase Memory 对 workspace 可查询。
索引缺失时先 index_repository。openspec: cli-only 时按 Frame Skill 固定三行报告
并询问 initialize_repo，不得发明平行 Markdown 状态。

先读 ANALYSIS_ROOT/upgrade-summary.json；再打开
ANALYSIS_ROOT/vue2-to-vue3-upgrade-report.md 的「1. 基线与假设」「3. 推荐迁移路径」，
其他章节按 summary 点名读取。

分析包时效检查（硬前提）：只读重跑 vue2-to-vue3-upgrade-impact-analysis 的
scripts/profile_inventory.py 生成临时 inventory（不覆盖 ANALYSIS_ROOT），与
ANALYSIS_ROOT/inventory.json 逐字段对比 repo_revision、vue_major、builder、
ui_stack、lockfile_digests（锁文件 sha256，由脚本产出），并核对报告
「1. 基线与假设」的 repo_revision 与 inventory 一致。脚本不可用时降级为直接
对比 inventory.json 与当前仓库的 git HEAD、package.json vue 主版本、锁文件
sha256，并记录降级原因。任一漂移（例如仓库已被改成 Vue3 而分析仍描述 Vue2
基线）：判定分析 stale，停止本波，回 Wave 1 重跑，不得沿用旧决策包开规格闸门。
batch_implementation_gate=ready 不是实施授权，也不是规格批准。
「1. 基线与假设」Node 未知/冲突，或 build 的 Node 未 decided：停止，回 Wave 1。
「3. 推荐迁移路径」目标 Vue ≠ TARGET_VUE_VERSION：停止，回 Wave 1，不得在 Frame 改版本。
summary.recommended_path 为 host-port-direct，或 topology 不是 single-cutover：
停止本剧本，不要开规格闸门，不要加载其他剧本或 migrate Skill。
向用户说明拓扑不是单仓原地升。

创建或恢复唯一 CHANGE_DIR（与 Wave 1 同一 CHANGE_ID）。若 ANALYSIS_ROOT
已有定稿分析包，恢复该目录并补齐 OpenSpec 槽位，不要另建 change 或改 CHANGE_ID。
校验并补全 Wave 1 写入的 CONFIG（缺失时按报告与用户输入重建；不含批准）。
将分析报告与 summary 记为 external_artifacts（path+digest）。

范围：pages 空 = 全 workspace；pages 有值 = 这些页面+闭包+共享 runtime/build，其余 non-goals。
规格钉死 TARGET_VUE_VERSION，适用的 vue / @vue/compat / compiler-sfc / server-renderer
resolved 必须一致；禁止 latest。
non-goals 必须含：Composition API 全仓重写；Vue 3.6 / Vapor mode；生产发布/切流；
compat 若选用须写移除日期或退出条件。

quality_profiles.visual：分析 visual_acceptance_required=yes 或代码/配置出现
UI-kit、Tailwind/reset、表格混用、scoped-style 风险时为 required；否则按证据写明不需要。
required 时基线须在改 vue/依赖之前捕获；G9 目录 G9_ROOT。
required 时 required_visual_states 必须至少 5 个唯一状态——下游 G9 校验器按
证据行硬计数 ≥5；分析包不足 5 个时在规格批准前补足并写入已批准 spec，
不得留到执行期（那时基线窗口已关闭）。

required 时已批准 spec 还须同时写明下列四项，缺一不得通过规格闸门。它们定义 G9
的判据本身，留到执行期再定等于让 Wave 4 单方定义验收标准：
- assessment_mode：strict_parity 或 consistency_review（G9 证据的必填枚举）。
  UI-kit 整体更换（如 element-ui→element-plus）存在原生视觉系统差异，可以选
  consistency_review，但必须在本波声明并写明理由；Wave 4 不得自行改写该值。
- diff_policy：逐类列出哪些差异属 allowed native adjustment（例如弹层挂载点变化、
  空数据下分页隐藏），哪些属 forbidden failure。未归类的差异按 failure 处置。
- structural_parity_metrics：哪些结构计数是 parity 判据，哪些属数据依赖态、允许
  随后端数据缺失漂移。白名单之外的计数差异一律按 failure 处置。
- capture_conditions：基线与升级后必须同条件采集——同运行面（dev / build 产物静态
  serve，二者不可互替）、同端口策略、后端可用性一致、同 locale/timezone/theme。
  条件不一致时 404、SecurityError 之类的差异无法区分是环境还是升级回归，
  G9 结论不成立。

visual 是否 required，本波都必须批准一份控制台基线契约（与 G9 分开，不受
visual=no 影响）：
- console_baseline_required 固定 yes（除非有证据说明升级前 app 在任何 lane 都无法
  启动，此时按「无基线」记 residual，并要用户回 override:console-baseline:no-baseline
  显式批准——Agent 不得因为采集麻烦就自行降级）；
- 采集范围为 Wave 5 功能冒烟将覆盖的路由集合，采集口径与 Wave 4/5 一致
  （每路由独立 fresh page），采集条件复用同一份 capture_conditions；
- 采集内容为控制台**全量输出**（error 与 warning 全量、按消息类去重计数），不得只
  采 error 或只采某份白名单 warning：基线里没采到的类别，Wave 5 就无法判定它是
  regression 还是本来就有，只能当噪声滑过；
- 存在 dev 运行面时基线必须**两条运行面各采一次**，Wave 5 按同一运行面逐条对比。
基线在升级前 revision 采集，窗口与视觉基线同时关闭；事后无法在同一 revision 补采。

分析包含 ui_behavior_contract 时（UI 库整体替换/跨大版本），
required_behavior_assertions 逐条进入已批准 spec 的验收场景，与视觉 required 状态
分开列。这些是行为契约（懒挂载与 $refs 时机、prop / 枚举改名、事件契约），
G9 pass 不构成它们的证据，也不得被 visual=no 顺带豁免。

每个 required 场景在 spec 中声明最低可达层，不得把登录墙与数据墙合并：
- `entry-reachable`：越过登录/路由占位，真实迁移根组件已挂载；这是每条运行面
  至少一个代表入口的不可豁免最低线；
- `component-shell`：组件已挂载，可验证无数据结构与交互；
- `populated-data`：稳定真实/Mock 数据可用，可验证分页、编辑、回写等完整行为。
required 状态若仅 `populated-data` 不可得，允许以「component-shell parity + 绑定后续
真实后端验证任务」记 accepted-residual，但该分层必须在本波声明并写入已批准 spec，
且以基线在同条件下同样只能取到 component-shell 为前提。Wave 5 不得临时发明分层，
也不得用 accepted-residual 把 auth-walled/占位页说成 component-shell。

通过规格闸门：只问一次范围批准，但那一条消息里必须把它背后的取值逐条摊开——
visual 是否 required、assessment_mode、diff_policy、structural_parity_metrics、
capture_conditions、required_visual_states、console_baseline_required、验证可达性
三层与各场景最低层、ui_behavior_contract 断言——每项写「当前建议值 + 一行理由」。这些值定义验收
判据本身，不摊开就等于让用户批一个他看不见的东西，而 Wave 4/5 之后都不得单方改写。
用户回复 approve:spec 表示全部采纳；要改哪项就先写若干行 override:<项>:<值>，
最后一行再 approve:spec。含糊放行无效，重出清单。然后停止。下一步 Wave 3。
```

## 4. Wave 3：Delivery Plan go

本波 token 速查：逐项 `prereq:<项>:ready|missing`；需要改计划值时先
`override:<项>:<值>`，最后 `approve:plan`。

启动本 Wave（全新会话，或上波停止后经用户重新授权的同一会话）时粘贴
「每波必贴」和「Wave 2–5 追加」，再粘贴：

```text
本波：显式使用 delivery-plan-tasks。不要实施、不要改应用代码。

应已存在：已批准 Frame 规格、分析 path+digest、Frame handoff。缺失或批准失效则回 Wave 2。
先读 CONFIG；target_vue_version 或派生路径与通用头不一致时停止，回 Wave 2。
只读 ANALYSIS_ROOT/upgrade-summary.json（named_recipes / named_validations /
runtime_lanes / recipe_constraints / ui_behavior_contract）与
ANALYSIS_ROOT/inventory.json 的
source_impact_signals.interaction_assertion_candidates。
summary 有 ui_behavior_contract 时，另读报告「5.」的 ui_behavior_contract 块取详情。
需要某条决策时再打开 ANALYSIS_ROOT/decision-records 下对应文件。
同时只读已批准 spec。

把分析里的命名配方写成纵向任务（精确文件/符号或 glob、实施期命令、失败时证明什么、回滚要点）。
任务顺序按 summary.recipe_constraints 的 after 拓扑排列，不自行改序；atomic=yes 的配方
不得拆成多个可分别落地的任务，atomic=no 才允许按目录/模块分批并逐批 review diff。
pages 有值时，任务不得把未点名且未进入闭包的页面扩进范围。
本波不跑配方（gogocode / vue-upgrade-tool / webpack-to-vite / npm install）。
依赖任务必须使用 TARGET_VUE_VERSION，校验适用包 resolved version 相等，拒绝 lock 漂移。

tasks.md 必须**显式分区**，每条任务标注归属波次：
- **Wave 4 权威区**：全部应用代码与依赖 mutation，以及在 Wave 4 会话内就能证伪的
  验证（基线采集、frozen install、build/test、named_validations、G9、回滚演练）。
- **Wave 5 区**：只有在全新会话、按当前 revision 独立重跑才成立的验证——完整功能
  冒烟、逐路由 × 逐运行面的控制台对比、以及依赖本波人工前置（测试账号、后端/Mock
  数据）才能执行的已批准场景。
Wave 4 的 Delivery verified handoff **只对权威区判定**：Wave 5 区任务在 Wave 4 结束时
保持未勾选是预期状态，不构成 Wave 4 未完成，也不阻止写出 verified handoff。没有这条
分区，一条只能在 Wave 5 跑的登录态验证任务会同时卡住 Wave 4 的 verified 和依赖该
handoff 的 Wave 5，两波互相等待，实际只能靠偷偷勾选或降级绕过。
反向也不成立：任何需要改应用代码的任务一律进权威区，「要登录才能验」不是把实施
任务推到 Wave 5 的理由。分区随计划一并进入 approve:plan，Wave 4/5 不得单方改分区。

Node 任务须纵向且排在首次 install 之前：保存当前 Node 绿色基线；在改 Vue 依赖
前验证旧项目能否运行于目标 Node；按已批准策略把**所有**声明面更新到同一个
selected_node_version（报告「1.」记录的那个具体版本，不是 target_node_requirement
那个区间）——.nvmrc/.node-version/Volta/engines、CI、Docker/devcontainer、部署
builder 与 Corepack/packageManager 逐处核对一致；报告没有 selected_node_version
时停止回 Wave 1，不得由本波挑一个版本填进去。再用目标 Node frozen install + build/test。temporary-dual-node 要有两 lane、切换条件、
删除条件与缓存隔离。不得只改开发者本机 Node。

visual=required 时：基线捕获发生在升级之前；每个 required sample/state 映射到任务；G9 路径为 G9_ROOT。
基线任务须把已批准 spec 的 capture_conditions 固定成可复现的命令与参数（运行面、
端口策略、后端可用性、locale/timezone/theme）并记入证据，Wave 4/5 的 current 采集
复用同一条件。条件无法复现时按「无基线」处置，回 Wave 2 重议视觉契约，不得改条件后
硬比。

控制台基线任务（独立于 visual，按已批准的控制台基线契约生成）：在首次依赖/代码
mutation 之前，对升级前 revision 按批准的路由集合与运行面逐条采集，落盘
EVIDENCE_ROOT/console-baseline.json，字段与 console-evidence.json 同构并多一列
runtime_lane。该任务必须排在所有 install 与配方任务之前——窗口与视觉基线同时关闭。

控制台采集器全仓唯一：本波生成的任何控制台相关任务，都必须复用同一个采集器与同一
口径（每路由独立 fresh page，逐路由 runtime_lane 标注），不得另写第二套采集脚本或
另一种口径（例如单页面连续跳转累积监听）。口径分叉会让基线、Wave 4 与 Wave 5 三份
计数互不可比，还要额外解释差异。

运行面覆盖：存在 dev 运行面时，任务必须同时覆盖 dev 与 build 两条运行面，
逐条写明该任务在哪条运行面上验证；不得用一条运行面的绿代替另一条。
分析报告「10.」运行面差异行点名的证据（源码内 CJS、require.context、多入口 URL
形态、base/publicPath、env 分支）逐项生成验证任务。
基线可行性前置：必须先有任务证明旧 app 能在某个可用 lane 启动（老 Node 仓即
temporary-dual-node 的旧 lane）；若证明不可启动，须显式二选一并写入任务——
override:baseline:preprod（用预生产/生产环境捕获替代基线，建议）或
override:baseline:none（把「无基线」记为 blocking residual 并回 Wave 2 重议
visual 契约）。这是用户的选择，不是 Agent 的判断；不允许 baseline_status 悬空滑过。

交互断言清单：以 inventory 的
source_impact_signals.interaction_assertion_candidates.rows 为准，逐行生成交互
验证任务（每行一条「输入→状态回写」断言，最小组件测试或脚本化浏览器检查），
写入 tasks 与验证命令，不留给执行期自拟冒烟范围。

每一行的**语义、断言点与严重度以分析包为准**，本剧本不复述：该 signal 的结论写在
报告「5.」的 `ui_visual_risk` / `ui_behavior_contract` 块、「8.」验证矩阵对应行，以及
「10. 未决问题与证据缺口」人工补搜检查的同名行里（例如 model_option 的 live/dead
判定、sync_modifier 的目标库 prop 身份、kit_icon_class_prop 的 mount throw 分类）。
读那几行，不要凭本剧本或记忆重推——分析 Skill 会随实战增补 signal，复述在这里只会
比它旧一轮。缺少某行结论时停止并回 Wave 1，不得由本波自拟语义。

对所有行统一适用三条，与具体 signal 无关：
- 断言点必须是**运行期可观测的行为或最终 DOM**（弹层真的打开并挂载出子组件、图标
  出现且 toolbar 交互可执行、导航真的完成或按预期抛错、正文节点真的被绘制），
  不得写成「变量被置为 true」「页面渲染出来了」「build/lint 通过」——这一族的共同
  特征就是这些都绿。
- 报告判为运行期抛错或整块不渲染的行按 blocker，不得降级为纯视觉任务。
- 每行落在哪条运行面上验证要写明；存在 dev 运行面时按运行面各排一条。

summary.recipe_constraints 里有 overlaps_with 的配方对，必须额外生成一条**交集**
验证任务，不能用任一配方自身的任务顶替。
ui_behavior_contract.required_assertions 逐条生成行为验证任务（弹层打开后子组件确实
挂载、`$refs` 可用、prop 回写生效、枚举生效、事件不双触发），与视觉任务分开列；
这些断言不得由 G9 顶替。
candidates.truncated=true、source_impact_signals.truncated=true 或页面闭包超出
扫描面时，按 candidates.truncated_signals 与 total/emitted 计数补全对应 signal 的
检索再生成清单，不得把截断结果当完备清单。

回滚演练任务：计划中必须有一条命名验证——在临时 worktree checkout 升级前
revision，用旧 lane frozen install + build 证明回滚路径可用，产出机器证据。
worktree 能力不可用时任务须写明降级方案（临时目录 clone / detached checkout）；
两者都不可行则记 non-blocking residual（写明 owner 与补救计划）。

人工前置核对：Wave 5 功能冒烟所需的后端/Mock、测试账号与权限、验证码或
二次验证的处理方式、稳定测试数据——本波逐项列给用户，逐项收
prereq:<项>:ready 或 prereq:<项>:missing；missing 的写成计划前置任务并注明
owner。这些是 Agent 查不出来的事实，只能问；缺口不得拖到 Wave 5 才暴露。
每条运行面还须核对 `entry-reachable` 前置（同域 SSO、可访问部署/静态 serve、必要
cookie/账号）。若目标不变、只需临时同域代理/测试部署，把它写成具名测试基础设施任务，
说明作用域、还原方式，并把 hosts/代理/环境修改授权并入 approve:plan；不得留给 Wave 5
临场破障。若必须降低验收层级，停止并回 Wave 2 重批；`prereq:*:missing` 不能授权降级。

实现闸门只问一次（High 附代价/风险/回滚摘要，并把回滚演练所需的临时
worktree/git 操作授权一并在此询问）。用户回复 approve:plan 放行；要改哪项先写
override:<项>:<值> 再 approve:plan。go 必须绑定当前 artifact_revision 与仓库
revision。然后停止。下一步 Wave 4。
```

## 5. Wave 4：Delivery Execute

本波 token 速查：仅工作区冲突时使用 `resolve:workdir:stash|commit|include`；
规格/计划不对时输出 backflow，不在本波发明覆盖 token。

启动本 Wave（全新会话，或上波停止后经用户重新授权的同一会话）时粘贴
「每波必贴」和「Wave 2–5 追加」，再粘贴：

```text
本波：显式使用 delivery-execute-verify。它是唯一应用代码 mutation owner。
无绑定当前 revision 的实现 go：停止，不要编辑。

应已存在：design/tasks、Plan handoff、绑定当前 revision 的实现 go。缺失则回 Wave 3。
先读 CONFIG；target_vue_version 或派生路径与通用头不一致时停止，回 Wave 2。
visual=required 时，计划中必须有基线任务；基线须在本波首次依赖/代码 mutation 前捕获
并绑定当时 revision，而不是要求 Wave 3 已执行基线。

首次 mutation 前检查 git status：工作区不干净时停止，让用户在三个原样选项里挑一个——
resolve:workdir:stash（建议）、resolve:workdir:commit（会把在途改动写进历史）、
resolve:workdir:include（纳入本次范围，基线 revision 随之改变）。Agent 不得代选：
否则基线与 handoff 的 revision 绑定不可复现，而且可能把别人的在途改动一并提交。
首次 install 前打印实际 node -v、package manager 版本、NODE_ENV 与
npm config get production；node 不满足已批准 target range 时停止，production
环境噪声按固定边界处置后再装。
优先 frozen install；禁止用仓库拒绝的包管理器。现在可以安装依赖并运行已命名配方。
按 tasks.md 纵向实施，只实施并勾选 Wave 4 权威区；Wave 5 区任务保持未勾选是预期
状态，不得代跑、不得勾选，也不得因它们未勾选而拒绝写出 verified handoff。
实施后、Fresh Verification 前重新 index_repository，刷新 Codebase Memory 索引。
lock digest 未变化不重复安装。

改过模板的每个 SFC 在提交进本波证据前逐文件自检：用 @vue/compiler-sfc 解析（或跑仓
内 lint）断言解析无 error，且该文件的起始标签属性没有被降级成文本节点。多行起始标签
（`<el-table` 后面跟着若干行属性）在编辑时最容易被收成单行 `<el-table>`，剩下的属性变
成模板文本——页面照常渲染，表格空着，build 与 lint 可以全绿。同一遍自检覆盖裸
`<template>` 一族：改默认槽后重新确认无属性 `<template>` 已清零（`vue/no-lone-template`
是现成的静态判据），不要靠肉眼过 diff。
计划含临时同域代理、测试部署或 hosts 映射时，只能按 approve:plan 已授权的精确作用域
执行，记录原值、启停/还原步骤与实际 capture_conditions；未授权不得临场修改系统环境。

依赖变更使用 TARGET_VUE_VERSION。安装后查询 resolved versions：vue 必须等于
TARGET_VUE_VERSION；适用的 @vue/compat、@vue/compiler-sfc、@vue/server-renderer 必须与之完全一致。
不一致则停止并按 alignment_backflow 回 Wave 3。

visual=required：升级后写 delivery-visual-evidence/v1 到 G9_ROOT 并校验。
外部分析只作 external_artifacts path/digest，不能代替 G9 final_visual_result=pass。
assessment_mode、diff_policy、structural_parity_metrics 与 capture_conditions
一律取已批准 spec 的值填写，本波不得新定或改写——改写等同单方降级 required 状态，
须按 alignment_backflow 回 Wave 2。current 采集必须复用基线的 capture_conditions。
每个 required 视觉状态必须逐个记录**实际达到的可达层**（entry-reachable /
component-shell / populated-data）；低于该状态在 Wave 2 声明的最低层时，本波不得
写 final_visual_result=pass，按 alignment_backflow 回 Wave 2 重议该状态或其分层。
这一条是 G9 最容易空转的地方：截图对比只能证明它拍到的那一层，`#app` 空壳、登录页
和未挂载的占位页两边一样「相符」，于是空白正文、顶距翻倍、重复关闭钮这类**一眼可见**
的回归会连同一个 pass 一起交出去。缺状态不是「视觉无差异」，是没验。

控制台基线：若计划中的 console-baseline 任务尚未执行，必须在本波首次依赖/代码
mutation 之前执行并落盘 EVIDENCE_ROOT/console-baseline.json；首次 mutation 之后
才发现基线缺失的，按 alignment_backflow 回 Wave 2 重议控制台基线契约，不得在升级
后的 revision 上补采充数。
本波若采集 Vue runtime 控制台证据，采集口径必须与基线和 Wave 5 完全一致（每路由
独立 fresh page，逐行标注 runtime_lane），否则三份计数不可比，还要额外解释差异。

存在 dev 运行面时，本波结束前必须证明应用在 **dev 与 build 两条运行面上都能启动
并进入主路径**，两条各留证据。只跑通一条即宣布实施完成属未完成：两条运行面的模块
解析、入口/URL 形态与 env 处理都不同，一条绿不构成另一条的证据。

不要 archive OpenSpec，不要 commit/push/PR，除非用户在本波之后另授权。

结束时输出 verification、G9、独立审查、rollback 与 handoff path/revision。
任何从 Wave 5 回流的缺陷都在本波作为 High 修复重新进入 Fresh Verification 与独立
审查；通过后仍须从头执行完整 Wave 5，不得只重跑上次失败用例。
Node 证据须含：当前基线、目标 Node 下升级前兼容性（或为何不适用）、目标 Node frozen
install/build/test、声明面一致性；临时双 Node 未满足删除条件时记 residual。
回滚演练：执行计划中的回滚演练任务（临时 worktree + 升级前 revision +
旧 lane frozen install/build），证据写入 verification。worktree 授权应已随
实现 go 一并取得，缺失则先补授权再执行；worktree 能力不可用时按计划降级
（临时目录 clone / detached checkout），仍不可行则记 non-blocking residual
（写明 owner 与补救计划），不得越权执行未授权 git 操作。
写 verification.md 与 verified handoff（overall_status=verified，
archive.status=deferred_to_openspec）。Delivery verified ≠ 仓内 verified。
不要声称仓内 verified。G9 未过则留在本波；连续 2 次 G9 fail 且无新修复方向时，
不要原地重试，按 alignment_backflow 回 Wave 2 重议 required_states 或 non-goals。
visual/G9 的 required 状态不得在本波降级；降级只能走 Wave 2 重新批准并记 DR。
说明下一步 Wave 5，然后停止。
```

## 6. Wave 5：独立功能验证

本波 token 速查：逐条 `accept:console-error:<route>:<消息类>`、
`accept:coverage-gap:<项>`；失败回流只用 `backflow:wave2|wave3|wave4`。

新会话粘贴「每波必贴」和「Wave 2–5 追加」，再粘贴：

```text
本波：显式使用 delivery-execute-verify，仅做独立新鲜验证与升级后功能验收。
不得修改应用代码，不得改 tasks 勾选，不得跑新的实施配方，不得 archive/commit/push/PR。
发现缺陷不要在本波修复。
本波执行 tasks.md 的 **Wave 5 区**；它们在 Wave 4 结束时未勾选是预期状态，本波也不去
勾选——结果逐条落在 EVIDENCE_ROOT/inrepo-verification.md，不通过 tasks 勾选体现。
Wave 5 区里出现需要改应用代码的任务时，说明分区有误，按 backflow:wave3 回流。
本波必须是全新会话；若沿用了 Wave 4 会话，停止并重新开会话。

应已存在：绑定当前 revision 的 Delivery verification.md 与 verified handoff、
Plan/Execute 工件、CONFIG；visual=required 时含 G9_ROOT 且 final_visual_result=pass。
缺失、Delivery 未 verified、或 revision 与当前仓库不一致：停止，回 Wave 4。
先读 CONFIG；target_vue_version 或派生路径与通用头不一致时停止，回 Wave 2。

不要采信 Wave 4 会话结论或旧 pass 日志。以当前磁盘工件 + 本会话新跑命令为准。
图谱 revision 与当前仓库不一致时先 index_repository，再取证。

按当前 revision 启动干净服务（不要复用 Wave 4 残留进程）。运行面是**两条**，不是
二选一：workspace 存在 dev 运行面时，dev server 与 build 产物静态 serve 各跑一遍，
每条独立启动、独立采证。只跑其中一条不构成本波通过，也不得在结论里把一条运行面的
结果表述为整体 verified。
lock digest 未变化不重复安装；Node/包管理器或 lock 变化时 frozen install。
首次启动前打印实际 node -v、包管理器版本、NODE_ENV 与 npm config get production；
node 不满足已批准 target range 时停止，production 环境噪声按固定边界处置后再装。

必须在本会话重跑并阅读完整输出：
- ANALYSIS_ROOT/upgrade-summary.json 的 named_validations
- 已批准 spec 的 Requirement/Scenario
- 任务列出的验证命令
vue resolved version 必须仍等于 TARGET_VUE_VERSION；适用的
@vue/compat / @vue/compiler-sfc / @vue/server-renderer 必须与之完全一致。

功能冒烟（pages 空=全仓代表入口/路由；pages 有值=这些页面+闭包）：
已批准验收场景、登录后主路径、路由切换、列表/表单/弹层等规格点名交互。
每条运行面各跑一遍同一份冒烟清单——dev 与 build 的模块解析、入口/URL 形态、
env 分支都不同，一条运行面的通过不构成另一条的证据。
每个场景记录实际达到的可达层：entry-reachable / component-shell /
populated-data。存在 dev 运行面时，dev 与 build 每条运行面至少一个代表入口必须越过
登录/路由占位并真实挂载迁移组件；`#app` 空、登录页、项目不存在或其他占位页均未达到
entry-reachable，不能用 accept:coverage-gap 豁免，也不能声称仓内 verified。
同时记录控制台全量输出：error 与升级相关 warning 不得无处置。**「升级相关」按
发出方判定，不按记得住的消息清单判定**——四类发出方全部在内：Vue 框架自身
（compat、filters、已移除实例 API、指令用在非元素根组件上等）、目标 UI 库自身的
弃用告警（迁移后落在目标大版本已弃用的 API 上，按 mount 刷量）、构建/样式工具链
自身的弃用告警（样式编译器 `@import` 等，按编译刷量）、以及**基线里没有的任何
消息**（不论发出方，先按 regression 处置）。按消息类去重计数，不抽样：一条按 mount
刷屏的弃用告警是一个类，量大不等于严重，也不得让它把一条 error 埋掉。
控制台结论必须落盘为
EVIDENCE_ROOT/console-evidence.json（每个冒烟路由 × 每条运行面一行：route、
runtime_lane、error 数、升级相关 warning 数、warning 发出方分类计数、处置状态
resolved / config-silenced / accepted-residual），
不接受只在会话文字里"声称无异常"。采集口径固定为每路由独立 fresh page：每条路由
新开页面再挂监听，用完关闭。不得用单页面连续跳转累积监听——那会把同一条错误重复
计入多条路由，计数虚高且与基线、Wave 4 的证据不可比。
控制台结果必须与 EVIDENCE_ROOT/console-baseline.json **按同 route + 同 runtime_lane
逐条对比**，每条 error 归入 regression（基线无、升级后有）或 pre-existing（基线同
条件下已有）。没有基线对照就把某条 error 判为「环境问题/非回归」是主张而非证据，
不予接受。regression 一律须处置；pre-existing 记 non-blocking residual 并写明 owner。
warning 的合法处置只有三种：改写到未弃用的 API（resolved）；`config-silenced`——在
构建配置里**按具名弃用 id** 定点静默（样式编译器的弃用静默选项是典型），必须同时
记下该 id、理由与解除条件；`accepted-residual` 并写明 owner。禁止全局过滤控制台、
包裹 `console.*`，也禁止对 error 做任何静默。
error 记 accepted-residual 必须经用户显式批准并记录批准语句：逐条给出
route、runtime_lane、消息类、为何判定非回归，用户逐条回 accept:console-error:<route>:<消息类>
才成立。整批放行、口头「这个没事」都不成立，Agent 更不得自行接受运行时 error。交互断言（Wave 3 从 inventory 生成的
v-model 回写、`.sync` 目标 prop 身份、`$options.filters` 调用点、router 导航
（吞错覆写移除后按 name 跳转不得抛 Missing required param）、触发型插槽内容形状、
UI-kit icon class prop（真实 mount + icon/toolbar 交互）、外部全局脚本
（loaded→ready→instance→最小 round-trip）、配方交集等逐点检查）必须逐条执行并
记录结果。不得用测试已绿或静态复核代替未执行的场景。

visual=required：按当前 revision 重新校验 G9_ROOT 的 delivery-visual-evidence/v1。
基线仍是升级前捕获；必要时刷新 current/diff，不得改应用代码。刷新时必须复用已批准
spec 的 capture_conditions；assessment_mode、diff_policy 与 structural_parity_metrics
取已批准值，本波不得放宽。可达层按 Wave 2 已声明的三层与逐场景最低层判定；spec 未声明分层、
本波才发现某 required 状态在当前条件下只能取到 component-shell 的，按 fail 回流
Wave 2，不得当场记 accepted-residual。
validator 未过或 revision 不匹配：停止，回 Wave 4。

写本波 handoff 前，先把 Wave 4 的 verified handoff 复制留存为
EVIDENCE_ROOT/handoff-wave4.json（只读归档），本波 handoff 的
previous_handoff_id 指向它——handoff.json 是覆盖写，不归档就无法区分前置证据。

无论 pass 还是 fail，本波都要写一份回灌工件
EVIDENCE_ROOT/upgrade-retrospective.md，记录本次实测到的六类事实，每条附证据指针
（文件/路由/命令）与观察日期：
- codemod 实际产出特征（哪种改写是错的、错在哪、build/lint 为何没拦住）；
- **未被改写却换了语义的编译/挂载形态**：源码一字未动、两个大版本都合法，但编译产物
  或挂载后的 DOM 变了，因此 codemod 和 diff review 都看不见（裸 `<template>` 被编成
  真实元素、挂载容器不再被替换导致选择器命中两次、teleport 让原本生效的抑制规则
  失配）。这一类的共同症状是**用户一眼可见而所有闸门全绿**，写清是哪个构件、
  症状在哪条路由、最终靠什么判据发现的；
- UI 库行为差异（懒挂载、prop / icon identity / 枚举 / 事件 / 插槽契约、插槽内容形状与预期不符之处）；
- 运行面分叉（只在 dev 或只在 build 出现的问题）；
- 外部运行集成与可达性（裸全局脚本 ready/instance 时序、auth/同域环境实际达到的层）；
- 控制台弃用面（目标 UI 库与构建/样式工具链自身的告警：哪些改写消除、哪些按具名
  弃用 id 定点静默、哪些留 residual）。
它不是本波通过条件，也不改任何 Skill；它是把这次实战沉淀给下一个仓的唯一去处。
写明"依赖前须按当时选定的工具版本复核"。**append-only**：verified 之后仍可追加，
追加不改变本 change 的状态，也不需要重开波次。

已批准交互/场景因人工前置未兑现而**没能实际执行**的，逐条列出（哪一条、为什么不可得、
不验的风险是什么），由用户逐条回 accept:coverage-gap:<项> 才能计入覆盖声明；未逐条
接受的不得声称仓内 verified。该 token 仅适用于已达到 spec 允许的 entry/component-shell
后仍缺 populated-data 的场景；任何运行面未达到 entry-reachable 时一律 fail。不要把
「测试已绿」当作这些场景的替代证据。

仓内 verified 须同时满足（本波逐条核对，缺一不得声称）：
分析包 complete 且交接时 gate=ready；路径仍是原地升；规格批准与实现 go 绑定当前
revision；tasks.md 的 Wave 4 权威区任务完成（Wave 5 区任务由本波逐条执行并落盘
inrepo-verification.md，未勾选不构成缺口）；Wave 4 已写出绑定当前 revision 的 Delivery verification
与 verified handoff；Wave 4 Fresh Verification 与 High 独立审查通过；本波在全新
会话对当前 revision 重跑 named_validations、规格场景与升级后功能冒烟，且不混用
Wave 4 旧 pass；visual=required 时 G9 pass 且 required 状态未被任何 Wave 单方降级
（assessment_mode / diff_policy / structural_parity_metrics 仍是 Wave 2 已批准的值，
current 与基线同 capture_conditions）；回滚演练证据存在（升级前 revision 在旧 lane
frozen install/build 通过）；存在 dev 运行面时 dev 与 build 两条运行面各自独立跑过
完整冒烟并各有证据；console-evidence.json 按每路由 × 每运行面 fresh page 口径采集，
且已与 console-baseline.json 同 route 同 runtime_lane 逐条对比、每条 error 归入
regression 或 pre-existing 并无未处置项；交互断言清单逐条有结果；Wave 3 记录的人工
前置全部兑现，未兑现项已逐条经 accept:coverage-gap:<项> 接受；Vue resolved version
与 TARGET_VUE_VERSION 一致；Composition 全仓重写仍在 non-goals；无 blocking residual。
并且每条应验证运行面至少一个代表入口达到 entry-reachable，所有已批准场景达到其
Wave 2 声明的最低层；coverage-gap 没有被用于豁免登录/挂载最低线。

pass：对照上列条件逐条核对，并把结论落盘
EVIDENCE_ROOT/inrepo-verification.md（逐条核对结果、console-evidence 与交互
断言指针、G9 与 named_validations 结果、绑定当前 revision）后，才能声称仓内
verified。仓内 verified ≠ 生产完成。
仍不 archive/commit/push/PR/部署。然后停止。
fail：按 alignment_backflow 输出，不要改代码，给出建议回流波次与理由，由用户回
backflow:wave2（规格/验收）、backflow:wave3（任务/验证命令/回滚）或
backflow:wave4（实现、测试、G9 或功能回归）确认。然后停止。
环境结构性不可达时按性质建议：验收目标不变、只缺已知测试 harness/同域通道 →
backflow:wave3；必须降低最低可达层或验收范围 → backflow:wave2；应用实现导致登录、
路由或组件不挂载 → backflow:wave4。不得在本波临时改 hosts/代理后继续自验。
```

## 7. 失败回流

始终使用原 `CHANGE_ID`，不创建第二个 OpenSpec change。


| 发现                                       | 返回                             |
| ---------------------------------------- | ------------------------------ |
| workspace / 拓扑选错，或应走 host-port           | Wave 1；必要时改 A→B 剧本             |
| 分析报告目标 Vue 版本错误、不可用或证据不足             | Wave 1                           |
| 分析包 repo_revision 与当前仓库漂移（分析 stale）      | Wave 1                           |
| workspace 实为已（部分）升级完成的 Vue3 仓            | 停止主线；residual-audit 或结束     |
| 目标、验收、行为 parity、视觉是否 required、pages 范围错误 | Wave 2 规格批准                    |
| 视觉契约缺项或需放宽（assessment_mode、diff_policy、结构 parity 白名单、capture_conditions、可达性三层/场景最低层） | Wave 2 规格批准 |
| 分析缺 `ui_behavior_contract` / `ui_cutover_staging` / `default_path_deviation` | Wave 1 |
| 行为断言未进已批准 spec，或被当作 G9 的一部分顺带豁免 | Wave 2 规格批准 |
| 控制台基线缺失、条件不可复现，或首次 mutation 后才发现未采 | Wave 2 规格批准（重议控制台基线契约，不得在升级后 revision 补采） |
| 任务另起第二套控制台采集器或另一种口径 | Wave 3 Plan |
| tasks.md 未分区，或实施任务被放进 Wave 5 区（表现为 Wave 5 区未勾选卡住 Wave 4 verified，两波互等） | Wave 3 Plan 重新分区并重批 `approve:plan` |
| G9 pass 建立在低于 Wave 2 声明最低可达层的状态上（只拍到 shell / 占位页） | Wave 2 规格批准；实现导致不挂载则 Wave 4 |
| 运行面覆盖不全（只验证了 dev 或只验证了 build 产物） | Wave 3 Plan 补任务；已实施则 Wave 4 补跑另一条运行面 |
| Wave 3 人工前置未兑现，导致已批准交互无法执行 | Wave 3 Plan；确实不可得时回 Wave 2 重议验收范围 |
| auth/同域环境结构性不可达，但验收目标不变、可增加测试 harness | Wave 3 Plan：具名代理/测试部署任务与授权；有环境 mutation 时由 Wave 4 执行 |
| auth wall 导致任一运行面没有代表入口达到 entry-reachable | 不得 `accept:coverage-gap`；harness 缺失回 Wave 3，规格必须降级则回 Wave 2，实现回归则回 Wave 4 |
| 组件已挂载但 populated-data 不可得 | 仅当 Wave 2 已批准数据层降级时可逐项 `accept:coverage-gap`；否则回 Wave 2 |
| CONFIG / 已批准规格中的 target_vue_version 不一致      | Wave 2                           |
| 配方拆分、回滚、基线时机、任务范围错误                      | Wave 3 Plan                    |
| 已批准范围内的实现、测试、G9 或功能回归                   | Wave 4 Execute                 |
| 连续 2 次 G9 fail 且无新修复方向（重议 required_states / non-goals） | Wave 2 规格批准          |
| Wave 5 发现 Delivery 未 verified 或证据 stale | Wave 4 Execute                 |
| Wave 5 发现实现缺陷 | Wave 4 修复 + Fresh Verification + High 独立审查，然后完整重跑 Wave 5 |
| OpenSpec / Memory 硬前提失败                  | 停在当前 Delivery Wave，按三行报告恢复后再继续 |
| 分析 gate 仍 frozen 却进入 Wave 2              | 回 Wave 1                       |


回流携带：

```text
alignment_backflow:
  discovery / evidence / affected_scope / invalidated_artifacts /
  decision_needed / recommended_resolution / resume_point
```

规格或计划变更后，必须重跑受影响闸门。Wave 4 修复后必须重跑受影响任务的 Fresh
Verification，并重新执行完整 Wave 5；不得用 Wave 4 旧 pass 声称仓内 verified。

## 8. 完成判定

唯一权威清单是 Wave 5 粘贴块中「仓内 verified 须同时满足」的逐项条件；本章不再
维护第二份副本，避免两份规则漂移。通读时按以下索引回看 Wave 5：工件/revision 与
精确版本、Fresh Verification + High 独立审查、dev/build 双运行面、每条运行面的
entry-reachable 最低线、`console-evidence`、逐点交互断言、G9、回滚演练、人工
前置与合法 coverage gap、Node 声明面、non-goals 和 blocking residual。

只有 Wave 5 把该权威清单逐项落盘到 `EVIDENCE_ROOT/inrepo-verification.md` 后，才能
声称仓内 `verified`。此时仍不自动 archive、commit、push、PR、部署或生产切流。

## 9. verified 之后

仓内 verified 是本剧本的完成水位，**不新增运维波次**：一个开放式的"清退波次"没有
终止条件，实际效果是让 change 永远开着。但 verified 之后用户真实使用中冒出来的问题
需要一条合法通道，否则它们既回不到配方库、也没人认领。按性质二分，只有两条出口：

| verified 之后的发现 | 出口 | 用户原样回复 |
|---|---|---|
| 阻断、回归、或需要改应用代码 | 新开一个 change 走 Wave 2–5（新 `CHANGE_ID`；不得回改已 verified 的 change，也不得在无规格批准的情况下直接改代码） | `open:new-change` |
| 非阻断的控制台噪声、弃用告警、已记 residual 的项 | 追加到 `EVIDENCE_ROOT/upgrade-retrospective.md`（append-only，带观察日期与证据指针），并作为下一个仓 Wave 1 的输入 | `append:retrospective` |

归入哪一类由用户定，Agent 只给建议与理由：把阻断项误归成 retrospective 追加，等于
让一个真回归没有 owner 地留在仓里。

追加时按 Wave 5 的六类事实归类，`config-silenced` 的具名弃用 id 与解除条件一并记下。
这类发现**不表示 Wave 1–5 跑得不严**，而是分析期的建模面没覆盖到该破坏面；因此
追加的价值在于让下一个仓的 Wave 1 把它当成已知面来扫，而不是在这个仓重开波次。
若同一类发现在两个仓复现，那是分析 Skill 的信号或控制台分类该扩的证据，不是剧本
该加波次的证据。

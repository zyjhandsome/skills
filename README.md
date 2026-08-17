# skills

Cursor Agent Skills 集合。按用途分类如下。

## 交付流水线

四个 skill 按阶段串联（探索可选）；共享契约与脚本集中在 `delivery-frame-spec/`（四 skill 原子安装）。家族版本见 `delivery-frame-spec/references/family-contract.md`（当前 `delivery-family/1.6`）。

```
delivery-explore  →  delivery-frame-spec  →  delivery-plan-tasks  →  delivery-execute-verify
     （可选）              （默认入口）            （Standard/High）           （实现与验收）
```

| 技能 | 说明 |
|------|------|
| [delivery-explore](./delivery-explore/SKILL.md) | 交付探索：机会地图与方向选型（不实现、不立项） |
| [delivery-frame-spec](./delivery-frame-spec/SKILL.md) | 交付立项：路由 / 澄清 / Brief·Spec 闸门 |
| [delivery-plan-tasks](./delivery-plan-tasks/SKILL.md) | 交付规划：design / tasks / 实现闸门（不实现） |
| [delivery-execute-verify](./delivery-execute-verify/SKILL.md) | 交付实施与验证：按任务实现、调试、新鲜证据验收 |

归档仍交给 OpenSpec（`/opsx-archive` / `openspec-archive-change`），不在 execute 技能内完成。  
**现行自检：** `node delivery-frame-spec/tests/run_all.mjs`（`delivery-execute-verify/tests/legacy/` 仅为历史 prompt 对照，非验收）。

## 依赖升级影响分析

三个独立 skill：只分析、不实现；互不接力，也不内置挂接交付流水线。可单独调用；也可用下方提示词与 `delivery-frame-spec` 软挂载（frame 建/恢复 OpenSpec change，分析 skill 只写 `evidence/`）。报告可写入已有 change 的 `evidence/`，或用 `--output-dir`。

| 技能 | 说明 |
|------|------|
| [frontend-dependency-upgrade-impact-analysis](./frontend-dependency-upgrade-impact-analysis/SKILL.md) | 前端依赖升级影响分析：证据驱动的升级/移除/替换决策报告；A→B 迁入时可用 `migration-demand-diff` |
| [java-dependency-upgrade-impact-analysis](./java-dependency-upgrade-impact-analysis/SKILL.md) | Java/Maven/Gradle 依赖升级影响分析：处置阶梯、owner-first、确认队列决策包 |
| [vue2-to-vue3-upgrade-impact-analysis](./vue2-to-vue3-upgrade-impact-analysis/SKILL.md) | Vue 2→Vue 3 框架升级影响分析：迁移路径、子系统风险、确认队列；单仓原地升默认 `compat-big-bang`，A→B 分析默认 `host-port-direct` |

`vue2-to-vue3-upgrade-impact-analysis` 覆盖框架切仓决策（路径三维 + 子系统耦合 + Vue2 API 盘点），不是把 `vue` 当成又一个包来升。包级 from→to 仍走 frontend-dependency。A→B **实施**（改 B、视觉证据、iframe 退出）走下方 `migrate-vue2-pages-to-vue3-host`，不要用本 skill 改代码。

### 与 delivery-* 联用（短提示词）

分析定稿后，仅当 `batch_implementation_gate=ready` 且你显式 go，再进入实施。  
**单仓原地升**不要同一会话从分析接到 Execute，按
[`docs/vue2-to-vue3-inplace-upgrade-playbook.md`](./docs/vue2-to-vue3-inplace-upgrade-playbook.md)
分波粘贴。Java 依赖挂载仍见
[`docs/java-dependency-upgrade-delivery-usage.md`](./docs/java-dependency-upgrade-delivery-usage.md)。

**前端依赖**

```text
/delivery-frame-spec 结合 /frontend-dependency-upgrade-impact-analysis
对以下依赖做升级影响分析（只出决策包，不改代码）。
项目：<仓库或前端 workspace>
目标：
- axios:1.6.0:1.7.9
- <开放目标包名>  # 或：移除/替换说明
```

**Java 依赖**

```text
/delivery-frame-spec 结合 /java-dependency-upgrade-impact-analysis
对以下依赖做升级影响分析（只出决策包，不改代码）。
项目：<仓库路径>
目标：
- <groupId:artifactId:from:to>
# 或写：整仓巡检，先候选再问我选批
```

**Vue2→Vue3（单仓原地升，只分析）**

```text
/vue2-to-vue3-upgrade-impact-analysis
做 Vue2→Vue3 升级影响分析（只出决策包，不改代码/不跑 codemod）。
项目：<前端 workspace>
--output-dir <前端 workspace>/.vue2-to-vue3-upgrade-analysis
# 或多仓：多仓巡检，先候选再问我选批
```

要做到仓内 `verified`（测试 + 需要时的视觉 G9，不含生产发布）：不要把 Frame /
Plan / Execute 焊进上面这一条。按
[`docs/vue2-to-vue3-inplace-upgrade-playbook.md`](./docs/vue2-to-vue3-inplace-upgrade-playbook.md)
分波粘贴（分析 → Frame 规格批准 → Plan go → Execute；样式残差才开视觉 Skill）。

**Vue2→Vue3（A→B 只分析）**

```text
/vue2-to-vue3-upgrade-impact-analysis
做 A→B host-port 影响分析（只出决策包）。
source_root：<Vue2 仓 A>
implementation_target：<Vue3 host B>
forbid_source_mutation: yes
# 默认路径 host-port-direct；compat 非主路径
```

配套说明：

- [`docs/frontend-dependency-upgrade-impact-analysis-usage.md`](./docs/frontend-dependency-upgrade-impact-analysis-usage.md)
- [`docs/java-dependency-upgrade-impact-analysis-usage.md`](./docs/java-dependency-upgrade-impact-analysis-usage.md)
- [`docs/java-dependency-upgrade-delivery-usage.md`](./docs/java-dependency-upgrade-delivery-usage.md)（与 delivery-* 可选挂载）
- [`docs/vue2-to-vue3-upgrade-impact-analysis-usage.md`](./docs/vue2-to-vue3-upgrade-impact-analysis-usage.md)（Vue2 分析-only）
- [`docs/vue2-to-vue3-inplace-upgrade-playbook.md`](./docs/vue2-to-vue3-inplace-upgrade-playbook.md)（单仓原地升到仓内 verified；每步独立会话）

## Vue2 页面迁入 Vue3 Host

独立领域 skill：把 Vue2 源仓 A 的可切换用户行为（通常是一页）迁入已有 Vue3 宿主仓 B。默认 A 只读、B 壳保持 host-native、迁入内容 strict parity、视觉证据必做；只有 `assess` / `design` / `verify`，不改应用代码。不依赖、不调用 `delivery-*`；需要生命周期时按粘贴剧本组合 delivery。

| 技能 | 说明 |
|------|------|
| [migrate-vue2-pages-to-vue3-host](./migrate-vue2-pages-to-vue3-host/SKILL.md) | 跨仓页面迁移：页面闭包、Vuex→Pinia / Element UI→Plus 适配、iframe 退出、视觉与 runtime 证据 |

**不要**用它做「单仓把 Vue2 原地升到 Vue3」。单仓原地升的决策包走 `/vue2-to-vue3-upgrade-impact-analysis`（只分析）；改代码并验收按
[`docs/vue2-to-vue3-inplace-upgrade-playbook.md`](./docs/vue2-to-vue3-inplace-upgrade-playbook.md)。

A→B 不要混用职责：host-port **决策包**可用 vue 分析 skill；**页面迁入、iframe 退出**用本 skill。升级后「功能可用但搜索/表格/表单样式仍乱」走 `/frontend-ui-stack-visual-parity`（默认只定界，明确 go 后再改 CSS/配置）。

```text
/migrate-vue2-pages-to-vue3-host
依次执行 assess 和 design（本阶段不改应用代码）。
源仓 A：<Vue2 仓库>
宿主仓 B：<已有 Vue3 仓库>
migration_unit：
- source_entry：<A 的页面/入口文件>
- host entry：<B 的 route 或 HTML 入口>
# 缺具体入口就停，不要编占位
A 只读；B 壳 host-native；内容区 strict parity；visual=required
```

### 与 delivery-* 联用

不要在同一会话里把 Frame 和 migrate 焊在一起。按
[`docs/vue2-page-migration-playbook.md`](./docs/vue2-page-migration-playbook.md)
分波粘贴：先建 change（无规格闸门），再 assess / design，然后 Frame 规格批准、
Plan go、Execute，最后 migrate `verify`。

集成路线下，代码修改由 `delivery-execute-verify` 唯一拥有；migrate skill 只跑 `verify` 刷新领域证据。

配套说明：

- [`docs/vue2-page-migration-playbook.md`](./docs/vue2-page-migration-playbook.md)（A→B 用户粘贴剧本；每步独立会话）
- [`docs/migrate-vue2-pages-to-vue3-host-delivery-usage.md`](./docs/migrate-vue2-pages-to-vue3-host-delivery-usage.md)（解耦原则与交接字段；顺序以剧本为准）

## UI 栈视觉 parity（升级后样式）

独立 skill：针对「功能基本可用、搜索/表格/表单样式仍乱」做定界；也用于 A→B 迁入后与源仓 A 的样式对齐。**默认不改代码**，仅在用户对当前定界包明确 go 后允许改 CSS/配置（不装包、不升依赖、不重开 Vue2→3 路径选择；跨仓时只改 candidate/host）。

| 技能 | 说明 |
|------|------|
| [frontend-ui-stack-visual-parity](./frontend-ui-stack-visual-parity/SKILL.md) | UI 栈视觉 parity：Tailwind Preflight×Element 等共存定界；go 后最小 CSS/配置修复 |

```text
/frontend-ui-stack-visual-parity
项目：<前端 workspace>
# 可选：最差的 1～2 个列表页路由或文件
# 跨仓：baseline=源仓 A，candidate=Vue3 host B
# Phase A 只定界；回复「开始修复」等明确 go 后再改 CSS/配置
```

## 内容整理与发布

| 技能 | 说明 |
|------|------|
| [content-structuring](./content-structuring/SKILL.md) | 内容结构化整理（源材料→中文深度整理稿；v5.28 含过译护栏） |
| [ai-agent-update-brief](./ai-agent-update-brief/SKILL.md) | AI 编码 Agent / IDE / CLI 工具更新简报生成 |
| [github-repo-usage-article](./github-repo-usage-article/SKILL.md) | GitHub 仓库「使用示例」深度文章（房屋风格） |
| [md2html-lecture](./md2html-lecture/SKILL.md) | 将 content-structuring 的整理稿转换成单文件 HTML 阅读页 |
| [md2wechat](./md2wechat/SKILL.md) | 整理文档 MD → 微信公众号内联 HTML + 2.35:1 封面；含 build/validate 脚本 |

### md2html-lecture：把整理稿渲染成网页

`md2html-lecture` **基于 [content-structuring](./content-structuring/SKILL.md) 输出的格式结果**进行转换：它读取该技能产出的「对谈三层结构」整理稿
（`# 标题` / `## 文章元数据` / `## 核心导读` / 多个 `## 小节`，通常含 `核心洞察 · 深度解析`，`对谈实录` 可按 content-structuring 规则省略 / `## 延伸术语表` / `## 自检报告`），
生成一个自包含的单文件 HTML 阅读页：Claude 橙色主题、亮/暗双色、侧边目录、层级标签、对谈时间线、callout、Mermaid 流程图支持，
术语表与元数据默认折叠。

用法：

```bash
python md2html-lecture/scripts/build_html.py "path/to/<整理文档>.md"
```

结构转换是确定性的、由脚本完成；Mermaid 流程图不在源 Markdown 中，需转换后按小节手动补充（详见 `md2html-lecture/SKILL.md`）。

### md2wechat：整理文档 → 公众号粘贴稿 + 封面

`md2wechat` 把 content-structuring 产出的 `*_整理文档.md` 转成**可粘贴进微信公众号**的内联样式 HTML，并生成 **2.35:1** 封面 PNG。默认保留正文三层结构；去掉元数据表、目录、术语表、自检报告。

用法：

```bash
python md2wechat/scripts/build_wechat_html.py "path/to/<整理文档>.md"
python md2wechat/scripts/make_cover_235.py "cover-src.png" --out "<stem>_公众号封面_2.35x1.png"
python md2wechat/scripts/validate_wechat_bundle.py "<stem>_公众号完整版.html" --cover "<stem>_公众号封面_2.35x1.png"
```

详见 `md2wechat/SKILL.md`。


## 目录结构

```
delivery-explore/
├── SKILL.md
└── references/
    └── explore-output-template.md

delivery-frame-spec/                    # 家族枢纽（共享 references + scripts + tests）
├── SKILL.md
├── references/
│   ├── family-contract.md              # 版本 / 硬软前提 / 链式接力
│   ├── handoff-contract.md
│   ├── handoff-template.md             # 四阶段共用
│   ├── batch-clarification.md
│   ├── method-discipline-inline.md     # Superpowers 软依赖回退
│   ├── openspec-adapter.md
│   ├── routing-and-gates.md
│   ├── brief-template.md
│   ├── spec-template.md
│   ├── explore-handoff-consume.md
│   └── …
├── scripts/
│   ├── validate_handoff.mjs
│   ├── delivery_scaffold.mjs
│   └── hash_change_artifacts.mjs
└── tests/
    ├── run_all.mjs                     # 一键自检入口
    └── fixtures/

delivery-plan-tasks/
├── SKILL.md
└── references/
    ├── plan-template.md
    ├── readiness-review.md
    └── tasks-template.md

delivery-execute-verify/
├── SKILL.md
├── references/
│   ├── artifact-gate-checks.md
│   ├── implementation-loop.md
│   ├── subagent-orchestration.md
│   └── verification-template.md
├── scripts/
│   └── validate_delivery_change.mjs
└── tests/
    ├── test_template_anchor_consistency.mjs
    └── legacy/                         # 非现行验收

frontend-dependency-upgrade-impact-analysis/
├── SKILL.md              # 技能加载器（边界、工作流、报告闸门）
├── agents/
│   └── openai.yaml
├── fixtures/             # 合成前端 fixture（测试用）
├── references/           # 证据 schema、风险模型、迁入差分、报告契约等
├── scripts/              # 报告生成、Node 兼容探测、migration-demand-diff
└── tests/

java-dependency-upgrade-impact-analysis/
├── SKILL.md              # 技能加载器（边界、环境前置、工作流、报告闸门）
├── agents/
│   └── openai.yaml
├── fixtures/             # 决策包样例（partial / complete）
├── references/           # 处置阶梯、owner、拆批、确认队列、报告契约等
├── scripts/              # validate_report.py 结构校验
├── templates/            # 决策包 / 决策记录中文模板
└── tests/

vue2-to-vue3-upgrade-impact-analysis/
├── SKILL.md              # 技能加载器（原地升 / host-port、工作流、报告闸门）
├── agents/
│   └── openai.yaml
├── fixtures/             # 决策包样例（partial / complete / host-port）
├── references/           # 迁移路径、子系统清单、确认闸门、报告契约等
├── scripts/              # preflight / profile_inventory / validate_report
├── templates/            # 决策包 / 决策记录中文模板
└── tests/

migrate-vue2-pages-to-vue3-host/
├── SKILL.md              # 技能加载器（模式、闭包、授权、视觉/runtime 闸门）
├── agents/
│   └── openai.yaml
├── references/           # 页面闭包、Vue 变换、host 切片、视觉/runtime、领域包
├── scripts/              # validate_domain_packet / visual / runtime
└── tests/

frontend-ui-stack-visual-parity/
├── SKILL.md              # 技能加载器（Phase A 定界 / Phase B CSS 闸门）
├── agents/
│   └── openai.yaml
├── fixtures/             # 报告与 summary 样例（含 cross-repo）
├── references/           # 配置盘点、诊断流程、捕获契约、验证清单
├── scripts/              # validate_visual_report / validate_visual_summary
├── templates/
└── tests/

content-structuring/
├── SKILL.md              # 加载器（v5.28）
├── fixtures/             # 迷你金样（闸门回归）
├── references/
│   ├── spec.md           # 单一事实来源
│   └── over-translation-guard.md  # Skill/Creator 等过译护栏
└── scripts/
    ├── normalize_spacing.py  # 4d
    ├── check_4c.py           # 4c 裸词辅助
    └── tests/test_gates.py

ai-agent-update-brief/
└── SKILL.md              # AI Agent 工具更新简报规范

github-repo-usage-article/
├── SKILL.md              # 技能加载器（工作流、五件套、验收闸门、防模板污染）
├── TEMPLATE.md           # 带注释的文章骨架模板
├── EXAMPLE.md            # 黄金范例（Codebase Memory MCP 使用示例全文）
└── fix-beginner-sections.py  # 批量修正常见新手专区 MCP 模板污染

md2wechat/
├── SKILL.md
├── examples.md
├── reference-wechat-constraints.md
└── scripts/
    ├── build_wechat_html.py
    ├── make_cover_235.py
    └── validate_wechat_bundle.py

md2html-lecture/
├── SKILL.md              # 技能加载器（工作流、MD 格式约定、验收清单）
├── assets/
│   └── template.html     # 单文件 HTML 模板（CSS/JS + 占位符）
└── scripts/
    └── build_html.py     # 确定性的 MD → HTML 转换脚本（仅依赖标准库）
```

安装：将需要的技能目录复制到项目的 `.cursor/skills/` 或 `~/.cursor/skills/` 即可。

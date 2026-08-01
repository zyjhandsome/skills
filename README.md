# skills

Cursor Agent Skills 集合。按用途分类如下。

## 交付流水线

四个 skill 按阶段串联（探索可选）；共享契约与脚本集中在 `delivery-frame-spec/`（四 skill 原子安装）。家族版本见 `delivery-frame-spec/references/family-contract.md`（当前 `delivery-family/1.4`）。

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

三个独立 skill：只分析、不实现；互不接力，也不挂接交付流水线。可单独调用；报告可写入已有 OpenSpec change 的 `evidence/`，或用 `--output-dir`。

| 技能 | 说明 |
|------|------|
| [frontend-dependency-upgrade-impact-analysis](./frontend-dependency-upgrade-impact-analysis/SKILL.md) | 前端依赖升级影响分析：证据驱动的升级/移除/替换决策报告 |
| [java-dependency-upgrade-impact-analysis](./java-dependency-upgrade-impact-analysis/SKILL.md) | Java/Maven/Gradle 依赖升级影响分析：处置阶梯、owner-first、确认队列决策包 |
| [vue2-to-vue3-upgrade-impact-analysis](./vue2-to-vue3-upgrade-impact-analysis/SKILL.md) | Vue 2→Vue 3 框架升级影响分析：迁移路径、子系统风险、确认队列决策包 |

配套说明：

- [`docs/frontend-dependency-upgrade-impact-analysis-usage.md`](./docs/frontend-dependency-upgrade-impact-analysis-usage.md)
- [`docs/java-dependency-upgrade-impact-analysis-usage.md`](./docs/java-dependency-upgrade-impact-analysis-usage.md)
- [`docs/java-dependency-upgrade-delivery-usage.md`](./docs/java-dependency-upgrade-delivery-usage.md)（与 delivery-* 可选挂载）
- [`docs/vue2-to-vue3-upgrade-impact-analysis-usage.md`](./docs/vue2-to-vue3-upgrade-impact-analysis-usage.md)
- [`docs/vue2-to-vue3-upgrade-delivery-usage.md`](./docs/vue2-to-vue3-upgrade-delivery-usage.md)（与 delivery-* 可选挂载）

## 内容整理与发布

| 技能 | 说明 |
|------|------|
| [content-structuring](./content-structuring/SKILL.md) | 内容结构化整理 |
| [ai-agent-update-brief](./ai-agent-update-brief/SKILL.md) | AI 编码 Agent / IDE / CLI 工具更新简报生成 |
| [github-repo-usage-article](./github-repo-usage-article/SKILL.md) | GitHub 仓库「使用示例」深度文章（房屋风格） |
| [md2html-lecture](./md2html-lecture/SKILL.md) | 将 content-structuring 的整理稿转换成单文件 HTML 阅读页 |

### md2html-lecture：把整理稿渲染成网页

`md2html-lecture` **基于 [content-structuring](./content-structuring/SKILL.md) 输出的格式结果**进行转换：它读取该技能产出的「对谈三层结构」整理稿
（`# 标题` / `## 文章元数据` / `## 核心导读` / 多个 `## 小节`，每节含 `核心洞察 · 深度解析 · 对谈实录` / `## 延伸术语表` / `## 自检报告`），
生成一个自包含的单文件 HTML 阅读页：Claude 橙色主题、亮/暗双色、侧边目录、层级标签、对谈时间线、callout、Mermaid 流程图支持，
术语表与元数据默认折叠。

用法：

```bash
python md2html-lecture/scripts/build_html.py "path/to/<整理文档>.md"
```

结构转换是确定性的、由脚本完成；Mermaid 流程图不在源 Markdown 中，需转换后按小节手动补充（详见 `md2html-lecture/SKILL.md`）。

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
├── references/           # 证据 schema、风险模型、报告契约等
├── scripts/              # 报告生成与 Node 兼容探测
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
├── SKILL.md              # 技能加载器（边界、环境前置、工作流、报告闸门）
├── agents/
│   └── openai.yaml
├── fixtures/             # 决策包样例（partial / complete）
├── references/           # 迁移路径、子系统清单、确认闸门、报告契约等
├── scripts/              # preflight / profile_inventory / validate_report
├── templates/            # 决策包 / 决策记录中文模板
└── tests/

content-structuring/
├── SKILL.md              # 技能加载器
└── references/
    └── spec.md           # 完整规范（模板、验收闸门、术语校准等）

ai-agent-update-brief/
└── SKILL.md              # AI Agent 工具更新简报规范

github-repo-usage-article/
├── SKILL.md              # 技能加载器（工作流、五件套、验收闸门、防模板污染）
├── TEMPLATE.md           # 带注释的文章骨架模板
├── EXAMPLE.md            # 黄金范例（Codebase Memory MCP 使用示例全文）
└── fix-beginner-sections.py  # 批量修正常见新手专区 MCP 模板污染

md2html-lecture/
├── SKILL.md              # 技能加载器（工作流、MD 格式约定、验收清单）
├── assets/
│   └── template.html     # 单文件 HTML 模板（CSS/JS + 占位符）
└── scripts/
    └── build_html.py     # 确定性的 MD → HTML 转换脚本（仅依赖标准库）
```

安装：将需要的技能目录复制到项目的 `.cursor/skills/` 或 `~/.cursor/skills/` 即可。

# skills

Cursor Agent Skills 集合。

| 技能 | 说明 |
|------|------|
| [delivery-explore](./delivery-explore/SKILL.md) | 交付探索：机会地图与方向选型（不实现、不立项） |
| [delivery-frame-spec](./delivery-frame-spec/SKILL.md) | 交付立项：路由 / 澄清 / Brief·Spec 闸门 |
| [delivery-plan-tasks](./delivery-plan-tasks/SKILL.md) | 交付规划：design / tasks / 实现闸门（不实现） |
| [delivery-execute-verify](./delivery-execute-verify/SKILL.md) | 交付实施与验证：按任务实现、调试、新鲜证据验收 |
| [content-structuring](./content-structuring/SKILL.md) | 内容结构化整理 |
| [ai-agent-update-brief](./ai-agent-update-brief/SKILL.md) | AI 编码 Agent / IDE / CLI 工具更新简报生成 |
| [github-repo-usage-article](./github-repo-usage-article/SKILL.md) | GitHub 仓库「使用示例」深度文章（房屋风格） |
| [md2html-lecture](./md2html-lecture/SKILL.md) | 将 content-structuring 的整理稿转换成单文件 HTML 阅读页 |

## Delivery 流水线

四个 skill 按阶段串联（探索可选）：

```
delivery-explore  →  delivery-frame-spec  →  delivery-plan-tasks  →  delivery-execute-verify
     （可选）              （默认入口）            （Standard/High）           （实现与验收）
```

归档仍交给 OpenSpec（`/opsx-archive` / `openspec-archive-change`），不在 execute 技能内完成。

目录结构：

```
delivery-explore/
├── SKILL.md
└── references/
    ├── explore-output-template.md
    └── handoff-template.md

delivery-frame-spec/
├── SKILL.md
└── references/
    ├── batch-clarification.md
    ├── brief-template.md
    ├── clarification-example.md
    ├── handoff-template.md
    ├── routing-and-gates.md
    └── spec-template.md

delivery-plan-tasks/
├── SKILL.md
└── references/
    ├── handoff-template.md
    ├── plan-template.md
    ├── readiness-review.md
    └── tasks-template.md

delivery-execute-verify/
├── SKILL.md
└── references/
    ├── artifact-gate-checks.md
    ├── handoff-template.md
    ├── implementation-loop.md
    ├── subagent-orchestration.md
    ├── subagent-orchestration-test.md
    ├── verification-template.md
    └── workflow-system-regression-test.md

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

## md2html-lecture：把整理稿渲染成网页

`md2html-lecture` **基于 [content-structuring](./content-structuring/SKILL.md) 输出的格式结果**进行转换：它读取该技能产出的「对谈三层结构」整理稿
（`# 标题` / `## 文章元数据` / `## 核心导读` / 多个 `## 小节`，每节含 `核心洞察 · 深度解析 · 对谈实录` / `## 延伸术语表` / `## 自检报告`），
生成一个自包含的单文件 HTML 阅读页：Claude 橙色主题、亮/暗双色、侧边目录、层级标签、对谈时间线、callout、Mermaid 流程图支持，
术语表与元数据默认折叠。

用法：

```bash
python md2html-lecture/scripts/build_html.py "path/to/<整理文档>.md"
```

结构转换是确定性的、由脚本完成；Mermaid 流程图不在源 Markdown 中，需转换后按小节手动补充（详见 `md2html-lecture/SKILL.md`）。

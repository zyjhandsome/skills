---
name: ai-agent-update-brief
description: Create standalone HTML update briefs for AI coding agents, agentic IDEs, CLI agents, developer tools, and related AI productivity tools. Use when the user asks to research changelogs, release notes, official blogs, GitHub releases, or docs updates for tools such as Cursor, OpenAI Codex, Claude Code, Claude Cowork, Antigravity CLI, Google Antigravity, Antigravity IDE, VS Code, or similar tools. If the user does not name specific tools, default to the full default tool set defined in this skill. Default report language is Chinese for both the HTML file and the chat summary, including when the user only types /ai-agent-update-brief or writes in English. Use English only if the user explicitly requests it. The output should be a clear, practical HTML report with recent updates, latest versions, official sources, real user impact, and concrete examples.
---

# AI Agent Update Brief

## Core Output Principle

Build a decision-ready brief, not a raw changelog dump. Organize updates by user scenario, explain practical impact, include concrete examples inside each tool's impact text, and cite official sources.

## Default Behavior

When the user asks for an AI agent update brief, AI coding tools report, agentic IDE report, CLI agent update, or similar research task and does not specify a tool list, treat "all tools" as the default. Do not ask for clarification just to choose tools.

Default output is a standalone HTML report saved in the current workspace. Also provide a concise Chinese chat summary with the local file link after generation.

Only produce a chat-only brief when the user explicitly asks for no file, no HTML, quick summary, or chat-only output.

## Language and Localization

**Chinese is the default language.** Write both the HTML report and the chat summary in Chinese unless the user explicitly asks for English.

This default applies even when the user only invokes `/ai-agent-update-brief`, writes the request in English, or uses English product names. Do not infer English from the slash command, the tool list, or an English workspace path.

Switch to English only when the user explicitly requests it, for example: "in English", "English report", "英文", "用英语", or "English please". If the request is mixed and does not clearly ask for English, keep Chinese.

For Chinese reports (the default):

- Set `<html lang="zh-CN">`.
- Translate all natural-language analysis, labels, table headers, navigation, status notes, source-use notes, update-pool remarks, footer caveats, and glossary explanations into Chinese.
- Keep product names, model names, commands, API names, protocol names, version numbers, URLs, and official feature names in English when translation would reduce clarity, for example `Cursor`, `Claude Tag`, `MCP`, `BYOK`, `GitHub Changelog`, `/usage`, and `AGENTS.md`.
- Do not leave English work-note phrases in the report body, such as "checked", "latest", "official releases", "No qualifying update found", "billed to organization", "spend limits", "audit logs", or "release page checked". Translate them into polished Chinese, for example "已检查", "最新版本", "官方版本页", "未找到合格更新", "计入组织账单", "支出上限", "审计日志", and "已检查版本页".
- Link text should be reader-friendly in Chinese when possible, while the underlying URL remains unchanged. For example, prefer "Codex 官方 changelog" over a bare URL unless the URL itself is the clearest label.
- Keep terminology consistent throughout the report. For example, choose "Agent" and "子 Agent" consistently instead of mixing "agent", "subagent", and "Subagent" in natural-language sentences.
- Use these default Chinese section titles: 核心结论、建议动作、工程自动化、多 Agent / 子 Agent、权限安全与破坏性变更、模型配额与成本、按任务选工具、联合更新池、官方来源、术语表.
- After the HTML is written, run a localization pass over visible text. Source notes, update-pool remarks, glossary rows, and footer caveats are easy to leave half-English.
- Before finalizing, scan visible text for stray English fragments. Leave only deliberate English product/feature names, commands, URLs, and technical identifiers.

For English reports (explicit request only):

- Use English for all natural-language analysis, labels, notes, and the chat summary.
- Keep the same structure, inclusion rule, and official-source standard.
- Set `<html lang="en">`.

## Default Tool Set

Cover this full set by default unless the user narrows or expands the list:

- Cursor
- OpenAI Codex
- Claude Code
- Claude Cowork
- Claude Tag / Claude in Slack
- Gemini CLI
- Antigravity CLI
- Google Antigravity / Antigravity IDE
- VS Code and GitHub Copilot coding agent capabilities
- Windsurf
- JetBrains AI Assistant and Junie
- Aider
- Continue
- Sourcegraph Amp
- Factory Droid
- Devin
- Replit Agent
- GitHub Copilot Workspace or related GitHub agentic coding updates

If an item has no official updates available under the inclusion rule, keep it in the report with an explicit note and cite the official page checked when possible. Default wording: "未找到合格官方更新". Use "No qualifying official update found" only in an English report.

## Research Rules

1. Browse the web because release notes, model support, pricing, quotas, and tool availability change frequently.
2. Prefer official sources in this order:
 - Official changelog or release notes
 - Official docs
 - GitHub Releases from the official repository
 - Official blog or support article
 - Secondary sources only when official sources are unavailable, and label them clearly
3. Capture source URL and publication date for each included update.
4. Treat client-rendered official pages as usable official sources if their page resources contain version data. Note this in the final source notes.
5. For OpenAI product information, use official OpenAI sources only unless the user requests otherwise.
6. Do a capability-surface sweep for products whose agent updates may ship outside classic changelogs. Search official help centers, docs collections, connector/integration pages, team/enterprise capability pages, and official social/blog launch pages for new agent surfaces such as Slack agents, group/channel agents, mobile dispatch, browser/desktop agents, connectors, and admin controls. This is required for Claude, GitHub Copilot, Replit, Devin, and similar suite products.
7. Search by product-family aliases and user-facing feature names, not only by tool names. For example, for Anthropic search Claude Code, Claude Cowork, Claude Tag, Claude in Slack, Team and Enterprise capabilities, connectors, and release notes.

## Inclusion Rule

Use a union, not two separate lists:

`included updates = updates from the last 7 days ∪ each tool's latest 3 official versions or updates`

If a tool has no semantic version releases, use its latest official release-note entries or docs updates and label the source type. Default Chinese labels: "官方文档更新" or "发布说明条目". English labels ("official docs update", "release notes entry") only in an English report.

## Recommended Report Structure

For the HTML report, use this structure:

1. Title and date scope
 - State current date.
 - State the 7-day window using exact dates.
 - State the union inclusion rule.
 - Default Chinese heading style: `AI Agent 更新简报` plus the date.
2. Topline conclusions（核心结论）
 - Highlight the biggest migration, breaking change, security change, pricing/quota change, and agent workflow trend.
3. Recommended actions（建议动作）
 - Provide concrete next steps such as upgrade, migrate, check policy, verify quota, or pilot a workflow.
4. Scenario sections
 - Default Chinese scenario titles:
 - 工程自动化
 - 多 Agent / 子 Agent
 - 权限安全与破坏性变更
 - 模型配额与成本
 - 按任务选工具
 - In each scenario, include tool-specific rows or cards.
 - Put examples in each tool's "影响 / 示例" text, not as a single scenario-level example.
5. Union update pool（联合更新池）
 - List each tool's included versions or updates under the union rule.
6. Official sources（官方来源）
 - Link each official source used.
7. Glossary（术语表）
 - Name the section "术语表" by default, or "Glossary" only in an English report. Never "Beginner glossary" or "小白术语表".

## Scenario Row Pattern

For table rows, prefer these Chinese headers by default:

- 工具
- 日期
- 官方更新
- 实际影响 / 示例

The impact cell should answer:

- 谁该关心？
- 工作流会怎么变？
- 出现了什么风险或机会？
- 一个具体用法示例是什么？

Default Chinese impact style:

`适合把 CI 失败转成后台修复任务。示例：GitHub Actions 在 PR 上失败时，触发 Agent 查看日志、修好失败测试并开出修复 PR。`

Use English headers and impact style only in an English report.

## HTML Artifact Guidelines

Because standalone HTML is the default output:

1. Create a standalone HTML file with embedded CSS. Default `<html lang="zh-CN">`.
2. Use scenario navigation, summary cards, readable tables, and source links.
3. Avoid landing-page or marketing copy; make the first screen useful.
4. Do not include a "what this report is about for beginners" section unless explicitly requested.
5. Do not include a "which reader should read where" section unless explicitly requested.
6. Include "Glossary" / "术语表" only when useful.
7. Keep examples inside each tool's impact cell or card text.
8. Make the page readable without a local server.
9. Use a descriptive filename such as `ai-agent-update-brief-YYYY-MM-DD.html`.
10. After writing the HTML, open or inspect the file enough to verify it contains the required sections and links.
11. Chinese is the default, so always run a localization pass over visible text after content is complete. Translate source notes, update-pool remarks, glossary rows, and footer caveats; these areas are easy to leave half-English. Skip this pass only for an explicit English report.
12. Every standalone HTML brief must include **亮色** and **暗黑** modes in the same file. Read [references/html-theme.md](references/html-theme.md) and copy that token, toggle, and script contract. Do not invent a new palette unless the user asks.

## Appearance (Light / Dark)

Required for every standalone HTML brief:

- Ship both modes: 亮色 (`light`) and 暗黑 (`dark`).
- Default to the reader's `prefers-color-scheme` until they pick a mode.
- Persist an explicit pick in `localStorage` key `ai-agent-brief-theme`.
- Place a segmented toggle in the sticky nav so it stays visible while scrolling. Default labels: `亮色` / `暗黑`. English reports: `Light` / `Dark`.
- Put a tiny theme-restore script in `<head>` before CSS so the first paint does not flash the wrong mode.
- Express every color through CSS variables from the theme contract. Header, rule callout, sticky nav, cards, tables, chips, code, links, and footer must all flip with the mode.
- After writing, verify **both** modes on: the first screen (header + 核心结论 cards), one table with chips, the sticky nav, and the footer. Fix contrast problems before finishing.

## Tool-Specific Handling

- **Gemini CLI / Antigravity CLI**: If official sources indicate Gemini CLI migration or deprecation, present Antigravity CLI as the successor and treat migration as a breaking or high-priority change.
- **VS Code**: Position it as an IDE, Copilot, and agent-workbench base rather than a standalone coding agent.
- **Claude Cowork**: Position it as desktop and knowledge-work agent tooling. If no versioned changelog exists, use official release notes and support/docs updates.
- **Claude Tag / Claude in Slack**: Treat Slack-native channel/group collaboration as an agent workflow surface, not as a minor connector. Include it when official docs or launch pages show new channel tagging, shared context, agent identity, proactive follow-up, channel/workspace memory, routing to Claude Code, spend limits, audit logs, or admin permissions. Place it in engineering automation, team collaboration, permissions/security, and quota/cost sections as appropriate.
- **Agentic IDEs and CLIs**: Separate IDE, CLI, cloud automation, and desktop-agent use cases when the distinction affects user action.

## Quality Checklist

Before finalizing:

- Verify every included update satisfies the union rule.
- Ensure every tool has a recent update pool entry or an explicit note explaining why not.
- Ensure breaking changes, migrations, security changes, quota/pricing changes, and model support changes are easy to find.
- Ensure cross-surface launches are not missed: check official help/docs capability pages in addition to changelogs for Claude Tag/Slack, Copilot app/CLI/agent, Replit connectors, Devin automations, and similar agent surfaces.
- Ensure examples are attached to tool-level impact, not isolated as generic scenario examples.
- Ensure source links are official and dates are explicit.
- Ensure the report language is consistent. Default Chinese reports must use Chinese for visible prose, navigation, source notes, update-pool remarks, and footer caveats, except for deliberate product names, commands, URLs, API/protocol names, and version identifiers. The chat summary must match the report language.
- Ensure both 亮色 and 暗黑 modes are present, the sticky toggle works, the saved theme restores without a flash, and contrast holds in both modes on cards, tables, chips, and the header.
- If producing files, provide a clickable local file link in the final response.

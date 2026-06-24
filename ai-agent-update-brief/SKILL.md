---
name: ai-agent-update-brief
description: Create standalone HTML update briefs for AI coding agents, agentic IDEs, CLI agents, developer tools, and related AI productivity tools. Use when the user asks to research changelogs, release notes, official blogs, GitHub releases, or docs updates for tools such as Cursor, OpenAI Codex, Claude Code, Claude Cowork, Antigravity CLI, Google Antigravity, Antigravity IDE, VS Code, or similar tools. If the user does not name specific tools, default to the full default tool set defined in this skill. The output should be a clear, practical HTML report with recent updates, latest versions, official sources, real user impact, and concrete examples.
---

# AI Agent Update Brief

## Core Output Principle

Build a decision-ready brief, not a raw changelog dump. Organize updates by user scenario, explain practical impact, include concrete examples inside each tool's impact text, and cite official sources.

## Default Behavior

When the user asks for an AI agent update brief, AI coding tools report, agentic IDE report, CLI agent update, or similar research task and does not specify a tool list, treat "all tools" as the default. Do not ask for clarification just to choose tools.

Default output is a standalone HTML report saved in the current workspace. Also provide a concise chat summary with the local file link after generation.

Only produce a chat-only brief when the user explicitly asks for no file, no HTML, quick summary, or chat-only output.

## Language and Localization

Use the user's language for the report. If the user writes in Chinese or the existing report/workspace convention is Chinese, write the report in Chinese.

For Chinese reports:

- Translate all natural-language analysis, labels, table headers, status notes, source-use notes, and glossary explanations into Chinese.
- Keep product names, model names, commands, API names, protocol names, version numbers, URLs, and official feature names in English when translation would reduce clarity, for example `Cursor`, `Claude Tag`, `MCP`, `BYOK`, `GitHub Changelog`, `/usage`, and `AGENTS.md`.
- Do not leave English work-note phrases in the report body, such as "checked", "latest", "official releases", "No qualifying update found", "billed to organization", "spend limits", "audit logs", or "release page checked". Translate them into polished Chinese, for example "已检查", "最新版本", "官方版本页", "未找到合格更新", "计入组织账单", "支出上限", "审计日志", and "已检查版本页".
- Link text should be reader-friendly in Chinese when possible, while the underlying URL remains unchanged. For example, prefer "Codex 官方 changelog" over a bare URL unless the URL itself is the clearest label.
- Keep terminology consistent throughout the report. For example, choose "Agent" and "子 Agent" consistently instead of mixing "agent", "subagent", and "Subagent" in natural-language sentences.
- Before finalizing, scan visible text for stray English fragments. Leave only deliberate English product/feature names, commands, URLs, and technical identifiers.

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

If an item has no official updates available under the inclusion rule, keep it in the report with an explicit "no qualifying official update found" note and cite the official page checked when possible.

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

If a tool has no semantic version releases, use its latest official release-note entries or docs updates and label the source type, for example "official docs update" or "release notes entry".

## Recommended Report Structure

For the HTML report, use this structure:

1. Title and date scope
   - State current date.
   - State the 7-day window using exact dates.
   - State the union inclusion rule.
2. Topline conclusions
   - Highlight the biggest migration, breaking change, security change, pricing/quota change, and agent workflow trend.
3. Recommended actions
   - Provide concrete next steps such as upgrade, migrate, check policy, verify quota, or pilot a workflow.
4. Scenario sections
   - Use scenarios such as:
     - Engineering automation
     - Multi-agent or subagent workflows
     - Permissions, security, and breaking changes
     - Models, quota, pricing, and cost visibility
     - Tool selection by task
   - In each scenario, include tool-specific rows or cards.
   - Put examples in each tool's "Impact / Example" text, not as a single scenario-level example.
5. Union update pool
   - List each tool's included versions or updates under the union rule.
6. Official sources
   - Link each official source used.
7. Glossary
   - Name the section "Glossary" or "术语表", not "Beginner glossary" or "小白术语表".

## Scenario Row Pattern

For table rows, prefer:

- Tool
- Date
- Official update
- Practical impact / example

The impact cell should answer:

- Who should care?
- What workflow changes?
- What risk or opportunity appears?
- What is a concrete example of use?

Example impact style:

`Useful for turning CI failures into background repair tasks. Example: when GitHub Actions fails on a PR, trigger an agent to inspect logs, fix the failing test, and open a repair PR.`

## HTML Artifact Guidelines

Because standalone HTML is the default output:

1. Create a standalone HTML file with embedded CSS.
2. Use scenario navigation, summary cards, readable tables, and source links.
3. Avoid landing-page or marketing copy; make the first screen useful.
4. Do not include a "what this report is about for beginners" section unless explicitly requested.
5. Do not include a "which reader should read where" section unless explicitly requested.
6. Include "Glossary" / "术语表" only when useful.
7. Keep examples inside each tool's impact cell or card text.
8. Make the page readable without a local server.
9. Use a descriptive filename such as `ai-agent-update-brief-YYYY-MM-DD.html`.
10. After writing the HTML, open or inspect the file enough to verify it contains the required sections and links.
11. For non-English reports, run a localization pass over visible text after content is complete. Translate source notes, update-pool remarks, glossary rows, and footer caveats; these areas are easy to leave half-English.

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
- Ensure the report language is consistent. For Chinese reports, verify that visible prose, source notes, update-pool remarks, and footer caveats are Chinese except for deliberate product names, commands, URLs, API/protocol names, and version identifiers.
- If producing files, provide a clickable local file link in the final response.

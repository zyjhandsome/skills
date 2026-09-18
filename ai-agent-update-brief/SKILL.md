---
name: ai-agent-update-brief
description: >
  Creates a standalone HTML update brief for AI coding agents, agentic IDEs,
  and CLI tools. Use when the user invokes /ai-agent-update-brief or explicitly
  asks for an AI-agent / coding-tool changelog brief, release-notes digest, or
  weekly update report.
disable-model-invocation: true
---

# AI Agent Update Brief

Build a decision-ready brief, not a changelog dump. Copy the HTML skeleton, fill
research, then run the content verifier. Do not invent class names or `data-*`
attributes.

## Files

- [references/report-skeleton.html](references/report-skeleton.html) — copy this; fill content
- [references/sources.md](references/sources.md) — official URL index; edit it in the same turn if stale
- [references/html-theme.md](references/html-theme.md) — token/script contract (already inlined in the skeleton)
- [scripts/verify-brief.mjs](scripts/verify-brief.mjs) — required content gate
- [scripts/verify-theme.mjs](scripts/verify-theme.mjs) — optional light/dark screenshots

`<skill-dir>` is the folder that holds this `SKILL.md`. Use the absolute path you
loaded, not a guess.

## Workflow

```
- [ ] 1. Read sources.md and open those URLs first
- [ ] 2. Research by vendor in parallel; honor tool tiers and the fetch budget
- [ ] 3. Backfill sources.md in this turn if any URL is dead, renamed, or superseded
- [ ] 4. Copy report-skeleton.html → reports/ai-agent-update-brief-YYYY-MM-DD.html
- [ ] 5. Fill content; keep data-section / data-tool / data-window-* attributes
- [ ] 6. Localization pass (Chinese default); delete data-placeholder="1"
- [ ] 7. node <skill-dir>/scripts/verify-brief.mjs <report.html>
- [ ] 8. Optional: verify-theme.mjs; Chinese chat summary + local file link
```

Default output: standalone HTML under the workspace `reports/` folder (create it
if missing). Never write reports next to this skill. Chat-only only when the user
asks for no file / no HTML / a quick summary.

## Language

Chinese is the default for the HTML and the chat summary, including when the user
only types `/ai-agent-update-brief` or writes the request in English. Switch only
on an explicit English request (`in English`, `English report`, `英文`, `用英语`).

- Chinese report: `lang="zh-CN"`. Translate visible prose, labels, notes, and the
  footer. Keep product names, commands, APIs, versions, URLs, and official feature
  names in English. Ban leftover work-notes such as `checked`, `latest`,
  `No qualifying update found`, `official releases`.
- English report: `lang="en"` and pass `--en` to the verifier. Same structure and
  `data-*` attributes.

Chinese section titles: 核心结论、建议动作、工程自动化、多 Agent / 子 Agent、
权限安全与破坏性变更、模型配额与成本、按任务选工具、联合更新池、官方来源、术语表.

## Tool tiers

Baseline, not a frozen contract. Follow successors in `sources.md`. The user may
narrow or expand the list.

| Tier | `data-tool` | Report as | If research fails |
| --- | --- | --- | --- |
| Core (required) | `cursor`, `codex`, `claude-code`, `antigravity`, `vscode-copilot` | Cursor; Codex; Claude Code; Antigravity / Gemini CLI; VS Code / Copilot | Still emit a pool row; cite the page checked |
| Secondary (best effort) | `cowork`, `claude-tag`, `jetbrains`, `devin`, `amp`, `factory` | Cowork; Claude Tag; JetBrains / Junie; Devin / Windsurf; Amp; Factory Droid | May use `data-status="skipped"` + 「本轮未深挖」 |
| Tail (if found) | `aider`, `continue`, `replit`, `copilot-workspace` | Aider; Continue; Replit Agent; Copilot Workspace | Same as secondary; keep empty tail off the first screen |

**Degrade rule:** A brief is deliverable once every **core** row is filled
(`update` or `none`). If any secondary/tail row is `skipped`, set
`data-degrade="1"` on `.rule.degrade` and list what was skipped. Do not present a
partial run as a full default scan.

Budget: 2–4 fetches per researched tool. After that, write 「未找到合格官方更新」
(`data-status="none"`) and stop. Group by vendor (Anthropic, OpenAI, Google,
GitHub/Microsoft, Cognition, JetBrains, independents) and research groups in
parallel when possible.

## Research

1. Open the URLs in `sources.md` first. Search only if an entry is missing, dead,
   or clearly stale.
2. **Same turn:** patch `sources.md` (URL, successor note, 核实日期) when you
   correct the index. A note in the report is not enough.
3. Treat dated claims in `sources.md` as clues to re-verify, not as facts to paste.
4. Source order: official changelog → docs → official GitHub Releases → official
   blog/support → labeled secondary.
5. Capture URL + date + version while reading; never reconstruct them later.
6. Capability-surface sweep for suite products (Claude, Copilot, Replit, Devin):
   help/docs, connectors, enterprise pages, launch posts.
7. OpenAI product facts: official OpenAI sources only unless the user says otherwise.

Inclusion rule (a union, not two lists):

`included updates = last 7 days ∪ each tool's latest 3 official versions or updates`

No semver → latest official notes/docs; label 「官方文档更新」 or 「发布说明条目」.

## Report

Copy the skeleton. Keep `data-section` values, `nav.toc` / `.rule` / `.chip.*` /
`.theme-switch`, and pool-row attributes:

- `data-window-start` / `data-window-end` on `.rule.scope` (`YYYY-MM-DD`)
- each pool `tr`: `data-tool`, `data-status` = `update|none|skipped`
- if `update`: `data-date`; if that date is outside the 7-day window, also
  `data-latest="1|2|3"`

Table headers: 工具、日期、官方更新、实际影响 / 示例.

Impact cell answers: 谁该关心、工作流怎么变、风险或机会、一个具体用法. The
example lives in the tool row, not as a scenario-level blurb.

Filename: `reports/ai-agent-update-brief-YYYY-MM-DD.html`.

Do not add beginner-audience or "who should read where" sections unless asked.
Do not name the glossary 「小白术语表」 or 「Beginner glossary」.

## Theme

The skeleton already inlines [html-theme.md](references/html-theme.md). Do not
invent a palette. The header stays a dark masthead; paper, cards, tables, chips,
and the sticky nav flip.

## Tool-specific

- Gemini CLI → Antigravity CLI (`agy`) when official sources say so; treat as breaking.
- VS Code is an IDE / Copilot workbench, not a standalone agent.
- Cowork: desktop / knowledge-work; use official notes if unversioned.
- Claude Tag: first-class Slack agent surface, not a minor connector.
- Split IDE vs CLI vs cloud vs desktop when the split changes the action.

## Verify

Required:

```bash
node <skill-dir>/scripts/verify-brief.mjs reports/ai-agent-update-brief-YYYY-MM-DD.html
```

English report: add `--en`. Optional link HEAD: `--check-links`. Delivered reports
must not keep `data-placeholder="1"` (`--strict` fails on it).

Fix every ERROR before delivering. Then optional theme screenshots:

```bash
node <skill-dir>/scripts/verify-theme.mjs reports/ai-agent-update-brief-YYYY-MM-DD.html
```

`verify-theme.mjs` needs `playwright-core` plus Edge/Chrome, or `BRIEF_BROWSER_PATH`.
If it cannot run, spot-check both modes on the first screen, one table with chips,
the sticky nav, and the footer.

The chat summary matches the report language and includes a clickable local file link.

---
name: md2wechat
description: >-
  Convert 整理文档 Markdown/HTML into WeChat Official Account paste-ready HTML
  (full inline styles) plus a 2.35:1 cover PNG. Use when the user mentions
  微信公众号, 公众号排版, md2wechat, 公众号完整版, 封面 2.35, or publishing
  an Obsidian/md2html lecture note to WeChat.
---

# /md2wechat

把「对谈三层」类整理文档变成**可粘贴进微信公众号编辑器**的 HTML，并产出 **2.35:1** 封面图。

上游通常是 content-structuring / md2html 产出的 `*_整理文档.md`（及可选 `*_整理文档.html`）。**不要**把 md2html 网页原样粘进公众号（外链 CSS/JS/class/Mermaid 会失效）。

## Skill files

| File | Role |
|------|------|
| [reference-wechat-constraints.md](reference-wechat-constraints.md) | 微信 HTML/CSS 白名单与粘贴坑 |
| [examples.md](examples.md) | 输入输出命名与默认取舍对照 |
| [scripts/build_wechat_html.py](scripts/build_wechat_html.py) | MD → 公众号内联 HTML |
| [scripts/make_cover_235.py](scripts/make_cover_235.py) | 任意封面图 → 精确 2.35:1 PNG |
| [scripts/validate_wechat_bundle.py](scripts/validate_wechat_bundle.py) | 产物自检（须通过再交付） |

**先读本 SKILL，再按需读 reference；生成后必须跑 validate。**

## Outputs (next to source)

```
{stem}_公众号完整版.html          # 可复制正文（内联样式）
{stem}_公众号封面_2.35x1.png      # 1175×500（或等比例）
```

可选：`wechat-diagrams/*.png`（Mermaid 转图后嵌入）。

## Default content policy（公众号版）

| 区块 | 默认 |
|------|------|
| H1 标题 + 核心导读（全文论点与导读段） | **保留** |
| 正文各节洞察 / 深度解析 / 对谈实录 | **完整保留**（不压成精读摘要） |
| 「核心洞察」「深度解析」「对谈实录」标题 | **保留**（扫读分层；去掉会像一整墙字） |
| 文章元数据表 | **去掉**；只留「人物背景」卡片 |
| 目录 | **去掉** |
| 延伸术语表 | **去掉** |
| 自检报告 | **去掉** |
| 文末「来源与说明」 | **只留前两项**（原文标题/场次 + 视频或内容链接） |
| 页眉副标题如「完整整理版｜微信排版」 | **不要** |
| Mermaid / 流程图 | 微信不能原生跑。**默认不嵌入**；仅当用户明确要求「保留流程图/Mermaid」时，从 sibling `*_整理文档.html` 导出 PNG 再 `<img>` 嵌入 |

用户另有指示时覆盖上表。

## Workflow

Copy and track:

```
md2wechat Progress:
- [ ] 1 Resolve source (.md required; .html optional for Mermaid)
- [ ] 2 Build WeChat HTML (inline styles)
- [ ] 3 Cover 2.35:1
- [ ] 4 Validate bundle
- [ ] 5 Hand off paste / publish steps
```

### 1 — Resolve source

1. Prefer `*_整理文档.md` as content source.
2. If user only gives `.html`, recover sibling `.md`; if missing, extract text carefully and say so.
3. Confirm title (H1) and 2–3 cover keywords (e.g. 内部罗盘 / 机甲歌利亚).

### 2 — Build WeChat HTML

Prefer **absolute path** to the skill script (cwd-independent):

```bash
python "%USERPROFILE%\.cursor\skills\md2wechat\scripts\build_wechat_html.py" "<path-to>_整理文档.md"
```

On failure (missing Python / script error): fix the environment first; only hand-author HTML if the script cannot be unblocked and you still follow the same policy + inline-style rules.

Or implement the same rules by hand if the script cannot run:

1. Wrap copyable body in `#wechat-article` with **all styles inline** (no `<style>` dependency inside the copied region; preview chrome outside is OK).
2. Theme tokens (md2html terracotta): bg `#FAFAF7`, accent `#D97757`, accent-strong `#A85533`, soft `#FBEEE6`, border `#E5E4DC`.
3. Structure each section: `h2` → `h3 核心洞察` + insight card → `h3 深度解析` + paragraphs → `h3 对谈实录` + speaker cards.
4. Font stack: system + PingFang SC / Microsoft YaHei (no Google Fonts in paste body).
5. Add short howto above the fold: select beige card → copy → paste into 公众号编辑器 → mobile preview.

Details: [reference-wechat-constraints.md](reference-wechat-constraints.md).

### 3 — Cover 2.35:1

WeChat 首图常用 **2.35:1**。GenerateImage 无该比例时：

1. `GenerateImage` 用最接近的宽幅（`16:9`），构图把标题放在**垂直安全中带**（上下可能被裁）。
2. Prompt：暖米色底、赤陶强调色、与标题金句一致；忌紫霓虹赛博风、忌堆叠 Logo。
3. 裁切导出：

```bash
python scripts/make_cover_235.py "<generated.png>" --out "<stem>_公众号封面_2.35x1.png"
```

默认导出 **1175×500**（精确 2.35）。

### 4 — Validate (mandatory)

```bash
python scripts/validate_wechat_bundle.py "<stem>_公众号完整版.html" --cover "<stem>_公众号封面_2.35x1.png"
```

Fix until exit 0. Do not deliver a failing bundle.

### 5 — Hand off

告诉用户：

1. 浏览器打开 `*_公众号完整版.html`
2. 复制米色卡片内正文 → 粘贴公众号编辑器
3. 上传 `*_公众号封面_2.35x1.png` 为封面
4. 手机预览；**群发/发表由用户确认**

**不要假装已代发。** 无公众号 MCP/登录态时，停在「需用户登录授权」；用户说已登录后再给逐步核对清单。

## Anti-patterns

- 把 md2html 整页（外链字体、侧栏 TOC、主题切换、Mermaid `<pre>`）当公众号稿
- 默认大幅删正文「精读压缩」（除非用户明确要精读）
- 去掉「核心洞察 / 深度解析」分层却声称更易读
- 封面只给 16:9 / 1:1 却标成 2.35:1
- 文末堆免责声明与术语表拖垮完读率

## Related skills

- Upstream notes: `content-structuring` / lecture pipeline
- Web reading page: `md2html` / `md2html-lecture`（网页精读；**不是**公众号粘贴稿）

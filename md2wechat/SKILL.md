---
name: md2wechat
description: >-
  Turn 整理文档 Markdown into an edited WeChat Official Account article,
  paste-ready inline HTML, and a 2.35:1 cover. Use when existing Markdown,
  HTML, lecture notes, interviews or整理文档 need 微信公众号改写、排版或播报优化.
  Distinguish an editorial article from a complete-format conversion. Do not
  route unrelated from-scratch writing here when no source material exists.
---

# md2wechat

把整理文档变成真正适合公众号发布的内容，而不只是把 Markdown 换成带样式的 HTML。

公众号同时是阅读媒介和收听媒介。默认优化手机扫读、连续播报、可信度、转发意愿和粘贴稳定性；用户明确要求“完整版/完整保留/只排版”时，才保留原稿的完整三层结构。

## Choose the mode

| User intent | Mode | Result |
|---|---|---|
| “生成/改写成公众号文章”“更易读/易听” | `editorial`（默认） | 先写公众号成稿 Markdown，再生成 HTML；围绕一条主线删重、合并、转述 |
| “公众号完整版”“完整保留”“只排版” | `full` | 保留正文信息与“核心洞察/深度解析/对谈实录”三层，只删除元数据噪音 |

不要用 `full` 冒充“成稿”，也不要在用户要求完整保留时擅自压缩。

## Read as needed

- 两种模式都必须读 [references/content-integrity.md](references/content-integrity.md)，先完成内容覆盖审计，再交付。
- 做 `editorial` 时，必须读 [references/editorial-and-audio.md](references/editorial-and-audio.md)。
- 处理微信 HTML、表格或粘贴问题时，读 [reference-wechat-constraints.md](reference-wechat-constraints.md)。
- 查看命名和封面提示词时，读 [examples.md](examples.md)。

## Outputs

`editorial` 默认与源文件同目录产出：

```text
{stem}_公众号成稿.md
{stem}_公众号内容审计.md
{stem}_公众号文章.html
{stem}_公众号封面_2.35x1.png
```

`full` 默认产出：

```text
{stem}_公众号内容审计.md
{stem}_公众号完整版.html
{stem}_公众号封面_2.35x1.png
```

## Workflow

### 1. Resolve and diagnose

以 `*_整理文档.md` 为内容源；只有 HTML 时，先寻找同名 Markdown，找不到再谨慎提取正文并披露这一降级。同名 HTML 也可用于提取用户明确要求保留的图。先判断受众、原稿信息密度、可验证边界和最值得承诺的一条主线。用户没有指定读者时，从标题、栏目和原稿语气合理推断，不必停下来提问。

写作前列出源稿每个正文 H2 的核心结论、关键证据、限定/反方和行动含义。在 `*_公众号内容审计.md` 中逐节标记 `保留 / 合并 / 删减 / 删除`；任何删减或删除都要说明为什么不影响标题承诺。

### 2. Edit the content

`editorial`：先生成 `*_公众号成稿.md`。文章应有一条标题承诺、一个能独立听懂的开场、清晰的章节推进和行动性收束。合并重复的“洞察/解析/实录”，把对话改为叙述，只保留少量不可替代的短引语。表格改为口语化结论；链接、来源和复杂数字不要打断正文播报。正文主动提出的问题必须在本节或后文明确回答，不能只靠暗示闭环。

`full`：保留原稿主体和三层结构；删除目录、术语表、自检、抓取流水、编辑注及冗长免责声明。

共同要求：不得把简介中的问题写成嘉宾说过的结论；口述数字和观点要明确归于讲者，未核实内容不要升级成事实。区分短引语与编辑概括；访谈、演讲类精编稿在元数据加入简短“编辑说明”，向读者披露非逐字稿和观点归属。

### 3. Build paste-ready HTML

使用绝对路径，避免依赖当前目录：

```powershell
python "$env:USERPROFILE\.cursor\skills\md2wechat\scripts\build_wechat_html.py" "<公众号成稿.md>" --mode editorial --out "<公众号文章.html>"
python "$env:USERPROFILE\.cursor\skills\md2wechat\scripts\build_wechat_html.py" "<整理文档.md>" --mode full
```

复制区域 `#wechat-article` 内必须全是内联样式，不依赖 class、外链 CSS、JavaScript 或 Mermaid。正文表格在 `editorial` 中改写为句子；`full` 中 ≤4 列转内联表，≥5 列转卡片。只有用户明确要求保留 Mermaid/流程图时，才从同名 HTML 或源码渲染为 PNG，再以普通图片插入；不得保留 Mermaid 源码。

### 4. Make the cover

首图目标 2.35:1，默认 1175×500。画面应有单一隐喻、明确视觉中心和移动端安全区；文字尽量短。先生成宽幅图，再裁切：

```powershell
python "$env:USERPROFILE\.cursor\skills\md2wechat\scripts\make_cover_235.py" "<generated.png>" --out "<stem>_公众号封面_2.35x1.png"
```

裁切和封面校验需要 Pillow。先确认当前 Python 能执行 `from PIL import Image`；缺失时使用已有的工作区 Python 运行时或在当前环境安装 Pillow，不得跳过封面校验。

### 5. Validate before delivery

```powershell
python "$env:USERPROFILE\.cursor\skills\md2wechat\scripts\validate_wechat_bundle.py" "<公众号文章.html>" --profile editorial --source "<整理文档.md>" --audit "<公众号内容审计.md>" --cover "<cover.png>"
python "$env:USERPROFILE\.cursor\skills\md2wechat\scripts\validate_wechat_bundle.py" "<公众号完整版.html>" --profile full --source "<整理文档.md>" --audit "<公众号内容审计.md>" --cover "<cover.png>"
```

必须修到退出码为 0。校验器只能确认覆盖清单齐全，不能代替语义判断。还要人工检查：只听音频是否能理解指代和转折；只扫标题、每节首段和金句是否能复述主线；标题是否兑现；显式问题是否逐一回答；每个重要判断是否能区分“事实、讲者观点、编辑推论”；审计表中的删减理由是否成立。

### 6. Hand off

告诉用户打开 HTML，复制米色卡片内的正文，粘贴到公众号编辑器，上传 2.35:1 封面并手机预览。没有公众号登录态时停在这里；群发或发表必须由用户确认。

## Non-negotiable anti-patterns

- 把原稿逐段换皮，却称为“公众号成稿”
- 为了短而删除限定词、来源边界或相反观点
- 未做逐节覆盖审计，却声称“内容完整”
- 在正文提出问题，后文没有明确回答
- 用表格、括号注释、裸链接和连续 speaker 标签组织需要播报的正文
- 标题同时塞入四五个议题，正文没有单一回答
- 用工具效率代替读者价值，只报告“压缩了多少字”
- 封面给 16:9 或 1:1，却标成 2.35:1
- 把 md2html 整页或 Mermaid 源码直接粘进公众号

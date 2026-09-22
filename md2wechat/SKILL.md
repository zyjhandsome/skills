---
name: md2wechat
description: >-
  Turn 整理文档 Markdown into a WeChat Official Account article: paste-ready
  inline HTML and a 2.35:1 cover. Default editorial keeps the source H1,
  reader-facing H2s, and each section's claims; WeChat work is inside the
  section (flatten 三层, drop metadata noise, make it listenable). Use when
  整理文档 / lecture notes / interviews need 微信公众号排版 or 播报优化, or when a
  prior 公众号 was deleted for 运营规范. Do not rewrite titles unless the user
  asks 改写标题 or policy requires it. Do not route from-scratch writing here.
---

# md2wechat

把整理文档变成真正适合公众号发布的内容，而不只是把 Markdown 换成带样式的 HTML。

公众号同时是阅读媒介和收听媒介。默认两件事一起做：**标题、小节标题和各节判断跟整理文档走**；节内按公众号做扫读、连续播报、合规和粘贴稳定性。用户明确要求“完整版/完整保留/只排版”时，连三层标签也保留。用户明确要求“改写标题”时，才另写 H1/H2。

## Source fidelity（默认，未要求改写标题时）

- 成稿 H1 = 源稿 `#` 第一行，封面叠字用同一句。
- 每个读者向 H2 原样出现，不得改成更冲的金句，也不得把两节合成一个新标题。篇末「关键语录与交锋时刻」不进公众号（金句留在各节正文里）。
- 各节的核心结论、必要机制/例子、会改变力度的限定仍在该节标题下；压缩的是三层重复和过程噪音，不是另写一篇。
- 文件名仍跟源文件走，只加 `_公众号文章` / `_公众号封面`。页脚「原文：」用元数据原标题，不是 H1。

## Choose the mode

| User intent | Mode | Result |
|---|---|---|
| “生成/改写成公众号文章”“更易读/易听” | `editorial`（默认） | 先写公众号成稿 Markdown，再生成 HTML；**沿用源稿 H1 与读者向 H2**，节内去掉三层标签、改成可播报叙述 |
| “改写标题”“重写小节标题”“不要跟原文标题走” | `editorial` + 改写标题 | 只有用户明确要求时，才另写 H1/H2 |
| “公众号完整版”“完整保留”“只排版” | `full` | 连“核心洞察/深度解析/对谈实录”三层也保留；只删除元数据噪音；运营规范阻断的主张不能靠 full 重印，删不掉就停 |

不要用 `full` 冒充“成稿”，也不要在用户要求完整保留时擅自压缩。默认也不要为了「更好听」另起一套章节标题。

## Read as needed

- 两种模式都必须先读 [references/wechat-operation-policy.md](references/wechat-operation-policy.md)，对源稿做《微信公众平台运营规范》门禁；不可发布就停，不要出 HTML。
- 两种模式都必须读 [references/content-integrity.md](references/content-integrity.md)，先完成内容覆盖审计，再交付。
- 做 `editorial` 时，必须读 [references/editorial-and-audio.md](references/editorial-and-audio.md)。
- 处理微信 HTML、表格或粘贴问题时，读 [references/wechat-constraints.md](references/wechat-constraints.md)。
- 查看命名和封面提示词时，读 [examples.md](examples.md)。
- 改脚本后跑 `python -m unittest discover -s scripts/tests -v`，以及 `python scripts/build_wechat_html.py --self-test`。封面测试需要 Pillow。

## Outputs

与源文件同目录，两种模式都只交付这两个文件。文件名与原文文件名一致，只加后缀：

```text
{原文文件名去扩展名}_公众号文章.html
{原文文件名去扩展名}_公众号封面.png
```

例如 `20260803 刘润×吴军！…_整理文档.md` 对应 `…_整理文档_公众号文章.html` 与 `…_整理文档_公众号封面.png`。

从临时成稿生成 HTML 时，必须 `--out` 到上述原文文件名，不能用成稿或 H1 另起名。

不要留下 `*_公众号成稿.md`、`*_公众号内容审计.md`、`*_公众号完整版.html`、`*_公众号封面_2.35x1.png`。成稿和覆盖审计只作内部工作：可写在临时目录，校验通过后删除。只删本次写入的临时文件，不得删除目录里其他篇目已有的公众号文件。

封面图上的标题必须与 HTML 的 H1 相同（可按冒号折成两行，不得另写金句）。文字只由 `overlay_cover_text.py` 叠上去，水平垂直居中：标题在上、细分隔线、人物在下。不要白色底牌、色块或胶囊；**禁止让 GenerateImage 把汉字、字母、数字、箭头或标题画进画面**。封面**文件名**跟原文走，不跟 H1 走。

## Workflow

### 1. Resolve and diagnose

以 `*_整理文档.md` 为内容源；只有 HTML 时，先寻找同名 Markdown，找不到再谨慎提取正文并披露这一降级。同名 HTML 也可用于提取用户明确要求保留的图。先判断受众、原稿信息密度、可验证边界和最值得承诺的一条主线。用户没有指定读者时，从标题、栏目和原稿语气合理推断，不必停下来提问。

先做运营规范门禁，再做覆盖审计。政策先于覆盖：`full` 不能用来重印被阻断的主张。

```bash
python scripts/scan_wechat_policy.py "<整理文档.md>"
```

退出码 1：按 [wechat-operation-policy.md](references/wechat-operation-policy.md) 判 `可发布 / 改写后可发布 / 不可发布`。闭门会外泄全文、未证实融资新闻、落马官员关系 → **不可发布，停交付**。改写不能把泄稿合法化；归因到「知情人士」也不能把传闻当新闻。只有公开可核实的主线，才继续往下写。

写作前列出源稿每个正文 H2 的核心结论、关键证据、限定/反方和行动含义，并完成覆盖判断（`保留 / 合并 / 删减 / 删除`）。默认每个读者向 H2 标 `保留`，成稿位置写源稿原标题。因运营规范删去的章节标 `删除`，理由写「运营规范」。审计表不要写成交付文件。

### 2. Edit the content

`editorial`：先在临时目录写公众号成稿 Markdown，再生成 HTML。先抄源稿 H1 和读者向 H2（不含「关键语录与交锋时刻」），再写节内正文。公众号适配发生在**节内**：去掉「核心洞察/深度解析/对谈实录」标签，把对话改成叙述，表格改成口语化结论，删掉目录、术语表、自检、关键语录汇编、编者注和抓取流水。整理文档里已经加粗或写进核心洞察、术语表的判断，用 `==这句话==` 做成浅底荧光笔，每节一两处即可。不要把一节的洞察句提升为新 H2。链接、来源和复杂数字不要打断正文播报。正文主动提出的问题必须在本节或后文明确回答。只有用户明确要求「改写标题」，或源稿 H1 本身触碰运营规范 4.11 时，才另写 H1/H2，并给校验器加 `--allow-heading-rewrite`。

`full`：保留原稿主体和三层结构；删除目录、术语表、自检、关键语录汇编、抓取流水、编辑注及冗长免责声明。输出文件名仍是 `{原文文件名}_公众号文章.html`。

共同要求：不得把简介中的问题写成嘉宾说过的结论；口述数字和观点要明确归于讲者，未核实内容不要升级成事实。区分短引语与编辑概括。观点归属写在正文里；来源与说明只保留「原文：{原标题}」，不要视频链接、日期括注或编辑说明。标题和正文不要用外泄、全文、突然、震惊、心虚、爆料做传播点。页脚免责声明不能对冲违规内容。

### 3. Build paste-ready HTML

使用绝对路径，避免依赖当前目录：

```bash
python scripts/build_wechat_html.py "<成稿或整理文档.md>" --mode editorial --out "<原文文件名>_公众号文章.html"
python scripts/build_wechat_html.py "<整理文档.md>" --mode full
```

脚本会把自身目录加入 `sys.path`。当前 `python` 缺 Pillow 时，改用已安装 Pillow 的解释器跑封面和校验，不要跳过。

默认输出 `{原文文件名}_公众号文章.html`，与源文件同目录。从临时成稿构建时必须 `--out` 到该路径。

复制区域 `#wechat-article` 内必须全是内联样式，不依赖 class、外链 CSS、JavaScript 或 Mermaid。行高用大于该元素字号的 `px`，不要无单位倍数。每个块写明 `text-align:left` 或 `center`（只有标题和副标题居中）。`p` / `h1`–`h3` / `td` 的文字包在一个 `<span>` 里，避免浏览器复制出 `text-align:start`，也避免加粗和荧光笔被行高检测当成叠字。正文表格在 `editorial` 中改写为句子；`full` 中 ≤4 列转内联表，≥5 列转卡片。只有用户明确要求保留 Mermaid/流程图时，才从同名 HTML 或源码渲染为 PNG，再以普通图片插入；不得保留 Mermaid 源码。

### 4. Make the cover

首图目标 2.35:1，默认 1175×500。画面应有单一隐喻，**主体放在左右两侧**，正中留出一块安静的米色空场给叠字。

文字与画面必须分两步，不要写进生成提示词：

1. GenerateImage 只画场景。提示词须写明：无文字、无汉字、无字母、无数字、无箭头、无 UI、无水印；正中约一半宽度保持空旷。
2. `make_cover_235.py` 裁成 1175×500。
3. `overlay_cover_text.py` 叠字。脚本会选用宋体标题（华文中宋等）、字距、陶土色标题 `#A85533`、浅陶土人物行 `#B09480`、中间细分隔线；长标题按冒号折行并自动缩小字号。不要手写另一套颜色或微软雅黑纯黑硬叠。

```bash
python scripts/make_cover_235.py "<generated.png>" --out "<临时>/cover-crop.png"
python scripts/overlay_cover_text.py "<临时>/cover-crop.png" --title "<H1>" --people "<人物>" --out "<原文文件名>_公众号封面.png"
```

叠字脚本把标题写入 PNG tEXt，校验器拿它和文章 H1 对。已经叠过字的文件会拒绝第二次写入；改标题时从无字裁切图重跑。

裁切和封面校验需要 Pillow。先确认当前 Python 能执行 `from PIL import Image`；缺失时使用已有的工作区 Python 运行时或在当前环境安装 Pillow，不得跳过封面校验。

### 5. Validate before delivery

```bash
python scripts/validate_wechat_bundle.py "<原文文件名>_公众号文章.html" --cover "<原文文件名>_公众号封面.png" --source "<整理文档.md>" --audit "<临时目录>/公众号内容审计.md"
# 仅当用户明确要求改写标题时加： --allow-heading-rewrite
# 仅当正文仍残留机械 stop 信号、且你能写出理由时加： --policy-ack unverified_finance:<reason>
```

必须修到退出码为 0。缺 `--source` / `--audit` 会失败（调试结构可用 `--html-only`，不能当交付）。校验器检查 HTML、来源页脚是否只有原文、封面比例、封面 tEXt 标题是否等于文章 H1、封面/HTML 文件名是否与原文文件名同茎、源稿 H1/读者向 H2 是否原样保留、运营规范标题/审计门禁，以及成稿正文是否还带着源稿的 stop 信号。扫描器会误伤单独的「尚未核实」；只有「尚未核实/知情人士」贴着融资、估值时才停。覆盖与是否可发布仍要对照 [wechat-operation-policy.md](references/wechat-operation-policy.md) 人工判断。还要检查：只听音频是否能理解指代和转折；只扫标题、每节首段和金句是否能复述主线；标题是否兑现；显式问题是否逐一回答；每个重要判断是否能区分“事实、讲者观点、编辑推论”。发布结论是「不可发布」时不要修校验器去出 HTML。交付前删除临时成稿和审计文件。

### 6. Hand off

可发布或改写后可发布：告诉用户打开 HTML，复制米色卡片内的正文，粘贴到公众号编辑器，上传 2.35:1 封面并手机预览。没有公众号登录态时停在这里；群发或发表必须由用户确认。扫描仍有残余风险时，在交接里写明，不要暗示「校验通过=平台不会删」。

不可发布：只说明触碰了哪几条运营规范、为什么停，不要交付粘贴稿。

## Non-negotiable anti-patterns

脚本已挡住文件名、封面比例、H1/H2 保真、页脚内容、Mermaid 源码和成稿里残留的 stop 信号。下面只列脚本管不住的判断错误：

- 把原稿逐段换皮，或把各节改写成另一条主线，却仍沿用源稿标题
- 擅自改写源稿 H1 / 读者向 H2，或把两节合成一个新标题
- 为了短而删掉限定、反方、或唯一能让结论成立的机制/例子
- 未做逐节覆盖审计，却声称“内容完整”；或缺 `--audit` 用 `--html-only` 当交付
- 在正文提出问题，后文没有明确回答
- 用表格、括号注释、裸链接和连续 speaker 标签组织需要播报的正文
- 让 GenerateImage 把标题、人名、箭头或任何字母汉字画进画面；封面加白底牌 / 胶囊；或手写微软雅黑纯黑硬叠
- 把成稿、审计留在源目录当交付件；清目录时删掉其他篇目已有的公众号文件
- 把闭门会外泄「全文」改排后称为成稿；或把知情人士未核实的融资/估值写成新闻
- 用 `full` 或「覆盖完整」重印运营规范已阻断的主张
- 正文写落马官员关系等政治公共事件联想，即使标注「不采信」
- 用页脚免责声明、拆字、谐音或截图长文规避审核；源稿不可发布仍先出 HTML

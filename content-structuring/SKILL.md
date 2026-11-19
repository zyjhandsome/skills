---
name: content-structuring
description: >-
  Use when turning podcasts (YouTube, Bilibili, Xiaoyuzhou, Apple Podcasts),
  transcripts (.srt/.vtt/.txt), tech Keynotes/lectures, live-coding or tutorial
  videos, X threads/Articles, Substack/Medium/WeChat/blog longform, panel Q&A,
  or multi-source dumps into a Chinese Markdown deep article that replaces the
  source (对谈三层、争辩型访谈、声口模式、实操演示 or multi-source merge). Not for
  trend briefs (last30days), GitHub repo tutorials (github-repo-usage-article),
  AI-tool changelog HTML briefs (ai-agent-update-brief), standalone visual
  explainers/decks (visual-explainer / slides), or downstream MD→HTML/WeChat
  conversion (md2html-lecture / md2wechat).
metadata:
  version: "5.50"
---

# 内容结构化整理（Content Structuring）

## 核心目标与体裁路由

把原始素材重构成一份读者**不必回到视频、播客或原文**也能掌握绝大多数关键信息的中文 Markdown 深度文档。做语义级的**全息降噪重构**：核心论点、定量数据与口径、案例细节、实操步骤/代码/Prompt、原文配图与关键画面信息、时间戳回溯锚点、主持人追问与嘉宾声口均须完整落地。

| 素材形态 | 默认体裁与节内结构 | 关键组织原则 |
| :--- | :--- | :--- |
| **信息型多人播客 / 访谈 / 圆桌** | **对谈三层**（`核心洞察 → 深度解析 → 对谈实录`） | 省略篇末语录节；有判断转向时按「旧判断→触发证据→新判断→实践/方案→个人行动」合并问答；≥4 人圆桌启用立场光谱表与分级声纹 |
| **持续分歧 / 连续追问 / 拒答纠错** | **争辩型访谈 / 原声增强**（`原声交锋 → 语境与释义 → 未决问题`） | 导读写 `> **核心冲突**`；按交锋升级顺序组织，先声后解，严禁伪造共识 |
| **单人演讲 / Keynote / 作者长文** | **通用模板 + 声口模式默认开**（`核心洞察 → 深度解析`） | H1 沿用原核心表述，解析保第一人称论证链，默认省略篇末语录；带尾声 Q&A 时按主题内嵌 `### 对谈实录` 或单开三层节 |
| **实操演示 / 教程 / Live Coding** | 叠加**实操四步保真**（前置环境卡 + 步骤闭环） | 落地 `目标 → 输入（命令/代码/配置/Prompt 原文）→ 屏幕反馈 → 坑点`，消解「点这里/这个值」等现场指代 |
| **多源合并（≥2 来源）** | **通用模板 + 源口径标注 + 多源一致性核对** | 可在对谈源章节内嵌实录；跨源冲突用 `[编者注]` 并存或点明「互补/不同维度」，禁自称「互证」 |

**用户显式覆盖**：支持指定 `专栏文章模式`、`纯粹对话模式`、`不要对谈实录`、`简洁版`、`中英双语/保留英文`、`受众可读性内化适配`；各变体的结构契约与门禁豁免见 `references/spec.md` 与 `references/templates.md`。

## 语言、视觉资产与不可妥协红线

- **讲者或作者声音优先于编者声音**：精编保留比喻、反问、修正与推理节奏，严禁抹平成统一分析师腔；声纹卡与遮名检验写入自检。无法唯一确认发言人时标 `[说话人待核：疑似 A 或 B]`，禁强猜挂名。
- **成稿即中文 + 专名/概念标签不过译 + 代码/Prompt 保真**：叙述层、核心洞察与实录/交锋直接用中文写；公司/产品/API 及 AI/DevTools 社区原生概念标签（如 `Skill / Agent Skill / Skill Creator / Hooks / Computer Use / Composer / Canvas / Subagent / Builder / Agent Loop / Loop / Graph / Workflow / Harness / Evals`）及成组 taxonomy（如 `Agent → Loop → Graph`）保留英文；行业缩写（`IC/ASL/MTS/RAG/GTM` 等）首现注中文全称；代码、CLI 命令与可直接复用的功能性英文 Prompt 原块保留。
- **纯远程外链视觉保真（严禁本地 `assets/` 图片落盘）**：全程不在输出目录保存任何本地图片文件。网页文章直接外链源页有效原图/原视频 `https://...`（严禁盲删 X `?format=` 或飞书/语雀/S3 鉴权签名参数）。音视频关键画面按 **L1 同源官方远程原图直连 → L2 内联 `mermaid`/表格/代码块重构（临时抽帧检视后即删）→ L3 `[视觉盲区 @ MM:SS]` 直达锚点** 处理，执行「4 类必保真 vs 5 类必剔除」清点并在自检 `| 原文图 |` 登记。配图/`<video>`/`mermaid` 仅放解析或通用正文层，禁插入实录对话轮次内；正文禁裸「如上图」，改写为「如图 N 所示，{结论与数值}」。
- **解析索引与实录去重、定量口径与事实边界**：深度解析用紧凑表/列表提供折叠实录态也能扫读完本节的框架索引，具体故事、交锋与推理原话归实录（一项事实一个主要归宿，篇幅与重合度以 `scripts/check_readability.py` 为准）。核心数字绑定「分母/时间窗/基准线/状态」四要素。事实状态用句末轻标记或节末 `> **事实边界**`，禁「这不是……」编者旁白；括注 `[编者注：…]` 为原子块，禁跨段拆行或写成发言。
- **纯净排版契约**：正文 `##` 禁 `1. ` 序号与 `{#锚点}`，节间禁 `---`（仅单空行）；实录时间码用说话人角注 `**{全名}**（14:20）：「…」`；章节时间轴与延伸外链汇总统一挂在 `## 文章元数据` 下作 `### 官方章节索引` / `### 核心引用与资源` 副表（严禁新增顶层 `## 提及资源`）。

## 加载策略（一层路由）

先读本文件，再按任务类型**直接**读取对应参考分册（分册为单一事实来源，不二次跳转）：

| 分册（`references/` 下） | 承载细则 | 何时必读 |
| :--- | :--- | :--- |
| `spec.md` | 角色设定、偏好覆盖与豁免矩阵、执行步骤清单（含超长稿同轮规划、信息覆盖抽样） | **所有任务** |
| `editorial-standards.md` | 扫读呈现、**原文图与音视频三级视觉保真**、**实操演示规范**、声口模式、事实标记、全名与 `[说话人待核]`、**定量口径**、抓取链与元数据副表、术语校准 | **所有成稿** |
| `language-and-gates.md` | 四层语言分区（含代码/可执行 Prompt 保真）、语气迁移、原声占比、保真与压缩优先级、**4c / 4d / 4e / 4f / 判断行** 闸门、可读性内化、存量复审 | **成稿与验收必读** |
| `templates.md` | 文件命名规则、公共文档外壳 + 各体裁/覆盖变体正文插槽、统一自检表、下游同步契约 | **组装输出时** |
| `interview-structures.md` | 对谈三层、争辩型访谈、**Keynote+Q&A 混合与 ≥4 人圆桌**、时间角注、声纹交卷、多源合并、核心导读写法 | 播客 / 访谈 / 圆桌 / 带 Q&A 演讲 / 多源素材 |
| `over-translation-guard.md` | 专名与 AI/DevTools 概念标签判定口诀、多义词辨析与过译黑名单 | AI / 工程 / Agent 工具素材 |
| `lexicon.txt` | 4c 统一机器可读词库（单源维护） | `check_4c.py` 自动加载；手工复核参考 |

**上游抓取路由**：有主链接时，优先协同使用**宿主可用浏览器工具**（如 Cursor Browser / Orca Browser 等，抓渲染正文、DOM 原图地址与链上指标）与 **`agent-reach`**（取 YouTube/Bilibili 字幕轨、X 线程、小红书、小宇宙等），不可用时再按 `WebFetch → WebSearch → 用户粘贴` 降级并在自检注明。`fixtures/` 下的迷你金样供核对结构与门禁。

## 交付与机检闭环

- **输出路径与命名**：默认写入 `output/{发布日YYYYMMDD} {内容标题}_{实质性短标题}_整理文档.md`（同义省略短标题；存量稿不回溯改名；原标题含 `|` 在元数据表写 `\|`）。若同目录已有下游 `md2html-lecture` 或 `md2wechat` 产物，改名或改内容后须触发对应下游技能同茎重建（见 `templates.md`）。
- **强制验收**：成稿后必跑 `python -B scripts/selfcheck.py {稿}`（修订存量稿前先另存备份，跑 `python -B scripts/selfcheck.py {新稿} --before {备份稿}`）。将机检输出的 `正文中文叙事 / 纯净排版 / 可读性机检 / 判断行证据 / 括注完整`（及修订时的 `修订完整性`）原样贴入文末 `## 自检报告`；逐项完成 4c-2/过译复核、4c-3 实录扫描、原文图清点、声纹与遮名检验、3 处互不重叠「信息覆盖抽样」。**未跑机检或判断行缺证据严禁标 `✅`**（脚本非零退出时必须修复后重跑）。技能维护说明与变更记录见 `CHANGELOG.md`。

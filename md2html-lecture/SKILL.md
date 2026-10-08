---
name: md2html-lecture
description: >-
  Use when converting a finished content-structuring note (usually
  "_整理文档.md") into a single-file lecture HTML, or upgrading existing lecture
  HTML after the template or converter changed. Not for arbitrary Markdown,
  WeChat Official Account HTML (md2wechat), trend briefs (last30days), or
  AI-tool update briefs (ai-agent-update-brief).
---

# md2html-lecture

将完成的 `content-structuring` 整理稿转换为单文件讲义 HTML：浅色/深色主题、
目录、洞察与解析层级、可折叠实录、人物背景和来源面板。转换由脚本完成；
图示由 Agent 根据内容判断后添加。CSS/JS 内联，Mermaid 图形依赖 CDN，
断网时支持的小流程图显示为文本关系。

## 输入与修改边界

- 输入是完成的对谈三层、争辩型访谈或通用模板整理稿。检查 `# 标题`、
  `## 文章元数据`、`## 核心导读` 和正文；元数据应在正文前，包含内容链接。
  文件名后缀只是惯例，是否适用以文稿结构为准。
- 转换前读取 [references/source-shape.md](references/source-shape.md)，核对结构映射。
  上游写作要求由 `content-structuring` 维护，此处不重写。
- 默认输出为源稿同目录、同文件名的 `.html`；也可指定输出路径。
  已有讲义需要重建时使用升级脚本，避免直接覆盖人工添加的图示。
- 为一篇稿件修正明确的格式问题即可；涉及事实、引语或缺失来源的修订应核实，
  不为清除 WARN 编造内容。需要内容重写时回到上游任务。
- 单篇转换不要临时改脚本或全局模板。用户要求维护 Skill 或全局设计时才修改它们。

## 执行流程

### 1. 选择首次转换或已有页面升级

`<skill-dir>` 使用读取此文件时的绝对目录，`<notes-dir>` 使用实际稿件目录。

首次转换（第二个位置参数可指定自定义输出）：

```bash
python "<skill-dir>/scripts/build_html.py" "<notes-dir>/<name>.md"
```

升级一个已经转换的页面：

```bash
python "<skill-dir>/scripts/batch_upgrade_dir.py" "<notes-dir>" --glob "<name>.html"
```

升级目录内的已有页面：

```bash
python "<skill-dir>/scripts/batch_upgrade_dir.py" "<notes-dir>"
```

升级脚本只处理有同名 `.md` 的讲义 HTML，先生成临时页面，恢复图表与页头编辑，
核对章节和锚点后再替换。遇到 WARN、图表恢复不足或转换失败，保留旧 HTML，
报告 FAIL 并返回非零退出码；不得把这类结果描述为升级完成。

新页面记录自动推导的页头值，后续升级只保留被人工修改的字段，其余随源稿更新。
没有记录的旧页面会保留现有页头。若用户希望全部重新推导，添加 `--refresh-header`。
阅读时长和来源文件名始终重新计算。章节改名不按位置猜测图表归属。

遇到告警、章节改名、页头调整或旧 CSS 迁移时，读取
[references/operations.md](references/operations.md)。

### 2. 按需补图并调整页头

- 只有小图能清楚说明流程、分支、并列或对比时才加图，批量升级不自动发明图示。
- 图放在该节核心洞察之后、深度解析之前；没有核心洞察时放在正文 `<h2>` 后。
- 通常 3–6 个节点，中文标签；带标点的标签用双引号，缺失关系用带说明的虚线。
  图不能引入源稿未支持的关系或结论。
- 如需具体 Mermaid 格式或页头字段推导，读取
  [references/operations.md](references/operations.md)。只改页头与图示，正文改动回到源稿。
- 修改全局模板前读取 [references/design-decisions.md](references/design-decisions.md)。

### 3. 验收并交付

读取 [references/verification.md](references/verification.md)，按本次任务选用检查。
每份交付至少确认：

- 正文章节、代码、引语完整；目录锚点能跳到对应章节。
- 人物背景在导读前，来源、术语表、自检报告在末尾对应面板。
- 所有 WARN 已核实处理；升级的保存/恢复图表数一致，没有 FAIL。
- 页头调整符合用户意图，页脚来源匹配当前 `.md` 文件名。
- 在浏览器检查折叠、主题、图示；修改模板或交互时再检查移动端和打印。

修改脚本或模板后运行回归测试（从 Skill 根目录执行）：

```bash
python -X utf8 -m pytest scripts/tests/ -q
```

转换器只需 Python 标准库。测试需要 pytest；浏览器测试还需要 Playwright 和
本地 Chromium/Edge，默认跳过，启用方式见 verification.md。
字符串测试通过不代表浏览器验收通过。

交付时给出 HTML 路径、已完成检查、未解决的告警或失败文件；浏览器检查未执行时
明确说明。遇到失败先解决已报告原因，保留原件，不反复尝试覆盖。

## 资源

- `scripts/build_html.py`：确定性转换器。
- `scripts/batch_upgrade_dir.py`：校验后替换的已有页面升级器。
- `assets/template.html`：全局 CSS/JS 与页面结构。
- `scripts/tests/`：内容保留、升级失败保护和可选浏览器回归。
- `scripts/patch_key_emphasis.py`：仅供旧输出的一次性 CSS 迁移，见 operations.md。

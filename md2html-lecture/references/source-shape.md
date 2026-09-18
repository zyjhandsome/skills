# Source shape the converter understands

Input must be a finished **content-structuring** note. This file only records
how `build_html.py` maps that note onto HTML. Do not treat it as a writing
spec — change the upstream skill when the Markdown contract changes.

## Recognised `## ` titles

Matched by exact name:

| Title | Render |
|---|---|
| `文章元数据` | header fields + collapsed end panel (tables only; bio is moved) |
| `核心导读` | highlight box + summary paragraphs |
| `目录` | dropped (TOC is generated) |
| `延伸术语表` | collapsed `<details>` |
| `自检报告` | hidden `<h2>` + collapsed `<details>` |
| any other `## ` | content section |

Expected 对谈三层 subsections: `核心洞察` / `深度解析` / `对谈实录`.
**`对谈实录` is optional** — omit the whole block when there is no dialogue
worth quoting; the converter skips a missing layer and does not invent an
empty timeline.

Generic-template notes may use `## 关键语录与交锋时刻` instead of per-section
实录. That section renders as a normal content block.

## Skeleton

```markdown
# 标题
## 文章元数据
| 项目 | 内容 |            ← first table = source table (内容链接 holds the URL)
| ...
### 官方章节索引           ← optional extra tables keep their own heading
| 时间 | 章节 |
> **人物背景**：...        ← or **讲者背景**；lifted to article opening
## 核心导读
> **全文论点**：...        ← highlight box (label stripped)
段落…
## 目录                    ← dropped
## <小节标题>
### 核心洞察
> 一句话洞察               ← tip callout
### 深度解析
段落…
### 对谈实录
**讲者**：「台词」          ← timeline step
### 原声交锋               ← 争辩型: clash timeline
**讲者**：「台词」
### 语境与释义             ← 争辩型: prose
### 未决问题               ← 争辩型: warning callout
## 延伸术语表
## 自检报告
```

Block-level Markdown inside 深度解析 / 语境与释义 / 未决问题 is supported:
paragraphs, tables, `-` and `1.` lists, `>` blockquotes, fenced code, and
`*italics*`. Content under an unexpected `### `, or with no `### ` at all, is
rendered under its own heading rather than dropped.

## 争辩型访谈 layers

A section may use `原声交锋` / `语境与释义` / `未决问题` instead of (or
alongside) the three standard layers. The converter renders whichever layers
are present, in this order:

`核心洞察` → `深度解析` → `对谈实录` → `原声交锋` → `语境与释义` → `未决问题`

| Subsection | Renders as | Badge |
|---|---|---|
| `原声交锋` | timeline, same shape as 对谈实录 | 交锋 |
| `语境与释义` | plain prose blocks | 释义 |
| `未决问题` | warning callout | 未决 |

`核心导读` can open with `> **核心冲突**：…` instead of `> **全文论点**：…`.
The highlight box then carries a 核心冲突 pill.

## 文章元数据 with more than one table

The first table is the source table: it feeds the header fields and the
collapsible panel. Any further table under its own `### ` heading (chapter
index, release timeline) is kept below the source table with that heading
intact, not merged into one flat table.

## Placement of 人物背景 / 讲者背景

Source keeps the bio blockquote under `## 文章元数据`. The converter **moves**
it onto the reading path:

```
doc-header (title / subtitle / meta)
  ↓
人物背景 callout   ← who is speaking (info callout, label preserved)
  ↓
核心导读           ← thesis + summary
  ↓
content sections…
  ↓
延伸术语表 / 文章元数据（table only）/ 自检报告
```

Readers need speaker context before the thesis. The end metadata panel keeps
the source table only (no duplicate bio).

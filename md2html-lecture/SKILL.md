---
name: md2html-lecture
description: >-
  Convert a content-structuring "_整理文档.md" (对谈三层结构: 文章元数据 / 核心导读 / 多个
  ## 小节 each with 核心洞察·深度解析·对谈实录, or the debate variant
  原声交锋·语境与释义·未决问题 / 延伸术语表 / 自检报告) into the
  styled, single-file Claude-orange HTML used in this repo's output/ folder.
  Use when asked to turn one of these整理文档 Markdown files into HTML, or to
  batch-convert files under output/ to the lecture HTML format.
---

# md2html-lecture

Converts this repo's content-structuring Markdown notes into a single,
self-contained HTML page (Claude-orange light/dark theme, sticky TOC, layer
pills, timeline, callouts, Mermaid support, collapsible glossary + metadata).

The transform is deterministic and handled by a script. Mermaid diagrams are
**not** in the source Markdown — add them by hand after conversion (see below).

**人物/讲者背景** from `文章元数据` is lifted to the article opening (after the
doc header, before `核心导读`) as an info callout — not buried in the end
metadata panel.

## Files

- `scripts/build_html.py` — the converter (run it; do not rewrite it).
- `scripts/batch_upgrade_dir.py` — re-convert a directory of already-published
  notes against the current template, preserving hand-added Mermaid diagrams.
- `assets/template.html` — the full HTML scaffold (CSS/JS + placeholders). Edit
  this only to change the global design; the script injects content into it.

## Workflow

```
- [ ] 1. Run the converter
- [ ] 2. Add Mermaid diagrams where a section describes a flow/comparison
- [ ] 3. Refine the auto-derived header fields if needed
- [ ] 4. Verify (open in browser + checklist)
```

### 1. Run the converter

```bash
python ".cursor/skills/md2html-lecture/scripts/build_html.py" "output/<name>.md"
```

Output defaults to the same path with `.html`. Pass a second arg for a custom
output path. The script prints `sections`, `cjk` count, and reading time, and
warns if no source URL was found in 文章元数据.

It requires only the Python standard library (no pip installs).

### 2. Add Mermaid diagrams (judgment step)

The source Markdown has no diagrams. Where a section's 深度解析 describes a
**sequence / pipeline / fan-out / comparison**, insert one diagram immediately
**after that section's `<h2>`** and **before** its `核心洞察` `<h3>`:

```html
<figure class="diagram">
  <pre class="mermaid">
flowchart LR
  A[营销产品] --> B[收集申请]
  B --> C[AI 审批]
  C --> D[最终尽调]
  D --> E[执行放款]
  </pre>
  <figcaption class="diagram-caption">一句话说明这张图在表达什么。</figcaption>
</figure>
```

Guidance:
- Keep diagrams small (3–6 nodes). Use `flowchart LR` for sequences, `flowchart
  TD` for one-to-many fan-out. Labels in Chinese.
- Only add a diagram when it genuinely clarifies; not every section needs one.
- Diagrams render inside a card capped at the same reading width as the text
  (the theme handles light/dark colors automatically).

### 3. Refine auto-derived header fields (optional)

The script derives these heuristically; tweak the generated HTML if a file
needs a better fit:

| Field | Derived from | Note |
|-------|--------------|------|
| `doc-title` / `<title>` | `# 标题` | verbatim |
| `doc-eyebrow` | 文稿结构 / 人物数 | "对谈笔记" or "整理笔记" |
| `doc-subtitle` | 核心导读 `> 全文论点` (first clause) | trim if awkward |
| meta source line | 活动/节目/节目名称 短名 + 核心人物/对谈人物/讲者 | e.g. "On Purpose · A × B" |
| meta date | 发布时间 | |
| reading time | CJK chars ÷ 300 | estimate |

### 4. Verify

```
- [ ] 10/N sections present; TOC lists only lvl-2 (no 洞察/解析/实录 sub-links)
- [ ] No stray "<p>---</p>"; 目录 section dropped
- [ ] 人物/讲者背景 (if present) opens the article as an info callout before 核心导读
- [ ] 延伸术语表 and 文章元数据 render as collapsed <details> at the end; extra
      metadata tables keep their own <h3> heading inside the panel
- [ ] 自检报告 is a hidden <h2> + collapsed <details>
- [ ] Mermaid diagrams render (open the file in a browser)
- [ ] Dark mode: toggle theme — no flash on reload; callouts / highlight / strong chips /
      tables / code / Mermaid stay readable (borders + accent-on badges not washed out)
- [ ] Light mode: body links / TOC active use readable terracotta (--link); filled badges
      use --accent-fill + --accent-on (not washed white-on-peach); Mermaid node borders clear
- [ ] Header source line / subtitle read well
```

## Expected source Markdown shape

The converter assumes the content-structuring 对谈三层 format:

```markdown
# 标题
## 文章元数据
| 项目 | 内容 |            ← first table = source table (内容链接 cell holds the URL)
| ...
### 官方章节索引           ← optional extra tables keep their own heading
| 时间 | 章节 |
> **人物背景**：...        ← or **讲者背景**；lifted to article opening
## 核心导读
> **全文论点**：...        ← becomes the highlight box (label stripped)
段落…                      ←导读 summary paragraphs
## 目录                    ← dropped (TOC is auto-generated)
## <小节标题>              ← repeated content sections
### 核心洞察
> 一句话洞察               ← becomes a tip callout
### 深度解析
段落…
### 对谈实录
**讲者**：「台词」          ← each line becomes a timeline step
### 原声交锋               ← 争辩型 only: timeline of the clashing quotes
**讲者**：「台词」
### 语境与释义             ← 争辩型 only: prose unpacking the clash
段落…
### 未决问题               ← 争辩型 only: warning callout
段落…
## 延伸术语表              ← table → collapsed <details>
## 自检报告                ← table → hidden heading + collapsed <details>
```

Section titles `文章元数据 / 核心导读 / 目录 / 延伸术语表 / 自检报告` are matched
by exact name. Any other `## ` section is treated as a content section.

Expected subsections for 对谈三层 notes: `核心洞察` / `深度解析` / `对谈实录`.
**`对谈实录` is optional** — content-structuring omits the whole block when there is
no dialogue worth quoting; the converter simply skips a missing layer (do not invent
an empty timeline). Generic-template notes may use `## 关键语录与交锋时刻` instead
of per-section 实录; that section renders as a normal content block if present.

### 争辩型访谈的第二组分层

When the interview is an argument rather than an explanation, a section may use
`原声交锋` / `语境与释义` / `未决问题` instead of (or alongside) the three
standard layers — the converter renders whichever layers are present, in the
order 核心洞察 → 深度解析 → 对谈实录 → 原声交锋 → 语境与释义 → 未决问题:

| Subsection | Renders as | Badge |
|---|---|---|
| `原声交锋` | timeline, same shape as 对谈实录 | 交锋 |
| `语境与释义` | plain prose blocks | 释义 |
| `未决问题` | warning callout | 未决 |

`核心导读` can open with `> **核心冲突**：…` instead of `> **全文论点**：…`;
the highlight box then carries a 核心冲突 pill. Use it when the thesis is the
disagreement itself.

### 文章元数据 with more than one table

The first table is the source table: it feeds the header fields and the
collapsible panel. Any further table under its own `### ` heading (a chapter
index, a timeline of releases) is kept and rendered below the source table with
that heading intact, instead of being merged into one flat table.

### Placement of 人物背景 / 讲者背景

Source keeps the bio blockquote under `## 文章元数据` (content-structuring
convention). The converter **moves** it to the reading path:

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

Rationale: readers need speaker context before the thesis, not after the whole
article. The end metadata panel keeps the source table only (no duplicate bio).

## Design refinements baked into the template

The template already encodes earlier review decisions — keep them when editing:
- One unified reading measure (`--measure: 75ch`) for all blocks (text,
  callouts, diagrams, timeline, tables) so widths stay consistent.
- TOC shows section titles only (no repeated 洞察/解析/实录 links); bio label
  appears as the first TOC entry when present.
- No per-section jump-pill row (`injectSectionJumps` is intentionally not called).
- Tight 对谈实录 spacing.
- Key-info hierarchy: body `strong` uses soft accent chip; thesis `.highlight`
  is stronger (border/shadow + CSS `全文论点` pill); `.section-insight` tip
  callouts get a left accent bar + slightly larger type. Speaker bio / timeline /
  info-callout `strong` stay calm (no chip) so names and quotes do not flood.
- 延伸术语表 + 文章元数据 collapsed by default.
- Speaker bio uses `callout-info` (blue), distinct from tip insights (orange)
  and the thesis highlight.
- Dark theme: head script sets `data-theme` before paint (no FOUC); `color-scheme`
  follows theme; raised `--border` / `--code-bg`; `--accent-on` for text on accent
  fills; Mermaid uses `theme: "base"` + warm Claude palette variables.
- Light theme: body links / TOC use `--link` / `--link-hover` (AA terracotta, not the
  softer brand peach); solid badges use `--accent-fill` + `--accent-on`; topbar has a
  solid `--bg` fallback before `color-mix` glass.

## Batch conversion

To convert several files, run the script once per `.md`. Then do the Mermaid +
header pass per file. Do not auto-add diagrams in batch — that step needs
per-file judgment.

To re-publish notes that were already converted, after the template or the
converter changed:

```bash
python ".cursor/skills/md2html-lecture/scripts/batch_upgrade_dir.py" "<notes-dir>"
```

It walks `<notes-dir>` for `*_整理文档.html` files that still have a sibling
`.md`, saves each hand-added `<figure class="diagram">` under the `<h2>` it
follows, re-runs the converter, and puts those diagrams back. `--glob` changes
the filename pattern and `--build` points at another converter; both default
sensibly. It never invents a diagram, so a section that had none stays plain.

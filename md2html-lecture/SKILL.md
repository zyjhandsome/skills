---
name: md2html-lecture
description: >-
  Use when asked to convert a content-structuring "_整理文档.md" into the
  single-file lecture HTML, or to batch-upgrade already-published lecture HTML
  after the template or converter changed. Not for generic Markdown, WeChat
  Official Account HTML (md2wechat), last-30-days trend briefs, or AI-tool
  update briefs.
---

# md2html-lecture

Converts a finished content-structuring 整理文档 into a single-file HTML page
(Claude-orange light/dark theme, sticky TOC, layer pills, timeline, callouts,
Mermaid support, collapsible glossary + metadata). CSS and JS are inline; only
Mermaid loads from a CDN, so diagrams need network to render.

The transform is deterministic and handled by a script. Mermaid diagrams are
**not** in the source Markdown — add them by hand after conversion.

**REQUIRED UPSTREAM:** Input must be a finished **content-structuring** note
(对谈三层, 争辩型访谈, or generic-template). Do not restate that writing spec
here. How this converter maps it to HTML: [source-shape.md](references/source-shape.md).

**人物/讲者背景** from `文章元数据` is lifted to the article opening (after the
doc header, before `核心导读`) as an info callout.

## When not to use

- Generic or arbitrary Markdown → HTML
- WeChat Official Account paste HTML → **md2wechat**
- Trend / last-30-days briefs → **last30days**
- AI-agent update HTML briefs → **ai-agent-update-brief**
- Notes that are not a content-structuring `_整理文档.md`

## Files

- `scripts/build_html.py` — the converter (run it; do not rewrite it).
- `scripts/batch_upgrade_dir.py` — re-convert a directory of already-published
  notes against the current template, preserving hand-added Mermaid diagrams.
- `assets/template.html` — the full HTML scaffold (CSS/JS + placeholders). Edit
  this only to change the global design; the script injects content into it.
- `scripts/tests/test_build_html.py` — regression tests guarding "no silent
  content drops" plus 争辩型 layers. Run after touching either script:
  `python -m pytest scripts/tests/ -q` (needs pytest; the converter itself
  needs only stdlib).
- `scripts/patch_key_emphasis.py` — one-shot CSS migration for HTML published
  before the key-info emphasis pass. The template already includes it; only run
  it against old output files.
- [references/source-shape.md](references/source-shape.md) — heading map, optional
  实录, 争辩型 layers, extra metadata tables, bio placement.
- [references/design-decisions.md](references/design-decisions.md) — load only
  when editing the template.

## Workflow

```
- [ ] 1. Run the converter
- [ ] 2. Add Mermaid diagrams where a section describes a flow/comparison
- [ ] 3. Refine the auto-derived header fields if needed
- [ ] 4. Verify (open in browser + checklist)
```

### 1. Run the converter

```bash
python "<skill-dir>/scripts/build_html.py" "<notes-dir>/<name>.md"
```

`<skill-dir>` is the folder holding this SKILL.md — usually
`~/.cursor/skills/md2html-lecture` for a personal install, or
`.cursor/skills/md2html-lecture` when the skill is vendored into a repo. Use the
absolute path you loaded this file from rather than guessing. `<notes-dir>` is
wherever the 整理文档 lives in the current workspace (often `output/`, not
always).

Output defaults to the same path with `.html`. Pass a second arg for a custom
output path. The script prints `sections`, `cjk` count, and reading time, and
warns if no source URL was found in 文章元数据.

It requires only the Python standard library (no pip installs).

**Re-running the converter on a file overwrites hand-added Mermaid diagrams.**
To rebuild an already-published note, use `batch_upgrade_dir.py` (see below),
which saves and restores them.

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
- [ ] every `## ` content section present (compare the script's `sections=` count
      with the source); TOC lists only lvl-2 (no 洞察/解析/实录 sub-links)
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

## Common mistakes

| Mistake | Do this instead |
|---|---|
| Hand-write the whole HTML page from the template | Run `build_html.py` |
| Rewrite or patch the converter for one file | Fix the source Markdown, or edit the generated HTML for header/diagram only |
| Auto-add Mermaid while batch-converting | Diagrams need per-file judgment; batch never invents them |
| Ignore `WARN: no source URL` | Restore 内容链接 in 文章元数据, then re-run |
| Use this as a generic md2html | Stop; see When not to use |

## Batch conversion

To convert several files, run the script once per `.md`. Then do the Mermaid +
header pass per file. Do not auto-add diagrams in batch — that step needs
per-file judgment.

To re-publish notes that were already converted, after the template or the
converter changed:

```bash
python "<skill-dir>/scripts/batch_upgrade_dir.py" "<notes-dir>"
```

It walks `<notes-dir>` for `*_整理文档.html` files that still have a sibling
`.md`, saves each hand-added `<figure class="diagram">` under the `<h2>` it
follows, re-runs the converter, and puts those diagrams back. `--glob` changes
the filename pattern and `--build` points at another converter; both default
sensibly. It never invents a diagram, so a section that had none stays plain.

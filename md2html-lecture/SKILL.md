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
`WARN:` lines for problems in the source Markdown it cannot fix itself:

| WARN | Fix in the .md, then re-run |
|---|---|
| no source URL | restore 内容链接 in 文章元数据 |
| none is marked「主持」 | add「主持人」to the host's note in 对谈人物 (else no host color). `×` and `；` / `;` split people only outside `（）` / `()`, so a semicolon inside one person's note does not drop the host |
| duplicated blockquote | delete the repeated 事实边界 / quote block |
| editor note ［…］ | a process note (ASR/字幕/核对/编者注) or a >20-char aside leaked into the body: move it into 自检报告 or rewrite as reader prose. Short tags like ［预测］［编者推断］［主持人口播］ are intended and never flagged. A closed halfwidth `[编者注：…]` is left as written |
| unclosed editor note | `[编者注` / `[ASR` / `［编者注` (same process-note words) opened and not closed before the blank line: close it in the .md. The converter does not close it |
| orphan closing bracket | a line that is only `]` or `］`: join it back onto the note |
| bracket leaked into dialogue | a 实录 line whose quote starts with `]` / `］`, including `「]」`: that closer was turned into speech. Restore the note in the .md; the converter still prints the line |

Treat every WARN as a to-do before publishing.

It requires only the Python standard library (no pip installs).

**Re-running the converter on a file overwrites hand-added Mermaid diagrams.**
To rebuild an already-published note, use `batch_upgrade_dir.py` (see below),
which saves and restores them. To rebuild just one note, pass its filename as
the glob: `batch_upgrade_dir.py "<notes-dir>" --glob "<name>.html"`.

**If the `.md` is renamed after publishing** (for example a longer descriptive
stem), rename the `.html` to the same stem *and* rebuild it: the footer
`来源:` line is derived from the source filename at build time and will
otherwise keep pointing at a file that no longer exists. The companion 公众号
files from `md2wechat` must be regenerated too (their fingerprint and filename
stem are both checked against the `.md`).

### 2. Add Mermaid diagrams (judgment step)

The source Markdown has no diagrams. Where a section's 深度解析 describes a
**sequence / pipeline / fan-out / comparison**, insert one diagram immediately
**after that section's 核心洞察 callout** (`<div class="callout callout-tip
section-insight">…</div>`) and **before** its `深度解析` `<h3>` — conclusion
first, then the picture that explains it. In a section without 核心洞察, put it
right after the `<h2>`:

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
- Quote any label that carries punctuation: `D["护士、电工、教师"]`, not
  `D[护士电工教师]`. Gluing nouns together to dodge the quotes makes the node
  unreadable; `、` `，` `：` are all fine inside `["…"]`.
- A relation the speaker says is *absent* or *missing* is a dotted, labelled
  edge: `A -. 没有被培植 .-> D["中间：…"]`. The caption then states the gap.
- Typical shapes worth a picture: a "what to learn / what to do" list the
  speaker enumerates (fan-out), two poles with an empty middle, a two-path
  fork with different outcomes. A section whose 深度解析 already has a table
  usually does not need a diagram too.
- Only add a diagram when it genuinely clarifies; not every section needs one.
- Diagrams render inside a card capped at the same reading width as the text
  (the theme handles light/dark colors automatically). When the Mermaid CDN
  cannot be reached, the page renders each edge as a plain `A → B` line (dotted
  edges as `A ⇢（label）B`), so the diagram still reads offline; the caption
  must therefore make sense next to that text form too.

### 3. Refine auto-derived header fields (optional)

The script derives these heuristically; tweak the generated HTML if a file
needs a better fit:

| Field | Derived from | Note |
|-------|--------------|------|
| `doc-title` / `<title>` | `# 标题` | verbatim |
| `doc-eyebrow` | 文稿结构 / 人物数 | "对谈笔记" or "整理笔记" |
| `doc-subtitle` | left empty (hidden) — the 全文论点 box already states the thesis | do not refill it with the thesis |
| meta source line | 活动/节目/节目名称 短名 (else 对谈人物 host note "X 主持人" → X, else 原标题) + 核心人物/对谈人物/讲者 | e.g. "On Purpose · A × B" |
| dialogue colors | 对谈人物: entry noted「主持」→ host; others guest-1..4 | mark the host in 对谈人物 |
| meta date | 发布时间 | the `（…口径/抓取…）` parenthetical and any `；` tail are dropped from the header; the full field stays in the 文章元数据 panel |
| reading time | CJK chars ÷ 300 | estimate |

### 4. Verify

```
- [ ] every `## ` content section present (compare the script's `sections=` count
      with the source); TOC lists only lvl-2 (no 洞察/解析/实录 sub-links)
- [ ] No stray "<p>---</p>"; 目录 section dropped
- [ ] 人物/讲者背景 (if present) opens the article as an info callout before 核心导读
- [ ] 延伸术语表 and 文章元数据 render as collapsed <details> at the end; extra
      metadata tables keep their own <h3> heading inside the panel
- [ ] 自检报告 is a hidden <h2> + collapsed <details>, and keeps its ### blocks
      (人物声纹 / 遮名检验 …) instead of one merged table
- [ ] Dialogue: the real host has the host color (not whoever spoke first); every
      speaker (3+ included) has a distinct color; consecutive turns are merged
- [ ] Layer headings show a single pill (not "洞察 核心洞察")
- [ ] No duplicated 事实边界 blocks; no editor notes (［…］, ASR/核对说明) in
      导读 or 深度解析 — those belong in 自检报告 (fix the .md, then rebuild)
- [ ] Footer "来源" matches the current .md filename
- [ ] The build printed no WARN lines (or each was fixed in the .md)
- [ ] Every block's outer edge aligns to one column (headings, bio, thesis,
      insight, 事实边界, diagrams, dialogue, tables, panels, footer). A top-level
      `.table-wrap` is `--measure` wide, the same edge as the paragraph above
      it; it does not stretch to the grid column. Glossary and metadata tables
      stay inside their panel, which is already on that measure. A table that
      truly cannot fit uses `.full-bleed`, not a wider default column.
- [ ] TOC and section `<h2>` show the same numbers (01, 02 …); bio / 导读 /
      术语表 are unnumbered. A source heading `## 3. 标题` shows that one number,
      not `03` plus `3.`. Headings that start with `12%` or `2012 年` keep those digits
- [ ] 「只看要点」 is the arrival state: every 实录 / 交锋 block starts closed,
      the button is pressed, and one click opens them all; each fold can still
      be re-opened on its own; a saved "show transcript" choice is restored;
      print expands everything
- [ ] 「只看嘉宾」 appears only on notes with a host-colored speaker; pressing it
      hides every `.step.speaker-host` turn (guest turns stay), the choice is
      restored on reload, and it is off by default
- [ ] Diagrams sit after 核心洞察, before 深度解析
- [ ] Mermaid diagrams render (open the file in a browser)
- [ ] Offline fallback: with the CDN blocked (DevTools → block
      `cdn.jsdelivr.net`, or `delete window.mermaid; renderMermaid()`), each
      diagram shows readable `A → B` lines, not raw Mermaid source
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
| Ignore `WARN:` lines | Fix the source .md (see the WARN table in step 1), then re-run |
| Patch duplicates / editor notes in the generated HTML | Fix the .md — a rebuild would bring them back |
| Hand-delete a leading `1. ` from the generated `<h2>` | The converter already strips a section index (`N. ` / `N．`) from the visible title and TOC. Anchors stay on the original heading |
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

It walks `<notes-dir>` for converter-generated `.html` files (footer
"Generated by md2html", any suffix such as `_整理文档` or `_项目式学习`; 公众号
HTML is skipped) that still have a sibling `.md`, saves every hand-added
`<figure class="diagram">` of each section (wherever it sat), re-runs the
converter, and puts those diagrams back after the section's 核心洞察. `--glob` changes
the filename pattern and `--build` points at another converter; both default
sensibly. It never invents a diagram, so a section that had none stays plain.

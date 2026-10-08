# Template decisions — keep when editing `assets/template.html`

Read this only when changing the global design. The converter injects content
into the template; do not re-encode these rules in `build_html.py`.

- One unified reading measure (`--measure: 44rem`, ~44 CJK chars at 16px) for
  all blocks (headings, text, callouts, thesis, diagrams, timeline, tables,
  footer) so every outer edge aligns. Keep it a fixed length — `ch` resolves
  per element font-size and makes smaller-type boxes narrower. Inner text
  may be narrower (padding, avatar indent); outer edges may not differ.
  Use `.full-bleed` for a deliberately column-wide table or diagram.
  `.table-wrap { max-width: 100% }` only fills a parent that is already on
  the measure (glossary, metadata). A body table is also `.content > .table-wrap`;
  that rule matches `.content > *` in specificity and comes later, so the
  template restates `.content > .table-wrap, .content > table { max-width: var(--measure); }`
  immediately after it. Dropping that restatement stretches body tables to the
  grid column (~900px) while prose stays at 44rem. Do not widen the default
  column to split the difference, and do not shrink tables to their content.
- TOC shows section titles only (no repeated 洞察/解析/实录 links); the bio
  label is the first TOC entry when present.
- No per-section jump-pill row (`injectSectionJumps` is intentionally not
  called).
- Dialogue inside a turn uses 15.5px / line-height 1.8, with 16px between
  paragraphs and 12px between turns, so a long monologue is not one slab.
  Quotes use body color — they are evidence, not captions. Speaker names are
  `<p class="step-speaker">`, never headings (keeps the h3 outline to the
  three layers).
- Speaker roles are assigned by `build_html.py`, not JS: host = the 对谈人物
  entry whose note contains「主持」; others `speaker-guest-1..4` in 对谈人物
  order, then first appearance. People are split on `×` and on `；` / `;`
  only outside parentheses, so `（本场主持人；某公司首席执行官）` stays one
  person. Avatars show initials; consecutive turns by one speaker share one
  step.
- Layer headings (`洞察/解析/实录/…`) show only the pill; the rule must be
  `.content h3.layer-heading` or `.content h3` wins and both render.
- CJK typography: no italic blockquotes (faux-oblique CJK), no negative
  letter-spacing on headings, body line-height 1.78, `lang="zh-CN"`.
- No decorative motion (brand-dot pulse, step hover) on a long-read page.
- Print opens every `<details>` (beforeprint) and restores them afterwards.
- 对谈实录 / 原声交锋 are each one `<details class="dialogue-fold">` (closed
  on arrival) whose `<summary>` holds the layer h3 + "N 轮发言". Topbar
  「只看要点」 starts pressed. Clicking it opens or closes every fold,
  remembers the choice (localStorage, including an explicit "show the
  transcript"), and keeps the current h2 at the same screen position
  (disable `overflow-anchor` while toggling, or the browser's own scroll
  anchoring doubles the correction). Print still opens every panel.
- TOC: desktop links are 30px min-height (drawer keeps 36px touch targets) so
  15–20 entries fit; the TOC scrollbar is transparent until hover/focus (a
  TOC that overflows by a few px otherwise shows a near-full-height thumb that
  reads as a divider); scrollspy keeps the active entry inside the TOC.
- 「只看要点」 state is stored per note (`md2html-skim:` + pathname), never
  globally — all local files share one storage origin.
- 「只看嘉宾」 is a second topbar toggle, off by default, shown only when the
  note has a host-colored speaker. It adds `body.guest-only`, which hides
  `.step.speaker-host` turns so a reader can read the guest's voice straight
  through; it never deletes or reorders content, and it is stored per note
  (`md2html-guest-only:` + pathname) like skim. Print is unaffected (the body
  class is a reader filter, not a print state).
- Mermaid still loads from the CDN (an inline copy would add ~2 MB per note),
  but when `mermaid` is undefined at render time each `.mermaid` block is
  rewritten as plain `A → B` lines (`mermaidTextFallback`: node ids replaced
  by their labels, dotted edges as `A ⇢（label）B`) with class
  `.mermaid-fallback`, instead of showing raw source at 40 % opacity. Sources
  are cached in `diagramSources` before any rewrite so a later theme toggle
  can still re-render the real diagram.
- Content sections are numbered by CSS counters in both TOC (`.toc-sec`) and
  body (`h2.sec`), so numbers never drift from order and are not copied as text.
- No subtitle under the title: it could only repeat the 全文论点.
- System font stack only (no Google Fonts): CJK always came from system fonts;
  the web font was slow/blocked in mainland China and failed offline.
- Mermaid diagrams sit after 核心洞察 (conclusion first, then the picture).
- Key-info hierarchy: body `strong` uses a soft accent chip; thesis
  `.highlight` is stronger (border/shadow + CSS `全文论点` pill);
  `.section-insight` tip callouts get a left accent bar + slightly larger
  type. Speaker bio / timeline / info-callout `strong` stay calm (no chip) so
  names and quotes do not flood.
- 延伸术语表 + 文章元数据 collapsed by default.
- Speaker bio uses `callout-info` (blue), distinct from tip insights (orange)
  and the thesis highlight.
- Dark theme: head script sets `data-theme` before paint (no FOUC);
  `color-scheme` follows theme; raised `--border` / `--code-bg`; `--accent-on`
  for text on accent fills; Mermaid uses `theme: "base"` + warm Claude palette
  variables.
- Light theme: body links / TOC use `--link` / `--link-hover` (AA terracotta,
  not the softer brand peach); solid badges use `--accent-fill` +
  `--accent-on`; topbar has a solid `--bg` fallback before `color-mix` glass.

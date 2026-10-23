# Template decisions — keep when editing `assets/template.html`

Read this only when changing the global design. The converter injects content
into the template; do not re-encode these rules in `build_html.py`.

- Eye comfort (long reads): body text targets ~13:1 contrast in light and dark
  (`#2B2A27` on `#F7F5EF`, `#E3DCD0` on `#1A1714`), not 16:1+ — pure-black
  on white glares and near-white on dark halates. `--surface` sits barely
  above `--bg` so cards are not brighter patches. Dark semantic hues are
  desaturated. Check new colors: text ≥10:1, muted/subtle/links ≥4.5:1.
- Three themes in a menu: sepia (护眼, warm paper `#F4ECD8`, the default and
  the `data-theme` the page ships with), reader (阅读, paper on a screen),
  dark (also the default when the OS prefers dark). 浅色 and 墨水屏 were
  dropped by the owner; the head script maps a stored `light` → sepia and
  `eink` → reader so returning readers keep a close look. `:root` still holds
  the light tokens as the base every theme overrides. The button icon shows
  the current theme; the menu is a `menuitemradio` list with arrow/Escape
  keys. Mermaid colors come from `MERMAID_PALETTES[theme]`, so a new theme
  needs a palette entry there too.
- Book setting for `.content p, li`: `text-align: justify`,
  `line-break: strict` (no 。，」 at line start), `text-autospace: normal`.
- Reading module (`setupReading`) builds one ordered list of leaf blocks
  (h2/h3/p/li/pre/figure/tr) and drives three things:
  - Status pill「本节剩余约 N 分钟 · 全文 X%」: CJK chars at 300/min, the
    same pace as the header estimate; counts only visible blocks, so closed
    folds and 只看嘉宾 change it. Text is only rewritten when it changes.
    Centered below 1280px, in the right margin above it.
  - Position memory per note (`md2html-pos:` + pathname, block index +
    24-char snippet + section id, so it survives upgrades that shift
    blocks). Saving starts only after the reader scrolls, or the first paint
    at the top would erase it. On load a toast offers「继续阅读」 unless the
    URL has a hash or the browser already restored the spot; resuming opens
    the fold that holds the block. No automatic jump.
  - Immersive chrome: topbar slides away scrolling down past 240px and
    returns on any upward scroll, near the top, or pointer within 64px of
    the top. The TOC never dims (a faded TOC reads as disabled). Stays put while the TOC
    drawer or settings panel is open, or the topbar has keyboard
    (`:focus-visible`) focus — not plain focus, since a clicked button
    keeps focus and would pin the bar.
- Topbar: 「A− / 100% / A+」, a theme button (icon follows the theme) with a
  one-column dropdown (swatch + name + one-line hint; a pick closes it), and
  「Aa」 for typesetting only. One combined panel with theme + size + five rows
  of segments was tried and read as too busy; keep theme and size one click
  away and the panel short. No 每行 option — the measure is a design
  decision, not a reader knob.
- 「Aa」 holds 字体 (默认/黑体/宋体/楷体), 行距, 段落 (段间空行/首行缩进), 翻页
  (滚动/整屏翻页); ≤600px it also takes A−/A+, which leave the topbar. Selected
  segments use the soft accent, not a solid fill, to keep the panel quiet. Each
  non-default choice is a `data-font|lh|para|flip` attribute on
  `html`, stored together in `md2html-read-settings` and whitelisted by the
  head script before first paint; the empty value is the default and removes
  the attribute. Font choice applies to `.content` only — headings stay sans,
  code mono. Changing a setting keeps the current block under the reading
  line. Both popovers sit after `</header>`, not inside the topbar: the
  topbar's `backdrop-filter` makes it the containing block of any
  `position: fixed` child. JS pins them under their button on open; only one
  is open at a time. ≤600px 「Aa」 becomes a bottom sheet.
- 整屏翻页 is off by default (scroll). Opting in turns pages with Space /
  PageDown / → and Shift+Space / PageUp / ← only. A click never turns a page —
  readers click the text to focus or select, and that was jumping them ahead.
  Turns align to lines: a line cut by the bottom edge opens the next page at
  the 12px top margin; a fully visible last line scrolls fully off (no sliver
  of half-glyphs at the top). The topbar stays hidden past 240px while paging
  and returns when the pointer is within 64px of the top.
- 阅读 (reader) imitates e-ink paper: grayscale only (every semantic hue
  maps to ink, soft fills go transparent), no shadows/gradients/transitions/
  smooth scroll/backdrop blur (e-ink ghosts on repaint), body `strong` is
  weight only. Body text uses `--font-serif` (Georgia for Latin, then
  Noto Serif SC → Source Han Serif → Songti SC → STSong → SimSun); headings,
  summaries, speaker names and tags stay sans, code stays mono. Speakers
  lose their colors, so the host badge is solid ink to stay distinct.
- Body 17px, dialogue 16.5px, callouts 15.5px, tables 15px; no reading text
  below 12px. All reading type is rem so 「A− / A+」 (`--fs-scale` on `html`,
  0.9–1.3, stored globally in `md2html-font-scale`) scales everything,
  including the measure. The middle button shows the current scale ("120%")
  and resets to 100% (disabled at 100%). Only topbar chrome (brand, toggles,
  A−/100%/A+) keeps px so the controls do not grow. Print resets the scale.
  ≤600px hides the print button and brand label to fit.
- Body `strong` is borderless and faint (40+ marks per note would otherwise
  be a field of outlined orange chips); the thesis and section-insight keep
  bordered chips, so the hierarchy holds.
- `-webkit-font-smoothing: antialiased` only in dark (it washes out dark text
  on light paper on macOS).
- `.layout` is capped at TOC + gap + measure and centered, so on wide screens
  the spare width splits evenly on both sides instead of a blank band right of
  the text. The grid column therefore equals the measure. The TOC track is
  `clamp(200px, 100vw - 36rem - gap - padding, 220px)` with a 32px gap: it
  stays 220px while the article can hold about 34 CJK characters, then
  narrows only to 200px so titles still wrap to two lines. The off-canvas
  drawer starts at 760px (`isMobileToc`
  uses the same query) so a snapped window still shows titled sections.
- One unified reading measure (`--measure: 50rem`, ~47 CJK chars at 17px)
  for all blocks (headings, text, callouts, thesis, diagrams, timeline, tables,
  footer) so every outer edge aligns. There is no 每行 control. Keep the
  length in rem, not `ch` — `ch` resolves per element font-size and makes
  smaller-type boxes narrower. Inner text may be narrower (padding, avatar
  indent); outer edges may not differ.
  Use `.full-bleed` for a deliberately column-wide table or diagram.
  `.table-wrap { max-width: 100% }` only fills a parent that is already on
  the measure (glossary, metadata). A body table is also `.content > .table-wrap`;
  that rule matches `.content > *` in specificity and comes later, so the
  template restates `.content > .table-wrap, .content > table { max-width: var(--measure); }`
  immediately after it. Dropping that restatement stretches body tables to the
  grid column on narrower windows while prose stays at the measure. Do not widen the default
  column to split the difference, and do not shrink tables to their content.
- TOC shows section titles only (no repeated 洞察/解析/实录 links); the bio
  label is the first TOC entry when present.
- No per-section jump-pill row (`injectSectionJumps` is intentionally not
  called).
- Dialogue inside a turn uses 16.5px / line-height 1.8, with 16px between
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
  (`md2html-guest-only:` + pathname) like skim. Print CSS explicitly restores
  host turns as grid items, while beforeprint expands folds; afterprint restores
  the folds and the reader's guest-only filter still applies on screen.
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
- `lecture-header-defaults` is a non-executable JSON snapshot of auto-derived
  header contents. Keep it in the template: upgrades compare current fields
  against this snapshot to preserve manual edits while refreshing other fields.
  Reading time and the source footer always follow the current Markdown.
- System font stack only (no Google Fonts): CJK always came from system fonts;
  the web font was slow/blocked in mainland China and failed offline.
- Mermaid diagrams sit after 核心洞察 (conclusion first, then the picture).
  Source charts are different: a standalone Markdown image or video line
  becomes `figure.source-figure` where the note placed it. The image link
  has no underline. Video is width-capped, with a dark letterbox before play.
  These figures are not hand diagrams and are not moved on upgrade.
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

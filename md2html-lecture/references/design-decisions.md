# Template decisions — keep when editing `assets/template.html`

Read this only when changing the global design. The converter injects content
into the template; do not re-encode these rules in `build_html.py`.

- One unified reading measure (`--measure: 75ch`) for all blocks (text,
  callouts, diagrams, timeline, tables) so widths stay consistent.
- TOC shows section titles only (no repeated 洞察/解析/实录 links); the bio
  label is the first TOC entry when present.
- No per-section jump-pill row (`injectSectionJumps` is intentionally not
  called).
- Tight 对谈实录 spacing.
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

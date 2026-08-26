# WeChat HTML constraints (paste target)

## Hard rules

1. **No** external CSS / `<link>` / page-level `<style>` inside the **copied** article body.
2. **All** visual rules go on `style="..."` attributes.
3. **No** JavaScript, SVG sprite refs, localStorage theme toggles.
4. Prefer `section` / `p` / `h1–h3` / `strong` / `span` / `a` / `img`.
5. Lists (`ul`/`ol`) are flaky → prefer numbered paragraphs.
6. Body **GFM tables**: never leave `| col |` as `<p>`.
   - `editorial` mode → rewrite the comparison as sentences so audio listeners receive the conclusion.
   - `full` mode → convert as follows.
   - ≤4 columns → `<table cellspacing="0" cellpadding="0">` with **inline styles on every `td`**. Use `td` for header row too (`th` is often stripped/restyled).
   - ≥5 columns → stacked cards (`section` + labeled `p`); native tables overflow on phone.
   - Header row: accent-soft `#FBEEE6` / accent-strong text; body: white + border `#E5E4DC`.
7. Mermaid / complex diagrams → **PNG** (`img` with inline width style). After paste, WeChat may re-upload images; if paste drops images, upload PNGs manually in the editor.

## Safe inline CSS (commonly kept)

`color`, `background` / `background-color`, `font-size`, `font-weight`, `font-family`, `line-height`, `letter-spacing`, `text-align`, `margin`, `padding`, `border`, `border-radius`, `max-width`, `width`

## Risky / often stripped

`position: fixed`, animations, `@media`, CSS variables, `class`/`id` selectors (IDs OK for local preview but styles must not depend on them after paste), flex/grid (sometimes OK, prefer simple block layout for cards).

## Theme tokens (default)

| Token | Hex |
|-------|-----|
| bg | `#FAFAF7` |
| text | `#1A1A1A` |
| muted | `#4A4A45` |
| subtle | `#6B6B66` |
| accent | `#D97757` |
| accent-soft | `#FBEEE6` |
| accent-border | `#F0D5C4` |
| accent-strong | `#A85533` |
| surface | `#FFFFFF` |
| border | `#E5E4DC` |

## Cover ratio and type

- Target **2.35:1** (WeChat 首图常见比).
- Export size recommendation: **1175 × 500**.
- GenerateImage supports `16:9` etc. → generate wide, then `make_cover_235.py` center-crop.
- **Type is overlay-only.** Image model must not paint letters. `--title` is the article H1, which defaults to the source H1. `overlay_cover_text.py` uses 华文中宋 / Noto Serif (`#A85533`, tracked), a 56×2 hairline, and a sans people line (`#B09480`). Never Microsoft YaHei + `#1A1A1A` on the cover.

## Paste checklist

1. Select only `#wechat-article` (beige card), not the howto chrome.
2. Paste into 图文正文.
3. If title duplicates, delete one.
4. Mobile preview before publish.

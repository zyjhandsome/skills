# Examples

## Naming

Source:

```
20260730 YC Startup School_Alexandr Wang谈内部罗盘与前沿实验室重建_整理文档.md
```

Deliverables (same filename, suffix only):

```
20260730 YC Startup School_Alexandr Wang谈内部罗盘与前沿实验室重建_整理文档_公众号文章.html
20260730 YC Startup School_Alexandr Wang谈内部罗盘与前沿实验室重建_整理文档_公众号封面.png
```

Cover **text** is centered on the image: H1 on top, speakers underneath, no white plate. Cover **filename** follows the source file.

Do not leave 成稿、审计、完整版 HTML，or `*_公众号封面_2.35x1.png` in the source directory.

## Full-mode omit / keep (from production trial)

**Keep:** H1, 人物背景, 核心导读, all body sections with 核心洞察 / 深度解析 / 对谈实录 labels, 来源与说明 with 原文 only.

**Omit:** 元数据表 rows, 目录, 延伸术语表, 自检报告, 「完整整理版｜微信排版」eyebrow, long legal footer, 视频链接, 编辑说明, **过程流水账**. 副标题不要直接截断「内容来源」格.

**Subtitle:** `讲者 · 公开场次`，例如 `Garry Tan · Y Combinator · Startup School 2026`.

**Source footer:** `原文：{原标题}` only.

**Body tables:** GFM `| col |` in 深度解析 etc. → inline-styled `<table>` (≤4 cols) or stacked cards (≥5 cols). Do not paste raw pipes.

## Cover prompt skeleton

Do **not** ask the image model to draw the title. The generated scene must stay wordless; `overlay_cover_text.py` is the only source of type (serif terracotta title, hairline, tracked people line). Filename = `{原文文件名}_公众号封面.png`.

```
Ultra-wide WeChat cover illustration for a 2.35:1 crop. Cream #FAFAF7
background, terracotta #D97757 accents. Put the metaphor on the LEFT and
RIGHT sides. Keep the exact vertical and horizontal CENTER empty — a large
quiet cream field with no objects — for later typography.

Absolutely no text, no letters, no Chinese characters, no numbers, no
arrows, no UI, no logos, no captions, no watermarks, no white plates,
no purple neon.
```

After crop, overlay the real H1 (never a punchier rewrite):

```bash
python scripts/make_cover_235.py generated.png --out "{原文文件名}_公众号封面.png"
python scripts/overlay_cover_text.py "{原文文件名}_公众号封面.png" --title "{H1}" --people "{人物}"
```

Target type (already encoded in the overlay script): title `#A85533` 华文中宋 with tracking; people `#B09480` sans with wider tracking; a short hairline between them. Do not switch back to Microsoft YaHei + `#1A1A1A`.

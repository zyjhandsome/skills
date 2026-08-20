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

Cover text is embedded in the image center: H1 title on top, speakers underneath, no white background. Filename = `{原文文件名}_公众号封面.png`.

```
Ultra-wide WeChat cover for 2.35:1 crop. Cream #FAFAF7 background,
terracotta #D97757 accents. Leave the vertical and horizontal center
clear for later text. No captions, no logos, no purple neon, no white
text plates in the generated scene.
```

After crop, overlay text only (no plate):

```bash
python scripts/make_cover_235.py generated.png --out "{原文文件名}_公众号封面.png"
python scripts/overlay_cover_text.py "{原文文件名}_公众号封面.png" --title "{H1}" --people "{人物}"
```

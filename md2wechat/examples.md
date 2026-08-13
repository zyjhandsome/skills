# Examples

## Naming

Source:

```
20260730 YC Startup School_Alexandr Wang谈内部罗盘与前沿实验室重建_整理文档.md
```

Outputs:

```
…_公众号完整版.html
…_公众号封面_2.35x1.png
```

## Default omit / keep (from production trial)

**Keep:** H1, 人物背景, 核心导读, all body sections with 核心洞察 / 深度解析 / 对谈实录 labels, short 来源（原文 + 视频）.

**Omit:** 元数据表 rows, 目录, 延伸术语表, 自检报告, 「完整整理版｜微信排版」eyebrow, long legal footer.

**Body tables:** GFM `| col |` in 深度解析 etc. → inline-styled `<table>` (≤4 cols) or stacked cards (≥5 cols). Do not paste raw pipes.

## Cover prompt skeleton

```
Ultra-wide WeChat cover for 2.35:1 crop. Cream #FAFAF7 background,
terracotta #D97757 accents. Chinese title: 「{金句}」. Small eyebrow:
「{来源人物}」. Compass / metaphor visual, no purple neon, no logos.
Keep title in vertical center safe band.
```

Then:

```bash
python scripts/make_cover_235.py generated.png --out "{stem}_公众号封面_2.35x1.png"
```

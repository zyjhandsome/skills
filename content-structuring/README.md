# content-structuring

**内容结构化整理** — 将视频字幕、播客文稿、YouTube/B 站链接、X/Substack/Medium 长文、访谈逐字稿等素材，整理成读者不必回到原内容也能掌握绝大多数关键信息的中文 Markdown 深度文章。

- **当前版本**：v5.22
- **入口文件**：[`SKILL.md`](./SKILL.md)
- **完整规范**：[`references/spec.md`](./references/spec.md)

## 目录结构

```
content-structuring/
├── SKILL.md                          # 技能加载器（Agent 首先读取）
├── references/
│   └── spec.md                       # 完整规则、模板与验收闸门
└── rules/
    ├── cursor-content-structuring.mdc  # Cursor 项目规则（可选安装）
    └── codex-content-structuring.mdc   # Codex 项目规则（可选安装）
```

## 快速触发

在 Cursor 对话中：

- 手动附加本技能，或
- 使用 `/content-structuring`，或
- 提供字幕/链接并说「按 content-structuring 整理」

## 核心能力摘要

- 成稿即中文（叙述层、核心洞察、关键语录）
- 4c 验收闸门（grep + 连续英文词扫描）
- 有 URL 时浏览器优先抓取正文与元数据
- 文件名前缀使用内容发布时间（非生成日期）
- 可选受众可读性内化适配

详见 [`SKILL.md`](./SKILL.md) 与 [`references/spec.md`](./references/spec.md)。

# Content integrity gate

Read this reference for both `editorial` and `full` modes. Passing HTML validation does not prove semantic completeness.

## Build the source inventory

For every reader-facing H2 in the source, capture four things:

1. Core claim — what the section asks the reader to believe.
2. Necessary support — the example, mechanism or comparison that makes the claim intelligible.
3. Boundary — uncertainty, counterargument, speaker attribution or condition that prevents overclaiming.
4. Consequence — what the claim changes for the intended reader.

Ignore metadata, table of contents, glossary, self-check, the 关键语录与交锋时刻 anthology, and production notes. Do not ignore a remaining body section merely because its details do not fit the new article.

## Decide coverage explicitly

Create a coverage inventory before writing. Do not save `*_公众号内容审计.md` as a deliverable. If a working audit file is needed for validation, write it to a temp directory and delete it after the HTML and cover pass.

The coverage table must contain every source H2 exactly once.

Allowed decisions:

- `保留`: default. The source H2 title stays, and the core claim, necessary support and material boundary remain recognizable under that title.
- `合并`: only for layers **inside** one H2 (洞察/解析/实录). Do not merge two reader-facing H2s under a new heading.
- `删减`: the source H2 title stays; secondary evidence or branches are removed; record what and why.
- `删除`: the core claim is absent; allowed for 运营规范. 「关键语录与交锋时刻」is omitted like 术语表 / 自检, not listed in the coverage matrix.

`full` mode may not use `删减` or `删除` for reader-facing body sections, except when [wechat-operation-policy.md](wechat-operation-policy.md) requires it. Policy precedes coverage: a blocked claim is `删除` with reason `运营规范`, or the job stops. `full` may not reprint a blocked claim. `editorial` may also delete for policy; “篇幅有限” is still not a valid reason.

Both modes keep the source H1 and reader-facing H2 titles unless the user explicitly asked to 改写标题. Do not treat a punchier heading as `保留`.

## Required audit format

```markdown
# 公众号内容审计

## 文件与模式
- 模式：editorial
- 源稿：...
- 成稿：...

## 覆盖矩阵
| 源稿主题 | 处理 | 成稿位置 | 核心保留与删减理由 |
|---|---|---|---|
| Exact source H2 | 保留 | Exact source H2 | 节内去掉三层标签；结论与机制仍在 |

## 闭环检查
- 标题承诺：...；正文如何兑现：...
- 显式问题：问题 → 回答位置；不得写“均已回答”而不列问题。
- 事实与观点：列出需要归因的口述数字、观察和编辑推论。
- 来源披露：说明公开来源、编辑压缩和是否为逐字稿。
- 重要删除：逐项列出；没有则写“无”。

## 运营规范
- 官方页：微信公众平台运营规范（发送内容规范 + 当地法律监管）
- 扫描：风险码或「无」
- 处理：改写 / 删除 / 停交付
- 发布结论：可发布 | 改写后可发布 | 不可发布
```

Do not put the audit inside the pasted WeChat article, and do not leave it next to the source as a deliverable.

## Article integrity checks

### Promise closure

- The title is the source H1 unless policy or an explicit 改写标题 request changed it. The conclusion answers that same promise.
- Every explicit question in the opening or body receives an explicit answer.
- A heading that promises a number, such as “两件事”, delivers both items with comparable clarity.

### Attribution

- Attribute oral statistics, market observations, predictions and contested causal claims to the speaker.
- Label editor synthesis with language such as “可以把这条规律概括为”.
- Use quotation marks only for wording supported as a direct quote; use a card without quote marks for editorial summaries.

### Compression without distortion

- Preserve the distinction between correlation and causation, total unemployment and structural displacement, capability and commercial value, and fact versus forecast when those distinctions drive the source.
- Keep a counterpoint when removing it would make the retained claim stronger than the source.
- Keep at least one mechanism or example for every major conclusion; conclusions without support become slogans.

### Reader-facing provenance

Attribute oral claims in the body. 来源与说明 only contains `原文：{原标题}` — no video URL, date parenthesis, or “非逐字稿” note.

Keep operational details such as crawler failures or ASR tooling out of the article unless they materially affect reliability. If automatic transcription materially limits quote accuracy, avoid long direct quotations.

## Validation meaning

The deterministic validator checks HTML, that 来源与说明 contains only 原文, that the cover/HTML filenames match the source filename plus suffix, that the article H1 and reader-facing H2s match the source (unless `--allow-heading-rewrite`), and the mechanical 运营规范 title/audit gate. A human or model must still judge whether coverage is truthful and whether the source is publishable. Never report “content complete” or “safe to publish” based only on exit code 0. If 发布结论 is 不可发布, do not emit HTML.

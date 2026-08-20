# Content integrity gate

Read this reference for both `editorial` and `full` modes. Passing HTML validation does not prove semantic completeness.

## Build the source inventory

For every reader-facing H2 in the source, capture four things:

1. Core claim — what the section asks the reader to believe.
2. Necessary support — the example, mechanism or comparison that makes the claim intelligible.
3. Boundary — uncertainty, counterargument, speaker attribution or condition that prevents overclaiming.
4. Consequence — what the claim changes for the intended reader.

Ignore metadata, table of contents, glossary, self-check and production notes. Do not ignore a section merely because its details do not fit the new article.

## Decide coverage explicitly

Create `{stem}_公众号内容审计.md` before final delivery. Its coverage table must contain every source H2 exactly once.

Allowed decisions:

- `保留`: the core claim, necessary support and material boundary remain recognizable.
- `合并`: those elements move into another section without changing meaning.
- `删减`: the core claim remains but secondary evidence or branches are removed; record what and why.
- `删除`: the core claim is absent; explain why it is outside the title promise.

`full` mode may not use `删减` or `删除` for reader-facing body sections. `editorial` may, but the reason must be editorial rather than “篇幅有限”.

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
| Exact source H2 | 合并 | 二、... | Core retained; secondary example omitted because... |

## 闭环检查
- 标题承诺：...；正文如何兑现：...
- 显式问题：问题 → 回答位置；不得写“均已回答”而不列问题。
- 事实与观点：列出需要归因的口述数字、观察和编辑推论。
- 来源披露：说明公开来源、编辑压缩和是否为逐字稿。
- 重要删除：逐项列出；没有则写“无”。
```

Do not put the audit inside the pasted WeChat article. It is a production artifact for review.

## Article integrity checks

### Promise closure

- The title asks one question or makes one promise; the conclusion answers it in compatible terms.
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

For edited interviews or talks, include a concise note such as:

> 本文根据公开对谈编辑整理，非逐字稿；观点归属对谈嘉宾。

Keep operational details such as crawler failures or ASR tooling out of the article unless they materially affect reliability. If automatic transcription materially limits quote accuracy, avoid long direct quotations and disclose that the text is edited rather than verbatim.

## Validation meaning

The deterministic validator checks that every source H2 appears in the audit and that required audit fields exist. A human or model must still judge whether the mapping and reasons are truthful. Never report “content complete” based only on exit code 0.

# Editorial and audio guide

Use this reference only for `editorial` mode.

## The target form

The article should behave as one argument, not a transcript archive. Keep the source H1, each reader-facing H2, **and that section's claim**. WeChat work happens inside the section: flatten 核心洞察 / 深度解析 / 对谈实录 into narration, drop process noise, make it listenable. Do not keep the old heading and swap in a different argument.

Do not invent a shorter heading outline. Section count follows the source, minus 元数据 / 目录 / 术语表 / 自检 / 关键语录与交锋时刻. Completeness means every remaining source H2 still has a recognizable claim, one mechanism or example, and its material boundary — under the same heading. Short quotes already in those sections stay; do not reprint the anthology.

Length is a function of source density, not a badge of editorial quality:

| Source | Default editorial length | Why |
|---|---|---|
| Talk or essay under 30 minutes | about 2,000–4,000 汉字 | One argument, few branches |
| 30–90 minutes, or 5–8 H2s | about 4,000–6,000 汉字 | Merge repeated layers, keep reusable judgments |
| Over 90 minutes, or ≥8 H2s | about 5,000–8,000 汉字 | Do not collapse independently reusable insights into slogans |

If the knowledge base already extracted a section as its own note, that judgment is not “secondary color.” Keep it, with its mechanism, even after merging the insight/analysis/dialogue layers.

## Seven review dimensions

### 1. Mobile readability

- One paragraph should carry one move in the argument.
- Use short paragraphs and visible section breaks; do not split every sentence into a paragraph.
- Keep the source H2 wording. Do not replace it with a punchier claim. If a source heading is generic (“背景”), keep it; do not invent a new label.
- Keep only the numbers and names that change the conclusion.

### 2. Listenability

- The article must remain understandable without seeing bold, cards, tables or indentation.
- Replace tables with sentences that state the comparison and conclusion.
- Reintroduce the speaker or subject after a long gap; avoid chains of “他/这/其”.
- Use spoken transitions such as “更重要的是”“对企业来说”“这意味着”.
- Avoid bare URLs, parenthetical source audits, slash-heavy phrases and consecutive labels.
- Read every quote as audio: if the listener cannot tell who is speaking, turn it into attributed narration.

### 3. Editorial value

- Keep the source title promise. Advance it in source order.
- Merge repeated insight/analysis/dialogue **inside** a section. Do not merge two source H2s under a new title.
- Keep an example when it explains a mechanism, makes the conclusion memorable, or is already a reusable insight in the source. Cutting the only mechanism turns a claim into a slogan.
- Preserve useful tension; do not flatten a nuanced discussion into motivational slogans.
- After the draft, check whether a careful reader could reconstruct each source H2’s core claim. If not, the article is incomplete even if it “reads well.”

### 4. Credibility

- Attribute opinions and oral statistics to the speaker unless independently verified.
- Keep source caveats that affect the conclusion, but move process notes out of the reader copy.
- Do not promote a question from a video description into a claim made during the talk.
- Prefer precise paraphrase to long quotation.
- Attribution does not make a leak or unverified financing rumor publishable. Run the 运营规范 gate in `wechat-operation-policy.md` before writing.

### 5. Shareability

- The title is the source H1. Do not rewrite it for shareability unless the user asked to 改写标题.
- The opening should tell readers why the issue matters now without clickbait.
- Include one or two short, source-faithful lines that can stand alone as share cards.
- The ending should give a decision rule readers can reuse.

### 6. Audience utility

- Separate “what this means for a company” from “what this means for an individual” when both are present.
- Convert trend commentary into questions, choices or next actions.
- Avoid generic “拥抱变化”; name what to inspect, stop, learn or test.

### 7. WeChat robustness

- Inline styles only inside the copied article.
- Editorial body normally contains no native tables.
- Visual hierarchy must survive loss of class names and page-level CSS.
- Cover text is centered on the 2.35:1 crop with no white plate: title on top, speakers below. Title must match the article H1. Cover filename follows the source file, not the H1.

## Suggested editorial draft shape

The builder accepts ordinary Markdown. Keep the metadata section because it supplies the subtitle and source footer; it is removed from the pasted article.

```markdown
# {源稿 H1 原文}

## 文章元数据
| 项目 | 内容 |
|---|---|
| 原标题 | ... |
| 内容链接 | ... |
| 发布时间 | YYYY-MM-DD |
| 对谈人物 | A × B |
| 内容来源 | public venue/platform only |

> **人物背景**：one short reader-facing sentence.

## 核心导读
> **全文论点**：source thesis, not a rewrite.

## {源稿第一节 H2 原文}
Narrative that keeps that section's claim, mechanism, boundary.

## {源稿第二节 H2 原文}
...
```

## Final listening pass

Listen mentally from the first character, without looking at formatting:

- Can a listener identify the topic within the first 20–30 seconds?
- Does each section begin with enough context after the heading is spoken?
- Are numbers rounded or explained instead of delivered as a dense sequence?
- Does every pronoun have an audible antecedent?
- Does the ending resolve the title promise?

If not, revise the prose rather than relying on visual styling.

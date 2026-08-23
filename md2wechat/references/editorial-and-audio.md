# Editorial and audio guide

Use this reference only for `editorial` mode.

## The target form

The article should behave as one argument, not a transcript archive. Prefer this progression when it fits the source:

1. A concrete tension or counter-intuitive claim.
2. What most readers currently misunderstand.
3. The mechanism behind it.
4. Separate implications for organizations and individuals.
5. A closing decision rule or action.

Four to seven body sections usually gives enough navigation without turning the audio into repeated menu announcements. This is a judgment range, not a hard quota. Talks longer than about 90 minutes, or sources with eight or more reader-facing H2s, may need eight to ten body sections. Completeness means every source H2 still has a recognizable claim, one mechanism or example, and its material boundary — not that the article is short.

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
- Headings should state an idea, not use generic labels such as “背景” or “思考”.
- Keep only the numbers and names that change the conclusion.

### 2. Listenability

- The article must remain understandable without seeing bold, cards, tables or indentation.
- Replace tables with sentences that state the comparison and conclusion.
- Reintroduce the speaker or subject after a long gap; avoid chains of “他/这/其”.
- Use spoken transitions such as “更重要的是”“对企业来说”“这意味着”.
- Avoid bare URLs, parenthetical source audits, slash-heavy phrases and consecutive labels.
- Read every quote as audio: if the listener cannot tell who is speaking, turn it into attributed narration.

### 3. Editorial value

- Choose one central promise and make every section advance it.
- Merge repeated insight/analysis/dialogue material instead of preserving the source order. Do not merge away a distinct judgment just to hit a section quota.
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

- The title promises one useful judgment, not a catalog of topics.
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
# One clear title

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
> **全文论点**：one sentence.

Opening paragraphs.

## 一、A claim heading
Narrative paragraphs.
> One short source-faithful line if useful.

## 二、A claim heading
...

## 结语：A reusable decision rule
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

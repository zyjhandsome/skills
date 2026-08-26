# 过译护栏：专名与 AI/DevTools 概念标签勿误译（v5.31）

配合 `spec.md`「专名 vs 行话」与 4c 闸门。目标：叙述层中文，但**不要把官方产品名、平台对象名、命令名，或讲者刻意使用的 AI/DevTools 概念标签，译成「看起来很中文」却失去行业指向的近义词**。

## 判定口诀（先于词库）

1. **精确标识符 → 保留英文**：官方文档/UI/命令行、产品对象、API、文件名和代码符号不可翻掉。
2. **概念标签 → 保留英文或首现中英并写**：讲者用某词命名角色、身份、范式、工作流原语、架构层或对照组时，英文词本身承载可检索性与圈内含义。
3. **成组 taxonomy → 整组保留**：原文若并列 `Agent → Loop → Graph`、`Plan → Tool Call → Observe` 等术语链，不得逐词抹平成普通中文名词。
4. **普通叙述 → 译中文**：仅表达动作、状态、形容、比喻的普通英语写中文。**同形词看指称，禁止按单词一刀切。**

## AI/DevTools 社区原生标签（不是只有产品名才保留）

| 原文用法 | 推荐写法 | 何时仍译中文 |
| :--- | :--- | :--- |
| **Builder**（身份、角色、群体标签） | **Builder**；首现可「Builder（把产品做出来的人）」 | 普通动词 *build a page* → 构建页面；泛指施工者时按原义翻译 |
| **Agent**（AI 系统类别/术语链） | **Agent**；需要照顾通识读者时首现「AI Agent」 | 泛指代理商、法律代理人等非 AI 语境 |
| **Agent Loop / agentic loop** | **Agent Loop** / **agentic loop**；可补「代理执行闭环」解释 | 普通代码循环、重复动作可写「循环」 |
| **Loop / Graph / Workflow**（并列范式或工作流原语） | **Loop / Graph / Workflow**；尤其保留原文并列关系 | 普通「循环三次」「关系图」「办事流程」按中文写 |
| **Harness / Evals / Prompt / Context Window / Tool Call**（技术对象或层名） | 英文保留，或首次「中文说明（English）」后沿用英文标签 | 仅作为普通动作/非技术名词时中文化 |

**最小双语原则**：保留术语不等于每句堆英文。首次用 `Builder（产品构建者）`、`Agent Loop（代理执行闭环）` 之类说明一次；后文若它持续作为标签，直接沿用英文。已有稳定中文且英文不承担标签作用时，正文只写中文。

**来源优先**：能看到逐字稿时，以讲者是否把该词当作命名、对照或自我身份为准；看不到原文时，先保留可逆的中英并写，不凭中文词库武断删掉英文。

## 高频过译黑名单（禁止这样译）

| 原文指称（保留） | ❌ 过译 | ✅ 写法 |
| :--- | :--- | :--- |
| **Skill / Skills**（Cursor / Claude **Agent Skill** 包、`SKILL.md`） | 技能、技能包（单独当产品名时） | **Skill** / **Agent Skill**；说明可用「Skill（代理技能包）」**仅首现** |
| **Skill Creator** | 技能创建者 | **Skill Creator** |
| **Agent Skills**（产品/目录名） | 智能体技能、代理技能（作正式名时） | **Agent Skills** |
| **Hooks**（Cursor Hooks 产品能力） | 钩子（作产品名时） | **Hooks**；通用编程 hook → 钩子（hook） |
| **Rules**（Cursor Project Rules / `.mdc`） | 规则（作产品名时） | **Rules**；说明「项目规则（Rules）」 |
| **Subagent / sub-agent**（产品对象） | 子代理（作正式名时可括注） | **Subagent**；首现可「Subagent（子代理）」 |
| **Claude Code** | 克劳德代码、Claude 代码工具（替换专名） | **Claude Code** |
| **Computer Use** | 电脑使用、计算机使用 | **Computer Use** |
| **Composer** / **Canvas**（Cursor 产品面） | 作曲家、画布（作产品名时） | **Composer** / **Canvas** |
| **MCP** / **Model Context Protocol** | 模型上下文协议（可作释义，不可删英文专名） | **MCP**；首现可「模型上下文协议（MCP）」 |
| **PR** / **CI** / **CD** | 拉取请求/持续集成（作对象名时可括注） | **PR** / **CI**；首现可「拉取请求（PR）」 |
| **worktree** / **`/loop`** / **tmux** / **bash** | 工作树/循环命令（替换命令名） | 保留英文命令/对象名 |
| **Artifacts**（Claude 产品） | 神器、工件（作产品名时） | **Artifacts** |
| **Custom GPT / GPTs** | 自定义 GPT 机器人（可描述，专名保留） | **Custom GPT** / **GPTs** |
| **Creator**（平台角色/产品名，如 Skill Creator） | 创建者（作该专名时） | 按官方英文；通用「创作者经济」可中文 |

## 词库误伤白名单（4c 不得因这些标 ❌）

下列在**专名/命令/官方缩写**用法下，**即使出现在统一词库**，也不算夹写失败：

- `hook` → Cursor **Hooks**；git/CLI hook 作对象名
- `checkout` → `git checkout` / 命令名
- `spawn` / `subprocess` → API/系统调用名讨论
- `RAG` / `MCP` / `CI` / `PR` → 缩写专名（RAG/行业缩写仍要**首现中文全称**）
- `sandbox` / `harness` → 产品或评测框架专名；通用义再译
- `context` → **context window** / MCP 相关专名短语；口语 *lose context* → 失去上下文
- `onboarding` → 产品模块正式名时可保留；口语 → 新用户引导
- `roadmap` → 文件/栏目名可保留；叙述「路线图」亦可
- `demo` → **Demo Day** / 产品名；口语 → 演示
- `builder` → 产品套餐、角色名或身份标签时保留 **Builder**；普通动作按语境写「构建 / 做产品」，不要机械写「建造者心态」
- `feature` → **feature flag** 等固定搭配可保留英文术语；口语 → 功能
- `ship` → 动词口语 → 上线/发布；不是专名时不要留英文

## Skill / Creator 专项（用户高频踩坑）

整理 **AI 编码 Agent / Cursor / Claude** 类素材时：

| 口播/原文 | ❌ | ✅ |
| :--- | :--- | :--- |
| "install this skill" | 安装这个技能 | 安装这个 **Skill** |
| "skill creator flow" | 技能创建者流程 | **Skill Creator** 流程 |
| "creator of the skill" | 该技能的创建者 | 视语境：人 → 「作者/维护者」；产品 → **Skill Creator** |
| "agent skills directory" | 智能体技能目录 | **Agent Skills** 目录 |

**例外**：讲者在谈「沟通技能 / 领导力技能」等**人类软技能**时，用中文「技能」，不要写成 Skill。

## 典型过译回归

| ❌ 过译 | ✅ 保真写法 | 原因 |
| :--- | :--- | :--- |
| `先是代理，然后循环，然后图` | `先是 Agent，接着是 Loop，再到 Graph` | 原文在列举一组行业范式，英文标签本身是信息 |
| `他爱的是建造，编程只是手段`（原文强调身份） | `他真正认同的是 Builder 身份；编程只是实现手段` | **Builder** 是自我定位，不是施工意义的「建造者」 |
| `代理循环图` | `Agent Loop / Agent Graph`（按原文） | 中文压缩会混淆一个术语、两个术语或一条演化链 |

## 与 4c 的关系

- 首现 `中文（English）` 括注中的英文**不计入** 4c-1 裸词失败（见 spec「4c 验收闸门」）。
- 过译（把专名或概念标签译没）与漏译（叙述层堆普通英文）是**两类缺陷**；自检可在「正文中文叙事」备注中写「过译护栏已核」。
- 4c 词库只是**候选检索器**，不是翻译裁决器。命中 `builder`、`loop`、`graph`、`harness` 等多义词时必须先判断指称；不得为追求脚本 0 命中而牺牲术语保真。
- 扩展例子以本文件为准；`spec.md` 只保留摘要表。

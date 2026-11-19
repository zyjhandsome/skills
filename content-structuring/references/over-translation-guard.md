# 过译护栏：专名、AI/DevTools 概念标签与多义词辨析（参考分册）

> 配合 `language-and-gates.md` 4c 闸门与单源词库 `lexicon.txt` 使用。核心目标：叙述层保持流畅中文，但**严禁将官方产品对象、命令符号，或讲者刻意用来命名角色、范式、架构层与对照组的社区原生概念标签，强译成失去行业指向与可检索性的字面中文**。

---

## 一、四条判定准则（优先级高于词库字面匹配）

1. **精确标识符保留英文**：官方产品名、功能模块名、CLI 命令与参数、API、配置文件键名、代码符号与文件名原样保留。
2. **社区原生概念标签保留英文（首现可短释义）**：当讲者用某个词命名身份角色、技术范式、工作流原语或架构层级时，首次出现可写 `Builder（产品构建者）`、`Agent Loop（代理执行闭环）`，后文作为标签持续出现时直接沿用英文。
3. **成组 Taxonomy 整链保留**：当原文将一组概念并列为演化链或对比框架（如 `Agent → Loop → Graph`、`Plan → Tool Call → Observe`）时，整组保留英文标签，严禁拆散抹平为「先是代理，然后循环，然后图」。
4. **同形普通词译为自然中文**：同一单词仅表达日常动作、状态、形容或泛指时（如 *build a page* → 构建页面，人类「沟通技能」→ 技能而非 `Skill`），正常译为中文，禁止按单词一刀切。

---

## 二、高频过译黑名单（禁止强译）

| 原文专名 / 概念标签 | ❌ 典型过译错误 | ✅ 标准保真写法 |
| :--- | :--- | :--- |
| **Skill / Agent Skill / Agent Skills**（`SKILL.md` 包） | 技能、智能体技能（替代专名时） | **Skill** / **Agent Skill** / **Agent Skills**（首现可括注「代理技能包」） |
| **Skill Creator** | 技能创建者（易误读为岗位头衔） | **Skill Creator**（指人时按语境写「该 Skill 的作者/维护者」） |
| **Claude Code** | 克劳德代码、Claude 代码工具 | **Claude Code** |
| **Computer Use** | 电脑使用、计算机使用 | **Computer Use** |
| **Hooks / Rules / Composer / Canvas / Artifacts** | 钩子/规则/作曲家/画布/神器（作产品能力名时） | 保留首字母大写官方专名；普通编程概念才写「钩子（hook）」「规则」 |
| **Subagent / Custom GPT / GPTs** | 子代理 / 自定义机器人（替代正式对象名） | **Subagent**（首现可注「子代理」）、**Custom GPT** / **GPTs** |
| **MCP / Model Context Protocol** | 仅写「模型上下文协议」删掉英文缩写 | **MCP**（首现可写「模型上下文协议（MCP）」） |
| **Builder**（自我认同/角色标签） | 施工者、建造者心态 | **Builder**（例：`他真正认同的是 Builder 身份，编程只是手段`） |
| **Agent / Agent Loop / Loop / Graph / Workflow** | 代理、代理循环图（混淆单术语与演化链） | 作范式或原语标签时保留 **Agent / Agent Loop / Loop / Graph / Workflow** |
| **Harness / Evals / Context Window / Tool Call** | 马具/评测集（抹掉架构层专名） | 作评测框架或系统层名时保留英文（首现可补中文说明） |
| **worktree / `/loop` / tmux / bash / `git checkout`** | 工作树、循环命令（替换命令字面量） | 原样保留命令与对象名 |

---

## 三、语境多义词辨析表（配合 `lexicon.txt` 人工复核）

`lexicon.txt` 中的 `[contextual]` 与 `[contextual-case-sensitive]` 命中仅作人工复核提示，按以下语境裁决，严禁为追求 0 提示而盲目替换：

| 多义词 / 缩写 | 普通叙述译法 | 保留英文或特殊译法的语境 |
| :--- | :--- | :--- |
| **rollout** | 发布 / 灰度推进（禁一律译「推广」） | 强化学习/训练采样语境译为「采样轨迹（rollout）」 |
| **onboarding** | 新用户引导 / 入职引导 | 官方产品模块正式名称可保留 `Onboarding` |
| **demo** | 演示 / 实操演示 | **Demo Day** 或产品固定命名保留英文 |
| **pitch** | 推销陈述 / 路演陈述 | 勿误译为体育场地或音高 |
| **hook / sandbox / harness** | 钩子 / 沙箱 / 管控框架 | 指特定产品特性或评测套件专名（如 Cursor **Hooks**、**Harness**）时保留首字母大写英文 |
| **spawn / subprocess / checkout** | 拉起 / 子进程 / 检出 | 讨论具体系统调用、API 名或 `git checkout` 命令时保留英文 |
| **feature / context / ship** | 功能 / 上下文 / 发布上线 | **feature flag**、**context window / context engineering** 等固定技术搭配可保留或首现括注；动词 *ship it* 译中文 |
| **IC / ASL / MTS / RAG / GTM / TAM / COGS / PIP / T&E** | 行业缩写 | **首次出现必须注中文全称**（如 `独立贡献者（IC）`、`自主安全等级（ASL）`、`检索增强生成（RAG）`），后文可直接使用英文缩写 |

---

## 四、与 4c 机检脚本的协同约定

- **括注豁免**：首次出现采用 `中文全称或释义（English）` 格式时，括号内的英文不计入 4c-1 阻断命中；图片中文 `alt` 若需保留投屏原英文标题，同样写入 `（原片标题：English Title）` 括注。
- **大小写区分**：`Skill / Builder / Agent / Loop / Graph / Workflow / Harness` 在 `lexicon.txt` `[allow-case-sensitive]` 中仅豁免首字母大写的专名/标签形态；小写普通用法（如 *skill gap*、*vibe code*）仍受 4c-1/4c-2 约束。
- **双向核查**：成稿自检「正文中文叙事」行须同时确认「无普通英文漏译（4c-1=0）」与「无核心概念过译（`over-translation` 提示已核查）」。

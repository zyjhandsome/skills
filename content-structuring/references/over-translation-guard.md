# 过译护栏：专名与产品词勿误译（v5.28）

配合 `spec.md`「专名 vs 行话」与 4c 闸门。目标：叙述层中文，但**不要把官方产品名、平台对象名、命令名译成「看起来很中文」的近义词**。

## 判定口诀（先于词库）

1. **能写进官方文档/UI/命令行的固定名字 → 保留英文**（可加中文说明，不可替换专名本身）。
2. **普通口语形容词/动词/比喻 → 译中文**（可首现 `中文（English）`）。
3. **同形词看指称**：同一英文词既可能是专名也可能是口语——按指称选，禁止一刀切。

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
- `builder` → 产品套餐/角色正式名；口语 *builder mindset* → 建造者心态
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

## 与 4c 的关系

- 首现 `中文（English）` 括注中的英文**不计入** 4c-1 裸词失败（见 spec「4c 验收闸门」）。
- 过译（把专名译没）与漏译（叙述层堆英文）是**两类缺陷**；自检可在「正文中文叙事」备注中写「过译护栏已核」。
- 扩展例子以本文件为准；`spec.md` 只保留摘要表。

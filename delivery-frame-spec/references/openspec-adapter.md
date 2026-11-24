# OpenSpec semantic adapter（Delivery Family 共用）

本文件把 Delivery Family 的语义操作解析到当前安装的 OpenSpec 能力。命令名和默认工件路径只是候选，不是稳定 API。OpenSpec 是硬前提：默认仓库已 `init`、CLI 可用；不为未安装/未初始化配置备用路径（见 `family-contract.md` 第 2 节）。

## 目录

1. 解析顺序
2. 语义操作
3. 工件槽位
4. 失败与升级

## 1. 解析顺序

在本阶段第一次依赖 OpenSpec 时：

1. 探测当前可用入口：宿主命令目录、OpenSpec CLI help/version/status 或已声明的工具 schema。
2. 读取 active change/schema；不要仅凭目录名推断。
3. 把本阶段需要的语义操作解析到实际入口，写入 `capability_bindings.openspec`。
4. 只执行已解析且与当前 route/gate 相符的操作。

禁止为了探测而创建 change、修改工件或执行 archive。若第一次真实需要 OpenSpec 时发现仓库未初始化（`openspec: cli-only`），停止 mutation/gate，用 `family-contract.md` 固定三行报告，并提议已解析的 `initialize_repo`；用户拒绝则变更车道保持停止（只读除外）。

## 2. 语义操作

| 语义操作 | 用途 | 常见候选（仅提示） |
|---|---|---|
| `initialize_repo` | 采用/初始化 OpenSpec 仓库 | `openspec init` |
| `create_change` | 创建/提出 change | `openspec new change "<id>"`（只建目录和 `.openspec.yaml`；不要用一步生成全部工件的入口，它会越过规格闸门和实现闸门） |
| `inspect_change` | status、active change、artifact readiness | `openspec status --change "<id>" --json`、`openspec list --json`、`openspec list --specs --json`、`openspec show "<spec-id>" --type spec` |
| `continue_artifacts` | 生成或更新 proposal/spec/design/tasks | `openspec instructions <artifact> --change "<id>" --json` 取模板与约束后写文件；修订已有工件可用 `openspec-update-change` |
| `apply_tasks` | 按权威 tasks 实施 | `openspec instructions apply --change "<id>" --json`、`openspec-apply-change` |
| `validate_structure` | 校验工件结构/schema | `openspec validate "<id>" --type change --json` |
| `verify_coherence` | 规格—实现一致性 | 当前安装有 verify 类入口时用它；没有时由 Agent 逐条 Requirement/Scenario 对照实现并记录 |
| `archive_change` | sync/archive 已验证 change | `openspec-archive-change`、`openspec archive "<id>"` |

**结构校验的通过条件：** `openspec validate "<id>" --type change --json` 返回的 `items[].valid` 全为 `true`。默认不加 `--strict`；WARNING 逐条处理或在闸门摘要里列出。规格闸门、实现闸门和 `verified` 之前各跑一次。

**`.openspec.yaml` 标记：** `skip_specs: true` 表示本 change 没有规格级行为变化，此时 `specs/` 下不得有文件；`retire_capabilities: true` 用于下线整个 capability。两者都会改变归档行为，已计入 `artifact_revision`。

**`openspec instructions` 返回的 `context` 和 `rules`：** 是项目 `openspec/config.yaml` 给 Agent 的写作约束，照做但不要抄进工件正文。写 proposal 的 Capabilities 之前先用 `openspec list --specs --json` 看已有 capability，复用既有路径，不新造近义名。

如果当前版本没有一一对应操作，记录实际组合和限制；不要编造命令。`archive_change` 永远由 Execute verified 后的下一动作触发，不在 Execute 内执行。

## 3. 工件槽位

优先读取当前 change schema/status 返回的工件槽位。只有当前版本明确采用默认 `spec-driven` 形态时，才使用这些常见映射：

| Delivery 语义 | 常见 OpenSpec 槽位 |
|---|---|
| brief / lightweight contract | `proposal.md` |
| delta specification | `changes/<id>/specs/<cap>/spec.md` |
| technical design | `design.md` |
| executable tasks | `tasks.md` |
| verification evidence | schema 支持的附件或受管 `verification.md` |
| 最新 handoff 快照缓存 | 受管附件 `handoff.json`（覆盖写；见 `handoff-contract.md` 第 4 节） |

若槽位、结构标记或 requirement/scenario skeleton 与当前说明不一致，以当前 OpenSpec schema 为准，并更新 `capability_bindings.openspec.schema`。不得创建平行 Markdown 后端。

### `spec-driven` + Delivery brief 拼合（推荐）

当 `openspec instructions proposal` 要求 Why / What Changes / Capabilities / Impact，而 Delivery Standard/High 要求意图 / 代码事实 / 消歧与闸门时，**写入同一 `proposal.md`**，顺序建议：

1. OpenSpec 机器骨架：`## Why` → `## What Changes` → `## Capabilities` → `## Impact`（标题保持英文 schema 要求时的原样）。
2. 分隔线后接 Delivery 中文简报全文（见 `brief-template.md`），含 Explore 交接消费与状态源。
3. Quick / Debug-Low：OpenSpec Why/What 可极简，主体用轻量契约，仍不要另建 `brief.md`。有可观察行为变化时写一条最小 delta（一条 Requirement + Scenario），不因此升到 Standard；没有规格级行为变化时设 `skip_specs: true`，不写 spec。

**Quick 车道的 status 解读（防展示噪音）：** `inspect_change` / `openspec status` 在 Quick 下显示 design 槽未完成（如 3/4）**属预期**——Quick 按定义不产 `design.md`。判定完整性以「轻量契约 + 最小 delta + `validate` 通过」为准；向用户呈现 status 时附一句解释，不要为凑满槽位写假 design 或空占位文件。

Capabilities 中的 kebab-case 名必须与后续 `specs/<name>/spec.md` 一致。

## 4. 失败与升级

- CLI 运行中真实失败（命令报错、schema 读不出）：按 `family-contract.md` 硬前提故障处理——停止 mutation/gate 写入并用固定三行报告，恢复后继续。
- 仓库未 init 但 CLI 可用：标 `openspec: cli-only`，提议 `initialize_repo`；同意则执行并恢复 `initialized`，拒绝则 mutation 停止。这不是 degraded 取证模式。
- 解析不到必需语义操作：将 `openspec` 标为真实状态（`unavailable` 或 `cli-only`）；只读可继续，mutation 停止。
- OpenSpec 版本/schema 在流程中变化：标记依赖旧绑定的 artifact/gate stale，重新解析所需操作并做定点验证。
- 旧 alias 失效但语义操作仍可解析：更新绑定即可，不修改核心阶段规则。
- archive 行为、sync 提示或确认形态变化：保留当前版本的交互，不在 Delivery Skill 中复制它们。

# OpenSpec semantic adapter（Delivery Family 共用）

本文件把 Delivery Family 的语义操作解析到当前安装的 OpenSpec 能力。命令名和默认工件路径只是候选，不是稳定 API。

## 目录

1. 解析顺序
2. 语义操作
3. 工件槽位
4. 失败与升级

## 1. 解析顺序

在本阶段第一次依赖 OpenSpec 时：

1. 探测当前可用入口：宿主命令目录、OpenSpec CLI help/version/status 或已声明的工具 schema。
2. 读取当前仓库采用状态和 active change/schema；不要仅凭目录名推断。
3. 把本阶段需要的语义操作解析到实际入口，并写入 `capability_bindings.openspec`。
4. 只执行已解析且与当前 route/gate 相符的操作。

禁止为了探测而创建 change、修改工件或执行 archive。

## 2. 语义操作

| 语义操作 | 用途 | 常见候选（仅提示） |
|---|---|---|
| `initialize_repo` | 采用/初始化 OpenSpec 仓库 | `init`、`openspec init` |
| `create_change` | 创建/提出 change | `new`、`propose`、`/opsx-new`、`/opsx-propose` |
| `inspect_change` | status、active change、artifact readiness | `status`、`list`、宿主面板 |
| `continue_artifacts` | 生成或更新 proposal/spec/design/tasks | `continue`、`update`、`/opsx-continue`、`/opsx-update` |
| `apply_tasks` | 按权威 tasks 实施 | `apply`、`/opsx-apply` |
| `validate_structure` | 校验工件结构/schema | `validate` |
| `verify_coherence` | 规格—实现一致性 | `verify`、`/opsx-verify` |
| `archive_change` | sync/archive 已验证 change | `archive`、`/opsx-archive`、`openspec-archive-change` |

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

若槽位、结构标记或 requirement/scenario skeleton 与当前说明不一致，以当前 OpenSpec schema 为准，并更新 `capability_bindings.openspec.schema`。不得创建平行 Markdown 后端。

### `spec-driven` + Delivery brief 拼合（推荐）

当 `openspec instructions proposal` 要求 Why / What Changes / Capabilities / Impact，而 Delivery Standard/High 要求意图 / 代码事实 / 消歧与闸门时，**写入同一 `proposal.md`**，顺序建议：

1. OpenSpec 机器骨架：`## Why` → `## What Changes` → `## Capabilities` → `## Impact`（标题保持英文 schema 要求时的原样）。
2. 分隔线后接 Delivery 中文简报全文（见 `brief-template.md`），含 Explore 交接消费与状态源。
3. Quick / Debug-Low：OpenSpec Why/What 可极简；主体用轻量契约；仍不要另建 `brief.md`。若 `openspec validate` 报「must have at least one delta」，补最小 `specs/<cap>/spec.md`（一条 Requirement + Scenario），不要因此升到 Standard。

Capabilities 中的 kebab-case 名必须与后续 `specs/<name>/spec.md` 一致。

## 4. 失败与升级

- 解析不到必需语义操作：将 `openspec` 标为 `unavailable` 或 `cli-only` 的真实状态；只读可继续，mutation 停止。
- OpenSpec 版本/schema 在流程中变化：标记依赖旧绑定的 artifact/gate stale，重新解析所需操作并做定点验证。
- 旧 alias 失效但语义操作仍可解析：更新绑定即可，不修改核心阶段规则。
- archive 行为、sync 提示或确认形态变化：保留当前版本的交互，不在 Delivery Skill 中复制它们。

# Delivery Family contract

本文件定义四个 `delivery-*` Skill 的包级兼容边界与全家族共享约定。它不是第五个用户可见 Router；四个阶段 Skill 仍是唯一入口。

## 目录

1. Family 版本
2. 硬前提能力（无降级）
3. 能力绑定记录
4. 语言与命名约定（全家族）
5. Memory 索引新鲜度规则
6. 升级与兼容规则

## 1. Family 版本

```text
family_version: delivery-family/1.2
handoff_schema: delivery-handoff/v1
presentation_schema: delivery-presentation/v1
structured_ui_schema: delivery-ui/v1
visible_skills:
  - delivery-explore
  - delivery-frame-spec
  - delivery-plan-tasks
  - delivery-execute-verify
```

四个 Skill 和共享 references 必须原子安装/升级。发现缺失阶段或共享文件时停止跨阶段转换并报告缺失项；不要临时复制规则或创建替代 Router。

**链式接力（宿主适配）：** handoff 校验通过且允许转换时，若宿主允许 Agent 直接读取技能文件（如 Cursor：技能位于本地目录，`SKILL.md` 可直接 Read），应在**同一会话**读取下一技能的 `SKILL.md` 并继续执行，不停下等用户复述；仅当宿主无法加载下一技能、或转换本身被闸门/阻塞项挡住时，才停止并提示「请使用 <next_skill>」。跨会话恢复走 `handoff-contract.md` 的持久化槽位（change 目录内 `handoff.json`）。

**版本权威源与兼容口径：** 本文件是 `family_version` 的唯一权威声明；其他文件中的版本字符串只是当前值的复制。兼容性按 **major** 判定：同 major 的 minor 递增是向后兼容的加法式变更（新增可选字段、`x_` 扩展键），不触发停机。`validate_handoff.py` 只校验 major（接受 `delivery-family/1.x`）。

## 2. 硬前提能力（无降级）

以下能力是 Family 的**硬前提**，默认已安装、已初始化、可用。不为「未安装 / 未初始化」配置备用路径。

| 能力 | 角色 | 运行中实际失败时 |
|---|---|---|
| OpenSpec（仓库已 init） | 唯一工件/状态后端 | **停止**一切 mutation、artifact、gate 写入；报告故障与最后已验证状态；恢复后继续。禁止创建应急 Markdown 状态 |
| Codebase Memory MCP（索引已建） | 唯一代码证据入口 | **停止**依赖证据的结论输出；报告故障（如索引损坏）；先修复/重建索引再继续。禁止用全仓 grep 转储替代图查询 |
| Superpowers | 方法层（TDD、systematic-debugging、review 等） | 报告缺失的方法名并**停止**依赖它的环节；不内联复制外部 Skill 全文 |
| SubAgent / worktree | 并行执行与独立审查 | 报告宿主实际限制（如并发上限=1）；并发上限是宿主事实需解析，但「完全不可用」按异常报告处理 |
| 结构化提问 / 展示 UI | 可选体验层（唯一的软依赖） | Markdown fallback；不改变语义或授权 |

规则：

- **不做安装态预检。** 阶段开始时不探测「是否安装/是否初始化」，直接按已就绪使用；第一次真实调用失败才触发上表的停止-报告行为。
- **失败报告形状（中文，一行起）：**「<能力> 调用失败：<错误摘要>。已停止 <受影响环节>。请修复后回复继续。」不做降级选项列表。
- `capability_snapshot` 在 handoff 中保留（schema 稳定），但本 profile 下预期恒为标称值：`memory: ok`、`openspec: initialized`、`superpowers: loaded`。出现非标称值时不得携带阶段转换（`next_skill`/`next_action` 保持 `null`，`stop_condition` 写明故障）。此规则由 `validate_handoff.py` 默认强制（`--profile hard`）。
- `evidence_mode` 恒为 `full`。没有 degraded 取证模式。

## 3. 能力绑定记录

`capability_bindings` 记录本次实际解析到的版本/接口（绑定 ≠ 健康）。只记录本阶段实际需要的绑定；未使用的方法不要求穷举。

```json
{
  "capability_bindings": {
    "openspec": {
      "version": null,
      "schema": null,
      "operations": {
        "create_change": null,
        "inspect_change": null,
        "continue_artifacts": null,
        "apply_tasks": null,
        "validate_structure": null,
        "verify_coherence": null,
        "archive_change": null
      }
    },
    "memory": { "server": null, "schema_version": null, "resolved_tools": [] },
    "superpowers": { "source": null, "version": null, "resolved_methods": [] },
    "subagents": {
      "max_concurrency": null,
      "worktree_support": "unknown|available|unavailable",
      "independent_review": "available"
    }
  }
}
```

命名约定：引用外部能力时写 仓库 + 语义能力，如 Superpowers `brainstorming`、OpenSpec `create_change`、Codebase Memory MCP `trace_path`。裸技能名保留给 `delivery-*` 家族。

## 4. 语言与命名约定（全家族）

- 四份 `SKILL.md` 为英文；**所有面向人的 Markdown 工件默认中文**（简报/契约/设计/任务/验证报告的正文、标题、表格），遵循 `references/` 下的中文模板。
- 保持英文的仅有：路径、命令、代码标识符、机读键/枚举（如 `medium`/`high`、handoff 键）、原始工具/测试输出（原样粘贴），以及 OpenSpec 的机器解析骨架（如 `## Requirements`、`### Requirement:`、`#### Scenario:`、`SHALL`/`MUST`——以当前 OpenSpec schema 实际声明为准）。
- 用户使用其他语言时跟随用户语言；机读骨架仍保持英文。
- 简报各部分用**稳定标题名**引用（如「意图」「代码事实」「开放问题清单」），不用章节号（`§` 等）。

## 5. Memory 索引新鲜度规则

已知存在于磁盘的路径/符号（git status、用户告知、先前读取、契约/任务引用）被 Memory `search_graph` / `search_code` / `get_code_snippet` 漏检时：

1. 视为索引过期，**先重建/刷新索引**（`index_repository` 或等价操作）再重查；
2. 图查询 miss 不得作为「代码不存在」的证据；
3. 重建后仍失败 → 按第 2 节硬前提故障处理（停止并报告）。

执行阶段编辑代码后，依赖影响面证据前先确认索引新鲜度。

## 6. 升级与兼容规则

1. 先比较 `family_version` 与 `handoff_schema`；只按 major 判兼容；major 不受支持时停止自动链式转换。
2. 外部能力按语义操作解析（OpenSpec 规则见 `openspec-adapter.md`），不把命令别名当稳定 API。
3. Memory 调用前发现当前 MCP schema；Superpowers 记录实际加载来源；SubAgent 使用宿主实际并发上限。
4. 外部能力升级后，只重新验证受影响的 adapter、工件和 gate。
5. handoff 是可验证的传输快照，不是第二状态源；OpenSpec change 仍是变更车道的唯一权威状态。快照的持久化槽位见 `handoff-contract.md`。

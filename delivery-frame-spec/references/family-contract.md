# Delivery Family contract

本文件定义四个 `delivery-*` Skill 的包级兼容边界。它不是第五个用户可见 Router；四个阶段 Skill 仍是唯一入口。

## 目录

1. Family 版本
2. 能力依赖等级
3. 能力绑定记录
4. 升级与兼容规则

## 1. Family 版本

```text
family_version: delivery-family/1.1
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

**版本权威源与兼容口径：** 本文件（`family-contract.md`）是 `family_version` 的唯一权威声明；其他文件与模板中出现的 `delivery-family/1.1` 只是当前值的复制示例，升级时以本文件为准。兼容性按 **major** 判定：同一 major 下的 minor 递增视为**向后兼容的加法式变更**（新增可选字段、新增 `x_` 扩展键），不触发停机。`validate_handoff.py` 据此只校验 major（接受 `delivery-family/1.x`），因此 minor bump 不需要改校验器。只有 major 不受支持时才停止自动链式转换。

## 2. 能力依赖等级

| 能力 | 等级 | 缺失行为 |
|---|---|---|
| 四个 `delivery-*` Skill + 共享协议 | Family 必需 | 当前阶段可报告，但不得交给缺失阶段 |
| OpenSpec | 变更车道必需 | 只读可继续；任何 mutation/artifact/gate 写入停止 |
| Codebase Memory MCP | 首选、可降级 | 改用定点源码/测试/git 证据并标记 `evidence_mode: degraded` |
| Superpowers | 首选、可降级 | 使用本 Family 的最小安全不变量并记录 fallback；不复制完整外部 Skill |
| SubAgent/worktree | 可选执行加速 | 顺序内联；保持同样验证和所有权门禁 |
| 结构化提问/展示 | 可选体验层 | Markdown fallback；不得改变语义或授权 |

不要把“预期已安装”和“流程硬依赖”混为一谈。只有 OpenSpec（对变更车道）和完整 Family 是硬阻塞项。

## 3. 能力绑定记录

`capability_snapshot` 只记录健康状态；`capability_bindings` 记录本次实际解析到的版本/接口。无法发现时使用 `null` 或空对象，不猜测。

```json
{
  "capability_bindings": {
    "openspec": {
      "version": null,
      "schema": null,
      "operations": {
        "initialize_repo": null,
        "create_change": null,
        "inspect_change": null,
        "continue_artifacts": null,
        "apply_tasks": null,
        "validate_structure": null,
        "verify_coherence": null,
        "archive_change": null
      }
    },
    "memory": {
      "server": null,
      "schema_version": null,
      "resolved_tools": []
    },
    "superpowers": {
      "source": null,
      "version": null,
      "resolved_methods": []
    },
    "subagents": {
      "availability": "unknown|available|unavailable",
      "max_concurrency": null,
      "worktree_support": "unknown|available|unavailable",
      "independent_review": "unknown|available|unavailable"
    }
  }
}
```

只记录本阶段实际需要或已经探测的绑定；未使用的方法不要求穷举。绑定变化时更新快照，并重新判断依赖它的证据或批准是否失效。

## 4. 升级与兼容规则

1. 先比较 `family_version` 和 `handoff_schema`；只按 **major** 判定兼容，同 major 的 minor 递增须保持加法式向后兼容（新增可选字段或 `x_` 扩展键，不改已有语义）；major 不受支持时停止自动链式转换。
2. 外部能力按语义操作解析，不把命令别名当成稳定 API。OpenSpec 规则见 `openspec-adapter.md`。
3. Memory 调用前发现当前 MCP schema；Superpowers 记录实际加载的方法来源；SubAgent 使用宿主实际并发上限。
4. 外部能力升级后，只重新验证受影响的 adapter、工件和 gate，不无条件重跑所有阶段。
5. handoff 是可验证的传输快照，不是第二状态源；OpenSpec change 仍是变更车道的唯一权威状态。

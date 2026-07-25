# 人工决策记录契约

## 1. 为什么与分析证据分开

`--analysis-evidence-file` 记录的是**事实与候选**，契约明确禁止它记录审批或选择。人在确认队列里做出的选择是**决策**，因此单独存放在 `--decision-file`。

两者的边界：

| 文件 | 内容 | 谁写 | 谁读 |
|---|---|---|---|
| `--analysis-evidence-file` | 复核过的候选、删除覆盖、运行时约束等事实 | Agent 调研后写 | 生成器读 |
| `--decision-file` | 人选定的轨道、包与版本 | Agent 在人确认后写 | 生成器读 |

生成器**只读**决策文件，不会创建也不会修改它。默认路径为 `<报告目录>/human-decisions.json`，存在即读取；也可用 `--decision-file` 显式指定。

**记录选型不等于实施授权。** 决策文件不能授予安装依赖、执行项目脚本、切换 Node 或提交改动的权限；实施审批只从调用方的任务生命周期取得。

## 2. 文件格式

```json
{
  "version": 1,
  "decisions": [
    {
      "package": "axios",
      "track": "replace",
      "choice": "replace:ky@1.14.3",
      "selected_package": "ky",
      "selected_version": "1.14.3",
      "rationale": "满足项目 Node 20；拦截器缺口已确认可由适配层承接",
      "decided_at": "2026-07-25T22:10:00+08:00",
      "source": "confirmation-queue"
    },
    {
      "package": "legacy-utils",
      "track": "native-refactor",
      "choice": "native-refactor",
      "rationale": "无合规替代包，按逐调用点改造表推进",
      "decided_at": "2026-07-25T22:12:00+08:00",
      "source": "confirmation-queue"
    }
  ]
}
```

字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `package` | 是 | 必须属于本次分析清单，否则记为 `unknown-package` 并忽略 |
| `track` | 否 | `remove` / `replace` / `native-refactor`；缺省时按报告主轨呈现 |
| `choice` | 是 | 确认队列给出的选项 ID |
| `selected_package` | 选包时必填 | 选定的依赖包名 |
| `selected_version` | 选包时必填 | 精确 semver，不接受范围 |
| `rationale` | 建议 | 决策理由，会原样呈现在决策记录表 |
| `decided_at` | 建议 | ISO 时间 |
| `source` | 否 | `confirmation-queue`（选了队列里的选项）或 `other`（人自填） |

`switch:<轨道>` 是改轨答案而不是最终选择，不得写入本文件；应改问对应轨道的问题后再记录结果。生成器遇到它会忽略该条并给出警告。

## 3. 重跑时的重验规则

每次重跑都会重验已存决策，结果只取三种状态：`confirmed`（仍成立，静默沿用、不再提问）、`invalidated`（作废并带着失效原因重新进入确认队列）、`unknown-package`（不在本次分析清单内，忽略）。

| 记录 | 失效条件 |
|---|---|
| `remove` | 删除结论变为 `not_viable` |
| `native-refactor` | 改造方向不再 `established`（调用点证据丢失） |
| 同库版本 | 记录选择了同库升级；该路径已不再是选项，需改用精确升级模式重跑 |
| 替代包 | 该包已不在候选中（`source=other` 除外）、被 registry 标弃用、与项目 Node 或现有 peer 冲突、推荐版本已变更 |
| 任意选包 | `selected_version` 不是精确 semver |

`source=other` 的自填选择只做能核对的检查（精确 semver、若该包也在候选中则同样核对弃用与约束冲突），其余按未经生成器核对呈现。

确认后的包：`selection_status=selected`、`decision_status=not_needed`、`recommended_action=awaiting-implementation-approval`，队列状态为 `decided`。

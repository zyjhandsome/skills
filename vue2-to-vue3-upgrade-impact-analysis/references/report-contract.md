# 报告契约

## 文件名

- `vue2-to-vue3-upgrade-report.md`（必填）
- `decision-records/migration-path__<path-id>.md`（路径单元必填）
- `decision-records/subsystem__<subsystem-id>.md`（每个 High/blocker 子系统必填；其余可选）
- `vue2-to-vue3-upgrade-report.json`（可选）

语言：可见正文默认简体中文；枚举、包名、版本、路径、命令、URL 保持英文原文。

## 报告目录解析

1. 显式 `--output-dir`
2. 既有 `--change-dir` → `<change-dir>/evidence/vue2-to-vue3-upgrade/`
3. 目标仓已有唯一 `openspec/changes/<id>/` → 当作 change-dir；多个询问
4. 否则默认候选：`<project-root>/.vue2-to-vue3-upgrade-analysis`

硬规则：不得创建 OpenSpec change；优先使用既有 change 的 evidence 子目录；无 change 时可用默认候选目录，但须复述绝对路径并得到显式确认（`--output-dir <path>` 或 `confirm:output-dir`）后再写。路径未确认前只读分析、禁止写入。口语「写到仓库」无效。

## 多批次布局

| 批次数 | 布局 |
|---|---|
| 1 | 报告在证据目录根 |
| ≥2 | `<entry-kind>/<workspace-slug>__variant-<build-variant>__scope-<batch-scope>/vue2-to-vue3-upgrade-report.md` + 根 `BATCH-INDEX.md` |

`entry-kind`：`workspace` / `inventory`

## 顶层状态字段

| 字段 | 取值 |
|---|---|
| `analysis_status` | `partial` / `blocked` / `complete` |
| `decision_status` | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | `frozen` / `ready` |
| `behavior_parity_required` | `yes` / `no` |
| `network_mode` | `online` / `offline` / `partial` |
| `report_path` | 实际目录 |

## 必选章节（按顺序）

1. 基线与假设
2. 仓画像与依赖就绪度
3. 推荐迁移路径
4. 子系统影响清单
5. 分层影响分析
6. 风险分级
7. 确认队列
8. 验证矩阵
9. 回滚与责任人
10. 未决问题与证据缺口

章节「1. 基线与假设」必须出现字面 `lockfile`（大小写不敏感），说明 lock 路径或「无 lockfile」及复现性风险。
章节「3. 推荐迁移路径」必须出现字面：`Composition API 全仓重写：另立项，本次不评估工作量`。
章节「3」或「7」附近必须出现：`Name, never run`，**或**同时出现「命名配方」与「不执行」（二者缺一不可；仅有「命名配方」表头不算）。
章节「10」必须出现字面：`人工补搜检查`，并勾选/回答下列项（即使 profile 已扫描）：

- `slot-scope` / 旧 `slot=` 模板
- 全局 `Vue.filter` 注册
- 非 `vue-*` 前缀的 Vue2-only / 编辑器类包
- lockfile 缺失或未解析时的版本复现风险

§4 中每个 `risk` 为 `high`/`blocker` 且非 `not_applicable` 的子系统，必须出现在 §7 确认队列；`analysis_status=complete` 时还须有对应 `decision-records/subsystem__<id>.md`。
路径未 `decided` 前，子系统行不得为 `ready`。

## 仓画像表列（§2）

`包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据`

就绪度：`ready` / `needs-major` / `replace` / `unknown` / `unused`

## 子系统表列（§4）

`子系统 | scope_status | 风险 | 就绪度 | 命名配方 | 说明`

## 确认队列表列（§7）

`单元 | 类型 | 状态 | 问题 | 选项`

- 类型：`path` / `subsystem`
- 状态：`ready` / `pending` / `blocked` / `decided` / `deferred`
- 路径选项须含 `proceed:path:` 形式；子系统含 `proceed:subsystem:`

## 校验

```shell
python -m unittest discover -s tests -v
python scripts/validate_report.py <report.md>
python scripts/validate_report.py --evidence-dir <evidence-dir> [--json]
```

退出码 `0` / `3` / `4`。通过只表示结构合规。

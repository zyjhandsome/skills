# 报告契约

## 文件名

- `vue2-to-vue3-upgrade-report.md`（必填）
- `upgrade-summary.json`（必填，≤12 KiB）
- `inventory.json`（执行 profile 时必填）
- `decision-records/migration-path__<path-id>.md`（路径单元必填）
- `decision-records/subsystem__<subsystem-id>.md`（每个 High/blocker 或 `required_for_path=yes` 子系统必填；其余可选）

语言：可见正文默认简体中文；枚举、包名、版本、路径、命令、URL 保持英文原文。

## 报告目录解析

1. 显式 `--output-dir`
2. 否则默认候选：`<project-root>/.vue2-to-vue3-upgrade-analysis`

硬规则：输出目录只属于本 Skill；须复述绝对路径并得到显式确认（`--output-dir <path>` 或 `confirm:output-dir`）后再写。路径未确认前只读分析、禁止写入。口语「写到仓库」无效。

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
| `batch_implementation_gate` | `frozen` / `ready`（**仅分析交接**；≠实施授权） |
| `implementation_readiness` | `not_assessed`（本技能固定值） |
| `behavior_parity_required` | `yes` / `no` |
| `network_mode` | `online` / `offline` / `partial` |
| `report_path` | 实际报告目录（禁止单独 `.` / `./`；须与校验时目录 resolve 等价；相对路径相对进程 cwd） |
| `evidence_as_of` | 证据采集日，`YYYY-MM-DD`（registry/官方页/仓画像读取日；非“永远正确”证明） |

以下为独立输出字段；不表示任何外部流程的状态或实施授权：

| 字段 | 取值 |
|---|---|
| `schema` | `vue3-upgrade-report/v1` |
| `producer` | `vue2-to-vue3-upgrade-impact-analysis` |
| `summary_path` | 同一输出目录内的 `upgrade-summary.json` |
| `visual_acceptance_required` | `yes` / `no` |

`batch_implementation_gate=ready` 额外要求：§1 的结构化字段必须为
`lockfile_status: present`；`absent` / `unparsed` 一律保持 `frozen`。每个
High/blocker 与每个 `required_for_path=yes` 均为 `decided`（`deferred` 只允许
`complete`+`frozen`）。

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

章节「1. 基线与假设」必须出现结构化字段
`lockfile_status: present|absent|unparsed`，并说明 lock 路径、解析错误或缺失时的
复现性风险。即使正文另写「无 lockfile」，也不得用自然语言同义词代替该字段；
非 `present` 时 handoff gate 必须
`frozen`。
§1 可复述 `evidence_as_of`；若复述则必须与状态表一致。
章节「3. 推荐迁移路径」必须出现字面：`Composition API 全仓重写：另立项，本次不评估工作量`。
章节「3」必须出现 `推荐路径 id：<path-id>`，且 `<path-id>` ∈
`compat-big-bang` / `direct-vue3` / `microfrontend-coexist` /
`deferred-inventory-only`。
章节「3」必须出现三轴标记（取值见 `migration-path-ladder.md`）：

- `runtime_axis:` `compat` / `direct-vue3`
- `build_axis:` `vite` / `cli5-webpack5` / `existing-vite`
- `topology_axis:` `single-cutover` / `coexist`

三轴须与 path preset 一致（例如 `compat-big-bang` ⇒ `runtime_axis: compat` +
`topology_axis: single-cutover`；`build_axis` 可为 `vite` 或 `cli5-webpack5`）。
非默认轴组合须改选匹配的 path id，或 Wave 1 走 `other` 后把最终 path id /
轴写进 Decision Record——校验器拒绝 preset 与轴互相矛盾的报告。
§7 唯一 path 行的 id 必须与 §3 `推荐路径 id` 相同。

当 §2 出现 UI-kit、Tailwind/reset、表格/editor/tree/DAG 等视觉触发包，或
源码证据命中 scoped-style/fallthrough/theme/Teleport 风险时，状态表必须写
`visual_acceptance_required: yes`，§5 必须含 `### ui_visual_risk` 与以下非空标记：

- `triggers:`
- `legacy_selectors:`
- `css_entry_order:`
- `theme_and_teleport:`
- `tailwind_reset:`
- `primary_sample:`
- `secondary_sample:`（不适用时写有依据的 `not_applicable`）
- `baseline_status:`
- `required_visual_states:`
- `recommended_next_action:`（通用动作，不得填写其他 Skill 名称）

仅写“做视觉回归”不合规。无触发器时可写
`visual_acceptance_required: no`，但须保留可审计的证据理由。

章节「3」或「7」附近必须出现：`Name, never run`，**或**同时出现「命名配方」与「不执行」（二者缺一不可；仅有「命名配方」表头不算）。
章节「10」必须出现字面：`人工补搜检查`，并勾选/回答下列项（即使 profile 已扫描）：

- `slot-scope` / 旧 `slot=` 模板
- 全局 `Vue.filter` 注册
- 非 `vue-*` 前缀的 Vue2-only / 编辑器类包
- `Vue.prototype.$*` 定义与 `this.$*` 消费点（独立行）
- 对应的 `app.config.globalProperties` 或 `provide/inject` 迁移目标（独立行）
- lockfile 缺失或未解析时的版本复现风险

上述每一项必须有**独立行**与非空实质结果；禁止一行打包全部项，禁止仅写
`已声明` / `已检查` / `已核对` / `ok` 等空泛词。

§4 必须覆盖默认子系统全集（`core-vue` / `router` / `build` / `store` /
`ui` / `test` / `lint-ide` / `i18n-plugins` / `composition-existing` /
`blockers`）；不适用者标 `not_applicable`，不得省略。
§4 中每个 `risk` 为 `high`/`blocker` 且非 `not_applicable` 的子系统，以及每个 `required_for_path=yes` 行，必须出现在 §7 确认队列；`analysis_status=complete` 时还须有对应 `decision-records/subsystem__<id>.md`。
`in_scope` 且 `high`/`blocker` 的行必须 `required_for_path=yes`。
路径未 `decided` 前，子系统行不得为 `ready`。

## 仓画像表列（§2）

`包名 | 当前版本 | Vue3 就绪度 | 建议 | 证据`

就绪度：`ready` / `needs-major` / `replace` / `unknown` / `unused`

## 子系统表列（§4）

`子系统 | scope_status | 风险 | 就绪度 | required_for_path | 命名配方 | 说明`

`required_for_path`：`yes` / `no`

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

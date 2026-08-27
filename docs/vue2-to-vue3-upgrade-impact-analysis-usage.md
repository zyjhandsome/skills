# Vue2→Vue3 升级影响分析 — 使用导览

> 受众：第一次跑本 Skill 的同学，以及只需要决策包、还不改代码的调用方。  
> 基准：`vue2-to-vue3-upgrade-impact-analysis/SKILL.md` + `references/*`。  
> 语言：正文简体中文；枚举、包名、路径、命令、URL 保持英文原文。
>
> 本 Skill **只出决策包**，不改代码、不跑 codemod、不写 OpenSpec/delivery 状态。  
> 单仓原地升要做到仓内 `verified`，唯一顺序以
> [`vue2-to-vue3-upgrade-impact-analysis-playbook.md`](./vue2-to-vue3-upgrade-impact-analysis-playbook.md)
> 为准。跨仓页面迁入走
> [`vue2-pages-to-vue3-host-migration-playbook.md`](./vue2-pages-to-vue3-host-migration-playbook.md)，
> 不要用本 Skill 当实施器。

---

## 1. 一句话心智模型

Agent 体检环境 → 画像 workspace → 推荐路径三维 → 当场按确认队列问你 → 写入决策并重生成 → `analysis_status=complete`（本 Skill 终点）。

**只有** `batch_implementation_gate=ready` **且**另有实施授权时，才可以改依赖 / 跑配方。那一步不在本 Skill 内，`implementation_readiness` 永远是 `not_assessed`。

| 轴 | 问题 | 典型取值 |
|---|---|---|
| `analysis_status` | 证据齐了吗？ | `partial` / `blocked` / `complete` |
| `decision_status` | 人拍板了吗？ | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | 整批能否去交接实施？ | `frozen` / `ready`（仅分析交接；≠实施授权） |

`ready` 额外要求：lockfile `present`；每个 High/blocker 与每个 `required_for_path=yes` 均为 `decided`（`deferred` 只允许 `complete` + `frozen`）。

---

## 2. 最短上手提示词

先决定输出目录，再抄提示词——这一步选错，Wave 2 会到空目录里找分析包。

| 你接下来要做什么 | `--output-dir` 写哪 |
|---|---|
| 之后要按原地升剧本改代码、做到仓内 `verified` | `<workspace>/openspec/changes/vue2-to-vue3-inplace-<SLUG>/evidence/vue2-to-vue3-upgrade` |
| 只要一份决策包，不接剧本 | `<前端 workspace>/.vue2-to-vue3-upgrade-analysis` |

**单仓原地升（要接剧本，推荐）：**

```text
用 vue2-to-vue3-upgrade-impact-analysis 做 Vue2→Vue3 升级影响分析。
只出决策包，不改代码、不跑 codemod。
项目：<前端 workspace 绝对路径>
--output-dir <workspace>/openspec/changes/vue2-to-vue3-inplace-<SLUG>/evidence/vue2-to-vue3-upgrade
```

**单仓一次性分析（不接剧本）：** 同上，把 `--output-dir` 换成
`<前端 workspace>/.vue2-to-vue3-upgrade-analysis`。两个目录不要同时维护。

**多仓巡检：**

```text
用 vue2-to-vue3-upgrade-impact-analysis 做多仓巡检，先给候选清单并问我选批，
再对选定批出决策包（不改代码）。
roots：<父目录或仓库列表>
```

**A→B 只分析（不是页面迁入实施）：**

```text
用 vue2-to-vue3-upgrade-impact-analysis 做 A→B host-port 影响分析（只出决策包）。
source_root：<Vue2 仓 A>
implementation_target：<Vue3 host B>
forbid_source_mutation: yes
```

想把报告挂进 OpenSpec change 时，由**调用方**提供绝对路径。单仓原地升剧本默认：
`--output-dir <workspace>/openspec/changes/vue2-to-vue3-inplace-<SLUG>/evidence/vue2-to-vue3-upgrade`。
本 Skill 不认识 OpenSpec，也不创建 change。

---

## 3. 你需要回答的常见问题

路径未确认前只读、禁止写报告。口语「写到仓库」无效；用 `--output-dir <path>`
或 `confirm:output-dir`。

「继续 / 全部放行 / 别再问了 / 全部纳入」**不是**确认。须逐单元回复字面 token：

| 场景 | 建议项 | 你怎么答 |
|---|---|---|
| Wave 0 设置确认（画像期一次问完） | 见下表 | 一行一个 `confirm:<topic>[:<值>]`；出现未开启项、未知 topic 或 `全部` 则**整条消息作废**重问 |
| Wave 1 路径 | 原地升 `compat-big-bang`；A→B `host-port-direct` | `proceed:path:compat-big-bang` / `proceed:path:direct-vue3` / `proceed:path:host-port-direct` / `proceed:path:microfrontend-coexist` / `defer` / `other` |
| Wave 2+ 子系统 | 全部 `proceed`（`required_for_path=yes` 是路径前提） | `proceed:subsystem:<id>` / `defer` / `other`；也可一次答多个**列举**的 id：`proceed:subsystem:core-vue,router,ui,build`（不接受 `all` / `*` / `全部`；含未知或未 ready 的 id 则整条作废重问） |
| 多仓候选 | 先出一个仓，证据才可比 | `proceed:batch:<workspace_id>`，多选逐个列全，或 `defer` |
| 无 lockfile | 先补 lock 再求 `ready` | 否则最多 `complete` + `frozen` |
| 推荐变成 host-port / 仓内已有 Vue3 宿主 | 停原地升 | 改走页面迁入剧本 |
| workspace 本身已是 Vue3 | `defer`（没有 Vue2 基线可升） | `proceed:path:residual-audit` 出残留审计包（不写 Vue2 基线） |

Wave 0 的九项设置确认（触发了才问，其余按证据默认；完整选项与不答的后果见 Skill 的
`references/user-decision-catalog.md`）：

| topic | 何时问你 | 建议项 | 你怎么答 |
|---|---|---|---|
| `output-dir` | 调用没带 `--output-dir` | 候选 `.vue2-to-vue3-upgrade-analysis` | `confirm:output-dir` 或 `confirm:output-dir:<绝对路径>` |
| `workspace` | 根下有多个前端 workspace | 含待升 `vue` 且离根最近的 | `confirm:workspace:<workspace_id>` |
| `package-manager` | ≥2 个 lockfile 或与 `packageManager` 不一致 | `packageManager` 声明的那个 | `confirm:package-manager:pnpm` |
| `network-mode` | registry 与官方文档**双双**探测失败 | `defer`，补网络再跑 | `confirm:network-mode:offline` / `:partial` |
| `browser-floor` | 无 browserslist，或配置含旧浏览器 | 无旧浏览器证据时取 `modern` | `confirm:browser-floor:modern` / `:legacy-plugin` |
| `behavior-parity` | 你要求行为变更，或 UI 库 `replace` 使严格 parity 不可能 | `yes` | `confirm:behavior-parity:yes` / `:no` + 逐条列出允许变化的行为 |
| `scope` | 调用没限定范围 | 原地升 `full-stack`，A→B `page-closure` | `confirm:scope:full-stack` |
| `target-version` | 需要目标面 `engines.node`，或某包 `latest` 已越过迁移文档区间 | 钉迁移文档区间覆盖的那个 major | `confirm:target-version:vite@5.4.11` |
| `node-target` | 同上 | 目标区间内维护期最长的活跃 LTS | `confirm:node-target:22.12.0` |
| `node-strategy` | `node_compatibility_status: upgrade-required` | `upgrade-before-vue`（先让旧仓在目标 Node 跑绿，再动 Vue） | `confirm:node-strategy:upgrade-before-vue` |

`node-target` 与 `node-strategy` 是两问：`target_node_requirement` 给的是**区间**
（如 `^20.19.0 || >=22.12.0`），而 `.nvmrc`、`engines.node`、CI、Docker、部署 builder
每一处只能填**一个值**——那个值由你定，写进 §1 `selected_node_version`；策略只回答
「怎么从当前 Node 走过去」。

子系统除了「纳不纳入」，多数还有一个**内部分叉**，与该子系统的问题同时出示，各有
各的 token（完整清单见 catalog D15–D20）：

| 子系统 | 分叉 | 建议项 | 你怎么答 |
|---|---|---|---|
| `router` | 装 v4 还是 v5 | v4（Vue2 仓主迁移文档是 v3→v4；`latest` 已是 v5，裸装会落到 v5） | `confirm:router-major:4` |
| `store` | 留 Vuex 4 还是迁 Pinia | Vuex 4（本轮目标是升级，不是换状态库） | `confirm:store-target:vuex4` |
| `ui` | 与 runtime 同批切还是切完再切 | `after-runtime`（同批时两个 codemod 落在同一批调用点上） | `confirm:ui-staging:after-runtime` |
| `i18n-plugins` | vue-i18n v9 legacy 还是 composition | `legacy`（与保留 Options API 一致） | `confirm:i18n-mode:legacy` |
| `blockers` | 每个残留包 replace/fork/remove/defer | 逐包给建议 | `confirm:blocker:<pkg>:replace` |
| `test` | 保留现有 runner 还是换 | 保留，只升 `@vue/test-utils` 到 v2 | `confirm:test-runner:keep` |

`build` 的 Vite vs cli5-webpack5 不在此列：它是路径三轴之一（`build_axis`），跟着
path preset 走，要非默认组合只能在 Wave 1 路径那一问回 `other`。

`defer` 与 `other` 的区别：`defer` 是「现在不定」，该项若是 High/blocker 或
`required_for_path=yes`，`batch_implementation_gate` 就永远 `frozen`；`other` 是
「给的选项都不合适」，你补一句 `other: <想要什么>`，Agent 须把它翻译成具体的
path id + 三轴再用原样 token 重问一次，`other` 本身不会被记成 `decided`。

这里的 **Wave 是确认队列的批次**（先路径、后子系统），和剧本里 Wave 1–5 的会话
阶段不是一回事。剧本 Wave 1 整个装的就是本 Skill 的全部 Wave。

`proceed:path:residual-audit` 只在画像显示 workspace 已是 Vue3 时出现，且那一轮
只有它和 `defer` 两个选项——它不是升级路径，不会混进升级菜单当备选。

贴剧本跑时，目标 Vue 版本用的是剧本通用头里那个**核对日期已知的固定钉**，它随
时间必然落后于 registry 最新补丁；要装别的补丁，须自己在通用头写出精确版本号。
单独跑本 Skill 时不吃这个钉，按当天 registry 解析。

单仓 Vue2 SPA 默认推荐 `compat-big-bang`（`compat` + `vite` + `single-cutover`）。  
同一 git 仓里「Vue2 应用 + 已有 Vue3 宿主」不是原地升，应按 `host-port`。  
`Composition API` 全仓重写：另立项，本次不评估工作量。

---

## 4. 定稿之后

横幅若写 `batch_implementation_gate=ready`，只表示分析交接可以开始，不是
install / codemod / 改 `package.json` 的授权。

- 只要决策包：到此停止。
- 单仓原地升要改代码并做到仓内 `verified`：按
  [`vue2-to-vue3-upgrade-impact-analysis-playbook.md`](./vue2-to-vue3-upgrade-impact-analysis-playbook.md)
  分波粘贴；不要同一会话从本 Skill 接到 Execute。实施会话（Wave 4）通过后还须
  新开 Wave 5 做独立功能验证，才能声称仓内 `verified`。
- 跨仓把一页迁入已有 Vue3 host：按
  [`vue2-pages-to-vue3-host-migration-playbook.md`](./vue2-pages-to-vue3-host-migration-playbook.md)。

报告里的 `recommended_next_action`（如 `run_visual_review`）是通用动作，**不会**
写出其他 Skill 名称。Skill 名只出现在上述剧本里。

定稿的 `upgrade-summary.json` 应含 `lockfile_status`、`named_recipes`、
`named_validations`，供后续实施会话在不加载本 Skill 文件夹时仍能点名配方与
验证命令（仍不在分析阶段执行）。

---

## 5. 相关路径

- Skill：`vue2-to-vue3-upgrade-impact-analysis/SKILL.md`
- 单仓原地升剧本：`docs/vue2-to-vue3-upgrade-impact-analysis-playbook.md`
- A→B 页面迁入剧本：`docs/vue2-pages-to-vue3-host-migration-playbook.md`
- 校验：

```shell
python vue2-to-vue3-upgrade-impact-analysis/scripts/validate_report.py <report.md>
python vue2-to-vue3-upgrade-impact-analysis/scripts/validate_upgrade_summary.py <upgrade-summary.json>
```

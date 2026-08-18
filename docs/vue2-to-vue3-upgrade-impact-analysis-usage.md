# Vue2→Vue3 升级影响分析 — 使用导览

> 受众：第一次跑本 Skill 的同学，以及只需要决策包、还不改代码的调用方。  
> 基准：`vue2-to-vue3-upgrade-impact-analysis/SKILL.md` + `references/*`。  
> 语言：正文简体中文；枚举、包名、路径、命令、URL 保持英文原文。
>
> 本 Skill **只出决策包**，不改代码、不跑 codemod、不写 OpenSpec/delivery 状态。  
> 单仓原地升要做到仓内 `verified`，唯一顺序以
> [`vue2-to-vue3-inplace-upgrade-playbook.md`](./vue2-to-vue3-inplace-upgrade-playbook.md)
> 为准。跨仓页面迁入走
> [`vue2-page-migration-playbook.md`](./vue2-page-migration-playbook.md)，
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

**单仓原地升（只分析）：**

```text
用 vue2-to-vue3-upgrade-impact-analysis 做 Vue2→Vue3 升级影响分析。
只出决策包，不改代码、不跑 codemod。
项目：<前端 workspace 绝对路径>
--output-dir <前端 workspace>/.vue2-to-vue3-upgrade-analysis
```

若接下来会按原地升剧本做到仓内 `verified`，把 `--output-dir` 改成剧本默认的
`<workspace>/openspec/changes/vue2-to-vue3-inplace-<SLUG>/evidence/vue2-to-vue3-upgrade`，
不要再写一份到 workspace 根。

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

| 场景 | 你怎么答 |
|---|---|
| Wave 1 路径 | `proceed:path:compat-big-bang` / `proceed:path:direct-vue3` / `proceed:path:host-port-direct` / `proceed:path:microfrontend-coexist` / `defer` / `other` |
| Wave 2+ 子系统 | `proceed:subsystem:<id>` / `defer` / `other` |
| 多仓候选 | 选 `workspace_id`（可多选）或 `defer` |
| 无 lockfile | 先补 lock 再求 `ready`；否则最多 `complete` + `frozen` |
| 推荐变成 host-port / 仓内已有 Vue3 宿主 | 停原地升；改走页面迁入剧本 |

单仓 Vue2 SPA 默认推荐 `compat-big-bang`（`compat` + `vite` + `single-cutover`）。  
同一 git 仓里「Vue2 应用 + 已有 Vue3 宿主」不是原地升，应按 `host-port`。  
`Composition API` 全仓重写：另立项，本次不评估工作量。

---

## 4. 定稿之后

横幅若写 `batch_implementation_gate=ready`，只表示分析交接可以开始，不是
install / codemod / 改 `package.json` 的授权。

- 只要决策包：到此停止。
- 单仓原地升要改代码并做到仓内 `verified`：按
  [`vue2-to-vue3-inplace-upgrade-playbook.md`](./vue2-to-vue3-inplace-upgrade-playbook.md)
  分波粘贴；不要同一会话从本 Skill 接到 Execute。实施会话（Wave 4）通过后还须
  新开 Wave 5 做独立功能验证，才能声称仓内 `verified`。
- 跨仓把一页迁入已有 Vue3 host：按
  [`vue2-page-migration-playbook.md`](./vue2-page-migration-playbook.md)。

报告里的 `recommended_next_action`（如 `run_visual_review`）是通用动作，**不会**
写出其他 Skill 名称。Skill 名只出现在上述剧本里。

定稿的 `upgrade-summary.json` 应含 `lockfile_status`、`named_recipes`、
`named_validations`，供后续实施会话在不加载本 Skill 文件夹时仍能点名配方与
验证命令（仍不在分析阶段执行）。

---

## 5. 相关路径

- Skill：`vue2-to-vue3-upgrade-impact-analysis/SKILL.md`
- 单仓原地升剧本：`docs/vue2-to-vue3-inplace-upgrade-playbook.md`
- A→B 页面迁入剧本：`docs/vue2-page-migration-playbook.md`
- 校验：

```shell
python vue2-to-vue3-upgrade-impact-analysis/scripts/validate_report.py <report.md>
python vue2-to-vue3-upgrade-impact-analysis/scripts/validate_upgrade_summary.py <upgrade-summary.json>
```

# Vue2 → Vue3 升级影响分析 — 使用逻辑总览

> 受众：Skill 维护/扩展者与操作者。  
> 基准：`vue2-to-vue3-upgrade-impact-analysis/SKILL.md` + `references/*`。  
> 语言：正文简体中文；枚举、包名、路径、命令保持英文原文。

本 Skill **只做证据驱动的决策包（Stage A）**，不做实施。与其他 Skill **解耦**。

---

## 1. 一句话心智模型

Agent 解析前端 workspace → preflight + 仓画像 → 推荐迁移路径 → 子系统风险清单 → **当场**确认队列（先路径，再 High/blocker 子系统）→ 决策落盘 → 校验 → `analysis_status=complete`。

| 轴 | 问题 | 取值 |
|---|---|---|
| `analysis_status` | 证据是否够完整？ | `partial` / `blocked` / `complete` |
| `decision_status` | 人是否已确认？ | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | 调用方可否开实施？ | `frozen` / `ready` |
| 实施授权 | 是否允许改代码/装依赖？ | 默认否；报告不能授权 |

---

## 2. 默认推荐路径

`compat-big-bang`：单仓大爆炸切流 + 仓内 `@vue/compat` + 构建必须同升（偏 Vite）。  
Composition API 全仓重写：**另立项，本次不评估工作量**。  
迁移工具：**只点名、不执行**。

---

## 3. 入口

| 入口 | 用法 |
|---|---|
| 单仓 workspace | 给出项目根 / workspace |
| 多仓 inventory | 先巡检候选表，人选批次后再出完整决策包 |

---

## 4. 常用命令

```shell
cd vue2-to-vue3-upgrade-impact-analysis
python scripts/preflight.py --project-root <app> --json
python scripts/profile_inventory.py --project-root <app> --json
python scripts/validate_report.py fixtures/valid-report.md
python -m unittest discover -s tests -v
```

报告目录：既有 `--change-dir` →  
`<change-dir>/evidence/vue2-to-vue3-upgrade/`。

---

## 5. 确认队列

1. Wave 1：`proceed:path:<id>` / `defer` / `other`  
2. Wave 2：每个 High/blocker `proceed:subsystem:<id>` / `defer` / `other`（同波）  
有 `ready`/`pending` ⇒ **当场问**，不要只贴草稿等「继续」。

---

## 6. 相关文档

- 调研摘要：[`vue2-to-vue3-migration-research.md`](./vue2-to-vue3-migration-research.md)  
- 可选 delivery 软挂载：[`vue2-to-vue3-upgrade-delivery-usage.md`](./vue2-to-vue3-upgrade-delivery-usage.md)
